from weather_data import WeatherData
from pixoo_radar.models import WeatherSnapshot


class WeatherService:
    def __init__(self, latitude: float, longitude: float, refresh_seconds: int):
        self._client = WeatherData(latitude=latitude, longitude=longitude, refresh_seconds=refresh_seconds)

    def get_current(self):
        payload, refreshed = self._client.get_current()
        return WeatherSnapshot.from_dict(payload), refreshed

    def get_current_with_options(self, force_refresh: bool = False):
        payload, refreshed = self._client.get_current_with_options(force_refresh=force_refresh)
        return WeatherSnapshot.from_dict(payload), refreshed

    def get_last_error(self):
        return self._client.get_last_error()
