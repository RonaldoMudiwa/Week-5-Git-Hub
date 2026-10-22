"""Weather Dashboard.

Live forecasts from the free Open-Meteo service, shown as a dashboard.

    from weather import Location, describe
"""

from .codes import Condition, WeatherCode, describe, known_codes
from .exceptions import ValidationError, WeatherError
from .models import CurrentWeather, DailyForecast, Forecast, Location
from .units import Imperial, Metric, UnitSystem, compass, unit_system

__version__ = "0.1.0"

__all__ = [
    "Location",
    "CurrentWeather",
    "DailyForecast",
    "Forecast",
    "WeatherCode",
    "Condition",
    "describe",
    "known_codes",
    "UnitSystem",
    "Metric",
    "Imperial",
    "unit_system",
    "compass",
    "WeatherError",
    "ValidationError",
    "__version__",
]
