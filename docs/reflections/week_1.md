# Week 1 Reflection — WeatherFlow

## What I built

- Created my WeatherFlow project repository on GitHub and configured the project structure, virtual environment, `.gitignore`, and dependency files.
- Studied the reference WeatherFlow project and documented its architecture and limitations.
- Developed `extract.py` to retrieve weather data from the Open-Meteo API for five UK cities.
- Created a Jupyter notebook to explore weather data and understand its structure.
- Developed `etl_v1.py` to extract, transform, and load weather records into an SQLite database.
- Successfully processed 240 hourly weather records across five UK cities.
- Created SQL queries to analyse the stored weather data.
- Improved dependency management by replacing the original frozen `requirements.txt` with a smaller, cross-platform dependency list and creating `requirements-dev.txt`.

## What went well

- Successfully configured Python, Git, GitHub, VS Code, and the project environment.
- Connected to the Open-Meteo API and retrieved weather data for all five cities.
- Built and executed an end-to-end ETL pipeline.
- Successfully loaded 240 weather records into SQLite.
- Verified that the ETL pipeline could be rerun without creating duplicate records.
- Learned how to use Git commands to track changes, commit updates, and push them to GitHub.

## What was hard, and how I solved it

1. **Understanding Git and project structure.** As a beginner in data engineering, I initially found repository organisation, Git commands, and file paths challenging. I worked through the instructions step by step and verified the results in Git Bash.

2. **Managing Python dependencies.** My original `requirements.txt` contained unnecessary packages and Windows-specific dependencies. I replaced it with a smaller list of project dependencies, created a separate development requirements file, and tested package installation in a fresh virtual environment.

3. **Understanding the ETL process.** Initially, I found it challenging to understand how extraction, transformation, and loading work together. Building and running the pipeline helped me understand how API responses become structured records in an SQLite database.

4. **Troubleshooting installation problems.** During dependency testing, I encountered package installation and compatibility issues. I used `python -m pip`, installed a missing compatible dependency in the test environment, and verified the installation using `pip check` and Python import tests.

## What surprised me

- A single API extraction could generate 240 hourly records across five cities.
- Running an ETL pipeline more than once does not necessarily create duplicates when the database loading logic is designed correctly.
- A `requirements.txt` file generated automatically with `pip freeze` can contain unnecessary dependencies and cause compatibility problems on other operating systems.
- Git and GitHub are useful not only for storing code but also for tracking the development and improvement of a project.

## Learning Through Week 1 Feedback

**Date:** 24 November 2026

After receiving feedback on my Week 1 deliverables, I worked on improving the reliability, portability, maintainability and data quality of my WeatherFlow pipeline.

### What I improved

- Replaced print statements with structured logging and persistent log files to make pipeline execution easier to monitor and troubleshoot.
- Used `pathlib` and `PROJECT_ROOT` to ensure that the pipeline could run from different working directories.
- Updated the pipeline to request weather observations in UTC and retain timezone-aware UTC and UK local timestamps.
- Migrated 480 historical weather records to the updated SQLite database schema without losing existing records.
- Implemented a composite primary key using `city` and `observed_at_utc` to prevent duplicate observations.
- Updated the SQL queries, README and data dictionary to reflect the revised database schema.
- Centralised API extraction logic in `extract.py` to avoid duplicated code.
- Centralised seven shared pipeline configuration constants in `extract.py`, including project paths, the API endpoint, hourly weather variables and city configuration.
- Updated `etl_v1.py` to import shared database and logging paths from `extract.py`, reducing duplicated configuration and improving maintainability.
- Implemented request timeouts, exception handling and exponential backoff with retry intervals of 1, 2 and 4 seconds.
- Added failed city tracking and process exit codes to ensure that unsuccessful pipeline executions are reported accurately.

### What went well during the improvements

I successfully tested the pipeline under normal operating conditions and different failure scenarios.

Using Python's `unittest.mock` module, I simulated temporary request timeouts, connection errors, HTTP 503 server errors and persistent failures. I verified that temporary failures were retried and that HTTP 404 client errors were not retried.

I also tested partial and complete pipeline failures using temporary directories and disposable SQLite databases.

The partial failure test successfully loaded 192 records from four cities while returning exit code 1 because Cardiff had failed.

The complete failure test confirmed that transformation and loading were skipped when all five cities failed.

