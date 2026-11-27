"""Test backfill planning, watermarks and incremental loading."""

import logging
import sqlite3

from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock

import pandas as pd
import pytest
import requests

from weatherflow.config import load_config
from weatherflow.extract import fetch_window
from weatherflow.load import load
from weatherflow.pipeline import backfill, run
from weatherflow.storage import load_wmo_codes
from weatherflow.transform import transform
from weatherflow.windows import (
    ARCHIVE_SOURCE,
    FORECAST_SOURCE,
    date_chunks,
    expected_window_hours,
    plan_backfill,
    plan_incremental,
    read_watermark,
    resolve_backfill_dates,
)


NOW = datetime(
    2026, 11, 26, 12, 30,
    tzinfo=timezone.utc,
)


@pytest.fixture
def window_config(tmp_path):
    """Use isolated storage and one configured city."""

    config = load_config()

    config["cities"] = [
        city
        for city in config["cities"]
        if city["name"] == "London"
    ]

    config["paths"].update({
        "database": tmp_path / "weather.db",
        "raw_dir": tmp_path / "raw",
        "processed_dir": tmp_path / "processed",
        "quarantine_dir": tmp_path / "quarantine",
        "dq_reports_dir": tmp_path / "dq_reports",
        "log_file": tmp_path / "pipeline.log",
    })

    config["backfill"]["request_delay_seconds"] = 0

    return config


def make_payload(hours):
    """Build deterministic weather measurements for test hours."""

    n = len(hours)

    return {
        "latitude": 51.50853,
        "longitude": -0.12574,
        "hourly": {
            "time": [
                hour.strftime("%Y-%m-%dT%H:%M")
                for hour in hours
            ],
            "temperature_2m": [10.0] * n,
            "relative_humidity_2m": [80] * n,
            "apparent_temperature": [9.0] * n,
            "precipitation": [0.0] * n,
            "wind_speed_10m": [10.0] * n,
            "weather_code": [0] * n,
            "is_day": [
                int(8 <= hour.hour < 16)
                for hour in hours
            ],
        },
    }


def fake_fetch(
    city,
    api,
    start,
    end,
    *,
    archive=False,
):
    """Return exactly the requested hours without network access."""

    hours = pd.date_range(
        start,
        end,
        freq="h",
    )

    return make_payload(hours)


def seed_facts(config, hours, source):
    """Insert test observations through the real loader."""

    timestamps = pd.to_datetime(
        hours,
        utc=True,
    )

    df = transform(
        [("London", make_payload(timestamps))],
        load_wmo_codes(),
        NOW.isoformat(),
    )

    df["source"] = source

    load(df, config)


def fact_count(config, source):
    """Count fact records for a single source."""

    with closing(sqlite3.connect(
        config["paths"]["database"]
    )) as conn:

        return conn.execute(
            """
            SELECT COUNT(*)
            FROM fact_weather_hourly
            WHERE source = ?
            """,
            (source,),
        ).fetchone()[0]


def test_default_backfill_dates(window_config):
    """Thirty days end five days before the current UTC date."""

    start, end = resolve_backfill_dates(
        window_config,
        NOW,
        days=30,
    )

    assert start == date(2026, 10, 23)
    assert end == date(2026, 11, 21)
    assert (end - start).days + 1 == 30


def test_seven_day_chunks_cover_all_hours(window_config):
    """Five non-overlapping chunks cover exactly thirty days."""

    start = date(2026, 10, 23)
    end = date(2026, 11, 21)

    chunks = date_chunks(start, end, 7)

    lengths = [
        (last - first).days + 1
        for first, last in chunks
    ]

    assert lengths == [7, 7, 7, 7, 2]

    for previous, following in zip(
        chunks,
        chunks[1:],
    ):

        assert (
            previous[1] + timedelta(days=1)
            == following[0]
        )

    windows = plan_backfill(
        window_config,
        start,
        end,
    )

    expected = expected_window_hours(windows)

    assert len(windows) == 5
    assert len(expected["London"]) == 720


