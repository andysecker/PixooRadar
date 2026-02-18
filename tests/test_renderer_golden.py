import hashlib
import json
from pathlib import Path

from pixoo_radar.render.holding_view import build_and_send_holding_screen
from pixoo_radar.render.weather_view import draw_runway_wind_diagram, draw_weather_summary_frame
from pixoo_radar.settings import AppSettings
from tests.render_recorder import RecordingPizzoo

GOLDEN_DIR = Path(__file__).parent / "golden"


def _settings():
    return AppSettings(
        pixoo_ip="127.0.0.1",
        pixoo_port=80,
        pixoo_reconnect_seconds=1,
        font_name="splitflap",
        font_path="./fonts/splitflap.bdf",
        runway_label_font_name="splitflap",
        runway_label_font_path="./fonts/splitflap.bdf",
        animation_frame_speed=300,
        color_box="#454545",
        color_text="#FFFF00",
        data_refresh_seconds=60,
        flight_search_radius_meters=50000,
        flight_speed_unit="mph",
        latitude=0,
        longitude=0,
        log_level="INFO",
        log_verbose_events=True,
        logo_dir="airline_logos",
        runway_heading_deg=110,
        weather_refresh_seconds=900,
        weather_view_seconds=10,
        weather_wind_speed_unit="mph",
    )


def _ops_sha256(ops) -> str:
    payload = json.dumps(ops, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_weather_summary_frame_snapshot():
    recorder = RecordingPizzoo()
    draw_weather_summary_frame(
        recorder,
        _settings(),
        {
            "condition": "CLEAR",
            "temperature_c": 22.4,
            "humidity_pct": 55.2,
            "wind_kph": 16.0,
            "wind_dir_deg": 45.0,
        },
    )

    expected_path = GOLDEN_DIR / "weather_summary_frame.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    assert recorder.ops == expected


def test_runway_diagram_snapshot_hash():
    recorder = RecordingPizzoo()
    draw_runway_wind_diagram(
        recorder,
        _settings(),
        wind_dir_deg=90.0,
        runway_heading_deg=110.0,
    )

    expected_hash = (GOLDEN_DIR / "runway_diagram.sha256").read_text(encoding="utf-8").strip()
    assert _ops_sha256(recorder.ops) == expected_hash


def test_holding_screen_snapshot_hash():
    recorder = RecordingPizzoo()
    build_and_send_holding_screen(recorder, _settings(), status="NO FLIGHTS")

    expected_hash = (GOLDEN_DIR / "holding_screen.sha256").read_text(encoding="utf-8").strip()
    assert _ops_sha256(recorder.ops) == expected_hash
