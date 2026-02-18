import pixoo_radar.render.flight_view as flight_view


def test_aircraft_display_prefers_icao_display_map(monkeypatch):
    monkeypatch.setattr(flight_view, "AIRCRAFT_MODEL_DISPLAY_MAP", {"A320": "A320 MAP"})
    assert flight_view.format_aircraft_display("Airbus A320", "A320") == "A320 MAP"


def test_aircraft_display_falls_back_to_text_after_first_space(monkeypatch):
    monkeypatch.setattr(flight_view, "AIRCRAFT_MODEL_DISPLAY_MAP", {})
    assert flight_view.format_aircraft_display("Antonov An-32", "AN32") == "An-32"


def test_aircraft_display_falls_back_to_icao_code(monkeypatch):
    monkeypatch.setattr(flight_view, "AIRCRAFT_MODEL_DISPLAY_MAP", {})
    assert flight_view.format_aircraft_display("", "B77W") == "B77W"
    assert flight_view.format_aircraft_display(None, "B77W") == "B77W"
