# WeatherFlow Data Dictionary

## Dataset overview

- **Source:** Open-Meteo Forecast API
- **Source URL:** https://api.open-meteo.com/v1/forecast
- **Licence:** CC BY 4.0
- **Refresh frequency:** Hourly extraction (as scheduled or manually run)
- **Grain:** One row per city per hour
- **Cities:** London, Manchester, Birmingham, Edinburgh and Cardiff
- **Timezone:** Europe/London
- **Dataset size:** 240 rows and 10 columns
- **Records per city:** 48 hourly records

## Column definitions

| Column | Type | Unit | Description | Example | Nullable? | Source |
|---|---|---|---|---|---|---|
| `time` | datetime | Europe/London local time | Start time of the hourly period | `2026-11-17T14:00` | No | Open-Meteo `hourly.time` |
| `temperature_2m` | float64 | °C | Air temperature 2 metres above ground | `8.4` | Yes | Open-Meteo `hourly.temperature_2m` |
| `relative_humidity_2m` | int64 | % | Relative humidity at 2 metres above ground | `80` | Yes | Open-Meteo `hourly.relative_humidity_2m` |
| `apparent_temperature` | float64 | °C | Feels-like temperature, accounting for environmental conditions | `6.5` | Yes | Open-Meteo `hourly.apparent_temperature` |
| `precipitation` | float64 | mm | Total precipitation during the preceding hour | `0.2` | Yes | Open-Meteo `hourly.precipitation` |
| `wind_speed_10m` | float64 | km/h | Wind speed at 10 metres above ground | `15.0` | Yes | Open-Meteo `hourly.wind_speed_10m` |
| `weather_code` | int64 | WMO code | Numeric description of weather conditions | `3` | Yes | Open-Meteo `hourly.weather_code` |
| `city` | str | Not applicable | Name of the city associated with the observation | `London` | No | `CITIES` list in `extract.py` |
| `latitude` | float64 | Decimal degrees | Latitude of the requested city location | `51.5085` | No | Open-Meteo response metadata |
| `longitude` | float64 | Decimal degrees | Longitude of the requested city location | `-0.1257` | No | Open-Meteo response metadata |

## Notes

- Weather measurements are taken directly from the Open-Meteo hourly response.
- Units are obtained from the `hourly_units` object in each raw JSON response.
- `weather_code` follows the WMO weather interpretation code system.
- The `time` values use the Europe/London timezone requested from the API.
- The dataset contains no missing values across all 10 columns in the current profiling results.
- The `time` column was converted from a string to a datetime data type during notebook processing.
- The `city`, `latitude` and `longitude` columns are added during the flattening process using the city name and API response metadata.
- Nullable indicates whether a field can contain missing values. All columns had zero missing values in the current dataset, although weather measurements may be nullable in future API responses.