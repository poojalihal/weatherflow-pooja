# ADR 0001: Run the PostgreSQL warehouse in Docker

- **Status:** Accepted
- **Date:** 2026-11-28
- **Author:** Pooja Lihal

## Context

WeatherFlow previously used SQLite as its analytical warehouse.
Week 3 requires a shared database that can support the
pipeline, scheduler, dashboard and analytical queries.
PostgreSQL 18 provides native timestamp and boolean types,
transactional upserts and network-based database access.
Native Windows Psycopg imports were blocked by Application
Control, although the Linux binary implementation worked
successfully inside Docker.

## Decision

We will run PostgreSQL 18 in Docker Compose with persistent
named-volume storage and environment-based credentials.
PostgreSQL-dependent Python operations will run inside Linux
containers, while SQLite remains available for backward
compatibility and existing tests.

## Consequences

- **Good:** Consistent database environment, persistent
  storage, native data types and transactional upserts.
- **Good:** Existing transformation, validation and incremental
  processing logic can be reused.
- **Bad:** Docker adds resource usage and operational complexity.
- **Bad:** Native Windows PostgreSQL execution remains blocked.
- **Follow-up:** Containerise the full pipeline in Task 3.3.
- **Follow-up:** Improve retry handling for invalid API responses.
- **Follow-up:** Retain automated PostgreSQL integration tests
  in continuous integration.

## Alternatives considered

| Option | Why not chosen |
| --- | --- |
| Continue using SQLite only | Does not meet the shared warehouse requirement. |
| Install PostgreSQL directly on Windows | Less reproducible and does not resolve the verified Psycopg restriction. |
| Copy historical SQLite records | Reprocessing the raw zone exercises transformation and validation again. |
| Disable Windows Application Control | Would weaken device security and is unnecessary. |

## Evidence

- PostgreSQL 18.7 and Psycopg 3.3.9 verified.
- 76 automated tests passed.
- Overall test coverage: 91.69%.
- PostgreSQL module coverage: 91%.
- Three consecutive pipeline runs retained 3,840 fact records.
- Invalid risk value triggered a complete transaction rollback.
- Docker container recreation preserved all 3,840 fact records.
- All five analytical SQL queries executed successfully.

See [Task 3.2 acceptance evidence](../task_3_2_acceptance.md)
and [PostgreSQL integration tests](../../tests/test_postgres.py).
