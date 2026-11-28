"""WeatherFlow operational weather dashboard."""

import os
from pathlib import Path

import pandas as pd
import psycopg
import streamlit as st
import yaml

from dotenv import load_dotenv
from psycopg.rows import dict_row


ROOT = Path(__file__).resolve().parents[1]

load_dotenv(ROOT / ".env", override=False)

UK_TZ = "Europe/London"

FORECAST_SOURCES = [
    "open_meteo_forecast",
    "weatherapi_forecast",
]

RISK_ORDER = {
    "low": 1,
    "medium": 2,
    "high": 3,
}

RISK_LABELS = {
    1: "Low",
    2: "Medium",
    3: "High",
}


st.set_page_config(
    page_title="WeatherFlow",
    page_icon="🌦️",
    layout="wide",
)


with (ROOT / "config.yaml").open(
    encoding="utf-8"
) as file:
    config = yaml.safe_load(file)

dq_config = config["data_quality"]

FRESHNESS_HOURS = dq_config.get(
    "freshness_max_hours", 3
)

DIFFERENCE_THRESHOLD = dq_config.get(
    "cross_source_temperature_threshold_c", 3.0
)


@st.cache_data(ttl=300, show_spinner=False)
def read_warehouse(start, end):
    """Read warehouse data using parameterised SQL."""

    url = os.getenv("DATABASE_URL")

    if not url:
        raise RuntimeError("DATABASE_URL is not configured")

    with psycopg.connect(
        url,
        connect_timeout=5,
        row_factory=dict_row,
    ) as conn:

        conn.execute("SET TRANSACTION READ ONLY")

        cities = conn.execute("""
            SELECT city_name
            FROM dim_city
            ORDER BY city_name
        """).fetchall()

        totals = conn.execute("""
            SELECT
                COUNT(*) AS total_records,
                MAX(ingested_at_utc) AS latest_ingestion
            FROM fact_weather_hourly
        """).fetchone()

        freshness = conn.execute("""
            SELECT
                c.city_name,
                MAX(f.ingested_at_utc) AS latest_forecast
            FROM dim_city c
            LEFT JOIN fact_weather_hourly f
                ON f.city_id = c.city_id
                AND f.source = ANY(%s)
            GROUP BY c.city_name
            ORDER BY c.city_name
        """, (FORECAST_SOURCES,)).fetchall()

        rows = conn.execute("""
            SELECT
                c.city_name,
                f.observed_at_utc,
                f.temperature_c,
                f.wind_speed_kmh,
                f.outdoor_work_risk,
                f.source,
                f.ingested_at_utc
            FROM fact_weather_hourly f
            JOIN dim_city c
                ON c.city_id = f.city_id
            WHERE f.observed_at_utc >= %s
              AND f.observed_at_utc < %s
            ORDER BY f.observed_at_utc, c.city_name
        """, (start, end)).fetchall()

    columns = [
        "city_name",
        "observed_at_utc",
        "temperature_c",
        "wind_speed_kmh",
        "outdoor_work_risk",
        "source",
        "ingested_at_utc",
    ]

    df = pd.DataFrame(rows, columns=columns)

    df["observed_at_utc"] = pd.to_datetime(
        df["observed_at_utc"], utc=True
    )

    df["ingested_at_utc"] = pd.to_datetime(
        df["ingested_at_utc"], utc=True
    )

    return (
        df,
        [city["city_name"] for city in cities],
        totals,
        freshness,
    )


