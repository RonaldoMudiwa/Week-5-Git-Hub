"""Tests for the real HTTP client, with urlopen swapped for a fake."""

from __future__ import annotations

import io
import socket
import urllib.error
import urllib.request

import pytest

from weather import ApiError, NetworkError, UrllibHttpClient
from weather.http import USER_AGENT, build_url


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def http_error(code: int, body: bytes = b"") -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://x", code, "Server said no", {}, io.BytesIO(body))


@pytest.fixture
def server(monkeypatch):
    """Answers come off a list, one per request. Requests are remembered."""
    state = {"answers": [], "requests": []}

    def fake_urlopen(request, timeout):
        state["requests"].append((request, timeout))
        answer = state["answers"].pop(0)
        if isinstance(answer, BaseException):
            raise answer
        return FakeResponse(answer)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return state


@pytest.fixture
def waits():
    return []


@pytest.fixture
def client(waits) -> UrllibHttpClient:
    return UrllibHttpClient(timeout=5, retries=2, backoff=0.5, sleep=waits.append)


def test_success(server, client):
    server["answers"] = [b'{"ok": true}']
    assert client.get_json("https://example.com/api", {"a": 1}) == {"ok": True}
    request, timeout = server["requests"][0]
    assert request.full_url == "https://example.com/api?a=1"
    assert request.get_header("User-agent") == USER_AGENT
    assert timeout == 5


def test_busy_server_is_tried_again_with_longer_waits(server, client, waits):
    server["answers"] = [http_error(503), http_error(429), b"[1, 2]"]
    assert client.get_json("https://x") == [1, 2]
    assert waits == [0.5, 1.0]


def test_gives_up_after_the_retries(server, client, waits):
    server["answers"] = [http_error(500)] * 3
    with pytest.raises(ApiError) as raised:
        client.get_json("https://x")
    assert raised.value.status == 500
    assert len(waits) == 2


def test_bad_request_is_not_retried_and_shows_the_reason(server, client, waits):
    server["answers"] = [http_error(400, b'{"error": true, "reason": "Latitude must be in range"}')]
    with pytest.raises(ApiError, match="400: Latitude must be in range"):
        client.get_json("https://x")
    assert waits == []


def test_error_without_json(server, client):
    server["answers"] = [http_error(404, b"<html>nope</html>")]
    with pytest.raises(ApiError, match="404: Server said no"):
        client.get_json("https://x")


@pytest.mark.parametrize("problem", [
    urllib.error.URLError("no internet"), socket.timeout("timed out"), ConnectionResetError("reset"),
])
def test_connection_problems(server, client, waits, problem):
    server["answers"] = [problem] * 3
    with pytest.raises(NetworkError, match="Couldn't reach"):
        client.get_json("https://x")
    assert len(waits) == 2


def test_connection_comes_back(server, client):
    server["answers"] = [urllib.error.URLError("blip"), b'{"fine": 1}']
    assert client.get_json("https://x") == {"fine": 1}


@pytest.mark.parametrize("body", [b"not json", b"\xff\xfe"])
def test_answer_that_is_not_json(server, client, body):
    server["answers"] = [body]
    with pytest.raises(ApiError, match="valid JSON"):
        client.get_json("https://x")


def test_build_url():
    assert build_url("https://x") == "https://x"
    assert build_url("https://x", {"a": [1, 2], "b": "hi there", "c": None}) == \
        "https://x?a=1%2C2&b=hi+there"
