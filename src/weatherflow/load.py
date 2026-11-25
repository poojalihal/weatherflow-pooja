"""Load standardised weather records into SQLite."""

import logging
import sqlite3
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def load(df: pd.DataFrame, db_path: Path) -> int:
    """Write weather records idempotently and return rows written."""
    db_path.parent.mkdir(parents=True, exist_ok=True)

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

    records = []

    for row in df.itertuples(index=False):
        records.append((
            row.city,
            row.observed_at_utc.isoformat(timespec="seconds"),
            row.observed_at_local.isoformat(timespec="seconds"),
            row.temperature_c,
            row.feels_like_c,
            row.humidity_pct,
            row.precipitation_mm,
            row.wind_speed_kmh,
            row.weather_code,
            row.ingested_at_utc,
        ))

    conn = sqlite3.connect(db_path)

    try:
        with conn:
            conn.execute(create_table_sql)
            conn.executemany(insert_sql, records)

        total = conn.execute(
            "SELECT COUNT(*) FROM weather_hourly"
        ).fetchone()[0]

        logger.info("Loaded %s rows into %s", len(records), db_path)
        logger.info("Total rows in database: %s", total)

    finally:
        conn.close()

    return len(records)