@st.cache_data(ttl=300, show_spinner=False)
def read_latest_dq():
    """Read summary information from the latest DQ report."""

    reports_dir = ROOT / "docs" / "dq_reports"

    reports = sorted(
        reports_dir.glob("*.md"),
        reverse=True,
    )

    if not reports:
        return None

    try:
        content = reports[0].read_text(
            encoding="utf-8"
        )
    except OSError:
        return None

    summary = {
        "filename": reports[0].name,
        "status": "UNKNOWN",
        "run_time": None,
        "input": 0,
        "valid": 0,
        "quarantined": 0,
        "loaded": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
    }

    metrics = {
        "Input records": "input",
        "Valid records": "valid",
        "Quarantined records": "quarantined",
        "Loaded records": "loaded",
    }

    for line in content.splitlines():

        if line.startswith("Run status:"):
            summary["status"] = line.split(
                ":", 1
            )[1].strip()

        elif line.startswith("Run time UTC:"):
            summary["run_time"] = line.split(
                ":", 1
            )[1].strip()

        elif line.startswith("|"):

            cells = [
                cell.strip()
                for cell in line.strip("|").split("|")
            ]

            if len(cells) == 2:
                key = metrics.get(cells[0])

                if key:
                    try:
                        summary[key] = int(cells[1])
                    except ValueError:
                        pass

            if len(cells) >= 6:

                result = cells[3]

                if result == "PASS":
                    summary["passed"] += 1

                elif result == "FAIL":
                    summary["failed"] += 1

                elif result == "SKIPPED":
                    summary["skipped"] += 1

    return summary


def uk_time(value):
    """Format a timestamp in UK local time."""

    if value is None or pd.isna(value):
        return "Unavailable"

    return pd.to_datetime(
        value, utc=True
    ).tz_convert(UK_TZ).strftime(
        "%d %b %Y, %H:%M %Z"
    )


def risk_style(value):
    """Show risk using both colour and text."""

    colours = {
        "High": "background-color: #fca5a5; color: #7f1d1d",
        "Medium": "background-color: #fde68a; color: #78350f",
        "Low": "background-color: #bbf7d0; color: #14532d",
        "Missing": "background-color: #e5e7eb; color: #374151",
    }

    return colours.get(value, "")


st.title("🌦️ WeatherFlow")
st.caption(
    "Outdoor operations planning across five UK cities"
)

if st.sidebar.button("Refresh warehouse data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.caption(
    "Database queries are cached for five minutes."
)

now = pd.Timestamp.now(tz="UTC")

start = now.floor("h")
end = start + pd.Timedelta(hours=24)

today_uk = now.tz_convert(UK_TZ).normalize()

trend_start = (
    today_uk - pd.DateOffset(days=7)
).tz_convert("UTC")

trend_end = today_uk.tz_convert("UTC")

try:
    df, cities, totals, freshness = read_warehouse(
        trend_start.to_pydatetime(),
        end.to_pydatetime(),
    )
except Exception:
    st.error(
        "Warehouse unavailable. Check PostgreSQL "
        "and the runtime database configuration."
    )
    st.stop()

if not cities:
    st.warning(
        "No cities have been loaded into the warehouse."
    )
    st.stop()


# --------------------------------------------------
# 1. Freshness and data quality
# --------------------------------------------------

dq = read_latest_dq()

columns = st.columns(4)

columns[0].metric(
    "Monitored cities", len(cities)
)

columns[1].metric(
    "Warehouse records",
    f"{totals['total_records']:,}",
)

columns[2].metric(
    "Latest DQ status",
    dq["status"] if dq else "Unavailable",
)

columns[3].metric(
    "Quarantined rows",
    dq["quarantined"] if dq else "Unavailable",
)

st.caption(
    "Data as of "
    + uk_time(totals["latest_ingestion"])
)

stale_cities = []

for row in freshness:

    timestamp = row["latest_forecast"]

    if timestamp is None:
        stale_cities.append(row["city_name"])
        continue

    age = (
        now - pd.to_datetime(timestamp, utc=True)
    ).total_seconds() / 3600

    if age > FRESHNESS_HOURS:
        stale_cities.append(row["city_name"])

