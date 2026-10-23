"""Weather Dashboard.

Live forecasts from the free Open-Meteo service, shown as a dashboard.

    from weather import Location, describe
"""

from .codes import Condition, WeatherCode, describe, known_codes
from .exceptions import ApiError, NetworkError, PlaceNotFoundError, ValidationError, WeatherError
from .http import HttpClient, UrllibHttpClient
from .models import CurrentWeather, DailyForecast, Forecast, Location
from .providers import OpenMeteoProvider, WeatherProvider, parse_forecast
from .units import Imperial, Metric, UnitSystem, compass, unit_system

__version__ = "0.2.0"

__all__ = [
    "WeatherProvider",
    "OpenMeteoProvider",
    "parse_forecast",
    "HttpClient",
    "UrllibHttpClient",
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
    "NetworkError",
    "ApiError",
    "PlaceNotFoundError",
    "__version__",
]
