"""Orchestrate historical and incremental WeatherFlow loads."""

import logging

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone

from .extract import extract
from .transform import transform
from .load import load
from .postgres import load_postgres
from .storage import load_wmo_codes, save_processed
from .validate import (
    CheckResult,
    DataQualityError,
    forecast_expected_hours,
    validate,
)
from .dq_reporting import (
    save_quarantine,
    write_dq_report,
)
from .windows import (
    ARCHIVE_SOURCE,
    FORECAST_SOURCE,
    count_load_changes,
    expected_window_hours,
    extract_windows,
    plan_backfill,
    plan_incremental,
    resolve_backfill_dates,
)

logger = logging.getLogger(__name__)


def _execute(
    config: dict,
    acquire,
    source: str,
    run_time: datetime,
    *,
    incremental: bool,
) -> int:
    """Execute the shared transform, validate and load path."""

    logger.info(
        "Starting WeatherFlow pipeline: source=%s",
        source,
    )

    results = []
    input_count = 0
    good_count = 0
    quarantine_count = 0
    loaded_count = 0
    status = "FAILED"
    error_message = ""

    try:

        raw, failed, expected_hours = acquire()

        results.append(
            CheckResult(
                name="extraction_success",
                dimension="completeness",
                severity="fail",
                passed=bool(raw) and not failed,
                failed_rows=0,
                details=(
                    f"{len(raw)} successful requests; "
                    f"{len(failed)} failed requests. "
                    f"Failures: {', '.join(failed)}"
                ),
            )
        )

        if not raw:
            raise RuntimeError(
                "No successful extractions. "
                "Database load cancelled."
            )

        df = transform(
            raw,
            load_wmo_codes(),
            ingested_at_utc=run_time.isoformat(
                timespec="seconds"
            ),
            deduplicate_records=False,
        )

        df["source"] = source

        input_count = len(df)

        logger.info(
            "Transformed records: %s",
            input_count,
        )

        # Check for unexpected hours as well as missing hours.
        unexpected = 0

        for city, hours in expected_hours.items():

            mask = (
                df["city"].eq(city)
                & df["observed_at_utc"].notna()
                & ~df["observed_at_utc"].isin(hours)
            )

            unexpected += int(mask.sum())

        results.append(
            CheckResult(
                name="unexpected_observation_hours",
                dimension="validity",
                severity="fail",
                passed=unexpected == 0,
                failed_rows=unexpected,
                details=(
                    f"{unexpected} records outside "
                    "the requested observation window."
                ),
            )
        )

        try:

            good, bad, checks = validate(
                df,
                config,
                expected_hours,
                now=run_time,
                incremental=incremental,
            )

        except DataQualityError as error:

            good = error.good_rows
            bad = error.quarantined_rows
            checks = error.results

        results.extend(checks)

        good_count = len(good)
        quarantine_count = len(bad)

        for result in results:

            if result.skipped:

                logger.info(
                    "DQ SKIPPED: %s | %s",
                    result.name,
                    result.details,
                )

            elif result.passed:

                logger.info(
                    "DQ PASS: %s",
                    result.name,
                )

            else:

                level = (
                    logging.ERROR
                    if result.severity == "fail"
                    else logging.WARNING
                )

                logger.log(
                    level,
                    "DQ FAIL: %s | severity=%s | "
                    "affected=%s | %s",
                    result.name,
                    result.severity,
                    result.failed_rows,
                    result.details,
                )

        logger.info(
            "DQ summary: input=%s, valid=%s, "
            "quarantined=%s",
            input_count,
            good_count,
            quarantine_count,
        )

        if not bad.empty:

            save_quarantine(
                bad,
                config["paths"]["quarantine_dir"],
                run_time,
            )

        if any(
            result.severity == "fail"
            and not result.passed
            for result in results
        ):

            raise DataQualityError(
                good,
                bad,
                results,
            )

        if good.empty:
            raise RuntimeError(
                "No valid records available to load."
            )

        if config.get("database_backend") == "postgres":
            new_count, updated_count = 0, 0
        else:
            new_count, updated_count = count_load_changes(good, config['paths']['database'])

        save_processed(
            good,
            config["paths"]["processed_dir"],
            run_time,
        )

        if config.get("database_backend") == "postgres":
            loaded_count, new_count, updated_count = load_postgres(good, config)
        else:
            loaded_count = load(good, config)

        logger.info(
            "Load summary: source=%s new=%s updated=%s "
            "total_upserted=%s",
            source,
            new_count,
            updated_count,
            loaded_count,
        )

        status = (
            "SUCCESS_WITH_DQ_ISSUES"
            if any(not result.passed for result in results)
            else "SUCCESS"
        )

        logger.info(
            "WeatherFlow ETL pipeline completed successfully!"
        )

        return 0

    except DataQualityError as error:

        error_message = str(error)

        logger.error(
            "%s. Database load cancelled.",
            error_message,
        )

        return 1

    except Exception as error:

        error_message = str(error)

        logger.exception(
            "WeatherFlow pipeline failed"
        )

        return 1

    finally:

        write_dq_report(
            results,
            config["paths"]["dq_reports_dir"],
            run_time,
            status=status,
            input_rows=input_count,
            good_rows=good_count,
            quarantined_rows=quarantine_count,
            loaded_rows=loaded_count,
            error=error_message,
        )


def run(
    config: dict,
    *,
    incremental: bool = True,
) -> int:
    """Run incremental forecast loading by default."""

    run_time = datetime.now(timezone.utc)

    def acquire():

        if not incremental:

            raw, failed = extract(config)

            return (
                raw,
                failed,
                forecast_expected_hours(
                    config,
                    run_time,
                ),
            )

        windows = plan_incremental(
            config,
            run_time,
        )

        raw, failed = extract_windows(
            config,
            windows,
            archive=False,
        )

        return (
            raw,
            failed,
            expected_window_hours(windows),
        )

    return _execute(
        config,
        acquire,
        FORECAST_SOURCE,
        run_time,
        incremental=incremental,
    )


def backfill(
    config: dict,
    *,
    days: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> int:
    """Load historical archive data using the shared pipeline."""

    run_time = datetime.now(timezone.utc)

    start, end = resolve_backfill_dates(
        config,
        run_time,
        days=days,
        start_date=start_date,
        end_date=end_date,
    )

    # Extend the date dimension when older history is requested.
    # Do not modify the original configuration or shrink its range.
    config = deepcopy(config)

    existing_start = date.fromisoformat(
        str(config["dim_date"]["start"])
    )

    existing_end = date.fromisoformat(
        str(config["dim_date"]["end"])
    )

    config["dim_date"]["start"] = min(
        existing_start,
        start,
    ).isoformat()

    config["dim_date"]["end"] = max(
        existing_end,
        end + timedelta(days=1),
    ).isoformat()

    logger.info(
        "Backfill requested: start=%s end=%s days=%s",
        start,
        end,
        (end - start).days + 1,
    )

    def acquire():

        windows = plan_backfill(
            config,
            start,
            end,
        )

        logger.info(
            "Historical request windows: %s",
            len(windows),
        )

        raw, failed = extract_windows(
            config,
            windows,
            archive=True,
        )

        return (
            raw,
            failed,
            expected_window_hours(windows),
        )

    return _execute(
        config,
        acquire,
        ARCHIVE_SOURCE,
        run_time,
        incremental=False,
    )
