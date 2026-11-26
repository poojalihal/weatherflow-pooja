"""Data quality checks for transformed weather records."""

import logging
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """Describe the outcome of an individual quality check."""

    name: str
    dimension: str
    severity: str
    passed: bool
    failed_rows: int
    details: str
    skipped: bool = False


class DataQualityError(Exception):
    """Indicate a blocking data quality failure."""

    def __init__(
        self,
        good_rows: pd.DataFrame,
        quarantined_rows: pd.DataFrame,
        results: list[CheckResult],
    ) -> None:
        self.good_rows = good_rows
        self.quarantined_rows = quarantined_rows
        self.results = results

        failures = [
            result.name
            for result in results
            if result.severity == "fail"
            and not result.passed
        ]

        super().__init__(
            "Blocking data quality failure: "
            + ", ".join(failures)
        )


def forecast_expected_hours(
    config: dict,
    run_time: datetime,
) -> dict[str, pd.DatetimeIndex]:
    """Build the expected UTC observation window per city."""

    today = pd.Timestamp(run_time).tz_convert(
        "UTC"
    ).normalize()

    start = today - pd.Timedelta(
        days=config["api"]["past_days"]
    )

    end = today + pd.Timedelta(
        days=config["api"]["forecast_days"]
    )

    hours = pd.date_range(
        start=start,
        end=end,
        freq="h",
        inclusive="left",
    )

    return {
        city["name"]: hours
        for city in config["cities"]
    }


