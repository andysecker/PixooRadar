import logging
from math import cos, radians, sin
from pathlib import Path

from PIL import Image


COLOR_ROUTE_LINE = "#666666"
COLOR_PLANE = "#FFFFFF"
COLOR_SEPARATOR = "#555555"
COLOR_LABEL = "#999999"
DEBUG_RENDER_GIF_PATH = Path("debug/current_pixoo_render.gif")

LOGGER = logging.getLogger("pixoo_radar")

PLANE_WIDTH = 5
ROUTE_START = 21
ROUTE_END = 43
ROUTE_WIDTH = ROUTE_END - ROUTE_START
AIRPLANE_CYCLE = ROUTE_WIDTH + PLANE_WIDTH
TOTAL_FRAMES = AIRPLANE_CYCLE


def measure_text_width(text: str) -> int:
    return max(1, len(str(text)) * 6 - 1)


def center_x(rect_width: int, text: str) -> int:
    return max(0, (rect_width - measure_text_width(text)) // 2)


def draw_separator_line(pizzoo, y: int, style: str = "solid") -> None:
    if style == "solid":
        pizzoo.draw_rectangle(xy=(0, y), width=64, height=1, color=COLOR_SEPARATOR, filled=True)
    elif style == "dashed":
        for x in range(0, 64, 4):
            pizzoo.draw_rectangle(xy=(x, y), width=2, height=1, color=COLOR_SEPARATOR, filled=True)


def draw_airplane_icon(pizzoo, x: int, y: int, clip_left: int = 0, clip_right: int = 64, color: str = COLOR_PLANE) -> None:
    for px in range(x, x + 5):
        if clip_left <= px < clip_right:
            pizzoo.draw_rectangle(xy=(px, y + 2), width=1, height=1, color=color, filled=True)
    if clip_left <= x + 2 < clip_right:
        pizzoo.draw_rectangle(xy=(x + 2, y), width=1, height=5, color=color, filled=True)
    if clip_left <= x < clip_right:
        pizzoo.draw_rectangle(xy=(x, y + 1), width=1, height=3, color=color, filled=True)


def fit_text(text: str, max_chars: int = 10) -> str:
    return str(text)[:max_chars]


def signed_angle_diff_deg(angle_a: float, angle_b: float) -> float:
    return ((angle_a - angle_b + 180.0) % 360.0) - 180.0


def runway_designator(heading_deg: float) -> str:
    runway = int(round(float(heading_deg) / 10.0)) % 36
    if runway == 0:
        runway = 36
    return f"{runway:02d}"


def bearing_to_xy(cx: int, cy: int, bearing_deg: float, distance: float):
    rad = radians(float(bearing_deg) % 360.0)
    return int(round(cx + distance * sin(rad))), int(round(cy - distance * cos(rad)))


def draw_px(pizzoo, x: int, y: int, color: str) -> None:
    if 0 <= x < 64 and 0 <= y < 64:
        pizzoo.draw_rectangle(xy=(x, y), width=1, height=1, color=color, filled=True)


def draw_line(pizzoo, x0: int, y0: int, x1: int, y1: int, color: str, thickness: int = 1) -> None:
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    radius = max(0, (thickness - 1) // 2)
    while True:
        for ox in range(-radius, radius + 1):
            for oy in range(-radius, radius + 1):
                draw_px(pizzoo, x0 + ox, y0 + oy, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def format_flight_level(altitude_ft: int) -> str:
    if altitude_ft is None or altitude_ft < 1000:
        return "GND"
    return f"FL{(altitude_ft // 100):03d}"


def format_altitude_feet_raw(altitude_ft) -> str:
    """Format raw altitude in feet with thousands separator."""
    if altitude_ft is None:
        return "---"
    try:
        value = int(round(float(altitude_ft)))
    except (TypeError, ValueError):
        return "---"
    return f"{value:,}"


def format_speed(speed_kts: int, unit: str) -> str:
    if speed_kts is None:
        return "---Mph" if unit.lower() == "mph" else "---Kt"
    if unit.lower() == "mph":
        return f"{int(round(float(speed_kts) * 1.15078))}Mph"
    return f"{int(round(float(speed_kts)))}Kt"


def format_heading(heading: int) -> str:
    if heading is None:
        return "---"
    return f"{heading:03d}"


def format_temp_c(temperature_c) -> str:
    if temperature_c is None:
        return "--C"
    return f"{int(round(temperature_c))}C"


def format_humidity(humidity_pct) -> str:
    if humidity_pct is None:
        return "--%"
    return f"{int(round(humidity_pct))}%"


def format_wind_kph(wind_kph, wind_unit: str) -> str:
    unit = wind_unit.lower()
    use_mph = unit == "mph"
    use_kmh = unit in ("kmh", "kph")
    if wind_kph is None:
        return "-- Mph" if use_mph else "-- Kmh"
    if use_mph:
        return f"{int(round(float(wind_kph) * 0.621371))} Mph"
    if use_kmh:
        return f"{int(round(float(wind_kph)))} Kmh"
    return f"{int(round(float(wind_kph)))} Kmh"


def format_wind_dir(wind_dir_deg) -> str:
    if wind_dir_deg is None:
        return "--"
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return directions[int((float(wind_dir_deg) + 22.5) // 45) % 8]


def dump_render_debug_gif(pizzoo, frame_speed: int, output_path: Path = DEBUG_RENDER_GIF_PATH) -> bool:
    """
    Persist the current Pizzoo frame buffer as a single debug GIF.

    Returns True on successful write. Returns False when no compatible frame
    buffer is available (for example during unit tests using RecordingPizzoo).
    """
    buffer = getattr(pizzoo, "_Pizzoo__buffer", None)
    size = getattr(pizzoo, "size", None)
    if not isinstance(buffer, list) or not buffer:
        return False
    try:
        size = int(size)
    except (TypeError, ValueError):
        return False

    expected_len = size * size * 3
    images = []
    for frame in buffer:
        if not isinstance(frame, list) or len(frame) != expected_len:
            return False
        images.append(Image.frombytes("RGB", (size, size), bytes(frame), "raw"))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(
        output_path,
        format="GIF",
        save_all=True,
        append_images=images[1:],
        loop=0,
        duration=max(1, int(frame_speed)),
    )
    LOGGER.info("Saved render debug GIF: %s (%s frames)", output_path, len(images))
    return True


def ensure_clean_render_buffer(pizzoo) -> None:
    """
    Reset render buffer before drawing to avoid frame accumulation after failures.

    The upstream `pizzoo` object can retain buffered frames if `render()` fails
    before it resets internal state.
    """
    reset_buffer = getattr(pizzoo, "reset_buffer", None)
    if not callable(reset_buffer):
        return
    try:
        removed = int(reset_buffer())
    except Exception:  # noqa: BLE001
        return
    if removed > 1:
        LOGGER.warning("Recovered stale Pixoo frame buffer before render (%s old frames removed).", removed)
