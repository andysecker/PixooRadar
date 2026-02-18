"""Pixoo Flight Tracker Display entrypoint."""

import argparse
import logging
import os
import subprocess
import sys

from pixoo_radar.controller import PixooRadarController
from pixoo_radar.models import FlightSnapshot, WeatherSnapshot
from pixoo_radar.services.weather_service import WeatherService
from pixoo_radar.settings import load_settings

LOGGER = logging.getLogger("pixoo_radar")


def configure_logging(level_name: str, verbose_events: bool) -> None:
    level_name = str(level_name).upper()
    level = getattr(logging, level_name, logging.INFO)
    if not verbose_events and level < logging.WARNING:
        level = logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


class DemoFlightService:
    """Synthetic flight source for local rendering tests."""

    def __init__(self):
        self._tick = 0

    def get_closest_flight(self, latitude: float, longitude: float):
        self._tick += 1
        speed = 220 + ((self._tick % 8) * 7)
        altitude = min(39000, 1200 + (self._tick * 850))
        heading = (95 + (self._tick * 3)) % 360
        payload = {
            "icao24": "TEST123",
            "flight_number": "GAF001",
            "origin": "ETAR",
            "destination": "LCPH",
            "airline": "Germany - Air Force",
            "registration": "10+01",
            "aircraft_type_icao": "A400",
            "altitude": altitude,
            "ground_speed": speed,
            "heading": heading,
            "status": "EN ROUTE",
        }
        return FlightSnapshot.from_dict(payload)


class DemoWeatherService:
    """Stub weather service used only when forcing test-flight mode."""

    @staticmethod
    def _snapshot():
        return WeatherSnapshot.from_dict(
            {
                "temperature_c": 20,
                "condition": "CLEAR",
                "humidity_pct": 50,
                "wind_kph": 15,
                "wind_dir_deg": 90,
                "wind_dir_from": None,
                "wind_dir_to": None,
                "location": "LOCAL WX",
                "source": "demo",
            }
        )

    def validate_startup_sources(self, require_metar: bool = False):
        return None

    def get_current(self):
        return self._snapshot(), False

    def get_current_with_options(self, force_refresh: bool = False):
        return self._snapshot(), False

    @staticmethod
    def get_last_error():
        return None


def main() -> None:
    try:
        settings = load_settings()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)

    parser = argparse.ArgumentParser(description="Pixoo Flight Tracker Display")
    parser.add_argument("--caffeinate", action="store_true", help="Prevent macOS from sleeping while tracker runs")
    parser.add_argument(
        "--test-flight",
        action="store_true",
        help="Use synthetic flight data (no live FlightRadar calls) for display testing.",
    )
    args = parser.parse_args()

    configure_logging(settings.log_level, settings.log_verbose_events)
    LOGGER.info("Starting Pixoo Radar.")
    if args.test_flight:
        LOGGER.warning("Test-flight mode enabled: using synthetic flight payloads.")
        weather_service = DemoWeatherService()
        flight_service = DemoFlightService()
    else:
        weather_service = WeatherService(
            latitude=settings.latitude,
            longitude=settings.longitude,
            refresh_seconds=settings.weather_refresh_seconds,
            metar_icao=settings.weather_metar_icao,
        )
        try:
            weather_service.validate_startup_sources(require_metar=bool(settings.weather_metar_icao))
            LOGGER.info("Weather startup validation passed.")
            LOGGER.info("Weather updated from API (startup prefetch).")
        except Exception as exc:
            LOGGER.error("Weather startup validation failed: %s", exc)
            sys.exit(2)
        flight_service = None

    if args.caffeinate:
        child_cmd = [sys.executable, os.path.abspath(__file__)]
        if args.test_flight:
            child_cmd.append("--test-flight")
        sys.exit(subprocess.call(["caffeinate", "-i", *child_cmd]))

    try:
        PixooRadarController(settings, weather_service=weather_service, flight_service=flight_service).run()
    except RuntimeError as exc:
        LOGGER.error("Startup failed: %s", exc)
        sys.exit(2)


if __name__ == "__main__":
    main()
