import logging
import re
from importlib.util import find_spec
from dataclasses import dataclass
from math import isfinite
from pathlib import Path

import config as app_config


@dataclass(frozen=True)
class AppSettings:
    pixoo_ip: str
    pixoo_port: int
    pixoo_reconnect_seconds: int
    font_name: str
    font_path: str
    runway_label_font_name: str
    runway_label_font_path: str
    animation_frame_speed: int
    color_box: str
    color_text: str
    data_refresh_seconds: int
    flight_search_radius_meters: int
    flight_speed_unit: str
    latitude: float
    longitude: float
    log_level: str
    log_verbose_events: bool
    logo_dir: str
    runway_heading_deg: float
    weather_refresh_seconds: int
    weather_view_seconds: int
    weather_wind_speed_unit: str
    weather_metar_icao: str = ""
    pixoo_startup_connect_timeout_seconds: int = 120


def _valid_log_level(level_name: str) -> bool:
    return isinstance(getattr(logging, str(level_name).upper(), None), int)


def validate_settings(settings: AppSettings) -> AppSettings:
    """Validate startup configuration and raise a clear error on invalid values."""
    errors = []

    if not str(settings.pixoo_ip).strip():
        errors.append("PIXOO_IP must be a non-empty string.")
    if int(settings.pixoo_port) < 1 or int(settings.pixoo_port) > 65535:
        errors.append("PIXOO_PORT must be between 1 and 65535.")

    if int(settings.pixoo_reconnect_seconds) <= 0:
        errors.append("PIXOO_RECONNECT_SECONDS must be > 0.")
    if int(settings.pixoo_startup_connect_timeout_seconds) <= 0:
        errors.append("PIXOO_STARTUP_CONNECT_TIMEOUT_SECONDS must be > 0.")
    if int(settings.data_refresh_seconds) <= 0:
        errors.append("DATA_REFRESH_SECONDS must be > 0.")
    if int(settings.weather_refresh_seconds) <= 0:
        errors.append("WEATHER_REFRESH_SECONDS must be > 0.")
    if int(settings.weather_view_seconds) <= 0:
        errors.append("WEATHER_VIEW_SECONDS must be > 0.")
    if int(settings.animation_frame_speed) <= 0:
        errors.append("ANIMATION_FRAME_SPEED must be > 0.")
    if int(settings.flight_search_radius_meters) <= 0:
        errors.append("FLIGHT_SEARCH_RADIUS_METERS must be > 0.")

    if not isfinite(float(settings.latitude)) or not (-90.0 <= float(settings.latitude) <= 90.0):
        errors.append("LATITUDE must be a finite value in range [-90, 90].")
    if not isfinite(float(settings.longitude)) or not (-180.0 <= float(settings.longitude) <= 180.0):
        errors.append("LONGITUDE must be a finite value in range [-180, 180].")

    runway_heading = float(settings.runway_heading_deg)
    if not isfinite(runway_heading) or not (0.0 <= runway_heading < 360.0):
        errors.append("RUNWAY_HEADING_DEG must be a finite value in range [0, 360).")

    if str(settings.flight_speed_unit).lower() not in {"mph", "kt"}:
        errors.append("FLIGHT_SPEED_UNIT must be 'mph' or 'kt'.")
    if str(settings.weather_wind_speed_unit).lower() not in {"mph", "kmh", "kph"}:
        errors.append("WEATHER_WIND_SPEED_UNIT must be 'mph' or 'kmh' (legacy 'kph' accepted).")
    if settings.weather_metar_icao and (len(str(settings.weather_metar_icao).strip()) != 4 or not str(settings.weather_metar_icao).strip().isalnum()):
        errors.append("WEATHER_METAR_ICAO must be a 4-character ICAO station code when set.")
    if settings.weather_metar_icao and find_spec("metar") is None:
        errors.append("WEATHER_METAR_ICAO is set, but dependency 'metar' is not installed. Install with: pip install metar")
    if settings.weather_metar_icao and find_spec("timezonefinder") is None:
        errors.append(
            "WEATHER_METAR_ICAO is set, but dependency 'timezonefinder' is not installed. "
            "Install with: pip install timezonefinder"
        )
    if settings.weather_metar_icao and find_spec("airportsdata") is None:
        errors.append(
            "WEATHER_METAR_ICAO is set, but dependency 'airportsdata' is not installed. "
            "Install with: pip install airportsdata"
        )
    if find_spec("openmeteo_requests") is None:
        errors.append(
            "Dependency 'openmeteo-requests' is required for weather idle view. "
            "Install with: pip install openmeteo-requests"
        )
    if not _valid_log_level(settings.log_level):
        errors.append("LOG_LEVEL must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL (or equivalent).")

    font_path = Path(settings.font_path).expanduser()
    runway_font_path = Path(settings.runway_label_font_path).expanduser()
    if not font_path.is_file():
        errors.append(f"FONT_PATH does not exist or is not a file: {settings.font_path}")
    if not runway_font_path.is_file():
        errors.append(f"RUNWAY_LABEL_FONT_PATH does not exist or is not a file: {settings.runway_label_font_path}")

    if errors:
        raise ValueError("Invalid configuration:\n- " + "\n- ".join(errors))
    return settings


def load_settings() -> AppSettings:
    try:
        settings = AppSettings(
            pixoo_ip=app_config.PIXOO_IP,
            pixoo_port=app_config.PIXOO_PORT,
            pixoo_reconnect_seconds=app_config.PIXOO_RECONNECT_SECONDS,
            font_name=app_config.FONT_NAME,
            font_path=app_config.FONT_PATH,
            runway_label_font_name=app_config.RUNWAY_LABEL_FONT_NAME,
            runway_label_font_path=app_config.RUNWAY_LABEL_FONT_PATH,
            animation_frame_speed=app_config.ANIMATION_FRAME_SPEED,
            color_box=app_config.COLOR_BOX,
            color_text=app_config.COLOR_TEXT,
            data_refresh_seconds=app_config.DATA_REFRESH_SECONDS,
            flight_search_radius_meters=app_config.FLIGHT_SEARCH_RADIUS_METERS,
            flight_speed_unit=app_config.FLIGHT_SPEED_UNIT,
            latitude=app_config.LATITUDE,
            longitude=app_config.LONGITUDE,
            log_level=app_config.LOG_LEVEL,
            log_verbose_events=app_config.LOG_VERBOSE_EVENTS,
            logo_dir=app_config.LOGO_DIR,
            runway_heading_deg=app_config.RUNWAY_HEADING_DEG,
            weather_refresh_seconds=app_config.WEATHER_REFRESH_SECONDS,
            weather_view_seconds=app_config.WEATHER_VIEW_SECONDS,
            weather_wind_speed_unit=app_config.WEATHER_WIND_SPEED_UNIT,
            weather_metar_icao=getattr(app_config, "WEATHER_METAR_ICAO", ""),
            pixoo_startup_connect_timeout_seconds=getattr(app_config, "PIXOO_STARTUP_CONNECT_TIMEOUT_SECONDS", 120),
        )
    except AttributeError as exc:
        attr_match = re.search(r"has no attribute '([^']+)'", str(exc))
        missing_attr = attr_match.group(1) if attr_match else str(exc)
        raise ValueError(f"Invalid configuration:\n- Missing required config setting: {missing_attr}") from exc
    return validate_settings(settings)
