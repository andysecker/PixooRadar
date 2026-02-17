"""Flight payload mapping helpers."""


def safe_get(mapping, *keys):
    """Nested dict lookup with graceful None fallback."""
    value = mapping
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def build_flight_payload(closest_flight, details: dict | None):
    """Map provider objects/details into a stable payload dict."""
    details = details or {}

    trail_point = None
    if isinstance(details.get("trail"), list) and details["trail"]:
        trail_point = details["trail"][0] or details["trail"][-1]

    return {
        "icao24": getattr(closest_flight, "icao", None) or safe_get(details, "identification", "id"),
        "callsign": safe_get(details, "identification", "callsign") or getattr(closest_flight, "callsign", None),
        "flight_number": safe_get(details, "identification", "number", "default"),
        "registration": safe_get(details, "aircraft", "registration") or getattr(closest_flight, "registration", None),
        "aircraft_type": safe_get(details, "aircraft", "model", "text"),
        "aircraft_type_icao": safe_get(details, "aircraft", "model", "code"),
        "airline": safe_get(details, "airline", "name"),
        "airline_icao": safe_get(details, "airline", "code", "icao"),
        "airline_iata": safe_get(details, "airline", "code", "iata"),
        "origin": safe_get(details, "airport", "origin", "code", "iata"),
        "destination": safe_get(details, "airport", "destination", "code", "iata"),
        "destination_icao": safe_get(details, "airport", "destination", "code", "icao"),
        "latitude": getattr(closest_flight, "latitude", None) or (trail_point and trail_point.get("lat")),
        "longitude": getattr(closest_flight, "longitude", None) or (trail_point and trail_point.get("lng")),
        "altitude": getattr(closest_flight, "altitude", None),
        "ground_speed": getattr(closest_flight, "ground_speed", None),
        "heading": getattr(closest_flight, "heading", None),
        "status": safe_get(details, "status", "text"),
        "scheduled_departure": safe_get(details, "time", "scheduled", "departure"),
        "scheduled_arrival": safe_get(details, "time", "scheduled", "arrival"),
        "estimated_arrival": safe_get(details, "time", "estimated", "arrival"),
    }

