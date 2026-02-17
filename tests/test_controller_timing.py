from pixoo_radar.controller import PixooRadarController
from pixoo_radar.models import FlightSnapshot, RenderState
from pixoo_radar.settings import AppSettings


def _settings(idle_mode="weather", data_refresh_seconds=60):
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
        data_refresh_seconds=data_refresh_seconds,
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


class FakePixooService:
    def __init__(self, reachable=True):
        self.reachable = reachable
        self.connect_calls = 0

    def is_reachable(self):
        return self.reachable

    def connect_with_retry(self):
        self.connect_calls += 1
        return FakePizzoo()


class FakeFlightService:
    def __init__(self, snapshot=None, cooldown=0, error=None):
        self.snapshot = snapshot
        self.cooldown = cooldown
        self.error = error

    def get_closest_flight(self, latitude, longitude):
        return self.snapshot

    def get_api_cooldown_remaining(self):
        return self.cooldown

    def get_last_api_error(self):
        return self.error


class FakeWeatherService:
    def get_current(self):
        return None, False

    def get_current_with_options(self, force_refresh=False):
        return None, False

    def get_last_error(self):
        return None


class FakePizzoo:
    def cls(self):
        return None

    def draw_rectangle(self, **kwargs):
        return None

    def draw_text(self, *args, **kwargs):
        return None

    def render(self, **kwargs):
        return None


def test_run_once_uses_injected_sleep_for_unchanged_flight():
    payload = {
        "icao24": "abc123",
        "flight_number": "AB123",
        "origin": "AAA",
        "destination": "BBB",
        "altitude": 12000,
        "ground_speed": 250,
        "heading": 90,
        "status": "CLIMB",
    }
    snapshot = FlightSnapshot.from_dict(payload)
    sleeps = []
    controller = PixooRadarController(
        _settings(data_refresh_seconds=42),
        pixoo_service=FakePixooService(reachable=True),
        flight_service=FakeFlightService(snapshot=snapshot),
        weather_service=FakeWeatherService(),
        sleep_fn=sleeps.append,
        clock_fn=lambda: 123.456,
    )
    controller.pizzoo = FakePizzoo()
    controller.current_flight_id = payload["icao24"]
    controller.current_flight_signature = controller.flight_render_signature(payload)

    controller.run_once()

    assert sleeps == [42]
    assert controller.last_cycle_started_at == 123.456


def test_run_once_no_flight_backoff_uses_injected_sleep():
    sleeps = []
    controller = PixooRadarController(
        _settings(idle_mode="holding"),
        pixoo_service=FakePixooService(reachable=True),
        flight_service=FakeFlightService(snapshot=None, cooldown=0, error=None),
        weather_service=FakeWeatherService(),
        sleep_fn=sleeps.append,
        clock_fn=lambda: 1.0,
    )
    controller.pizzoo = FakePizzoo()

    controller.run_once()

    assert controller.current_state == RenderState.IDLE_HOLDING
    assert sleeps == [15]
    assert controller.no_data_retry_seconds == 30

