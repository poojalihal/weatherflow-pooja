"""PostgreSQL warehouse operations for WeatherFlow."""

import logging
import os
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from .load import (
    MEASUREMENT_COLUMNS,
    build_fact_rows,
    generate_date_rows,
)

logger = logging.getLogger(__name__)


def configure_database(config: dict) -> None:
    """Select the database backend for CLI execution."""

    from dotenv import load_dotenv

    project_root = Path(
        config["paths"]["schema_sql"]
    ).parent.parent

    load_dotenv(
        project_root / ".env",
        override=False,
    )

    config["database_backend"] = (
        "postgres"
        if os.getenv("DATABASE_URL")
        else "sqlite"
    )

    logger.info(
        "Database backend: %s",
        config["database_backend"],
    )


def connect_postgres():
    """Connect without exposing database credentials."""

    import psycopg

    url = os.getenv("DATABASE_URL")

    if not url:
        raise RuntimeError(
            "DATABASE_URL is required for PostgreSQL"
        )

    try:
        return psycopg.connect(
            url,
            connect_timeout=10,
        )

    except psycopg.Error:
        raise RuntimeError(
            "PostgreSQL connection failed. "
            "Check warehouse availability and credentials."
        ) from None


def load_dimensions_postgres(
    conn,
    config: dict,
) -> dict[str, int]:
    """Upsert dimensions within the active transaction."""

    city_rows = [
        (
            city["name"],
            city["country"],
            city["latitude"],
            city["longitude"],
        )
        for city in config["cities"]
    ]

    with conn.cursor() as cur:

        cur.executemany(
            """
            INSERT INTO dim_city (
                city_name,
                country,
                latitude,
                longitude
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (city_name) DO UPDATE SET
                country = EXCLUDED.country,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude
            """,
            city_rows,
        )

        date_config = config["dim_date"]

        date_rows = [
            (
                row[0],
                date.fromisoformat(row[1]),
                row[2],
                bool(row[3]),
                *row[4:],
            )
            for row in generate_date_rows(
                date_config["start"],
                date_config["end"],
            )
        ]

        cur.executemany(
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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (date_id) DO UPDATE SET
                full_date = EXCLUDED.full_date,
                day_of_week = EXCLUDED.day_of_week,
                is_weekend = EXCLUDED.is_weekend,
                day_of_month = EXCLUDED.day_of_month,
                month = EXCLUDED.month,
                year = EXCLUDED.year,
                quarter = EXCLUDED.quarter
            """,
            date_rows,
        )

        cur.execute(
            "SELECT city_id, city_name FROM dim_city"
        )

        return {
            city_name: city_id
            for city_id, city_name in cur.fetchall()
        }


FACT_COLUMNS = [
    "city_id",
    "date_id",
    "observed_at_utc",
    "observed_at_local",
    "hour_local",
    *MEASUREMENT_COLUMNS,
    "source",
    "ingested_at_utc",
]


def build_postgres_rows(
    df: pd.DataFrame,
    city_ids: dict[str, int],
) -> list[tuple]:
    """Reuse existing fact preparation and adapt types."""

    rows = []

    daylight_index = FACT_COLUMNS.index("is_daylight")

    for existing_row in build_fact_rows(df, city_ids):

        row = list(existing_row)

        row[2] = datetime.fromisoformat(row[2])

        row[3] = datetime.fromisoformat(
            row[3]
        ).replace(tzinfo=None)

        if row[daylight_index] is not None:
            row[daylight_index] = bool(
                row[daylight_index]
            )

        row[-1] = datetime.fromisoformat(row[-1])

        rows.append(tuple(row))

    return rows


def load_postgres(
    df: pd.DataFrame,
    config: dict,
) -> tuple[int, int, int]:
    """Atomically upsert dimensions and hourly facts.

    Returns:
        (total_upserted, new_count, updated_count)
    """

    schema_path = Path(
        config["paths"]["schema_sql"]
    ).with_name("schema_postgres.sql")

    schema = schema_path.read_text(
        encoding="utf-8"
    )

    key_columns = {
        "city_id",
        "observed_at_utc",
        "source",
    }

    placeholders = ", ".join(
        "%s" for _ in FACT_COLUMNS
    )

    updates = ", ".join(
        f"{column} = EXCLUDED.{column}"
        for column in FACT_COLUMNS
        if column not in key_columns
    )

    upsert_sql = f"""
        INSERT INTO fact_weather_hourly (
            {", ".join(FACT_COLUMNS)}
        )
        VALUES ({placeholders})
        ON CONFLICT (
            city_id,
            observed_at_utc,
            source
        )
        DO UPDATE SET {updates}
        RETURNING (OLD.city_id IS NULL) AS inserted
    """

    new_count = 0
    updated_count = 0

    try:

        with connect_postgres() as conn:

            with conn.transaction():

                conn.execute(
                    "SET LOCAL TIME ZONE 'UTC'"
                )

                conn.execute(schema)

                city_ids = load_dimensions_postgres(
                    conn,
                    config,
                )

                rows = build_postgres_rows(
                    df,
                    city_ids,
                )

                with conn.cursor() as cur:

                    for row in rows:

                        cur.execute(upsert_sql, row)

                        inserted = cur.fetchone()[0]

                        if inserted:
                            new_count += 1
                        else:
                            updated_count += 1

                    cur.execute(
                        "SELECT COUNT(*) "
                        "FROM fact_weather_hourly"
                    )

                    fact_count = cur.fetchone()[0]

                    cur.execute(
                        "SELECT COUNT(*) FROM dim_city"
                    )

                    city_count = cur.fetchone()[0]

                    cur.execute(
                        "SELECT COUNT(*) FROM dim_date"
                    )

                    date_count = cur.fetchone()[0]

        logger.info(
            "PostgreSQL dimensions: %s cities, %s dates",
            city_count,
            date_count,
        )

        logger.info(
            "PostgreSQL upsert: new=%s updated=%s total=%s",
            new_count,
            updated_count,
            len(rows),
        )

        logger.info(
            "Total fact rows in PostgreSQL: %s",
            fact_count,
        )

        return len(rows), new_count, updated_count

    except Exception:
        logger.error(
            "PostgreSQL load failed; transaction rolled back"
        )
        raise


def read_postgres_watermark(
    city_name: str,
    source: str,
    now,
) -> pd.Timestamp | None:
    """Return the latest eligible loaded observation."""

    now_utc = (
        pd.Timestamp(now)
        .tz_convert("UTC")
        .to_pydatetime()
    )

    with connect_postgres() as conn:

        with conn.cursor() as cur:

            cur.execute(
                "SELECT to_regclass('fact_weather_hourly')"
            )

            if cur.fetchone()[0] is None:
                return None

            cur.execute(
                """
                SELECT MAX(f.observed_at_utc)
                FROM fact_weather_hourly AS f
                JOIN dim_city AS c
                    ON c.city_id = f.city_id
                WHERE c.city_name = %s
                  AND f.source = %s
                  AND f.observed_at_utc <= %s
                """,
                (
                    city_name,
                    source,
                    now_utc,
                ),
            )

            value = cur.fetchone()[0]

    if value is None:
        return None

    return pd.Timestamp(value).tz_convert("UTC")
