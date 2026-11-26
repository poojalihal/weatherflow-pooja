# WeatherFlow – Data Engineering Project

## Project Overview

WeatherFlow is a data engineering project that collects weather data for five UK cities using the Open-Meteo API.

The project implements an ETL (Extract, Transform, Load) pipeline that retrieves hourly weather information, stores the original raw data, transforms it into a structured format and loads the results into a SQLite database for SQL analysis.

The five cities covered are:

- Birmingham
- Cardiff
- Edinburgh
- London
- Manchester

## Technologies

- Python
- Git and GitHub
- Requests
- Pandas
- Jupyter Notebook
- SQLite
- SQL
- Python Logging
- VS Code

## Project Structure

```text
weatherflow-pooja/
├── data/
│   ├── raw/
│   └── backups/
├── docs/
│   ├── reflections/
│   │   └── week_1.md
│   ├── reference_critique.md
│   ├── reference_architecture.md
│   ├── data_dictionary.md
│   └── skills_tracker.md
├── logs/
│   └── pipeline.log
├── notebooks/
│   └── 01_explore.ipynb
├── scripts/
│   └── migrate_utc.py
├── sql/
│   └── week1_queries.sql
├── extract.py
├── etl_v1.py
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── .gitignore
└── weather.db
```

The raw data, database, backup and log files are local runtime artefacts and are excluded from version control.

## How to Set Up

1. Clone the repository:

   ```bash
   git clone https://github.com/poojalihal/weatherflow-pooja.git
   cd weatherflow-pooja
   ```

2. Open the project folder in VS Code.

3. Create a Python virtual environment:

   ```bash
   python -m venv .venv
   ```

4. Activate the virtual environment.

   Windows (Git Bash):

   ```bash
   source .venv/Scripts/activate
   ```

   macOS and Linux:

   ```bash
   source .venv/bin/activate
   ```

5. Install the required dependencies:

   ```bash
   python -m pip install -r requirements.txt
   python -m pip install -e .
   ```

6. For notebook exploration, testing and development, install the development dependencies:

   ```bash
   python -m pip install -r requirements-dev.txt
   ```

7. Verify the installed dependencies:

   ```bash
   python -m pip check
   ```

## How to Run the ETL Pipeline

Run the following command from the project root directory:

```bash
python etl_v1.py
```

The pipeline uses absolute project paths derived from `PROJECT_ROOT` using `pathlib`. This ensures that raw data, logs and the SQLite database are stored in the correct project locations regardless of the current working directory.

The pipeline performs three main stages:

### 1. Extract

- Fetches hourly weather data from the Open-Meteo API for five UK cities.
- Requests weather observation timestamps in UTC.
- Uses a configurable request timeout of 10 seconds by default.
- Retries transient API failures up to three times using exponential backoff.
- Does not retry HTTP 4xx client errors.
- Tracks successful extractions and failed cities separately.
- Continues processing the remaining cities if an individual city fails.
- Saves the complete successful API responses as raw JSON files.
- Stores raw files in `data/raw/`, organised by extraction date.
- Prevents raw JSON files from being overwritten when multiple extractions occur within the same second.

### 2. Transform

- Converts API observation timestamps into timezone-aware UTC datetime values.
- Stores the primary observation timestamp as `observed_at_utc`.
- Derives `observed_at_local` using the `Europe/London` timezone.
- Handles UK daylight saving time through timezone-aware conversion.
- Renames weather measurement columns to include their units.
- Adds city and UTC ingestion timestamp information.
- Removes duplicate records using city and UTC observation time.

### 3. Load

- Loads transformed weather records into the SQLite database.
- Creates the `weather_hourly` table if it does not already exist.
- Uses `(city, observed_at_utc)` as the composite primary key.
- Stores timestamps in ISO 8601 format with explicit timezone offsets.
- Uses `INSERT OR REPLACE` to support repeated pipeline runs without creating duplicate city/time records.

## Centralised Pipeline Configuration

