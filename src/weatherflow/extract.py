"""Extract weather data and save raw API responses."""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


def fetch_city(city: dict, api: dict) -> dict:
    """Fetch weather data with retries for transient request failures."""
    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "hourly": ",".join(api["hourly_variables"]),
        "past_days": api["past_days"],
        "forecast_days": api["forecast_days"],
        "timezone": api["timezone"],
    }

    return _request_json(
        api["forecast_url"],
        params,
        api,
        city["name"],
    )


def _request_json(
    url: str,
    params: dict,
    api: dict,
    city_name: str,
) -> dict:
    """Request JSON using the shared transient retry policy."""

    max_retries = api["max_retries"]

    for attempt in range(max_retries + 1):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=api["timeout_seconds"],
            )

            response.raise_for_status()
            return response.json()

        except requests.HTTPError as error:
            status = (
                error.response.status_code
                if error.response is not None
                else None
            )

            # Retry server errors only.
            if status is None or not 500 <= status < 600:
                raise

            last_error = error

        except (requests.Timeout, requests.ConnectionError) as error:
            last_error = error

        if attempt < max_retries:
            wait = 2 ** attempt

            logger.warning(
                "%s: request attempt %s failed (%s); retrying in %s seconds",
                city_name,
                attempt + 1,
                last_error,
                wait,
            )

            time.sleep(wait)

    raise last_error



def fetch_window(
    city: dict,
    api: dict,
    start,
    end,
    *,
    archive: bool = False,
) -> dict:
    """Fetch an explicit inclusive UTC observation window."""

    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "hourly": ",".join(api["hourly_variables"]),
        "timezone": "UTC",
    }

    if archive:
        url = api["archive_url"]

        params.update({
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
        })

    else:
        url = api["forecast_url"]

        params.update({
            "start_hour": start.strftime("%Y-%m-%dT%H:%M"),
            "end_hour": end.strftime("%Y-%m-%dT%H:%M"),
        })

    return _request_json(
        url,
        params,
        api,
        city["name"],
    )


def save_raw(city_name: str, payload: dict, raw_dir: Path) -> Path:
    """Save the complete API response without overwriting existing files."""
    now = datetime.now(timezone.utc)

    date_folder = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%Y%m%dT%H%M%S")

    output_folder = raw_dir / date_folder
    output_folder.mkdir(parents=True, exist_ok=True)

    output_file = output_folder / f"{city_name.lower()}_{timestamp}.json"

    counter = 1

    while output_file.exists():
        output_file = output_folder / (
            f"{city_name.lower()}_{timestamp}_{counter}.json"
        )
        counter += 1

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    return output_file


def extract(config: dict) -> tuple[list[tuple[str, dict]], list[str]]:
    """Extract weather data and return successful and failed cities."""
    results = []
    failed = []

    for city in config["cities"]:
        city_name = city["name"]

        try:
            logger.info("Fetching weather for %s...", city_name)
            payload = fetch_city(city, config["api"])

        except requests.RequestException as error:
            logger.error("%s: extraction failed: %s", city_name, error)
            failed.append(city_name)
            logger.warning("Continuing with the next city...")
            continue

        saved_file = save_raw(
            city_name,
            payload,
            config["paths"]["raw_dir"],
        )

        hourly_records = len(payload["hourly"]["time"])

        results.append((city_name, payload))

        logger.info(
            "Success: %s - %s hourly records saved to %s",
            city_name,
            hourly_records,
            saved_file,
        )

    logger.info(
        "Extraction summary: %s successful, %s failed",
        len(results),
        len(failed),
    )

    return results, failed
