from pixoo_radar.render.common import measure_text_width
from pixoo_radar.render.holding_view import POLL_PAUSE_FONT_HEIGHT, build_and_send_poll_pause_screen
from pixoo_radar.settings import AppSettings
from tests.render_recorder import RecordingPizzoo


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


def test_poll_pause_screen_random_origin_keeps_text_within_display(monkeypatch):
    recorder = RecordingPizzoo()
    randint_calls = []

    def fake_randint(low, high):
        randint_calls.append((low, high))
        return high

    monkeypatch.setattr("pixoo_radar.render.holding_view.random.randint", fake_randint)

    build_and_send_poll_pause_screen(recorder, _settings(), resume_hhmm="0700")

    text_ops = [op for op in recorder.ops if op.get("op") == "draw_text"]
    assert len(text_ops) == 4
    assert randint_calls[0][0] == 0
    assert randint_calls[1][0] == 0
    for op in text_ops:
        x, y = op["xy"]
        text = op["text"]
        assert x >= 0
        assert y >= 0
        assert x + measure_text_width(text) <= 64
        assert y + POLL_PAUSE_FONT_HEIGHT <= 64
