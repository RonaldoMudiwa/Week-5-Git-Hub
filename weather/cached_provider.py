"""A provider that remembers answers.

CachedProvider wraps any other provider, like a phone case wraps a phone.
It does the same job with the same buttons, and adds one thing on top:
answers are kept for a while, so asking twice doesn't go online twice.
This is called the Decorator pattern.
"""

from __future__ import annotations

from datetime import timedelta

from .cache import Cache
from .exceptions import NetworkError
from .models import Forecast, Location
from .providers import WeatherProvider
from .serialise import forecast_from_dict, forecast_to_dict, location_from_dict, location_to_dict

FORECAST_LIFETIME = timedelta(minutes=15)
PLACES_LIFETIME = timedelta(days=30)   # towns don't move


class CachedProvider(WeatherProvider):
    def __init__(self, inner: WeatherProvider, cache: Cache,
                 forecast_lifetime: timedelta = FORECAST_LIFETIME,
                 places_lifetime: timedelta = PLACES_LIFETIME) -> None:
        self._inner = inner
        self._cache = cache
        self._forecast_lifetime = forecast_lifetime
        self._places_lifetime = places_lifetime

    def find_places(self, name: str, limit: int = 5) -> list[Location]:
        key = f"places:{str(name).strip().lower()}:{limit}"
        saved = self._cache.get(key)
        if saved is not None:
            return [location_from_dict(item) for item in saved]
        places = self._inner.find_places(name, limit)
        self._cache.set(key, [location_to_dict(p) for p in places], self._places_lifetime)
        return places

    def forecast(self, location: Location, days: int = 7) -> Forecast:
        """A saved forecast if it's fresh, otherwise a new one.

        If going online fails, an old saved forecast is better than nothing,
        so that's returned instead. Its fetched_at time shows how old it is.
        """
        key = f"forecast:{location.key}:{days}"
        saved = self._cache.get(key)
        if saved is not None:
            return forecast_from_dict(saved)
        try:
            forecast = self._inner.forecast(location, days)
        except NetworkError:
            old = self._cache.get(key, allow_expired=True)
            if old is None:
                raise
            return forecast_from_dict(old)
        self._cache.set(key, forecast_to_dict(forecast), self._forecast_lifetime)
        return forecast
