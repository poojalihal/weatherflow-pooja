"""Command-line entry point for WeatherFlow."""

import argparse
import logging

from .config import load_config
from .pipeline import backfill, run

logger = logging.getLogger(__name__)


def main() -> int:
    """Parse arguments and execute the selected pipeline."""

    parser = argparse.ArgumentParser(
        description="WeatherFlow data engineering pipeline"
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    run_parser = subparsers.add_parser(
        "run",
        help="Run incremental forecast extraction",
    )

    run_parser.add_argument(
        "--full",
        action="store_true",
        help="Use the original full forecast window",
    )

    backfill_parser = subparsers.add_parser(
        "backfill",
        help="Load historical weather archive records",
    )

    backfill_parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Number of historical days (default: 30)",
    )

    backfill_parser.add_argument(
        "--start-date",
        help="Historical start date, YYYY-MM-DD",
    )

    backfill_parser.add_argument(
        "--end-date",
        help="Historical end date, YYYY-MM-DD",
    )

    args = parser.parse_args()

    try:

        config = load_config()
        from .postgres import configure_database
        configure_database(config)

        log_file = config["paths"]["log_file"]

        log_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        logging.basicConfig(
            level=logging.INFO,
            format=(
                "%(asctime)s | %(levelname)s | "
                "%(name)s | %(message)s"
            ),
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(
                    log_file,
                    encoding="utf-8",
                ),
            ],
        )

        if args.command == "run":

            return run(
                config,
                incremental=not args.full,
            )

        if args.command == "backfill":

            return backfill(
                config,
                days=args.days,
                start_date=args.start_date,
                end_date=args.end_date,
            )

    except Exception:

        logger.exception(
            "WeatherFlow pipeline failed"
        )

        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