I tested a deliberately incorrect API endpoint and confirmed that the pipeline returned exit code 1. After restoring the correct endpoint, the pipeline successfully processed all five cities and returned exit code 0.

I successfully validated the centralised pipeline configuration through syntax checks, module import checks, standalone extraction and full ETL execution.

I also tested the pipeline from outside the project directory by running it from my home directory. All five cities were successfully processed, 240 weather records were transformed and loaded, and the pipeline returned exit code 0.

I verified that the raw JSON files, SQLite database and persistent logs remained inside the WeatherFlow project directory. No pipeline-generated files were created in my home directory.

### What was challenging, and how I addressed it

**Understanding timezone-aware timestamps**

I initially found it challenging to understand the difference between UTC, local time and timezone offsets. By working through timestamp conversion and database migration step by step, I learned why UTC provides a consistent reference for storing weather observations and why local timestamps remain useful for business analysis.

**Protecting existing database records**

Changing the database schema required careful planning because I did not want to lose previously collected weather data. I created a database backup, tested the migration on a separate database copy and reconciled the migrated records against the original data before updating the project database.

**Understanding API retries and exception handling**

I needed guidance to understand which API failures should be retried and how exponential backoff works. Implementing and testing the retry mechanism helped me understand the difference between temporary network or server failures and client errors that require corrective action.

**Understanding partial pipeline failures**

One of the most important concepts I learned was that successfully loading some records does not necessarily mean that the entire pipeline has succeeded.

If one city fails, the remaining cities can still be processed, but the overall pipeline must report failure. Otherwise, a downstream dashboard or scheduler could incorrectly treat incomplete or stale weather data as reliable.

**Testing without damaging existing data**

I learned how to use mock objects, temporary directories and disposable databases to test failure scenarios safely. I also used SHA-256 checksum comparisons to verify that the original database remained unchanged during failure testing.

**Understanding centralised configuration and modular programming**

I learned that defining the same configuration settings in multiple Python files can make a project harder to maintain and increase the risk of inconsistent behaviour.

By centralising shared constants in `extract.py` and importing them into `etl_v1.py`, I gained a better understanding of how Python modules can share configuration and reusable functionality.

I also learned the difference between the current working directory and the directory containing a Python script. Using `pathlib`, `__file__` and absolute project paths helped me understand how to make a pipeline portable across different working directories.

I reviewed the standalone database migration utility and learned that configuration centralisation should also consider module dependencies and the purpose of individual scripts. The migration utility retained its independent paths because it performs a separate historical database maintenance task.

### Evidence of successful improvements

The final database validation confirmed:

- 600 stored weather records across five UK cities.
- 120 stored records per city.
- All 480 historical records preserved during migration.
- Zero duplicate primary key groups.
- Zero missing mandatory values.
- Zero invalid or inconsistent observation timestamps.
- Successful SQLite database integrity verification.
- Successful record-count idempotency verification.
- Successful API retry and failure-handling tests.
- Successful validation of seven shared pipeline configuration constants.
- Successful syntax and shared module import checks.
- Successful standalone extraction and full ETL execution after configuration centralisation.
- Successful pipeline execution from outside the project directory.
- Correct storage of raw JSON files, SQLite database and persistent logs within the project directory.
- No pipeline-generated files created in the home directory.
- Database record count retained at 600 after repeated execution over the same observation window.

### What surprised me during the improvements

I was surprised by how much additional work is required to make a basic ETL pipeline reliable.

Initially, I focused mainly on retrieving, transforming and loading weather data. Through the feedback, I learned that a reliable data pipeline must also handle failures, protect existing data, maintain consistent timestamps, provide useful logs and communicate its execution status accurately.

I also learned that testing unsuccessful scenarios is just as important as testing successful executions.

### What I want to improve next

Although I have gained practical experience with these concepts, I still require guidance when implementing more complex data engineering solutions.

My next goals are to:

- Improve my independent Python programming and debugging skills.
- Develop reusable automated tests using pytest.
- Implement automated data quality and API response validation.
- Learn more about pipeline scheduling, orchestration and monitoring.
- Improve my SQL and database design skills.
- Practise Git branching, pull requests and code reviews.
- Strengthen my understanding of timezone handling and daylight saving time.

Working through the Week 1 feedback has helped me develop a better understanding of the responsibilities involved in building reliable data engineering pipelines. I want to continue practising these concepts until I can implement and troubleshoot them more independently.
