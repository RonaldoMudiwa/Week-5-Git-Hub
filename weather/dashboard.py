"""Drawing the dashboard.

DashboardRenderer is the plug. TextDashboard draws it for the terminal.
Another renderer, like an HTML page, can draw the same forecast in its own
way without the forecast or the alerts changing at all.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Callable, Sequence

from .alerts import Alert
from .models import DailyForecast, Forecast
from .units import Metric, UnitSystem, compass

OLD_AFTER_MINUTES = 60  # older than this and the dashboard says it might be out of date


class DashboardRenderer(ABC):
    @abstractmethod
    def render(self, forecast: Forecast, alerts: Sequence[Alert] = (),
               units: UnitSystem | None = None) -> str:
        """The whole dashboard as text."""


def day_name(day: date, today: date) -> str:
    """"Today", "Tomorrow", or e.g. "Mon 27"."""
    gap = (day - today).days
    if gap == 0:
        return "Today"
    if gap == 1:
        return "Tomorrow"
    return day.strftime("%a %d")


def age_text(fetched_at: datetime, now: datetime) -> str:
    minutes = max(int((now - fetched_at).total_seconds() // 60), 0)
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    return f"{hours} hour{'s' if hours != 1 else ''} ago"


class TextDashboard(DashboardRenderer):
    """A dashboard made of plain text, so it works in any terminal.

    Only ordinary characters are used for the chart, so it prints fine even
    on older Windows consoles.
    """

    def __init__(self, width: int = 72, clock: Callable[[], datetime] | None = None) -> None:
        self.width = max(width, 60)
        self._clock = clock or datetime.now

    def render(self, forecast: Forecast, alerts: Sequence[Alert] = (),
               units: UnitSystem | None = None) -> str:
        units = units or Metric()
        sections = [
            self._header(forecast),
            self._now(forecast, units),
            self._days(forecast, units),
            self._chart(forecast, units),
            self._alerts(alerts, forecast),
            self._summary(forecast, units),
        ]
        return "\n\n".join(sections)

    # ------------------------------------------------------------------

    def _rule(self, title: str = "") -> str:
        return f"-- {title} ".ljust(self.width, "-") if title else "-" * self.width

    def _header(self, forecast: Forecast) -> str:
        now = self._clock()
        updated = f"Updated {age_text(forecast.fetched_at, now)}"
        if (now - forecast.fetched_at).total_seconds() > OLD_AFTER_MINUTES * 60:
            updated += " (saved copy, may be out of date)"
        place = forecast.location.label
        return "\n".join(["=" * self.width, place.center(self.width).rstrip(),
                          updated.center(self.width).rstrip(), "=" * self.width])

    def _now(self, forecast: Forecast, units: UnitSystem) -> str:
        now = forecast.current
        wind = f"{units.speed(now.wind_speed)} from the {compass(now.wind_direction)}"
        lines = [
            self._rule("Right now"),
            f"  {units.temperature(now.temperature):<8}{now.code.description}",
            f"  Feels like {units.temperature(now.feels_like)}   "
            f"Humidity {now.humidity}%   Wind {wind}",
        ]
        if now.precipitation > 0:
            lines.append(f"  Rain in the last hour: {units.rain(now.precipitation)}")
        return "\n".join(lines)

    def _days(self, forecast: Forecast, units: UnitSystem) -> str:
        today = forecast.current.time.date()
        lines = [self._rule("Next days"),
                 f"  {'Day':<10}{'Sky':<24}{'High':>6}{'Low':>6}{'Rain':>14}{'Wind':>10}"]
        for d in forecast.days:
            rain = f"{d.rain_chance}% {units.rain(d.rain_total)}"
            lines.append(f"  {day_name(d.day, today):<10}{d.code.description[:23]:<24}"
                         f"{units.temperature(d.high):>6}{units.temperature(d.low):>6}"
                         f"{rain:>14}{units.speed(d.wind_max):>10}")
        return "\n".join(lines)

    def _chart(self, forecast: Forecast, units: UnitSystem) -> str:
        """Each day's low to high drawn as a bar on one shared scale, so the
        warm and cold days stand out at a glance."""
        today = forecast.current.time.date()
        lowest = min(units.temperature_value(d.low) for d in forecast.days)
        highest = max(units.temperature_value(d.high) for d in forecast.days)
        bar_width = self.width - 30
        lines = [self._rule("Temperature")]
        for d in forecast.days:
            bar = temperature_bar(units.temperature_value(d.low), units.temperature_value(d.high),
                                  lowest, highest, bar_width)
            lines.append(f"  {day_name(d.day, today):<10}{units.temperature(d.low):>6} "
                         f"{bar} {units.temperature(d.high)}")
        return "\n".join(lines)

    def _alerts(self, alerts: Sequence[Alert], forecast: Forecast) -> str:
        if not alerts:
            return f"{self._rule('Alerts')}\n  No weather alerts."
        today = forecast.current.time.date()
        lines = [self._rule("Alerts")]
        for alert in alerts:
            lines.append(f"  [{alert.severity.label}] {day_name(alert.day, today)}: "
                         f"{alert.title}. {alert.message}")
        return "\n".join(lines)

    def _summary(self, forecast: Forecast, units: UnitSystem) -> str:
        today = forecast.current.time.date()
        dry = [day_name(d.day, today) for d in forecast.dry_days()]
        return "\n".join([
            self._rule("This week"),
            f"  Warmest: {_named(forecast.warmest, today)} at {units.temperature(forecast.warmest.high)}",
            f"  Wettest: {_named(forecast.wettest, today)} with "
            f"{units.rain(forecast.wettest.rain_total)}",
            f"  Total rain: {units.rain(forecast.total_rain)}",
            f"  Dry days: {', '.join(dry) if dry else 'none, keep a coat handy'}",
        ])


def temperature_bar(low: float, high: float, lowest: float, highest: float, width: int) -> str:
    """Draw low to high as #### inside a row of dots.

        temperature_bar(5, 10, 0, 20, 20)  ->  '.....#####..........'
    """
    span = (highest - lowest) or 1
    start = round((low - lowest) / span * width)
    end = round((high - lowest) / span * width)
    end = max(end, start + 1)  # always show at least one block
    end = min(end, width)
    start = min(start, end - 1)
    return "." * start + "#" * (end - start) + "." * (width - end)


def _named(day: DailyForecast, today: date) -> str:
    return day_name(day.day, today)
