"""Test dimensional loading and database integrity."""

import sqlite3
from contextlib import closing

import pandas as pd
import pytest

from weatherflow.config import load_config
from weatherflow.load import generate_date_rows, load
from weatherflow.storage import load_wmo_codes
from weatherflow.transform import transform


@pytest.fixture
def test_config(tmp_path) -> dict:
    """Use a temporary database with the project configuration."""
    config = load_config()
    config["paths"]["database"] = (
        tmp_path / "test_weather.db"
    )
    return config


@pytest.fixture
def sample_frame() -> pd.DataFrame:
    """Provide three transformed weather observations."""
    payload = {
        "latitude": 51.50853,
        "longitude": -0.12574,
        "hourly": {
            "time": [
                "2026-06-30T22:00",
                "2026-06-30T23:00",
                "2026-07-01T00:00",
            ],
            "temperature_2m": [10.0, 11.0, 12.0],
            "relative_humidity_2m": [80, 75, 70],
            "apparent_temperature": [9.0, 10.0, 11.0],
            "precipitation": [0.0, 0.0, 1.0],
            "wind_speed_10m": [3.6, 7.2, 10.8],
            "weather_code": [0, 2, 63],
            "is_day": [0, 0, 0],
        },
    }

    df = transform(
        [("London", payload)],
        load_wmo_codes(),
        "2026-07-01T12:00:00+00:00",
    )

    df["source"] = "open_meteo_forecast"

    return df


def test_schema_creates_all_tables(test_config):
    """Create the schema from scratch with keys and constraints."""
    schema = test_config["paths"]["schema_sql"].read_text(
        encoding="utf-8"
    )

    with closing(sqlite3.connect(":memory:")) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(schema)

        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table'"
            )
        }

        assert {
            "dim_city",
            "dim_date",
            "fact_weather_hourly",
        }.issubset(tables)

        pk_columns = [
            row[1]
            for row in sorted(
                conn.execute(
                    "PRAGMA table_info(fact_weather_hourly)"
                ),
                key=lambda row: row[5],
            )
            if row[5] > 0
        ]

        assert pk_columns == [
            "city_id",
            "observed_at_utc",
            "source",
        ]

        foreign_tables = {
            row[2]
            for row in conn.execute(
                "PRAGMA foreign_key_list(fact_weather_hourly)"
            )
        }

        assert foreign_tables == {
            "dim_city",
            "dim_date",
        }


def test_generate_date_rows():
    """Generate inclusive dates with correct weekend flags."""
    rows = generate_date_rows(
        "2026-11-27",
        "2026-11-29",
    )

    assert len(rows) == 3
    assert rows[0][0] == 20261127
    assert rows[0][2] == "Friday"
    assert rows[0][3] == 0

    assert rows[1][2] == "Saturday"
    assert rows[1][3] == 1

    assert rows[2][2] == "Sunday"
    assert rows[2][3] == 1


def test_load_is_idempotent_and_updates(
    sample_frame,
    test_config,
):
    """Reload observations without increasing their row count."""
    load(sample_frame, test_config)

    updated = sample_frame.copy()

    updated.loc[0, "temperature_c"] = 15.0
    updated.loc[0, "temperature_f"] = 59.0
    updated["ingested_at_utc"] = (
        "2026-07-01T13:00:00+00:00"
    )

    load(updated, test_config)
    load(updated, test_config)

    with closing(sqlite3.connect(
        test_config["paths"]["database"]
    )) as conn:

        count = conn.execute(
            "SELECT COUNT(*) FROM fact_weather_hourly"
        ).fetchone()[0]

        assert count == 3

        record = conn.execute(
            """
            SELECT temperature_c, temperature_f,
                   ingested_at_utc
            FROM fact_weather_hourly
            ORDER BY observed_at_utc
            LIMIT 1
            """
        ).fetchone()

        assert record == (
            15.0,
            59.0,
            "2026-07-01T13:00:00+00:00",
        )

        assert conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0] == "ok"

        assert conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchall() == []


def test_date_id_uses_london_calendar(
    sample_frame,
    test_config,
):
    """Use the UK local date rather than the UTC date."""
    load(sample_frame, test_config)

    with closing(sqlite3.connect(
        test_config["paths"]["database"]
    )) as conn:

        record = conn.execute(
            """
            SELECT date_id, hour_local
            FROM fact_weather_hourly
            WHERE observed_at_utc = ?
            """,
            ("2026-06-30T23:00:00+00:00",),
        ).fetchone()

        assert record == (20260701, 0)


