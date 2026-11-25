"""Transform raw weather responses into standardised records."""

import logging
from datetime import datetime, timezone

import pandas as pd

logger = logging.getLogger(__name__)


def transform(raw: list[tuple[str, dict]]) -> pd.DataFrame:
    """Flatten, clean and standardise hourly weather data."""
    city_dfs = []

    ingested_at = datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )

    for city_name, payload in raw:
        city_df = pd.DataFrame(payload["hourly"])

        city_df["city"] = city_name
        city_df["latitude"] = payload["latitude"]
        city_df["longitude"] = payload["longitude"]
        city_df["ingested_at_utc"] = ingested_at

        city_dfs.append(city_df)

    df = pd.concat(city_dfs, ignore_index=True)

    df["time"] = pd.to_datetime(df["time"], utc=True)

    df = df.rename(columns={
        "time": "observed_at_utc",
        "temperature_2m": "temperature_c",
        "apparent_temperature": "feels_like_c",
        "relative_humidity_2m": "humidity_pct",
        "precipitation": "precipitation_mm",
        "wind_speed_10m": "wind_speed_kmh",
    })

    df["observed_at_local"] = (
        df["observed_at_utc"].dt.tz_convert("Europe/London")
    )

    df = df.drop_duplicates(
        subset=["city", "observed_at_utc"],
        keep="last",
    )

    columns = [
        "city",
        "observed_at_utc",
        "observed_at_local",
        "temperature_c",
        "feels_like_c",
        "humidity_pct",
        "precipitation_mm",
        "wind_speed_kmh",
        "weather_code",
        "ingested_at_utc",
    ]

    df = df[columns]

    logger.info("Transformed records: %s", len(df))

    return df
