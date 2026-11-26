"""Test partitioned Parquet storage."""

from datetime import datetime, timezone

import pandas as pd

from weatherflow.storage import save_processed


def test_save_processed_parquet(tmp_path):
    """Write and read a Parquet file in the expected partition."""
    df = pd.DataFrame({
        "city": ["London", "Cardiff"],
        "temperature_c": [10.5, 12.0],
        "outdoor_work_risk": ["low", "medium"],
    })

    run_time = datetime(
        2026, 11, 25, 12, 0,
        tzinfo=timezone.utc,
    )

    output = save_processed(df, tmp_path, run_time)

    assert output.exists()
    assert output.suffix == ".parquet"
    assert output.name.startswith("part-")
    assert output.parent.name == "run_date=2026-11-25"
    assert output.parent.parent.name == "weather_hourly"

    result = pd.read_parquet(output)

    pd.testing.assert_frame_equal(
        df,
        result,
        check_dtype=False,
    )
