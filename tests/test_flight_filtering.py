from types import SimpleNamespace

from flight_data import FlightData


class FakeApi:
    def __init__(self, flights):
        self._flights = flights

    def get_bounds_by_point(self, lat, lon, radius):
        return (lat, lon, radius)

    def get_flights(self, bounds=None):
        return self._flights

    def get_flight_details(self, flight):
        return {
            "identification": {"number": {"default": "AB123"}},
            "airport": {"origin": {"code": {"iata": "AAA"}}, "destination": {"code": {"iata": "BBB", "icao": "KBBB"}}},
            "airline": {"code": {"iata": "AB", "icao": "ABC"}, "name": "Air"},
        }


def test_stationary_ground_target_is_excluded():
    stationary = SimpleNamespace(
        airline_iata="AB",
        altitude=0,
        ground_speed=0,
        latitude=1.0,
        longitude=1.0,
        icao="icao1",
        callsign="AB123",
        registration="N1",
        heading=10,
    )
    moving = SimpleNamespace(
        airline_iata="AB",
        altitude=1000,
        ground_speed=250,
        latitude=1.1,
        longitude=1.1,
        icao="icao2",
        callsign="AB124",
        registration="N2",
        heading=20,
    )
    fd = FlightData(fr_api=FakeApi([stationary, moving]))
    data = fd.get_closest_flight_data(1.0, 1.0, save_logo=False)
    assert data is not None
    assert data["icao24"] == "icao2"
