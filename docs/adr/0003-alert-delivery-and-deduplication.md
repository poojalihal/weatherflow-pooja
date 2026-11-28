# ADR 0003: Store and deduplicate actionable alerts

- **Status:** Accepted (implementation decision; programme agreement pending)
- **Date:** 2026-11-28
- **Author:** Pooja Lihal

## Context

WeatherFlow must notify users about high-risk outdoor
working conditions and pipeline failures.

No external webhook channel has been configured.
Repeated hourly executions must not generate duplicate
notifications for the same risky period.

The programme permits a database-and-log fallback
when an external notification channel is unavailable.

## Decision

We will store actionable alerts in PostgreSQL and write
new messages to the application log after a successful
database transaction.

Consecutive unnotified high-risk hours will be grouped
by city, using unique UTC hourly keys to prevent
duplicate notifications across executions and sources.

## Consequences

- **Good:** Durable and auditable alert history.
- **Good:** Duplicate notifications are suppressed.
- **Good:** No external webhook credentials are required.
- **Good:** Consecutive risky hours are grouped.
- **Bad:** No proactive external messaging delivery.
- **Bad:** A failure after database commit but before
  logging may leave a stored alert without a log message.
- **Follow-up:** Obtain programme agreement on the fallback.
- **Follow-up:** Integrate Airflow failure alerts in Task 3.4.
- **Follow-up:** Verify both forecast sources in Task 3.1.

## Alternatives considered

| Option | Why not chosen |
| --- | --- |
| External messaging webhook | No channel configured. |
| Log messages only | No durable alert history. |
| One notification per risky hour | Unnecessary notification volume. |
| Repeat alerts every execution | Creates alert fatigue. |

## Evidence

- 79 automated tests passed in 4.76 seconds.
- Overall code coverage: 89.99%.
- Alert module coverage: 78%.
- Two live executions generated zero unnecessary alerts.
- PostgreSQL integration tests verified risk grouping,
  source combination and duplicate suppression.

### Controlled end-to-end verification

Synthetic high-risk observations were created inside
an isolated PostgreSQL test schema.

- City: Edinburgh.
- Risk period: 28 November 2026, 02:00-05:00 GMT.
- Reasons: heavy precipitation, storm and strong wind.
- First execution: one new consolidated alert.
- Second execution: zero new alerts.
- Stored alerts after both runs: one.
- Unique hourly deduplication keys: three.
- Temporary test schema successfully removed.

The synthetic scenario was not a real weather warning.

See [acceptance evidence](../task_3_6_acceptance.md)
and [alert tests](../../tests/test_alerts.py).
