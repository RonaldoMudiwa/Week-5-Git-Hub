"""Tests for the command line interface. None of them go online."""

from __future__ import annotations

import io
import json
import runpy
import sys
from datetime import datetime

import pytest

from weather import NetworkError, OpenMeteoProvider
from weather.cli import COMMANDS, _file_name, build_parser, main
from weather.demo import DEMO_PLACE, demo_forecast

from .sample_data import GEOCODING, NO_PLACES, FakeHttpClient, forecast_json

GEO = OpenMeteoProvider.GEOCODING_URL
FORECAST = OpenMeteoProvider.FORECAST_URL
NOW = datetime(2026, 10, 22, 9, 10)


class Runner:
    """Runs commands against saved answers and a temp data folder."""

    def __init__(self, data_dir) -> None:
        self.data_dir = data_dir
        self.http = FakeHttpClient({GEO: GEOCODING, FORECAST: forecast_json()})

    def __call__(self, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        provider = OpenMeteoProvider(self.http, clock=lambda: NOW)
        code = main(["--data", str(self.data_dir), *argv], out=out, provider=provider,
                    clock=lambda: NOW)
        return code, out.getvalue()

    def calls_to(self, url: str) -> int:
        return sum(1 for called, _ in self.http.calls if called == url)


@pytest.fixture
def run(tmp_path) -> Runner:
    return Runner(tmp_path / "data")


def test_no_command_shows_help(run):
    code, text = run()
    assert code == 0
    assert "forecast" in text and "clear-cache" in text


def test_every_command_has_a_name_and_help():
    names = [command.name for command in COMMANDS]
    assert len(names) == len(set(names))
    assert all(command.help for command in COMMANDS)


def test_forecast_for_a_named_place(run):
    code, text = run("forecast", "Bromley")
    assert code == 0
    assert "Bromley, England, United Kingdom" in text
    assert "-- Next days" in text and "-- Alerts" in text


def test_place_names_can_have_spaces(run):
    run("forecast", "New", "York")
    names = [params["name"] for url, params in run.http.calls if url == GEO]
    assert names == ["New York"]


def test_days_option_is_passed_on(run):
    run("forecast", "Bromley", "--days", "3")
    params = [params for url, params in run.http.calls if url == FORECAST][0]
    assert params["forecast_days"] == 3


def test_bad_days_is_a_clear_error(run):
    code, text = run("forecast", "Bromley", "--days", "40")
    assert code == 1
    assert "Error: Days must be between 1 and 16." in text


def test_imperial(run):
    code, text = run("--units", "imperial", "forecast", "Bromley")
    assert "°F" in text and "°C" not in text


def test_now(run):
    code, text = run("now", "Bromley")
    assert code == 0
    assert text.strip() == ("Bromley, England, United Kingdom: 12°C, overcast, "
                            "feels like 11°C, wind 14 km/h from the SW")


def test_second_forecast_comes_from_the_cache(run):
    run("forecast", "Bromley")
    run("forecast", "Bromley")
    assert run.calls_to(FORECAST) == 1
    assert run.calls_to(GEO) == 1
    assert (run.data_dir / "cache.json").exists()


def test_no_place_and_no_home(run):
    code, text = run("forecast")
    assert code == 1
    assert "no home place saved yet" in text


def test_unknown_place(run):
    run.http.answers[GEO] = NO_PLACES
    code, text = run("now", "Nowhereville")
    assert code == 1
    assert "Couldn't find a place called 'Nowhereville'" in text


def test_offline_with_nothing_saved(run):
    run.http.answers[GEO] = NetworkError("No internet.")
    code, text = run("now", "Bromley")
    assert code == 1
    assert "Error: No internet." in text


# ----------------------------------------------------------------------
# Places
# ----------------------------------------------------------------------

def test_save_and_use_home(run):
    code, text = run("save", "Bromley")
    assert text.strip() == "Saved Bromley, England, United Kingdom."
    code, text = run("now")
    assert code == 0 and text.startswith("Bromley")


def test_save_twice(run):
    run("save", "Bromley")
    code, text = run("save", "Bromley")
    assert "already saved" in text


def test_saved_place_is_used_without_searching(run):
    run("save", "Bromley")
    run.http.calls.clear()
    run("now", "bromley")
    assert run.calls_to(GEO) == 0


def test_places_list_and_home(run):
    code, text = run("places")
    assert "No saved places yet" in text

    paris = {"name": "Paris", "latitude": 48.85, "longitude": 2.35, "country": "France"}
    run.data_dir.mkdir(parents=True, exist_ok=True)
    (run.data_dir / "places.json").write_text(json.dumps([
        {"name": "Bromley", "latitude": 51.4, "longitude": 0.02}, paris]), encoding="utf-8")

    code, text = run("places")
    assert text.splitlines() == ["1. Bromley  (home)", "2. Paris, France"]

    code, text = run("home", "paris")
    assert text.strip() == "Home is now Paris, France."
    code, text = run("places")
    assert text.splitlines()[0] == "1. Paris, France  (home)"


def test_remove(run):
    run("save", "Bromley")
    code, text = run("remove", "Bromley")
    assert text.strip() == "Removed Bromley, England, United Kingdom."
    code, text = run("remove", "Bromley")
    assert code == 1 and "isn't one of your saved places" in text


def test_search(run):
    code, text = run("search", "Bromley")
    assert text.splitlines() == [
        "1. Bromley, England, United Kingdom  (51.41,0.02)",
        "2. Bromley, Queensland, Australia  (-27.50,153.00)",
    ]


def test_search_with_no_matches(run):
    run.http.answers[GEO] = NO_PLACES
    code, text = run("search", "Nowhereville")
    assert text.strip() == "No places found."


# ----------------------------------------------------------------------
# Web page, cache and demo
# ----------------------------------------------------------------------

def test_html_default_path(run):
    code, text = run("html", "Bromley")
    path = run.data_dir / "bromley.html"
    assert code == 0
    assert f"Saved {path}" in text
    assert path.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


def test_html_chosen_path(run, tmp_path):
    out = tmp_path / "pages" / "mine.html"
    code, _ = run("html", "Bromley", "--out", str(out))
    assert code == 0 and out.exists()


def test_clear_cache(run):
    run("forecast", "Bromley")
    code, text = run("clear-cache")
    assert text.strip() == "Cleared 2 saved answers."
    code, text = run("clear-cache")
    assert text.strip() == "Cleared 0 saved answers."
    run("forecast", "Bromley")
    assert run.calls_to(FORECAST) == 2


def test_clear_cache_says_answer_for_one(run):
    run("now", "Bromley")
    run.data_dir.joinpath("cache.json").write_text(
        json.dumps({"only": {"expires": "2030-01-01T00:00:00", "value": 1}}), encoding="utf-8")
    code, text = run("clear-cache")
    assert text.strip() == "Cleared 1 saved answer."


def test_demo_needs_no_internet(run):
    run.http.answers = {}   # any request would raise a KeyError
    code, text = run("demo")
    assert code == 0
    assert "Bromley" in text and "[Warning] Tomorrow: Heavy rain." in text


def test_demo_forecast_starts_today():
    forecast = demo_forecast(datetime(2026, 10, 28, 8, 30, 15))
    assert forecast.location == DEMO_PLACE
    assert forecast.today.day.isoformat() == "2026-10-28"
    assert len(forecast.days) == 7
    assert forecast.fetched_at == datetime(2026, 10, 28, 8, 30)


def test_demo_forecast_default_time():
    assert demo_forecast().today.day == datetime.now().date()


@pytest.mark.parametrize("name, file_name", [
    ("Bromley", "bromley"), ("New York", "new-york"), ("St. Albans", "st-albans"), ("!!!", "weather"),
])
def test_file_name(name, file_name):
    from weather import Location

    assert _file_name(Location(name, 0, 0)) == file_name


def test_unknown_units_are_refused_by_the_parser():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--units", "kelvin", "demo"])


def test_runs_as_a_module(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, "argv", ["weather", "--data", str(tmp_path), "demo"])
    with pytest.raises(SystemExit) as finished:
        runpy.run_module("weather", run_name="__main__")
    assert finished.value.code == 0
    assert "Bromley" in capsys.readouterr().out


def test_main_writes_to_stdout_by_default(capsys, tmp_path):
    assert main(["--data", str(tmp_path), "demo"]) == 0
    assert "Bromley" in capsys.readouterr().out
