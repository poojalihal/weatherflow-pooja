"""Pure transformations for hourly weather records."""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def flatten_payload(payload: dict, city: str) -> pd.DataFrame:
    """Convert one city's hourly API response into tabular records."""
    df = pd.DataFrame(payload["hourly"])

    df["city"] = city
    df["latitude"] = payload["latitude"]
    df["longitude"] = payload["longitude"]

    # Older raw responses may not contain daylight information.
    if "is_day" not in df.columns:
        df["is_day"] = pd.NA

    return df


def standardise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns, standardise numeric types and derive timestamps."""
    result = df.copy()

    result = result.rename(columns={
        "time": "observed_at_utc",
        "temperature_2m": "temperature_c",
        "apparent_temperature": "feels_like_c",
        "relative_humidity_2m": "humidity_pct",
        "precipitation": "precipitation_mm",
        "wind_speed_10m": "wind_speed_kmh",
    })

    result["observed_at_utc"] = pd.to_datetime(
        result["observed_at_utc"],
        utc=True,
        errors="coerce",
    )

    result["observed_at_local"] = (
        result["observed_at_utc"]
        .dt.tz_convert("Europe/London")
    )

    numeric_columns = [
        "temperature_c",
        "feels_like_c",
        "humidity_pct",
        "precipitation_mm",
        "wind_speed_kmh",
        "weather_code",
        "latitude",
        "longitude",
        "is_day",
    ]

    for column in numeric_columns:
        result[column] = pd.to_numeric(
            result[column],
            errors="coerce",
        )

    return result


def add_weather_description(
    df: pd.DataFrame,
    lookup: pd.DataFrame,
) -> pd.DataFrame:
    """Join weather codes to descriptions and categories."""
    reference = lookup.rename(columns={
        "code": "weather_code",
        "description": "weather_description",
        "category": "weather_category",
    })

    result = df.merge(
        reference,
        on="weather_code",
        how="left",
        validate="many_to_one",
    )

    result["weather_description"] = (
        result["weather_description"].fillna("unknown")
    )

    result["weather_category"] = (
        result["weather_category"].fillna("unknown")
    )

    return result


def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate converted units, Beaufort force, daylight and work risk."""
    result = df.copy()

    result["temperature_f"] = (
        result["temperature_c"] * 9 / 5 + 32
    )

    result["wind_speed_ms"] = (
        result["wind_speed_kmh"] / 3.6
    )

    beaufort_bins = [
        0, 0.3, 1.6, 3.4, 5.5, 8.0, 10.8,
        13.9, 17.2, 20.8, 24.5, 28.5, 32.7,
        float("inf"),
    ]

    result["beaufort_scale"] = pd.cut(
        result["wind_speed_ms"].round(10),
        bins=beaufort_bins,
        labels=range(13),
        right=False,
    ).astype("Int64")

    result["is_daylight"] = (
        result["is_day"]
        .map({0: False, 1: True})
        .astype("boolean")
    )

    high_risk = (
        (result["beaufort_scale"] >= 7)
        | result["weather_category"].isin(["storm", "snow"])
        | (result["precipitation_mm"] >= 4)
    ).fillna(False)

    medium_risk = (
        (result["beaufort_scale"] >= 5)
        | (result["precipitation_mm"] >= 1)
        | (result["temperature_c"] <= 0)
    ).fillna(False)

    result["outdoor_work_risk"] = "low"

    # High risk takes precedence over medium risk.
    result.loc[medium_risk, "outdoor_work_risk"] = "medium"
    result.loc[high_risk, "outdoor_work_risk"] = "high"

    return result


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Keep the latest ingested record for each city and UTC hour."""
    result = df.sort_values(
        "ingested_at_utc",
        key=lambda values: pd.to_datetime(values, utc=True),
        kind="stable",
        na_position="first",
    )

    return result.drop_duplicates(
        subset=["city", "observed_at_utc"],
        keep="last",
    ).reset_index(drop=True)


def transform(
    raw_records: list[tuple[str, dict]],
    lookup: pd.DataFrame,
    ingested_at_utc: str,
) -> pd.DataFrame:
    """Apply the complete transformation sequence."""
    if not raw_records:
        raise ValueError("No raw weather records supplied")

    city_dfs = [
        flatten_payload(payload, city)
        for city, payload in raw_records
    ]

    df = pd.concat(city_dfs, ignore_index=True)

    df["ingested_at_utc"] = ingested_at_utc

    df = standardise_columns(df)
    df = add_weather_description(df, lookup)
    df = add_derived_metrics(df)
    df = deduplicate(df)

    # Retain the original schema columns for loader compatibility.
    columns = [
        "city",
        "observed_at_utc",
        "observed_at_local",
        "temperature_c",
        "feels_like_c",
        "humidity_pct",
        "precipitation_mm",
        "wind_speed_kmh",
        "weather_code",
        "ingested_at_utc",
        "latitude",
        "longitude",
        "weather_description",
        "weather_category",
        "temperature_f",
        "wind_speed_ms",
        "beaufort_scale",
        "is_daylight",
        "outdoor_work_risk",
    ]

    return df[columns]
