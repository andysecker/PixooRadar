from flight_data import FlightData
from pixoo_radar.models import FlightSnapshot


class FlightService:
    def __init__(self, logo_dir: str):
        self._client = FlightData(save_logo_dir=logo_dir)

    def get_closest_flight(self, latitude: float, longitude: float):
        payload = self._client.get_closest_flight_data(latitude, longitude)
        if not payload:
            return None
        return FlightSnapshot.from_dict(payload)
