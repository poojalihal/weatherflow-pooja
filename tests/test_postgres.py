"""PostgreSQL integration tests."""

import json
import os
from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest

from weatherflow.config import load_config
from weatherflow.postgres import (
    load_postgres,
    read_postgres_watermark,
)
from weatherflow.storage import load_wmo_codes
from weatherflow.transform import transform


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL requires DATABASE_URL",
)

FORECAST = "open_meteo_forecast"
ARCHIVE = "open_meteo_archive"


@pytest.fixture
def postgres_warehouse(monkeypatch):
    """Create an isolated PostgreSQL test schema."""

    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo

    base_url = os.environ["DATABASE_URL"]
    schema = f"test_weatherflow_{uuid4().hex}"

    with psycopg.connect(
        base_url, autocommit=True
    ) as conn:

        conn.execute(
            sql.SQL("CREATE SCHEMA {}").format(
                sql.Identifier(schema)
            )
        )

    try:
        test_url = make_conninfo(
            base_url,
            options=f"-c search_path={schema}",
        )

        monkeypatch.setenv(
            "DATABASE_URL", test_url
        )

        config = load_config()

        config["cities"] = [
            city for city in config["cities"]
            if city["name"] == "London"
        ]

        config["database_backend"] = "postgres"

        yield config, test_url

    finally:
        with psycopg.connect(
            base_url, autocommit=True
        ) as conn:

            conn.execute(
                sql.SQL(
                    "DROP SCHEMA {} CASCADE"
                ).format(sql.Identifier(schema))
            )


@pytest.fixture
def weather_records():
    """Reuse the existing London weather fixture."""

    fixture = (
        Path(__file__).parent
        / "fixtures"
        / "open_meteo_london.json"
    )

    payload = json.loads(
        fixture.read_text(encoding="utf-8")
    )

    df = transform(
        [("London", payload)],
        load_wmo_codes(),
        ingested_at_utc="2026-11-26T12:00:00+00:00",
    )

    df["source"] = FORECAST

    return df


def count_facts(url):
    import psycopg

    with psycopg.connect(url) as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM fact_weather_hourly"
        ).fetchone()[0]


def test_postgres_idempotent_upsert(
    postgres_warehouse,
    weather_records,
):
    config, url = postgres_warehouse

    expected = len(weather_records)

    first = load_postgres(weather_records, config)
    assert first == (expected, expected, 0)
    assert count_facts(url) == expected

    second = load_postgres(weather_records, config)
    assert second == (expected, 0, expected)
    assert count_facts(url) == expected

    third = load_postgres(weather_records, config)
    assert third == (expected, 0, expected)
    assert count_facts(url) == expected


def test_postgres_atomic_rollback(
    postgres_warehouse,
    weather_records,
):
    import psycopg

    config, url = postgres_warehouse

    load_postgres(weather_records, config)

    before = count_facts(url)

    original_country = config["cities"][0]["country"]

    config["cities"][0]["country"] = "Rollback probe"

    bad = weather_records.copy()

    bad["source"] = "rollback_probe"

    # Earlier rows are valid; the final row must fail.
    bad.loc[
        bad.index[-1], "outdoor_work_risk"
    ] = "invalid_risk"

    with pytest.raises(
        psycopg.errors.CheckViolation
    ):
        load_postgres(bad, config)

    assert count_facts(url) == before

    with psycopg.connect(url) as conn:

        probe_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM fact_weather_hourly
            WHERE source = %s
            """,
            ("rollback_probe",),
        ).fetchone()[0]

        country = conn.execute(
            """
            SELECT country
            FROM dim_city
            WHERE city_name = %s
            """,
            ("London",),
        ).fetchone()[0]

    assert probe_count == 0
    assert country == original_country


def test_postgres_watermark(
    postgres_warehouse,
    weather_records,
):
    config, _ = postgres_warehouse

    ordered = weather_records.sort_values(
        "observed_at_utc"
    ).reset_index(drop=True)

    hours = ordered["observed_at_utc"]

    now = pd.Timestamp(hours.iloc[-1])

    assert read_postgres_watermark(
        "London", FORECAST, now
    ) is None

    load_postgres(
        ordered.iloc[:3].copy(), config
    )

    archive = ordered.copy()
    archive["source"] = ARCHIVE

    load_postgres(archive, config)

    # Archive data must not change the forecast watermark.
    assert read_postgres_watermark(
        "London", FORECAST, now
    ) == pd.Timestamp(hours.iloc[2])

    # Future forecast observations must be excluded.
    earlier_now = (
        pd.Timestamp(hours.iloc[1])
        + pd.Timedelta(minutes=30)
    )

    assert read_postgres_watermark(
        "London", FORECAST, earlier_now
    ) == pd.Timestamp(hours.iloc[1])

    assert read_postgres_watermark(
        "Cardiff", FORECAST, now
    ) is None
