"""Weather data provider for idle display mode (METAR + Open-Meteo)."""

import logging
import re
from math import exp
from time import monotonic

from pixoo_radar.flight.metar import fetch_metar_report


LOGGER = logging.getLogger("pixoo_radar.weather")
WIND_VARIATION_RE = re.compile(r"\b(\d{3})V(\d{3})\b")


class WeatherData:
    """Fetch and cache weather payloads for idle display mode."""

    OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
    WEATHER_CODE_LABELS = {
        0: "CLEAR",
        1: "MAINLY CLR",
        2: "PART CLOUD",
        3: "OVERCAST",
        45: "FOG",
        48: "RIME FOG",
        51: "DRIZZLE",
        53: "DRIZZLE",
        55: "DRIZZLE",
        56: "FRZ DRIZ",
        57: "FRZ DRIZ",
        61: "RAIN",
        63: "RAIN",
        65: "HEAVY RAIN",
        66: "FRZ RAIN",
        67: "FRZ RAIN",
        71: "SNOW",
        73: "SNOW",
        75: "HEAVY SNOW",
        77: "SNOW GRAIN",
        80: "RAIN SHWR",
        81: "RAIN SHWR",
        82: "HVY SHWR",
        85: "SNOW SHWR",
        86: "SNOW SHWR",
        95: "TSTORM",
        96: "TSTM HAIL",
        99: "TSTM HAIL",
    }

    def __init__(
        self,
        latitude: float,
        longitude: float,
        refresh_seconds: int = 900,
        metar_icao: str = "",
        provider=None,
        metar_fetcher=None,
        metar_parser=None,
    ):
        self.latitude = latitude
        self.longitude = longitude
        self.refresh_seconds = max(30, int(refresh_seconds))
        self.metar_icao = str(metar_icao or "").strip().upper()
        self.provider = provider or self._fetch_from_provider
        self.metar_fetcher = metar_fetcher or fetch_metar_report
        self.metar_parser = metar_parser or self._parse_metar_fields_with_library
        self._cache = None
        self._cache_at = 0.0
        self._last_error = None

    def get_current(self):
        """Return (payload, refreshed) where refreshed indicates provider was queried."""
        return self.get_current_with_options(force_refresh=False)

    def get_current_with_options(self, force_refresh: bool = False):
        """Return (payload, refreshed) with optional forced provider refresh."""
        now = monotonic()
        if not force_refresh and self._cache and (now - self._cache_at) < self.refresh_seconds:
            return self._cache, False

        refreshed = True
        try:
            raw = self._fetch_raw()
            LOGGER.info("Weather API raw payload: %s", raw)
            payload = self._normalize(raw)
            LOGGER.info("Weather API normalized payload: %s", payload)
            if payload:
                self._cache = payload
                self._cache_at = now
                return self._cache, refreshed
            self._last_error = "Weather provider returned no data"
            LOGGER.warning("Weather provider returned no data payload after normalization.")
        except Exception as exc:  # noqa: BLE001
            self._last_error = f"Weather provider error: {exc}"
            LOGGER.warning("Weather API fetch failed: %s", exc)

        if self._cache:
            return self._cache, False

        self._cache = self._fallback_payload()
        self._cache_at = now
        return self._cache, refreshed

    def get_last_error(self):
        return self._last_error

    def _normalize(self, raw):
        if not isinstance(raw, dict):
            return None

        open_meteo = raw.get("open_meteo")
        metar = raw.get("metar")
        condition = None
        if isinstance(open_meteo, dict):
            condition = open_meteo.get("condition")

        metar_fields = self.metar_parser(metar)
        temp_c = metar_fields.get("temperature_c")
        humidity_pct = self._relative_humidity_from_temp_dewpoint(
            temp_c,
            metar_fields.get("dewpoint_c"),
        )
        wind_kph = metar_fields.get("wind_speed_kph")

        if condition is None and temp_c is None and humidity_pct is None and wind_kph is None:
            return None

        if temp_c is not None or humidity_pct is not None or wind_kph is not None:
            source = "metar+open-meteo" if condition is not None else "metar"
        else:
            source = "open-meteo"

        return {
            "temperature_c": temp_c,
            "condition": condition,
            "humidity_pct": humidity_pct,
            "wind_kph": wind_kph,
            "wind_dir_deg": metar_fields.get("wind_dir_deg"),
            "wind_dir_from": metar_fields.get("wind_dir_from"),
            "wind_dir_to": metar_fields.get("wind_dir_to"),
            "location": metar_fields.get("location") or "LOCAL WX",
            "source": source,
        }

    @staticmethod
    def _fallback_payload():
        return {
            "temperature_c": None,
            "condition": "SET PROVIDER",
            "humidity_pct": None,
            "wind_kph": None,
            "wind_dir_deg": None,
            "wind_dir_from": None,
            "wind_dir_to": None,
            "location": "LOCAL WX",
            "source": "scaffold",
        }

    def _fetch_from_provider(self, latitude, longitude):
        """Fetch current weather condition from Open-Meteo via openmeteo-requests."""
        try:
            import openmeteo_requests
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Missing dependency `openmeteo-requests`. Install with: pip install openmeteo-requests"
            ) from exc

        client = openmeteo_requests.Client()
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": ["weather_code"],
            "timezone": "auto",
        }
        responses = client.weather_api(self.OPEN_METEO_URL, params=params)
        if not responses:
            return None

        response = responses[0]
        current = response.Current()
        if current is None:
            return None

        weather_code = int(round(current.Variables(0).Value()))
        condition = self.WEATHER_CODE_LABELS.get(weather_code, f"WCODE {weather_code}")

        return {
            "condition": condition,
            "location": "LOCAL WX",
            "source": "open-meteo",
            "weather_code": weather_code,
        }

    def _fetch_raw(self):
        self._last_error = None
        open_meteo_payload = None
        metar_payload = None
        provider_error = None
        metar_error = None

        try:
            open_meteo_payload = self.provider(self.latitude, self.longitude)
        except Exception as exc:  # noqa: BLE001
            provider_error = str(exc)
            LOGGER.warning("Open-Meteo fetch failed: %s", exc)

        if self.metar_icao:
            try:
                metar_payload = self.metar_fetcher(self.metar_icao)
                metar_raw = None
                if isinstance(metar_payload, dict):
                    metar_raw = metar_payload.get("raw")
                LOGGER.info("METAR raw string (%s): %s", self.metar_icao, metar_raw if metar_raw else "<none>")
            except Exception as exc:  # noqa: BLE001
                metar_error = str(exc)
                LOGGER.warning("METAR fetch failed for %s: %s", self.metar_icao, exc)
        else:
            LOGGER.info("WEATHER_METAR_ICAO not configured; METAR-derived weather fields unavailable.")

        if provider_error and metar_error:
            raise RuntimeError(f"Open-Meteo error: {provider_error}; METAR error: {metar_error}")

        if provider_error:
            self._last_error = f"Open-Meteo error: {provider_error}"
        elif metar_error:
            self._last_error = f"METAR error: {metar_error}"

        return {
            "open_meteo": open_meteo_payload,
            "metar": metar_payload,
            "metar_icao": self.metar_icao or None,
        }

    @staticmethod
    def _quantity_value(value, unit=None):
        if value is None:
            return None
        if hasattr(value, "value"):
            try:
                return value.value(unit) if unit else value.value()
            except TypeError:
                return value.value()
        if isinstance(value, int | float):
            return value
        return None

    def _parse_metar_fields_with_library(self, metar_payload):
        if not isinstance(metar_payload, dict):
            return {}
        raw = str(metar_payload.get("raw") or "").strip().upper()
        if not raw:
            return {}
        try:
            from metar import Metar
        except ModuleNotFoundError:
            try:
                from Metar import Metar  # pragma: no cover - legacy fallback
            except ModuleNotFoundError:
                LOGGER.warning("Missing dependency `metar`; install with: pip install metar")
                return {}

        try:
            decoded = Metar.Metar(raw)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("METAR decode failed (%s): %s", self.metar_icao or "unknown", exc)
            return {}

        temp_c = self._quantity_value(getattr(decoded, "temp", None), "C")
        dewpoint_c = self._quantity_value(getattr(decoded, "dewpt", None), "C")
        wind_speed_kph = self._quantity_value(getattr(decoded, "wind_speed", None), "KMH")
        if wind_speed_kph is None:
            wind_speed_kph = self._quantity_value(getattr(decoded, "wind_speed", None), "KPH")
        raw_wind_dir = getattr(decoded, "wind_dir", None)
        wind_dir_deg = self._quantity_value(raw_wind_dir)
        wind_dir_from = self._quantity_value(
            getattr(decoded, "wind_dir_from", None) or getattr(decoded, "wind_var_from", None)
        )
        wind_dir_to = self._quantity_value(
            getattr(decoded, "wind_dir_to", None) or getattr(decoded, "wind_var_to", None)
        )
        if wind_dir_from is None or wind_dir_to is None:
            variation_match = WIND_VARIATION_RE.search(raw)
            if variation_match:
                wind_dir_from = int(variation_match.group(1))
                wind_dir_to = int(variation_match.group(2))
        if wind_dir_deg is not None:
            wind_dir_deg = int(round(float(wind_dir_deg))) % 360
        if wind_dir_from is not None:
            wind_dir_from = int(round(float(wind_dir_from))) % 360
        if wind_dir_to is not None:
            wind_dir_to = int(round(float(wind_dir_to))) % 360
        if wind_speed_kph is not None:
            wind_speed_kph = float(wind_speed_kph)

        return {
            "temperature_c": temp_c,
            "dewpoint_c": dewpoint_c,
            "wind_dir_deg": wind_dir_deg,
            "wind_dir_from": wind_dir_from,
            "wind_dir_to": wind_dir_to,
            "wind_speed_kph": wind_speed_kph,
            "location": metar_payload.get("station") or getattr(decoded, "station_id", None) or "LOCAL WX",
        }

    @staticmethod
    def _relative_humidity_from_temp_dewpoint(temp_c, dewpoint_c):
        if temp_c is None or dewpoint_c is None:
            return None
        temp = float(temp_c)
        dew = float(dewpoint_c)
        gamma_t = (17.625 * temp) / (243.04 + temp)
        gamma_td = (17.625 * dew) / (243.04 + dew)
        rh = 100.0 * exp(gamma_td - gamma_t)
        return max(0.0, min(100.0, rh))
