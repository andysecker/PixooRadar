"""Pixoo Flight Tracker Display entrypoint."""

import argparse
import logging
import os
import subprocess
import sys

from pixoo_radar.controller import PixooRadarController
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


def main() -> None:
    try:
        settings = load_settings()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    configure_logging(settings.log_level, settings.log_verbose_events)
    LOGGER.info("Starting Pixoo Radar.")
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

    parser = argparse.ArgumentParser(description="Pixoo Flight Tracker Display")
    parser.add_argument("--caffeinate", action="store_true", help="Prevent macOS from sleeping while tracker runs")
    args = parser.parse_args()

    if args.caffeinate:
        sys.exit(subprocess.call(["caffeinate", "-i", sys.executable, os.path.abspath(__file__)]))

    try:
        PixooRadarController(settings, weather_service=weather_service).run()
    except RuntimeError as exc:
        LOGGER.error("Startup failed: %s", exc)
        sys.exit(2)


if __name__ == "__main__":
    main()
