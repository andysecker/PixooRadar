# Pixoo Radar

A state-driven Pixoo64 display that renders nearby-flight data when available and weather/holding views when idle.

## Run

```bash
python display_flight_data_pizoo.py
python display_flight_data_pizoo.py --caffeinate
```

## Refactored Architecture

- `display_flight_data_pizoo.py`: slim bootstrap (logging, args, controller startup)
- `pixoo_radar/settings.py`: typed `AppSettings` loaded from `config.py`
- `pixoo_radar/models.py`: typed snapshots (`FlightSnapshot`, `WeatherSnapshot`) + `RenderState`
- `pixoo_radar/controller.py`: state machine and polling/retry orchestration
- `pixoo_radar/services/pixoo_client.py`: Pixoo connect/reconnect/reachability
- `pixoo_radar/services/flight_service.py`: `FlightData` wrapper
- `pixoo_radar/services/weather_service.py`: `WeatherData` wrapper
- `pixoo_radar/render/flight_view.py`: flight animation rendering
- `pixoo_radar/render/weather_view.py`: weather summary + runway/wind rendering
- `pixoo_radar/render/holding_view.py`: no-flight/rate-limit/api-error holding views
- `flight_data.py`: flight API fetch/filter/logo/METAR implementation dependency
- `weather_data.py`: weather provider + cache implementation dependency

## Tests and checks

```bash
.venv/bin/python -m py_compile display_flight_data_pizoo.py flight_data.py weather_data.py
.venv/bin/python -m pytest -q
```

Added targeted tests:
- state transition resolution
- runway active-heading + label placement utilities
- stationary ground-flight filtering
- weather cache/force-refresh behavior
