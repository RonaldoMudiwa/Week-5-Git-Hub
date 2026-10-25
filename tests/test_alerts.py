"""Tests for weather alerts."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from weather import (
    Alert,
    AlertChecker,
    AlertRule,
    Condition,
    ConditionRule,
    FrostRule,
    HeatRule,
    HeavyRainRule,
    Severity,
    UmbrellaRule,
    WindRule,
    default_rules,
)

from .conftest import make_day, make_forecast

DAY = date(2026, 10, 22)


@pytest.mark.parametrize("rule, day, expected", [
    (FrostRule(), make_day(DAY, low=1), None),
    (FrostRule(), make_day(DAY, low=0), Severity.WARNING),
    (FrostRule(), make_day(DAY, low=-5), Severity.DANGER),
    (HeatRule(), make_day(DAY, high=27.9), None),
    (HeatRule(), make_day(DAY, high=28), Severity.WARNING),
    (HeatRule(), make_day(DAY, high=33), Severity.DANGER),
    (WindRule(), make_day(DAY, wind_max=49), None),
    (WindRule(), make_day(DAY, wind_max=50), Severity.WARNING),
    (WindRule(), make_day(DAY, wind_max=80), Severity.DANGER),
    (HeavyRainRule(), make_day(DAY, rain_total=9.9), None),
    (HeavyRainRule(), make_day(DAY, rain_total=10), Severity.WARNING),
    (HeavyRainRule(), make_day(DAY, rain_total=30), Severity.DANGER),
    (UmbrellaRule(), make_day(DAY, rain_chance=59), None),
    (UmbrellaRule(), make_day(DAY, rain_chance=60), Severity.INFO),
])
def test_each_rule(rule, day, expected):
    alert = rule.check_day(day)
    assert (alert.severity if alert else None) is expected


def test_condition_rule():
    rule = ConditionRule(Condition.STORM, "Thunderstorm", "Stay inside.", Severity.DANGER)
    assert rule.check_day(make_day(DAY, code=95)).title == "Thunderstorm"
    assert rule.check_day(make_day(DAY, code=3)) is None


def test_umbrella_is_only_for_today():
    days = [make_day(DAY + timedelta(days=n), rain_chance=90) for n in range(3)]
    assert len(UmbrellaRule().check(make_forecast(days))) == 1


def test_rules_check_every_day():
    days = [make_day(DAY + timedelta(days=n), low=-1) for n in range(3)]
    assert len(FrostRule().check(make_forecast(days))) == 3


def test_custom_limits():
    assert FrostRule(below=5).check_day(make_day(DAY, low=4)) is not None
    assert HeatRule(warm=20, hot=25).check_day(make_day(DAY, high=26)).severity is Severity.DANGER


def test_checker_sorts_by_day_then_most_serious():
    days = [
        make_day(DAY, low=-1, rain_chance=80),
        make_day(DAY + timedelta(days=1), wind_max=90, code=95),
    ]
    alerts = AlertChecker().check(make_forecast(days))
    assert [(a.day.day, a.title) for a in alerts] == [
        (22, "Frost"), (22, "Umbrella"), (23, "Strong wind"), (23, "Thunderstorm")]


def test_calm_week_has_no_alerts(forecast):
    assert AlertChecker().check(forecast) == []


def test_a_new_rule_can_be_added():
    class FogRule(AlertRule):
        def check_day(self, day):
            if day.code.condition is Condition.FOG:
                return Alert(day.day, "Fog", "Drive slowly.", Severity.WARNING)
            return None

    checker = AlertChecker([*default_rules(), FogRule()])
    alerts = checker.check(make_forecast([make_day(DAY, code=45)]))
    assert [a.title for a in alerts] == ["Fog"]
    assert len(checker.rules) == len(default_rules()) + 1


def test_no_rules_no_alerts():
    assert AlertChecker([]).check(make_forecast([make_day(DAY, low=-10)])) == []


def test_severity_labels():
    assert [s.label for s in Severity] == ["Info", "Warning", "Danger"]