if stale_cities:
    st.warning(
        "Forecast data is missing or older than "
        f"{FRESHNESS_HOURS} hours for: "
        + ", ".join(stale_cities)
        + ". Do not rely on risk classifications "
          "without checking updated conditions."
    )
else:
    st.success(
        "All five city forecasts are within "
        "the freshness threshold."
    )

if dq:

    if dq["status"] != "SUCCESS" or dq["failed"]:
        st.warning(
            "The latest recorded DQ report contains "
            "a failure or unsuccessful run."
        )

    st.caption(
        f"Latest DQ report: {uk_time(dq['run_time'])} | "
        f"Passed: {dq['passed']} | "
        f"Failed: {dq['failed']} | "
        f"Skipped: {dq['skipped']}"
    )

    with st.expander("Latest data quality summary"):

        st.write({
            "Input records": dq["input"],
            "Valid records": dq["valid"],
            "Quarantined records": dq["quarantined"],
            "Loaded records": dq["loaded"],
            "Checks passed": dq["passed"],
            "Checks failed": dq["failed"],
            "Checks skipped": dq["skipped"],
        })

else:
    st.warning("No data quality report is available.")


# --------------------------------------------------
# 2. Outdoor work risk: next 24 hourly slots
# --------------------------------------------------

st.header("Outdoor work risk — next 24 hours")

st.caption(
    "Includes the current hour. All displayed times "
    "are UK local time. Where both forecast sources "
    "are available, the higher risk is displayed."
)

future = df[
    df["source"].isin(FORECAST_SOURCES)
    & (df["observed_at_utc"] >= start)
    & (df["observed_at_utc"] < end)
].copy()

hours = pd.date_range(
    start=start,
    periods=24,
    freq="h",
)

risk_table = pd.DataFrame(
    "Missing",
    index=cities,
    columns=hours,
)

if not future.empty:

    future["risk_rank"] = future[
        "outdoor_work_risk"
    ].map(RISK_ORDER)

    highest = future.groupby(
        ["city_name", "observed_at_utc"]
    )["risk_rank"].max()

    for (city, hour), rank in highest.items():

        if city in cities and hour in hours:

            risk_table.loc[city, hour] = (
                RISK_LABELS.get(rank, "Missing")
            )

high_hours = int(
    (risk_table == "High").sum().sum()
)

missing_hours = int(
    (risk_table == "Missing").sum().sum()
)

a, b, c = st.columns(3)

a.metric("High-risk city-hours", high_hours)

b.metric(
    "Available city-hours",
    risk_table.size - missing_hours,
)

c.metric("Missing city-hours", missing_hours)

if high_hours:
    st.warning(
        "High-risk outdoor work periods identified. "
        "Review the affected cities and hours."
    )

if missing_hours:
    st.warning(
        f"{missing_hours} city-hour slots have no "
        "forecast. Missing data is not low risk."
    )

display_risk = risk_table.copy()

display_risk.columns = [
    hour.tz_convert(UK_TZ).strftime(
        "%d %b %H:%M %Z"
    )
    for hour in hours
]

display_risk.index.name = "City"

st.dataframe(
    display_risk.style.map(risk_style),
    width="stretch",
)

st.caption(
    "High = red | Medium = amber | "
    "Low = green | Missing = grey"
)


# --------------------------------------------------
# 3. Seven-day temperature and wind trends
# --------------------------------------------------

st.header("Weather trends — last seven completed UK days")

past = df[
    (df["observed_at_utc"] >= trend_start)
    & (df["observed_at_utc"] < trend_end)
    & df["source"].isin([
        "open_meteo_archive",
        "open_meteo_forecast",
    ])
].copy()

# Prefer historical archive records where both Open-Meteo
# sources cover the same city and hour.
past["priority"] = past["source"].map({
    "open_meteo_archive": 0,
    "open_meteo_forecast": 1,
})

past = past.sort_values(
    ["priority", "ingested_at_utc"],
    ascending=[True, False],
).drop_duplicates(
    ["city_name", "observed_at_utc"],
    keep="first",
)

