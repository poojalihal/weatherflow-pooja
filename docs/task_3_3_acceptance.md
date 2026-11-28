# Task 3.3: Containerise the Pipeline

**Verification date:** 28 November 2026

**Branch:** feature/docker

**Implementation commit:** 1849f88

## Implementation

- Official Python 3.13 slim base image.
- Runtime dependencies installed before application code.
- WeatherFlow installed as a Python package.
- Non-root container user with UID 1000.
- Configuration path supplied through WEATHERFLOW_CONFIG.
- Credentials supplied through runtime environment variables.
- PostgreSQL service accessed at warehouse:5432.
- Warehouse health-check dependency.
- Persistent data, log and DQ report bind mounts.
- Secrets and local data excluded from Docker build context.

## Automated regression testing

| Measurement | Result |
| --- | --- |
| Tests passed | 76 |
| Tests failed | 0 |
| Execution time | 4.69 seconds |
| Overall coverage | 91.70% |
| Required coverage | 70% |
| Configuration module coverage | 83% |
| PostgreSQL module coverage | 91% |

Regression tests were executed using the Linux development
image with the updated repository source code.

## Image security

- Non-root user verified: UID 1000.
- Configuration path: /app/config.yaml.
- Five configured cities.
- No .env file found in the application image.
- No DATABASE_URL, POSTGRES_PASSWORD or WEATHERAPI_KEY
  found in the standalone image environment.
- All four staged implementation files passed the
  credential protection check.

## Filesystem permission recovery

The first containerised execution failed because the non-root
user could not write to an existing raw data subdirectory.

Existing directory ownership was corrected using a one-off
administrative container.

The permanent pipeline continued running as UID 1000.

All seven directory write checks passed after the correction.
Historical files and PostgreSQL records were retained.

## Containerised pipeline idempotency

Two successful live executions:

| Measurement | Run 1 | Run 2 |
| --- | ---: | ---: |
| Successful API requests | 5 | 5 |
| Failed API requests | 0 | 0 |
| Input records | 125 | 125 |
| Valid records | 125 | 125 |
| Quarantined records | 0 | 0 |
| New records | 0 | 0 |
| Updated records | 125 | 125 |
| Total fact records | 3840 | 3840 |

Log evidence:

    PostgreSQL upsert: new=0 updated=125 total=125
    Total fact rows in PostgreSQL: 3840

Both runs generated raw JSON, processed Parquet and
data quality reports.

Result: PASS.

## Failure exit-code propagation

An intentionally invalid historical date range was supplied.

Expected error:

    ValueError: Start date must not be after end date.

Expected exit code: 1.
Actual exit code: 1.

Result: PASS.

## Fresh-clone build

A separate repository was cloned from GitHub using the
feature/docker branch at commit 1849f88.

The environment template was copied to .env without using
the original development credentials.

Docker Compose configuration validation passed.
Docker Compose built the pipeline image successfully.

Docker reused cached build layers.

Fresh-clone verification exit code: 0.

Result: PASS.

## Acceptance checklist

- [x] Docker Compose builds the pipeline from a fresh clone.
- [x] Two containerised runs retain identical fact counts.
- [x] No .env file inside the application image.
- [x] Pipeline runs as a non-root user.
- [x] CLI failure exit code propagates through Docker.
- [x] Mounted directories are writable.
- [x] Existing regression tests pass.
- [x] README documents Docker execution.
- [ ] Missing WeatherAPI key produces exit code 1.

## Deferred acceptance criterion

The WeatherAPI-specific missing-key test is deferred until
Task 3.1 because the programme's accelerated priority order
places containerisation before the second source.

General CLI failure exit-code propagation has already
been verified.

Task 3.3 must be revisited after Task 3.1 to close this
remaining acceptance criterion.