The WeatherFlow pipeline uses a shared configuration defined in `extract.py` to avoid duplicated settings and improve maintainability.

### Configuration Constants

| Constant | Purpose |
|---|---|
| `PROJECT_ROOT` | Absolute path to the WeatherFlow project directory |
| `RAW_DIR` | Directory for storing raw API responses |
| `DB_PATH` | Location of the SQLite weather database |
| `LOG_DIR` | Directory for storing structured pipeline logs |
| `BASE_URL` | Open-Meteo API endpoint |
| `HOURLY_VARIABLES` | Weather variables requested from the API |
| `CITIES` | Configured UK cities and their geographical coordinates |

All seven pipeline configuration constants are defined in `extract.py`. The ETL module imports the shared database path, logging directory and extraction function rather than defining them again.

```python
from extract import DB_PATH, LOG_DIR, extract
```

This approach reduces configuration duplication, improves consistency and allows shared pipeline settings to be maintained in one location.

### Working Directory Independence

All pipeline storage paths are derived from `PROJECT_ROOT` using `pathlib`.

The project root is determined from the location of the Python module rather than the current working directory.

```python
PROJECT_ROOT = Path(__file__).resolve().parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
DB_PATH = PROJECT_ROOT / "weather.db"
LOG_DIR = PROJECT_ROOT / "logs"
```

This ensures that raw JSON files, the SQLite database and pipeline logs remain in their intended project locations even when the pipeline is executed from another directory.

### Configuration and Portability Validation

The centralised configuration was successfully validated on 24 November 2026.

| Validation check | Result |
|---|---|
| Shared pipeline configuration definitions | Passed |
| Shared module imports | Passed |
| Absolute project paths | Passed |
| Standalone extraction for five cities | Passed |
| Full ETL execution with 240 records | Passed |
| Execution from outside the project directory | Passed |
| Correct raw data, database and log locations | Passed |
| No pipeline files created in the home directory | Passed |
| Successful pipeline exit code | 0 |
| Database record count retained | 600 |
| Duplicate primary keys | 0 |
| Database integrity | Passed |

The portability test confirmed that the pipeline could run successfully from the user's home directory while storing all generated files inside the WeatherFlow project directory.

Repeated execution over the same observation window retained the database record count of 600 without creating duplicate primary keys.

The standalone historical migration utility, `scripts/migrate_utc.py`, retains independent project, database and backup paths so that it can operate separately from the normal weather extraction pipeline.

## Timestamp Handling

The pipeline uses three timestamp columns:

| Column | Description |
|---|---|
| `observed_at_utc` | Weather observation timestamp in UTC |
| `observed_at_local` | Weather observation timestamp in the Europe/London timezone |
| `ingested_at_utc` | Timestamp recording when the data was processed, in UTC |

UTC is used as the canonical observation timestamp to provide a consistent timeline and avoid ambiguity during daylight saving time transitions.

Example during British Summer Time:

| Timestamp | Example |
|---|---|
| UTC | `2026-07-15T12:00:00+00:00` |
| UK local | `2026-07-15T13:00:00+01:00` |

## Structured Logging

The pipeline uses Python's built-in logging module instead of print statements.

Log messages include:

- Execution timestamp
- Logging severity level
- Module name
- Descriptive message

Logs are displayed in the terminal and saved to:

```text
logs/pipeline.log
```

## API Retry and Failure Handling

The extraction process includes a retry mechanism to improve pipeline reliability when temporary API or network failures occur.

### Retry Policy

The `fetch_city()` function in `extract.py` makes one initial API request and allows up to three additional retries.

The default request timeout is 10 seconds.

| Error type | Retry behaviour |
|---|---|
| Request timeout | Retry |
| Connection error | Retry |
| HTTP 5xx server error | Retry |
| HTTP 4xx client error | Do not retry |

HTTP 4xx client errors are raised immediately because repeating the same invalid request is unlikely to resolve the problem.

