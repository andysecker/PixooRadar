import logging
import socket
from time import monotonic, sleep

from pizzoo import Pizzoo

LOGGER = logging.getLogger("pixoo_radar")
PIXOO_HTTP_TIMEOUT_SECONDS = 5.0
_PIXOO_POST_TIMEOUT_PATCHED = False


def _install_pizzoo_http_timeout_patch(timeout_seconds: float = PIXOO_HTTP_TIMEOUT_SECONDS) -> None:
    """
    Patch pizzoo renderer HTTP calls to use a finite timeout.

    The upstream library uses requests.post without timeout, which can block
    indefinitely if the device disappears mid-render.
    """
    global _PIXOO_POST_TIMEOUT_PATCHED
    if _PIXOO_POST_TIMEOUT_PATCHED:
        return
    try:
        import pizzoo._renderers as pizzoo_renderers
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Unable to apply Pixoo HTTP timeout patch: %s", exc)
        return

    original_post = getattr(pizzoo_renderers, "post", None)
    if not callable(original_post):
        LOGGER.warning("Unable to apply Pixoo HTTP timeout patch: renderer post callable not found.")
        return

    def post_with_timeout(*args, **kwargs):
        kwargs.setdefault("timeout", timeout_seconds)
        return original_post(*args, **kwargs)

    pizzoo_renderers.post = post_with_timeout
    _PIXOO_POST_TIMEOUT_PATCHED = True
    LOGGER.info("Applied Pixoo HTTP timeout patch (%ss).", timeout_seconds)


class PixooClient:
    def __init__(self, settings):
        self.settings = settings

    def _load_fonts(self, pixoo) -> None:
        try:
            pixoo.load_font(self.settings.font_name, self.settings.font_path)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load primary font '{self.settings.font_name}' "
                f"from '{self.settings.font_path}': {exc}"
            ) from exc
        if (
            self.settings.runway_label_font_name != self.settings.font_name
            or self.settings.runway_label_font_path != self.settings.font_path
        ):
            try:
                pixoo.load_font(self.settings.runway_label_font_name, self.settings.runway_label_font_path)
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to load runway label font '{self.settings.runway_label_font_name}' "
                    f"from '{self.settings.runway_label_font_path}': {exc}"
                ) from exc

    def connect_with_retry(self, fail_fast: bool = False):
        _install_pizzoo_http_timeout_patch()
        deadline = None
        if fail_fast:
            deadline = monotonic() + float(self.settings.pixoo_startup_connect_timeout_seconds)
        while True:
            try:
                LOGGER.info("Connecting to Pixoo at %s:%s...", self.settings.pixoo_ip, self.settings.pixoo_port)
                pixoo = Pizzoo(self.settings.pixoo_ip, debug=True)
                self._load_fonts(pixoo)
                LOGGER.info("Pixoo connected.")
                return pixoo
            except RuntimeError:
                raise
            except Exception as exc:
                if deadline is not None and monotonic() >= deadline:
                    raise RuntimeError(
                        "Failed to connect to Pixoo at "
                        f"{self.settings.pixoo_ip}:{self.settings.pixoo_port} within "
                        f"{self.settings.pixoo_startup_connect_timeout_seconds}s: {exc}"
                    ) from exc
                LOGGER.warning("Pixoo unavailable (%s). Retrying in %ss...", exc, self.settings.pixoo_reconnect_seconds)
                sleep(self.settings.pixoo_reconnect_seconds)

    def is_reachable(self, timeout_seconds: float = 2.0) -> bool:
        try:
            with socket.create_connection((self.settings.pixoo_ip, self.settings.pixoo_port), timeout=timeout_seconds):
                return True
        except OSError:
            return False
