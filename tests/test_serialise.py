"""Tests for turning forecasts into dictionaries and back."""

from __future__ import annotations

import json

from weather import forecast_from_dict, forecast_to_dict
from weather.serialise import location_from_dict, location_to_dict

from .conftest import BROMLEY, make_day, make_forecast


def test_forecast_round_trip_through_json(forecast):
    text = json.dumps(forecast_to_dict(forecast))
    assert forecast_from_dict(json.loads(text)) == forecast


def test_missing_sunrise_survives(forecast):
    from dataclasses import replace

    day = replace(make_day(forecast.today.day), sunrise=None, sunset=None)
    plain = make_forecast([day])
    assert forecast_from_dict(forecast_to_dict(plain)).today.sunrise is None


def test_location_round_trip():
    assert location_from_dict(location_to_dict(BROMLEY)) == BROMLEY


def test_location_defaults():
    place = location_from_dict({"name": "X", "latitude": 1, "longitude": 2})
    assert (place.country, place.region, place.timezone) == ("", "", "auto")