### Exponential Backoff

Temporary failures are retried using exponential backoff, calculated as `2 ** attempt`.

| Request attempt | Waiting time before attempt |
|---|---|
| Initial request | None |
| Retry 1 | 1 second |
| Retry 2 | 2 seconds |
| Retry 3 | 4 seconds |

A maximum of four request attempts is permitted per city by default.

The total scheduled waiting time is seven seconds if all three retries are required, excluding the time spent making the API requests.

If all permitted attempts fail, the final request exception is raised.

### Partial and Complete Failure Handling

The `extract()` function returns two collections:

- Successful city extractions containing the city name and API response.
- Failed city names for which extraction could not be completed.

If an individual city fails, the pipeline continues attempting the remaining cities.

Successful city records are transformed and loaded into SQLite, even when another city fails. However, the overall pipeline execution reports failure.

If all cities fail, transformation and loading are skipped.

Existing database records are not deleted when a city extraction fails. However, previously stored observations for a failed city may become stale.

### Pipeline Exit Codes

The pipeline uses process exit codes to communicate execution status to external systems and future workflow schedulers.

| Exit code | Meaning |
|---|---|
| `0` | All configured cities were successfully processed |
| `1` | One or more city extractions failed |

A partial load does not represent a fully successful pipeline execution.

To run the pipeline and inspect its exit code in Git Bash, macOS or Linux:

```bash
python etl_v1.py
echo $?
```

In Windows PowerShell:

```powershell
python etl_v1.py
echo $LASTEXITCODE
```

Retry attempts, failed cities, extraction summaries and the final pipeline status are recorded in `logs/pipeline.log`.

This prevents incomplete weather data from being silently reported as a successful pipeline execution.

## Example Pipeline Output

### Successful Execution

The following log excerpt was recorded on 24 November 2026 after restoring the correct API endpoint:

```text
2026-11-24 03:52:15,438 | INFO | __main__ | Starting WeatherFlow ETL pipeline...
2026-11-24 03:52:15,438 | INFO | extract | Fetching weather for Birmingham...
2026-11-24 03:52:16,871 | INFO | extract | Extraction summary: 5 successful, 0 failed
2026-11-24 03:52:16,882 | INFO | __main__ | Transformed records: 240
2026-11-24 03:52:16,893 | INFO | __main__ | Loaded 240 rows into weather.db
2026-11-24 03:52:16,893 | INFO | __main__ | Total rows in database: 600
2026-11-24 03:52:16,893 | INFO | __main__ | WeatherFlow ETL pipeline completed successfully!
```

Process exit code: `0`.

The total database record count depends on the existing data and the number of overlapping observation timestamps.

### Failed Execution

The following log excerpt was recorded during a deliberately incorrect API endpoint test on 24 November 2026:

```text
2026-11-24 03:49:10,518 | INFO | extract | Extraction summary: 0 successful, 5 failed
2026-11-24 03:49:10,518 | WARNING | etl_v1 | No successful extractions. Skipping transformation and loading.
2026-11-24 03:49:10,518 | ERROR | etl_v1 | Run FAILED: no data for Birmingham, Cardiff, Edinburgh, London, Manchester
```

Process exit code: `1`.

The incorrect endpoint returned HTTP 404 errors for all five cities. No retries were performed because HTTP 404 is a client error.

The incorrect endpoint was temporarily configured in memory without permanently modifying the source code.

The original database remained unchanged, as verified by matching SHA-256 checksums before and after the failed execution.

A subsequent execution using the correct API endpoint successfully processed all five cities and returned exit code `0`.

## Database Schema

The `weather_hourly` table contains ten columns:

| Column | SQLite Type |
|---|---|
| `city` | TEXT |
| `observed_at_utc` | TEXT |
| `observed_at_local` | TEXT |
| `temperature_c` | REAL |
| `feels_like_c` | REAL |
| `humidity_pct` | INTEGER |
| `precipitation_mm` | REAL |
| `wind_speed_kmh` | REAL |
| `weather_code` | INTEGER |
| `ingested_at_utc` | TEXT |

