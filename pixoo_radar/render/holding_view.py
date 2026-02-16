import logging

from .flight_view import draw_info_page, draw_top_section

LOGGER = logging.getLogger("pixoo_radar")


def build_and_send_holding_screen(pizzoo, settings, status: str = "NO FLIGHTS") -> None:
    radius_km = max(1, int(round(settings.flight_search_radius_meters / 1000)))
    range_text = f"{radius_km}KM"

    pizzoo.cls()
    draw_top_section(pizzoo, settings, logo="", origin="---", destination="---", airline_name=status, y_route=20)
    draw_info_page(pizzoo, settings, ("STATUS", status[:10]), ("RANGE", range_text))
    LOGGER.info("Sending holding screen (%s).", status)
    pizzoo.render(frame_speed=settings.animation_frame_speed)
