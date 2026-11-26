"""Orchestrate the WeatherFlow ETL pipeline."""

import logging
from datetime import datetime, timezone

from .extract import extract
from .transform import transform
from .load import load
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

logger = logging.getLogger(__name__)


def run(config: dict) -> int:
    """Run extraction, transformation, validation and loading."""

    logger.info(
        "Starting WeatherFlow ETL pipeline..."
    )

    run_time = datetime.now(timezone.utc)

    results = []
    input_count = 0
    good_count = 0
    quarantine_count = 0
    loaded_count = 0
    status = "FAILED"
    error_message = ""

    try:
        raw, failed = extract(config)

        extraction_passed = (
            bool(raw) and not failed
        )

        results.append(
            CheckResult(
                name="extraction_success",
                dimension="completeness",
                severity="fail",
                passed=extraction_passed,
                failed_rows=0,
                details=(
                    f"{len(raw)} successful cities; "
                    f"{len(failed)} failed cities. "
                    f"Failures: {', '.join(failed)}"
                ),
            )
        )

        if not raw:
            raise RuntimeError(
                "No successful extractions. "
                "Database load cancelled."
            )

        lookup = load_wmo_codes()

        df = transform(
            raw,
            lookup,
            ingested_at_utc=run_time.isoformat(
                timespec="seconds"
            ),
            deduplicate_records=False,
        )

        df["source"] = "open_meteo_forecast"

        input_count = len(df)

        logger.info(
            "Transformed records: %s",
            input_count,
        )

        expected_hours = forecast_expected_hours(
            config,
            run_time,
        )

        # Current runs use a full forecast window.
        # Incremental mode is introduced in Task 2.6.
        try:
            good, bad, checks = validate(
                df,
                config,
                expected_hours,
                now=run_time,
                incremental=False,
            )

        except DataQualityError as error:
            # Preserve the check results and quarantined
            # records even when the run must fail.
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

        # Blocking failures must stop BEFORE loading.
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

        # Only validated records reach processed storage.
        save_processed(
            good,
            config["paths"]["processed_dir"],
            run_time,
        )

        loaded_count = load(
            good,
            config,
        )

        if any(
            not result.passed
            for result in results
        ):
            status = "SUCCESS_WITH_DQ_ISSUES"
        else:
            status = "SUCCESS"

        logger.info(
            "WeatherFlow ETL pipeline "
            "completed successfully!"
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
        # Produce a report on successful and failed runs.
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
