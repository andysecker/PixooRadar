from pixoo_radar.render.weather_view import COLOR_ACTIVE_RWY_ARROW, COLOR_WIND_ARROW, draw_runway_wind_diagram, draw_weather_summary_frame
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
        no_flight_retry_seconds=15,
        no_flight_max_retry_seconds=120,
        runway_heading_deg=110,
        weather_refresh_seconds=900,
        weather_view_seconds=10,
        weather_wind_speed_unit="mph",
    )


def test_weather_summary_omits_wind_direction_when_missing():
    recorder = RecordingPizzoo()
    draw_weather_summary_frame(
        recorder,
        _settings(),
        {
            "condition": "CLEAR",
            "temperature_c": 22.4,
            "humidity_pct": 55.2,
            "wind_kph": 16.0,
            "wind_dir_deg": None,
        },
    )
    bottom_text = [op["text"] for op in recorder.ops if op.get("op") == "draw_text" and op.get("xy", [None, None])[1] == 49]
    assert bottom_text == ["- 10Mph"]


def test_runway_diagram_omits_wind_and_active_runway_arrows_when_wind_direction_missing():
    recorder = RecordingPizzoo()
    draw_runway_wind_diagram(
        recorder,
        _settings(),
        wind_dir_deg=None,
        runway_heading_deg=110.0,
    )
    colors = [op.get("color") for op in recorder.ops if op.get("op") == "draw_rectangle"]
    assert COLOR_WIND_ARROW not in colors
    assert COLOR_ACTIVE_RWY_ARROW not in colors


def test_runway_diagram_highlights_variable_wind_ticks_when_range_available():
    recorder = RecordingPizzoo()
    draw_runway_wind_diagram(
        recorder,
        _settings(),
        wind_dir_deg=None,
        runway_heading_deg=110.0,
        wind_dir_from=120,
        wind_dir_to=180,
    )
    orange_ticks = [
        op for op in recorder.ops
        if op.get("op") == "draw_rectangle" and op.get("color") == COLOR_WIND_ARROW and op.get("width") == 1 and op.get("height") == 1
    ]
    assert orange_ticks
