-- WeatherFlow star-schema analytical queries.
-- Query 2 uses :yesterday, supplied as a UK calendar date.

-- Query 1: Record count and observation range by city.

SELECT
    c.city_name,
    COUNT(*) AS total_records,
    MIN(f.observed_at_utc) AS earliest_observation_utc,
    MAX(f.observed_at_utc) AS latest_observation_utc
FROM fact_weather_hourly AS f
JOIN dim_city AS c
    ON f.city_id = c.city_id
GROUP BY c.city_name
ORDER BY c.city_name;


-- Query 2: Average temperature yesterday in UK local time.

SELECT
    c.city_name,
    ROUND(AVG(f.temperature_c), 2) AS average_temperature_c
FROM fact_weather_hourly AS f
JOIN dim_city AS c
    ON f.city_id = c.city_id
JOIN dim_date AS d
    ON f.date_id = d.date_id
WHERE d.full_date = :yesterday
GROUP BY c.city_name
ORDER BY average_temperature_c DESC;


-- Query 3: Five windiest hours across all cities.

SELECT
    c.city_name,
    f.observed_at_utc,
    f.observed_at_local,
    ROUND(f.wind_speed_kmh, 2) AS wind_speed_kmh,
    f.beaufort_scale
FROM fact_weather_hourly AS f
JOIN dim_city AS c
    ON f.city_id = c.city_id
ORDER BY f.wind_speed_kmh DESC, f.observed_at_utc
LIMIT 5;


-- Query 4: Average wind speed on weekends versus weekdays.

SELECT
    c.city_name,
    CASE
        WHEN d.is_weekend = 1 THEN 'Weekend'
        ELSE 'Weekday'
    END AS day_type,
    ROUND(AVG(f.wind_speed_kmh), 2) AS average_wind_kmh,
    COUNT(*) AS observations
FROM fact_weather_hourly AS f
JOIN dim_city AS c
    ON f.city_id = c.city_id
JOIN dim_date AS d
    ON f.date_id = d.date_id
GROUP BY c.city_name, d.is_weekend
ORDER BY c.city_name, day_type;


-- Query 5: Outdoor work risk distribution by city and date.

SELECT
    c.city_name,
    d.full_date,
    f.outdoor_work_risk,
    COUNT(*) AS hours
FROM fact_weather_hourly AS f
JOIN dim_city AS c
    ON f.city_id = c.city_id
JOIN dim_date AS d
    ON f.date_id = d.date_id
GROUP BY
    c.city_name,
    d.full_date,
    f.outdoor_work_risk
ORDER BY
    c.city_name,
    d.full_date,
    f.outdoor_work_risk;
