# Weather Dashboard

A weather dashboard for the terminal, written in Python using only the
standard library. Live forecasts come from the free
[Open-Meteo](https://open-meteo.com) service, which needs no sign up or key.

Project 5 of a 12 week portfolio. Weeks 1 to 4 covered OOP, SOLID, SQLite
and security. This week is about working with a real web API.

## Status

Day 3 of 7. Weather models, weather codes, units, live forecasts from
Open-Meteo, caching and favourite places.

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

## Getting forecasts

```python
from weather import OpenMeteoProvider

provider = OpenMeteoProvider()
bromley = provider.find_place("Bromley")       # best match
provider.find_places("Bromley")               # every match: UK, Australia...
forecast = provider.forecast(bromley, days=7)
forecast.current.temperature                  # 12.3
```

How it talks to the internet:

- **Two APIs.** The geocoding API turns a name into a latitude and longitude.
  The forecast API turns those into weather. Neither needs a key.
- **Retries with growing waits.** If the server is busy (429 or 5xx) or the
  connection drops, it waits 0.5 seconds, then 1, then gives up. Like
  redialling a busy line, but not straight away, so a struggling server
  isn't flooded.
- **Mistakes aren't retried.** A 400 means our request was wrong, so asking
  again won't help. The service's own reason is shown in the error.
- **Clear errors.** `NetworkError` means it couldn't connect. `ApiError`
  means it connected but got an error or something it couldn't read.
  Damaged answers become an `ApiError`, never a confusing `KeyError`.
- **Gaps are handled.** Open-Meteo sends `null` for unknown values. Rain
  totals and chances become zero, and a missing sunrise just means daylight
  hours aren't shown.

The forecast's daily part comes as one list per field, like columns in a
spreadsheet. `parse_forecast` uses `zip()` to read across them a day at a
time.

`WeatherProvider` is an abstract class with two methods. `OpenMeteoProvider`
is one version of it, and another weather service could be added as a new
class without changing anything else. `HttpClient` is abstract too, so the
tests hand in a fake one with saved answers and never need the internet.

## Caching

```python
from weather import CachedProvider, FileCache, OpenMeteoProvider

provider = CachedProvider(OpenMeteoProvider(), FileCache("data/cache.json"))
provider.forecast(bromley)    # goes online
provider.forecast(bromley)    # straight from the cache, no internet needed
```

Weather doesn't change much in a few minutes, and towns don't move, so
there's no need to ask the internet every time. A cache is like writing the
answer on a sticky note with a "use until" time.

- Forecasts are kept for **15 minutes**, place searches for **30 days**.
- If the internet is down, an older saved forecast is shown instead of an
  error. Its `fetched_at` time says how old it is.
- A damaged cache file counts as empty, so the worst case is fetching again.
- Files are written to a temporary file first and then swapped in, so a
  crash never leaves half a file.

`CachedProvider` is the **Decorator pattern**. It wraps any other provider,
like a phone case wraps a phone. It has the same methods, so the rest of the
program can't tell the difference, and it adds caching on top.

## Favourite places

```python
from weather import Favourites

favourites = Favourites("data/places.json")
favourites.add(bromley)
favourites.set_home("Paris")     # the first place is used when none is named
favourites.remove("bromley")     # case doesn't matter
```

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
pytest          # 147 tests
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
