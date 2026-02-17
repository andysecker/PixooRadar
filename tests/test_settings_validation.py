import pytest

from pixoo_radar.settings import AppSettings, validate_settings


def _base_settings():
    return AppSettings(
        pixoo_ip="127.0.0.1",
        pixoo_port=80,
        pixoo_reconnect_seconds=60,
        font_name="splitflap",
        font_path="./fonts/splitflap.bdf",
        runway_label_font_name="splitflap",
        runway_label_font_path="./fonts/splitflap.bdf",
        animation_frame_speed=300,
        color_box="#454545",
        color_text="#FFFF00",
        data_refresh_seconds=60,
        flight_search_radius_meters=5000,
        flight_speed_unit="mph",
        latitude=34.0,
        longitude=32.0,
        log_level="INFO",
        log_verbose_events=True,
        logo_dir="airline_logos",
        idle_mode="weather",
        no_flight_retry_seconds=15,
        no_flight_max_retry_seconds=120,
        runway_heading_deg=110.0,
        weather_refresh_seconds=900,
        weather_view_seconds=10,
        weather_wind_speed_unit="mph",
    )


def test_validate_settings_accepts_valid_configuration():
    settings = _base_settings()
    assert validate_settings(settings) == settings


def test_validate_settings_rejects_invalid_runway_heading():
    settings = _base_settings()
    settings = AppSettings(**{**settings.__dict__, "runway_heading_deg": 360.0})
    with pytest.raises(ValueError, match="RUNWAY_HEADING_DEG"):
        validate_settings(settings)


def test_validate_settings_rejects_invalid_weather_wind_unit():
    settings = _base_settings()
    settings = AppSettings(**{**settings.__dict__, "weather_wind_speed_unit": "knots"})
    with pytest.raises(ValueError, match="WEATHER_WIND_SPEED_UNIT"):
        validate_settings(settings)


def test_validate_settings_rejects_missing_font_file():
    settings = _base_settings()
    settings = AppSettings(**{**settings.__dict__, "font_path": "./fonts/does-not-exist.bdf"})
    with pytest.raises(ValueError, match="FONT_PATH"):
        validate_settings(settings)


def test_validate_settings_rejects_retry_bounds():
    settings = _base_settings()
    settings = AppSettings(**{**settings.__dict__, "no_flight_retry_seconds": 120, "no_flight_max_retry_seconds": 60})
    with pytest.raises(ValueError, match="NO_FLIGHT_MAX_RETRY_SECONDS"):
        validate_settings(settings)

