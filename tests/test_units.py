"""Tests for units."""

from __future__ import annotations

import pytest

from weather import Imperial, Metric, UnitSystem, ValidationError, compass, unit_system
from weather.units import celsius_to_fahrenheit, kmh_to_mph, mm_to_inches


def test_conversions():
    assert celsius_to_fahrenheit(0) == 32
    assert celsius_to_fahrenheit(100) == 212
    assert celsius_to_fahrenheit(-40) == -40
    assert kmh_to_mph(1.609344) == pytest.approx(1)
    assert mm_to_inches(25.4) == pytest.approx(1)


def test_metric():
    units = Metric()
    assert units.temperature(12.4) == "12°C"
    assert units.speed(14.6) == "15 km/h"
    assert units.rain(2.345) == "2.3 mm"
    assert units.temperature_value(10) == 10


def test_imperial():
    units = Imperial()
    assert units.temperature(20) == "68°F"
    assert units.speed(16.09) == "10 mph"
    assert units.rain(25.4) == "1.00 in"
    assert units.temperature_value(0) == 32


@pytest.mark.parametrize("name, cls", [("metric", Metric), (" Imperial ", Imperial)])
def test_pick_by_name(name, cls):
    assert isinstance(unit_system(name), cls)
    assert isinstance(unit_system(name), UnitSystem)


def test_unknown_units():
    with pytest.raises(ValidationError, match="metric or imperial"):
        unit_system("kelvin")


@pytest.mark.parametrize("degrees, point", [
    (0, "N"), (44, "NE"), (90, "E"), (135, "SE"), (180, "S"), (225, "SW"),
    (270, "W"), (315, "NW"), (350, "N"), (360, "N"), (-90, "W"),
])
def test_compass(degrees, point):
    assert compass(degrees) == point
