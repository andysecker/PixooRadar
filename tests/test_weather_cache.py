from weather_data import WeatherData


class Provider:
    def __init__(self):
        self.calls = 0

    def __call__(self, lat, lon):
        self.calls += 1
        return {
            "temperature_c": 20,
            "condition": "CLEAR",
            "humidity_pct": 50,
            "wind_kph": 10,
            "wind_dir_deg": 90,
            "location": "LOCAL WX",
            "source": "test",
        }


def test_weather_cache_and_force_refresh():
    provider = Provider()
    wx = WeatherData(latitude=1.0, longitude=1.0, refresh_seconds=900, provider=provider)

    _, refreshed1 = wx.get_current()
    _, refreshed2 = wx.get_current()
    _, refreshed3 = wx.get_current_with_options(force_refresh=True)

    assert refreshed1 is True
    assert refreshed2 is False
    assert refreshed3 is True
    assert provider.calls == 2
