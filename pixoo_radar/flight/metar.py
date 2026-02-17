"""METAR fetcher utilities."""

import requests


def fetch_metar_report(icao: str | None, timeout_seconds: int = 5):
    """Fetch latest NOAA METAR text for the given ICAO code."""
    if not icao:
        return None
    station = str(icao).strip().upper()
    url = f"https://tgftp.nws.noaa.gov/data/observations/metar/stations/{station}.TXT"
    try:
        response = requests.get(url, timeout=timeout_seconds)
        if response.status_code != 200:
            return None
        lines = response.text.strip().splitlines()
        if not lines:
            return None
        if len(lines) >= 2:
            timestamp = lines[0].strip()
            raw = lines[1].strip()
        else:
            timestamp = None
            raw = lines[0].strip()
        return {"raw": raw, "timestamp": timestamp, "source": url}
    except Exception:
        return None

