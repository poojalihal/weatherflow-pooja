
import logging
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from extract import DB_PATH, LOG_DIR, extract

logger = logging.getLogger(__name__)



# --------------------------------------------------
# 2. TRANSFORM
# --------------------------------------------------

def transform(raw: list[tuple[str, dict]]) -> pd.DataFrame:
    """Flatten, clean and standardise the weather data."""

    city_dfs = []

    # One UTC timestamp for this entire pipeline run
    ingested_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for city_name, payload in raw:

        # Convert hourly JSON data into a DataFrame
        city_df = pd.DataFrame(payload["hourly"])

        # Add city and location metadata
        city_df["city"] = city_name
        city_df["latitude"] = payload["latitude"]
        city_df["longitude"] = payload["longitude"]

        # Add pipeline ingestion timestamp
        city_df["ingested_at_utc"] = ingested_at

        city_dfs.append(city_df)

    # Combine all cities into one DataFrame
    df = pd.concat(city_dfs, ignore_index=True)

    # Convert time from text to timezone-aware UTC datetime
    df["time"] = pd.to_datetime(df["time"], utc=True)

    # Rename columns to include clear units
    df = df.rename(columns={
        "time": "observed_at_utc",
        "temperature_2m": "temperature_c",
        "apparent_temperature": "feels_like_c",
        "relative_humidity_2m": "humidity_pct",
        "precipitation": "precipitation_mm",
        "wind_speed_10m": "wind_speed_kmh",
    })

    # Derive UK local time from UTC
    df["observed_at_local"] = df["observed_at_utc"].dt.tz_convert("Europe/London")

    # Remove duplicate city and UTC timestamp combinations
    df = df.drop_duplicates(
        subset=["city", "observed_at_utc"],
        keep="last"
    )

    # Keep a consistent column order
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

    return df


# --------------------------------------------------
# 3. LOAD
# --------------------------------------------------

def load(df: pd.DataFrame, db_path: str | Path = DB_PATH) -> int:
    """Write weather records into SQLite and return rows written."""

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS weather_hourly (
        city TEXT NOT NULL,
        observed_at_utc TEXT NOT NULL,
        observed_at_local TEXT NOT NULL,
        temperature_c REAL,
        feels_like_c REAL,
        humidity_pct INTEGER,
        precipitation_mm REAL,
        wind_speed_kmh REAL,
        weather_code INTEGER,
        ingested_at_utc TEXT NOT NULL,
        PRIMARY KEY (city, observed_at_utc)
    );
    """

    insert_sql = """
    INSERT OR REPLACE INTO weather_hourly (
        city,
        observed_at_utc,
        observed_at_local,
        temperature_c,
        feels_like_c,
        humidity_pct,
        precipitation_mm,
        wind_speed_kmh,
        weather_code,
        ingested_at_utc
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

    # Prepare records for SQLite with timezone-aware timestamps
    records = []
    for row in df.itertuples(index=False):
        observed_at_utc = row.observed_at_utc.isoformat(timespec="seconds")
        observed_at_local = row.observed_at_local.isoformat(timespec="seconds")

        records.append((
            row.city,
            observed_at_utc,
            observed_at_local,
            row.temperature_c,
            row.feels_like_c,
            row.humidity_pct,
            row.precipitation_mm,
            row.wind_speed_kmh,
            row.weather_code,
            row.ingested_at_utc,
        ))
    # Connect to SQLite
    conn = sqlite3.connect(db_path)

    try:
        with conn:
            cursor = conn.cursor()

            # Create table if it does not already exist
            cursor.execute(create_table_sql)

            # Insert or replace existing records
            cursor.executemany(insert_sql, records)

    finally:
        conn.close()

    return len(records)


# --------------------------------------------------
# MAIN PIPELINE
# --------------------------------------------------

def main() -> None:
    """Run the complete Extract, Transform and Load pipeline."""

    logger.info("Starting WeatherFlow ETL pipeline...")

    raw, failed = extract()

    if raw:
        df = transform(raw)

        logger.info("Transformed records: %s", len(df))

        rows = load(df)

        logger.info("Loaded %s rows into weather.db", rows)

        # Verify the total number of records in the database
        connection = sqlite3.connect(DB_PATH)

        try:
            result = connection.execute(
                "SELECT COUNT(*) FROM weather_hourly"
            ).fetchone()

            logger.info("Total rows in database: %s", result[0])

        finally:
            connection.close()

    else:
        logger.warning(
            "No successful extractions. Skipping transformation and loading."
        )

    if failed:
        logger.error(
            "Run FAILED: no data for %s",
            ", ".join(failed),
        )

        sys.exit(1)

    logger.info("WeatherFlow ETL pipeline completed successfully!")

    sys.exit(0)


if __name__ == "__main__":
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                LOG_DIR / "pipeline.log",
                encoding="utf-8",
            ),
        ],
    )

    main()
