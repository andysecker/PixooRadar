import logging
from PIL import Image

from .common import (
    AIRPLANE_CYCLE,
    COLOR_LABEL,
    COLOR_ROUTE_LINE,
    ROUTE_END,
    ROUTE_START,
    TOTAL_FRAMES,
    center_x,
    draw_airplane_icon,
    draw_separator_line,
    dump_render_debug_gif,
    format_altitude_feet_raw,
    format_heading,
    format_speed,
    measure_text_width,
)

LOGGER = logging.getLogger("pixoo_radar")

TOP_BAND_HEIGHT = 20
TOP_TEXT_HEIGHT = 7
TOP_TEXT_Y_CENTERED = (TOP_BAND_HEIGHT - TOP_TEXT_HEIGHT) // 2
TOP_TEXT_Y_STATIC = 7
AIRLINE_SCROLL_GAP_PX = 12


def _draw_airline_name(pizzoo, settings, airline_name: str, frame_idx: int | None) -> None:
    name = str(airline_name or "")
    if not name:
        return

    if frame_idx is None:
        static_name = name[:10]
        pizzoo.draw_text(static_name, xy=(center_x(64, static_name), TOP_TEXT_Y_STATIC), font=settings.font_name, color="#FFFFFF")
        return

    text_w = measure_text_width(name)
    if text_w <= 64:
        pizzoo.draw_text(name, xy=(center_x(64, name), TOP_TEXT_Y_CENTERED), font=settings.font_name, color="#FFFFFF")
        return

    total_steps = max(1, TOTAL_FRAMES - 1)
    travel_px = text_w + AIRLINE_SCROLL_GAP_PX
    progress = min(max(frame_idx, 0), total_steps) / total_steps
    primary_x = int(round(-travel_px * progress))
    line_width = max(64, text_w + 1)
    pizzoo.draw_text(name, xy=(primary_x, TOP_TEXT_Y_CENTERED), font=settings.font_name, color="#FFFFFF", line_width=line_width)


def draw_top_section(
    pizzoo,
    settings,
    logo: str,
    origin: str,
    destination: str,
    airline_name: str = "",
    y_route: int = 20,
    frame_idx: int | None = None,
) -> None:
    if logo:
        pizzoo.draw_image(logo, xy=(0, 0), size=(64, 20), resample_method=Image.LANCZOS)
    elif airline_name:
        _draw_airline_name(pizzoo, settings, airline_name, frame_idx=frame_idx)

    draw_separator_line(pizzoo, y=20, style="dashed")
    pizzoo.draw_rectangle(xy=(0, 21), width=64, height=11, color=settings.color_box, filled=True)
    pizzoo.draw_text(origin, xy=(2, y_route), font=settings.font_name, color=settings.color_text)
    dest_width = measure_text_width(destination)
    pizzoo.draw_text(destination, xy=(62 - dest_width, y_route), font=settings.font_name, color=settings.color_text)

    for i in range(ROUTE_START, ROUTE_END, 3):
        pizzoo.draw_rectangle(xy=(i, y_route + 6), width=2, height=1, color=COLOR_ROUTE_LINE, filled=True)


def draw_label_value(pizzoo, settings, label: str, value: str, y: int) -> None:
    full_text = f"{label} {value}"
    x_start = center_x(64, full_text)
    pizzoo.draw_text(label, xy=(x_start, y), font=settings.font_name, color=COLOR_LABEL)
    value_x = x_start + (len(label) + 1) * 6
    pizzoo.draw_text(value, xy=(value_x, y), font=settings.font_name, color=settings.color_text)


def draw_altitude_ft_value(pizzoo, settings, altitude_raw, y: int) -> None:
    value = format_altitude_feet_raw(altitude_raw)
    suffix = "ft"
    full_text = f"{value} {suffix}"
    x_start = center_x(64, full_text)
    pizzoo.draw_text(value, xy=(x_start, y), font=settings.font_name, color=settings.color_text)
    suffix_x = x_start + measure_text_width(f"{value} ")
    pizzoo.draw_text(suffix, xy=(suffix_x, y), font=settings.font_name, color=COLOR_LABEL)


def draw_info_page(pizzoo, settings, upper_pair: tuple, lower_pair: tuple) -> None:
    pizzoo.draw_rectangle(xy=(0, 33), width=64, height=31, color=settings.color_box, filled=True)
    draw_separator_line(pizzoo, y=32, style="dashed")
    draw_label_value(pizzoo, settings, upper_pair[0], upper_pair[1], y=34)
    draw_separator_line(pizzoo, y=48, style="dashed")
    if lower_pair[0] == "__ALT_RAW_FT__":
        draw_altitude_ft_value(pizzoo, settings, lower_pair[1], y=50)
    else:
        draw_label_value(pizzoo, settings, lower_pair[0], lower_pair[1], y=50)


def build_and_send_animation(pizzoo, settings, data: dict) -> None:
    logo = data.get("airline_logo_path", "")
    airline_name = str(data.get("airline", "") or "")
    origin = str(data.get("origin", "---"))[:3]
    destination = str(data.get("destination", "---"))[:3]
    callsign = str(data.get("callsign") or data.get("flight_number") or "----")[:7]
    aircraft = str(data.get("aircraft_type_icao", "----"))[:4]
    registration = str(data.get("registration", "------"))[:7]
    altitude = data.get("altitude")
    speed = data.get("ground_speed", 0) or 0
    heading = data.get("heading")

    info_pages = [
        (("CS", callsign), ("__ALT_RAW_FT__", altitude)),
        (("TYPE", aircraft), ("REG", registration)),
        (("SPD", format_speed(speed, settings.flight_speed_unit)), ("HDG", format_heading(heading))),
    ]
    frames_per_page = TOTAL_FRAMES // len(info_pages)
    y_route = 20

    for frame_idx in range(TOTAL_FRAMES):
        pizzoo.cls()
        draw_top_section(pizzoo, settings, logo, origin, destination, airline_name, y_route, frame_idx=frame_idx)
        plane_x = ROUTE_START - 5 + (frame_idx % AIRPLANE_CYCLE)
        draw_airplane_icon(pizzoo, plane_x, y_route + 4, clip_left=ROUTE_START, clip_right=ROUTE_END)

        page_idx = min(frame_idx // frames_per_page, len(info_pages) - 1)
        upper_pair, lower_pair = info_pages[page_idx]
        draw_info_page(pizzoo, settings, upper_pair, lower_pair)
        if frame_idx < TOTAL_FRAMES - 1:
            pizzoo.add_frame()

    LOGGER.info("Sending %s flight frames to device (frame speed: %sms).", TOTAL_FRAMES, settings.animation_frame_speed)
    dump_render_debug_gif(pizzoo, settings.animation_frame_speed)
    pizzoo.render(frame_speed=settings.animation_frame_speed)
