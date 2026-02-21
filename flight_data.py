"""
Flight Data Module

Facade for fetching closest-flight payloads while delegating to componentized
provider/filter/logo/METAR modules.
"""

import json
import logging

from config import FLIGHT_SEARCH_RADIUS_METERS, LOGO_BG_COLOR, RUNWAY_HEADING_DEG
from pixoo_radar.flight.filters import choose_closest_flight
from pixoo_radar.flight.logos import LogoManager
from pixoo_radar.flight.mapping import build_flight_payload
from pixoo_radar.flight.provider import FlightRadarProvider

LOGGER = logging.getLogger("pixoo_radar.flight")


def _loggable(value, depth: int = 0):
    if depth > 6:
        return "<max-depth>"
    if isinstance(value, dict):
        return {key: _loggable(val, depth + 1) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_loggable(item, depth + 1) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "__dict__"):
        return {key: _loggable(val, depth + 1) for key, val in vars(value).items()}
    return repr(value)


def _to_log_json(value) -> str:
    try:
        return json.dumps(_loggable(value), sort_keys=True)
    except Exception:
        return repr(value)


class FlightData:
    """Fetch closest flight details and attach destination METAR + cached logo."""

    def __init__(
        self,
        save_logo_dir: str | None = None,
        fr_api=None,
        provider=None,
        logo_manager: LogoManager | None = None,
    ):
        self.provider = provider or FlightRadarProvider(fr_api=fr_api, search_radius_meters=FLIGHT_SEARCH_RADIUS_METERS)
        self.logo_manager = logo_manager or LogoManager(save_logo_dir=save_logo_dir, bg_color=LOGO_BG_COLOR)

    def _find_closest(self, lat, lon):
        try:
            flights = self.provider.get_flights_near(lat, lon)
        except Exception as exc:
            LOGGER.warning("Flight fetch failed: %s", exc)
            return None, None

        if not flights:
            LOGGER.info("Flight API returned no candidates in search area.")
            return None, None

        closest_flight, filter_stats = choose_closest_flight(
            flights,
            lat,
            lon,
            runway_heading_deg=RUNWAY_HEADING_DEG,
            return_stats=True,
        )
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug("Flight candidate filter stats: %s", filter_stats)
        if not closest_flight:
            LOGGER.info(
                "No usable flight candidate after filtering "
                "(total=%s, missing_airline=%s, stationary_ground=%s, taxiing_ground=%s, "
                "distance_error=%s, usable=%s).",
                filter_stats.get("total"),
                filter_stats.get("missing_airline"),
                filter_stats.get("stationary_ground"),
                filter_stats.get("taxiing_ground"),
                filter_stats.get("distance_error"),
                filter_stats.get("usable"),
            )
            return None, None

        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug("Flight API selected flight raw: %s", _to_log_json(closest_flight))
        try:
            details = self.provider.get_flight_details(closest_flight)
            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug("Flight API details raw: %s", _to_log_json(details))
            return closest_flight, details
        except Exception as exc:
            LOGGER.warning("Flight details fetch failed for %s: %s", getattr(closest_flight, "icao", "unknown"), exc)
            return closest_flight, None

    def get_closest_flight_data(self, lat, lon, save_logo: bool = True):
        """Return closest-flight payload dict or None."""
        closest_flight, details = self._find_closest(lat, lon)
        if not closest_flight:
            return None

        flight_data = build_flight_payload(closest_flight, details)

        if save_logo and self.logo_manager:
            try:
                logo_path = self.logo_manager.resolve_or_fetch_logo(
                    provider=self.provider,
                    airline_iata=flight_data.get("airline_iata"),
                    airline_icao=flight_data.get("airline_icao"),
                )
                if logo_path:
                    flight_data["airline_logo_path"] = logo_path
            except Exception:
                pass

        return flight_data
