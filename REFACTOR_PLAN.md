# Pixoo Radar Refactor Plan (Codex-Executable)

This document is an execution runbook for a separate Codex instance to perform a substantial refactor safely.

## Objectives
- Improve maintainability by splitting orchestration, rendering, and data/integration concerns.
- Preserve existing runtime behavior (display states, retry rules, reconnect behavior, unit formatting).
- Add a minimal automated safety net for future changes.

## Non-Goals
- No UI redesign during refactor.
- No change to external config semantics unless explicitly listed.
- No behavior changes to polling/backoff/retry logic unless covered by tests and noted in commit message.

## Current Pain Points
- `display_flight_data_pizoo.py` mixes CLI, state machine, geometry, rendering, device I/O, and retry policy.
- Reconnect and error branches are repeated in `main()`.
- `flight_data.py` combines API fetch, filtering, logo processing, and METAR enrichment.
- `weather_data.py` uses loose dict payloads and bundles provider + cache + normalization.

## Guardrails
- Work on branch: `refactor-phase1` (or new branch from it).
- Keep commits small and scoped (one phase = one commit minimum).
- After every phase run:
  - `.venv/bin/python -m py_compile display_flight_data_pizoo.py flight_data.py weather_data.py`
  - if tests exist: `.venv/bin/python -m pytest -q`
- Do not remove existing logging behavior unless replaced with equivalent or better logs.

## Target Structure (Incremental)
Create package modules while keeping `display_flight_data_pizoo.py` as entrypoint wrapper:

```
pixoo_radar/
  __init__.py
  settings.py
  models.py
  controller.py
  services/
    __init__.py
    pixoo_client.py
    flight_service.py
    weather_service.py
  render/
    __init__.py
    common.py
    flight_view.py
    weather_view.py
    holding_view.py
tests/
  test_state_machine.py
  test_runway_geometry.py
  test_flight_filtering.py
  test_weather_cache.py
```

## Phase Plan

### Phase 0: Baseline Freeze
- Capture current behavior assumptions in `tests/` TODO notes or markdown checklist.
- Add a smoke command that imports modules and runs formatting helpers without Pixoo hardware.
- Commit message: `chore: baseline behavior notes before refactor`

Acceptance:
- Repo imports cleanly.
- No runtime behavior changes.

### Phase 1: Settings + Models Extraction
- Add `pixoo_radar/settings.py` with `AppSettings` dataclass loaded from current `config` module.
- Add `pixoo_radar/models.py` with typed snapshots:
  - `FlightSnapshot`
  - `WeatherSnapshot`
  - `RenderState` enum/string constants.
- Keep existing dict interfaces at boundaries; add adapters to/from dataclasses.

Acceptance:
- Entrypoint still runs unchanged.
- Config names in `config.py` remain valid.

### Phase 2: Service Layer Extraction
- Create:
  - `services/pixoo_client.py` (connect, load fonts, render wrappers, reachability checks)
  - `services/flight_service.py` (wrap existing `FlightData` behavior)
  - `services/weather_service.py` (wrap existing `WeatherData` behavior)
- Keep old modules as implementation dependencies initially.

Acceptance:
- `main` (or controller) uses service interfaces, not raw provider calls.
- Reconnect behavior unchanged.

### Phase 3: Renderer Split
- Move draw helpers into:
  - `render/common.py` (line drawing, geometry, text width/centering)
  - `render/flight_view.py`
  - `render/weather_view.py` (summary + runway diagram)
  - `render/holding_view.py`
- Keep pixel output behavior equivalent (same constants, same coordinates unless unavoidable).

Acceptance:
- All previous display states still render.
- Weather runway diagram still includes active runway arrow + designator logic.

### Phase 4: Controller State Machine
- Move loop logic from `main()` into `controller.py` with explicit methods:
  - `poll_flight()`
  - `resolve_target_state()`
  - `handle_state_transition()`
  - `handle_same_state_tick()`
- Centralize duplicated reconnect/error handling into shared helper(s).

Acceptance:
- State transitions preserved:
  - `flight_active`
  - `idle_weather`
  - `idle_holding`
  - `rate_limit`
  - `api_error`
- No regression in no-flight exponential backoff.

### Phase 5: Tests (High-Value Only)
- Add tests for:
  - state transition selection logic
  - runway active-heading + label placement scoring functions
  - flight filter exclusion for stationary ground targets
  - weather refresh/cache behavior (force refresh vs cached path)
- Use pure-function extraction where needed to make logic testable.

Acceptance:
- Tests run in CI/local without Pixoo hardware.

### Phase 6: Entrypoint Slimming + Docs
- Keep `display_flight_data_pizoo.py` as minimal bootstrap:
  - configure logging
  - load settings
  - instantiate controller
  - run loop
- Update `README.md` and `AGENTS.md` with new module map and test commands.

Acceptance:
- Entrypoint <= ~120 lines.
- Docs reflect actual architecture.

## Suggested Commit Sequence
1. `chore: capture baseline behavior for refactor`
2. `refactor: introduce typed settings and snapshot models`
3. `refactor: extract pixoo flight and weather service interfaces`
4. `refactor: split renderers into dedicated modules`
5. `refactor: move main loop into controller state machine`
6. `test: add state geometry filter and weather cache coverage`
7. `docs: update README and AGENTS for refactored architecture`

## Rollback Strategy
- If any phase regresses behavior, revert only that phase commit.
- Keep each phase independently releasable.
- Avoid long-lived uncommitted changes.

## Definition of Done
- Behavior parity for current features.
- Reduced complexity in entrypoint and `main` loop.
- Core logic test coverage for transitions/geometry/filter/cache.
- Updated docs aligned with code structure.
