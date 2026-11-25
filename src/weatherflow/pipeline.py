"""Orchestrate the WeatherFlow ETL pipeline."""

import logging

from .extract import extract
from .transform import transform
from .load import load

logger = logging.getLogger(__name__)


def run(config: dict) -> int:
    """Run the ETL pipeline and return its exit code."""
    logger.info("Starting WeatherFlow ETL pipeline...")

    raw, failed = extract(config)

    if raw:
        df = transform(raw)
        load(df, config["paths"]["database"])

    else:
        logger.warning(
            "No successful extractions. Skipping transformation and loading."
        )

    if failed:
        logger.error(
            "Run FAILED: no data for %s",
            ", ".join(failed),
        )
        return 1

    logger.info("WeatherFlow ETL pipeline completed successfully!")

    return 0
