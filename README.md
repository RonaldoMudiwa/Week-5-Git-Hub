# Weather Dashboard

A weather dashboard for the terminal, written in Python using only the
standard library. Live forecasts come from the free
[Open-Meteo](https://open-meteo.com) service, which needs no sign up or key.

Project 5 of a 12 week portfolio. Weeks 1 to 4 covered OOP, SOLID, SQLite
and security. This week is about working with a real web API.

## Status

Day 1 of 7. Weather models, weather codes and units.

## Getting started

```bash
python -m venv .venv
.venv\Scripts\activate           # macOS or Linux: source .venv/bin/activate
pip install -r requirements.txt  # only needed for the tests

pytest                           # run the tests
```

Needs Python 3.10 or newer.

## The weather data

| Class | Holds |
| --- | --- |
| `Location` | A place: name, latitude, longitude, region, country and time zone |
| `CurrentWeather` | Right now: temperature, feels like, humidity, wind, rain, sky |
| `DailyForecast` | One day: high, low, chance of rain, rain total, wind, sunrise, sunset |
| `Forecast` | A place, its current weather and the days ahead |

```python
forecast.warmest            # the hottest day ahead
forecast.wettest            # the rainiest day ahead
forecast.dry_days()         # days with 30% chance of rain or less
forecast.total_rain         # mm expected across the whole forecast
```

Every class is frozen, like a printed weather report, so the dashboard can
never show half updated numbers. Values are checked when they're made, so a
latitude of 200 or a day where the low is above the high is refused straight
away.

## Weather codes

Weather services describe the sky with a number from the World
Meteorological Organization list. `describe(61)` gives "Light rain", and
its `Condition` (`RAIN`) is used to group the weather for alerts. A code
the program doesn't know gives "Unknown" instead of crashing.

## Units

Everything is stored in metric and only changed when it's shown, like
choosing which language to print a report in.

```python
from weather import unit_system

units = unit_system("imperial")
units.temperature(20)    # '68°F'
units.speed(16.09)       # '10 mph'
units.rain(25.4)         # '1.00 in'
```

`Metric` and `Imperial` are two versions of the abstract `UnitSystem`. The
dashboard just asks whichever one it's given, and never checks which.

## Tests

```bash
pytest          # 60 tests
```

## Week plan

| Day | Focus |
| --- | --- |
| 1 | Weather models, weather codes and units |
| 2 | Fetching forecasts from the Open-Meteo API |
| 3 | Caching and favourite places |
| 4 | The text dashboard and weather alerts |
| 5 | HTML dashboard with a chart |
| 6 | Command line interface |
| 7 | Final tests and README |