Composite primary key:

```text
(city, observed_at_utc)
```

Detailed column definitions are available in `docs/data_dictionary.md`.

## Database Migration

The original database schema used a timezone-naive `observed_at` column.

The migration script, `scripts/migrate_utc.py`, was developed to convert existing records to the new timezone-aware schema while preserving historical weather measurements.

The migration process included:

- Creating a SQLite database backup.
- Validating database integrity.
- Converting existing UK local timestamps to UTC.
- Creating a staging table with the updated schema.
- Migrating records within a database transaction.
- Validating record counts and database integrity.
- Rolling back transactional changes if an error occurs.
- Comparing migrated data against the original backup.

The migration was successfully tested on a disposable database copy before being applied to the original database.

All 480 existing records were preserved, with no data mismatches detected during reconciliation.

The migration script is intended only for databases using the legacy schema. It is not required for a fresh installation or a database that has already been migrated.

Before migrating a legacy database, create and validate a backup at:

```text
data/backups/weather_before_utc_migration.db
```

The migration command is:

```bash
python scripts/migrate_utc.py
```

Do not execute the migration again on an already migrated database.

## Data Validation and Idempotency

The updated pipeline was successfully tested on 24 November 2026.

### Database Quality Validation

| Validation metric | Result |
|---|---|
| Cities successfully processed | 5 |
| Hourly records per city per run | 48 |
| Records processed per successful run | 240 |
| Historical records preserved during migration | 480 |
| Total database records after updated pipeline run | 600 |
| Stored records per city | 120 |
| Duplicate primary keys | 0 |
| Missing mandatory values | 0 |
| Invalid or inconsistent observation timestamps | 0 |
| Composite primary key validation | Passed |
| Database integrity | Passed |
| Migration data reconciliation | Passed |
| Record-count idempotency test | Passed |

Running the pipeline again over the same observation window retained the total database record count of 600, with zero duplicate primary keys.

Existing weather measurements and ingestion timestamps may be updated when overlapping records are processed.

### Retry Mechanism Validation

The retry mechanism was tested using Python's `unittest.mock` module to simulate temporary and permanent API failures.

| Test scenario | Verified behaviour | Result |
|---|---|---|
| Temporary request timeout | Successful retry | Passed |
| Temporary connection error | Successful retry | Passed |
| HTTP 503 server error | Successful retry | Passed |
| Multiple transient failures | Backoff intervals of 1, 2 and 4 seconds | Passed |
| Persistent request timeout | Maximum of four attempts followed by an exception | Passed |
| HTTP 404 client error | Immediate exception without retries | Passed |

Mocked waiting functions were used to verify the scheduled exponential backoff intervals without introducing unnecessary delays during testing.

### Pipeline Integration Testing

| Test scenario | Successful cities | Records loaded | Pipeline exit code | Result |
|---|---:|---:|---:|---|
| Normal operation | 5 | 240 | 0 | Passed |
| Simulated partial city failure | 4 | 192 | 1 | Passed |
| Simulated complete city failure | 0 | 0 | 1 | Passed |
| Real incorrect API endpoint | 0 | 0 | 1 | Passed |
| Successful recovery | 5 | 240 | 0 | Passed |

The simulated integration tests used temporary directories and disposable SQLite databases to protect the original project data.

The partial failure test simulated a persistent extraction failure for Cardiff while allowing the remaining four cities to complete successfully.

The complete failure test confirmed that raw data saving, transformation and loading were skipped when all five cities failed.

The incorrect API endpoint test made real HTTP requests and confirmed that the pipeline reported failure with an actual process exit code of `1`.

SHA-256 checksum comparisons confirmed that the original database remained unchanged during the failure tests.

After restoring normal operation, the final database validation confirmed that all 600 records remained available, with no duplicate primary keys, missing mandatory values, inconsistent observation timestamps or SQLite integrity errors.

