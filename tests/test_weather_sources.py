import sys
import types
from datetime import datetime, timezone

import pytest

from weather_data import WeatherData


def test_weather_uses_metar_for_temp_wind_and_open_meteo_for_condition():
    def open_meteo_provider(_lat, _lon):
        return {"condition": "OVERCAST"}

    def metar_fetcher(_icao):
        return {
            "raw": "LCPH 170850Z 27012KT 9999 FEW020 20/10 Q1016",
            "timestamp": "2026/02/17 08:50",
        }

    wx = WeatherData(
        latitude=34.0,
        longitude=32.0,
        refresh_seconds=900,
        metar_icao="LCPH",
        provider=open_meteo_provider,
        metar_fetcher=metar_fetcher,
        metar_parser=lambda _payload: {
            "temperature_c": 20,
            "dewpoint_c": 10,
            "wind_dir_deg": 270,
            "wind_dir_from": 250,
            "wind_dir_to": 290,
            "wind_speed_kph": 12 * 1.852,
            "wind_gust_kph": 18 * 1.852,
            "metar_station": "LCPH",
            "metar_day_utc": 17,
            "metar_time_z": "0850Z",
            "location": "LCPH",
        },
        timezone_name="Europe/Nicosia",
        iata_mapper=lambda _icao: "PFO",
        utc_now_provider=lambda: datetime(2026, 2, 17, 10, 0, tzinfo=timezone.utc),
    )
    payload, refreshed = wx.get_current_with_options(force_refresh=True)

    assert refreshed is True
    assert payload["condition"] == "OVERCAST"
    assert payload["temperature_c"] == 20
    assert payload["wind_dir_deg"] == 270
    assert payload["wind_dir_from"] == 250
    assert payload["wind_dir_to"] == 290
    assert payload["wind_kph"] == pytest.approx(12 * 1.852)
    assert payload["wind_gust_kph"] == pytest.approx(18 * 1.852)
    assert payload["metar_station"] == "LCPH"
    assert payload["metar_station_iata"] == "PFO"
    assert payload["metar_time_z"] == "0850Z"
    assert payload["metar_time_local"] == "1050"
    assert payload["humidity_pct"] is not None
    assert payload["source"] == "metar+open-meteo"


def test_weather_uses_open_meteo_condition_when_metar_missing():
    def open_meteo_provider(_lat, _lon):
        return {"condition": "CLEAR"}

    wx = WeatherData(
        latitude=34.0,
        longitude=32.0,
        refresh_seconds=900,
        metar_icao="LCPH",
        provider=open_meteo_provider,
        metar_fetcher=lambda _icao: None,
        metar_parser=lambda _payload: {},
    )
    payload, _ = wx.get_current_with_options(force_refresh=True)

    assert payload["condition"] == "CLEAR"
    assert payload["temperature_c"] is None
    assert payload["wind_kph"] is None
    assert payload["source"] == "open-meteo"


def test_parse_metar_with_library_handles_negative_temp_and_variable_wind():
    pytest.importorskip("metar")
    wx = WeatherData(latitude=0.0, longitude=0.0, metar_parser=None)
    parsed = wx._parse_metar_fields_with_library({"raw": "EGXX 170850Z VRB03KT 9999 FEW020 M02/M05 Q1016"})
    assert parsed["temperature_c"] == -2
    assert parsed["dewpoint_c"] == -5
    assert parsed["wind_speed_kph"] == pytest.approx(3 * 1.852, rel=0.05)
    assert parsed["wind_dir_deg"] is None
    assert parsed["metar_day_utc"] == 17
    assert parsed["metar_time_z"] == "0850Z"


def test_parse_metar_with_library_extracts_wind_gust():
    pytest.importorskip("metar")
    wx = WeatherData(latitude=0.0, longitude=0.0, metar_parser=None)
    parsed = wx._parse_metar_fields_with_library({"raw": "EGXX 170850Z 26010G18KT 9999 FEW020 12/08 Q1016"})
    assert parsed["wind_speed_kph"] == pytest.approx(10 * 1.852, rel=0.05)
    assert parsed["wind_gust_kph"] == pytest.approx(18 * 1.852, rel=0.05)


def test_open_meteo_fetch_requests_only_weather_code(monkeypatch):
    captured = {}

    class FakeVar:
        def __init__(self, value):
            self._value = value

        def Value(self):
            return self._value

    class FakeCurrent:
        def Variables(self, idx):
            assert idx == 0
            return FakeVar(3)

    class FakeResponse:
        def Current(self):
            return FakeCurrent()

    class FakeClient:
        def weather_api(self, url, params):
            captured["url"] = url
            captured["params"] = params
            return [FakeResponse()]

    fake_module = types.SimpleNamespace(Client=lambda: FakeClient())
    monkeypatch.setitem(sys.modules, "openmeteo_requests", fake_module)

    wx = WeatherData(latitude=34.0, longitude=32.0)
    payload = wx._fetch_from_provider(34.0, 32.0)

    assert captured["url"] == wx.OPEN_METEO_URL
    assert captured["params"]["current"] == ["weather_code"]
    assert payload["condition"] == "OVERCAST"


def test_relative_humidity_derived_from_celsius_temp_and_dewpoint():
    rh = WeatherData._relative_humidity_from_temp_dewpoint(20.0, 10.0)
    assert rh == pytest.approx(52.5, abs=0.5)


def test_weather_startup_validation_fails_when_openmeteo_condition_missing():
    wx = WeatherData(
        latitude=34.0,
        longitude=32.0,
        provider=lambda _lat, _lon: None,
        metar_fetcher=lambda _icao: None,
        metar_icao="",
    )
    with pytest.raises(RuntimeError, match="Open-Meteo condition is unavailable"):
        wx.validate_startup_sources(require_metar=False)


def test_weather_startup_validation_fails_when_required_metar_missing():
    wx = WeatherData(
        latitude=34.0,
        longitude=32.0,
        provider=lambda _lat, _lon: {"condition": "CLEAR"},
        metar_fetcher=lambda _icao: None,
        metar_icao="LCPH",
    )
    with pytest.raises(RuntimeError, match="no METAR raw data returned"):
        wx.validate_startup_sources(require_metar=True)
