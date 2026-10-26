"""The dashboard as a web page.

HtmlDashboard draws the same forecast as TextDashboard, but as one HTML
file you can open in any browser. Everything is inside the one file (the
styles and the chart too), so it can be emailed or opened offline.

The temperature chart is SVG, which is a picture made of instructions like
"draw a line from here to here". The browser draws it, so no chart library
is needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from html import escape
from pathlib import Path
from typing import Callable, Sequence

from .alerts import Alert
from .dashboard import OLD_AFTER_MINUTES, DashboardRenderer, age_text, day_name
from .files import write_safely
from .models import Forecast
from .units import Metric, UnitSystem, compass

STYLE = """
body { font-family: Segoe UI, Arial, sans-serif; background: #f2f5f9; color: #1d2733;
       margin: 0; padding: 24px; }
main { max-width: 860px; margin: 0 auto; }
header h1 { margin: 0; font-size: 28px; }
header p { margin: 4px 0 0; color: #5a6878; }
header p.old { color: #b4541a; }
section { background: #fff; border-radius: 10px; padding: 16px 20px; margin-top: 16px;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08); }
h2 { font-size: 18px; margin: 0 0 12px; }
.now { display: flex; align-items: baseline; gap: 16px; flex-wrap: wrap; }
.now .temp { font-size: 48px; font-weight: 600; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid #e3e8ef; }
th { color: #5a6878; font-weight: 600; }
td.num, th.num { text-align: right; }
ul.alerts { list-style: none; padding: 0; margin: 0; }
ul.alerts li { padding: 8px 12px; border-radius: 6px; margin-bottom: 6px; }
.info { background: #e6f0fb; }
.warning { background: #fdf1d8; }
.danger { background: #fbe1df; }
svg { width: 100%; height: auto; }
footer { margin-top: 16px; font-size: 13px; color: #5a6878; }
"""


@dataclass(frozen=True)
class ChartSize:
    """How big the chart is, in SVG units. The browser scales it to fit."""

    width: int = 760
    height: int = 260
    margin: int = 40
    label_space: int = 28   # room under the chart for the day names


class TemperatureChart:
    """Draws the highs and lows as two lines, with the rain chance as bars
    underneath. Kept in its own class so the page and the chart can change
    without getting in each other's way."""

    HIGH_COLOUR = "#d9534f"
    LOW_COLOUR = "#3b7dd8"
    RAIN_COLOUR = "#9cc3ea"

    def __init__(self, size: ChartSize | None = None) -> None:
        self.size = size or ChartSize()

    def draw(self, forecast: Forecast, units: UnitSystem) -> str:
        size = self.size
        today = forecast.current.time.date()
        highs = [units.temperature_value(d.high) for d in forecast.days]
        lows = [units.temperature_value(d.low) for d in forecast.days]
        top, bottom = max(highs), min(lows)
        span = (top - bottom) or 1
        plot_height = size.height - 2 * size.margin - size.label_space
        step = (size.width - 2 * size.margin) / max(len(forecast.days) - 1, 1)

        def x(index: int) -> float:
            return round(size.margin + index * step, 1)

        def y(value: float) -> float:
            # SVG counts down from the top, so warmer means a smaller y.
            return round(size.margin + (top - value) / span * plot_height, 1)

        parts = [f'<svg viewBox="0 0 {size.width} {size.height}" role="img" '
                 f'aria-label="Highs and lows for the days ahead">']

        # Rain chance bars first, so the lines are drawn on top of them.
        bar_width = max(step * 0.4, 6)
        floor = size.margin + plot_height
        for index, day in enumerate(forecast.days):
            bar = round(day.rain_chance / 100 * plot_height, 1)
            parts.append(f'<rect class="rain" x="{round(x(index) - bar_width / 2, 1)}" '
                         f'y="{round(floor - bar, 1)}" width="{round(bar_width, 1)}" '
                         f'height="{bar}" fill="{self.RAIN_COLOUR}" opacity="0.5">'
                         f'<title>{day.rain_chance}% chance of rain</title></rect>')

        for values, colour, name in ((highs, self.HIGH_COLOUR, "high"),
                                     (lows, self.LOW_COLOUR, "low")):
            points = " ".join(f"{x(i)},{y(v)}" for i, v in enumerate(values))
            parts.append(f'<polyline class="{name}" points="{points}" fill="none" '
                         f'stroke="{colour}" stroke-width="3"/>')

        for index, day in enumerate(forecast.days):
            parts.append(_dot(x(index), y(highs[index]), self.HIGH_COLOUR,
                              units.temperature(day.high), above=True))
            parts.append(_dot(x(index), y(lows[index]), self.LOW_COLOUR,
                              units.temperature(day.low), above=False))
            parts.append(f'<text x="{x(index)}" y="{size.height - 12}" text-anchor="middle" '
                         f'font-size="13">{escape(day_name(day.day, today))}</text>')

        parts.append("</svg>")
        return "".join(parts)


def _dot(x: float, y: float, colour: str, label: str, above: bool) -> str:
    text_y = round(y - 10 if above else y + 20, 1)
    return (f'<circle cx="{x}" cy="{y}" r="4" fill="{colour}"/>'
            f'<text x="{x}" y="{text_y}" text-anchor="middle" font-size="12">'
            f'{escape(label)}</text>')


class HtmlDashboard(DashboardRenderer):
    """A dashboard as a single web page."""

    def __init__(self, chart: TemperatureChart | None = None,
                 clock: Callable[[], datetime] | None = None) -> None:
        self.chart = chart or TemperatureChart()
        self._clock = clock or datetime.now

    def render(self, forecast: Forecast, alerts: Sequence[Alert] = (),
               units: UnitSystem | None = None) -> str:
        units = units or Metric()
        today = forecast.current.time.date()
        body = "\n".join([
            self._header(forecast),
            self._now(forecast, units),
            f"<section><h2>Temperature</h2>{self.chart.draw(forecast, units)}</section>",
            self._days(forecast, units, today),
            self._alerts(alerts, today),
            self._summary(forecast, units, today),
            '<footer>Weather data by <a href="https://open-meteo.com">Open-Meteo</a>.</footer>',
        ])
        title = escape(f"Weather for {forecast.location.name}")
        return ("<!DOCTYPE html>\n"
                '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                f"<title>{title}</title>\n<style>{STYLE}</style>\n</head>\n"
                f"<body>\n<main>\n{body}\n</main>\n</body>\n</html>\n")

    def save(self, path: str | Path, forecast: Forecast, alerts: Sequence[Alert] = (),
             units: UnitSystem | None = None) -> Path:
        """Write the page to a file and return where it went."""
        path = Path(path)
        write_safely(path, self.render(forecast, alerts, units))
        return path

    # ------------------------------------------------------------------

    def _header(self, forecast: Forecast) -> str:
        now = self._clock()
        updated = f"Updated {age_text(forecast.fetched_at, now)}"
        old = (now - forecast.fetched_at).total_seconds() > OLD_AFTER_MINUTES * 60
        if old:
            updated += " (saved copy, may be out of date)"
        css = ' class="old"' if old else ""
        return (f"<header><h1>{escape(forecast.location.label)}</h1>"
                f"<p{css}>{escape(updated)}</p></header>")

    def _now(self, forecast: Forecast, units: UnitSystem) -> str:
        now = forecast.current
        details = (f"Feels like {units.temperature(now.feels_like)} · "
                   f"Humidity {now.humidity}% · "
                   f"Wind {units.speed(now.wind_speed)} from the {compass(now.wind_direction)}")
        if now.precipitation > 0:
            details += f" · Rain in the last hour {units.rain(now.precipitation)}"
        return ('<section><h2>Right now</h2><div class="now">'
                f'<span class="temp">{escape(units.temperature(now.temperature))}</span>'
                f"<span>{escape(now.code.description)}</span></div>"
                f"<p>{escape(details)}</p></section>")

    def _days(self, forecast: Forecast, units: UnitSystem, today: date) -> str:
        rows = []
        for d in forecast.days:
            cells = [day_name(d.day, today), d.code.description]
            numbers = [units.temperature(d.high), units.temperature(d.low),
                       f"{d.rain_chance}% {units.rain(d.rain_total)}", units.speed(d.wind_max)]
            rows.append("<tr>" + "".join(f"<td>{escape(c)}</td>" for c in cells)
                        + "".join(f'<td class="num">{escape(n)}</td>' for n in numbers) + "</tr>")
        head = ("<tr><th>Day</th><th>Sky</th><th class=\"num\">High</th><th class=\"num\">Low</th>"
                "<th class=\"num\">Rain</th><th class=\"num\">Wind</th></tr>")
        return f"<section><h2>Next days</h2><table>{head}{''.join(rows)}</table></section>"

    def _alerts(self, alerts: Sequence[Alert], today: date) -> str:
        if not alerts:
            return "<section><h2>Alerts</h2><p>No weather alerts.</p></section>"
        items = "".join(
            f'<li class="{alert.severity.name.lower()}"><strong>{escape(alert.severity.label)}'
            f" · {escape(day_name(alert.day, today))}: {escape(alert.title)}.</strong> "
            f"{escape(alert.message)}</li>"
            for alert in alerts)
        return f'<section><h2>Alerts</h2><ul class="alerts">{items}</ul></section>'

    def _summary(self, forecast: Forecast, units: UnitSystem, today: date) -> str:
        dry = [day_name(d.day, today) for d in forecast.dry_days()]
        lines = [
            f"Warmest: {day_name(forecast.warmest.day, today)} at "
            f"{units.temperature(forecast.warmest.high)}",
            f"Wettest: {day_name(forecast.wettest.day, today)} with "
            f"{units.rain(forecast.wettest.rain_total)}",
            f"Total rain: {units.rain(forecast.total_rain)}",
            f"Dry days: {', '.join(dry) if dry else 'none, keep a coat handy'}",
        ]
        items = "".join(f"<li>{escape(line)}</li>" for line in lines)
        return f"<section><h2>This week</h2><ul>{items}</ul></section>"
