# Pixoo Radar

Pixoo64 display app with:

- `Flight mode`: shows the closest flight from FlightRadar24 data.
- `Idle weather mode`: always shows weather views (including runway/wind diagram) when no flights are available.

This is no longer the original fork behavior. The app now prioritizes useful always-on output instead of showing stale flight data.

## What It Shows

### Flight Mode
- Airline logo (cached locally)
- Route (`origin -> destination`)
- Callsign, altitude (raw feet), aircraft type text, registration
- Ground speed and heading
- Speed unit configurable (`mph` or `kt`)

### Idle Weather Mode
Two-frame weather loop (frame duration configurable):

1. Weather summary
- Top bar header shows METAR station/time when available (e.g. `LCPH 1130Z`), otherwise `Weather`
- Temperature
- Condition
- Humidity
- Wind (direction + speed, with gusts when available)

2. Runway wind diagram
- Runway drawn at your configured heading
- Wind arrow overlaid by current wind direction
- Active runway direction arrow (green), selected from wind/runway alignment
- Active runway designator label near the green arrow (requires runway label font config)
- North marker at top of the compass ring

## Data Sources

- Flight data: `FlightRadarAPI` (community package, unofficial access pattern)
- Weather conditions: Open-Meteo via `openmeteo-requests` (`weather_code` only)
- Weather temperature/wind: NOAA METAR (station configured by `WEATHER_METAR_ICAO`)
- Humidity: derived from METAR temperature + dewpoint (Magnus approximation)

## Requirements

- Python 3.10+
- Pixoo64 on your local network
- Internet access for FlightRadar24/Open-Meteo/NOAA METAR APIs
- Python package `metar` when `WEATHER_METAR_ICAO` is configured

## Install

```bash
git clone <your-fork-url>
cd PixooRadar
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.py config.py
```

Edit `config.py` for your local setup (Pixoo IP, coordinates, runway heading, units).

## Run

```bash
python display_flight_data_pizoo.py
python display_flight_data_pizoo.py --caffeinate
```

## Key Configuration

All runtime settings are in `config.py`.

- Device/location: `PIXOO_IP`, `PIXOO_PORT`, `LATITUDE`, `LONGITUDE`, `FLIGHT_SEARCH_RADIUS_METERS`
- Pixoo startup fail-fast: `PIXOO_STARTUP_CONNECT_TIMEOUT_SECONDS`
- Polling: `DATA_REFRESH_SECONDS`
- Idle weather: `WEATHER_REFRESH_SECONDS`, `WEATHER_VIEW_SECONDS`, `RUNWAY_HEADING_DEG`
- METAR source: `WEATHER_METAR_ICAO` (4-letter ICAO; blank disables METAR fields)
- Units: `FLIGHT_SPEED_UNIT` (`mph` or `kt`), `WEATHER_WIND_SPEED_UNIT` (`mph` or `kmh`; legacy `kph` accepted)
- Fonts: `FONT_NAME`, `FONT_PATH`, `RUNWAY_LABEL_FONT_NAME`, `RUNWAY_LABEL_FONT_PATH` (required)
- Logging: `LOG_LEVEL`, `LOG_VERBOSE_EVENTS`
- Startup validates config values and file paths and exits with clear errors if invalid.
- Startup validates weather sources by fetching Open-Meteo (and METAR when configured) before entering the main loop.
- If `WEATHER_METAR_ICAO` is set, startup also hard-fails unless dependency `metar` is installed.

## Runtime Behavior

State machine values:

- `flight_active`
- `idle_weather`

Operational behavior:

- Flight view is re-rendered when tracked flight telemetry changes (altitude, speed, heading, status).
- Flight page 1 displays `CS` + raw altitude in feet (`12,345 ft`), not flight level (`FLxxx`).
- Flight page 2 displays aircraft text parsed from `aircraft_type` (substring after first space, with ICAO code fallback) and `REG`.
- Stationary ground targets are filtered out (`altitude<=0` and `ground_speed<=0`).
- Moving ground targets are filtered as taxiing unless heading aligns with runway heading or reciprocal within `+/-10` degrees.
- Flight API is polled on a fixed interval (`DATA_REFRESH_SECONDS`) for all flight polling.
- No exponential backoff is used for no-flight periods.
- If Pixoo is offline, flight/weather API polling is paused until reconnect succeeds.
- Pixoo HTTP requests use a finite timeout (5s) to avoid indefinite hangs during device/network failures.
- Each render path resets stale frame buffers before drawing to prevent frame accumulation after failed renders.
- Debug render output is written before send to `debug/current_pixoo_render.gif` (single rolling file).
- Weather refresh logs include both raw provider payloads (Open-Meteo + METAR) and normalized payload.
- Each API call logs immediate raw return data:
  - `Open-Meteo raw response: ...`
  - `METAR raw response (ICAO): ...`
