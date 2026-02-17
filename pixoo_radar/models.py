from dataclasses import dataclass
from enum import Enum


class RenderState(str, Enum):
    FLIGHT_ACTIVE = "flight_active"
    IDLE_WEATHER = "idle_weather"
    RATE_LIMIT = "rate_limit"
    API_ERROR = "api_error"


@dataclass(frozen=True)
class FlightSnapshot:
    icao24: str | None
    flight_number: str | None
    origin: str | None
    destination: str | None
    altitude: float | int | None
    ground_speed: float | int | None
    heading: float | int | None
    status: str | None
    payload: dict

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            icao24=data.get("icao24"),
            flight_number=data.get("flight_number"),
            origin=data.get("origin"),
            destination=data.get("destination"),
            altitude=data.get("altitude"),
            ground_speed=data.get("ground_speed"),
            heading=data.get("heading"),
            status=data.get("status"),
            payload=data,
        )


@dataclass(frozen=True)
class WeatherSnapshot:
    temperature_c: float | int | None
    condition: str | None
    humidity_pct: float | int | None
    wind_kph: float | int | None
    wind_dir_deg: float | int | None
    wind_dir_from: float | int | None
    wind_dir_to: float | int | None
    location: str | None
    source: str | None
    payload: dict

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            temperature_c=data.get("temperature_c"),
            condition=data.get("condition"),
            humidity_pct=data.get("humidity_pct"),
            wind_kph=data.get("wind_kph"),
            wind_dir_deg=data.get("wind_dir_deg"),
            wind_dir_from=data.get("wind_dir_from"),
            wind_dir_to=data.get("wind_dir_to"),
            location=data.get("location"),
            source=data.get("source"),
            payload=data,
        )
