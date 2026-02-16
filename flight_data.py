"""
Flight Data Module

Fetches real-time flight information from FlightRadar24 API, including:
- Flight details (callsign, registration, aircraft type)
- Route information (origin, destination)
- Position data (altitude, speed, heading)
- Airline logos (processed for Pixoo display)
- Destination METAR weather data
"""

import json
import re
from io import BytesIO
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from time import monotonic

import requests

try:
    # Expected package for this project: FlightRadarAPI (module: FlightRadar24)
    from FlightRadar24.api import FlightRadar24API
except ModuleNotFoundError as exc:
    if exc.name == "FlightRadar24":
        raise ImportError(
            "Missing compatible FlightRadar24 client. Install `FlightRadarAPI` and remove `flightradar24` if present: "
            "`pip uninstall -y flightradar24 && pip install FlightRadarAPI`."
        ) from exc
    if exc.name == "bs4":
        raise ImportError(
            "Missing dependency `beautifulsoup4` required by `FlightRadarAPI`. "
            "Install it with: `pip install beautifulsoup4`."
        ) from exc
    raise

from config import API_RATE_LIMIT_COOLDOWN_SECONDS, FLIGHT_SEARCH_RADIUS_METERS, LOGO_BG_COLOR


class FlightData:
    """Fetch flight details (closest flight to a point) and attach destination METAR.

    Usage:
        fd = FlightData(save_logo_dir='airline_logos')
        data = fd.get_closest_flight_data(lat, lon)
    """

    def __init__(self, save_logo_dir: str | None = None, fr_api: FlightRadar24API | None = None):
        self.fr_api = fr_api or FlightRadar24API()
        self.save_logo_dir = Path(save_logo_dir) if save_logo_dir else None
        self._api_cooldown_until = 0.0
        self._last_api_error = None
        if self.save_logo_dir:
            self.save_logo_dir.mkdir(parents=True, exist_ok=True)

    def get_api_cooldown_remaining(self) -> int:
        """Return remaining API cooldown seconds if rate-limited, else 0."""
        return max(0, int(self._api_cooldown_until - monotonic()))

    def get_last_api_error(self) -> str | None:
        """Return the latest API-related error message, if any."""
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

    @staticmethod
    def haversine(lat1, lon1, lat2, lon2):
        """Calculate the great circle distance in kilometers between two points."""
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        r = 6371
        return c * r

    def _find_closest(self, lat, lon):
        if self.get_api_cooldown_remaining() > 0:
            return None, None

        try:
            bounds = self.fr_api.get_bounds_by_point(lat, lon, FLIGHT_SEARCH_RADIUS_METERS)
            flights = self.fr_api.get_flights(bounds=bounds)
        except Exception as exc:
            if self._is_rate_limited_error(exc):
                retry_after = self._extract_retry_after_seconds(exc)
                self._set_api_cooldown(retry_after, f"Rate-limited while fetching flights: {exc}")
            else:
                self._last_api_error = f"Flight fetch error: {exc}"
            return None, None

        if not flights:
            return None, None

        self._last_api_error = None

        closest_flight = None
        min_dist = float("inf")
        details = None
        for flight in flights:
            # Skip flights without airline information (only consider flights with a non-null 'airline' field)
            if not getattr(flight, "airline_iata", None):
                continue

            # Skip stationary ground targets (e.g., aircraft parked at gates with transponders on).
            try:
                altitude = float(getattr(flight, "altitude", 0) or 0)
                ground_speed = float(getattr(flight, "ground_speed", 0) or 0)
            except (TypeError, ValueError):
                altitude = 0.0
                ground_speed = 0.0
            if altitude <= 0 and ground_speed <= 0:
                continue

            try:
                dist = self.haversine(lat, lon, flight.latitude, flight.longitude)
            except Exception:
                continue
            if dist < min_dist:
                min_dist = dist
                closest_flight = flight
                try:
                    details = self.fr_api.get_flight_details(closest_flight)
                except Exception as exc:
                    if self._is_rate_limited_error(exc):
                        retry_after = self._extract_retry_after_seconds(exc)
                        self._set_api_cooldown(retry_after, f"Rate-limited while fetching flight details: {exc}")
                        break
                    self._last_api_error = f"Flight details error: {exc}"
                    details = None
        return closest_flight, details

    @staticmethod
    def _safe_get(d, *keys):
        v = d
        for k in keys:
            if not isinstance(v, dict):
                return None
            v = v.get(k)
        return v

    def _fetch_metar(self, icao):
        if not icao:
            return None
        icao = str(icao).strip().upper()
        url = f"https://tgftp.nws.noaa.gov/data/observations/metar/stations/{icao}.TXT"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code != 200:
                return None
            lines = resp.text.strip().splitlines()
            if not lines:
                return None
            if len(lines) >= 2:
                timestamp = lines[0].strip()
                raw = lines[1].strip()
            else:
                timestamp = None
                raw = lines[0].strip()
            return {"raw": raw, "timestamp": timestamp, "source": url}
        except Exception:
            return None

    def _resize_logo_bytes(self, logo_bytes: bytes, target_w: int = 64, target_h: int = 20,
                           bg=(255, 255, 255, 0), sharpen: bool = True, autocontrast: bool = True,
                           flatten_bg: bool = True):
        """Resize logo image bytes to target_w x target_h with minimal loss for text.

        Strategy:
        - Use Pillow (if available) and LANCZOS resampling for high-quality downsampling.
        - Preserve aspect ratio, scale to fit within target and center on canvas.
        - Optionally flatten transparency onto provided bg color to avoid haloing on non-alpha displays.
        - Apply autocontrast and a light unsharp mask to improve small-text legibility.
        Returns a tuple (resized_bytes, ext) where ext is 'png' when successful. On failure returns (original_bytes, None).
        """
        try:
            from PIL import Image, ImageOps, ImageFilter
        except Exception:
            # Pillow not available; return original
            return logo_bytes, None

        try:
            src = Image.open(BytesIO(logo_bytes)).convert("RGBA")
        except Exception:
            return logo_bytes, None

        # Flatten transparency if requested (helps on displays that don't support alpha)
        if flatten_bg and src.mode == "RGBA":
            try:
                background = Image.new("RGBA", src.size, bg)
                background.paste(src, mask=src.split()[3])
                src = background
            except Exception:
                pass

        w, h = src.size
        if w == 0 or h == 0:
            return logo_bytes, None

        # Compute scale to fit inside target while preserving aspect ratio
        scale = min(target_w / w, target_h / h)
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))

        try:
            resized = src.resize((new_w, new_h), resample=Image.LANCZOS)
        except Exception:
            try:
                resized = src.resize((new_w, new_h))
            except Exception:
                return logo_bytes, None

        if autocontrast:
            try:
                resized = ImageOps.autocontrast(resized, cutoff=0)
            except Exception:
                pass

        if sharpen:
            try:
                resized = resized.filter(ImageFilter.UnsharpMask(radius=0.8, percent=150, threshold=2))
            except Exception:
                pass

        # Paste onto final canvas
        canvas = Image.new("RGBA", (target_w, target_h), bg)
        x = (target_w - new_w) // 2
        y = (target_h - new_h) // 2
        try:
            canvas.paste(resized, (x, y), resized if resized.mode == "RGBA" else None)
        except Exception:
            canvas.paste(resized, (x, y))

        out = BytesIO()
        try:
            canvas.save(out, format="PNG", optimize=True)
            return out.getvalue(), "png"
        except Exception:
            return logo_bytes, None

    def get_closest_flight_data(self, lat, lon, save_logo: bool = True):
        """Return a dict with flight details for the closest flight to (lat, lon).

        The returned dict contains the same keys as the previous script plus
        'destination_icao' and 'destination_metar'. This method does not print.
        """
        closest_flight, details = self._find_closest(lat, lon)
        if not closest_flight:
            return None

        details = details or {}

        # If trail is present, use the most recent point as fallback for lat/lng
        trail_point = None
        if isinstance(details.get("trail"), list) and details["trail"]:
            trail_point = details["trail"][0] or details["trail"][-1]

        flight_data = {
            "icao24": getattr(closest_flight, "icao", None) or self._safe_get(details, "identification", "id"),
            "callsign": self._safe_get(details, "identification", "callsign") or getattr(closest_flight, "callsign", None),
            "flight_number": self._safe_get(details, "identification", "number", "default"),
            "registration": self._safe_get(details, "aircraft", "registration") or getattr(closest_flight, "registration", None),
            "aircraft_type": self._safe_get(details, "aircraft", "model", "text"),
            "aircraft_type_icao": self._safe_get(details, "aircraft", "model", "code"),
            "airline": self._safe_get(details, "airline", "name"),
            "airline_icao": self._safe_get(details, "airline", "code", "icao"),
            "airline_iata": self._safe_get(details, "airline", "code", "iata"),
            "origin": self._safe_get(details, "airport", "origin", "code", "iata"),
            "destination": self._safe_get(details, "airport", "destination", "code", "iata"),
            "destination_icao": self._safe_get(details, "airport", "destination", "code", "icao"),
            "latitude": getattr(closest_flight, "latitude", None) or (trail_point and trail_point.get("lat")),
            "longitude": getattr(closest_flight, "longitude", None) or (trail_point and trail_point.get("lng")),
            "altitude": getattr(closest_flight, "altitude", None),
            "ground_speed": getattr(closest_flight, "ground_speed", None),
            "heading": getattr(closest_flight, "heading", None),
            "status": self._safe_get(details, "status", "text"),
            "scheduled_departure": self._safe_get(details, "time", "scheduled", "departure"),
            "scheduled_arrival": self._safe_get(details, "time", "scheduled", "arrival"),
            "estimated_arrival": self._safe_get(details, "time", "estimated", "arrival"),
        }

        # Attach latest METAR for destination (if available)
        try:
            flight_data["destination_metar"] = self._fetch_metar(flight_data.get("destination_icao"))
        except Exception:
            flight_data["destination_metar"] = None

        # Optionally fetch and save airline logo
        if save_logo:
            try:
                # Build a safe base filename from IATA/ICAO and check if a PNG logo already exists.
                file_base = flight_data.get("airline_iata") or flight_data.get("airline_icao") or "airline_logo"
                safe_base = "".join(c for c in file_base if c.isalnum() or c in ("-", "_")).strip() or "airline_logo"

                existing_path = None
                if self.save_logo_dir:
                    p = self.save_logo_dir / f"{safe_base}.png"
                    if p.exists():
                        existing_path = p

                if existing_path:
                    # PNG logo already present, don't download
                    flight_data["airline_logo_path"] = str(existing_path)
                else:
                    # not present -> download and save (assume PNG)
                    logo_result = self.fr_api.get_airline_logo(iata=flight_data.get("airline_iata"), icao=flight_data.get("airline_icao"))
                    logo_bytes = None
                    if isinstance(logo_result, tuple) and len(logo_result) >= 1:
                        logo_bytes = logo_result[0]
                    else:
                        logo_bytes = logo_result

                    if logo_bytes and self.save_logo_dir:
                        # Attempt to resize the logo to a 64x20 graphic for the display
                        try:
                            resized_bytes, resized_ext = self._resize_logo_bytes(logo_bytes, target_w=64, target_h=20,
                                                                                  bg=LOGO_BG_COLOR, sharpen=True, autocontrast=True,
                                                                                  flatten_bg=True)
                            if resized_bytes and resized_ext:
                                logo_bytes_to_save = resized_bytes
                            else:
                                logo_bytes_to_save = logo_bytes
                        except Exception:
                            logo_bytes_to_save = logo_bytes

                        file_name = f"{safe_base}.png"
                        file_path = str(self.save_logo_dir / file_name)
                        with open(file_path, "wb") as f:
                            f.write(logo_bytes_to_save)
                        flight_data["airline_logo_path"] = file_path
            except Exception:
                # don't fail the whole method if logo fetch/save fails
                pass

        return flight_data


if __name__ == "__main__":
    # Example usage — uses coordinates from config.py
    from config import LATITUDE, LONGITUDE, LOGO_DIR

    fd = FlightData(save_logo_dir=LOGO_DIR)
    data = fd.get_closest_flight_data(LATITUDE, LONGITUDE)
    print(json.dumps(data, indent=4))
