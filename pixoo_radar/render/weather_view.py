import logging
from math import cos, radians, sin

from .common import (
    bearing_to_xy,
    center_x,
    draw_line,
    draw_px,
    dump_render_debug_gif,
    ensure_clean_render_buffer,
    fit_text,
    format_humidity,
    format_temp_c,
    format_wind_dir,
    format_wind_kph,
    measure_text_width,
    runway_designator,
    signed_angle_diff_deg,
)

LOGGER = logging.getLogger("pixoo_radar")

COLOR_WX_BG = "#10243F"
COLOR_WX_ACCENT = "#2F6EA4"
COLOR_WX_TEXT = "#EAF6FF"
COLOR_WX_MUTED = "#A8C7DE"
COLOR_RWY = "#111111"
COLOR_RWY_MARK = "#EDEDED"
COLOR_WIND_ARROW = "#FFD166"
COLOR_ACTIVE_RWY_ARROW = "#7CFC8A"
COLOR_HOME_ICON = "#EAF6FF"
RUNWAY_VIEW_ROTATION_DEG = 180.0


def wind_speed_value_for_unit(wind_kph, wind_unit: str):
    if wind_kph is None:
        return None
    unit = str(wind_unit or "").lower()
    if unit == "mph":
        return int(round(float(wind_kph) * 0.621371))
    return int(round(float(wind_kph)))


def normalize_wind_dir_deg(wind_dir_deg):
    if wind_dir_deg is None:
        return None
    try:
        return float(wind_dir_deg) % 360.0
    except (TypeError, ValueError):
        return None


def nearest_drawn_tick_bearing(wind_dir_deg):
    wind_dir = normalize_wind_dir_deg(wind_dir_deg)
    if wind_dir is None:
        return None
    tick_bearings = range(0, 360, 10)
    return min(tick_bearings, key=lambda b: abs(signed_angle_diff_deg(wind_dir, float(b))))


def resolve_active_runway_heading(wind_dir_deg, runway_heading_deg: float) -> float | None:
    wind_from = normalize_wind_dir_deg(wind_dir_deg)
    if wind_from is None:
        return None
    reciprocal_heading = (runway_heading_deg + 180.0) % 360.0
    diff_base = abs(signed_angle_diff_deg(wind_from, runway_heading_deg))
    diff_recip = abs(signed_angle_diff_deg(wind_from, reciprocal_heading))
    return runway_heading_deg if diff_base <= diff_recip else reciprocal_heading


def score_label_placement(tx: int, ty: int, label_w: int, label_h: int, cx: int, cy: int, nx: float, ny: float,
                          anchor_x: float, anchor_y: float):
    corners = (
        (tx, ty),
        (tx + label_w - 1, ty),
        (tx, ty + label_h - 1),
        (tx + label_w - 1, ty + label_h - 1),
    )
    clearance = min(abs((px - cx) * nx + (py - cy) * ny) for px, py in corners)
    anchor_dist = abs((tx + (label_w / 2)) - anchor_x) + abs((ty + (label_h / 2)) - anchor_y)
    return clearance, -anchor_dist


def choose_runway_label_position(label_w: int, label_h: int, runway_heading_deg: float, anchor_x: float, anchor_y: float):
    cx, cy = 32, 32
    rwy_rad = radians(float(runway_heading_deg) % 360.0)
    ux, uy = sin(rwy_rad), -cos(rwy_rad)
    nx, ny = uy, -ux
    best = None
    for side in (1, -1):
        for n_off in (7, 9, 11):
            for u_off in (-3, 0, 3):
                lx = anchor_x + side * n_off * nx + u_off * ux
                ly = anchor_y + side * n_off * ny + u_off * uy
                tx = max(0, min(64 - label_w, int(round(lx - (label_w / 2)))))
                ty = max(0, min(64 - label_h, int(round(ly - (label_h / 2)))))
                score = score_label_placement(tx, ty, label_w, label_h, cx, cy, nx, ny, anchor_x, anchor_y)
                if best is None or score > best[0]:
                    best = (score, tx, ty)
    _, tx, ty = best
    return max(0, min(64 - label_w, tx - 2)), max(0, min(64 - label_h, ty + 1))


