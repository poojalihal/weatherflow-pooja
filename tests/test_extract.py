"""Test WeatherFlow API retry behaviour."""

import logging
from unittest.mock import Mock, call

import pytest
import requests

from weatherflow.config import load_config
from weatherflow.extract import fetch_city

logger = logging.getLogger(__name__)


def http_error(status: int) -> requests.HTTPError:
    """Create a simulated HTTP error."""
    response = requests.Response()
    response.status_code = status
    return requests.HTTPError(
        f"HTTP {status}", response=response
    )


@pytest.mark.parametrize("error", [
    requests.Timeout("Simulated timeout"),
    requests.ConnectionError("Simulated connection error"),
    http_error(503),
])
def test_transient_retry(monkeypatch, error):
    """Verify that transient failures are retried."""
    config = load_config()

    response = Mock()
    response.json.return_value = {"success": True}

    get = Mock(side_effect=[error, response])
    sleep = Mock()

    monkeypatch.setattr("weatherflow.extract.requests.get", get)
    monkeypatch.setattr("weatherflow.extract.time.sleep", sleep)

    result = fetch_city(config["cities"][0], config["api"])

    assert result == {"success": True}
    assert get.call_count == 2
    sleep.assert_called_once_with(1)


@pytest.mark.parametrize("status", [400, 404])
def test_no_retry_on_client_error(monkeypatch, status):
    """Verify that client errors are not retried."""
    config = load_config()

    get = Mock(side_effect=http_error(status))
    sleep = Mock()

    monkeypatch.setattr("weatherflow.extract.requests.get", get)
    monkeypatch.setattr("weatherflow.extract.time.sleep", sleep)

    with pytest.raises(requests.HTTPError):
        fetch_city(config["cities"][0], config["api"])

    assert get.call_count == 1
    sleep.assert_not_called()

    logger.info(
        "Mocked HTTP %s: one request, zero retries",
        status,
    )


def test_retry_exhaustion(monkeypatch):
    """Verify the maximum retry count and backoff intervals."""
    config = load_config()

    get = Mock(side_effect=http_error(503))
    sleep = Mock()

    monkeypatch.setattr("weatherflow.extract.requests.get", get)
    monkeypatch.setattr("weatherflow.extract.time.sleep", sleep)

    with pytest.raises(requests.HTTPError):
        fetch_city(config["cities"][0], config["api"])

    assert get.call_count == 4
    assert sleep.call_args_list == [
        call(1), call(2), call(4)
    ]

    logger.info("Mocked HTTP 503: retry limit verified")


def test_fetch_succeeds_after_two_server_errors(
    monkeypatch,
    london_payload,
):
    """Retry two HTTP 503 responses before a successful response."""

    from unittest.mock import Mock, call

    import requests

    from weatherflow.config import load_config
    from weatherflow.extract import fetch_city

    config = load_config()

    city = next(
        city
        for city in config["cities"]
        if city["name"] == "London"
    )

    unavailable = requests.Response()
    unavailable.status_code = 503
    unavailable.url = config["api"]["forecast_url"]

    successful = Mock()
    successful.status_code = 200
    successful.json.return_value = london_payload

    mocked_get = Mock(
        side_effect=[
            unavailable,
            unavailable,
            successful,
        ]
    )

    mocked_sleep = Mock()

    monkeypatch.setattr(
        "weatherflow.extract.requests.get",
        mocked_get,
    )

    monkeypatch.setattr(
        "weatherflow.extract.time.sleep",
        mocked_sleep,
    )

    result = fetch_city(
        city,
        config["api"],
    )

    assert result == london_payload
    assert mocked_get.call_count == 3

    assert mocked_sleep.call_args_list == [
        call(1),
        call(2),
    ]

    request_args = mocked_get.call_args

    assert request_args.args[0] == (
        config["api"]["forecast_url"]
    )

    assert request_args.kwargs["params"]["timezone"] == "UTC"

    assert "is_day" in (
        request_args.kwargs["params"]["hourly"]
    )

    assert request_args.kwargs["timeout"] == (
        config["api"]["timeout_seconds"]
    )


def test_save_raw_writes_complete_json(
    tmp_path,
    london_payload,
):
    """Write a complete response to a temporary raw directory."""

    import json
    from datetime import date

    from weatherflow.extract import save_raw

    raw_dir = tmp_path / "raw"

    output = save_raw(
        "London",
        london_payload,
        raw_dir,
    )

    assert output.exists()
    assert output.suffix == ".json"
    assert output.name.startswith("london_")
    assert output.parent.parent == raw_dir

    # Confirm that the partition folder is a valid ISO date.
    date.fromisoformat(output.parent.name)

    result = json.loads(
        output.read_text(encoding="utf-8")
    )

    assert result == london_payload
    assert len(result["hourly"]["time"]) == 6


def test_save_raw_does_not_overwrite_existing_files(
    tmp_path,
    monkeypatch,
    london_payload,
):
    """Preserve both raw files when saved in the same second."""

    import json
    from datetime import datetime, timezone
    from unittest.mock import Mock

    from weatherflow.extract import save_raw

    fixed_time = datetime(
        2026, 11, 26, 12, 0,
        tzinfo=timezone.utc,
    )

    mocked_datetime = Mock()
    mocked_datetime.now.return_value = fixed_time

    monkeypatch.setattr(
        "weatherflow.extract.datetime",
        mocked_datetime,
    )

    first = save_raw(
        "London",
        london_payload,
        tmp_path,
    )

    second = save_raw(
        "London",
        london_payload,
        tmp_path,
    )

    assert first != second

    assert first.exists()
    assert second.exists()

    assert len(
        list(tmp_path.rglob("*.json"))
    ) == 2

    for path in [first, second]:

        result = json.loads(
            path.read_text(encoding="utf-8")
        )

        assert result == london_payload


def test_extract_preserves_successful_cities_after_failure(
    tmp_path,
    monkeypatch,
    london_payload,
):
    """Return successful and failed cities without losing raw data."""

    import json
    from unittest.mock import Mock

    import requests

    from weatherflow.config import load_config
    from weatherflow.extract import extract

    config = load_config()

    cities = {
        city["name"]: city
        for city in config["cities"]
    }

    config["cities"] = [
        cities["London"],
        cities["Cardiff"],
    ]

    config["paths"]["raw_dir"] = (
        tmp_path / "raw"
    )

    mocked_fetch = Mock(
        side_effect=[
            london_payload,
            requests.ConnectionError(
                "Simulated Cardiff connection failure"
            ),
        ]
    )

    monkeypatch.setattr(
        "weatherflow.extract.fetch_city",
        mocked_fetch,
    )

    successful, failed = extract(config)

    assert mocked_fetch.call_count == 2

    assert successful == [
        ("London", london_payload)
    ]

    assert failed == ["Cardiff"]

    raw_files = list(
        config["paths"]["raw_dir"]
        .rglob("*.json")
    )

    assert len(raw_files) == 1
    assert raw_files[0].name.startswith("london_")

    stored_payload = json.loads(
        raw_files[0].read_text(encoding="utf-8")
    )

    assert stored_payload == london_payload
