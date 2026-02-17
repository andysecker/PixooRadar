"""Flight candidate filtering and ranking helpers."""

from math import asin, cos, radians, sin, sqrt


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance in kilometers."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return c * 6371.0


def has_airline_info(flight) -> bool:
    """Return True when flight has non-empty airline identifier."""
    return bool(getattr(flight, "airline_iata", None))


def is_stationary_ground_target(flight) -> bool:
    """Exclude parked/idle transponders that pollute nearest-flight selection."""
    try:
        altitude = float(getattr(flight, "altitude", 0) or 0)
        ground_speed = float(getattr(flight, "ground_speed", 0) or 0)
    except (TypeError, ValueError):
        altitude = 0.0
        ground_speed = 0.0
    return altitude <= 0 and ground_speed <= 0


def choose_closest_flight(flights, latitude: float, longitude: float):
    """Return closest usable flight candidate or None."""
    closest_flight = None
    min_dist = float("inf")
    for flight in flights:
        if not has_airline_info(flight):
            continue
        if is_stationary_ground_target(flight):
            continue
        try:
            dist = haversine_km(latitude, longitude, flight.latitude, flight.longitude)
        except Exception:
            continue
        if dist < min_dist:
            min_dist = dist
            closest_flight = flight
    return closest_flight

