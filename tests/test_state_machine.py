from pixoo_radar.controller import PixooRadarController
from pixoo_radar.models import RenderState
from pixoo_radar.settings import AppSettings


class DummyService:
    pass


class DummyController(PixooRadarController):
    def __init__(self, settings):
        super().__init__(settings, pixoo_service=DummyService(), flight_service=DummyService(), weather_service=DummyService())


def _settings(idle_mode="weather"):
    return AppSettings(
        pixoo_ip="127.0.0.1",
        pixoo_port=80,
        pixoo_reconnect_seconds=1,
        font_name="f",
        font_path="f.bdf",
        runway_label_font_name="f",
        runway_label_font_path="f.bdf",
        animation_frame_speed=300,
        color_box="#000",
        color_text="#fff",
        data_refresh_seconds=60,
        flight_search_radius_meters=50000,
        flight_speed_unit="mph",
        latitude=0,
        longitude=0,
        log_level="INFO",
        log_verbose_events=True,
        logo_dir="airline_logos",
        idle_mode=idle_mode,
        no_flight_retry_seconds=15,
        no_flight_max_retry_seconds=120,
        runway_heading_deg=110,
        weather_refresh_seconds=900,
        weather_view_seconds=10,
        weather_wind_speed_unit="mph",
    )


def test_resolve_target_state_rate_limit_wins():
    c = DummyController(_settings())
    assert c.resolve_target_state(cooldown_remaining=30, api_error="oops") == RenderState.RATE_LIMIT


def test_resolve_target_state_api_error():
    c = DummyController(_settings())
    assert c.resolve_target_state(cooldown_remaining=0, api_error="oops") == RenderState.API_ERROR


def test_resolve_target_state_weather_idle():
    c = DummyController(_settings("weather"))
    assert c.resolve_target_state(cooldown_remaining=0, api_error=None) == RenderState.IDLE_WEATHER


def test_resolve_target_state_holding_idle():
    c = DummyController(_settings("holding"))
    assert c.resolve_target_state(cooldown_remaining=0, api_error=None) == RenderState.IDLE_HOLDING
