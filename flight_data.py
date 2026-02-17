"""
Flight Data Module

Facade for fetching closest-flight payloads while delegating to componentized
provider/filter/logo/METAR modules.
"""

import re
from time import monotonic

from config import API_RATE_LIMIT_COOLDOWN_SECONDS, FLIGHT_SEARCH_RADIUS_METERS, LOGO_BG_COLOR
from pixoo_radar.flight.filters import choose_closest_flight
from pixoo_radar.flight.logos import LogoManager
from pixoo_radar.flight.mapping import build_flight_payload
from pixoo_radar.flight.provider import FlightRadarProvider


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
        self._api_cooldown_until = 0.0
        self._last_api_error = None

    def get_api_cooldown_remaining(self) -> int:
        """Return remaining API cooldown seconds if rate-limited, else 0."""
        return max(0, int(self._api_cooldown_until - monotonic()))

    def get_last_api_error(self) -> str | None:
        """Return latest API-related error message, if any."""
        return self._last_api_error

    @staticmethod
    def _extract_status_code(exc: Exception):
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
        if isinstance(status, int):
            return status
        status = getattr(exc, "status_code", None)
        if isinstance(status, int):
            return status

        message = str(exc).lower()
        if "429" in message and ("too many" in message or "rate" in message):
            return 429
        return None

    @classmethod
    def _is_rate_limited_error(cls, exc: Exception) -> bool:
        if cls._extract_status_code(exc) == 429:
            return True
        message = str(exc).lower()
        return "rate limit" in message or "too many requests" in message

    @staticmethod
    def _extract_retry_after_seconds(exc: Exception) -> int:
        response = getattr(exc, "response", None)
        if response is not None:
            headers = getattr(response, "headers", {}) or {}
            retry_after = headers.get("Retry-After")
            if retry_after:
                try:
                    return max(1, int(retry_after))
                except (TypeError, ValueError):
                    pass

        match = re.search(r"retry\s*after\s*(\d+)", str(exc), flags=re.IGNORECASE)
        if match:
            return max(1, int(match.group(1)))

        return API_RATE_LIMIT_COOLDOWN_SECONDS

    def _set_api_cooldown(self, seconds: int, reason: str) -> None:
        cooldown_seconds = max(1, int(seconds))
        self._api_cooldown_until = monotonic() + cooldown_seconds
        self._last_api_error = reason

    def _find_closest(self, lat, lon):
        if self.get_api_cooldown_remaining() > 0:
            return None, None

        try:
            flights = self.provider.get_flights_near(lat, lon)
        except Exception as exc:
            if self._is_rate_limited_error(exc):
                retry_after = self._extract_retry_after_seconds(exc)
                self._set_api_cooldown(retry_after, f"Rate-limited while fetching flights: {exc}")
            else:
                self._last_api_error = f"Flight fetch error: {exc}"
            return None, None

        if not flights:
            return None, None

        closest_flight = choose_closest_flight(flights, lat, lon)
        if not closest_flight:
            self._last_api_error = None
            return None, None

        try:
            details = self.provider.get_flight_details(closest_flight)
            self._last_api_error = None
            return closest_flight, details
        except Exception as exc:
            if self._is_rate_limited_error(exc):
                retry_after = self._extract_retry_after_seconds(exc)
                self._set_api_cooldown(retry_after, f"Rate-limited while fetching flight details: {exc}")
            else:
                self._last_api_error = f"Flight details error: {exc}"
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
