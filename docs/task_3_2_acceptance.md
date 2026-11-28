# Task 3.2: PostgreSQL Warehouse in Docker

**Verification date:** 28 November 2026

**Branch:** feature/postgres

**Status:** Technical acceptance criteria passed.

## Environment

| Component | Version or configuration |
| --- | --- |
| PostgreSQL | 18.7 |
| Psycopg | 3.3.9 |
| Psycopg implementation | binary |
| Python test environment | Linux, Python 3.13.18 |
| Warehouse port | 127.0.0.1:5433 |
| Container port | 5432 |
| Persistent volume | weatherflow-pooja_pgdata |
| Container health | Healthy |

## Automated testing

- 76 tests passed in 4.39 seconds.
- 73 existing tests passed.
- 3 PostgreSQL integration tests passed.
- Overall coverage: 91.69%.
- Required coverage: 70%.
- PostgreSQL module coverage: 91%.
- Atomic rollback verified using an invalid risk value.
- Integration tests use isolated PostgreSQL schemas.

## Historical backfill

Historical period: 23 October to 21 November 2026.

The initial live Open-Meteo extraction encountered invalid JSON
responses and an HTTP 500 error.

| Metric | Initial attempt | Raw replay |
| --- | ---: | ---: |
| Successful windows | 15 | 25 |
| Failed windows | 10 | 0 |
| Valid records | 2280 | 3600 |
| Missing hourly slots | 1320 | 0 |
| Loaded records | 0 | 3600 |
| Exit code | 1 | 0 |

The pipeline correctly blocked the incomplete initial load.
The warehouse was subsequently rebuilt using genuine saved
raw API responses through the existing ETL and validation
pipeline. The SQLite database was not copied.

All five cities received 720 historical records each.

## Live pipeline idempotency

Three consecutive live executions on 28 November 2026:

| Metric | Run 1 | Run 2 | Run 3 |
| --- | ---: | ---: | ---: |
| Input records | 240 | 130 | 130 |
| Valid records | 240 | 130 | 130 |
| Quarantined records | 0 | 0 | 0 |
| New records | 240 | 0 | 0 |
| Updated records | 0 | 130 | 130 |
| Total fact rows | 3840 | 3840 | 3840 |

### Log evidence

Run 1:
    PostgreSQL upsert: new=240 updated=0 total=240
    Total fact rows in PostgreSQL: 3840

Run 2:
    PostgreSQL upsert: new=0 updated=130 total=130
    Total fact rows in PostgreSQL: 3840

Run 3:
    PostgreSQL upsert: new=0 updated=130 total=130
    Total fact rows in PostgreSQL: 3840

All three pipeline runs completed successfully.

The forecast watermark was 2026-11-28T00:00:00+00:00
for all five cities in runs 2 and 3.

The configured two-hour overlap was applied successfully.

Incremental processing reduced input volume from 240 to
130 records, a reduction of 45.83%.

## Persistence verification

- Facts before container removal: 3840.
- Docker Compose down completed.
- Docker Compose up recreated a healthy warehouse.
- Facts after container recreation: 3840.
- Records lost: 0.

Result: PASS.

## Database integrity

| Check | Result |
| --- | ---: |
| Cities | 5 |
| Dates | 1095 |
| Historical archive facts | 3600 |
| Forecast facts | 240 |
| Total facts | 3840 |
| Duplicate key groups | 0 |
| Orphaned fact records | 0 |
| Invalid risk records | 0 |

## Analytical SQL

All five analytical queries executed with exit code 0.

| Query | Returned rows |
| --- | ---: |
| City record counts and observation ranges | 5 |
| Average temperature yesterday | 5 |
| Five windiest hours | 5 |
| Weekday versus weekend wind speed | 10 |
| Outdoor work risk distribution | 233 |

## Acceptance checklist

- [x] PostgreSQL warehouse service is healthy.
- [x] Named volume preserves rows after container recreation.
- [x] Three consecutive pipeline runs retain identical fact counts.
- [x] Mid-load failure leaves no new fact records.
- [x] DATABASE_URL is read from the environment.
- [x] .env is ignored and not tracked by Git.
- [x] All five analytical queries run on PostgreSQL.
- [x] Historical data rebuilt from genuine raw responses.
- [x] Existing automated tests remain passing.

## Known limitations and follow-up

- Native Windows Psycopg imports remain blocked by Application
  Control. PostgreSQL operations use the Linux Docker runtime.
- Invalid JSON responses require improved retry handling.
- Historical reconstruction used a one-off raw replay procedure
  following an unsuccessful live historical extraction.
- The warehouse contains historical data from 23 October to
  21 November and forecast data from 27 to 28 November.
  It does not yet contain continuous coverage between those windows.
- The temporary development image will be replaced by the
  project Dockerfile and pipeline service in Task 3.3.
- CLI automated test coverage remains an improvement area.
