import pytest

from pixoo_radar.services.pixoo_client import PixooClient
from pixoo_radar.settings import AppSettings


class FakePixoo:
    def __init__(self):
        self.calls = []

    def load_font(self, name, path):
        self.calls.append((name, path))
        if name == "runway" and path == "bad/path.bdf":
            raise ValueError("missing file")


def _settings():
    return AppSettings(
        pixoo_ip="127.0.0.1",
        pixoo_port=80,
        pixoo_reconnect_seconds=1,
        font_name="main",
        font_path="main/path.bdf",
        runway_label_font_name="runway",
        runway_label_font_path="bad/path.bdf",
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
        idle_mode="weather",
        no_flight_retry_seconds=15,
        no_flight_max_retry_seconds=120,
        runway_heading_deg=110,
        weather_refresh_seconds=900,
        weather_view_seconds=10,
        weather_wind_speed_unit="mph",
    )


def test_runway_label_font_failure_has_diagnostic_message():
    client = PixooClient(_settings())
    with pytest.raises(RuntimeError) as exc:
        client._load_fonts(FakePixoo())
    message = str(exc.value)
    assert "Failed to load runway label font 'runway'" in message
    assert "from 'bad/path.bdf'" in message
