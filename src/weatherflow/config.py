"""Load and validate WeatherFlow configuration."""

import logging
import os
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

CONFIG_FILE = Path(
    os.getenv("WEATHERFLOW_CONFIG")
    or (Path(__file__).resolve().parents[2] / "config.yaml")
)


def _require_keys(data: dict, keys: list[str], section: str) -> None:
    """Check that all required configuration keys exist."""
    if not isinstance(data, dict):
        raise ValueError(f"{section} must be a mapping")

    for key in keys:
        if key not in data:
            raise ValueError(f"Missing required config key: {section}.{key}")


def load_config(config_file: Path = CONFIG_FILE) -> dict:
    """Load YAML settings, validate required keys and resolve paths."""
    config_file = Path(config_file).resolve()

    if not config_file.is_file():
        raise FileNotFoundError(f"Configuration not found: {config_file}")

    with config_file.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    _require_keys(config, ["api", "cities", "paths"], "config")

    _require_keys(
        config["api"],
        [
            "forecast_url", "archive_url", "timeout_seconds",
            "max_retries", "past_days", "forecast_days",
            "hourly_variables", "timezone"
        ],
        "api",
    )

    _require_keys(
        config["paths"],
        [
            "raw_dir", "processed_dir", "quarantine_dir",
            "database", "log_file"
        ],
        "paths",
    )

    if not isinstance(config["cities"], list) or not config["cities"]:
        raise ValueError("At least one city must be configured")

    for city in config["cities"]:
        _require_keys(
            city,
            ["name", "latitude", "longitude"],
            "cities",
        )

    retries = config["api"]["max_retries"]

    if type(retries) is not int or retries < 0:
        raise ValueError("max_retries must be a non-negative integer")

    if config["api"]["timeout_seconds"] <= 0:
        raise ValueError("timeout_seconds must be positive")

    if config["api"]["timezone"] != "UTC":
        raise ValueError("API timezone must be UTC")

    root = config_file.parent

    config["paths"] = {
        key: (root / value).resolve()
        for key, value in config["paths"].items()
    }

    return config
