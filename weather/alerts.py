"""Weather alerts: warnings worth knowing about, like frost or strong wind.

Each kind of alert is its own small rule class. The AlertChecker runs a
list of rules over a forecast and gathers whatever they find. A new kind of
alert is a new rule added to the list, nothing else changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Iterable

from .codes import Condition
from .models import DailyForecast, Forecast


class Severity(Enum):
    """How serious an alert is. The number makes them easy to sort."""

    INFO = 1
    WARNING = 2
    DANGER = 3

    @property
    def label(self) -> str:
        return self.name.title()


@dataclass(frozen=True)
class Alert:
    day: date
    title: str
    message: str
    severity: Severity


class AlertRule(ABC):
    """Looks at a forecast and returns any alerts it finds."""

    def check(self, forecast: Forecast) -> list[Alert]:
        """Most rules look at one day at a time, so by default each day is
        passed to check_day. A rule that needs the whole forecast can
        override this instead."""
        found = (self.check_day(day) for day in forecast.days)
        return [alert for alert in found if alert is not None]

    @abstractmethod
    def check_day(self, day: DailyForecast) -> Alert | None:
        """An alert for this day, or None."""


class FrostRule(AlertRule):
    def __init__(self, below: float = 0) -> None:
        self.below = below

    def check_day(self, day: DailyForecast) -> Alert | None:
        if day.low > self.below:
            return None
        severity = Severity.DANGER if day.low <= self.below - 5 else Severity.WARNING
        return Alert(day.day, "Frost", "Icy surfaces likely. Cover plants and check the car.",
                     severity)


class HeatRule(AlertRule):
    def __init__(self, warm: float = 28, hot: float = 32) -> None:
        self.warm, self.hot = warm, hot

    def check_day(self, day: DailyForecast) -> Alert | None:
        if day.high < self.warm:
            return None
        severity = Severity.DANGER if day.high >= self.hot else Severity.WARNING
        return Alert(day.day, "Heat", "Drink plenty of water and stay out of the midday sun.",
                     severity)


class WindRule(AlertRule):
    def __init__(self, strong: float = 50, gale: float = 75) -> None:
        self.strong, self.gale = strong, gale

    def check_day(self, day: DailyForecast) -> Alert | None:
        if day.wind_max < self.strong:
            return None
        severity = Severity.DANGER if day.wind_max >= self.gale else Severity.WARNING
        return Alert(day.day, "Strong wind", "Tie down loose things outside. Travel may be slow.",
                     severity)


class HeavyRainRule(AlertRule):
    def __init__(self, heavy: float = 10, flooding: float = 25) -> None:
        self.heavy, self.flooding = heavy, flooding

    def check_day(self, day: DailyForecast) -> Alert | None:
        if day.rain_total < self.heavy:
            return None
        severity = Severity.DANGER if day.rain_total >= self.flooding else Severity.WARNING
        return Alert(day.day, "Heavy rain", "Puddles and spray on the roads. Flooding is possible.",
                     severity)


class ConditionRule(AlertRule):
    """Alerts for a kind of weather, like storms or snow."""

    def __init__(self, condition: Condition, title: str, message: str,
                 severity: Severity = Severity.WARNING) -> None:
        self.condition, self.title, self.message, self.severity = condition, title, message, severity

    def check_day(self, day: DailyForecast) -> Alert | None:
        if day.code.condition is not self.condition:
            return None
        return Alert(day.day, self.title, self.message, self.severity)


class UmbrellaRule(AlertRule):
    """A friendly tip for today only. Not worth repeating for every rainy day."""

    def __init__(self, chance: int = 60) -> None:
        self.chance = chance

    def check(self, forecast: Forecast) -> list[Alert]:
        alert = self.check_day(forecast.today)
        return [alert] if alert else []

    def check_day(self, day: DailyForecast) -> Alert | None:
        if day.rain_chance < self.chance:
            return None
        return Alert(day.day, "Umbrella", f"{day.rain_chance}% chance of rain today.", Severity.INFO)


def default_rules() -> list[AlertRule]:
    return [
        FrostRule(), HeatRule(), WindRule(), HeavyRainRule(),
        ConditionRule(Condition.STORM, "Thunderstorm", "Lightning is possible. Avoid open ground."),
        ConditionRule(Condition.SNOW, "Snow", "Allow extra time for travel."),
        UmbrellaRule(),
    ]


class AlertChecker:
    def __init__(self, rules: Iterable[AlertRule] | None = None) -> None:
        self._rules = tuple(rules) if rules is not None else tuple(default_rules())

    @property
    def rules(self) -> tuple[AlertRule, ...]:
        return self._rules

    def check(self, forecast: Forecast) -> list[Alert]:
        """Every alert from every rule, soonest first, most serious first on each day."""
        alerts = [alert for rule in self._rules for alert in rule.check(forecast)]
        return sorted(alerts, key=lambda a: (a.day, -a.severity.value, a.title))
