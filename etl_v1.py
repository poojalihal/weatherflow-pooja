
import sqlite3
from datetime import datetime, timezone

import pandas as pd
import requests

from extract import CITIES, fetch_city, save_raw


# --------------------------------------------------
# 1. EXTRACT
# --------------------------------------------------

def extract() -> list[tuple[str, dict]]:
    """Fetch weather data for each city, save raw JSON,
    and return (city, payload) pairs.
    """

    raw = []

    for city in CITIES:
        city_name = city["name"]

        try:
            print(f"Fetching weather for {city_name}...")

            payload = fetch_city(city)

            saved_file = save_raw(city_name, payload)

            raw.append((city_name, payload))

            hourly_records = len(payload["hourly"]["time"])

            print(
                f"Success: {city_name} - "
                f"{hourly_records} hourly records saved to {saved_file}"
            )

        except requests.RequestException as error:
            print(f"Error fetching {city_name}: {error}")
            print("Continuing with the next city...")

    if not raw:
        raise RuntimeError("Extraction failed for all cities. No data to load.")

    return raw


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

    # Convert time from text to datetime
    df["time"] = pd.to_datetime(df["time"])

    # Rename columns to include clear units
    df = df.rename(columns={
        "time": "observed_at",
        "temperature_2m": "temperature_c",
        "apparent_temperature": "feels_like_c",
        "relative_humidity_2m": "humidity_pct",
        "precipitation": "precipitation_mm",
        "wind_speed_10m": "wind_speed_kmh",
    })

    # Remove duplicate city and timestamp combinations
    df = df.drop_duplicates(
        subset=["city", "observed_at"],
        keep="last"
    )

    # Keep a consistent column order
    columns = [
        "city",
        "observed_at",
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

def load(df: pd.DataFrame, db_path: str = "weather.db") -> int:
    """Write weather records into SQLite and return rows written."""

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS weather_hourly (
        city TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        temperature_c REAL,
        feels_like_c REAL,
        humidity_pct INTEGER,
        precipitation_mm REAL,
        wind_speed_kmh REAL,
        weather_code INTEGER,
        ingested_at_utc TEXT NOT NULL,
        PRIMARY KEY (city, observed_at)
    );
    """

    insert_sql = """
    INSERT OR REPLACE INTO weather_hourly (
        city,
        observed_at,
        temperature_c,
        feels_like_c,
        humidity_pct,
        precipitation_mm,
        wind_speed_kmh,
        weather_code,
        ingested_at_utc
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

    # Prepare records for SQLite
    records = []

    for row in df.itertuples(index=False):

        observed_at = row.observed_at.strftime("%Y-%m-%dT%H:%M:%S")

        records.append((
            row.city,
            observed_at,
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

def main():
    """Run the complete Extract, Transform and Load pipeline."""

    print("\nStarting WeatherFlow ETL pipeline...\n")

    raw = extract()

    df = transform(raw)

    print(f"\nTransformed records: {len(df)}")

    rows = load(df)

    print(f"Loaded {rows} rows into weather.db")

    print("\nWeatherFlow ETL pipeline completed successfully!")


if __name__ == "__main__":
    main()

import sqlite3

connection = sqlite3.connect("weather.db")

result = connection.execute(
    "SELECT COUNT(*) FROM weather_hourly"
).fetchone()

print("Total rows in database:", result[0])

connection.close()