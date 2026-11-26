"""Test WeatherFlow transformation functions."""

import pandas as pd
import pytest

from weatherflow.storage import load_wmo_codes
from weatherflow.transform import (
    flatten_payload,
    standardise_columns,
    add_weather_description,
    add_derived_metrics,
    deduplicate,
    transform,
)


@pytest.fixture
def sample_payload() -> dict:
    """Provide a small synthetic weather response."""
    return {
        "latitude": 51.50853,
        "longitude": -0.12574,
        "hourly": {
            "time": [
                "2026-06-30T22:00",
                "2026-06-30T23:00",
            ],
            "temperature_2m": [0.0, 20.0],
            "relative_humidity_2m": [80, 60],
            "apparent_temperature": [-2.0, 19.0],
            "precipitation": [0.0, 4.0],
            "wind_speed_10m": [3.6, 18.0],
            "weather_code": [0, 63],
            "is_day": [1, 0],
        },
    }


def test_flatten_payload(sample_payload):
    """Flatten hourly data and preserve city metadata."""
    df = flatten_payload(sample_payload, "London")

    assert len(df) == 2
    assert df["city"].eq("London").all()
    assert "latitude" in df.columns
    assert "longitude" in df.columns


def test_timezone_conversion(sample_payload):
    """Convert UTC to UK local time across midnight in summer."""
    df = flatten_payload(sample_payload, "London")
    result = standardise_columns(df)

    assert str(result["observed_at_utc"].dt.tz) == "UTC"

    assert result.iloc[1]["observed_at_local"].isoformat() == (
        "2026-07-01T00:00:00+01:00"
    )


def test_unknown_weather_code():
    """Map unrecognised weather codes to unknown."""
    df = pd.DataFrame({"weather_code": [0, 999]})

    result = add_weather_description(df, load_wmo_codes())

    assert result.iloc[0]["weather_category"] == "clear"
    assert result.iloc[1]["weather_description"] == "unknown"
    assert result.iloc[1]["weather_category"] == "unknown"


def test_unit_conversions(sample_payload):
    """Verify Fahrenheit and metres-per-second conversions."""
    df = flatten_payload(sample_payload, "London")
    df = standardise_columns(df)
    df = add_weather_description(df, load_wmo_codes())

    result = add_derived_metrics(df)

    assert result.iloc[0]["temperature_f"] == pytest.approx(32)
    assert result.iloc[1]["temperature_f"] == pytest.approx(68)
    assert result.iloc[0]["wind_speed_ms"] == pytest.approx(1)
    assert result.iloc[1]["wind_speed_ms"] == pytest.approx(5)
    assert result["is_daylight"].tolist() == [True, False]


@pytest.mark.parametrize(
    "wind_ms,precipitation,temperature,category,expected",
    [
        (2, 0, 10, "clear", "low"),
        (8, 0, 10, "clear", "medium"),
        (13.9, 0, 10, "clear", "high"),
        (2, 1, 10, "rain", "medium"),
        (2, 4, 10, "rain", "high"),
        (2, 0, 0, "clear", "medium"),
        (2, 0, 10, "storm", "high"),
        (2, 0, 10, "snow", "high"),
        (14, 4, -1, "snow", "high"),
        (7.9, 0.9, 0.1, "cloudy", "low"),
        (13.8, 3.9, 10, "rain", "medium"),
    ],
)
def test_outdoor_work_risk(
    wind_ms,
    precipitation,
    temperature,
    category,
    expected,
):
    """Verify every risk rule and important boundaries."""
    df = pd.DataFrame({
        "wind_speed_kmh": [wind_ms * 3.6],
        "temperature_c": [temperature],
        "precipitation_mm": [precipitation],
        "weather_category": [category],
        "is_day": [1],
    })

    result = add_derived_metrics(df)

    assert result.iloc[0]["outdoor_work_risk"] == expected


@pytest.mark.parametrize(
    "wind_ms,expected",
    [
        (0, 0),
        (0.3, 1),
        (8.0, 5),
        (13.9, 7),
        (32.7, 12),
        (40, 12),
    ],
)
def test_beaufort_boundaries(wind_ms, expected):
    """Verify Beaufort threshold mapping."""
    df = pd.DataFrame({
        "wind_speed_kmh": [wind_ms * 3.6],
        "temperature_c": [10],
        "precipitation_mm": [0],
        "weather_category": ["clear"],
        "is_day": [1],
    })

    result = add_derived_metrics(df)

    assert result.iloc[0]["beaufort_scale"] == expected


def test_deduplicate_keeps_latest():
    """Keep the newest ingestion regardless of input row order."""
    df = pd.DataFrame({
        "city": ["London", "London"],
        "observed_at_utc": pd.to_datetime([
            "2026-11-25T00:00:00Z",
            "2026-11-25T00:00:00Z",
        ]),
        "temperature_c": [12, 10],
        "ingested_at_utc": [
            "2026-11-25T02:00:00Z",
            "2026-11-25T01:00:00Z",
        ],
    })

    result = deduplicate(df)

    assert len(result) == 1
    assert result.iloc[0]["temperature_c"] == 12


def test_missing_daylight(sample_payload):
    """Preserve missing daylight data instead of inventing a value."""
    del sample_payload["hourly"]["is_day"]

    result = transform(
        [("London", sample_payload)],
        load_wmo_codes(),
        "2026-11-25T00:00:00+00:00",
    )

    assert result["is_daylight"].isna().all()


def test_complete_transform_is_repeatable(sample_payload):
    """Produce identical results from identical inputs."""
    raw = [("London", sample_payload)]
    lookup = load_wmo_codes()
    timestamp = "2026-11-25T00:00:00+00:00"

    first = transform(raw, lookup, timestamp)
    second = transform(raw, lookup, timestamp)

    pd.testing.assert_frame_equal(first, second)

    assert first.shape == (2, 19)
