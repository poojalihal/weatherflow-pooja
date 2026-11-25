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
