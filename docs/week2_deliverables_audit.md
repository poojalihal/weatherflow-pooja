# Week 2 Deliverables Audit — WeatherFlow

**Assessment date:** 27 November 2026

**Original submission deadline:** 18 November 2026,
18:00 UK time.

**Overall status:** Technical implementation verified.
Peer-review exchange and final documentation merge pending.

## Deliverables

| Deliverable | Description | Status | Evidence |
|---|---|---|---|
| D2.1 | Modular Python package, configuration, logging and CLI | Complete | PR #4 |
| D2.2 | Transformations, derived metrics and Parquet storage | Complete | PR #5 |
| D2.3 | Star schema and idempotent loading | Complete | PR #6 |
| D2.4 | Data quality checks and quarantine | Complete | PR #7 |
| D2.5 | Automated testing with pytest | Complete | PR #8 |
| D2.6 | Historical backfill, incremental loading and peer review | Technical criteria complete; peer review pending | PR #9 |
| D2.7 | Week 2 reflection and updated skills tracker | Documentation prepared; merge pending | Reflection PR |

## D2.1 — Modular Python Package

- [x] Package created under src/weatherflow/.
- [x] Centralised config.yaml.
- [x] Structured logging.
- [x] Command-line entry point.
- [x] Editable package installation verified during setup.
- [x] Pull request merged.

Evidence:
https://github.com/poojalihal/weatherflow-pooja/pull/4

Merge commit: 0b83c29.

The substitute pull request template was used because
the original programme template was unavailable.

## D2.2 — Transformations and Derived Metrics

- [x] Standardised column names and types.
- [x] UTC and UK local timestamps.
- [x] Weather code reference lookup.
- [x] Derived metrics and outdoor work risk.
- [x] Deduplication functionality.
- [x] Compressed and partitioned Parquet output.
- [x] Automated tests passed.
- [x] Pull request merged.

Validation evidence:

- 240 processed records.
- 48 records per configured city.
- Approximately 63.06% file size reduction
  in the tested CSV-to-Parquet comparison.
- 34 passing automated tests at task completion.

Evidence:
https://github.com/poojalihal/weatherflow-pooja/pull/5

Merge commit: dc4f02f.

## D2.3 — Star Schema and Idempotent Load

- [x] SQL schema containing three dimensional tables.
- [x] Documented fact grain.
- [x] Composite primary key and foreign keys.
- [x] Transactional upserts.
- [x] Transaction rollback verified.
- [x] Repeated loads preserved fact counts.
- [x] Entity relationship diagram.
- [x] Five analytical SQL queries.
- [x] Pull request merged.

Validation evidence:

- Five city dimension records.
- 1095 date dimension records.
- Three repeated loads: 240, 240, 240 fact records.
- Zero duplicate keys.
- Zero foreign-key violations.
- 41 passing automated tests at task completion.

Evidence:
https://github.com/poojalihal/weatherflow-pooja/pull/6

Merge commit: b065c03.

## D2.4 — Data Quality Checks and Quarantine

- [x] At least eight validation checks.
- [x] All five required quality dimensions.
- [x] Configurable validation thresholds.
- [x] Quarantine with failure reasons.
- [x] Blocking DataQualityError.
- [x] Invalid 99-degree temperature quarantined.
- [x] Duplicate observation blocks database loading.
- [x] Data quality reports generated.
- [x] Live pipeline validated.
- [x] Pull request merged.

Validation evidence:

- Nine checks at task completion.
- 240 valid records from 240 incoming records.
- Zero live quarantined records.
- 56 passing automated tests.

Evidence:
https://github.com/poojalihal/weatherflow-pooja/pull/7

Merge commit: 450a5f7.

## D2.5 — Testing with Pytest

- [x] Minimum 15 automated tests exceeded.
- [x] Genuine six-hour API response fixture.
- [x] Shared pytest fixtures.
- [x] Mocked API requests and retry delays.
- [x] Temporary raw storage tests.
- [x] Database idempotency integration test.
- [x] Offline testing documented.
- [x] Coverage exceeds 70%.
- [x] Coverage command and TOTAL output in README.
- [x] Pull request merged.

