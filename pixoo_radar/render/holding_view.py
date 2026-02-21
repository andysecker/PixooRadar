import logging
import random

from .common import dump_render_debug_gif, ensure_clean_render_buffer, measure_text_width
from .flight_view import draw_info_page, draw_top_section

LOGGER = logging.getLogger("pixoo_radar")
COLOR_POLL_PAUSE_TEXT = "#4A4A4A"
POLL_PAUSE_LINE_Y_OFFSETS = (0, 12, 28, 40)
POLL_PAUSE_FONT_HEIGHT = 8


def build_and_send_holding_screen(pizzoo, settings, status: str = "NO FLIGHTS") -> None:
    ensure_clean_render_buffer(pizzoo)
    radius_km = max(1, int(round(settings.flight_search_radius_meters / 1000)))
    range_text = f"{radius_km}KM"

    pizzoo.cls()
    draw_top_section(pizzoo, settings, logo="", origin="---", destination="---", airline_name=status, y_route=20)
    draw_info_page(pizzoo, settings, ("STATUS", status[:10]), ("RANGE", range_text))
    LOGGER.info("Sending holding screen (%s).", status)
    dump_render_debug_gif(pizzoo, settings.animation_frame_speed)
    pizzoo.render(frame_speed=settings.animation_frame_speed)


def build_and_send_poll_pause_screen(pizzoo, settings, resume_hhmm: str) -> None:
    """Render a simple pause notice during configured overnight polling pause."""
    ensure_clean_render_buffer(pizzoo)
    resume_token = "".join(ch for ch in str(resume_hhmm or "") if ch.isdigit())[:4]
    if len(resume_token) != 4:
        resume_token = "----"

    lines = ("Updates", "paused.", "Resume at", resume_token)
    block_width = max(measure_text_width(line) for line in lines)
    block_height = POLL_PAUSE_LINE_Y_OFFSETS[-1] + POLL_PAUSE_FONT_HEIGHT
    max_x = max(0, 64 - block_width)
    max_y = max(0, 64 - block_height)
    origin_x = random.randint(0, max_x)
    origin_y = random.randint(0, max_y)

    pizzoo.cls()
    pizzoo.draw_rectangle(xy=(0, 0), width=64, height=64, color="#000000", filled=True)
    for line, y_offset in zip(lines, POLL_PAUSE_LINE_Y_OFFSETS):
        pizzoo.draw_text(
            line,
            xy=(origin_x, origin_y + y_offset),
            font=settings.font_name,
            color=COLOR_POLL_PAUSE_TEXT,
        )

    LOGGER.info(
        "Sending polling-pause holding screen (resume at %s, text origin=(%s,%s)).",
        resume_token,
        origin_x,
        origin_y,
    )
    dump_render_debug_gif(pizzoo, settings.animation_frame_speed)
    pizzoo.render(frame_speed=settings.animation_frame_speed)
