from pixoo_radar.render.flight_view import format_aircraft_display


def test_aircraft_display_uses_text_after_first_space():
    assert format_aircraft_display("Airbus A320", "A320") == "A320"
    assert format_aircraft_display("Antonov An-32", "AN32") == "An-32"


def test_aircraft_display_uses_full_text_when_no_space():
    assert format_aircraft_display("A320", "A320") == "A320"


def test_aircraft_display_falls_back_to_icao_code():
    assert format_aircraft_display("", "B77W") == "B77W"
    assert format_aircraft_display(None, "B77W") == "B77W"
