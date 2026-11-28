"""Generate and deduplicate actionable weather risk alerts."""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .postgres import connect_postgres

logger = logging.getLogger(__name__)

UK_TZ = ZoneInfo("Europe/London")

FORECAST_SOURCES = [
    "open_meteo_forecast",
    "weatherapi_forecast",
]

ALERT_LOCK = 382601


def uk_time(value):
    """Format UTC timestamps in UK local time."""

    return value.astimezone(UK_TZ).strftime(
        "%d %b %Y %H:%M %Z"
    )


def risk_reasons(beaufort, precipitation, category):
    """Identify reasons for a high-risk weather classification."""

    reasons = set()

    if beaufort is not None and beaufort >= 7:
        reasons.add("strong wind")

    if precipitation is not None and precipitation >= 4:
        reasons.add("heavy precipitation")

    category = str(category).lower()

    if "snow" in category:
        reasons.add("snow")

    if "storm" in category:
        reasons.add("storm")

    return reasons or {"high weather risk"}


def alert_key(city, hour):
    """Build a stable UTC alert deduplication key."""

    hour = hour.astimezone(timezone.utc)

    return f"risk:{city}:{hour.isoformat()}"


def initialise_alerts(conn, schema_file):
    """Serialise alert writes and initialise the tables."""

    conn.execute(
        "SELECT pg_advisory_xact_lock(%s)",
        (ALERT_LOCK,),
    )

    conn.execute(
        Path(schema_file).read_text(
            encoding="utf-8"
        )
    )


def record_risk_alerts(conn, rows):
    """Store one alert per consecutive unnotified risk period."""

    grouped = defaultdict(set)

    # Combine high-risk observations from multiple sources.
    for city, hour, beaufort, rain, category in rows:

        hour = hour.astimezone(timezone.utc)

        grouped[(city, hour)].update(
            risk_reasons(beaufort, rain, category)
        )

    if not grouped:
        return []

    keys = [
        alert_key(city, hour)
        for city, hour in grouped
    ]

    existing = {
        row[0]
        for row in conn.execute(
            """
            SELECT alert_key
            FROM alerts_sent
            WHERE alert_key = ANY(%s)
            """,
            (keys,),
        ).fetchall()
    }

    pending = defaultdict(list)

    for (city, hour), reasons in sorted(
        grouped.items()
    ):

        key = alert_key(city, hour)

        if key not in existing:
            pending[city].append(
                (hour, reasons)
            )

    messages = []

    for city, items in pending.items():

        periods = []

        for hour, reasons in items:

            if (
                not periods
                or hour != periods[-1][-1][0]
                + timedelta(hours=1)
            ):
                periods.append([])

            periods[-1].append(
                (hour, reasons)
            )

        for period in periods:

            start = period[0][0]

            end = (
                period[-1][0]
                + timedelta(hours=1)
            )

            reasons = sorted(
                set().union(
                    *(item[1] for item in period)
                )
            )

            message = (
                f"{city}: HIGH outdoor work risk "
                f"from {uk_time(start)} "
                f"until {uk_time(end)}; "
                f"reason: {', '.join(reasons)}."
            )

            alert_id = conn.execute(
                """
                INSERT INTO alerts (
                    alert_type,
                    city_name,
                    period_start_utc,
                    period_end_utc,
                    message
                )
                VALUES (
                    'weather_risk', %s, %s, %s, %s
                )
                RETURNING alert_id
                """,
                (city, start, end, message),
            ).fetchone()[0]

            with conn.cursor() as cursor:

                cursor.executemany(
                    """
                    INSERT INTO alerts_sent (
                        alert_key,
                        alert_id
                    )
                    VALUES (%s, %s)
                    """,
                    [
                        (
                            alert_key(city, hour),
                            alert_id,
                        )
                        for hour, _ in period
                    ],
                )

            messages.append(message)

    return messages


def run_alerts(config, now=None):
    """Generate risk alerts for the next 12 hourly slots."""

    if config.get("database_backend") != "postgres":
        logger.error(
            "Alerts require a PostgreSQL warehouse"
        )
        return 1

    now = now or datetime.now(timezone.utc)

    start = now.astimezone(
        timezone.utc
    ).replace(
        minute=0,
        second=0,
        microsecond=0,
    )

    end = start + timedelta(hours=12)

    schema_file = Path(
        config["paths"]["schema_sql"]
    ).with_name("schema_alerts.sql")

    with connect_postgres() as conn:

        with conn.transaction():

            initialise_alerts(
                conn, schema_file
            )

            rows = conn.execute(
                """
                SELECT
                    c.city_name,
                    f.observed_at_utc,
                    f.beaufort_scale,
                    f.precipitation_mm,
                    f.weather_category
                FROM fact_weather_hourly f
                JOIN dim_city c
                    ON c.city_id = f.city_id
                WHERE f.observed_at_utc >= %s
                  AND f.observed_at_utc < %s
                  AND f.outdoor_work_risk = 'high'
                  AND f.source = ANY(%s)
                ORDER BY c.city_name,
                         f.observed_at_utc
                """,
                (start, end, FORECAST_SOURCES),
            ).fetchall()

            messages = record_risk_alerts(
                conn, rows
            )

    # Log only after the database transaction succeeds.
    for message in messages:
        logger.warning(
            "WEATHER RISK ALERT | %s",
            message,
        )

    logger.info(
        "Alert summary: high_risk_rows=%s new_alerts=%s",
        len(rows),
        len(messages),
    )

    return 0
