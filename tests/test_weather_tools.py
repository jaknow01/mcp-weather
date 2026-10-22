"""Weather tools with the external clients mocked (no network)."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from conftest import call_tools, text_of
from mcp_weather import tools


class _Weather:
    def to_dict(self):
        return {"status": "Clouds", "temperature": {"temp": 285.1}}


class _Manager:
    def __init__(self, fail=False):
        self.fail = fail

    def weather_at_place(self, city):
        if self.fail:
            raise RuntimeError("http://api.openweathermap.org/data/2.5/weather?appid=SECRET")
        return SimpleNamespace(location=SimpleNamespace(name=city, country="PL", lat=52.2, lon=21.0),
                               weather=_Weather())


@pytest.fixture
def owm(monkeypatch):
    state = {"fail": False}
    monkeypatch.setenv("OPENWEATHER_API_KEY", "test")
    monkeypatch.setattr(tools, "OWM", lambda key: SimpleNamespace(weather_manager=lambda: _Manager(state["fail"])))
    return state


def test_current_weather_returns_plain_dict(owm):
    out = asyncio.run(tools.current_weather("Kraków"))
    assert out["location"]["name"] == "Kraków" and out["weather"]["status"] == "Clouds"
    json.dumps(out)  # serializable over MCP


def test_current_weather_error_does_not_leak_url_or_key(owm):
    owm["fail"] = True
    out = asyncio.run(tools.current_weather("Kraków"))
    assert out["exception"] == "RuntimeError" and "SECRET" not in json.dumps(out)


def test_current_weather_without_key(monkeypatch):
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)
    assert "not configured" in asyncio.run(tools.current_weather())["message"]


def test_date_and_time_in_configured_timezone(monkeypatch):
    monkeypatch.setenv("TIMEZONE", "Europe/Warsaw")
    out = asyncio.run(tools.get_current_date_and_time())
    assert out["iso"].endswith(("+01:00", "+02:00")) and len(out["date"]) == 10


def test_forecast_geolocates_and_caps_locations(monkeypatch):
    places = [{"display_name": f"Place {i}", "lon": "21", "lat": "52"} for i in range(5)]
    monkeypatch.setattr(tools.requests, "get", lambda *a, **k: SimpleNamespace(
        raise_for_status=lambda: None, json=lambda: places))
    seen = []

    async def fake_forecast(place, days, kind):
        seen.append(place["name"])
        return {"time": [], "meta": {}}

    monkeypatch.setattr(tools, "get_forecast", fake_forecast)
    out = asyncio.run(tools.weather_forecast("3", "daily", "Warszawa"))
    assert len(out["Forecast"]) == 3 and len(seen) == 3 and "Multiple geolocations" in out["Note"]


def test_forecast_over_mcp(app, keys, monkeypatch):
    monkeypatch.setattr(tools.requests, "get", lambda *a, **k: SimpleNamespace(
        raise_for_status=lambda: None, json=lambda: [{"display_name": "Warszawa", "lon": "21", "lat": "52"}]))

    async def fake_forecast(place, days, kind):
        return {"temperature_2m_max": [12.0], "time": ["2026-10-23T00:00"]}

    monkeypatch.setattr(tools, "get_forecast", fake_forecast)
    (result,) = call_tools(app, keys["friend"], [("weather_forecast", {"forecast_days": "1", "forecast_type": "daily"})])
    assert not result.is_error and "temperature_2m_max" in text_of(result)
