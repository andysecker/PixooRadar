import pytest

from pixoo_radar.settings import AppSettings, load_settings, validate_settings


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
        runway_heading_deg=110.0,
        weather_refresh_seconds=900,
        weather_view_seconds=10,
        weather_wind_speed_unit="mph",
    )


def test_validate_settings_accepts_valid_configuration():
    settings = _base_settings()
    assert validate_settings(settings) == settings


def test_validate_settings_rejects_invalid_runway_heading():
    settings = AppSettings(**{**_base_settings().__dict__, "runway_heading_deg": 360.0})
    with pytest.raises(ValueError, match="RUNWAY_HEADING_DEG"):
        validate_settings(settings)


def test_validate_settings_rejects_invalid_weather_wind_unit():
    settings = AppSettings(**{**_base_settings().__dict__, "weather_wind_speed_unit": "knots"})
    with pytest.raises(ValueError, match="WEATHER_WIND_SPEED_UNIT"):
        validate_settings(settings)


def test_validate_settings_rejects_missing_font_file():
    settings = AppSettings(**{**_base_settings().__dict__, "font_path": "./fonts/does-not-exist.bdf"})
    with pytest.raises(ValueError, match="FONT_PATH"):
        validate_settings(settings)


def test_validate_settings_rejects_invalid_metar_icao():
    settings = AppSettings(**{**_base_settings().__dict__, "weather_metar_icao": "BAD"})
    with pytest.raises(ValueError, match="WEATHER_METAR_ICAO"):
        validate_settings(settings)


def test_validate_settings_rejects_missing_metar_dependency_when_icao_set(monkeypatch):
    import pixoo_radar.settings as settings_module

    monkeypatch.setattr(settings_module, "find_spec", lambda name: None if name == "metar" else object())
    settings = AppSettings(**{**_base_settings().__dict__, "weather_metar_icao": "LCPH"})
    with pytest.raises(ValueError, match="dependency 'metar' is not installed"):
        validate_settings(settings)


def test_validate_settings_rejects_missing_timezonefinder_dependency_when_icao_set(monkeypatch):
    import pixoo_radar.settings as settings_module

    def fake_find_spec(name):
        if name == "timezonefinder":
            return None
        return object()

    monkeypatch.setattr(settings_module, "find_spec", fake_find_spec)
    settings = AppSettings(**{**_base_settings().__dict__, "weather_metar_icao": "LCPH"})
    with pytest.raises(ValueError, match="dependency 'timezonefinder' is not installed"):
        validate_settings(settings)


def test_validate_settings_rejects_missing_airportsdata_dependency_when_icao_set(monkeypatch):
    import pixoo_radar.settings as settings_module

    def fake_find_spec(name):
        if name == "airportsdata":
            return None
        return object()

    monkeypatch.setattr(settings_module, "find_spec", fake_find_spec)
    settings = AppSettings(**{**_base_settings().__dict__, "weather_metar_icao": "LCPH"})
    with pytest.raises(ValueError, match="dependency 'airportsdata' is not installed"):
        validate_settings(settings)


def test_validate_settings_rejects_invalid_startup_connect_timeout():
    settings = AppSettings(**{**_base_settings().__dict__, "pixoo_startup_connect_timeout_seconds": 0})
    with pytest.raises(ValueError, match="PIXOO_STARTUP_CONNECT_TIMEOUT_SECONDS"):
        validate_settings(settings)


def test_validate_settings_accepts_valid_poll_pause_window():
    settings = AppSettings(**{**_base_settings().__dict__, "poll_pause_start_local": "0000", "poll_pause_end_local": "0700"})
    assert validate_settings(settings) == settings


def test_validate_settings_rejects_partial_poll_pause_window():
    settings = AppSettings(**{**_base_settings().__dict__, "poll_pause_start_local": "0000", "poll_pause_end_local": ""})
    with pytest.raises(ValueError, match="POLL_PAUSE_START_LOCAL and POLL_PAUSE_END_LOCAL must both be set"):
        validate_settings(settings)


def test_validate_settings_rejects_invalid_poll_pause_time_format():
    settings = AppSettings(**{**_base_settings().__dict__, "poll_pause_start_local": "24:00", "poll_pause_end_local": "0700"})
    with pytest.raises(ValueError, match="POLL_PAUSE_START_LOCAL must use 24-hour HHMM format"):
        validate_settings(settings)


def test_validate_settings_rejects_equal_poll_pause_times():
    settings = AppSettings(**{**_base_settings().__dict__, "poll_pause_start_local": "0000", "poll_pause_end_local": "0000"})
    with pytest.raises(ValueError, match="must not be equal"):
        validate_settings(settings)


def test_validate_settings_rejects_missing_openmeteo_dependency(monkeypatch):
    import pixoo_radar.settings as settings_module

    monkeypatch.setattr(settings_module, "find_spec", lambda name: None if name == "openmeteo_requests" else object())
    with pytest.raises(ValueError, match="openmeteo-requests"):
        validate_settings(_base_settings())


def test_load_settings_reports_missing_required_config(monkeypatch):
    import pixoo_radar.settings as settings_module

    monkeypatch.delattr(settings_module.app_config, "PIXOO_IP", raising=False)
    with pytest.raises(ValueError, match="Missing required config setting: PIXOO_IP"):
        load_settings()


def test_load_settings_reports_missing_required_runway_label_font_config(monkeypatch):
    import pixoo_radar.settings as settings_module

    monkeypatch.delattr(settings_module.app_config, "RUNWAY_LABEL_FONT_NAME", raising=False)
    with pytest.raises(ValueError, match="Missing required config setting: RUNWAY_LABEL_FONT_NAME"):
        load_settings()