These results demonstrate that the pipeline can recover from temporary API failures, report unsuccessful executions accurately and preserve existing database records.

## SQL Analysis

SQL queries are available in `sql/week1_queries.sql`.

The queries answer three business questions:

1. How many weather records are available for each city, and what are the earliest and latest UTC observation times?
2. What was the average temperature in each city yesterday, based on the UK local calendar date?
3. What were the five windiest hours across all cities, including UTC and UK local observation timestamps?

The second query assumes that the computer's local timezone is set to UK time.

All three queries were successfully executed against the migrated `weather_hourly` table.

## Data Storage

- Raw API responses are stored as JSON files under `data/raw/`.
- Database backups are stored under `data/backups/`.
- Transformed weather records are stored in the SQLite database `weather.db`.
- Structured pipeline logs are stored under `logs/`.
- Absolute project paths ensure that runtime files are stored in their intended locations.
- Raw data, database files, backups, logs and virtual environments are excluded from Git using `.gitignore`.

## Author

Pooja Lihal

## Week 2 — Modular WeatherFlow Pipeline

WeatherFlow has been refactored into a modular Python package using a `src/` layout.

### Run the pipeline

```bash
python -m weatherflow run
```

### Run automated tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

### Configuration

Pipeline settings are stored in `config.yaml`, including API endpoints, city coordinates, retry settings and storage paths.

### Package modules

- `config.py` — Configuration loading and validation.
- `extract.py` — API extraction, exponential backoff and raw JSON storage.
- `transform.py` — Data cleaning and standardisation.
- `load.py` — Idempotent SQLite loading.
- `pipeline.py` — ETL orchestration.
- `__main__.py` — Command-line interface and logging.

### Pipeline outputs

- Raw JSON: `data/raw/`
- SQLite database: `data/weather.db`
- Pipeline logs: `logs/pipeline.log`

### Validation

- Successful pipeline execution from the project root and its parent directory.
- 240 hourly weather records across five UK cities.
- No increase in database row count when repeating the same extraction window.
- Nine passing automated configuration and retry tests.

The original Week 1 scripts and database are retained for historical reference.

#### Task 2.2 Validation Results

Validation date: 25 November 2026.

| Validation metric | Result |
|---|---|
| Automated tests | 34 passed |
| Pipeline exit code | 0 |
| Processed records | 240 |
| Processed columns | 19 |
| Cities | 5 |
| Records per city | 48 |
| Duplicate records | 0 |
| Missing daylight values | 0 |
| Low outdoor work risk | 236 |
| Medium outdoor work risk | 4 |
| High outdoor work risk | 0 |
| Daylight records | 84 |
| Nighttime records | 156 |

#### CSV vs Parquet Comparison

The same 240-row, 19-column dataset was stored in both formats.

| File format | Size in bytes |
|---|---:|
| CSV | 44,386 |
| Parquet (Snappy compression) | 16,395 |

Parquet reduced storage size by 63.06%, saving 27,991 bytes.

Parquet also preserves column data types and supports efficient
column-level reading for analytical workloads.

The measured storage reduction applies to this particular dataset.

### Task 2.2 — Implementation Overview

The transformation layer consists of five independently
testable functions:

- flatten_payload
- standardise_columns
- add_weather_description
- add_derived_metrics
- deduplicate

Derived metrics include Fahrenheit temperature, wind speed
in metres per second, Beaufort scale, daylight status and
outdoor work risk.

Weather descriptions are mapped using the WMO reference CSV.

Processed Parquet files are stored under:

data/processed/weather_hourly/run_date=YYYY-MM-DD/

The storage module handles reference data loading and
Parquet writing separately from the pure transformations.

Metric definitions and formulas are documented in
docs/data_dictionary.md.

### Task 2.3 — Star Schema and Idempotent Load

WeatherFlow now uses a dimensional database model consisting
of three tables:

