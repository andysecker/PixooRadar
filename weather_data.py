"""Weather data provider for idle display mode (Open-Meteo)."""

from time import monotonic


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

    def __init__(self, latitude: float, longitude: float, refresh_seconds: int = 900, provider=None):
        self.latitude = latitude
        self.longitude = longitude
        self.refresh_seconds = max(30, int(refresh_seconds))
        self.provider = provider or self._fetch_from_provider
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
            raw = self.provider(self.latitude, self.longitude)
            payload = self._normalize(raw)
            if payload:
                self._cache = payload
                self._cache_at = now
                self._last_error = None
                return self._cache, refreshed
            self._last_error = "Weather provider returned no data"
        except Exception as exc:  # noqa: BLE001
            self._last_error = f"Weather provider error: {exc}"

        if self._cache:
            return self._cache, False

        self._cache = self._fallback_payload()
        self._cache_at = now
        return self._cache, refreshed

    def get_last_error(self):
        return self._last_error

    @staticmethod
    def _normalize(raw):
        if not isinstance(raw, dict):
            return None

        return {
            "temperature_c": raw.get("temperature_c"),
            "condition": raw.get("condition"),
            "humidity_pct": raw.get("humidity_pct"),
            "wind_kph": raw.get("wind_kph"),
            "wind_dir_deg": raw.get("wind_dir_deg"),
            "location": raw.get("location") or "LOCAL WX",
            "source": raw.get("source") or "provider",
        }

    @staticmethod
    def _fallback_payload():
        return {
            "temperature_c": None,
            "condition": "SET PROVIDER",
            "humidity_pct": None,
            "wind_kph": None,
            "wind_dir_deg": None,
            "location": "LOCAL WX",
            "source": "scaffold",
        }

    def _fetch_from_provider(self, latitude, longitude):
        """Fetch current weather from Open-Meteo via openmeteo-requests."""
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
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "wind_speed_10m",
                "wind_direction_10m",
                "weather_code",
            ],
            "timezone": "auto",
        }
        responses = client.weather_api(self.OPEN_METEO_URL, params=params)
        if not responses:
            return None

        response = responses[0]
        current = response.Current()
        if current is None:
            return None

        temperature_c = current.Variables(0).Value()
        humidity_pct = current.Variables(1).Value()
        wind_kph = current.Variables(2).Value()
        wind_dir_deg = current.Variables(3).Value()
        weather_code = int(round(current.Variables(4).Value()))
        condition = self.WEATHER_CODE_LABELS.get(weather_code, f"WCODE {weather_code}")

        return {
            "temperature_c": temperature_c,
            "condition": condition,
            "humidity_pct": humidity_pct,
            "wind_kph": wind_kph,
            "wind_dir_deg": wind_dir_deg,
            "location": "LOCAL WX",
            "source": "open-meteo",
        }
