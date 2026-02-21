from types import SimpleNamespace

from flight_data import FlightData
from pixoo_radar.flight.filters import choose_closest_flight


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


def _flight(
    *,
    icao: str,
    altitude: float,
    ground_speed: float,
    heading: float,
    lat: float = 1.0,
    lon: float = 1.0,
):
    return SimpleNamespace(
        airline_iata="AB",
        altitude=altitude,
        ground_speed=ground_speed,
        latitude=lat,
        longitude=lon,
        icao=icao,
        callsign="AB123",
        registration="N1",
        heading=heading,
    )


def test_stationary_ground_target_is_excluded():
    stationary = _flight(icao="icao1", altitude=0, ground_speed=0, heading=10)
    moving = _flight(icao="icao2", altitude=1000, ground_speed=250, heading=20, lat=1.1, lon=1.1)
    fd = FlightData(fr_api=FakeApi([stationary, moving]))
    data = fd.get_closest_flight_data(1.0, 1.0, save_logo=False)
    assert data is not None
    assert data["icao24"] == "icao2"


def test_ground_movement_aligned_with_runway_heading_is_allowed():
    # RUNWAY_HEADING_DEG in test config is 110; heading 112 is within +/-10 deg.
    aligned_ground = _flight(icao="icao1", altitude=0, ground_speed=15, heading=112)
    fd = FlightData(fr_api=FakeApi([aligned_ground]))
    data = fd.get_closest_flight_data(1.0, 1.0, save_logo=False)
    assert data is not None
    assert data["icao24"] == "icao1"


def test_ground_target_aligned_but_zero_speed_is_excluded():
    # Even when heading aligns with runway, speed must be > 0 to be shown.
    aligned_stationary = _flight(icao="icao1", altitude=0, ground_speed=0, heading=112)
    fd = FlightData(fr_api=FakeApi([aligned_stationary]))
    data = fd.get_closest_flight_data(1.0, 1.0, save_logo=False)
    assert data is None


def test_ground_movement_not_aligned_with_runway_is_excluded():
    taxiing = _flight(icao="icao1", altitude=0, ground_speed=15, heading=200)
    fd = FlightData(fr_api=FakeApi([taxiing]))
    data = fd.get_closest_flight_data(1.0, 1.0, save_logo=False)
    assert data is None


def test_ground_movement_aligned_with_reciprocal_runway_is_allowed():
    # Reciprocal of 110 is 290; heading 295 is within +/-10 deg.
    aligned_recip = _flight(icao="icao1", altitude=0, ground_speed=18, heading=295)
    fd = FlightData(fr_api=FakeApi([aligned_recip]))
    data = fd.get_closest_flight_data(1.0, 1.0, save_logo=False)
    assert data is not None
    assert data["icao24"] == "icao1"


def test_choose_closest_flight_can_return_filter_stats():
    stationary = _flight(icao="icao1", altitude=0, ground_speed=0, heading=112)
    taxiing = _flight(icao="icao2", altitude=0, ground_speed=15, heading=200)
    airborne = _flight(icao="icao3", altitude=1000, ground_speed=200, heading=110, lat=1.05, lon=1.05)

    closest, stats = choose_closest_flight(
        [stationary, taxiing, airborne],
        latitude=1.0,
        longitude=1.0,
        runway_heading_deg=110,
        return_stats=True,
    )

    assert closest is not None
    assert closest.icao == "icao3"
    assert stats["total"] == 3
    assert stats["stationary_ground"] == 1
    assert stats["taxiing_ground"] == 1
    assert stats["usable"] == 1
    assert stats["selected_distance_km"] is not None
