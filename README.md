# Pixoo Radar

Pixoo64 display app with:

- `Flight mode`: shows the closest flight from FlightRadar24 data.
- `Idle weather mode`: always shows weather summary when no flights are available, and adds runway/wind diagram when wind direction is available.

This is no longer the original fork behavior. The app now prioritizes useful always-on output instead of showing stale flight data.

## What It Shows

### Flight Mode
- Airline logo (cached locally)
- Route (`origin -> destination`)
- Callsign, altitude (raw feet), aircraft type text, registration
- Ground speed and heading
- Speed unit configurable (`mph` or `kt`)

### Idle Weather Mode
Weather loop (frame duration configurable):

1. Weather summary
- Top bar header shows METAR station/time when available in human-friendly local format (e.g. `PFO 1330`), otherwise `Weather`
  - Station uses IATA code when mappable from METAR ICAO; otherwise ICAO is used
  - Time is converted from METAR UTC to local time using timezone derived from `LATITUDE`/`LONGITUDE`
  - Header text is centered in the top accent bar
- Temperature
- Condition
- Humidity
- Wind (direction + speed, with gusts when available)
  - Variable direction (`VRB`) shows as `VAR`
  - Missing/omitted direction shows as `-`

2. Runway wind diagram (shown only when wind direction bearing is available)
- Runway drawn at your configured heading
- View is rotated 180° (south-up orientation)
- Wind arrow overlaid by current wind direction
- Active runway direction arrow (green), selected from wind/runway alignment
- Active runway designator label near the green arrow (requires runway label font config)
- South marker (`S`, small font) at top center
- Top-center tick mark is intentionally suppressed to keep `S` legible

## Data Sources

- Flight data: `FlightRadarAPI` (community package, unofficial access pattern)
- Weather conditions: Open-Meteo via `openmeteo-requests` (`weather_code` only)
- Weather temperature/wind: NOAA METAR (station configured by `WEATHER_METAR_ICAO`)
- Humidity: derived from METAR temperature + dewpoint (Magnus approximation)

## Requirements