def draw_home_icon(pizzoo, x: int = 1, y: int = 1, color: str = COLOR_HOME_ICON) -> None:
    """Draw a tiny 10x9 house icon in the runway view corner."""
    # Roof drawn as explicit pixels for symmetric low-res rendering.
    roof_pixels = (
        (4, 0), (5, 0),
        (3, 1), (6, 1),
        (2, 2), (7, 2),
        (1, 3), (8, 3),
        (0, 4), (9, 4),
    )
    for dx, dy in roof_pixels:
        draw_px(pizzoo, x + dx, y + dy, color)

    # House body outline.
    for dx in range(1, 9):
        draw_px(pizzoo, x + dx, y + 4, color)
        draw_px(pizzoo, x + dx, y + 8, color)
    for dy in range(4, 9):
        draw_px(pizzoo, x + 1, y + dy, color)
        draw_px(pizzoo, x + 8, y + dy, color)

    # Door (2x3).
    for dy in range(6, 9):
        draw_px(pizzoo, x + 4, y + dy, color)
        draw_px(pizzoo, x + 5, y + dy, color)


def draw_runway_wind_diagram(pizzoo, settings, wind_dir_deg, runway_heading_deg: float, wind_dir_from=None, wind_dir_to=None) -> None:
    def view_bearing(bearing_deg: float) -> float:
        return (float(bearing_deg) + RUNWAY_VIEW_ROTATION_DEG) % 360.0

    cx, cy = 32, 32
    runway_half_len = 22
    pizzoo.draw_rectangle(xy=(0, 0), width=64, height=64, color=COLOR_WX_BG, filled=True)
    draw_home_icon(pizzoo, x=54, y=54)

    highlighted_ticks = set()
    from_tick = nearest_drawn_tick_bearing(wind_dir_from)
    to_tick = nearest_drawn_tick_bearing(wind_dir_to)
    if from_tick is not None:
        highlighted_ticks.add(from_tick)
    if to_tick is not None:
        highlighted_ticks.add(to_tick)

    for b in range(0, 360, 10):
        vb = view_bearing(b)
        if int(round(vb)) % 360 == 0:
            continue
        x1, y1 = bearing_to_xy(cx, cy, vb, 28)
        x2, y2 = bearing_to_xy(cx, cy, vb, 30)
        tick_color = COLOR_WIND_ARROW if b in highlighted_ticks else COLOR_WX_ACCENT
        draw_line(pizzoo, x1, y1, x2, y2, color=tick_color, thickness=1)

    pizzoo.draw_text("S", xy=(center_x(64, "S") + 2, -1), font=settings.runway_label_font_name, color=COLOR_WX_TEXT)

    rx0, ry0 = bearing_to_xy(cx, cy, view_bearing(runway_heading_deg), runway_half_len)
    rx1, ry1 = bearing_to_xy(cx, cy, view_bearing((runway_heading_deg + 180) % 360), runway_half_len)
    draw_line(pizzoo, rx0, ry0, rx1, ry1, color=COLOR_RWY, thickness=7)
    draw_line(pizzoo, rx0, ry0, rx1, ry1, color=COLOR_RWY_MARK, thickness=1)

    active_heading = resolve_active_runway_heading(wind_dir_deg, runway_heading_deg)
    if active_heading is not None:
        if active_heading == runway_heading_deg:
            ax0, ay0 = rx1, ry1
        else:
            ax0, ay0 = rx0, ry0
        ax1, ay1 = bearing_to_xy(ax0, ay0, view_bearing(active_heading), 11)
        draw_line(pizzoo, ax0, ay0, ax1, ay1, color=COLOR_ACTIVE_RWY_ARROW, thickness=2)
        left = view_bearing((active_heading + 142.0) % 360.0)
        right = view_bearing((active_heading - 142.0) % 360.0)
        hx0, hy0 = bearing_to_xy(ax1, ay1, left, 3)
        hx1, hy1 = bearing_to_xy(ax1, ay1, right, 3)
        draw_line(pizzoo, ax1, ay1, hx0, hy0, color=COLOR_ACTIVE_RWY_ARROW, thickness=1)
        draw_line(pizzoo, ax1, ay1, hx1, hy1, color=COLOR_ACTIVE_RWY_ARROW, thickness=1)

        active_rwy = runway_designator(active_heading)
        label_w, label_h = measure_text_width(active_rwy), 7
        anchor_x, anchor_y = (ax0 + ax1) / 2.0, (ay0 + ay1) / 2.0
        tx, ty = choose_runway_label_position(label_w, label_h, runway_heading_deg, anchor_x, anchor_y)
        pizzoo.draw_text(active_rwy, xy=(tx, ty), font=settings.runway_label_font_name, color=COLOR_ACTIVE_RWY_ARROW)

    wind_from = normalize_wind_dir_deg(wind_dir_deg)
    if wind_from is not None:
        shaft_bearing = view_bearing((wind_from + 180.0) % 360.0)
        wind_from_view = view_bearing(wind_from)
        ax0, ay0 = bearing_to_xy(cx, cy, wind_from_view, 24)
        ax1, ay1 = bearing_to_xy(cx, cy, wind_from_view, 10)
        draw_line(pizzoo, ax0, ay0, ax1, ay1, color=COLOR_WIND_ARROW, thickness=2)
        left = (shaft_bearing + 150.0) % 360.0
        right = (shaft_bearing - 150.0) % 360.0
        hx0, hy0 = bearing_to_xy(ax1, ay1, left, 4)
        hx1, hy1 = bearing_to_xy(ax1, ay1, right, 4)
        draw_line(pizzoo, ax1, ay1, hx0, hy0, color=COLOR_WIND_ARROW, thickness=1)
        draw_line(pizzoo, ax1, ay1, hx1, hy1, color=COLOR_WIND_ARROW, thickness=1)


