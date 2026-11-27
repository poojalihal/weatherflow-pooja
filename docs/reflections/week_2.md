# Week 2 Reflection — WeatherFlow

**Date:** 27 November 2026

## What I built

During Week 2, I developed the WeatherFlow project from a
basic ETL pipeline into a more modular, reliable, testable
and maintainable data engineering solution.

### Task 2.1 — Modular Package, Configuration and Logging

- Refactored the project into a Python package under
  src/weatherflow/.
- Separated extraction, transformation, loading,
  configuration and pipeline orchestration.
- Centralised API settings, city information and file
  paths in config.yaml.
- Improved structured logging and exception handling.
- Implemented a command-line interface.
- Practised working with feature branches and pull requests.

### Task 2.2 — Transformations and Derived Metrics

- Flattened nested weather API responses into structured
  Pandas DataFrames.
- Standardised column names, data types and timestamps.
- Preserved UTC timestamps and derived UK local timestamps.
- Implemented weather code descriptions and categories.
- Calculated Fahrenheit temperature, wind speed in metres
  per second, Beaufort scale and outdoor work risk.
- Added daylight indicators and deduplication logic.
- Implemented compressed Parquet storage.

The Parquet comparison demonstrated a file size reduction
of approximately 63.06% compared with CSV for the tested
dataset.

### Task 2.3 — Star Schema and Idempotent Loading

- Designed a dimensional database model containing
  dim_city, dim_date and fact_weather_hourly.
- Defined the fact grain as one row per city, per UTC
  observation hour, per source.
- Implemented primary keys, foreign keys and database
  constraints.
- Used transactional upserts to support safe reruns.
- Tested database rollback following deliberately invalid
  loads.
- Created an entity relationship diagram and five
  analytical SQL queries.

Three repeated pipeline executions maintained the same
240 fact records without introducing duplicates.

### Task 2.4 — Data Quality Checks and Quarantine

- Implemented configurable validation rules covering
  completeness, validity, uniqueness, timeliness and
  consistency.
- Distinguished between quarantine, blocking failures
  and non-blocking warnings.
- Created a custom DataQualityError exception.
- Implemented quarantine storage with failure reasons.
- Generated Markdown data quality reports.
- Ensured validation takes place before database loading.

I deliberately tested an invalid temperature of 99 degrees
Celsius and confirmed that it was quarantined while valid
records continued through the pipeline.

I also confirmed that duplicate observation keys prevent
the entire database load.

The live validation processed 240 valid records with
zero quarantined records.

### Task 2.5 — Automated Testing with Pytest

- Developed unit and integration tests throughout Week 2.
- Used a genuine Open-Meteo London API response containing
  six hourly observations as a reusable test fixture.
- Implemented shared pytest fixtures.
- Mocked API requests, connection failures and retry delays.
- Used temporary directories and databases to isolate tests.
- Verified that tests could run without internet access.
- Measured code coverage using pytest-cov.

Task 2.5 finished with 62 passing tests and 92.75%
overall statement coverage.

### Task 2.6 — Backfill and Incremental Loading

- Implemented historical extraction using the Open-Meteo
  Historical Weather API.
- Divided historical requests into seven-day chunks.
- Implemented per-city and per-source watermarks.
- Excluded future forecast timestamps from watermark
  calculations.
- Added a two-hour overlap to capture late corrections.
- Reused the existing transformation, validation and
  loading functions.
- Added new-versus-updated record counts to pipeline logs.

The historical backfill loaded all 3,600 expected records
for the period 23 October to 21 November 2026.

Repeating the same historical backfill maintained an
unchanged database count of 3,840 total fact records.

Two incremental executions each requested 15 records
instead of the original 240-record full window.

This represented a 93.75% reduction in extraction volume
for the demonstrated request interval.

The technical implementation is complete and Pull
Request #9 has been opened. The peer-review requirement
remains pending.

## What went well

- I successfully organised a growing Python project into
  reusable modules with centralised configuration.
- I became more familiar with Git branches, commits,
  pull requests and repository synchronisation.
- I developed automated tests alongside each technical
  task rather than leaving all testing until the end.
- I successfully implemented dimensional data modelling
  and transactional database loading.
- I applied my existing data quality experience to
  automated data engineering validation.
- I verified that invalid records could be quarantined
  without silently losing their failure reasons.
- I successfully implemented historical and incremental
  ingestion using shared processing functions.
- I documented implementation decisions and measured
  acceptance results throughout the development process.

## What was hard, and how I solved it

### 1. Modular Python project organisation

Understanding how Python packages, imports, configuration
and command-line entry points work together was initially
challenging.

I worked through the refactoring with guidance, separating
responsibilities into modules and verifying that the
package could be executed correctly.

### 2. Dimensional database modelling

Understanding fact tables, dimension tables, composite
primary keys and foreign-key relationships required
additional practice.

Creating the WeatherFlow star schema and ERD helped me
understand how dimensional modelling supports analytical
queries and consistent data relationships.

### 3. Idempotency and transaction handling

I needed to understand how repeated loads could update
existing records without creating duplicates.

I used composite keys and transactional upserts, then
verified the behaviour through repeated loading and
deliberate rollback tests.

