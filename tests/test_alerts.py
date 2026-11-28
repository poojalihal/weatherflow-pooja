"""WeatherFlow alert unit and PostgreSQL integration tests."""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from weatherflow.alerts import (
    alert_key,
    initialise_alerts,
    record_risk_alerts,
    risk_reasons,
)


SCHEMA_FILE = (
    Path(__file__).resolve().parents[1]
    / "sql"
    / "schema_alerts.sql"
)


def test_risk_reasons():

    assert risk_reasons(8, 0, "clear") == {
        "strong wind"
    }

    assert risk_reasons(2, 5, "rain") == {
        "heavy precipitation"
    }

    assert risk_reasons(2, 0, "snow") == {
        "snow"
    }

    assert risk_reasons(2, 0, "storm") == {
        "storm"
    }

    assert risk_reasons(None, None, "unknown") == {
        "high weather risk"
    }


def test_alert_key_uses_utc():

    utc_hour = datetime(
        2026, 11, 28, 9,
        tzinfo=timezone.utc,
    )

    other_timezone = timezone(
        timedelta(hours=2)
    )

    assert alert_key(
        "London", utc_hour
    ) == alert_key(
        "London",
        utc_hour.astimezone(other_timezone),
    )


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL not configured",
)
def test_alert_periods_and_deduplication():

    schema = "test_alerts_" + uuid4().hex

    conn = psycopg.connect(
        os.environ["DATABASE_URL"],
        autocommit=True,
        connect_timeout=5,
    )

    try:

        conn.execute(
            sql.SQL("CREATE SCHEMA {}").format(
                sql.Identifier(schema)
            )
        )

        conn.execute(
            sql.SQL("SET search_path TO {}").format(
                sql.Identifier(schema)
            )
        )

        start = datetime(
            2026, 11, 28, 9,
            tzinfo=timezone.utc,
        )

        rows = [
            ("Edinburgh", start, 8, 0, "clear"),
            (
                "Edinburgh",
                start + timedelta(hours=1),
                8, 0, "clear",
            ),
            (
                "Edinburgh",
                start + timedelta(hours=2),
                3, 5, "rain",
            ),

            # Second source for the same observation.
            ("Edinburgh", start, 8, 0, "storm"),

            # Separate city and risk period.
            ("Cardiff", start, 7, 0, "clear"),
        ]

        with conn.transaction():

            initialise_alerts(
                conn, SCHEMA_FILE
            )

            first = record_risk_alerts(
                conn, rows
            )

        assert len(first) == 2

        assert any(
            "Edinburgh" in message
            and "strong wind" in message
            and "storm" in message
            and "heavy precipitation" in message
            for message in first
        )

        with conn.transaction():

            initialise_alerts(
                conn, SCHEMA_FILE
            )

            second = record_risk_alerts(
                conn, rows
            )

        assert second == []

        assert conn.execute(
            "SELECT COUNT(*) FROM alerts"
        ).fetchone()[0] == 2

        assert conn.execute(
            "SELECT COUNT(*) FROM alerts_sent"
        ).fetchone()[0] == 4

        # An extended risk period should notify
        # only the newly identified hour.
        rows.append((
            "Edinburgh",
            start + timedelta(hours=3),
            8, 0, "clear",
        ))

        with conn.transaction():

            initialise_alerts(
                conn, SCHEMA_FILE
            )

            extended = record_risk_alerts(
                conn, rows
            )

        assert len(extended) == 1

        assert conn.execute(
            "SELECT COUNT(*) FROM alerts_sent"
        ).fetchone()[0] == 5

    finally:

        conn.execute(
            sql.SQL(
                "DROP SCHEMA IF EXISTS {} CASCADE"
            ).format(
                sql.Identifier(schema)
            )
        )

        conn.close()
