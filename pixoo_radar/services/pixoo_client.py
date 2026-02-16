import logging
import socket
from time import sleep

from pizzoo import Pizzoo

LOGGER = logging.getLogger("pixoo_radar")


class PixooClient:
    def __init__(self, settings):
        self.settings = settings

    def connect_with_retry(self):
        while True:
            try:
                LOGGER.info("Connecting to Pixoo at %s:%s...", self.settings.pixoo_ip, self.settings.pixoo_port)
                pixoo = Pizzoo(self.settings.pixoo_ip, debug=True)
                pixoo.load_font(self.settings.font_name, self.settings.font_path)
                if (
                    self.settings.runway_label_font_name != self.settings.font_name
                    or self.settings.runway_label_font_path != self.settings.font_path
                ):
                    pixoo.load_font(self.settings.runway_label_font_name, self.settings.runway_label_font_path)
                LOGGER.info("Pixoo connected.")
                return pixoo
            except Exception as exc:
                LOGGER.warning("Pixoo unavailable (%s). Retrying in %ss...", exc, self.settings.pixoo_reconnect_seconds)
                sleep(self.settings.pixoo_reconnect_seconds)

    def is_reachable(self, timeout_seconds: float = 2.0) -> bool:
        try:
            with socket.create_connection((self.settings.pixoo_ip, self.settings.pixoo_port), timeout=timeout_seconds):
                return True
        except OSError:
            return False
