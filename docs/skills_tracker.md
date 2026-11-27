# WeatherFlow — Skills Tracker

## Week 1: Python, Git, APIs and ETL Fundamentals

**Initial assessment:** 23 November 2026

**Last updated:** 27 November 2026

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
| Modular Programming | Beginner | Centralised API extraction logic and seven shared pipeline configuration constants in extract.py. Reused the extraction function and shared database and logging paths in etl_v1.py. | Practise separating configuration, business logic and reusable functions into appropriate Python modules. |
| API Resilience | Beginner | Implemented and tested recovery from temporary network and server failures. | Explore rate limiting, retry policies and response validation. |
| Exponential Backoff | Beginner | Implemented a maximum of three retries with waiting intervals of 1, 2 and 4 seconds. | Explore configurable retry policies and randomised backoff intervals. |
| HTTP Status Codes | Beginner | Distinguished retryable HTTP 5xx server errors from non-retryable HTTP 4xx client errors. | Learn additional HTTP status codes and API-specific error-handling requirements. |
| Structured Logging | Beginner | Replaced print statements with timestamped logging and persistent log files. | Practise logging configuration, log rotation and monitoring. |
| Process Exit Codes | Beginner | Implemented exit code 0 for successful execution and exit code 1 when city extraction fails. | Learn how workflow schedulers use process exit codes. |
| Partial Failure Handling | Beginner | Loaded successful city records while reporting an overall pipeline failure when another city failed. | Explore failed-record tracking, recovery workflows and data freshness monitoring. |
| Project Path Management | Beginner | Used pathlib, __file__ and PROJECT_ROOT to centralise RAW_DIR, DB_PATH and LOG_DIR. Successfully executed the ETL pipeline from outside the project directory and verified that all generated files remained in their intended project locations. | Practise portable configuration, environment-specific settings and cross-platform path management. |

## Data Quality and Database Management

| Skill | Current Level | Evidence of Learning | Next Steps |
|---|---|---|---|
| Timezone-Aware Data Processing | Beginner | Converted weather observations to UTC and derived UK local timestamps using Europe/London. | Practise daylight saving time edge cases and timezone-aware SQL analysis. |
| Database Migration | Beginner | Migrated 480 historical weather records to an updated timezone-aware schema with guidance. | Practise schema evolution and repeatable database migration strategies. |
| Database Backup and Recovery | Beginner | Created SQLite backups and tested migration on a disposable database copy before updating the original database. | Practise automated backup and recovery procedures. |
| Database Transactions | Beginner | Used transactional migration and rollback handling to protect existing records. | Learn transaction isolation and atomic database operations. |
| Data Quality Validation | Developing | Validated record counts, city coverage, mandatory fields, duplicate keys and observation timestamp consistency. Confirmed that configuration centralisation preserved 600 database records with zero duplicate primary keys and successful database integrity verification. | Implement reusable and automated data quality checks, including regression testing after pipeline changes. |
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

I further improved pipeline maintainability by centralising seven shared configuration constants in `extract.py` and importing the shared database and logging paths into `etl_v1.py`.

Through this improvement, I learned how Python modules can share configuration and reusable functionality without duplicating definitions.

I validated the configuration through syntax checks, module import checks, standalone extraction and full ETL execution.

I also successfully executed the pipeline from my home directory. All five cities were processed, 240 records were transformed and loaded, and the pipeline returned exit code 0.

I verified that raw JSON files, the SQLite database and persistent logs remained inside the project directory. The database record count remained at 600, with no duplicate primary keys.

Reviewing the standalone database migration utility also helped me understand the importance of considering module dependencies and the purpose of individual scripts when making configuration management decisions.

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

1. Improve independent Python programming, modular code organisation and centralised configuration management.
2. Develop reusable automated unit tests using pytest.
3. Improve automated data quality and API response validation.
4. Explore pipeline scheduling, orchestration and monitoring.
5. Improve SQL querying, database design and incremental loading.
6. Practise Git branching, pull requests and code reviews.
7. Strengthen understanding of timezone handling and daylight saving time.
8. Improve data visualisation and analytical findings.
9. Become more confident debugging and implementing data engineering solutions independently.
10. Maintain accurate technical documentation as the project evolves.

---

## Week 2 — Reliable Data Engineering and Testing

**Assessment date:** 27 November 2026

The original self-assessment scale remains unchanged:

- Beginner — Learning the fundamentals and requiring guidance.
- Developing — Able to complete basic tasks with occasional guidance.
- Confident — Able to complete tasks independently.

The assessments below reflect practical experience gained
through WeatherFlow. I continue to need guidance for some
complex implementations.