- Python 3.10+
- Pixoo64 on your local network
- Internet access for FlightRadar24/Open-Meteo/NOAA METAR APIs
- Python packages `metar`, `timezonefinder`, and `airportsdata` when `WEATHER_METAR_ICAO` is configured

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
python display_flight_data_pizoo.py --test-flight
```

## Key Configuration

All runtime settings are in `config.py`.

- Device/location: `PIXOO_IP`, `PIXOO_PORT`, `LATITUDE`, `LONGITUDE`, `FLIGHT_SEARCH_RADIUS_METERS`
- Pixoo startup fail-fast: `PIXOO_STARTUP_CONNECT_TIMEOUT_SECONDS`
- Polling: `DATA_REFRESH_SECONDS`
- Optional polling pause window (local time): `POLL_PAUSE_START_LOCAL`, `POLL_PAUSE_END_LOCAL` (`HHMM`)
- Idle weather: `WEATHER_REFRESH_SECONDS`, `WEATHER_VIEW_SECONDS`, `RUNWAY_HEADING_DEG`
- METAR source: `WEATHER_METAR_ICAO` (4-letter ICAO; blank disables METAR fields)
- Units: `FLIGHT_SPEED_UNIT` (`mph` or `kt`), `WEATHER_WIND_SPEED_UNIT` (`mph` or `kmh`; legacy `kph` accepted)
- Fonts: `FONT_NAME`, `FONT_PATH`, `RUNWAY_LABEL_FONT_NAME`, `RUNWAY_LABEL_FONT_PATH` (required)
- Logging: `LOG_LEVEL`, `LOG_VERBOSE_EVENTS`
- App logs are written to console and to `logs/pixoo_radar.log` with daily rotation (7 days retained).
- Startup validates config values and file paths and exits with clear errors if invalid.
- Startup validates weather sources by fetching Open-Meteo (and METAR when configured) before entering the main loop.
- If `WEATHER_METAR_ICAO` is set, startup also hard-fails unless dependencies `metar`, `timezonefinder`, and `airportsdata` are installed.

## Runtime Behavior

State machine values:

- `flight_active`
- `idle_weather`

Operational behavior:

- Flight view is re-rendered when tracked flight telemetry changes (altitude, speed, heading, status).
- Flight page 1 displays flight identifier as text-only + raw altitude in feet (`12,345 ft`), not flight level (`FLxxx`).
- Flight page 2 displays aircraft text from ICAO mapping (`aircraft_type_icao -> model_display`) and `REG`.
- ICAO display map source: `data/icao_model_display_map.json` (10-char-safe values for 64x64 text layout).
- Fallback behavior when ICAO code is missing from map: parse `aircraft_type` (substring after first space), then ICAO code.
- Stationary ground targets are filtered out (`altitude<=0` and `ground_speed<=0`).
- Moving ground targets are filtered as taxiing unless heading aligns with runway heading or reciprocal within `+/-10` degrees.
- Flight API is polled on a fixed interval (`DATA_REFRESH_SECONDS`) for all flight polling.
- No exponential backoff is used for no-flight periods.
- Optional local-time pause window can suspend all polling activity:
  - set both `POLL_PAUSE_START_LOCAL` and `POLL_PAUSE_END_LOCAL` in `HHMM` (24-hour) format
  - each loop checks current local system time; when inside the window, no Pixoo/API polling is performed
  - on pause-window entry, a dedicated black holding screen is sent once: `Updates paused. Resume at XXXX`
  - pause-screen text is dark grey and rendered from a randomized top-left origin each time it is generated (anti burn-in)
  - while pause remains active, the app does not resend the pause screen every cycle
  - loop cadence remains unchanged (`DATA_REFRESH_SECONDS`)
- If Pixoo is offline, flight/weather API polling is paused until reconnect succeeds.
- Pixoo HTTP requests use a finite timeout (5s) to avoid indefinite hangs during device/network failures.
- Each render path resets stale frame buffers before drawing to prevent frame accumulation after failed renders.
- Debug render output is written before send to `debug/current_pixoo_render.gif` (single rolling file).
- `--test-flight` mode emits synthetic flight payloads using `A320` so aircraft mapping logic is exercised.
- Weather refresh logs include both raw provider payloads (Open-Meteo + METAR) and normalized payload.
- Each API call logs immediate raw return data:
  - `Open-Meteo raw response: ...`
  - `METAR raw response (ICAO): ...`
- METAR raw string is logged on every weather refresh.
- FlightRadar selected-flight/details raw payload dumps are available at `DEBUG` level only (to avoid very large `INFO` logs).
- Log file retention: `logs/pixoo_radar.log` rolls daily at local midnight and keeps the most recent 7 days.
- Weather wind line format:
  - non-gusting: e.g. `NE 10Mph`
  - gusting: e.g. `NE 10/18`
  - variable direction: `VAR 10Mph`
  - unknown/missing direction: `- 10Mph`
- Weather summary top header format:
  - with METAR station+time: `IATA HHMM` local (example: `PFO 1330`)
  - fallback when IATA mapping is unavailable: `ICAO HHMM` local
  - fallback when local-time conversion is unavailable: `ICAO HHMMZ` from METAR
  - fallback when unavailable: `Weather`
- On runway weather view, if METAR provides variable wind sector (`dddVddd`), boundary ticks are highlighted in orange and intermediate sector ticks are highlighted in lighter blue.
- If wind direction is missing or variable-only (`VRB`), runway weather view is skipped for that cycle and only summary view is rendered.

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
- renderer golden snapshots (weather summary, runway diagram hash)
- stationary ground-flight filtering
- taxiing ground-flight filtering (runway-alignment gate for moving ground targets)
- aircraft display mapping + fallback behavior
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
