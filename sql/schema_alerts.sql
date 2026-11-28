-- WeatherFlow alert messages and deduplication records.

CREATE TABLE IF NOT EXISTS alerts (
    alert_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    alert_type TEXT NOT NULL
        CHECK (alert_type IN ('weather_risk', 'pipeline_failure')),
    city_name TEXT,
    period_start_utc TIMESTAMPTZ,
    period_end_utc TIMESTAMPTZ,
    message TEXT NOT NULL,
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alerts_sent (
    alert_key TEXT PRIMARY KEY,
    alert_id BIGINT NOT NULL REFERENCES alerts(alert_id),
    sent_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
