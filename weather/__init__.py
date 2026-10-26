"""Weather Dashboard.

Live forecasts from the free Open-Meteo service, shown as a dashboard.

    from weather import Location, describe
"""

from .alerts import (
    Alert,
    AlertChecker,
    AlertRule,
    ConditionRule,
    FrostRule,
    HeatRule,
    HeavyRainRule,
    Severity,
    UmbrellaRule,
    WindRule,
    default_rules,
)
from .cache import Cache, FileCache, MemoryCache
from .cached_provider import CachedProvider
from .codes import Condition, WeatherCode, describe, known_codes
from .dashboard import DashboardRenderer, TextDashboard
from .exceptions import (
    ApiError,
    NetworkError,
    PlaceNotFoundError,
    StorageError,
    ValidationError,
    WeatherError,
)
from .favourites import Favourites
from .html_dashboard import ChartSize, HtmlDashboard, TemperatureChart
from .http import HttpClient, UrllibHttpClient
from .models import CurrentWeather, DailyForecast, Forecast, Location
from .providers import OpenMeteoProvider, WeatherProvider, parse_forecast
from .serialise import forecast_from_dict, forecast_to_dict
from .units import Imperial, Metric, UnitSystem, compass, unit_system

__version__ = "0.5.0"

__all__ = [
    "DashboardRenderer",
    "TextDashboard",
    "HtmlDashboard",
    "TemperatureChart",
    "ChartSize",
    "Alert",
    "AlertChecker",
    "AlertRule",
    "Severity",
    "FrostRule",
    "HeatRule",
    "WindRule",
    "HeavyRainRule",
    "ConditionRule",
    "UmbrellaRule",
    "default_rules",
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
