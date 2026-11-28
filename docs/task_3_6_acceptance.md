# Task 3.6: Dashboard, Alerts and Decision Records

**Verification date:** 28 November 2026

**Branch:** feature/dashboard

## Dashboard implementation

- Streamlit dashboard connected to PostgreSQL.
- Separate non-root Docker dashboard service.
- Parameterised SQL queries.
- Read-only database transactions.
- Database query caching with a 300-second TTL.
- UK local timestamp display.
- Outdoor work risk displayed in words and colours.
- Seven-day temperature and wind trends.
- Missing observation and stale forecast warnings.
- Latest data quality report summary.
- Multi-source comparison interface.

## Dashboard verification

| Measurement | Result |
| --- | ---: |
| Monitored cities | 5 |
| Warehouse records | 3840 |
| DQ checks passed | 10 |
| DQ checks failed | 0 |
| Quarantined records | 0 |
| Available forecast city-hours | 115 |
| Missing forecast city-hours | 5 |
| Available high-risk city-hours | 0 |
| Historical trend records | 240 |
| Expected historical trend records | 840 |
| HTTP health status | 200 |

The dashboard correctly identifies incomplete forecast
and historical coverage rather than inventing observations.

## Automated testing

| Measurement | Result |
| --- | --- |
| Tests passed | 79 |
| Tests failed | 0 |
| Execution time | 4.76 seconds |
| Overall coverage | 89.99% |
| Alert module coverage | 78% |
| Required coverage | 70% |

## Risk alerts

The alert engine examines the next 12 hourly slots,
combines high-risk observations from available sources,
groups consecutive risky periods by city, and stores
notifications in PostgreSQL.

Unique UTC city-hour keys prevent duplicate notifications.

### Live execution

| Measurement | Run 1 | Run 2 |
| --- | ---: | ---: |
| High-risk rows | 0 | 0 |
| New alerts | 0 | 0 |
| Warehouse records | 3840 | 3840 |

Both executions correctly avoided unnecessary alerts.

### Controlled end-to-end test

Synthetic high-risk observations were created inside
an isolated temporary PostgreSQL schema.

| Measurement | Run 1 | Run 2 |
| --- | ---: | ---: |
| High-risk rows | 3 | 3 |
| New alerts | 1 | 0 |
| Stored alerts | 1 | 1 |
| Deduplication keys | 3 | 3 |

The generated message identified Edinburgh, the risky
period, heavy precipitation, storm and strong wind.

The temporary schema was removed after verification.

Result: PASS.

## Acceptance checklist

- [x] Dashboard displays all five cities.
- [x] PostgreSQL connection verified.
- [x] Risk displayed in words as well as colour.
- [x] UK local timestamps displayed.
- [x] Missing and stale data warnings implemented.
- [x] Latest data quality summary displayed.
- [x] Risk alert storage and logging verified.
- [x] Alert deduplication verified.
- [x] All 79 automated tests pass.
- [ ] Both weather sources available in the dashboard.
- [ ] Airflow pipeline failure notification verified.
- [ ] Programme agreement on alert-delivery fallback.
- [ ] Week 3 reflection completed.

## Known limitations and follow-up

- WeatherAPI comparison requires Task 3.1.
- Airflow failure notifications require Task 3.4.
- Database-and-log alert delivery requires programme agreement.
- Historical coverage is incomplete within the trend window.
- Forecast coverage does not yet extend across all 24 slots.
- Updated trend chart point visibility requires visual verification.
- Synthetic alert evidence is not an actual weather warning.
- External messaging delivery has not been implemented.