def test_different_sources_are_distinct(
    sample_frame,
    test_config,
):
    """Keep forecast and archive rows separately."""
    load(sample_frame, test_config)

    archive = sample_frame.copy()
    archive["source"] = "open_meteo_archive"

    load(archive, test_config)

    with closing(sqlite3.connect(
        test_config["paths"]["database"]
    )) as conn:

        counts = dict(conn.execute(
            """
            SELECT source, COUNT(*)
            FROM fact_weather_hourly
            GROUP BY source
            """
        ))

        assert counts == {
            "open_meteo_forecast": 3,
            "open_meteo_archive": 3,
        }


def test_failed_load_rolls_back_all_changes(
    sample_frame,
    test_config,
):
    """Undo successful earlier writes when a later row fails."""
    load(sample_frame.iloc[:1], test_config)

    db_path = test_config["paths"]["database"]

    with closing(sqlite3.connect(db_path)) as conn:
        before = conn.execute(
            "SELECT * FROM fact_weather_hourly"
        ).fetchall()

        cities_before = conn.execute(
            "SELECT * FROM dim_city ORDER BY city_id"
        ).fetchall()

    bad_batch = sample_frame.copy()

    # Row 1 updates an existing observation.
    bad_batch.loc[0, "temperature_c"] = 99.0

    # Row 2 inserts a valid new observation.

    # Row 3 violates the database CHECK constraint.
    bad_batch.loc[2, "outdoor_work_risk"] = "invalid"

    # Attempt a dimension update in the same transaction.
    test_config["cities"][0]["country"] = "Test change"

    with pytest.raises(sqlite3.IntegrityError):
        load(bad_batch, test_config)

    with closing(sqlite3.connect(db_path)) as conn:
        after = conn.execute(
            "SELECT * FROM fact_weather_hourly"
        ).fetchall()

        cities_after = conn.execute(
            "SELECT * FROM dim_city ORDER BY city_id"
        ).fetchall()

        # Existing fact update and new fact insertion
        # must both be rolled back.
        assert after == before
        assert len(after) == 1

        # Dimension updates must also be rolled back.
        assert cities_after == cities_before

        assert conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchall() == []


def test_missing_date_dimension_rejects_load(
    sample_frame,
    test_config,
):
    """Reject observations whose dates lack dimension records."""
    test_config["dim_date"] = {
        "start": "2025-01-01",
        "end": "2025-01-02",
    }

    with pytest.raises(
        sqlite3.IntegrityError,
        match="FOREIGN KEY",
    ):
        load(sample_frame, test_config)


def test_real_london_fixture_load_is_idempotent(
    london_payload,
    test_config,
):
    """Transform and load the real fixture twice without duplicates."""

    df = transform(
        [("London", london_payload)],
        load_wmo_codes(),
        "2026-11-26T12:00:00+00:00",
    )

    df["source"] = "open_meteo_forecast"

    assert len(df) == 6

    db_path = test_config["paths"]["database"]

    # First load.
    assert load(df, test_config) == 6

    with closing(sqlite3.connect(db_path)) as conn:

        first_count = conn.execute(
            "SELECT COUNT(*) "
            "FROM fact_weather_hourly"
        ).fetchone()[0]

    # Second load of identical observation keys.
    assert load(df, test_config) == 6

    with closing(sqlite3.connect(db_path)) as conn:

        second_count = conn.execute(
            "SELECT COUNT(*) "
            "FROM fact_weather_hourly"
        ).fetchone()[0]

        duplicate_keys = conn.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT
                    city_id,
                    observed_at_utc,
                    source
                FROM fact_weather_hourly
                GROUP BY
                    city_id,
                    observed_at_utc,
                    source
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        city_name = conn.execute(
            """
            SELECT DISTINCT c.city_name
            FROM fact_weather_hourly AS f
            JOIN dim_city AS c
                ON f.city_id = c.city_id
            """
        ).fetchone()[0]

        integrity = conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        foreign_key_errors = conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

    assert first_count == 6
    assert second_count == 6
    assert duplicate_keys == 0
    assert city_name == "London"
    assert integrity == "ok"
    assert foreign_key_errors == []
