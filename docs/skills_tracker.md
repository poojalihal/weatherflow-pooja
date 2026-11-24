# WeatherFlow — Skills Tracker

## Week 1: Python, Git, APIs and ETL Fundamentals

**Initial assessment:** 23 November 2026

**Last updated:** 24 November 2026

**Self-assessment scale:**
- Beginner — Learning the fundamentals and requiring guidance.
- Developing — Able to complete basic tasks with occasional guidance.
- Confident — Able to complete tasks independently.

## Core Technical Skills

| Skill | Current Level | Evidence of Learning | Next Steps |
|---|---|---|---|
| Python | Beginner | Created and improved Python scripts for weather data extraction, transformation and loading. | Practise functions, exception handling, type hints and reusable code independently. |
| Git & GitHub | Developing | Created a GitHub repository, committed changes, pushed updates and reviewed changes using Git diff commands. | Practise branching, pull requests and code reviews. |
| APIs | Developing | Retrieved weather data for five UK cities using Open-Meteo and implemented request timeouts and retry handling with guidance. | Practise API response validation, pagination and rate-limit handling. |
| ETL Pipelines | Developing | Built and improved an ETL pipeline that processes 240 hourly weather records during a successful execution. | Practise pipeline orchestration, scheduling and automated monitoring. |
| SQL & SQLite | Developing | Created SQL queries, implemented a composite primary key and validated database integrity and record counts. | Practise joins, window functions, aggregations and database design. |
| Pandas | Beginner | Used Pandas to explore, transform, deduplicate and convert weather timestamps. | Practise data cleaning, missing-value handling and schema validation. |
| Jupyter Notebook | Beginner | Created a notebook to explore weather data. | Improve visualisations and document analytical findings. |
| Virtual Environments | Developing | Created Python virtual environments, separated runtime and development dependencies and verified package compatibility. | Practise reproducible dependency management across operating systems. |
| Debugging | Developing | Investigated package installation issues, API failures, database migration problems and pipeline execution behaviour with guidance. | Improve independent debugging and systematic root-cause analysis. |
| Technical Documentation | Developing | Created and updated the README, data dictionary, skills tracker and Week 1 reflection. | Improve concise technical explanations and maintain documentation alongside code changes. |

## Pipeline Reliability and Software Engineering

| Skill | Current Level | Evidence of Learning | Next Steps |
|---|---|---|---|
| Python Exception Handling | Beginner | Implemented handling for request timeouts, connection errors and HTTP exceptions. | Practise custom exceptions and exception handling in other Python applications. |
| Modular Programming | Beginner | Centralised API extraction logic in extract.py and reused it in etl_v1.py. | Practise separating configuration, business logic and reusable functions. |
| API Resilience | Beginner | Implemented and tested recovery from temporary network and server failures. | Explore rate limiting, retry policies and response validation. |
| Exponential Backoff | Beginner | Implemented a maximum of three retries with waiting intervals of 1, 2 and 4 seconds. | Explore configurable retry policies and randomised backoff intervals. |
| HTTP Status Codes | Beginner | Distinguished retryable HTTP 5xx server errors from non-retryable HTTP 4xx client errors. | Learn additional HTTP status codes and API-specific error-handling requirements. |
| Structured Logging | Beginner | Replaced print statements with timestamped logging and persistent log files. | Practise logging configuration, log rotation and monitoring. |
| Process Exit Codes | Beginner | Implemented exit code 0 for successful execution and exit code 1 when city extraction fails. | Learn how workflow schedulers use process exit codes. |
| Partial Failure Handling | Beginner | Loaded successful city records while reporting an overall pipeline failure when another city failed. | Explore failed-record tracking, recovery workflows and data freshness monitoring. |
| Project Path Management | Beginner | Used pathlib and PROJECT_ROOT to make file locations independent of the current working directory. | Practise portable configuration and environment-specific settings. |

## Data Quality and Database Management

