"""Weather Dashboard.

Live forecasts from the free Open-Meteo service, shown as a dashboard.

    from weather import Location, describe
"""

from .cache import Cache, FileCache, MemoryCache
from .cached_provider import CachedProvider
from .codes import Condition, WeatherCode, describe, known_codes
from .exceptions import (
    ApiError,
    NetworkError,
    PlaceNotFoundError,
    StorageError,
    ValidationError,
    WeatherError,
)
from .favourites import Favourites
from .http import HttpClient, UrllibHttpClient
from .models import CurrentWeather, DailyForecast, Forecast, Location
from .providers import OpenMeteoProvider, WeatherProvider, parse_forecast
from .serialise import forecast_from_dict, forecast_to_dict
from .units import Imperial, Metric, UnitSystem, compass, unit_system

__version__ = "0.3.0"

__all__ = [
    "CachedProvider",
    "Cache",
    "MemoryCache",
    "FileCache",
    "Favourites",
    "forecast_to_dict",
    "forecast_from_dict",
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
    "StorageError",
    "__version__",
]
