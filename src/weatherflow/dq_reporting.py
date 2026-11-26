"""Persist quarantined weather records and quality reports."""

import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .validate import CheckResult

logger = logging.getLogger(__name__)


def save_quarantine(
    df: pd.DataFrame,
    quarantine_dir: Path,
    run_time: datetime,
) -> Path:
    """Write rejected records to partitioned Parquet."""

    run_time = run_time.astimezone(timezone.utc)

    run_date = run_time.strftime("%Y-%m-%d")

    timestamp = run_time.strftime(
        "%Y%m%dT%H%M%S%f"
    )

    output_dir = (
        quarantine_dir
        / f"run_date={run_date}"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        output_dir
        / f"part-{timestamp}.parquet"
    )

    df.to_parquet(
        output_file,
        engine="pyarrow",
        compression="snappy",
        index=False,
    )

    logger.warning(
        "Quarantined %s records to %s",
        len(df),
        output_file,
    )

    return output_file


def _markdown_cell(value: object) -> str:
    """Escape text used inside a Markdown table."""

    return (
        str(value)
        .replace("|", r"\|")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def write_dq_report(
    results: list[CheckResult],
    reports_dir: Path,
    run_time: datetime,
    *,
    status: str,
    input_rows: int,
    good_rows: int,
    quarantined_rows: int,
    loaded_rows: int,
    error: str = "",
) -> Path:
    """Write a Markdown report for a pipeline execution."""

    run_time = run_time.astimezone(timezone.utc)

    reports_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = run_time.strftime(
        "%Y%m%dT%H%M%S%f"
    )

    output = reports_dir / f"{timestamp}.md"

    lines = [
        "# WeatherFlow Data Quality Report",
        "",
        f"Run time UTC: {run_time.isoformat()}",
        "",
        f"Run status: {status}",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Input records | {input_rows} |",
        f"| Valid records | {good_rows} |",
        f"| Quarantined records | {quarantined_rows} |",
        f"| Loaded records | {loaded_rows} |",
        "",
        "## Check Results",
        "",
        "| Check | Dimension | Severity | Result | "
        "Affected rows or missing slots | Details |",
        "|---|---|---|---|---:|---|",
    ]

    for result in results:

        if result.skipped:
            outcome = "SKIPPED"
        elif result.passed:
            outcome = "PASS"
        else:
            outcome = "FAIL"

        values = [
            result.name,
            result.dimension,
            result.severity,
            outcome,
            result.failed_rows,
            result.details,
        ]

        lines.append(
            "| "
            + " | ".join(
                _markdown_cell(value)
                for value in values
            )
            + " |"
        )

    if error:
        lines.extend([
            "",
            "## Run Error",
            "",
            error,
        ])

    output.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    logger.info(
        "Data quality report saved to %s",
        output,
    )

    return output