### Core Programming and Development Skills

| Skill | Current Level | Evidence of Learning | Next Steps |
|---|---|---|---|
| Python | Developing | Implemented reusable functions, exceptions, data classes and type hints. | Write more functions independently. |
| Modular Programming | Developing | Refactored WeatherFlow into a reusable Python package. | Improve module design and separation of responsibilities. |
| Configuration Management | Developing | Centralised API settings, paths, thresholds and loading options in YAML. | Explore environment-specific configuration and validation. |
| Git and GitHub | Developing | Created feature branches, meaningful commits and pull requests. | Improve independent branching, conflict resolution and collaboration. |
| Command-Line Interfaces | Developing | Implemented run, backfill and date-range arguments using argparse. | Add automated CLI tests. |
| Virtual Environments | Developing | Used isolated runtime and development dependencies and editable installation. | Practise reproducible installations on different platforms. |
| Debugging | Developing | Investigated Git synchronisation, API and database failure scenarios. | Improve independent root-cause analysis. |
| Technical Documentation | Developing | Maintained README, data dictionary, ERD and measured acceptance evidence. | Improve concise and consistent documentation. |

### Data Extraction and Pipeline Engineering

| Skill | Current Level | Evidence of Learning | Next Steps |
|---|---|---|---|
| REST APIs | Developing | Retrieved forecast and archive weather responses using configurable requests. | Explore pagination, authentication and API limits. |
| API Resilience | Developing | Reused timeout handling, retries and exponential backoff. | Practise rate-limit handling and recovery strategies. |
| Structured Logging | Developing | Logged extraction windows, quality results and loading statistics. | Explore monitoring, alerting and log rotation. |
| ETL Pipelines | Developing | Implemented shared extraction, transformation, validation and loading workflows. | Explore workflow orchestration and scheduling. |
| Historical Backfill | Developing | Loaded 3600 historical records using seven-day request chunks. | Practise large-volume and selective historical reprocessing. |
| Incremental Loading | Developing | Implemented watermark-based extraction with a two-hour overlap. | Explore late-arriving data and recovery after longer outages. |
| Watermark Logic | Developing | Excluded future forecast observations and separated watermarks by city and source. | Practise watermark logic in other data sources. |
| Raw Data Persistence | Developing | Preserved original API responses and tested overwrite protection. | Implement a reusable historical replay workflow. |

### Transformation and Storage Skills

| Skill | Current Level | Evidence of Learning | Next Steps |
|---|---|---|---|
| Pandas | Developing | Flattened, standardised, enriched and validated structured weather records. | Practise more complex transformations and performance optimisation. |
| Timezone-Aware Processing | Developing | Stored UTC timestamps and derived Europe/London local times. | Explore additional daylight saving time edge cases. |
| Derived Metrics | Developing | Implemented temperature conversion, Beaufort scale and outdoor work risk. | Practise business-rule design and metric validation. |
| Reference Data | Developing | Enriched weather codes using a reusable CSV lookup. | Explore reference data versioning. |
| Parquet and Compression | Developing | Implemented compressed Parquet output with date partitions. | Explore partition pruning and storage optimisation. |

### Database and Data Modelling Skills

| Skill | Current Level | Evidence of Learning | Next Steps |
|---|---|---|---|
| SQL and SQLite | Developing | Created analytical SQL queries, joins and aggregations. | Practise window functions and complex queries. |
| Dimensional Modelling | Developing | Implemented city and date dimensions with an hourly weather fact table. | Explore slowly changing dimensions. |
| Entity Relationship Diagrams | Developing | Documented the WeatherFlow star schema in Mermaid. | Practise designing additional relational models. |
| Database Constraints | Developing | Implemented primary keys, foreign keys and CHECK constraints. | Explore database design and indexing strategies. |
| Transaction Management | Developing | Verified rollback following deliberately invalid loads. | Learn more about transaction isolation. |
| Idempotent Loading | Developing | Repeated historical and forecast loads without duplicate facts. | Explore idempotency in distributed data systems. |
| Database Integrity | Developing | Verified zero duplicate keys, zero foreign-key violations and successful integrity checks. | Automate integrity monitoring. |

### Data Quality Skills

