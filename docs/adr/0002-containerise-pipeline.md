# ADR 0002: Containerise the WeatherFlow pipeline

- **Status:** Accepted
- **Date:** 2026-11-28
- **Author:** Pooja Lihal

## Context

WeatherFlow previously depended on a local Python environment
or a temporary Linux development image. Native Windows
Psycopg execution was restricted by Application Control.
The pipeline needs a reproducible runtime for developers,
reviewers and future Airflow orchestration.

## Decision

We will package WeatherFlow using the official Python
3.13 slim image and run it as a non-root user.

Docker Compose will connect the pipeline to PostgreSQL
through the warehouse service hostname and persist generated
data, logs and quality reports using bind mounts.

## Consequences

- **Good:** Consistent Python and dependency environment.
- **Good:** No native Windows Psycopg dependency for normal runs.
- **Good:** Credentials are supplied at runtime.
- **Good:** Dependency layers are cached during builds.
- **Good:** CLI failures propagate through Docker exit codes.
- **Bad:** Docker requires additional disk space and memory.
- **Bad:** Existing root-owned directories may require a
  one-off permission correction.
- **Follow-up:** Reuse the containerised pipeline in Airflow.
- **Follow-up:** Complete the WeatherAPI missing-key test
  after Task 3.1.

## Alternatives considered

| Option | Why not chosen |
| --- | --- |
| Local Python environment only | Platform-specific dependency restrictions. |
| Temporary development image | Does not provide the permanent packaged CLI workflow. |
| Run the pipeline as root | Unnecessary privileges and ownership problems. |
| Include credentials in the image | Creates a security risk. |

## Evidence

- Docker image built successfully from a fresh GitHub clone.
- Container runs as UID 1000.
- All seven mounted directory write checks passed.
- No .env file or configured credentials found in the image checks.
- 76 regression tests passed.
- Overall coverage: 91.70%.
- Two live containerised runs retained 3840 fact records.
- Intentional invalid date range returned exit code 1.

See [Task 3.3 acceptance evidence](../task_3_3_acceptance.md)
and the [Dockerfile](../../Dockerfile).
