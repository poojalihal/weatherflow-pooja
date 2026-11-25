"""Command-line entry point for WeatherFlow."""

import argparse
import logging

from .config import load_config
from .pipeline import run

logger = logging.getLogger(__name__)


def main() -> int:
    """Parse command-line arguments and execute the selected command."""
    parser = argparse.ArgumentParser(
        description="WeatherFlow data engineering pipeline"
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "run",
        help="Run the weather ETL pipeline",
    )

    args = parser.parse_args()

    try:
        config = load_config()

        log_file = config["paths"]["log_file"]
        log_file.parent.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_file, encoding="utf-8"),
            ],
        )

        if args.command == "run":
            return run(config)

    except Exception:
        logger.exception("WeatherFlow pipeline failed")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