### 4. Data quality validation

One important challenge was understanding the difference
between invalid individual records and invalid datasets.

I learned that an incorrect temperature can be isolated,
while duplicate keys or missing requested hours may
require the entire load to stop.

I also learned that duplicate checks must run before
deduplication, otherwise the original quality problem
could be hidden.

### 5. Automated testing

Writing tests using mocks, fixtures, parametrisation and
temporary databases was new to me.

I developed these skills gradually and used test results
to verify both expected behaviour and failure scenarios.

This helped me understand the difference between testing
software correctness and validating incoming data quality.

### 6. Watermark-based incremental extraction

Understanding how future forecast observations could
incorrectly advance a watermark was particularly important.

I implemented a watermark that only considers timestamps
that have already occurred, with a two-hour overlap to
capture corrections.

The automated tests and live request logs helped me
verify the implementation.

### 7. Git branch synchronisation

During Task 2.4, an uncommitted README modification
prevented me from switching to the main branch.

I inspected the changes using git diff, restored the
unintentionally modified content and synchronised main.

I learned to use conditional command chaining with &&
so that later Git commands do not execute when an
earlier command fails.

## What surprised me

- Writing automated tests throughout development made
  Task 2.5 significantly easier to complete.
- A dimensional database can store historical and forecast
  observations for the same city and timestamp without
  conflicts when the source is included in the fact key.
- Parquet compression substantially reduced the size of
  the tested weather dataset.
- Incremental extraction could retrieve only 15 records
  instead of 240 for the demonstrated request window.
- Repeating a historical backfill did not increase the
  number of database records.
- A successful pipeline requires more than working code:
  it also requires validation, logging, testing, reliable
  recovery and clear documentation.
- High statement coverage does not necessarily mean
  every possible execution path has been tested.

## Measured Week 2 achievements

| Metric | Result |
|---|---|
| Automated tests | 73/73 passed |
| Failed tests | 0 |
| Final test execution time | 2.43 seconds |
| Overall statement coverage | 92.55% |
| Minimum required coverage | 70% |
| Covered source statements | 596 of 644 |
| Configured cities | 5 |
| Historical backfill days | 30 |
| Historical observations per city | 720 |
| Historical archive records | 3600 |
| Forecast records | 240 |
| Total fact records | 3840 |
| Historical record completeness | 100% |
| Historical requests per run | 25 successful |
| Historical quarantine count | 0 |
| Historical rerun row count increase | 0 |
| Incremental records per run | 15 |
| Demonstrated extraction reduction | 93.75% |
| Duplicate fact keys | 0 |
| Foreign key violations | 0 |
| Database integrity | ok |
| Parquet size reduction in tested comparison | 63.06% |

## Applying my professional experience

My professional experience as a Data Quality Analyst
helped me understand the importance of accuracy,
consistency, completeness and reliable quality reporting.

Week 2 allowed me to apply these principles within an
automated data engineering pipeline.

Instead of identifying quality issues only after data
has been produced, I learned how validation can be built
into the pipeline to prevent unsuitable records from
reaching analytical systems.

This has helped me understand the relationship between
data quality analysis, software testing and data
engineering.

## What I would do differently

- Plan module responsibilities and data models before
  implementing larger changes.
- Continue writing tests alongside new functionality.
- Review smaller changes more frequently.
- Investigate edge cases earlier, particularly timestamps,
  missing data and failed extraction windows.
- Arrange peer review earlier rather than leaving it
  until after the technical implementation.
- Practise implementing smaller functions independently
  before seeking additional guidance.
- Add automated tests for the command-line entry point.

## What remains outstanding

The technical acceptance criteria for Tasks 2.1 to 2.6
have been satisfied.

Pull Requests #4 to #8 have been merged.

Pull Request #9 remains open while I arrange the required
peer-review exchange with my assigned review partner.

I still need to review my partner's pull request with at
least three meaningful comments, receive feedback on my
own pull request, and address all received comments
before completing the merge.

The original Week 2 submission deadline was
18 November 2026 at 18:00 UK time. This reflection
documents my subsequent completion of the technical work.

## Goals for Week 3

1. Become more confident writing Python functions and
   debugging problems independently.

2. Improve my understanding of pipeline orchestration,
   scheduling and automated monitoring.

3. Develop stronger SQL and analytical skills.

4. Learn more about automated deployment and continuous
   integration.

5. Improve test coverage for command-line execution and
   additional edge cases.

6. Complete the peer-review exchange and become more
   comfortable giving and receiving technical feedback.

7. Continue maintaining clear documentation, measurable
   acceptance criteria and reliable data quality controls.

## Overall reflection

Week 2 was more challenging than Week 1 because it
introduced several new software engineering and data
engineering concepts.

Although I still require guidance for some implementations,
I have developed a much stronger practical understanding
of how a reliable data pipeline is designed, tested and
maintained.

My main achievement was developing WeatherFlow into a
modular pipeline capable of historical and incremental
loading, supported by 73 passing automated tests,
92.55% code coverage and verified database integrity.

I am pleased with my progress and would like to continue
developing the confidence to implement these concepts
independently.
