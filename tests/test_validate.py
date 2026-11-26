"""Test validation rules, quarantine and blocking failures."""

import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pandas as pd
import pytest

from weatherflow.config import load_config
from weatherflow.storage import load_wmo_codes
from weatherflow.transform import transform
from weatherflow.validate import (
    DataQualityError,
    forecast_expected_hours,
    validate,
)
from weatherflow.pipeline import run


NOW = datetime(
    2026, 11, 26, 12, 0,
    tzinfo=timezone.utc,
)


@pytest.fixture
def dq_config(tmp_path) -> dict:
    """Configure isolated paths and one test city."""

    config = load_config()

    config["cities"] = [
        city
        for city in config["cities"]
        if city["name"] == "London"
    ]

    config["api"]["past_days"] = 0
    config["api"]["forecast_days"] = 1

    config["paths"]["database"] = (
        tmp_path / "test_weather.db"
    )

    config["paths"]["raw_dir"] = (
        tmp_path / "raw"
    )

    config["paths"]["processed_dir"] = (
        tmp_path / "processed"
    )

    config["paths"]["quarantine_dir"] = (
        tmp_path / "quarantine"
    )

    config["paths"]["dq_reports_dir"] = (
        tmp_path / "dq_reports"
    )

    return config


@pytest.fixture
def weather_payload() -> dict:
    """Provide 24 complete hourly weather observations."""

    hours = pd.date_range(
        "2026-11-26",
        periods=24,
        freq="h",
    )

    return {
        "latitude": 51.50853,
        "longitude": -0.12574,
        "hourly": {
            "time": [
                hour.strftime("%Y-%m-%dT%H:%M")
                for hour in hours
            ],
            "temperature_2m": [10.0] * 24,
            "relative_humidity_2m": [80] * 24,
            "apparent_temperature": [9.0] * 24,
            "precipitation": [0.0] * 24,
            "wind_speed_10m": [10.8] * 24,
            "weather_code": [0] * 24,
            "is_day": [
                int(8 <= hour < 16)
                for hour in range(24)
            ],
        },
    }


@pytest.fixture
def clean_frame(weather_payload) -> pd.DataFrame:
    """Create a complete transformed test dataset."""

    df = transform(
        [("London", weather_payload)],
        load_wmo_codes(),
        NOW.isoformat(),
        deduplicate_records=False,
    )

    df["source"] = "open_meteo_forecast"

    return df


def check_frame(
    df: pd.DataFrame,
    config: dict,
    *,
    now: datetime = NOW,
    incremental: bool = True,
):
    """Validate test records against the fixed request window."""

    expected = forecast_expected_hours(
        config,
        NOW,
    )

    return validate(
        df,
        config,
        expected,
        now,
        incremental=incremental,
    )


def test_clean_data_passes_all_checks(
    clean_frame,
    dq_config,
):
    """A complete valid dataset passes all eight checks."""

    good, bad, results = check_frame(
        clean_frame,
        dq_config,
    )

    assert len(good) == 24
    assert bad.empty
    assert len(results) == 8
    assert all(result.passed for result in results)


@pytest.mark.parametrize(
    "column,value,reason",
    [
        (
            "temperature_c",
            99.0,
            "temperature_range",
        ),
        (
            "temperature_c",
            None,
            "mandatory_fields",
        ),
        (
            "humidity_pct",
            101,
            "humidity_range",
        ),
        (
            "precipitation_mm",
            -1.0,
            "non_negative_weather",
        ),
        (
            "wind_speed_kmh",
            -5.0,
            "non_negative_weather",
        ),
    ],
)
def test_invalid_records_are_quarantined(
    clean_frame,
    dq_config,
    column,
    value,
    reason,
):
    """Invalid weather measurements are quarantined."""

    clean_frame.loc[0, column] = value

    good, bad, results = check_frame(
        clean_frame,
        dq_config,
    )

    assert len(good) == 23
    assert len(bad) == 1

    assert reason in bad.iloc[0][
        "dq_failure_reason"
    ]

    assert any(
        result.name == reason
        and not result.passed
        for result in results
    )


def test_duplicate_raises_data_quality_error(
    clean_frame,
    dq_config,
):
    """Duplicate observation keys block the whole load."""

    duplicate_frame = pd.concat(
        [clean_frame, clean_frame.iloc[:1]],
        ignore_index=True,
    )

    with pytest.raises(
        DataQualityError,
        match="unique_observations",
    ) as error:
        check_frame(
            duplicate_frame,
            dq_config,
        )

    duplicate_result = next(
        result
        for result in error.value.results
        if result.name == "unique_observations"
    )

    assert not duplicate_result.passed
    assert duplicate_result.failed_rows == 2


def test_missing_requested_hour_blocks_load(
    clean_frame,
    dq_config,
):
    """Detect a missing hour even when row count is unchanged."""

    clean_frame.loc[
        0, "observed_at_utc"
    ] = pd.Timestamp(
        "2026-11-27T00:00:00Z"
    )

    assert len(clean_frame) == 24

    with pytest.raises(
        DataQualityError,
        match="expected_hourly_coverage",
    ):
        check_frame(
            clean_frame,
            dq_config,
        )


@pytest.mark.parametrize(
    "now",
    [
        NOW + timedelta(days=2),
        NOW - timedelta(days=1),
    ],
)
def test_stale_or_future_only_data_warns(
    clean_frame,
    dq_config,
    now,
):
    """Stale data and future-only data trigger freshness warnings."""

    good, bad, results = check_frame(
        clean_frame,
        dq_config,
        now=now,
    )

    freshness = next(
        result
        for result in results
        if result.name == "observation_freshness"
    )

    assert not freshness.passed
    assert freshness.severity == "warn"
    assert len(good) == 24
    assert bad.empty


