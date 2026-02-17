import logging
from time import monotonic, sleep

from pixoo_radar.models import RenderState
from pixoo_radar.render.flight_view import build_and_send_animation
from pixoo_radar.render.holding_view import build_and_send_holding_screen
from pixoo_radar.render.weather_view import build_and_send_weather_idle_screen

LOGGER = logging.getLogger("pixoo_radar")


class PixooRadarController:
    def __init__(
        self,
        settings,
        pixoo_service=None,
        flight_service=None,
        weather_service=None,
        sleep_fn=None,
        clock_fn=None,
    ):
        self.settings = settings

        if pixoo_service is None:
            from pixoo_radar.services.pixoo_client import PixooClient
            pixoo_service = PixooClient(settings)
        if flight_service is None:
            from pixoo_radar.services.flight_service import FlightService
            flight_service = FlightService(logo_dir=settings.logo_dir)
        if weather_service is None:
            from pixoo_radar.services.weather_service import WeatherService
            weather_service = WeatherService(
                latitude=settings.latitude,
                longitude=settings.longitude,
                refresh_seconds=settings.weather_refresh_seconds,
                metar_icao=settings.weather_metar_icao,
            )

        self.pixoo_service = pixoo_service
        self.flight_service = flight_service
        self.weather_service = weather_service
        self.pizzoo = None
        self.current_state = None
        self.current_flight_id = None
        self.current_flight_signature = None
        self.no_data_retry_seconds = settings.no_flight_retry_seconds
        self.sleep_fn = sleep_fn or sleep
        self.clock_fn = clock_fn or monotonic
        self.last_cycle_started_at = None

    @staticmethod
    def flight_render_signature(data: dict) -> tuple:
        return (
            data.get("icao24"),
            int(round(float(data.get("altitude") or 0))),
            int(round(float(data.get("ground_speed") or 0))),
            int(round(float(data.get("heading") or 0))),
            str(data.get("status") or ""),
        )

    def poll_flight(self):
        return self.flight_service.get_closest_flight(self.settings.latitude, self.settings.longitude)

    def resolve_target_state(self, cooldown_remaining: int, api_error: str | None):
        if cooldown_remaining > 0:
            return RenderState.RATE_LIMIT
        if api_error:
            return RenderState.API_ERROR
        if self.settings.idle_mode.lower() == "weather":
            return RenderState.IDLE_WEATHER
        return RenderState.IDLE_HOLDING

    def reset_tracking(self):
        self.current_state = None
        self.current_flight_id = None
        self.current_flight_signature = None
        self.no_data_retry_seconds = self.settings.no_flight_retry_seconds

    @staticmethod
    def _is_fatal_weather_error(exc: Exception) -> bool:
        msg = str(exc)
        return msg.startswith("Weather bootstrap failed:") or msg.startswith("Weather startup validation failed:")

    def reconnect(self, fail_fast: bool = False):
        self.pizzoo = self.pixoo_service.connect_with_retry(fail_fast=fail_fast)
        self.reset_tracking()

    def handle_state_transition(self, target_state):
        self.current_flight_id = None
        self.current_flight_signature = None
        if target_state == RenderState.IDLE_WEATHER:
            force_refresh = self.current_state == RenderState.FLIGHT_ACTIVE
            weather_snapshot, refreshed = self.weather_service.get_current_with_options(force_refresh=force_refresh)
            if refreshed:
                weather_error = self.weather_service.get_last_error()
                if weather_error:
                    LOGGER.warning("Weather refresh failed (%s); using cached/fallback weather data.", weather_error)
                else:
                    LOGGER.info("Weather updated from API (%s).", weather_snapshot.source or "unknown source")
            build_and_send_weather_idle_screen(self.pizzoo, self.settings, weather_snapshot.payload)
        elif target_state == RenderState.RATE_LIMIT:
            build_and_send_holding_screen(self.pizzoo, self.settings, status="RATE LIMIT")
        elif target_state == RenderState.API_ERROR:
            build_and_send_holding_screen(self.pizzoo, self.settings, status="API ERROR")
        else:
            build_and_send_holding_screen(self.pizzoo, self.settings, status="NO FLIGHTS")
        self.current_state = target_state

    def handle_same_state_tick(self, target_state):
        if target_state == RenderState.IDLE_WEATHER:
            weather_snapshot, refreshed = self.weather_service.get_current()
            if refreshed:
                weather_error = self.weather_service.get_last_error()
                if weather_error:
                    LOGGER.warning("Weather refresh failed (%s); using cached/fallback weather data.", weather_error)
                else:
                    LOGGER.info("Weather updated from API (%s).", weather_snapshot.source or "unknown source")
                build_and_send_weather_idle_screen(self.pizzoo, self.settings, weather_snapshot.payload)

    def run_once(self):
        LOGGER.info("Starting polling cycle.")
        self.last_cycle_started_at = self.clock_fn()
        if not self.pixoo_service.is_reachable():
            LOGGER.warning("Pixoo offline; pausing flight/weather API updates until reconnect succeeds.")
            self.reconnect()
            return

        LOGGER.info("Fetching closest flight data.")
        flight_snapshot = self.poll_flight()
        cooldown_remaining = self.flight_service.get_api_cooldown_remaining()
        api_error = self.flight_service.get_last_api_error()

        if flight_snapshot:
            self.no_data_retry_seconds = self.settings.no_flight_retry_seconds
            self.current_state = RenderState.FLIGHT_ACTIVE
            data = flight_snapshot.payload
            new_flight_id = data.get("icao24")
            new_signature = self.flight_render_signature(data)
            if new_flight_id == self.current_flight_id:
                if new_signature == self.current_flight_signature:
                    LOGGER.info("Still tracking %s; telemetry unchanged.", data.get("flight_number"))
                    self.sleep_fn(self.settings.data_refresh_seconds)
                    return
                LOGGER.info("Still tracking %s; telemetry changed, updating animation.", data.get("flight_number"))

                self.current_flight_id = new_flight_id
                self.current_flight_signature = new_signature
                LOGGER.info("New flight: %s (%s -> %s).", data.get("flight_number"), data.get("origin"), data.get("destination"))
                LOGGER.info("Flight raw payload: %s", data)
                try:
                    build_and_send_animation(self.pizzoo, self.settings, data)
                except Exception as exc:
                    LOGGER.error("Lost Pixoo connection while rendering flight view (%s).", exc)
                    self.reconnect()
                    return
            LOGGER.info("Animation playing. Next check in %ss.", self.settings.data_refresh_seconds)
            self.sleep_fn(self.settings.data_refresh_seconds)
            return

        retry_seconds = max(self.no_data_retry_seconds, cooldown_remaining)
        target_state = self.resolve_target_state(cooldown_remaining, api_error)
        if target_state != self.current_state:
            LOGGER.info("State transition: %s -> %s", self.current_state, target_state)
            try:
                self.handle_state_transition(target_state)
            except Exception as exc:
                if self._is_fatal_weather_error(exc):
                    LOGGER.error("Fatal weather error: %s", exc)
                    raise
                LOGGER.error("Lost Pixoo connection while rendering idle view (%s).", exc)
                self.reconnect()
                return
        else:
            try:
                self.handle_same_state_tick(target_state)
            except Exception as exc:
                if self._is_fatal_weather_error(exc):
                    LOGGER.error("Fatal weather error: %s", exc)
                    raise
                LOGGER.error("Lost Pixoo connection while rendering weather view (%s).", exc)
                self.reconnect()
                return

        if target_state == RenderState.RATE_LIMIT:
            if cooldown_remaining > 0:
                LOGGER.warning("FlightRadar24 rate limit active, retrying in %ss.", retry_seconds)
        elif target_state == RenderState.API_ERROR:
            LOGGER.warning("Flight API error, retrying in %ss.", retry_seconds)
        else:
            LOGGER.info("No flight data available, retrying in %ss.", retry_seconds)

        self.sleep_fn(retry_seconds)
        self.no_data_retry_seconds = min(
            self.no_data_retry_seconds * 2,
            self.settings.no_flight_max_retry_seconds,
        )

    def run(self):
        self.reconnect(fail_fast=True)
        while True:
            self.run_once()
