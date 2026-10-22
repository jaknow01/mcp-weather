"""Open-Meteo forecast fetch for weather_forecast (blocking client run in a thread)."""

import asyncio
import logging
from datetime import timedelta, datetime
from typing import Literal

import openmeteo_requests
import requests_cache
from retry_requests import retry

logger = logging.getLogger(__name__)


async def get_forecast(params: dict,
                       forecast_days: Literal["1", "3", "7"],
                       forecast_type: Literal["hourly", "daily"]
                       ) -> dict:

    # In-memory cache: the container's working dir is not writable.
    cache_session = requests_cache.CachedSession(backend="memory", expire_after=3600)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)

    forecast_url = "https://api.open-meteo.com/v1/forecast"

    if forecast_type == "daily":
        type_params = ["temperature_2m_max", "temperature_2m_min", "weather_code", "sunrise", "sunset", "uv_index_max", "rain_sum", "snowfall_sum"]
    else:
        type_params = ["temperature_2m", "apparent_temperature", "weather_code", "precipitation"]

    request_params = {
        "latitude": params["lat"],
        "longitude": params["long"],
        forecast_type: type_params,
        "forecast_days": forecast_days
    }

    try:
        # openmeteo_requests is blocking (with retries); keep it off the event loop.
        response = await asyncio.to_thread(openmeteo.weather_api, url=forecast_url, params=request_params)
        response = response[0]
    except Exception as e:
        logger.warning("Error while getting the forecast (%s)", type(e).__name__)
        return []

    data = response.Daily() if forecast_type == "daily" else response.Hourly()

    result = {}
    for i, variable in enumerate(type_params):
        value = data.Variables(i).ValuesAsNumpy()
        if hasattr(value, "tolist"):
            result[variable] = value.tolist()
        else:
            result[variable] = [value]

    start_time = datetime.fromtimestamp(data.Time())
    end_time = datetime.fromtimestamp(data.TimeEnd())
    interval = timedelta(seconds=data.Interval())

    timestamps = []
    current = start_time
    while current < end_time:
        timestamps.append(current.isoformat())
        current += interval

    result["time"] = timestamps

    result["meta"] = {
        "lat": response.Latitude(),
        "long": response.Longitude(),
        "elevation": response.Elevation(),
        "utc_offset": response.UtcOffsetSeconds()
    }

    logger.info("Forecast obtained")

    return result
