# WeatherFlow – Data Engineering Project

## Project Overview

WeatherFlow is a data engineering project that collects weather data for five UK cities using the Open-Meteo API.

The project implements an ETL (Extract, Transform, Load) pipeline that retrieves weather information, stores the original raw data, transforms it into a structured format and loads the results into a SQLite database for SQL analysis.

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
- VS Code

## Project Structure

```text
weatherflow-pooja/
├── data/
│   └── raw/
├── docs/
│   ├── reference_critique.md
│   ├── reference_architecture.md
│   └── data_dictionary.md
├── notebooks/
│   └── 01_explore.ipynb
├── sql/
│   └── week1_queries.sql
├── extract.py
├── etl_v1.py
├── requirements.txt
├── README.md
├── .gitignore
└── weather.db
```

## How to Set Up

1. Clone this repository.
2. Open the project folder in VS Code.
3. Create a Python virtual environment:

   ```bash
   python -m venv .venv
   ```

4. Activate the virtual environment (Git Bash on Windows):

   ```bash
   source .venv/Scripts/activate
   ```

5. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## How to Run the ETL Pipeline

Run the following command from the project root directory:

```bash
python etl_v1.py
```

The pipeline performs three main stages:

### 1. Extract

- Fetches hourly weather data from the Open-Meteo API for five UK cities.
- Saves the complete API responses as raw JSON files.
- Stores raw files in `data/raw/`, organised by extraction date.

### 2. Transform

- Converts observation timestamps into datetime format.
- Renames columns to include measurement units.
- Adds city and ingestion timestamp information.
- Removes duplicate records using city and observation time.

### 3. Load

- Loads the transformed weather records into the SQLite database.
- Creates the `weather_hourly` table if it does not already exist.
- Uses `(city, observed_at)` as the primary key.
- Uses `INSERT OR REPLACE` to support repeated pipeline runs without creating duplicate city/time records.

## Example Pipeline Output

A successful pipeline execution produces output similar to:

```text
Starting WeatherFlow ETL pipeline...

Fetching weather for Birmingham...
Success: Birmingham - 48 hourly records saved

Fetching weather for Cardiff...
Success: Cardiff - 48 hourly records saved

Fetching weather for Edinburgh...
Success: Edinburgh - 48 hourly records saved

Fetching weather for London...
Success: London - 48 hourly records saved

Fetching weather for Manchester...
Success: Manchester - 48 hourly records saved

Transformed records: 240
Loaded 240 rows into weather.db

WeatherFlow ETL pipeline completed successfully!
```

**Data validation:**
- Total records processed: 240
- Cities covered: 5
- Records per city: 48
- Missing values in the explored dataset: 0
- Duplicate city/time records: 0

## SQL Analysis

SQL queries are available in `sql/week1_queries.sql`.

The queries answer three business questions:

1. How many weather records are available for each city, and what are the earliest and latest observation times?
2. What was the average temperature in each city yesterday?
3. What were the five windiest hours across all cities?

The queries are executed against the `weather_hourly` table in `weather.db`.

## Data Storage

- Raw API responses are stored as JSON files under `data/raw/`.
- Transformed weather records are stored in the SQLite database `weather.db`.
- Raw data and database files are excluded from Git using `.gitignore`.

## Author

Pooja Lihal
