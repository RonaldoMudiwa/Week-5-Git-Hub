"""Tests for weather codes."""

from __future__ import annotations

import pytest

from weather import Condition, describe, known_codes


@pytest.mark.parametrize("code, words, condition", [
    (0, "Clear sky", Condition.CLEAR),
    (3, "Overcast", Condition.CLOUDY),
    (45, "Fog", Condition.FOG),
    (55, "Heavy drizzle", Condition.DRIZZLE),
    (63, "Rain", Condition.RAIN),
    (81, "Showers", Condition.RAIN),
    (75, "Heavy snow", Condition.SNOW),
    (95, "Thunderstorm", Condition.STORM),
])
def test_known_codes(code, words, condition):
    found = describe(code)
    assert (found.code, found.description, found.condition) == (code, words, condition)
    assert str(found) == words


@pytest.mark.parametrize("code", [4, 100, -3, "3", None, True, 3.0])
def test_unknown_codes_never_crash(code):
    assert describe(code).condition is Condition.UNKNOWN
    assert describe(code).description == "Unknown"


def test_every_code_has_words():
    assert len(known_codes()) == 28
    assert all(describe(c).description != "Unknown" for c in known_codes())


def test_wet_conditions():
    assert Condition.RAIN.is_wet and Condition.SNOW.is_wet and Condition.STORM.is_wet
    assert not Condition.CLEAR.is_wet and not Condition.FOG.is_wet
