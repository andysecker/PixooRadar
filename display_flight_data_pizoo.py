"""
Pixoo Flight Tracker Display

Displays real-time flight information on a Pixoo64 LED display in a
flight-strip style layout inspired by ATC radar displays.

Uses pre-buffered animation: all frames are computed upfront and sent
to the device at once. The Pixoo loops the animation natively for
smooth playback without continuous network traffic.

The lower half emulates an airport departure board, cycling through
flight details one at a time with centered text — no overlap possible.

Usage:
    python display_flight_data_pizoo.py
    python display_flight_data_pizoo.py --caffeinate   # prevent macOS sleep

Configuration:
    Edit config.py to set your Pixoo IP address, location coordinates, and display preferences.
"""

import argparse
import logging
import os
import socket
import subprocess
import sys
from math import cos, radians, sin
from time import sleep

from PIL import Image
from pizzoo import Pizzoo

from config import (
    ANIMATION_FRAME_SPEED,
    COLOR_BOX,
    COLOR_TEXT,
    DATA_REFRESH_SECONDS,
    FLIGHT_SEARCH_RADIUS_METERS,
    FLIGHT_SPEED_UNIT,
    FONT_NAME,
    FONT_PATH,
    LATITUDE,
    LOG_LEVEL,
    LOG_VERBOSE_EVENTS,
    LOGO_DIR,
    LONGITUDE,
    IDLE_MODE,
    NO_FLIGHT_MAX_RETRY_SECONDS,
    NO_FLIGHT_RETRY_SECONDS,
    PIXOO_IP,
    PIXOO_PORT,
    PIXOO_RECONNECT_SECONDS,
    RUNWAY_HEADING_DEG,
    WEATHER_REFRESH_SECONDS,
    WEATHER_VIEW_SECONDS,
    WEATHER_WIND_SPEED_UNIT,
)
from flight_data import FlightData
from weather_data import WeatherData

# Aviation-style colors
COLOR_ROUTE_LINE = "#666666"      # Dim gray for route line
COLOR_PLANE = "#FFFFFF"           # White for airplane icon
COLOR_SEPARATOR = "#555555"       # Separator lines
COLOR_LABEL = "#999999"           # Muted gray for info labels
COLOR_WX_BG = "#10243F"           # Weather mode background
COLOR_WX_ACCENT = "#2F6EA4"       # Weather accent
COLOR_WX_TEXT = "#EAF6FF"         # Weather primary text
COLOR_WX_MUTED = "#A8C7DE"        # Weather muted text
COLOR_RWY = "#111111"             # Runway asphalt
COLOR_RWY_MARK = "#EDEDED"        # Runway markings
COLOR_WIND_ARROW = "#FFD166"      # Wind arrow (high-contrast amber)

# Airplane animation constants
PLANE_WIDTH = 5
ROUTE_START = 21
ROUTE_END = 43
ROUTE_WIDTH = ROUTE_END - ROUTE_START
AIRPLANE_CYCLE = ROUTE_WIDTH + PLANE_WIDTH  # 27 frames per airplane loop

# Total frames = 1 airplane cycle (27 frames). Device is unreliable above ~40 frames
# since each frame is a separate HTTP request. Info pages: 27 / 3 = 9 frames per page.
# At 400ms per frame: ~3.6s per page, ~10.8s full cycle.
TOTAL_FRAMES = AIRPLANE_CYCLE  # 27


STATE_FLIGHT_ACTIVE = "flight_active"
STATE_IDLE_WEATHER = "idle_weather"
STATE_IDLE_HOLDING = "idle_holding"
STATE_RATE_LIMIT = "rate_limit"
STATE_API_ERROR = "api_error"
LOGGER = logging.getLogger("pixoo_radar")


def _configure_logging() -> None:
    """Configure app logging with standard Python logging."""
    level_name = str(LOG_LEVEL).upper()
    level = getattr(logging, level_name, logging.INFO)
    if not LOG_VERBOSE_EVENTS and level < logging.WARNING:
        level = logging.WARNING

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _measure_text_width(text: str) -> int:
    """Estimate text width in pixels (5px char + 1px spacing)."""
    return max(1, len(str(text)) * 6 - 1)


