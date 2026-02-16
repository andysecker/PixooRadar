"""Pixoo Flight Tracker Display entrypoint."""

import argparse
import logging
import os
import subprocess
import sys

from pixoo_radar.controller import PixooRadarController
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
    settings = load_settings()
    configure_logging(settings.log_level, settings.log_verbose_events)
    LOGGER.info("Starting Pixoo Radar.")

    parser = argparse.ArgumentParser(description="Pixoo Flight Tracker Display")
    parser.add_argument("--caffeinate", action="store_true", help="Prevent macOS from sleeping while tracker runs")
    args = parser.parse_args()

    if args.caffeinate:
        sys.exit(subprocess.call(["caffeinate", "-i", sys.executable, os.path.abspath(__file__)]))

    PixooRadarController(settings).run()


if __name__ == "__main__":
    main()
