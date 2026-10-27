"""The command line interface.

    python -m weather forecast Bromley
    python -m weather now
    python -m weather html Paris --days 5
    python -m weather save Bromley
    python -m weather demo

When no place is given, the home place is used. That's the first saved
place, and "python -m weather home <name>" changes it.
"""

from __future__ import annotations

import argparse
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Callable, Sequence, TextIO

from .alerts import AlertChecker
from .cache import Cache, FileCache
from .cached_provider import CachedProvider
from .dashboard import TextDashboard
from .demo import demo_forecast
from .exceptions import PlaceNotFoundError, WeatherError
from .favourites import Favourites
from .html_dashboard import HtmlDashboard
from .models import Forecast, Location
from .providers import MAX_DAYS, OpenMeteoProvider, WeatherProvider
from .units import UnitSystem, compass, unit_system

DEFAULT_DATA = Path("data")
NO_HOME = ("No place given and no home place saved yet. "
           "Try: python -m weather save Bromley")


class Context:
    """What a command gets to work with while it runs."""

    def __init__(self, out: TextIO, provider: WeatherProvider, favourites: Favourites,
                 cache: Cache, units: UnitSystem, data_dir: Path,
                 clock: Callable[[], datetime] = datetime.now) -> None:
        self.out = out
        self.provider = provider
        self.favourites = favourites
        self.cache = cache
        self.units = units
        self.data_dir = data_dir
        self.clock = clock
        self.alerts = AlertChecker()

    def say(self, text: str = "") -> None:
        print(text, file=self.out)

    def place(self, name: str | None) -> Location:
        """A saved place if the name matches one, otherwise a search.
        No name at all means the home place."""
        if not name:
            home = self.favourites.home
            if home is None:
                raise PlaceNotFoundError(NO_HOME)
            return home
        try:
            return self.favourites.find(name)
        except PlaceNotFoundError:
            return self.provider.find_place(name)


class Command(ABC):
    """One thing the user can ask for. Each command is its own small class."""

    name = ""
    help = ""

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add this command's own options. Commands with none can skip it."""

    @abstractmethod
    def run(self, ctx: Context, args: argparse.Namespace) -> None:
        """Do the job. Raise a WeatherError if it can't be done."""


def _days_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--days", type=int, default=7, help=f"how many days, 1 to {MAX_DAYS}")


def _place_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("place", nargs="*", help="a place name, or leave out for home")


def _joined(words: Sequence[str]) -> str | None:
    # nargs="*" lets people type New York without quotes.
    return " ".join(words) or None


# ----------------------------------------------------------------------
# Weather
# ----------------------------------------------------------------------

class NowCommand(Command):
    name = "now"
    help = "the weather right now, in one line"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        _place_option(parser)

    def run(self, ctx: Context, args: argparse.Namespace) -> None:
        forecast = ctx.provider.forecast(ctx.place(_joined(args.place)), days=1)
        now, units = forecast.current, ctx.units
        ctx.say(f"{forecast.location.label}: {units.temperature(now.temperature)}, "
                f"{now.code.description.lower()}, feels like {units.temperature(now.feels_like)}, "
                f"wind {units.speed(now.wind_speed)} from the {compass(now.wind_direction)}")


class ForecastCommand(Command):
    name = "forecast"
    help = "the full dashboard for the days ahead"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        _place_option(parser)
        _days_option(parser)

    def run(self, ctx: Context, args: argparse.Namespace) -> None:
        forecast = ctx.provider.forecast(ctx.place(_joined(args.place)), days=args.days)
        show_dashboard(ctx, forecast)


class HtmlCommand(Command):
    name = "html"
    help = "save the dashboard as a web page"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        _place_option(parser)
        _days_option(parser)
        parser.add_argument("--out", help="where to save it (default data/<place>.html)")

    def run(self, ctx: Context, args: argparse.Namespace) -> None:
        forecast = ctx.provider.forecast(ctx.place(_joined(args.place)), days=args.days)
        path = Path(args.out) if args.out else ctx.data_dir / f"{_file_name(forecast.location)}.html"
        HtmlDashboard(clock=ctx.clock).save(path, forecast, ctx.alerts.check(forecast), ctx.units)
        ctx.say(f"Saved {path}. Open it in your browser.")


class DemoCommand(Command):
    name = "demo"
    help = "show the dashboard with made up weather, no internet needed"

    def run(self, ctx: Context, args: argparse.Namespace) -> None:
        show_dashboard(ctx, demo_forecast(ctx.clock()))


