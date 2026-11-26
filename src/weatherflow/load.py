"""Transactional dimensional loading for WeatherFlow."""

import logging
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


MEASUREMENT_COLUMNS = [
    "temperature_c",
    "feels_like_c",
    "humidity_pct",
    "precipitation_mm",
    "wind_speed_kmh",
    "weather_code",
    "weather_description",
    "weather_category",
    "temperature_f",
    "wind_speed_ms",
    "beaufort_scale",
    "is_daylight",
    "outdoor_work_risk",
]


def generate_date_rows(
    start_date: str,
    end_date: str,
) -> list[tuple]:
    """Generate calendar dimension records for an inclusive range."""
    start = date.fromisoformat(str(start_date))
    end = date.fromisoformat(str(end_date))

    if start > end:
        raise ValueError(
            "Date dimension start must not be after end"
        )

    rows = []
    current = start

    while current <= end:
        rows.append((
            int(current.strftime("%Y%m%d")),
            current.isoformat(),
            current.strftime("%A"),
            int(current.weekday() >= 5),
            current.day,
            current.month,
            current.year,
            (current.month - 1) // 3 + 1,
        ))

        current += timedelta(days=1)

    return rows


def load_dimensions(
    conn: sqlite3.Connection,
    config: dict,
) -> dict[str, int]:
    """Upsert city and date dimensions within the active transaction."""

    city_rows = [
        (
            city["name"],
            city["country"],
            city["latitude"],
            city["longitude"],
        )
        for city in config["cities"]
    ]

    conn.executemany(
        """
        INSERT INTO dim_city (
            city_name,
            country,
            latitude,
            longitude
        )
        VALUES (?, ?, ?, ?)
        ON CONFLICT (city_name) DO UPDATE SET
            country = excluded.country,
            latitude = excluded.latitude,
            longitude = excluded.longitude
        """,
        city_rows,
    )

    date_config = config["dim_date"]

    date_rows = generate_date_rows(
        date_config["start"],
        date_config["end"],
    )

    conn.executemany(
        """
        INSERT INTO dim_date (
            date_id,
            full_date,
            day_of_week,
            is_weekend,
            day_of_month,
            month,
            year,
            quarter
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (date_id) DO UPDATE SET
            full_date = excluded.full_date,
            day_of_week = excluded.day_of_week,
            is_weekend = excluded.is_weekend,
            day_of_month = excluded.day_of_month,
            month = excluded.month,
            year = excluded.year,
            quarter = excluded.quarter
        """,
        date_rows,
    )

    city_ids = {
        city_name: city_id
        for city_id, city_name in conn.execute(
            "SELECT city_id, city_name FROM dim_city"
        )
    }

    return city_ids


def _sqlite_value(value: object) -> object:
    """Convert nullable pandas values to SQLite-compatible scalars."""
    if pd.isna(value):
        return None

    if hasattr(value, "item"):
        value = value.item()

    if isinstance(value, bool):
        return int(value)

    return value


def build_fact_rows(
    df: pd.DataFrame,
    city_ids: dict[str, int],
) -> list[tuple]:
    """Resolve dimension keys and prepare hourly fact records."""
    rows = []

    for row in df.itertuples(index=False):
        observed_utc = pd.Timestamp(
            row.observed_at_utc
        ).tz_convert("UTC")

        observed_local = observed_utc.tz_convert(
            "Europe/London"
        )

        date_id = int(
            observed_local.strftime("%Y%m%d")
        )

        measurements = tuple(
            _sqlite_value(getattr(row, column))
            for column in MEASUREMENT_COLUMNS
        )

        rows.append((
            city_ids[row.city],
            date_id,
            observed_utc.isoformat(timespec="seconds"),
            observed_local.isoformat(timespec="seconds"),
            observed_local.hour,
            *measurements,
            row.source,
            pd.to_datetime(
                row.ingested_at_utc,
                utc=True,
            ).isoformat(timespec="seconds"),
        ))

    return rows


def load(df: pd.DataFrame, config: dict) -> int:
    """Atomically upsert dimensions and hourly weather facts."""
    db_path = Path(config["paths"]["database"])
    schema_path = Path(config["paths"]["schema_sql"])

    schema = schema_path.read_text(encoding="utf-8")

    db_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    columns = [
        "city_id",
        "date_id",
        "observed_at_utc",
        "observed_at_local",
        "hour_local",
        *MEASUREMENT_COLUMNS,
        "source",
        "ingested_at_utc",
    ]

    key_columns = {
        "city_id",
        "observed_at_utc",
        "source",
    }

    placeholders = ", ".join(
        "?" for _ in columns
    )

    updates = ", ".join(
        f"{column} = excluded.{column}"
        for column in columns
        if column not in key_columns
    )

    upsert_sql = f"""
        INSERT INTO fact_weather_hourly (
            {", ".join(columns)}
        )
        VALUES ({placeholders})
        ON CONFLICT (
            city_id,
            observed_at_utc,
            source
        )
        DO UPDATE SET {updates}
    """

    conn = sqlite3.connect(db_path)

    try:
        conn.execute("PRAGMA foreign_keys = ON")

        with conn:
            # executescript can commit an existing transaction.
            # Begin the transaction INSIDE the script so all
            # schema, dimension and fact changes are atomic.
            conn.executescript(
                "BEGIN IMMEDIATE;\n" + schema
            )

            city_ids = load_dimensions(
                conn,
                config,
            )

            rows = build_fact_rows(
                df,
                city_ids,
            )

            conn.executemany(
                upsert_sql,
                rows,
            )

            fact_count = conn.execute(
                "SELECT COUNT(*) "
                "FROM fact_weather_hourly"
            ).fetchone()[0]

            city_count = conn.execute(
                "SELECT COUNT(*) FROM dim_city"
            ).fetchone()[0]

            date_count = conn.execute(
                "SELECT COUNT(*) FROM dim_date"
            ).fetchone()[0]

        logger.info(
            "Dimension counts: %s cities, %s dates",
            city_count,
            date_count,
        )

        logger.info(
            "Upserted %s hourly weather records",
            len(rows),
        )

        logger.info(
            "Total fact rows in database: %s",
            fact_count,
        )

        return len(rows)

    except Exception:
        logger.exception(
            "Database load failed; transaction rolled back"
        )
        raise

    finally:
        conn.close()
