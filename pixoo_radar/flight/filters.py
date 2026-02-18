"""Flight candidate filtering and ranking helpers."""

from math import asin, cos, isfinite, radians, sin, sqrt


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


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_heading_deg(value):
    heading = _to_float(value, default=None)
    if heading is None or not isfinite(heading):
        return None
    return heading % 360.0


def heading_diff_deg(a: float, b: float) -> float:
    """Return smallest absolute angle difference in degrees."""
    return abs(((a - b + 180.0) % 360.0) - 180.0)


def is_ground_target(flight) -> bool:
    altitude = _to_float(getattr(flight, "altitude", 0) or 0, default=0.0)
    return altitude <= 0


def is_stationary_ground_target(flight) -> bool:
    """Exclude parked/idle transponders that pollute nearest-flight selection."""
    if not is_ground_target(flight):
        return False
    ground_speed = _to_float(getattr(flight, "ground_speed", 0) or 0, default=0.0)
    return ground_speed <= 0


def is_taxiing_ground_target(
    flight,
    runway_heading_deg: float,
    alignment_tolerance_deg: float = 10.0,
) -> bool:
    """
    Exclude moving ground targets not aligned with runway heading/reciprocal.

    Ground targets moving along runway direction are kept so landing/takeoff
    traffic can still be displayed.
    """
    if not is_ground_target(flight):
        return False
    ground_speed = _to_float(getattr(flight, "ground_speed", 0) or 0, default=0.0)
    if ground_speed <= 0:
        return False

    heading = _normalize_heading_deg(getattr(flight, "heading", None))
    runway_heading = _normalize_heading_deg(runway_heading_deg)
    if heading is None or runway_heading is None:
        return True

    reciprocal_heading = (runway_heading + 180.0) % 360.0
    tolerance = max(0.0, _to_float(alignment_tolerance_deg, default=10.0))
    aligned = (
        heading_diff_deg(heading, runway_heading) <= tolerance
        or heading_diff_deg(heading, reciprocal_heading) <= tolerance
    )
    return not aligned


def choose_closest_flight(
    flights,
    latitude: float,
    longitude: float,
    runway_heading_deg: float,
    alignment_tolerance_deg: float = 10.0,
):
    """Return closest usable flight candidate or None."""
    closest_flight = None
    min_dist = float("inf")
    for flight in flights:
        if not has_airline_info(flight):
            continue
        if is_stationary_ground_target(flight):
            continue
        if is_taxiing_ground_target(
            flight,
            runway_heading_deg=runway_heading_deg,
            alignment_tolerance_deg=alignment_tolerance_deg,
        ):
            continue
        try:
            dist = haversine_km(latitude, longitude, flight.latitude, flight.longitude)
        except Exception:
            continue
        if dist < min_dist:
            min_dist = dist
            closest_flight = flight
    return closest_flight
