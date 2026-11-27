"""Plan and extract historical and incremental weather windows."""

import logging
import sqlite3
import time

from contextlib import closing
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

from .extract import fetch_window, save_raw

logger = logging.getLogger(__name__)

FORECAST_SOURCE = "open_meteo_forecast"
ARCHIVE_SOURCE = "open_meteo_archive"


@dataclass(frozen=True)
class RequestWindow:
    """An inclusive hourly request window for one city."""

    city: dict
    start: pd.Timestamp
    end: pd.Timestamp


def resolve_backfill_dates(
    config: dict,
    now,
    *,
    days: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> tuple[date, date]:
    """Resolve and validate inclusive historical dates."""

    settings = config["backfill"]

    today = pd.Timestamp(now).tz_convert("UTC").date()

    latest_date = today - timedelta(
        days=settings["archive_lag_days"]
    )

    if start_date is not None:
        if end_date is None or days is not None:
            raise ValueError(
                "Use --start-date and --end-date together, "
                "without --days."
            )

        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

    else:
        number_of_days = (
            settings["default_days"]
            if days is None
            else days
        )

        if number_of_days < 1:
            raise ValueError("Backfill days must be positive.")

        end = (
            date.fromisoformat(end_date)
            if end_date is not None
            else latest_date
        )

        start = end - timedelta(
            days=number_of_days - 1
        )

    if start > end:
        raise ValueError(
            "Start date must not be after end date."
        )

    if end > latest_date:
        raise ValueError(
            f"Archive end date must be on or before "
            f"{latest_date} because of the configured "
            "historical data availability lag."
        )

    return start, end


def date_chunks(
    start: date,
    end: date,
    chunk_days: int = 7,
) -> list[tuple[date, date]]:
    """Split inclusive dates into non-overlapping chunks."""

    if chunk_days < 1 or start > end:
        raise ValueError("Invalid historical chunk range.")

    chunks = []
    current = start

    while current <= end:

        chunk_end = min(
            current + timedelta(days=chunk_days - 1),
            end,
        )

        chunks.append((current, chunk_end))

        current = chunk_end + timedelta(days=1)

    return chunks


def plan_backfill(
    config: dict,
    start: date,
    end: date,
) -> list[RequestWindow]:
    """Create historical request windows for every city."""

    chunks = date_chunks(
        start,
        end,
        config["backfill"]["chunk_days"],
    )

    return [
        RequestWindow(
            city=city,
            start=pd.Timestamp(first, tz="UTC"),
            end=(
                pd.Timestamp(last, tz="UTC")
                + pd.Timedelta(hours=23)
            ),
        )
        for city in config["cities"]
        for first, last in chunks
    ]


def _fact_table_exists(conn) -> bool:
    """Check whether the dimensional fact table exists."""

    return conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'fact_weather_hourly'
        """
    ).fetchone() is not None


def read_watermark(
    db_path: Path,
    city_name: str,
    source: str,
    now,
) -> pd.Timestamp | None:
    """Find the latest loaded hour that has already happened."""

    db_path = Path(db_path)

    if not db_path.is_file():
        return None

    now_utc = (
        pd.Timestamp(now)
        .tz_convert("UTC")
        .isoformat(timespec="seconds")
    )

    with closing(sqlite3.connect(db_path)) as conn:

        if not _fact_table_exists(conn):
            return None

        value = conn.execute(
            """
            SELECT MAX(f.observed_at_utc)
            FROM fact_weather_hourly AS f
            JOIN dim_city AS c
                ON c.city_id = f.city_id
            WHERE c.city_name = ?
              AND f.source = ?
              AND f.observed_at_utc <= ?
            """,
            (city_name, source, now_utc),
        ).fetchone()[0]

    if value is None:
        return None

    return pd.Timestamp(value).tz_convert("UTC")


def plan_incremental(
    config: dict,
    now,
) -> list[RequestWindow]:
    """Plan a separate incremental request for each city."""

    now_utc = pd.Timestamp(now).tz_convert("UTC")
    today = now_utc.normalize()

    forecast_days = config["api"]["forecast_days"]

    if forecast_days < 1:
        raise ValueError(
            "forecast_days must be at least one."
        )

    end = (
        today
        + pd.Timedelta(days=forecast_days)
        - pd.Timedelta(hours=1)
    )

    settings = config["incremental"]

    windows = []

    for city in config["cities"]:

        watermark = read_watermark(
            config["paths"]["database"],
            city["name"],
            FORECAST_SOURCE,
            now_utc,
        )

        if watermark is None:

            start = today - pd.Timedelta(
                days=settings["fallback_past_days"]
            )

            logger.info(
                "%s: no forecast watermark; "
                "fallback past_days=%s",
                city["name"],
                settings["fallback_past_days"],
            )

        else:

            start = watermark.floor("h") - pd.Timedelta(
                hours=settings["overlap_hours"]
            )

            logger.info(
                "%s: watermark=%s; overlap=%s hours",
                city["name"],
                watermark.isoformat(),
                settings["overlap_hours"],
            )

        windows.append(
            RequestWindow(
                city=city,
                start=start,
                end=end,
            )
        )

    return windows


def expected_window_hours(
    windows: list[RequestWindow],
) -> dict[str, pd.DatetimeIndex]:
    """Build expected hours from planned requests, not API data."""

    expected = {}

    for window in windows:

        city = window.city["name"]

        hours = pd.date_range(
            window.start,
            window.end,
            freq="h",
        )

        if city in expected:

            expected[city] = expected[city].union(hours)

        else:

            expected[city] = hours

    return expected


def extract_windows(
    config: dict,
    windows: list[RequestWindow],
    *,
    archive: bool,
) -> tuple[list[tuple[str, dict]], list[str]]:
    """Fetch planned intervals and land each raw response."""

    raw = []
    failed = []

    mode = "archive" if archive else "forecast"

    for index, window in enumerate(windows):

        name = window.city["name"]

        logger.info(
            "%s request: city=%s start=%s end=%s",
            mode,
            name,
            window.start.isoformat(),
            window.end.isoformat(),
        )

        try:

            payload = fetch_window(
                window.city,
                config["api"],
                window.start,
                window.end,
                archive=archive,
            )

            raw_path = save_raw(
                f"{name}_{mode}",
                payload,
                config["paths"]["raw_dir"],
            )

            raw.append((name, payload))

            logger.info(
                "%s: saved %s hourly records to %s",
                name,
                len(payload["hourly"]["time"]),
                raw_path,
            )

        except requests.RequestException as error:

            failure = (
                f"{name} "
                f"{window.start.isoformat()} "
                f"to {window.end.isoformat()}"
            )

            failed.append(failure)

            logger.error(
                "Request failed: %s: %s",
                failure,
                error,
            )

        if archive and index < len(windows) - 1:

            time.sleep(
                config["backfill"][
                    "request_delay_seconds"
                ]
            )

    logger.info(
        "%s extraction summary: %s successful, "
        "%s failed requests",
        mode,
        len(raw),
        len(failed),
    )

    return raw, failed


def count_load_changes(
    df: pd.DataFrame,
    db_path: Path,
) -> tuple[int, int]:
    """Count new and already existing incoming fact keys."""

    if df.empty:
        return 0, 0

    db_path = Path(db_path)

    if not db_path.is_file():
        return len(df), 0

    timestamps = pd.to_datetime(
        df["observed_at_utc"],
        utc=True,
    )

    start = timestamps.min().isoformat(timespec="seconds")
    end = timestamps.max().isoformat(timespec="seconds")

    with closing(sqlite3.connect(db_path)) as conn:

        if not _fact_table_exists(conn):
            return len(df), 0

        existing = set(
            conn.execute(
                """
                SELECT
                    c.city_name,
                    f.observed_at_utc,
                    f.source
                FROM fact_weather_hourly AS f
                JOIN dim_city AS c
                    ON c.city_id = f.city_id
                WHERE f.observed_at_utc
                      BETWEEN ? AND ?
                """,
                (start, end),
            ).fetchall()
        )

    updated = 0

    for row in df.itertuples(index=False):

        key = (
            row.city,
            pd.Timestamp(row.observed_at_utc)
            .tz_convert("UTC")
            .isoformat(timespec="seconds"),
            row.source,
        )

        if key in existing:
            updated += 1

    return len(df) - updated, updated