- dim_city
- dim_date
- fact_weather_hourly

Grain: one row per city, per hour, per source.

The fact table uses a composite primary key and foreign keys
to maintain uniqueness and referential integrity.

All enriched weather metrics are stored in the fact table.

The date dimension uses the Europe/London local calendar date.

Database loads use transactional upserts to prevent duplicates
and roll back all database changes if an error occurs.

The city metadata, date dimension range and schema location
are configured in config.yaml.

Database schema:

sql/schema.sql

Entity Relationship Diagram:

docs/erd.md

Analytical SQL queries:

sql/analysis_queries.sql

Run the pipeline:

```bash
python -m weatherflow run
```

Run automated tests:

```bash
python -m pytest tests/ -v
```

The original weather_hourly table is preserved for historical
reference. New records are loaded into fact_weather_hourly.

#### Task 2.3 Validation Results

Validation date: 26 November 2026.

| Validation metric | Result |
|---|---|
| Automated tests | 41/41 passed |
| Test execution time | 0.91 seconds |
| Live pipeline run 1 | 240 fact records |
| Live pipeline run 2 | 240 fact records |
| Live pipeline run 3 | 240 fact records |
| City dimension records | 5 |
| Date dimension records | 1,095 |
| Duplicate fact keys | 0 |
| Foreign key violations | 0 |
| Database integrity | ok |
| Preserved legacy records | 240 |
| Transaction rollback test | Passed |
| Separate weather sources test | Passed |
| UK local calendar date test | Passed |
| Analytical SQL queries | 5/5 passed |

All three live pipeline executions maintained identical
fact row counts, demonstrating record-count idempotency.

Atomicity was verified by forcing a constraint violation
after successful writes in a temporary database.
All preceding fact and dimension changes were rolled back.

#### Analytical Query Results

| Query | Result rows |
|---|---:|
| Record counts by city | 5 |
| Yesterday's average temperature | 5 |
| Five windiest hours | 5 |
| Weekday versus weekend wind speed | 5 |
| Outdoor work risk by city and date | 10 |

The observation window covers 25-26 November 2026.

Query 4 currently returns weekday observations only.
Weekend comparisons will become available when historical
data is loaded during Task 2.6.

### Task 2.4 — Data Quality Checks and Quarantine

WeatherFlow includes a configurable data quality validation
gate between transformation and database loading.

Eight validation checks cover five data quality dimensions:

- Completeness
- Validity
- Uniqueness
- Timeliness
- Consistency

| Check | Severity |
|---|---|
| Mandatory fields | Quarantine |
| Temperature range | Quarantine |
| Humidity range | Quarantine |
| Non-negative precipitation and wind speed | Quarantine |
| Duplicate observation keys | Fail |
| Expected hourly coverage | Fail |
| Observation freshness | Warn |
| Feels-like temperature consistency | Warn |

Thresholds are defined in config.yaml under data_quality.

Invalid rows are written to partitioned Parquet files under:

data/quarantine/run_date=YYYY-MM-DD/

Each quarantined row contains a dq_failure_reason field.

Blocking checks raise DataQualityError and prevent the
database load.

Warning checks are recorded without blocking valid data.

Hourly coverage is evaluated before quarantine so that
invalid measurements can be isolated without automatically
causing a missing-hour failure.

Duplicate observations are retained during transformation
until the uniqueness validation has been performed.

Only validated records reach processed Parquet storage
and the analytical database.

Data quality reports are generated under:

docs/dq_reports/

Reports include check results, severity, affected record
counts, quarantined records and loaded records.

Generated reports are excluded from Git.

The timeliness check applies to incremental runs and
ignores future forecast observations. Incremental extraction
will be introduced in Task 2.6.

Run the pipeline:

```bash
python -m weatherflow run
```

Run the automated tests:

```bash
python -m pytest tests/ -v
```

The automated tests include deliberately invalid temperatures,
duplicate observations, missing hourly records, freshness
warnings and extraction failures.