| Skill | Current Level | Evidence of Learning | Next Steps |
|---|---|---|---|
| Timezone-Aware Data Processing | Beginner | Converted weather observations to UTC and derived UK local timestamps using Europe/London. | Practise daylight saving time edge cases and timezone-aware SQL analysis. |
| Database Migration | Beginner | Migrated 480 historical weather records to an updated timezone-aware schema with guidance. | Practise schema evolution and repeatable database migration strategies. |
| Database Backup and Recovery | Beginner | Created SQLite backups and tested migration on a disposable database copy before updating the original database. | Practise automated backup and recovery procedures. |
| Database Transactions | Beginner | Used transactional migration and rollback handling to protect existing records. | Learn transaction isolation and atomic database operations. |
| Data Quality Validation | Developing | Validated record counts, city coverage, mandatory fields, duplicate keys and observation timestamp consistency. | Implement reusable and automated data quality checks. |
| Database Integrity | Beginner | Used SQLite PRAGMA integrity_check and verified the composite primary key definition. | Practise database constraints and integrity monitoring. |
| Record-Count Idempotency | Beginner | Verified that repeated pipeline runs over the same observation window retained 600 records without introducing duplicates. | Explore incremental loading and stronger idempotency guarantees. |
| Data Reconciliation | Beginner | Compared migrated records against the original database backup and verified that all 480 historical records were preserved. | Practise source-to-target reconciliation across different data systems. |

## Testing and Verification

| Skill | Current Level | Evidence of Learning | Next Steps |
|---|---|---|---|
| Mock Testing | Beginner | Used unittest.mock, patch, Mock and call to simulate API failures and verify retry behaviour. | Write reusable automated unit tests using pytest. |
| Integration Testing | Beginner | Tested normal execution, partial failure, complete failure and successful pipeline recovery. | Build a repeatable automated integration test suite. |
| Test Isolation | Beginner | Used temporary directories and disposable SQLite databases to protect original project data during failure testing. | Practise pytest fixtures and isolated test environments. |
| Failure Recovery Testing | Beginner | Tested a deliberately incorrect API endpoint, verified exit code 1 and restored successful operation with exit code 0. | Explore automated recovery and failure alerting. |
| Checksum Verification | Beginner | Compared SHA-256 database checksums before and after failure tests to verify that the original database remained unchanged. | Explore file integrity verification in data ingestion workflows. |
| Dependency Validation | Developing | Verified installed packages using pip check, import tests and isolated virtual environments. | Practise dependency testing in continuous integration workflows. |

## Week 1 Reflection on Skills Development

During Week 1, I developed a foundational understanding of data engineering by working on a practical weather data pipeline.

As data engineering is a new field for me, I needed additional time and guidance to understand the tools, commands and development workflow. By following the project instructions and troubleshooting issues, I gained experience with Python, Git, APIs, ETL processing and SQLite.

My initial achievement was successfully running an end-to-end ETL pipeline that processed 240 hourly weather records across five UK cities.

## Learning Through Week 1 Feedback

Following the Week 1 feedback, I worked on improving the reliability, portability, maintainability and data quality of the WeatherFlow pipeline.

I improved dependency management, introduced structured logging, implemented project-root paths and converted weather observation timestamps to a timezone-aware UTC format.

I also migrated 480 existing weather records to the updated database schema and verified that all historical records were preserved.

To improve pipeline reliability, I implemented API timeouts, exception handling, exponential backoff and failed city tracking.

I learned that a pipeline can successfully load some records while still representing an unsuccessful overall execution. This is particularly important because incomplete or stale data could otherwise be incorrectly presented as reliable information.

I tested temporary API failures, persistent timeouts, HTTP client and server errors, partial failures and complete failures using mock testing and isolated integration tests.

The final database validation confirmed:

- 600 stored weather records.
- 120 records for each of the five UK cities.
- Zero duplicate primary key groups.
- Zero missing mandatory values.
- Zero invalid or inconsistent observation timestamps.
- Successful SQLite database integrity verification.

These improvements helped me understand that data engineering involves not only moving and transforming data but also ensuring that pipelines are reliable, observable, testable and capable of reporting failures accurately.

Although I have gained practical experience with these concepts, I still need further practice to implement them independently and confidently.

## Goals for Week 2

1. Improve independent Python programming and modular code organisation.
2. Develop reusable automated unit tests using pytest.
3. Improve automated data quality and API response validation.
4. Explore pipeline scheduling, orchestration and monitoring.
5. Improve SQL querying, database design and incremental loading.
6. Practise Git branching, pull requests and code reviews.
7. Strengthen understanding of timezone handling and daylight saving time.
8. Improve data visualisation and analytical findings.
9. Become more confident debugging and implementing data engineering solutions independently.
10. Maintain accurate technical documentation as the project evolves.