def validate(
    df: pd.DataFrame,
    config: dict,
    expected_hours: dict[str, pd.DatetimeIndex],
    now: datetime,
    *,
    incremental: bool = False,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    list[CheckResult],
]:
    """Validate records and separate valid and quarantined rows."""

    thresholds = config["data_quality"]

    frame = df.reset_index(drop=True).copy()

    results = []

    reasons = [
        []
        for _ in range(len(frame))
    ]

    timestamps = pd.to_datetime(
        frame["observed_at_utc"],
        utc=True,
        errors="coerce",
    )

    temperature = pd.to_numeric(
        frame["temperature_c"],
        errors="coerce",
    )

    humidity = pd.to_numeric(
        frame["humidity_pct"],
        errors="coerce",
    )

    precipitation = pd.to_numeric(
        frame["precipitation_mm"],
        errors="coerce",
    )

    wind = pd.to_numeric(
        frame["wind_speed_kmh"],
        errors="coerce",
    )

    feels_like = pd.to_numeric(
        frame["feels_like_c"],
        errors="coerce",
    )

    def row_check(
        name: str,
        dimension: str,
        severity: str,
        mask: pd.Series,
        details: str,
    ) -> None:
        """Record a row-level result and quarantine reasons."""

        mask = mask.fillna(False).astype(bool)

        failed_rows = int(mask.sum())

        results.append(
            CheckResult(
                name=name,
                dimension=dimension,
                severity=severity,
                passed=failed_rows == 0,
                failed_rows=failed_rows,
                details=details,
            )
        )

        if severity == "quarantine":
            for index in mask[mask].index:
                reasons[index].append(name)

    # CHECK 1: Mandatory fields.
    missing_city = (
        frame["city"]
        .astype("string")
        .str.strip()
        .eq("")
        .fillna(True)
    )

    missing_source = (
        frame["source"]
        .astype("string")
        .str.strip()
        .eq("")
        .fillna(True)
    )

    row_check(
        "mandatory_fields",
        "completeness",
        "quarantine",
        (
            missing_city
            | missing_source
            | timestamps.isna()
            | temperature.isna()
        ),
        "City, UTC observation time, temperature and "
        "source must be present.",
    )

    # CHECK 2: Temperature range.
    temperature_valid = temperature.between(
        thresholds["temperature_min_c"],
        thresholds["temperature_max_c"],
    ).fillna(False)

    row_check(
        "temperature_range",
        "validity",
        "quarantine",
        ~temperature_valid,
        (
            f"Temperature must be between "
            f'{thresholds["temperature_min_c"]} and '
            f'{thresholds["temperature_max_c"]} C.'
        ),
    )

    # CHECK 3: Humidity range.
    humidity_valid = humidity.between(
        thresholds["humidity_min_pct"],
        thresholds["humidity_max_pct"],
    ).fillna(False)

    row_check(
        "humidity_range",
        "validity",
        "quarantine",
        ~humidity_valid,
        (
            f"Humidity must be between "
            f'{thresholds["humidity_min_pct"]} and '
            f'{thresholds["humidity_max_pct"]} percent.'
        ),
    )

    # CHECK 4: Non-negative precipitation and wind.
    precipitation_valid = precipitation.ge(
        thresholds["precipitation_min_mm"]
    ).fillna(False)

    wind_valid = wind.ge(
        thresholds["wind_speed_min_kmh"]
    ).fillna(False)

    row_check(
        "non_negative_weather",
        "validity",
        "quarantine",
        ~(precipitation_valid & wind_valid),
        (
            f"Precipitation must be at least "
            f'{thresholds["precipitation_min_mm"]} mm; '
            f"wind speed must be at least "
            f'{thresholds["wind_speed_min_kmh"]} km/h.'
        ),
    )

    # CHECK 5: Duplicate observation keys.
    key_frame = frame[
        ["city", "observed_at_utc", "source"]
    ].copy()

    key_frame["observed_at_utc"] = timestamps

    duplicates = key_frame.duplicated(
        subset=[
            "city",
            "observed_at_utc",
            "source",
        ],
        keep=False,
    )

    duplicate_count = int(duplicates.sum())

    results.append(
        CheckResult(
            name="unique_observations",
            dimension="uniqueness",
            severity="fail",
            passed=duplicate_count == 0,
            failed_rows=duplicate_count,
            details=(
                "Each city, UTC observation time and "
                "source combination must be unique. "
                f"{duplicate_count} rows involved "
                "in duplicate keys."
            ),
        )
    )

    # CHECK 6: Exact expected hourly coverage.
    missing_total = 0
    missing_details = []

    for city, requested in expected_hours.items():

        city_mask = frame["city"].eq(
            city
        ).fillna(False)

        actual = pd.DatetimeIndex(
            timestamps[city_mask].dropna().unique()
        )

        missing = requested.difference(actual)

        if len(missing) > 0:
            missing_total += len(missing)

            examples = ", ".join(
                value.isoformat()
                for value in missing[:3]
            )

            missing_details.append(
                f"{city}: {len(missing)} missing "
                f"hours; examples: {examples}"
            )

    unexpected_cities = (
        frame["city"].notna()
        & ~frame["city"].isin(expected_hours)
        & ~missing_city
    )

    unexpected_count = int(
        unexpected_cities.sum()
    )

    coverage_passed = (
        missing_total == 0
        and unexpected_count == 0
    )

    results.append(
        CheckResult(
            name="expected_hourly_coverage",
            dimension="completeness",
            severity="fail",
            passed=coverage_passed,
            failed_rows=(
                missing_total + unexpected_count
            ),
            details=(
                "All configured cities and requested "
                "UTC hours are present."
                if coverage_passed
                else (
                    f"Missing hourly slots: "
                    f"{missing_total}. "
                    f"Unexpected city rows: "
                    f"{unexpected_count}. "
                    + "; ".join(missing_details)
                )
            ),
        )
    )

    # CHECK 7: Timeliness for incremental runs.
    if incremental:
        now_utc = pd.Timestamp(now).tz_convert("UTC")

        past_observations = timestamps[
            timestamps <= now_utc
        ]

        latest = past_observations.max()

        if pd.isna(latest):
            freshness_passed = False

            freshness_details = (
                "No non-future observations available."
            )

        else:
            age_hours = (
                now_utc - latest
            ).total_seconds() / 3600

            freshness_passed = (
                age_hours
                <= thresholds["freshness_max_hours"]
            )

            freshness_details = (
                f"Latest non-future observation: "
                f"{latest.isoformat()}; "
                f"age: {age_hours:.2f} hours."
            )

        results.append(
            CheckResult(
                name="observation_freshness",
                dimension="timeliness",
                severity="warn",
                passed=freshness_passed,
                failed_rows=0,
                details=freshness_details,
            )
        )

    else:
        results.append(
            CheckResult(
                name="observation_freshness",
                dimension="timeliness",
                severity="warn",
                passed=True,
                failed_rows=0,
                details=(
                    "Not applicable to full-window "
                    "or historical loads."
                ),
                skipped=True,
            )
        )

    # CHECK 8: Feels-like temperature consistency.
    temperature_difference = (
        feels_like - temperature
    ).abs()

    row_check(
        "feels_like_consistency",
        "consistency",
        "warn",
        temperature_difference.gt(
            thresholds[
                "feels_like_max_difference_c"
            ]
        ),
        (
            "Actual and feels-like temperature "
            "difference exceeds the configured "
            "maximum when this check fails."
        ),
    )

    # Separate valid rows and quarantined rows.
    reason_series = pd.Series(
        [
            "; ".join(row_reasons)
            for row_reasons in reasons
        ],
        index=frame.index,
        dtype="string",
    )

    bad_mask = reason_series.ne("")

    good_rows = frame.loc[
        ~bad_mask
    ].copy()

    quarantined_rows = frame.loc[
        bad_mask
    ].copy()

    quarantined_rows["dq_failure_reason"] = (
        reason_series.loc[bad_mask]
    )

    # A blocking failure prevents the entire load.
    if any(
        result.severity == "fail"
        and not result.passed
        for result in results
    ):
        raise DataQualityError(
            good_rows,
            quarantined_rows,
            results,
        )

    return (
        good_rows,
        quarantined_rows,
        results,
    )
