
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = "https://api.open-meteo.com/v1/forecast"

CITIES = [
    {"name": "Birmingham", "latitude": 52.48142, "longitude": -1.89983},
    {"name": "Cardiff", "latitude": 51.48, "longitude": -3.18},
    {"name": "Edinburgh", "latitude": 55.95206, "longitude": -3.19648},
    {"name": "London", "latitude": 51.50853, "longitude": -0.12574},
    {"name": "Manchester", "latitude": 53.48095, "longitude": -2.23743},
]


def fetch_city(city: dict) -> dict:
    """Fetch the weather forecast for one city."""

    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "hourly": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "apparent_temperature,"
            "precipitation,"
            "wind_speed_10m,"
            "weather_code"
        ),
        "past_days": 1,
        "forecast_days": 1,
        "timezone": "Europe/London",
    }

    response = requests.get(BASE_URL, params=params, timeout=10)
    response.raise_for_status()

    return response.json()


def save_raw(city_name: str, payload: dict) -> Path:
    """Save the complete API response as a raw JSON file."""

    now = datetime.now(timezone.utc)

    date_folder = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%Y%m%dT%H%M%S")

    output_folder = Path("data") / "raw" / date_folder
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


if __name__ == "__main__":

    for city in CITIES:
        city_name = city["name"]

        try:
            print(f"Fetching weather for {city_name}...")

            weather_data = fetch_city(city)

            saved_file = save_raw(city_name, weather_data)

            hourly_records = len(weather_data["hourly"]["time"])

            print(
                f"Success: {city_name} - "
                f"{hourly_records} hourly records saved to {saved_file}"
            )

        except requests.RequestException as error:
            print(f"Error fetching {city_name}: {error}")
            print("Continuing with the next city...")