| Skill | Current Level | Evidence of Learning | Next Steps |
|---|---|---|---|
| Automated Data Quality Validation | Developing | Implemented eight required rules and two supplementary pipeline checks. | Explore reusable validation frameworks. |
| Data Completeness | Developing | Verified every expected UTC hour for each configured city. | Explore missing-window recovery. |
| Data Validity | Developing | Implemented configurable measurement thresholds. | Practise additional schema and business-rule checks. |
| Data Uniqueness | Developing | Detected duplicate observation keys before loading. | Explore entity-level duplication and reconciliation. |
| Data Timeliness | Developing | Implemented and tested freshness checks for incremental runs. | Integrate freshness monitoring with alerting. |
| Data Consistency | Developing | Implemented actual versus feels-like temperature checks. | Explore cross-field and cross-source validation. |
| Quarantine Handling | Developing | Isolated invalid records with recorded failure reasons. | Develop quarantine investigation and reprocessing workflows. |
| Quality Reporting | Developing | Generated Markdown DQ reports with check outcomes and record counts. | Explore data quality dashboards and automated alerts. |
| Failure Handling | Developing | Blocked incomplete or duplicate datasets before database loading. | Explore automated recovery and operational alerting. |

### Automated Testing Skills

| Skill | Current Level | Evidence of Learning | Next Steps |
|---|---|---|---|
| Pytest | Developing | Developed a suite of 73 passing automated tests. | Write new tests more independently. |
| Unit Testing | Developing | Tested individual extraction, transformation and validation functions. | Improve boundary and exceptional-condition testing. |
| Integration Testing | Developing | Verified real SQLite, Parquet and shared pipeline operations. | Explore larger end-to-end scenarios. |
| Mock Testing | Developing | Simulated HTTP 503, HTTP 404, connection failures and successful responses. | Practise mocking additional external dependencies. |
| Pytest Fixtures | Developing | Created shared fixtures from genuine API response data. | Develop reusable fixture factories. |
| Parametrised Testing | Developing | Tested outdoor work risk and validation rule boundaries. | Practise broader boundary coverage. |
| Test Isolation | Developing | Used temporary directories and disposable databases. | Explore isolated CI testing environments. |
| Code Coverage | Developing | Achieved 92.55% overall statement coverage after Task 2.6. | Add CLI tests and investigate uncovered branches. |
| Offline Testing | Developing | Verified that the Task 2.5 test suite runs without internet access. | Maintain independent and deterministic test suites. |

### Collaboration and Professional Development

| Skill | Current Level | Evidence of Learning | Next Steps |
|---|---|---|---|
| Pull Requests | Developing | Created and merged PRs #4 to #8 and opened PR #9. | Continue reviewing smaller changes before merging. |
| Self-Review | Developing | Used Git diff and acceptance evidence to inspect changes. | Improve independent code review techniques. |
| Peer Code Review | Beginner | Identified my assigned review partner and opened PR #9. | Complete the review exchange and address feedback. |
| Continuous Integration | Beginner | Used reproducible local automated test and coverage commands. | Learn to configure automated CI checks. |

## Week 2 Testing Progress

| Task | Cumulative Passing Tests |
|---|---:|
| 2.1 | 9 |
| 2.2 | 34 |
| 2.3 | 41 |
| 2.4 | 56 |
| 2.5 | 62 |
| 2.6 | 73 |

## Week 2 Reflection on Skills Development

During Week 2, I moved beyond basic ETL processing and
developed practical experience in modular programming,
dimensional modelling, automated testing, data quality
validation, historical backfill and incremental loading.

My professional Data Quality Analyst experience helped me
understand the importance of reliable validation,
traceability and consistent quality reporting.

The main improvement in my technical skills was learning
how to incorporate these principles into an automated
data engineering pipeline.

I gained experience with concepts that were new to me,
including transactional upserts, pytest fixtures,
API mocking, Parquet storage and watermark calculations.

Although the project has achieved strong technical
results, I recognise that completing guided
implementations is not the same as being able to
implement every concept independently.

I will continue practising these skills to develop
greater technical confidence.

## Week 2 Measured Evidence

- 73 passing automated tests.
- 92.55% overall statement coverage.
- 3600 historical archive records across five cities.
- 3840 total fact records.
- Zero duplicate fact keys.
- Zero foreign-key violations.
- Successful database integrity verification.
- Historical reruns maintained unchanged fact counts.
- Incremental requests reduced extraction volume by
  93.75% for the demonstrated request interval.
- Ten data quality checks in the Task 2.6 pipeline.
- Five merged Week 2 technical pull requests.
- Pull Request #9 open with peer review pending.

## Goals for Week 3

1. Improve independent Python development and debugging.
2. Strengthen SQL and analytical querying skills.
3. Explore scheduling, orchestration and monitoring.
4. Improve command-line test coverage.
5. Learn more about continuous integration.
6. Complete the outstanding peer-review exchange.
7. Maintain reliable data quality and technical documentation.
