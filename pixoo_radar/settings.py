from dataclasses import dataclass

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
    idle_mode: str
    no_flight_retry_seconds: int
    no_flight_max_retry_seconds: int
    runway_heading_deg: float
    weather_refresh_seconds: int
    weather_view_seconds: int
    weather_wind_speed_unit: str



def load_settings() -> AppSettings:
    return AppSettings(
        pixoo_ip=app_config.PIXOO_IP,
        pixoo_port=app_config.PIXOO_PORT,
        pixoo_reconnect_seconds=app_config.PIXOO_RECONNECT_SECONDS,
        font_name=app_config.FONT_NAME,
        font_path=app_config.FONT_PATH,
        runway_label_font_name=getattr(app_config, "RUNWAY_LABEL_FONT_NAME", app_config.FONT_NAME),
        runway_label_font_path=getattr(app_config, "RUNWAY_LABEL_FONT_PATH", app_config.FONT_PATH),
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
        idle_mode=app_config.IDLE_MODE,
        no_flight_retry_seconds=app_config.NO_FLIGHT_RETRY_SECONDS,
        no_flight_max_retry_seconds=app_config.NO_FLIGHT_MAX_RETRY_SECONDS,
        runway_heading_deg=app_config.RUNWAY_HEADING_DEG,
        weather_refresh_seconds=app_config.WEATHER_REFRESH_SECONDS,
        weather_view_seconds=app_config.WEATHER_VIEW_SECONDS,
        weather_wind_speed_unit=app_config.WEATHER_WIND_SPEED_UNIT,
    )