def build_and_send_weather_idle_screen(pizzoo, settings, weather: dict) -> None:
    ensure_clean_render_buffer(pizzoo)
    draw_weather_summary_frame(pizzoo, settings, weather)
    pizzoo.add_frame()
    draw_runway_wind_diagram(
        pizzoo,
        settings,
        wind_dir_deg=weather.get("wind_dir_deg"),
        runway_heading_deg=float(settings.runway_heading_deg),
        wind_dir_from=weather.get("wind_dir_from"),
        wind_dir_to=weather.get("wind_dir_to"),
    )
    LOGGER.info("Sending weather idle screen (2 frames, %ss per frame).", settings.weather_view_seconds)
    frame_speed = max(500, int(settings.weather_view_seconds * 1000))
    dump_render_debug_gif(pizzoo, frame_speed)
    pizzoo.render(frame_speed=frame_speed)


def draw_weather_summary_frame(pizzoo, settings, weather: dict) -> None:
    """Draw frame 1 of weather idle mode (summary text card)."""
    condition = fit_text(str(weather.get("condition") or "NO DATA").upper(), 10)
    temperature = format_temp_c(weather.get("temperature_c"))
    humidity = format_humidity(weather.get("humidity_pct"))
    wind = format_wind_kph(weather.get("wind_kph"), settings.weather_wind_speed_unit)
    wind_speed = wind_speed_value_for_unit(weather.get("wind_kph"), settings.weather_wind_speed_unit)
    wind_gust = wind_speed_value_for_unit(weather.get("wind_gust_kph"), settings.weather_wind_speed_unit)
    wind_dir_deg = normalize_wind_dir_deg(weather.get("wind_dir_deg"))
    wind_dir = format_wind_dir(wind_dir_deg) if wind_dir_deg is not None else None
    metar_station = str(weather.get("metar_station") or "").strip().upper()
    metar_time_z = str(weather.get("metar_time_z") or "").strip().upper()
    weather_header = fit_text(f"{metar_station} {metar_time_z}", 10) if metar_station and metar_time_z else "Weather"

    pizzoo.cls()
    pizzoo.draw_rectangle(xy=(0, 0), width=64, height=64, color=COLOR_WX_BG, filled=True)
    pizzoo.draw_rectangle(xy=(0, 0), width=64, height=11, color=COLOR_WX_ACCENT, filled=True)
    pizzoo.draw_text(weather_header, xy=(2, -1), font=settings.font_name, color=COLOR_WX_TEXT)
    hum_line = fit_text(f"HUM {humidity}", 10)
    if wind_gust is not None and wind_speed is not None:
        wind_text = f"{wind_speed}/{wind_gust}"
        wind_line = fit_text(f"{wind_dir} {wind_text}", 10) if wind_dir else fit_text(f"-- {wind_text}", 10)
    else:
        wind_text = wind.replace(" ", "")
        wind_line = fit_text(f"{wind_dir} {wind_text}", 10) if wind_dir else fit_text(f"-- {wind_text}", 10)
    pizzoo.draw_text(temperature, xy=(center_x(64, temperature), 13), font=settings.font_name, color=COLOR_WX_TEXT)
    pizzoo.draw_text(condition, xy=(center_x(64, condition), 25), font=settings.font_name, color=COLOR_WX_MUTED)
    pizzoo.draw_text(hum_line, xy=(center_x(64, hum_line), 37), font=settings.font_name, color=COLOR_WX_TEXT)
    pizzoo.draw_text(wind_line, xy=(center_x(64, wind_line), 49), font=settings.font_name, color=COLOR_WX_TEXT)
