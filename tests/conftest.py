"""Shared WeatherFlow test fixtures and network protection."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def london_payload() -> dict:
    """Return a genuine London API response trimmed to six hours."""

    path = (
        Path(__file__).parent
        / "fixtures"
        / "open_meteo_london.json"
    )

    return json.loads(
        path.read_text(encoding="utf-8")
    )


@pytest.fixture(autouse=True)
def block_real_http_requests(monkeypatch) -> None:
    """Prevent tests from making accidental real HTTP requests."""

    def blocked_request(*args, **kwargs):
        raise AssertionError(
            "Unexpected real HTTP request during testing. "
            "Mock the external API instead."
        )

    monkeypatch.setattr(
        "requests.sessions.Session.request",
        blocked_request,
    )
