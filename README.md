# Pixoo Radar

A state-driven Pixoo64 display that does two jobs:

- `Flight mode`: shows the closest nearby aircraft from FlightRadar24 data.
- `Idle mode`: when no flights are in range, shows weather views (including a runway wind diagram) or a holding screen.

This is no longer the original fork behavior. The app now prioritizes useful always-on output instead of showing stale flight data.

## What It Shows

### Flight Mode
- Airline logo (cached locally)
- Route (`origin -> destination`)
- Flight number, altitude, aircraft type, registration
- Ground speed and heading
- Speed unit configurable (`mph` or `kt`)

### Idle Weather Mode
Two-frame weather loop (frame duration configurable):

1. Weather summary
- Temperature
- Condition
- Humidity
- Wind (direction + speed)

2. Runway wind diagram
- Runway drawn at your configured heading
- Wind arrow overlaid by current wind direction
- North marker at top of the compass ring

## Data Sources

- Flight data: `FlightRadarAPI` (community package, unofficial access pattern)
- Weather data: Open-Meteo via `openmeteo-requests`
- Destination METAR enrichment: NOAA

## Requirements

- Python 3.10+
- Pixoo64 on your local network
- Internet access for flight/weather APIs

## Installation

```bash
git clone <your-fork-url>
cd PixooRadar
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create your local config:

```bash
cp config.example.py config.py
# then edit config.py
```

Run:

```bash
python display_flight_data_pizoo.py
```

Optional (macOS):

```bash
python display_flight_data_pizoo.py --caffeinate
```

## Configuration

All settings are in `config.py`.

### Device / Location
- `PIXOO_IP`
- `PIXOO_RECONNECT_SECONDS`
- `LATITUDE`
- `LONGITUDE`
- `FLIGHT_SEARCH_RADIUS_METERS`

### Flight Polling / Backoff
- `DATA_REFRESH_SECONDS`
- `NO_FLIGHT_RETRY_SECONDS`
- `NO_FLIGHT_MAX_RETRY_SECONDS`
- `API_RATE_LIMIT_COOLDOWN_SECONDS`

### Idle Behavior
- `IDLE_MODE` (`"weather"` or `"holding"`)
- `WEATHER_REFRESH_SECONDS`
- `WEATHER_VIEW_SECONDS`
- `RUNWAY_HEADING_DEG`

### Units
- `FLIGHT_SPEED_UNIT` (`"mph"` or `"kt"`)
- `WEATHER_WIND_SPEED_UNIT` (`"mph"` or `"kph"`)

### Rendering
- `ANIMATION_FRAME_SPEED`
- `FONT_NAME`, `FONT_PATH`
- `LOGO_DIR`

## Runtime Behavior

The app switches display state based on data availability:

- `flight_active`: renders flight animation
- `idle_weather`: renders two weather views
- `idle_holding`: renders static holding view
- `rate_limit`: explicit cooldown view when rate-limited
- `api_error`: explicit API error view

When no usable flight is available, stale flight content is cleared and replaced by idle output.

Weather refresh logging is explicit:
- `Weather updated from API (...)` when new weather is fetched successfully.
- `Weather refresh failed (...); using cached/fallback weather data.` when provider calls fail.

Pixoo reconnect logging is explicit:
- `Connecting to Pixoo at ...` on connect attempts.
- `Pixoo unavailable (...). Retrying in ...s...` while offline.
- `Lost Pixoo connection while rendering ...` when connection drops mid-run.

## Project Structure

- `display_flight_data_pizoo.py` main app + rendering/state machine
- `flight_data.py` flight retrieval, filtering, logo caching, METAR enrichment
- `weather_data.py` weather provider and cache
- `config.py` local runtime configuration (ignored by git)
- `config.example.py` template for new setups

## Notes

- `config.py` is intended to stay local and untracked.
- If using a Raspberry Pi, run this under `systemd` or `screen` for 24/7 uptime.
- Flight API behavior can vary; backoff/cooldown settings are important for long-running stability.
