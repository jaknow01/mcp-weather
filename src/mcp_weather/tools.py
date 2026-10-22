"""Weather tools: current conditions (OpenWeather via pyowm), local date/time, and forecasts
(Open-Meteo after Nominatim geocoding). Blocking clients run in threads with timeouts."""

import asyncio
import logging
import os
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

import requests
from pyowm import OWM

from mcp_weather.forecast import get_forecast
from mcp_weather.server import server

logger = logging.getLogger(__name__)

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_USER_AGENT = "jarvis-mcp-weather (https://github.com/jaknow01/mcp-weather)"


def _timezone() -> ZoneInfo:
    return ZoneInfo(os.getenv("TIMEZONE") or "Europe/Warsaw")


def _observation_dict(observation) -> dict:
    """pyowm's Observation → plain JSON-able dict (location + weather fields)."""
    loc = observation.location
    return {
        "location": {"name": loc.name, "country": loc.country, "lat": loc.lat, "lon": loc.lon},
        "weather": observation.weather.to_dict(),
    }


@server.tool()
async def current_weather(city: str = "Warsaw") -> dict:
    """
    Description:
        This tool is used to get the current weather conditions in a specified city.

    Parameters:
    city: str = "Warsaw"
        Name of the city where the weather conditions are to be checked.
        Unless specified otherwise by the user the default city is Warsaw.
        Return the city name in nominative form (base form) — do not inflect or decline it.

    Output:
        JSON object with current weather conditions in a specified place: the matched
        location (name, country, coordinates) and the weather fields (status, detailed
        status, temperature in Kelvin, humidity, pressure, wind, clouds, rain/snow, sunrise
        and sunset as Unix times).
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return {"message": "Current weather is not configured on this server (no OpenWeather key)."}
    manager = OWM(api_key).weather_manager()
    logger.info("Getting weather at %s", city)
    try:
        observation = await asyncio.wait_for(asyncio.to_thread(manager.weather_at_place, city), timeout=20)
    except Exception as e:  # never echo the error text: pyowm errors can carry the request URL (appid)
        logger.warning("Couldn't get weather at %s (%s)", city, type(e).__name__)
        return {"message": f"Couldnt get weather at {city}", "exception": type(e).__name__}
    return _observation_dict(observation)


@server.tool()
async def get_current_date_and_time() -> dict:
    """
    Description:
        This tool is used to obtain today's date and current time in the server's timezone
        (Europe/Warsaw unless configured otherwise). Use it to turn relative days such as
        "today", "tomorrow" or a weekday name into concrete dates before reading a forecast.

    Output:
        JSON object with the current local date, time, weekday and ISO 8601 timestamp.
    """
    now = datetime.now(_timezone())
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": now.strftime("%A"),
        "iso": now.isoformat(),
    }


@server.tool()
async def weather_forecast(forecast_days: Literal["1", "3", "7"],
                           forecast_type: Literal["hourly", "daily"],
                           city: str = "Warsaw") -> dict:
    """
    Description:
        This tool is used to check a current weather forecast in a given location, for 1, 3
        or 7 days ahead, hourly or daily. Timestamps in the result are local to the location;
        match them to the dates the user means (call get_current_date_and_time first if you
        do not know today's date).

    Parameters:
    forecast_days: Literal["1", "3", "7"]
        How long into the future should the forecast reach measured in days.

    forecast_type: Literal["hourly", "daily"]
        Time intervals in which the forecast will be divided. When asking for a short-term forecast
        more granular data obtained with 'hourly' may be more optimal wheras for long-term forecast
        it usually is better to provide 'daily' intervals.

    city: str = "Warsaw"
        Name of the city where the weather conditions are to be checked.
        Unless specified otherwise by the user the default city is Warsaw. The city name should be in polish.
        Return the city name in nominative form (base form) — do not inflect or decline it.

    Output:
        JSON object with the weather forecast made according to specifications: for each
        matched location (up to 3) the variables per time step (daily: max/min temperature,
        weather code, sunrise, sunset, UV index, rain and snowfall sums; hourly: temperature,
        apparent temperature, weather code, precipitation) and their timestamps.
    """
    def _geolocate():
        resp = requests.get(_NOMINATIM_URL, params={"q": city, "format": "json"},
                            headers={"User-Agent": _USER_AGENT, "Accept": "application/json"}, timeout=10)
        resp.raise_for_status()
        return resp.json()

    logger.info("Geolocating %s", city)
    try:
        geolocation = await asyncio.to_thread(_geolocate)
    except Exception as e:
        logger.warning("Couldn't geolocate %s (%s)", city, type(e).__name__)
        return {"message": f"Couldnt geolocate this location {city}", "error": type(e).__name__}

    places = [{"name": r["display_name"], "long": r["lon"], "lat": r["lat"]} for r in geolocation]
    if not places:
        return {"message": f"No location found for {city}"}
    multiple = len(places) > 1
    places = places[:3]

    forecasts = await asyncio.gather(*(get_forecast(p, forecast_days, forecast_type) for p in places))
    result = {"Message": f"Successfully obtained weather forecasts for {city}", "Forecast": forecasts}
    if multiple:
        names = ", ".join(p["name"] for p in places)
        result["Note"] = (f"Multiple geolocations have been found for {city}. If they are not actually "
                          f"the same city listed out multiple times inform the user about this. "
                          f"Location names: {names}")
    return result