def _center_x(rect_width: int, text: str) -> int:
    """Calculate x-coordinate to center text within a given width."""
    text_width = _measure_text_width(text)
    return max(0, (rect_width - text_width) // 2)


def _draw_airplane_icon(pizzoo: Pizzoo, x: int, y: int, clip_left: int = 0,
                       clip_right: int = 64, color: str = COLOR_PLANE) -> None:
    """
    Draw a small 5x5 airplane icon pointing right with clipping support.

    The icon looks like:
       #
      ###
     #####
      ###
       #
    """
    # Fuselage (horizontal line) - x to x+4, y+2
    for px in range(x, x + 5):
        if clip_left <= px < clip_right:
            pizzoo.draw_rectangle(xy=(px, y + 2), width=1, height=1, color=color, filled=True)

    # Wings (vertical line in middle) - x+2, y to y+4
    if clip_left <= x + 2 < clip_right:
        pizzoo.draw_rectangle(xy=(x + 2, y), width=1, height=5, color=color, filled=True)

    # Tail (small vertical at back) - x, y+1 to y+3
    if clip_left <= x < clip_right:
        pizzoo.draw_rectangle(xy=(x, y + 1), width=1, height=3, color=color, filled=True)


def _draw_top_section(pizzoo: Pizzoo, logo: str, origin: str, destination: str,
                      airline_name: str = "", y_route: int = 20) -> None:
    """Draw the top section: airline logo and route display (y=0-33)."""
    # === AIRLINE LOGO (y=0-19) ===
    if logo:
        pizzoo.draw_image(logo, xy=(0, 0), size=(64, 20), resample_method=Image.LANCZOS)
    elif airline_name:
        name = airline_name[:10]
        pizzoo.draw_text(name, xy=(_center_x(64, name), 7), font=FONT_NAME, color="#FFFFFF")

    # === SEPARATOR after logo ===
    _draw_separator_line(pizzoo, y=20, style="dashed")

    # === ROUTE DISPLAY background (y=21-31) ===
    pizzoo.draw_rectangle(xy=(0, 21), width=64, height=11, color=COLOR_BOX, filled=True)

    # Origin and destination text
    pizzoo.draw_text(origin, xy=(2, y_route), font=FONT_NAME, color=COLOR_TEXT)
    dest_width = _measure_text_width(destination)
    pizzoo.draw_text(destination, xy=(62 - dest_width, y_route), font=FONT_NAME, color=COLOR_TEXT)

    # Route line (dashed)
    for i in range(ROUTE_START, ROUTE_END, 3):
        pizzoo.draw_rectangle(xy=(i, y_route + 6), width=2, height=1, color=COLOR_ROUTE_LINE, filled=True)


def _draw_label_value(pizzoo: Pizzoo, label: str, value: str, y: int) -> None:
    """Draw a label in muted gray and value in yellow, centered as a unit."""
    full_text = f"{label} {value}"
    x_start = _center_x(64, full_text)
    pizzoo.draw_text(label, xy=(x_start, y), font=FONT_NAME, color=COLOR_LABEL)
    value_x = x_start + (len(label) + 1) * 6  # label chars + space, each 6px wide
    pizzoo.draw_text(value, xy=(value_x, y), font=FONT_NAME, color=COLOR_TEXT)


def _draw_info_page(pizzoo: Pizzoo, upper_pair: tuple, lower_pair: tuple) -> None:
    """
    Draw a departure board info page in the lower section (y=33-63).

    Each pair is (label, value) drawn with label in muted gray and value in yellow,
    like an airport split-flap display (e.g., ("FLT", "FR2263") / ("ALT", "FL034")).
    """
    # Background
    pizzoo.draw_rectangle(xy=(0, 33), width=64, height=31, color=COLOR_BOX, filled=True)

    # Separator between route and info area
    _draw_separator_line(pizzoo, y=32, style="dashed")

    # Upper row (centered)
    _draw_label_value(pizzoo, upper_pair[0], upper_pair[1], y=34)

    # Separator between rows
    _draw_separator_line(pizzoo, y=48, style="dashed")

    # Lower row (centered)
    _draw_label_value(pizzoo, lower_pair[0], lower_pair[1], y=50)


def _draw_separator_line(pizzoo: Pizzoo, y: int, style: str = "solid") -> None:
    """Draw a horizontal separator line across the display."""
    if style == "solid":
        pizzoo.draw_rectangle(xy=(0, y), width=64, height=1, color=COLOR_SEPARATOR, filled=True)
    elif style == "dashed":
        for x in range(0, 64, 4):
            pizzoo.draw_rectangle(xy=(x, y), width=2, height=1, color=COLOR_SEPARATOR, filled=True)


def _format_flight_level(altitude_ft: int) -> str:
    """Convert altitude in feet to flight level format (e.g., FL350)."""
    if altitude_ft is None or altitude_ft < 1000:
        return "GND"
    fl = altitude_ft // 100
    return f"FL{fl:03d}"


def _format_speed(speed_kts: int) -> str:
    """Format ground speed using configured unit."""
    if speed_kts is None:
        return "---Mph" if FLIGHT_SPEED_UNIT.lower() == "mph" else "---Kt"
    if FLIGHT_SPEED_UNIT.lower() == "mph":
        speed_mph = int(round(float(speed_kts) * 1.15078))
        return f"{speed_mph}Mph"
    return f"{int(round(float(speed_kts)))}Kt"


def _format_heading(heading: int) -> str:
    """Format heading as 3-digit degrees."""
    if heading is None:
        return "---"
    return f"{heading:03d}"


def _format_temp_c(temperature_c) -> str:
    if temperature_c is None:
        return "--C"
    return f"{int(round(temperature_c))}C"


def _format_humidity(humidity_pct) -> str:
    if humidity_pct is None:
        return "--%"
    return f"{int(round(humidity_pct))}%"


def _format_wind_kph(wind_kph) -> str:
    wind_unit = WEATHER_WIND_SPEED_UNIT.lower()
    use_mph = wind_unit == "mph"
    # Keep backward compatibility for older 'kph' config values.
    use_kmh = wind_unit in ("kmh", "kph")

    if wind_kph is None:
        return "-- Mph" if use_mph else "-- Kmh"
    if use_mph:
        wind_mph = int(round(float(wind_kph) * 0.621371))
        return f"{wind_mph} Mph"
    if use_kmh:
        return f"{int(round(float(wind_kph)))} Kmh"
    return f"{int(round(float(wind_kph)))} Kmh"


def _format_wind_dir(wind_dir_deg) -> str:
    if wind_dir_deg is None:
        return "--"
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int((float(wind_dir_deg) + 22.5) // 45) % 8
    return directions[idx]


def _fit_text(text: str, max_chars: int = 10) -> str:
    """Clamp text length so lines starting at x=2 always fit 64px width."""
    return str(text)[:max_chars]


def _signed_angle_diff_deg(angle_a: float, angle_b: float) -> float:
    """Return signed shortest-angle difference (a-b) in range [-180, 180)."""
    return ((angle_a - angle_b + 180.0) % 360.0) - 180.0


def _runway_designator(heading_deg: float) -> str:
    """Convert heading to runway designator (e.g. 110 -> '11')."""
    runway = int(round(float(heading_deg) / 10.0)) % 36
    if runway == 0:
        runway = 36
    return f"{runway:02d}"


def _bearing_to_xy(cx: int, cy: int, bearing_deg: float, distance: float):
    rad = radians(float(bearing_deg) % 360.0)
    x = int(round(cx + distance * sin(rad)))
    y = int(round(cy - distance * cos(rad)))
    return x, y


def _draw_px(pizzoo: Pizzoo, x: int, y: int, color: str) -> None:
    if 0 <= x < 64 and 0 <= y < 64:
        pizzoo.draw_rectangle(xy=(x, y), width=1, height=1, color=color, filled=True)


def _draw_line(pizzoo: Pizzoo, x0: int, y0: int, x1: int, y1: int, color: str, thickness: int = 1) -> None:
    """Draw a clipped integer line using a small Bresenham variant."""
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    radius = max(0, (thickness - 1) // 2)

    while True:
        for ox in range(-radius, radius + 1):
            for oy in range(-radius, radius + 1):
                _draw_px(pizzoo, x0 + ox, y0 + oy, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def _draw_runway_wind_diagram(pizzoo: Pizzoo, wind_dir_deg, runway_heading_deg: float) -> None:
    """Diagram-only runway/wind frame (no text)."""
    cx, cy = 32, 32
    runway_half_len = 22

    pizzoo.draw_rectangle(xy=(0, 0), width=64, height=64, color=COLOR_WX_BG, filled=True)

    # Subtle compass ring
    for b in range(0, 360, 10):
        if b == 0:
            continue
        x1, y1 = _bearing_to_xy(cx, cy, b, 28)
        x2, y2 = _bearing_to_xy(cx, cy, b, 30)
        _draw_line(pizzoo, x1, y1, x2, y2, color=COLOR_WX_ACCENT, thickness=1)
    pizzoo.draw_text("N", xy=(_center_x(64, "N"), -1), font=FONT_NAME, color=COLOR_WX_MUTED)

    # Runway body
    rx0, ry0 = _bearing_to_xy(cx, cy, runway_heading_deg, runway_half_len)
    rx1, ry1 = _bearing_to_xy(cx, cy, (runway_heading_deg + 180) % 360, runway_half_len)
    _draw_line(pizzoo, rx0, ry0, rx1, ry1, color=COLOR_RWY, thickness=7)
    _draw_line(pizzoo, rx0, ry0, rx1, ry1, color=COLOR_RWY_MARK, thickness=1)

    # Wind arrow: meteorological direction means "from", so arrow points toward center.
    if wind_dir_deg is not None:
        wind_from = float(wind_dir_deg) % 360.0
        shaft_bearing = (wind_from + 180.0) % 360.0

        ax0, ay0 = _bearing_to_xy(cx, cy, wind_from, 24)
        ax1, ay1 = _bearing_to_xy(cx, cy, wind_from, 10)
        _draw_line(pizzoo, ax0, ay0, ax1, ay1, color=COLOR_WIND_ARROW, thickness=2)

        # Arrow head near center
        left = (shaft_bearing + 150.0) % 360.0
        right = (shaft_bearing - 150.0) % 360.0
        hx0, hy0 = _bearing_to_xy(ax1, ay1, left, 4)
        hx1, hy1 = _bearing_to_xy(ax1, ay1, right, 4)
        _draw_line(pizzoo, ax1, ay1, hx0, hy0, color=COLOR_WIND_ARROW, thickness=1)
        _draw_line(pizzoo, ax1, ay1, hx1, hy1, color=COLOR_WIND_ARROW, thickness=1)


def _build_and_send_animation(pizzoo: Pizzoo, data: dict) -> None:
    """Pre-compute all animation frames and send them to the device.

    Builds TOTAL_FRAMES frames combining:
    - Smooth airplane animation (loops every AIRPLANE_CYCLE frames)
    - Departure board info cycling (one page per info item)
    """
    logo = data.get("airline_logo_path", "")
    airline_name = str(data.get("airline", "") or "")
    origin = str(data.get("origin", "---"))[:3]
    destination = str(data.get("destination", "---"))[:3]
    flight_num = str(data.get("flight_number", "----"))[:7]
    aircraft = str(data.get("aircraft_type_icao", "----"))[:4]
    registration = str(data.get("registration", "------"))[:7]
    altitude = data.get("altitude", 0) or 0
    speed = data.get("ground_speed", 0) or 0
    heading = data.get("heading")

    # Departure board pages: ((upper_label, upper_value), (lower_label, lower_value))
    # Two rows cycling together — 3 pages shown for ~3.6s each
    info_pages = [
        (("FLT", flight_num), ("ALT", _format_flight_level(altitude))),
        (("TYPE", aircraft), ("REG", registration)),
        (("SPD", _format_speed(speed)), ("HDG", _format_heading(heading))),
    ]

    frames_per_page = TOTAL_FRAMES // len(info_pages)
    y_route = 20

    # Frame 0 is created automatically by pizzoo
    for frame_idx in range(TOTAL_FRAMES):
        pizzoo.cls()

        # Top section: logo + route + animated airplane
        _draw_top_section(pizzoo, logo, origin, destination, airline_name, y_route)

        plane_x = ROUTE_START - PLANE_WIDTH + (frame_idx % AIRPLANE_CYCLE)
        _draw_airplane_icon(pizzoo, plane_x, y_route + 4,
                           clip_left=ROUTE_START, clip_right=ROUTE_END, color=COLOR_PLANE)

        # Bottom section: departure board with two info rows
        page_idx = min(frame_idx // frames_per_page, len(info_pages) - 1)
        upper_pair, lower_pair = info_pages[page_idx]
        _draw_info_page(pizzoo, upper_pair, lower_pair)

        if frame_idx < TOTAL_FRAMES - 1:
            pizzoo.add_frame()

    LOGGER.info("Sending %s flight frames to device (frame speed: %sms).", TOTAL_FRAMES, ANIMATION_FRAME_SPEED)
    pizzoo.render(frame_speed=ANIMATION_FRAME_SPEED)


def _build_and_send_holding_screen(pizzoo: Pizzoo, status: str = "NO FLIGHTS") -> None:
    """Render a static holding screen when no active flight should be shown."""
    radius_km = max(1, int(round(FLIGHT_SEARCH_RADIUS_METERS / 1000)))
    range_text = f"{radius_km}KM"

    pizzoo.cls()
    _draw_top_section(pizzoo, logo="", origin="---", destination="---", airline_name=status, y_route=20)
    _draw_info_page(pizzoo, ("STATUS", status[:10]), ("RANGE", range_text))
    LOGGER.info("Sending holding screen (%s).", status)
    pizzoo.render(frame_speed=ANIMATION_FRAME_SPEED)


def _build_and_send_weather_idle_screen(pizzoo: Pizzoo, weather: dict) -> None:
    """Render weather-focused idle view with a distinct visual style."""
    condition = _fit_text(str(weather.get("condition") or "NO DATA").upper(), 10)
    temperature = _format_temp_c(weather.get("temperature_c"))
    humidity = _format_humidity(weather.get("humidity_pct"))
    wind = _format_wind_kph(weather.get("wind_kph"))
    wind_dir = _format_wind_dir(weather.get("wind_dir_deg"))
    wind_dir_deg = weather.get("wind_dir_deg")

    # Frame 1: weather summary (single-column, evenly spaced)
    pizzoo.cls()
    pizzoo.draw_rectangle(xy=(0, 0), width=64, height=64, color=COLOR_WX_BG, filled=True)
    pizzoo.draw_rectangle(xy=(0, 0), width=64, height=11, color=COLOR_WX_ACCENT, filled=True)
    pizzoo.draw_text("Weather", xy=(2, -1), font=FONT_NAME, color=COLOR_WX_TEXT)
    hum_line = _fit_text(f"HUM {humidity}", 10)
    wind_compact = wind.replace(" ", "")
    wind_line = _fit_text(f"{wind_dir} {wind_compact}", 10)
    pizzoo.draw_text(temperature, xy=(_center_x(64, temperature), 13), font=FONT_NAME, color=COLOR_WX_TEXT)
    pizzoo.draw_text(condition, xy=(_center_x(64, condition), 25), font=FONT_NAME, color=COLOR_WX_MUTED)
    pizzoo.draw_text(hum_line, xy=(_center_x(64, hum_line), 37), font=FONT_NAME, color=COLOR_WX_TEXT)
    pizzoo.draw_text(wind_line, xy=(_center_x(64, wind_line), 49), font=FONT_NAME, color=COLOR_WX_TEXT)

    # Frame 2: diagram-only runway + wind arrow
    runway_heading_deg = float(RUNWAY_HEADING_DEG)
    pizzoo.add_frame()
    _draw_runway_wind_diagram(pizzoo, wind_dir_deg=wind_dir_deg, runway_heading_deg=runway_heading_deg)
    LOGGER.info("Sending weather idle screen (2 frames, %ss per frame).", WEATHER_VIEW_SECONDS)
    pizzoo.render(frame_speed=max(500, int(WEATHER_VIEW_SECONDS * 1000)))


def _connect_pixoo_with_retry() -> Pizzoo:
    """Connect to Pixoo and keep retrying until available."""
    while True:
        try:
            LOGGER.info("Connecting to Pixoo at %s:%s...", PIXOO_IP, PIXOO_PORT)
            pixoo = Pizzoo(PIXOO_IP, debug=True)
            pixoo.load_font(FONT_NAME, FONT_PATH)
            LOGGER.info("Pixoo connected.")
            return pixoo
        except Exception as exc:
            LOGGER.warning("Pixoo unavailable (%s). Retrying in %ss...", exc, PIXOO_RECONNECT_SECONDS)
            sleep(PIXOO_RECONNECT_SECONDS)


def _is_pixoo_reachable(timeout_seconds: float = 2.0) -> bool:
    """Return True when Pixoo host:port is reachable over TCP."""
    try:
        with socket.create_connection((PIXOO_IP, PIXOO_PORT), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def main():
    """Main function to run the flight tracker display."""
    _configure_logging()
    LOGGER.info("Starting Pixoo Radar.")
    parser = argparse.ArgumentParser(description="Pixoo Flight Tracker Display")
    parser.add_argument("--caffeinate", action="store_true",
                        help="Prevent macOS from sleeping while the tracker runs")
    args = parser.parse_args()

    if args.caffeinate:
        sys.exit(subprocess.call(
            ["caffeinate", "-i", sys.executable, os.path.abspath(__file__)]
        ))

    pizzoo = _connect_pixoo_with_retry()
    fd = FlightData(save_logo_dir=LOGO_DIR)
    wx = WeatherData(latitude=LATITUDE, longitude=LONGITUDE, refresh_seconds=WEATHER_REFRESH_SECONDS)

    current_state = None
    current_flight_id = None
    no_data_retry_seconds = NO_FLIGHT_RETRY_SECONDS

    while True:
        LOGGER.info("Starting polling cycle.")
        if not _is_pixoo_reachable():
            LOGGER.warning("Pixoo offline; pausing flight/weather API updates until reconnect succeeds.")
            pixoo = _connect_pixoo_with_retry()
            current_state = None
            current_flight_id = None
            no_data_retry_seconds = NO_FLIGHT_RETRY_SECONDS
            continue

        LOGGER.info("Fetching closest flight data.")
        data = fd.get_closest_flight_data(LATITUDE, LONGITUDE)
        cooldown_remaining = fd.get_api_cooldown_remaining()
        api_error = fd.get_last_api_error()

        if data:
            no_data_retry_seconds = NO_FLIGHT_RETRY_SECONDS
            current_state = STATE_FLIGHT_ACTIVE
            new_flight_id = data.get("icao24")
            if new_flight_id == current_flight_id:
                LOGGER.info("Still tracking %s; animation unchanged.", data.get("flight_number"))
                sleep(DATA_REFRESH_SECONDS)
                continue

            current_flight_id = new_flight_id
            LOGGER.info("New flight: %s (%s -> %s).", data.get("flight_number"), data.get("origin"), data.get("destination"))
            try:
                _build_and_send_animation(pizzoo, data)
            except Exception as exc:
                LOGGER.error("Lost Pixoo connection while rendering flight view (%s).", exc)
                pizzoo = _connect_pixoo_with_retry()
                current_state = None
                current_flight_id = None
                continue
            LOGGER.info("Animation playing. Next check in %ss.", DATA_REFRESH_SECONDS)
            sleep(DATA_REFRESH_SECONDS)
            continue

        retry_seconds = max(no_data_retry_seconds, cooldown_remaining)
        if cooldown_remaining > 0:
            target_state = STATE_RATE_LIMIT
        elif api_error:
            target_state = STATE_API_ERROR
        elif IDLE_MODE.lower() == "weather":
            target_state = STATE_IDLE_WEATHER
        else:
            target_state = STATE_IDLE_HOLDING
        if target_state != current_state:
            LOGGER.info("State transition: %s -> %s", current_state, target_state)

        if target_state != current_state:
            current_flight_id = None
            if target_state == STATE_IDLE_WEATHER:
                force_refresh = current_state == STATE_FLIGHT_ACTIVE
                weather_payload, refreshed = wx.get_current_with_options(force_refresh=force_refresh)
                if refreshed:
                    weather_error = wx.get_last_error()
                    if weather_error:
                        LOGGER.warning("Weather refresh failed (%s); using cached/fallback weather data.", weather_error)
                    else:
                        LOGGER.info("Weather updated from API (%s).", weather_payload.get("source", "unknown source"))
                try:
                    _build_and_send_weather_idle_screen(pizzoo, weather_payload)
                except Exception as exc:
                    LOGGER.error("Lost Pixoo connection while rendering weather view (%s).", exc)
                    pizzoo = _connect_pixoo_with_retry()
                    current_state = None
                    current_flight_id = None
                    continue
            elif target_state == STATE_RATE_LIMIT:
                try:
                    _build_and_send_holding_screen(pizzoo, status="RATE LIMIT")
                except Exception as exc:
                    LOGGER.error("Lost Pixoo connection while rendering holding view (%s).", exc)
                    pizzoo = _connect_pixoo_with_retry()
                    current_state = None
                    current_flight_id = None
                    continue
            elif target_state == STATE_API_ERROR:
                try:
                    _build_and_send_holding_screen(pizzoo, status="API ERROR")
                except Exception as exc:
                    LOGGER.error("Lost Pixoo connection while rendering holding view (%s).", exc)
                    pizzoo = _connect_pixoo_with_retry()
                    current_state = None
                    current_flight_id = None
                    continue
            else:
                try:
                    _build_and_send_holding_screen(pizzoo, status="NO FLIGHTS")
                except Exception as exc:
                    LOGGER.error("Lost Pixoo connection while rendering holding view (%s).", exc)
                    pizzoo = _connect_pixoo_with_retry()
                    current_state = None
                    current_flight_id = None
                    continue
            current_state = target_state
        elif target_state == STATE_IDLE_WEATHER:
            weather_payload, refreshed = wx.get_current()
            if refreshed:
                weather_error = wx.get_last_error()
                if weather_error:
                    LOGGER.warning("Weather refresh failed (%s); using cached/fallback weather data.", weather_error)
                else:
                    LOGGER.info("Weather updated from API (%s).", weather_payload.get("source", "unknown source"))
                try:
                    _build_and_send_weather_idle_screen(pizzoo, weather_payload)
                except Exception as exc:
                    LOGGER.error("Lost Pixoo connection while rendering weather view (%s).", exc)
                    pizzoo = _connect_pixoo_with_retry()
                    current_state = None
                    current_flight_id = None
                    continue

        if target_state == STATE_RATE_LIMIT:
            if cooldown_remaining > 0:
                LOGGER.warning("FlightRadar24 rate limit active, retrying in %ss.", retry_seconds)
        elif target_state == STATE_API_ERROR:
            LOGGER.warning("Flight API error, retrying in %ss.", retry_seconds)
        else:
            LOGGER.info("No flight data available, retrying in %ss.", retry_seconds)

        sleep(retry_seconds)
        no_data_retry_seconds = min(no_data_retry_seconds * 2, NO_FLIGHT_MAX_RETRY_SECONDS)


if __name__ == "__main__":
    main()