def show_dashboard(ctx: Context, forecast: Forecast) -> None:
    dashboard = TextDashboard(clock=ctx.clock)
    ctx.say(dashboard.render(forecast, ctx.alerts.check(forecast), ctx.units))


def _file_name(place: Location) -> str:
    """"New York" -> "new-york". Only letters and digits, so it's safe on any system."""
    cleaned = "".join(c if c.isalnum() else "-" for c in place.name.lower())
    return "-".join(part for part in cleaned.split("-") if part) or "weather"


# ----------------------------------------------------------------------
# Places
# ----------------------------------------------------------------------

class SearchCommand(Command):
    name = "search"
    help = "list the places that match a name"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("name", nargs="+")

    def run(self, ctx: Context, args: argparse.Namespace) -> None:
        places = ctx.provider.find_places(" ".join(args.name))
        if not places:
            ctx.say("No places found.")
            return
        for number, place in enumerate(places, start=1):
            ctx.say(f"{number}. {place.label}  ({place.key})")


class PlacesCommand(Command):
    name = "places"
    help = "list your saved places"

    def run(self, ctx: Context, args: argparse.Namespace) -> None:
        places = ctx.favourites.all()
        if not places:
            ctx.say("No saved places yet. Try: python -m weather save Bromley")
            return
        for number, place in enumerate(places, start=1):
            ctx.say(f"{number}. {place.label}{'  (home)' if number == 1 else ''}")


class SaveCommand(Command):
    name = "save"
    help = "save a place. The first one saved becomes home"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("name", nargs="+")

    def run(self, ctx: Context, args: argparse.Namespace) -> None:
        place = ctx.provider.find_place(" ".join(args.name))
        if ctx.favourites.add(place):
            ctx.say(f"Saved {place.label}.")
        else:
            ctx.say(f"{place.label} is already saved.")


class RemoveCommand(Command):
    name = "remove"
    help = "forget a saved place"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("name", nargs="+")

    def run(self, ctx: Context, args: argparse.Namespace) -> None:
        place = ctx.favourites.remove(" ".join(args.name))
        ctx.say(f"Removed {place.label}.")


class HomeCommand(Command):
    name = "home"
    help = "pick which saved place is home"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("name", nargs="+")

    def run(self, ctx: Context, args: argparse.Namespace) -> None:
        place = ctx.favourites.set_home(" ".join(args.name))
        ctx.say(f"Home is now {place.label}.")


class ClearCacheCommand(Command):
    name = "clear-cache"
    help = "forget saved forecasts so the next one is fetched fresh"

    def run(self, ctx: Context, args: argparse.Namespace) -> None:
        count = ctx.cache.clear()
        ctx.say(f"Cleared {count} saved answer{'s' if count != 1 else ''}.")


COMMANDS: tuple[Command, ...] = (
    ForecastCommand(), NowCommand(), HtmlCommand(), SearchCommand(), PlacesCommand(),
    SaveCommand(), RemoveCommand(), HomeCommand(), ClearCacheCommand(), DemoCommand(),
)


# ----------------------------------------------------------------------
# Putting it together
# ----------------------------------------------------------------------

def build_parser(commands: Sequence[Command] = COMMANDS) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m weather",
                                     description="Weather forecasts in your terminal.")
    parser.add_argument("--units", default="metric", choices=["metric", "imperial"])
    parser.add_argument("--data", default=str(DEFAULT_DATA),
                        help="folder for saved places, the cache and web pages")
    sub = parser.add_subparsers(dest="command", metavar="command")
    for command in commands:
        child = sub.add_parser(command.name, help=command.help, description=command.help)
        command.add_arguments(child)
        child.set_defaults(handler=command)
    return parser


def main(argv: Sequence[str] | None = None, out: TextIO | None = None,
         provider: WeatherProvider | None = None,
         clock: Callable[[], datetime] = datetime.now) -> int:
    """Run one command. Returns 0 if it worked, 1 if it didn't.

    The provider and clock can be swapped for fakes, so the tests never go
    online and always see the same time.
    """
    out = out or sys.stdout
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help(out)
        return 0

    data_dir = Path(args.data)
    cache = FileCache(data_dir / "cache.json", clock=clock)
    ctx = Context(
        out=out,
        provider=CachedProvider(provider or OpenMeteoProvider(clock=clock), cache),
        favourites=Favourites(data_dir / "places.json"),
        cache=cache,
        units=unit_system(args.units),
        data_dir=data_dir,
        clock=clock,
    )
    try:
        args.handler.run(ctx, args)
    except WeatherError as error:
        ctx.say(f"Error: {error}")
        return 1
    return 0
