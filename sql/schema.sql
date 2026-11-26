-- WeatherFlow dimensional model.
-- Grain: one row per city, per hour, per source.

CREATE TABLE IF NOT EXISTS dim_city (
    city_id INTEGER PRIMARY KEY,
    city_name TEXT NOT NULL UNIQUE,
    country TEXT NOT NULL,
    latitude REAL NOT NULL
        CHECK (latitude BETWEEN -90 AND 90),
    longitude REAL NOT NULL
        CHECK (longitude BETWEEN -180 AND 180)
);


CREATE TABLE IF NOT EXISTS dim_date (
    date_id INTEGER PRIMARY KEY,
    full_date TEXT NOT NULL UNIQUE,
    day_of_week TEXT NOT NULL,
    is_weekend INTEGER NOT NULL
        CHECK (is_weekend IN (0, 1)),
    day_of_month INTEGER NOT NULL,
    month INTEGER NOT NULL
        CHECK (month BETWEEN 1 AND 12),
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL
        CHECK (quarter BETWEEN 1 AND 4)
);


CREATE TABLE IF NOT EXISTS fact_weather_hourly (
    city_id INTEGER NOT NULL,
    date_id INTEGER NOT NULL,

    observed_at_utc TEXT NOT NULL,
    observed_at_local TEXT NOT NULL,

    hour_local INTEGER NOT NULL
        CHECK (hour_local BETWEEN 0 AND 23),

    temperature_c REAL NOT NULL,
    feels_like_c REAL,
    humidity_pct INTEGER,
    precipitation_mm REAL,
    wind_speed_kmh REAL,
    weather_code INTEGER,

    weather_description TEXT NOT NULL,
    weather_category TEXT NOT NULL,

    temperature_f REAL,
    wind_speed_ms REAL,

    beaufort_scale INTEGER
        CHECK (beaufort_scale BETWEEN 0 AND 12),

    is_daylight INTEGER
        CHECK (is_daylight IN (0, 1)),

    outdoor_work_risk TEXT NOT NULL
        CHECK (
            outdoor_work_risk IN ('low', 'medium', 'high')
        ),

    source TEXT NOT NULL,
    ingested_at_utc TEXT NOT NULL,

    PRIMARY KEY (
        city_id,
        observed_at_utc,
        source
    ),

    FOREIGN KEY (city_id)
        REFERENCES dim_city(city_id),

    FOREIGN KEY (date_id)
        REFERENCES dim_date(date_id)
);


CREATE INDEX IF NOT EXISTS idx_fact_weather_date
ON fact_weather_hourly(date_id);

CREATE INDEX IF NOT EXISTS idx_fact_weather_utc
ON fact_weather_hourly(observed_at_utc);
