"""Read reference data and write processed weather files."""

import logging
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def load_wmo_codes() -> pd.DataFrame:
    """Load the packaged WMO weather code reference table."""
    reference = files("weatherflow").joinpath(
        "reference", "wmo_codes.csv"
    )

    with reference.open("rb") as file:
        return pd.read_csv(file)


def save_processed(
    df: pd.DataFrame,
    processed_dir: Path,
    run_time: datetime,
) -> Path:
    """Save transformed records as partitioned Parquet."""
    run_time = run_time.astimezone(timezone.utc)

    run_date = run_time.strftime("%Y-%m-%d")
    timestamp = run_time.strftime("%Y%m%dT%H%M%S%f")

    output_dir = (
        processed_dir
        / "weather_hourly"
        / f"run_date={run_date}"
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"part-{timestamp}.parquet"

    df.to_parquet(
        output_file,
        engine="pyarrow",
        compression="snappy",
        index=False,
    )

    logger.info(
        "Saved %s processed records to %s",
        len(df),
        output_file,
    )

    return output_file
