
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent

BASE_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_VARIABLES = (
    "temperature_2m,"
    "relative_humidity_2m,"
    "apparent_temperature,"
    "precipitation,"
    "wind_speed_10m,"
    "weather_code"
)

CITIES = [
    {"name": "Birmingham", "latitude": 52.48142, "longitude": -1.89983},
    {"name": "Cardiff", "latitude": 51.48, "longitude": -3.18},
    {"name": "Edinburgh", "latitude": 55.95206, "longitude": -3.19648},
    {"name": "London", "latitude": 51.50853, "longitude": -0.12574},
    {"name": "Manchester", "latitude": 53.48095, "longitude": -2.23743},
]


def fetch_city(
    city: dict,
    max_retries: int = 3,
    timeout: int = 10,
) -> dict:
    """Fetch weather data, retrying temporary API failures.

    Make one initial attempt and up to three retries,
    using exponential backoff.
    """

    if max_retries < 0:
        raise ValueError("max_retries must be non-negative")

    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "hourly": HOURLY_VARIABLES,
        "past_days": 1,
        "forecast_days": 1,
        "timezone": "UTC",
    }

    for attempt in range(max_retries + 1):
        try:
            response = requests.get(
                BASE_URL,
                params=params,
                timeout=timeout,
            )

            response.raise_for_status()

            return response.json()

        except requests.HTTPError as error:
            status = (
                error.response.status_code
                if error.response is not None
                else None
            )

            # Retry only HTTP server errors (5xx).
            if status is None or not 500 <= status < 600:
                raise

            last_error = error

        except (requests.Timeout, requests.ConnectionError) as error:
            last_error = error

        # Wait before retrying, unless all attempts are exhausted.
        if attempt < max_retries:
            wait = 2 ** attempt

            logger.warning(
                "%s: request attempt %s failed (%s); retrying in %s seconds",
                city["name"],
                attempt + 1,
                last_error,
                wait,
            )

            time.sleep(wait)

    # All permitted attempts have failed.
    raise last_error


def save_raw(city_name: str, payload: dict) -> Path:
    """Save the complete API response as a raw JSON file."""

    now = datetime.now(timezone.utc)

    date_folder = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%Y%m%dT%H%M%S")

    output_folder = PROJECT_ROOT / "data" / "raw" / date_folder
    output_folder.mkdir(parents=True, exist_ok=True)

    output_file = output_folder / f"{city_name.lower()}_{timestamp}.json"

    # Avoid overwriting a file if two runs happen in the same second.
    counter = 1
    while output_file.exists():
        output_file = output_folder / (
            f"{city_name.lower()}_{timestamp}_{counter}.json"
        )
        counter += 1

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    return output_file


def extract(
    cities: list[dict] = CITIES,
) -> tuple[list[tuple[str, dict]], list[str]]:
    """Fetch weather data and return successful and failed cities."""

    results = []
    failed = []

    for city in cities:
        city_name = city["name"]

        try:
            logger.info("Fetching weather for %s...", city_name)

            payload = fetch_city(city)

        except requests.RequestException as error:
            logger.error(
                "%s: giving up after request failure: %s",
                city_name,
                error,
            )

            failed.append(city_name)

            logger.warning("Continuing with the next city...")

            continue

        saved_file = save_raw(city_name, payload)

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


if __name__ == "__main__":
    log_folder = PROJECT_ROOT / "logs"
    log_folder.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                log_folder / "pipeline.log",
                encoding="utf-8",
            ),
        ],
    )

    logger.info("Starting WeatherFlow extraction...")

    results, failed = extract()

    if failed:
        logger.error(
            "Extraction FAILED: no data for %s",
            ", ".join(failed),
        )

        sys.exit(1)

    logger.info(
        "Extraction completed successfully for %s cities",
        len(results),
    )

    sys.exit(0)
