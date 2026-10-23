"""Fetching JSON from the internet.

The rest of the program only uses HttpClient, so tests can hand it a fake
one with saved answers. That way the tests never need the internet and
always get the same weather.
"""

from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, Callable, Mapping

from .exceptions import ApiError, NetworkError

USER_AGENT = "WeatherDashboard/1.0 (portfolio project)"

# Worth trying again: the server is busy or briefly broken.
RETRY_STATUSES = {429, 500, 502, 503, 504}


class HttpClient(ABC):
    @abstractmethod
    def get_json(self, url: str, params: Mapping[str, Any] | None = None) -> Any:
        """GET the url with these query params and return the JSON answer.

        Raises:
            NetworkError: The server couldn't be reached.
            ApiError: The server said no, or didn't send JSON.
        """


class UrllibHttpClient(HttpClient):
    """A real client using urllib from the standard library.

    If the server is busy or the connection drops, it waits a moment and
    tries again, waiting a bit longer each time. Like redialling a busy
    phone line, but not straight away.
    """

    def __init__(self, timeout: float = 10, retries: int = 2, backoff: float = 0.5,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self._timeout = timeout
        self._retries = retries
        self._backoff = backoff
        self._sleep = sleep

    def get_json(self, url: str, params: Mapping[str, Any] | None = None) -> Any:
        full_url = build_url(url, params)
        request = urllib.request.Request(full_url, headers={"User-Agent": USER_AGENT,
                                                            "Accept": "application/json"})
        attempt = 0
        while True:
            try:
                with urllib.request.urlopen(request, timeout=self._timeout) as response:
                    body = response.read()
                return _parse_json(body)
            except urllib.error.HTTPError as error:
                if error.code in RETRY_STATUSES and attempt < self._retries:
                    attempt = self._wait(attempt)
                    continue
                raise ApiError(_reason(error), status=error.code) from None
            except (urllib.error.URLError, socket.timeout, ConnectionError) as error:
                if attempt < self._retries:
                    attempt = self._wait(attempt)
                    continue
                reason = getattr(error, "reason", error)
                raise NetworkError(f"Couldn't reach the weather service: {reason}") from None

    def _wait(self, attempt: int) -> int:
        # 0.5s, then 1s, then 2s...
        self._sleep(self._backoff * (2 ** attempt))
        return attempt + 1


def build_url(url: str, params: Mapping[str, Any] | None = None) -> str:
    """Add query params to a url. Lists become comma separated, as Open-Meteo expects."""
    if not params:
        return url
    clean = {k: ",".join(map(str, v)) if isinstance(v, (list, tuple)) else v
             for k, v in params.items() if v is not None}
    return f"{url}?{urllib.parse.urlencode(clean)}"


def _parse_json(body: bytes) -> Any:
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ApiError("The weather service didn't send valid JSON.") from None


def _reason(error: urllib.error.HTTPError) -> str:
    """Open-Meteo explains errors as {"error": true, "reason": "..."}."""
    try:
        reason = json.loads(error.read().decode("utf-8")).get("reason")
    except Exception:
        reason = None
    return f"Weather service error {error.code}: {reason or error.reason}"
