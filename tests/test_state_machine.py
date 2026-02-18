from pixoo_radar.models import RenderState


def test_render_states_are_flight_and_idle_weather_only():
    assert RenderState.FLIGHT_ACTIVE.value == "flight_active"
    assert RenderState.IDLE_WEATHER.value == "idle_weather"
    assert len(RenderState) == 2
