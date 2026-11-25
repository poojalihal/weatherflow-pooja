"""Test WeatherFlow configuration loading and validation."""

import pytest
import yaml

from weatherflow.config import load_config


def test_valid_config():
    """Verify the expected configuration settings."""
    config = load_config()

    assert len(config["cities"]) == 5
    assert config["api"]["timezone"] == "UTC"
    assert config["api"]["max_retries"] == 3


def test_absolute_paths():
    """Verify that all configuration paths are absolute."""
    config = load_config()

    assert all(
        path.is_absolute()
        for path in config["paths"].values()
    )


def test_missing_required_key(tmp_path):
    """Verify that missing required keys raise a clear error."""
    config_file = tmp_path / "config.yaml"

    config_file.write_text(
        yaml.safe_dump({"cities": [], "paths": {}}),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError, match="Missing required config key"
    ):
        load_config(config_file)
