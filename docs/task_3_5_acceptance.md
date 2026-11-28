# Task 3.5: Continuous Integration with GitHub Actions

**Verification date:** 28 November 2026

**Branch:** feature/ci

**Pull request:** #14

## Implementation

- GitHub Actions workflow triggered on push and pull request.
- Ubuntu-hosted runner.
- Python 3.13.
- PostgreSQL 18 service container.
- Automated dependency installation.
- Editable WeatherFlow package installation.
- Minimum test coverage threshold of 70%.
- README CI status badge.
- Disposable CI database credentials.
- Mocked weather API requests.

## Offline verification

| Measurement | Result |
| --- | ---: |
| Unit tests passed | 2 |
| PostgreSQL integration tests skipped | 4 |
| Execution time | 0.64 seconds |

Integration tests correctly skip when DATABASE_URL
is not configured.

## Red-to-green CI demonstration

| Workflow | Event | Result | Duration |
| --- | --- | --- | --- |
| CI 1 | Initial push | Failed as expected | 1m 0s |
| CI 2 | Pull request opened | Failed as expected | 1m 21s |
| CI 3 | Corrective push | Passed | 1m 3s |
| CI 4 | Pull request updated | Passed | 1m 1s |

Initial commit: 50baa42.

A temporary failing test was introduced to demonstrate
that CI detects test failures.

The initial CI test summary showed:

- 79 tests passed.
- 1 test failed.
- Overall code coverage: 89.99%.
- Required coverage: 70%.
- Test execution time: 3.69 seconds.
- Process exit code: 1.

Corrective commit: 866d33f.

The temporary failing test was removed, and both push
and pull request workflows passed successfully.

## PostgreSQL integration tests

The integration suite includes:

- Idempotent PostgreSQL upserts.
- Atomic transaction rollback.
- PostgreSQL watermark handling.
- Alert period grouping and deduplication.

## Security

- Production credentials are excluded from Git.
- Secret protection verification passed.
- CI uses its own temporary PostgreSQL service.
- No production warehouse connection is required.
- No real WeatherAPI key is required.

## Screenshot evidence

- [Additional CI failure evidence](screenshots/intentional-failure.png)
- [Failed CI execution](screenshots/ci-failed-checks.png)
- [Successful CI check](screenshots/ci-passed-checks.png)
- [Successful job execution](screenshots/ci-passed-tests.png)

## Acceptance checklist

- [x] CI runs on every push and pull request.
- [x] PostgreSQL integration service configured.
- [x] Offline integration-test skipping verified.
- [x] Coverage gate configured at 70%.
- [x] Failing and passing checks demonstrated in one PR.
- [x] CI badge added to README.
- [ ] Latest CI run on main verified as successful.

## Follow-up

Verify successful CI execution on main after merging.

Mandatory branch protection is optional and has not
yet been configured.
