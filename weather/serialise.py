"""Turning weather objects into plain dictionaries and back.

JSON only understands text, numbers, lists and dictionaries. These
functions translate our objects into that, so they can be saved to a file
and loaded again later exactly as they were.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .codes import describe
from .models import CurrentWeather, DailyForecast, Forecast, Location


def location_to_dict(place: Location) -> dict[str, Any]:
    return {"name": place.name, "latitude": place.latitude, "longitude": place.longitude,
            "country": place.country, "region": place.region, "timezone": place.timezone}


def location_from_dict(data: dict[str, Any]) -> Location:
    return Location(data["name"], data["latitude"], data["longitude"], data.get("country", ""),
                    data.get("region", ""), data.get("timezone", "auto"))


def forecast_to_dict(forecast: Forecast) -> dict[str, Any]:
    now = forecast.current
    return {
        "location": location_to_dict(forecast.location),
        "fetched_at": forecast.fetched_at.isoformat(),
        "current": {
            "time": now.time.isoformat(), "code": now.code.code,
            "temperature": now.temperature, "feels_like": now.feels_like,
            "humidity": now.humidity, "wind_speed": now.wind_speed,
            "wind_direction": now.wind_direction, "precipitation": now.precipitation,
        },
        "days": [
            {"day": d.day.isoformat(), "code": d.code.code, "high": d.high, "low": d.low,
             "rain_chance": d.rain_chance, "rain_total": d.rain_total, "wind_max": d.wind_max,
             "sunrise": _iso(d.sunrise), "sunset": _iso(d.sunset)}
            for d in forecast.days
        ],
    }


def forecast_from_dict(data: dict[str, Any]) -> Forecast:
    now = data["current"]
    current = CurrentWeather(datetime.fromisoformat(now["time"]), describe(now["code"]),
                             now["temperature"], now["feels_like"], now["humidity"],
                             now["wind_speed"], now["wind_direction"], now["precipitation"])
    days = [DailyForecast(date.fromisoformat(d["day"]), describe(d["code"]), d["high"], d["low"],
                          d["rain_chance"], d["rain_total"], d["wind_max"],
                          _from_iso(d["sunrise"]), _from_iso(d["sunset"]))
            for d in data["days"]]
    return Forecast(location_from_dict(data["location"]), current, days,
                    datetime.fromisoformat(data["fetched_at"]))


def _iso(moment: datetime | None) -> str | None:
    return moment.isoformat() if moment else None


def _from_iso(text: str | None) -> datetime | None:
    return datetime.fromisoformat(text) if text else None
