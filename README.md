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
- Saves the complete API responses as raw JSON files.
- Stores raw files in `data/raw/`, organised by extraction date.

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

## Example Pipeline Output

A successful pipeline execution produces structured log messages similar to:

```text
2026-11-24 01:44:05,055 | INFO | __main__ | Starting WeatherFlow ETL pipeline...
2026-11-24 01:44:05,057 | INFO | __main__ | Fetching weather for Birmingham...
2026-11-24 01:44:06,801 | INFO | __main__ | Transformed records: 240
2026-11-24 01:44:06,811 | INFO | __main__ | Loaded 240 rows into weather.db
2026-11-24 01:44:06,812 | INFO | __main__ | Total rows in database: 600
2026-11-24 01:44:06,812 | INFO | __main__ | WeatherFlow ETL pipeline completed successfully!
```

The total database record count depends on the existing data and the number of overlapping observation timestamps.

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

| Validation metric | Result |
|---|---|
| Cities successfully processed | 5 |
| Hourly records per city per run | 48 |
| Records processed per run | 240 |
| Historical records preserved during migration | 480 |
| Total database records after updated pipeline run | 600 |
| Duplicate primary keys | 0 |
| Database integrity | Passed |
| Migration data reconciliation | Passed |
| Record-count idempotency test | Passed |

Running the pipeline again over the same observation window retained the total database record count of 600, with zero duplicate primary keys.

Existing weather measurements and ingestion timestamps may be updated when overlapping records are processed.

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
