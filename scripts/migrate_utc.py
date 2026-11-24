import logging
import sqlite3
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Define absolute project and database paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DB_PATH = PROJECT_ROOT / "weather.db"

BACKUP_PATH = (
    PROJECT_ROOT
    / "data"
    / "backups"
    / "weather_before_utc_migration.db"
)
def validate_databases() -> int:
    """Validate the original database and backup before migration."""

    # Check that both database files exist
    if not DB_PATH.is_file():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    if not BACKUP_PATH.is_file():
        raise FileNotFoundError(f"Backup not found: {BACKUP_PATH}")

    # Open both databases in read-only mode
    source = sqlite3.connect(
        DB_PATH.as_uri() + "?mode=ro", uri=True
    )
    try:
        backup = sqlite3.connect(
            BACKUP_PATH.as_uri() + "?mode=ro", uri=True
        )
        try:
            # Check database integrity
            for name, conn in [("Original", source), ("Backup", backup)]:
                result = conn.execute(
                    "PRAGMA integrity_check"
                ).fetchone()[0]

                if result != "ok":
                    raise RuntimeError(f"{name} database integrity check failed")

            # Count records in both databases
            source_count = source.execute(
                "SELECT COUNT(*) FROM weather_hourly"
            ).fetchone()[0]

            backup_count = backup.execute(
                "SELECT COUNT(*) FROM weather_hourly"
            ).fetchone()[0]

            # Ensure the backup contains the expected number of records
            if source_count != backup_count:
                raise RuntimeError(
                    "Original and backup row counts do not match"
                )

            if source_count == 0:
                raise RuntimeError("Original database is empty")

            logger.info("Database integrity checks passed")
            logger.info("Original database records: %s", source_count)
            logger.info("Backup database records: %s", backup_count)

            return source_count

        finally:
            backup.close()
    finally:
        source.close()


def convert_records() -> pd.DataFrame:
    """Read existing records and convert timestamps to UTC and UK local time."""

    # Read existing records without modifying the database
    conn = sqlite3.connect(
        DB_PATH.as_uri() + "?mode=ro", uri=True
    )

    try:
        df = pd.read_sql_query(
            "SELECT * FROM weather_hourly",
            conn
        )
    finally:
        conn.close()

    # Interpret the original timestamps as UK local time
    local_time = pd.to_datetime(df["observed_at"]).dt.tz_localize(
        "Europe/London",
        ambiguous="raise",
        nonexistent="raise"
    )

    # Convert UK local timestamps to UTC
    df["observed_at_utc"] = local_time.dt.tz_convert("UTC")

    # Preserve UK local timestamps
    df["observed_at_local"] = local_time

    # Remove the old timestamp column
    df = df.drop(columns=["observed_at"])

    # Arrange columns to match the new SQLite schema
    columns = [
        "city",
        "observed_at_utc",
        "observed_at_local",
        "temperature_c",
        "feels_like_c",
        "humidity_pct",
        "precipitation_mm",
        "wind_speed_kmh",
        "weather_code",
        "ingested_at_utc",
    ]

    df = df[columns]

    # Check for duplicate primary keys
    if df.duplicated(subset=["city", "observed_at_utc"]).any():
        raise RuntimeError("Duplicate UTC primary keys detected")

    logger.info("Converted %s existing records", len(df))

    return df


def migrate_database() -> None:

    """Migrate the existing SQLite table to the UTC timestamp schema."""

    # Validate databases and convert existing records
    expected_count = validate_databases()
    df = convert_records()

    if len(df) != expected_count:
        raise RuntimeError("Converted record count does not match original")

    # Preserve timezone offsets when storing timestamps
    for column in ["observed_at_utc", "observed_at_local"]:
        df[column] = df[column].map(
            lambda value: value.isoformat(timespec="seconds")
        )

    # Convert missing values to None for SQLite
    df = df.astype(object).where(pd.notna(df), None)

    records = list(df.itertuples(index=False, name=None))

    # Connect to the original database
    conn = sqlite3.connect(DB_PATH)

    try:
        # Start a protected database transaction
        conn.execute("BEGIN IMMEDIATE")

        # Verify that the original table still has the expected schema
        columns = [
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(weather_hourly)"
            )
        ]

        if "observed_at" not in columns:
            raise RuntimeError(
                "Old timestamp column not found. "
                "Database may already be migrated."
            )

        current_count = conn.execute(
            "SELECT COUNT(*) FROM weather_hourly"
        ).fetchone()[0]

        if current_count != expected_count:
            raise RuntimeError("Original record count has changed")

        # Create a staging table with the new schema
        conn.execute("""
            CREATE TABLE weather_hourly_new (
                city TEXT NOT NULL,
                observed_at_utc TEXT NOT NULL,
                observed_at_local TEXT NOT NULL,
                temperature_c REAL,
                feels_like_c REAL,
                humidity_pct INTEGER,
                precipitation_mm REAL,
                wind_speed_kmh REAL,
                weather_code INTEGER,
                ingested_at_utc TEXT NOT NULL,
                PRIMARY KEY (city, observed_at_utc)
            )
        """)

        # Insert converted records into the staging table
        conn.executemany("""
            INSERT INTO weather_hourly_new (
                city,
                observed_at_utc,
                observed_at_local,
                temperature_c,
                feels_like_c,
                humidity_pct,
                precipitation_mm,
                wind_speed_kmh,
                weather_code,
                ingested_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, records)

        # Verify migrated record count
        migrated_count = conn.execute(
            "SELECT COUNT(*) FROM weather_hourly_new"
        ).fetchone()[0]

        if migrated_count != expected_count:
            raise RuntimeError("Migration record count mismatch")

        logger.info("Verified %s migrated records", migrated_count)

        # Replace the old table with the validated new table
        conn.execute("DROP TABLE weather_hourly")

        conn.execute("""
            ALTER TABLE weather_hourly_new
            RENAME TO weather_hourly
        """)

        # Check database integrity before committing
        result = conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if result != "ok":
            raise RuntimeError("Post-migration integrity check failed")

        # Permanently save the migration
        conn.commit()

        logger.info("Database migration completed successfully")
        logger.info("Total records preserved: %s", migrated_count)

    except Exception:
        # Undo all migration changes if an error occurs
        conn.rollback()
        logger.exception("Migration failed. Changes rolled back.")
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    logger.info("Starting UTC database migration...")

    migrate_database()