def test_missing_database_has_no_watermark(
    window_config,
):
    """A new database must return no existing watermark."""

    result = read_watermark(
        window_config["paths"]["database"],
        "London",
        FORECAST_SOURCE,
        NOW,
    )

    assert result is None


def test_watermark_excludes_future_hours_and_other_sources(
    window_config,
):
    """Forecast hours in the future must not advance the mark."""

    seed_facts(
        window_config,
        [
            "2026-11-26T09:00:00Z",
            "2026-11-26T10:00:00Z",
            "2026-11-26T15:00:00Z",
        ],
        FORECAST_SOURCE,
    )

    seed_facts(
        window_config,
        ["2026-11-26T12:00:00Z"],
        ARCHIVE_SOURCE,
    )

    result = read_watermark(
        window_config["paths"]["database"],
        "London",
        FORECAST_SOURCE,
        NOW,
    )

    assert result == pd.Timestamp(
        "2026-11-26T10:00:00Z"
    )

    missing_city = read_watermark(
        window_config["paths"]["database"],
        "Cardiff",
        FORECAST_SOURCE,
        NOW,
    )

    assert missing_city is None


def test_incremental_overlap_and_city_fallback(
    window_config,
):
    """Use two-hour overlap for an existing city and fallback for another."""

    seed_facts(
        window_config,
        [
            "2026-11-26T10:00:00Z",
            "2026-11-26T12:00:00Z",
            "2026-11-26T18:00:00Z",
        ],
        FORECAST_SOURCE,
    )

    full_config = load_config()

    cardiff = next(
        city
        for city in full_config["cities"]
        if city["name"] == "Cardiff"
    )

    window_config["cities"].append(cardiff)

    windows = {
        window.city["name"]: window
        for window in plan_incremental(
            window_config,
            NOW,
        )
    }

    assert windows["London"].start == pd.Timestamp(
        "2026-11-26T10:00:00Z"
    )

    assert windows["London"].end == pd.Timestamp(
        "2026-11-26T23:00:00Z"
    )

    assert windows["Cardiff"].start == pd.Timestamp(
        "2026-11-25T00:00:00Z"
    )

    expected = expected_window_hours(
        list(windows.values())
    )

    assert len(expected["London"]) == 14
    assert len(expected["Cardiff"]) == 48


@pytest.mark.parametrize(
    "archive",
    [True, False],
)
def test_fetch_window_uses_correct_api_parameters(
    window_config,
    london_payload,
    monkeypatch,
    archive,
):
    """Use date parameters for archives and hour parameters for forecasts."""

    response = Mock()
    response.json.return_value = london_payload

    mocked_get = Mock(return_value=response)

    monkeypatch.setattr(
        "weatherflow.extract.requests.get",
        mocked_get,
    )

    start = pd.Timestamp(
        "2026-11-20T00:00:00Z"
    )

    end = pd.Timestamp(
        "2026-11-20T23:00:00Z"
    )

    result = fetch_window(
        window_config["cities"][0],
        window_config["api"],
        start,
        end,
        archive=archive,
    )

    assert result == london_payload

    args = mocked_get.call_args
    params = args.kwargs["params"]

    assert params["timezone"] == "UTC"
    assert "past_days" not in params
    assert "forecast_days" not in params

    if archive:

        assert args.args[0] == (
            window_config["api"]["archive_url"]
        )

        assert params["start_date"] == "2026-11-20"
        assert params["end_date"] == "2026-11-20"

    else:

        assert args.args[0] == (
            window_config["api"]["forecast_url"]
        )

        assert params["start_hour"] == "2026-11-20T00:00"
        assert params["end_hour"] == "2026-11-20T23:00"


