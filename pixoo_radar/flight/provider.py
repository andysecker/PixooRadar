"""FlightRadar24 provider adapter."""

try:
    # Expected package for this project: FlightRadarAPI (module: FlightRadar24)
    from FlightRadar24.api import FlightRadar24API
except ModuleNotFoundError as exc:
    if exc.name == "FlightRadar24":
        raise ImportError(
            "Missing compatible FlightRadar24 client. Install `FlightRadarAPI` and remove `flightradar24` if present: "
            "`pip uninstall -y flightradar24 && pip install FlightRadarAPI`."
        ) from exc
    if exc.name == "bs4":
        raise ImportError(
            "Missing dependency `beautifulsoup4` required by `FlightRadarAPI`. "
            "Install it with: `pip install beautifulsoup4`."
        ) from exc
    raise


class FlightRadarProvider:
    """Small adapter around FlightRadar24 API client."""

    def __init__(self, fr_api: FlightRadar24API | None = None, search_radius_meters: int = 50000):
        self._client = fr_api or FlightRadar24API()
        self.search_radius_meters = int(search_radius_meters)

    def get_flights_near(self, latitude: float, longitude: float):
        bounds = self._client.get_bounds_by_point(latitude, longitude, self.search_radius_meters)
        return self._client.get_flights(bounds=bounds)

    def get_flight_details(self, flight):
        return self._client.get_flight_details(flight)

    def get_airline_logo(self, airline_iata: str | None, airline_icao: str | None):
        return self._client.get_airline_logo(iata=airline_iata, icao=airline_icao)

