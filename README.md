# Pixoo Radar

Pixoo64 display app with two operating modes:

- `Flight mode`: shows the closest flight from FlightRadar24 data.
- `Idle mode`: shows weather views (including runway/wind diagram) or a holding screen when no flights are available.

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
- Polling/backoff: `DATA_REFRESH_SECONDS`, `NO_FLIGHT_RETRY_SECONDS`, `NO_FLIGHT_MAX_RETRY_SECONDS`, `API_RATE_LIMIT_COOLDOWN_SECONDS`
- Idle weather: `IDLE_MODE`, `WEATHER_REFRESH_SECONDS`, `WEATHER_VIEW_SECONDS`, `RUNWAY_HEADING_DEG`
- Units: `FLIGHT_SPEED_UNIT` (`mph` or `kt`), `WEATHER_WIND_SPEED_UNIT` (`mph` or `kmh`; legacy `kph` accepted)
- Fonts: `FONT_NAME`, `FONT_PATH`, optional `RUNWAY_LABEL_FONT_NAME`, `RUNWAY_LABEL_FONT_PATH`
- Logging: `LOG_LEVEL`, `LOG_VERBOSE_EVENTS`
- Startup validates config values and file paths and exits with clear errors if invalid.

## Runtime Behavior

State machine values:

- `flight_active`
- `idle_weather`
- `idle_holding`
- `rate_limit`
- `api_error`

Operational behavior:

- Flight view is re-rendered when tracked flight telemetry changes (altitude, speed, heading, status).
- Stationary ground targets are filtered out (`altitude<=0` and `ground_speed<=0`).
- No-flight retries use exponential backoff up to `NO_FLIGHT_MAX_RETRY_SECONDS`.
- If Pixoo is offline, flight/weather API polling is paused until reconnect succeeds.
- Weather refresh logs include both raw and normalized payloads.

## Refactored Architecture

- `display_flight_data_pizoo.py`: bootstrap entrypoint
- `pixoo_radar/settings.py`: typed `AppSettings` loaded from `config.py`
- `pixoo_radar/models.py`: `FlightSnapshot`, `WeatherSnapshot`, `RenderState`
- `pixoo_radar/controller.py`: polling loop, transitions, retry handling
- `pixoo_radar/flight/provider.py`: FlightRadar24 provider adapter
- `pixoo_radar/flight/filters.py`: candidate filtering and closest-flight selection
- `pixoo_radar/flight/mapping.py`: payload mapping helpers
- `pixoo_radar/flight/metar.py`: METAR fetch utility
- `pixoo_radar/flight/logos.py`: logo cache/resize handling
- `pixoo_radar/services/pixoo_client.py`: Pixoo connect/reconnect/reachability/font loading
- `pixoo_radar/services/flight_service.py`: flight service wrapper
- `pixoo_radar/services/weather_service.py`: weather service wrapper
- `pixoo_radar/render/flight_view.py`: flight animation
- `pixoo_radar/render/weather_view.py`: weather summary + runway/wind diagram
- `pixoo_radar/render/holding_view.py`: holding/rate-limit/API-error views
- `flight_data.py`: FlightRadar/API integration, logo handling, METAR
- `weather_data.py`: Open-Meteo provider and cache

## Development Checks

```bash
.venv/bin/python -m py_compile \
  display_flight_data_pizoo.py flight_data.py weather_data.py \
  pixoo_radar/settings.py pixoo_radar/models.py pixoo_radar/controller.py \
  pixoo_radar/flight/provider.py pixoo_radar/flight/filters.py \
  pixoo_radar/flight/mapping.py pixoo_radar/flight/metar.py \
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
- weather cache and force-refresh behavior
- settings validation (units, ranges, timings, font paths)
- Pixoo runway-label font diagnostic error messaging

## CI Gates

GitHub Actions runs on every push/PR:

- `py_compile` on all tracked Python files
- `ruff check .`
- `mypy`
- `pytest -q`