def test_backfill_is_idempotent(
    window_config,
    monkeypatch,
    caplog,
):
    """Load an eight-day archive interval twice using real SQLite."""

    caplog.set_level(logging.INFO)

    clock = Mock()

    clock.now.side_effect = [
        NOW,
        NOW + timedelta(seconds=1),
    ]

    monkeypatch.setattr(
        "weatherflow.pipeline.datetime",
        clock,
    )

    mocked_fetch = Mock(
        side_effect=fake_fetch
    )

    monkeypatch.setattr(
        "weatherflow.windows.fetch_window",
        mocked_fetch,
    )

    assert backfill(
        window_config,
        days=8,
    ) == 0

    assert fact_count(
        window_config,
        ARCHIVE_SOURCE,
    ) == 192

    assert "new=192 updated=0" in caplog.text

    assert backfill(
        window_config,
        days=8,
    ) == 0

    assert fact_count(
        window_config,
        ARCHIVE_SOURCE,
    ) == 192

    assert "new=0 updated=192" in caplog.text

    assert mocked_fetch.call_count == 4

    assert len(list(
        window_config["paths"]["raw_dir"]
        .rglob("*.json")
    )) == 4

    assert len(list(
        window_config["paths"]["dq_reports_dir"]
        .glob("*.md")
    )) == 2


def test_failed_archive_chunk_blocks_load(
    window_config,
    monkeypatch,
):
    """An incomplete archive batch must not reach the database."""

    clock = Mock()
    clock.now.return_value = NOW

    monkeypatch.setattr(
        "weatherflow.pipeline.datetime",
        clock,
    )

    successful = make_payload(
        pd.date_range(
            "2026-11-14T00:00:00Z",
            periods=168,
            freq="h",
        )
    )

    mocked_fetch = Mock(
        side_effect=[
            successful,
            requests.ConnectionError(
                "Simulated archive failure"
            ),
        ]
    )

    monkeypatch.setattr(
        "weatherflow.windows.fetch_window",
        mocked_fetch,
    )

    assert backfill(
        window_config,
        days=8,
    ) == 1

    assert not window_config[
        "paths"
    ]["database"].exists()

    reports = list(
        window_config["paths"]["dq_reports_dir"]
        .glob("*.md")
    )

    assert len(reports) == 1

    report = reports[0].read_text(
        encoding="utf-8"
    )

    assert "Run status: FAILED" in report
    assert "expected_hourly_coverage" in report
    assert "| Loaded records | 0 |" in report


def test_incremental_pipeline_refreshes_forecasts(
    window_config,
    monkeypatch,
    caplog,
):
    """Fetch only the watermark interval and upsert overlapping facts."""

    caplog.set_level(logging.INFO)

    seed_facts(
        window_config,
        [
            "2026-11-26T10:00:00Z",
            "2026-11-26T12:00:00Z",
            "2026-11-26T15:00:00Z",
        ],
        FORECAST_SOURCE,
    )

    clock = Mock()
    clock.now.return_value = NOW

    monkeypatch.setattr(
        "weatherflow.pipeline.datetime",
        clock,
    )

    mocked_fetch = Mock(
        side_effect=fake_fetch
    )

    monkeypatch.setattr(
        "weatherflow.windows.fetch_window",
        mocked_fetch,
    )

    assert run(window_config) == 0

    assert mocked_fetch.call_count == 1

    args = mocked_fetch.call_args

    assert args.args[2] == pd.Timestamp(
        "2026-11-26T10:00:00Z"
    )

    assert args.args[3] == pd.Timestamp(
        "2026-11-26T23:00:00Z"
    )

    assert args.kwargs["archive"] is False

    assert fact_count(
        window_config,
        FORECAST_SOURCE,
    ) == 14

    assert "new=11 updated=3" in caplog.text

    assert (
        "DQ PASS: observation_freshness"
        in caplog.text
    )


def test_recent_archive_dates_are_rejected(
    window_config,
):
    """Prevent requests inside the configured archive lag."""

    with pytest.raises(
        ValueError,
        match="availability lag",
    ):

        resolve_backfill_dates(
            window_config,
            NOW,
            start_date="2026-11-24",
            end_date="2026-11-25",
        )
