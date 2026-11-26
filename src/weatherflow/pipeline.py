"""Orchestrate the WeatherFlow ETL pipeline."""

import logging
from datetime import datetime, timezone

from .extract import extract
from .transform import transform
from .load import load
from .storage import load_wmo_codes, save_processed

logger = logging.getLogger(__name__)


def run(config: dict) -> int:
    """Run the ETL pipeline and return its exit code."""
    logger.info("Starting WeatherFlow ETL pipeline...")

    run_time = datetime.now(timezone.utc)

    raw, failed = extract(config)

    if raw:
        lookup = load_wmo_codes()

        df = transform(
            raw,
            lookup,
            ingested_at_utc=run_time.isoformat(
                timespec="seconds"
            ),
        )

        df["source"] = "open_meteo_forecast"

        logger.info(
            "Transformed records: %s",
            len(df),
        )

        save_processed(
            df,
            config["paths"]["processed_dir"],
            run_time,
        )

        load(df, config)

    else:
        logger.warning(
            "No successful extractions. "
            "Skipping transformation and loading."
        )

    if failed:
        logger.error(
            "Run FAILED: no data for %s",
            ", ".join(failed),
        )
        return 1

    logger.info(
        "WeatherFlow ETL pipeline completed successfully!"
    )

    return 0