past["uk_date"] = past[
    "observed_at_utc"
].dt.tz_convert(UK_TZ).dt.strftime("%Y-%m-%d")

days = pd.date_range(
    end=today_uk - pd.DateOffset(days=1),
    periods=7,
    freq="D",
).strftime("%Y-%m-%d")

expected_hours = len(pd.date_range(
    start=trend_start,
    end=trend_end,
    freq="h",
    inclusive="left",
)) * len(cities)

st.caption(
    "Daily averages use Open-Meteo archive data "
    "where available, otherwise Open-Meteo forecast "
    "data for past hours. Overlapping records "
    "are not counted twice."
)

if len(past) < expected_hours:
    st.warning(
        f"Incomplete historical coverage: "
        f"{len(past):,} of {expected_hours:,} "
        "expected city-hour records are available."
    )

if past.empty:
    st.info("No records are available in the trend window.")
else:

    temperature = past.pivot_table(
        index="uk_date",
        columns="city_name",
        values="temperature_c",
        aggfunc="mean",
    ).reindex(index=days, columns=cities)

    wind = past.pivot_table(
        index="uk_date",
        columns="city_name",
        values="wind_speed_kmh",
        aggfunc="mean",
    ).reindex(index=days, columns=cities)

    left, right = st.columns(2)

    with left:
        st.subheader("Average temperature (°C)")
        st.line_chart(temperature, point=True)

    with right:
        st.subheader("Average wind speed (km/h)")
        st.line_chart(wind, point=True)

    coverage = past.groupby(
        ["uk_date", "city_name"]
    ).size().unstack()

    coverage = coverage.reindex(
        index=days,
        columns=cities,
    ).fillna(0).astype(int)

    with st.expander("Daily observation coverage"):
        st.dataframe(coverage)

    st.caption(
        "Daily averages may represent partial days. "
        "Missing dates are not assigned artificial values."
    )


# --------------------------------------------------
# 4. Weather source comparison
# --------------------------------------------------

st.header("Weather source comparison")

selected_city = st.selectbox(
    "Select a city",
    cities,
)

comparison = future[
    future["city_name"] == selected_city
].pivot(
    index="observed_at_utc",
    columns="source",
    values="temperature_c",
).reindex(
    index=hours,
    columns=FORECAST_SOURCES,
)

comparison.columns = [
    "Open-Meteo",
    "WeatherAPI",
]

matched = comparison.dropna().copy()

st.caption(
    "Comparison uses matching UTC observation hours "
    f"and a temperature difference threshold of "
    f"{DIFFERENCE_THRESHOLD}°C."
)

if matched.empty:

    st.info(
        "No matching observations from both sources "
        "are available. WeatherAPI integration is "
        "required before disagreement can be measured."
    )

else:

    matched["Absolute difference (°C)"] = (
        matched["Open-Meteo"]
        - matched["WeatherAPI"]
    ).abs()

    disagreements = int(
        (
            matched["Absolute difference (°C)"]
            > DIFFERENCE_THRESHOLD
        ).sum()
    )

    a, b, c = st.columns(3)

    a.metric("Matching hours", len(matched))

    b.metric(
        "Hours exceeding threshold",
        disagreements,
    )

    c.metric(
        "Disagreement rate",
        f"{disagreements / len(matched):.1%}",
    )

    if disagreements:
        st.warning(
            "Forecast sources disagree beyond the "
            "configured temperature threshold."
        )

    matched.index = [
        uk_time(value) for value in matched.index
    ]

    st.dataframe(matched.round(2))

if comparison.notna().any().any():

    comparison.index = [
        uk_time(value) for value in comparison.index
    ]

    st.line_chart(comparison)

st.divider()

st.caption(
    "WeatherFlow is a planning aid. Check current "
    "conditions before undertaking hazardous outdoor work."
)