def test_full_window_skips_freshness_check(
    clean_frame,
    dq_config,
):
    """Do not apply incremental freshness rules to full loads."""

    good, bad, results = check_frame(
        clean_frame,
        dq_config,
        incremental=False,
    )

    freshness = next(
        result
        for result in results
        if result.name == "observation_freshness"
    )

    assert freshness.skipped
    assert len(good) == 24
    assert bad.empty


def test_feels_like_difference_warns(
    clean_frame,
    dq_config,
):
    """Consistency failures warn without quarantining rows."""

    clean_frame.loc[0, "feels_like_c"] = 40.0

    good, bad, results = check_frame(
        clean_frame,
        dq_config,
    )

    consistency = next(
        result
        for result in results
        if result.name == "feels_like_consistency"
    )

    assert not consistency.passed
    assert consistency.failed_rows == 1
    assert consistency.severity == "warn"
    assert len(good) == 24
    assert bad.empty


class FixedDatetime(datetime):
    """Keep pipeline test execution time reproducible."""

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return NOW.replace(tzinfo=None)

        return NOW.astimezone(tz)


def test_pipeline_quarantines_99c_and_loads_valid_rows(
    monkeypatch,
    dq_config,
    weather_payload,
):
    """Save an invalid row and load only valid observations."""

    weather_payload["hourly"][
        "temperature_2m"
    ][0] = 99.0

    monkeypatch.setattr(
        "weatherflow.pipeline.datetime",
        FixedDatetime,
    )

    monkeypatch.setattr(
        "weatherflow.pipeline.extract",
        lambda config: (
            [("London", weather_payload)],
            [],
        ),
    )

    assert run(dq_config) == 0

    quarantine_files = list(
        dq_config["paths"]["quarantine_dir"]
        .rglob("*.parquet")
    )

    assert len(quarantine_files) == 1

    bad = pd.read_parquet(
        quarantine_files[0]
    )

    assert len(bad) == 1
    assert bad.iloc[0]["temperature_c"] == 99.0

    assert "temperature_range" in bad.iloc[0][
        "dq_failure_reason"
    ]

    processed_files = list(
        dq_config["paths"]["processed_dir"]
        .rglob("*.parquet")
    )

    assert len(processed_files) == 1
    assert len(
        pd.read_parquet(processed_files[0])
    ) == 23

    with closing(sqlite3.connect(
        dq_config["paths"]["database"]
    )) as conn:

        count = conn.execute(
            "SELECT COUNT(*) "
            "FROM fact_weather_hourly"
        ).fetchone()[0]

        invalid_count = conn.execute(
            "SELECT COUNT(*) "
            "FROM fact_weather_hourly "
            "WHERE temperature_c = 99"
        ).fetchone()[0]

    assert count == 23
    assert invalid_count == 0

    reports = list(
        dq_config["paths"]["dq_reports_dir"]
        .glob("*.md")
    )

    assert len(reports) == 1

    report = reports[0].read_text(
        encoding="utf-8"
    )

    assert "SUCCESS_WITH_DQ_ISSUES" in report
    assert "| Quarantined records | 1 |" in report
    assert "| Loaded records | 23 |" in report


def test_pipeline_duplicate_blocks_database_load(
    monkeypatch,
    dq_config,
    weather_payload,
):
    """Keep duplicates visible and stop before database loading."""

    weather_payload["hourly"][
        "temperature_2m"
    ][0] = 99.0

    # Duplicate the second hourly observation.
    for values in weather_payload[
        "hourly"
    ].values():
        values.append(values[1])

    monkeypatch.setattr(
        "weatherflow.pipeline.datetime",
        FixedDatetime,
    )

    monkeypatch.setattr(
        "weatherflow.pipeline.extract",
        lambda config: (
            [("London", weather_payload)],
            [],
        ),
    )

    mocked_load = Mock()

    monkeypatch.setattr(
        "weatherflow.pipeline.load",
        mocked_load,
    )

    assert run(dq_config) == 1

    mocked_load.assert_not_called()

    assert not dq_config[
        "paths"
    ]["database"].exists()

    assert not list(
        dq_config["paths"]["processed_dir"]
        .rglob("*.parquet")
    )

    # The invalid temperature is still preserved.
    quarantine_files = list(
        dq_config["paths"]["quarantine_dir"]
        .rglob("*.parquet")
    )

    assert len(quarantine_files) == 1
    assert len(
        pd.read_parquet(quarantine_files[0])
    ) == 1

    reports = list(
        dq_config["paths"]["dq_reports_dir"]
        .glob("*.md")
    )

    assert len(reports) == 1

    report = reports[0].read_text(
        encoding="utf-8"
    )

    assert "Run status: FAILED" in report
    assert "unique_observations" in report
    assert "| Loaded records | 0 |" in report


def test_failed_extraction_produces_report(
    monkeypatch,
    dq_config,
):
    """Report extraction failure without attempting a load."""

    monkeypatch.setattr(
        "weatherflow.pipeline.datetime",
        FixedDatetime,
    )

    monkeypatch.setattr(
        "weatherflow.pipeline.extract",
        lambda config: ([], ["London"]),
    )

    mocked_load = Mock()

    monkeypatch.setattr(
        "weatherflow.pipeline.load",
        mocked_load,
    )

    assert run(dq_config) == 1

    mocked_load.assert_not_called()

    reports = list(
        dq_config["paths"]["dq_reports_dir"]
        .glob("*.md")
    )

    assert len(reports) == 1

    report = reports[0].read_text(
        encoding="utf-8"
    )

    assert "Run status: FAILED" in report
    assert "extraction_success" in report
    assert "| Loaded records | 0 |" in report