Validation evidence:

- 62 passing automated tests.
- 92.75% statement coverage.
- Successful six-record integration test loaded twice.

Evidence:
https://github.com/poojalihal/weatherflow-pooja/pull/8

Merge commit: 0e3a791.

## D2.6 — Backfill, Incremental Loads and Code Review

### Technical acceptance

- [x] Thirty-day historical backfill.
- [x] Seven-day request chunking.
- [x] Exactly 3600 historical records loaded.
- [x] Repeated backfill preserves fact counts.
- [x] Per-city and per-source watermarks.
- [x] Future timestamps excluded from watermarks.
- [x] Two-hour incremental overlap.
- [x] Incremental request dates recorded in logs.
- [x] New-versus-updated counts logged.
- [x] Shared transformation, validation and loading code.
- [x] At least two watermark tests.
- [x] Overall coverage exceeds 70%.
- [x] Final database integrity verification.
- [x] Pull request opened.

### Collaborative acceptance

- [x] Assigned review partner identified: potamv01.
- [ ] Review partner's pull request.
- [ ] Submit at least three meaningful review comments.
- [ ] Receive peer feedback on PR #9.
- [ ] Address every received review comment.
- [ ] Merge PR #9.
- [ ] Synchronise local main branch.

Technical validation evidence:

- 73 passing automated tests.
- 92.55% overall statement coverage.
- Historical interval: 2026-10-23 to 2026-11-21.
- 25 successful archive requests per backfill.
- 3600 archive records and 240 forecast records.
- 3840 total fact records.
- Repeated historical backfill: 3840 to 3840.
- Both incremental runs: 15 valid records,
  zero new records and 15 updated records.
- Zero duplicate keys.
- Zero foreign-key violations.
- Database integrity: ok.

Evidence:
https://github.com/poojalihal/weatherflow-pooja/pull/9

Status: Open; peer-review requirement pending.

## D2.7 — Weekly Reflection

- [x] Week 2 reflection prepared.
- [x] Skills tracker updated.
- [x] Measured achievements documented.
- [x] Learning challenges and future goals documented.
- [x] Outstanding peer review accurately recorded.
- [ ] Reflection pull request merged.

Files:

- docs/reflections/week_2.md
- docs/skills_tracker.md
- docs/week2_deliverables_audit.md

## Week 2 Definition of Done

| Requirement | Verified result | Status |
|---|---|---|
| Runtime dependency installation | Previously verified during setup | Pass |
| Editable package installation | Previously verified | Pass |
| All automated tests pass | 73/73 | Pass |
| Overall coverage at least 70% | 92.55% | Pass |
| Thirty-day historical backfill | 3600 archive records | Pass |
| Incremental pipeline execution | 15 valid records | Pass |
| Repeat incremental execution | No new fact keys | Pass |
| Database integrity | ok | Pass |
| Peer-review exchange | Not yet completed | Pending |
| Final technical branch merge | PR #9 open | Pending |
| Reflection and skills tracker | Prepared | Merge pending |

The thirty-day live backfills were anchored to the same
end date to ensure a reproducible idempotency comparison.

The technical definition-of-done evidence was obtained
from the feature/backfill branch. It does not imply that
Task 2.6 has already been merged into main.

## Final Coverage Evidence

Coverage command:

python -m pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=70

Measured output:

TOTAL                               644     48    93%
Required test coverage of 70% reached.
Total coverage: 92.55%
73 passed in 2.43s

The CLI entry point remains uncovered by the automated
test suite, although its commands were exercised manually.

## Known Limitations

- Peer review remains outstanding.
- Historical API availability depends on the external
  service and its configured availability lag.
- The archive and forecast date ranges may contain gaps.
- New-versus-updated counts assume one pipeline writer.
- A dedicated historical raw-file replay command has
  not yet been implemented.
- Generated raw data, databases, reports and logs remain
  local; measured evidence is recorded in README and PRs.

## Final Assessment

The technical requirements for Week 2 have been verified.

The Week 2 submission cannot be marked fully complete
until the outstanding peer review and required pull
request merges have been completed.
