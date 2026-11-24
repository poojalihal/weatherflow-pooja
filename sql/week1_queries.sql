-- Query 1: How many weather records do we have for each city?
-- Also show the earliest and latest observation time in UTC.

SELECT
    city,
    COUNT(*) AS total_records,
    MIN(observed_at_utc) AS earliest_observation_utc,
    MAX(observed_at_utc) AS latest_observation_utc
FROM weather_hourly
GROUP BY city
ORDER BY city;


-- Query 2: What was the average temperature in each city yesterday?
-- Use the UK local calendar date.

SELECT
    city,
    ROUND(AVG(temperature_c), 2) AS average_temperature_c
FROM weather_hourly
WHERE SUBSTR(observed_at_local, 1, 10)
      = DATE('now', 'localtime', '-1 day')
GROUP BY city
ORDER BY average_temperature_c DESC;


-- Query 3: What were the five windiest hours across all cities?
-- Show both UTC and UK local observation timestamps.

SELECT
    city,
    observed_at_utc,
    observed_at_local,
    ROUND(wind_speed_kmh, 2) AS wind_speed_kmh
FROM weather_hourly
ORDER BY wind_speed_kmh DESC
LIMIT 5;