- METAR raw string is logged on every weather refresh.
- FlightRadar selected-flight/details raw payload dumps are available at `DEBUG` level only (to avoid very large `INFO` logs).
- Weather wind line format:
  - non-gusting: e.g. `NE 10Mph`
  - gusting: e.g. `NE 10/18`
  - unknown direction: `--`
- Weather summary top header format:
  - with METAR station+time: `ICAO HHMMZ` (example: `LCPH 1130Z`)
  - fallback when unavailable: `Weather`
- On runway weather view, if METAR provides variable wind sector (`dddVddd`), nearest boundary tick marks are highlighted in orange.

## Refactored Architecture

- `display_flight_data_pizoo.py`: bootstrap entrypoint
- `pixoo_radar/settings.py`: typed `AppSettings` loaded from `config.py`
- `pixoo_radar/models.py`: `FlightSnapshot`, `WeatherSnapshot`, `RenderState`
- `pixoo_radar/controller.py`: polling loop and state transitions
- `pixoo_radar/flight/provider.py`: FlightRadar24 provider adapter
- `pixoo_radar/flight/filters.py`: candidate filtering and closest-flight selection
- `pixoo_radar/flight/mapping.py`: payload mapping helpers
- `pixoo_radar/flight/logos.py`: logo cache/resize handling
- `pixoo_radar/services/pixoo_client.py`: Pixoo connect/reconnect/reachability/font loading
- `pixoo_radar/services/flight_service.py`: flight service wrapper
- `pixoo_radar/services/weather_service.py`: weather service wrapper
- `pixoo_radar/render/flight_view.py`: flight animation
- `pixoo_radar/render/weather_view.py`: weather summary + runway/wind diagram
- `flight_data.py`: FlightRadar/API integration, logo handling, METAR
- `weather_data.py`: Open-Meteo provider and cache

## Development Checks

```bash
.venv/bin/python -m py_compile \
  display_flight_data_pizoo.py flight_data.py weather_data.py \
  pixoo_radar/settings.py pixoo_radar/models.py pixoo_radar/controller.py \
  pixoo_radar/flight/provider.py pixoo_radar/flight/filters.py \
  pixoo_radar/flight/mapping.py \
  pixoo_radar/flight/logos.py \
  pixoo_radar/render/common.py pixoo_radar/render/flight_view.py \
  pixoo_radar/render/weather_view.py pixoo_radar/render/holding_view.py \
  pixoo_radar/services/pixoo_client.py pixoo_radar/services/flight_service.py \
  pixoo_radar/services/weather_service.py
```

```bash
.venv/bin/python -m pytest -q
```

Current tests cover:

- state transition resolution
- controller deterministic cycle timing (`run_once` with injected sleeper/clock)
- runway active-heading and label placement helpers
- renderer golden snapshots (weather summary, runway diagram hash, holding screen hash)
- stationary ground-flight filtering
- taxiing ground-flight filtering (runway-alignment gate for moving ground targets)
- aircraft display text parsing fallback behavior
- weather cache and force-refresh behavior
- settings validation (units, ranges, timings, font paths)
- Pixoo runway-label font diagnostic error messaging

## Validation Workflow

This project currently uses local validation rather than hosted CI.

- Recommended check before pushing: `.venv/bin/python -m pytest -q`
- Optional stricter checks remain available locally:
  - `.venv/bin/python -m py_compile $(git ls-files '*.py')`
  - `.venv/bin/python -m ruff check .`
  - `.venv/bin/python -m mypy`

## Notes

- `config.py` is intended to stay local and untracked.
- If using a Raspberry Pi, run this under `systemd` or `screen` for 24/7 uptime.
- Flight API behavior can vary; this app now polls at a fixed interval (`DATA_REFRESH_SECONDS`).
