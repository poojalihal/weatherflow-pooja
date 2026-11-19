
-- Query 1: How many weather records do we have for each city?
-- Also show the earliest and latest observation time.

SELECT
    city,
    COUNT(*) AS total_records,
    MIN(observed_at) AS earliest_observation,
    MAX(observed_at) AS latest_observation
FROM weather_hourly
GROUP BY city
ORDER BY city;


-- Query 2: What was the average temperature in each city yesterday?

SELECT
    city,
    ROUND(AVG(temperature_c), 2) AS average_temperature_c
FROM weather_hourly
WHERE DATE(observed_at) = DATE('now', 'localtime', '-1 day')
GROUP BY city
ORDER BY average_temperature_c DESC;


-- Query 3: What were the five windiest hours across all cities?

SELECT
    city,
    observed_at,
    ROUND(wind_speed_kmh, 2) AS wind_speed_kmh
FROM weather_hourly
ORDER BY wind_speed_kmh DESC
LIMIT 5;
