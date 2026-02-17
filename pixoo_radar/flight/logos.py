"""Airline logo cache/resize utilities."""

from io import BytesIO
from pathlib import Path


class LogoManager:
    """Cache and normalize airline logos for Pixoo display."""

    def __init__(self, save_logo_dir: str | Path | None, bg_color=(255, 255, 255, 0)):
        self.save_logo_dir = Path(save_logo_dir) if save_logo_dir else None
        self.bg_color = bg_color
        if self.save_logo_dir:
            self.save_logo_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_base_name(airline_iata: str | None, airline_icao: str | None) -> str:
        file_base = airline_iata or airline_icao or "airline_logo"
        safe = "".join(c for c in str(file_base) if c.isalnum() or c in ("-", "_")).strip()
        return safe or "airline_logo"

    def _cached_logo_path(self, airline_iata: str | None, airline_icao: str | None):
        if not self.save_logo_dir:
            return None
        path = self.save_logo_dir / f"{self._safe_base_name(airline_iata, airline_icao)}.png"
        return path if path.exists() else None

    @staticmethod
    def _resize_logo_bytes(
        logo_bytes: bytes,
        target_w: int = 64,
        target_h: int = 20,
        bg=(255, 255, 255, 0),
        sharpen: bool = True,
        autocontrast: bool = True,
        flatten_bg: bool = True,
    ):
        try:
            from PIL import Image, ImageFilter, ImageOps
        except Exception:
            return logo_bytes, None

        try:
            src = Image.open(BytesIO(logo_bytes)).convert("RGBA")
        except Exception:
            return logo_bytes, None

        if flatten_bg and src.mode == "RGBA":
            try:
                background = Image.new("RGBA", src.size, bg)
                background.paste(src, mask=src.split()[3])
                src = background
            except Exception:
                pass

        w, h = src.size
        if w == 0 or h == 0:
            return logo_bytes, None

        scale = min(target_w / w, target_h / h)
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))

        try:
            resized = src.resize((new_w, new_h), resample=Image.LANCZOS)
        except Exception:
            try:
                resized = src.resize((new_w, new_h))
            except Exception:
                return logo_bytes, None

        if autocontrast:
            try:
                resized = ImageOps.autocontrast(resized, cutoff=0)
            except Exception:
                pass
        if sharpen:
            try:
                resized = resized.filter(ImageFilter.UnsharpMask(radius=0.8, percent=150, threshold=2))
            except Exception:
                pass

        canvas = Image.new("RGBA", (target_w, target_h), bg)
        x = (target_w - new_w) // 2
        y = (target_h - new_h) // 2
        try:
            canvas.paste(resized, (x, y), resized if resized.mode == "RGBA" else None)
        except Exception:
            canvas.paste(resized, (x, y))

        out = BytesIO()
        try:
            canvas.save(out, format="PNG", optimize=True)
            return out.getvalue(), "png"
        except Exception:
            return logo_bytes, None

    @staticmethod
    def _extract_logo_bytes(logo_result):
        if isinstance(logo_result, tuple) and logo_result:
            return logo_result[0]
        return logo_result

    def resolve_or_fetch_logo(self, provider, airline_iata: str | None, airline_icao: str | None):
        """Return cached/saved logo path or None when unavailable."""
        cached = self._cached_logo_path(airline_iata, airline_icao)
        if cached:
            return str(cached)
        if not self.save_logo_dir:
            return None

        logo_result = provider.get_airline_logo(airline_iata, airline_icao)
        logo_bytes = self._extract_logo_bytes(logo_result)
        if not logo_bytes:
            return None

        try:
            resized_bytes, resized_ext = self._resize_logo_bytes(
                logo_bytes,
                target_w=64,
                target_h=20,
                bg=self.bg_color,
                sharpen=True,
                autocontrast=True,
                flatten_bg=True,
            )
            to_save = resized_bytes if resized_bytes and resized_ext else logo_bytes
        except Exception:
            to_save = logo_bytes

        file_name = f"{self._safe_base_name(airline_iata, airline_icao)}.png"
        file_path = self.save_logo_dir / file_name
        with open(file_path, "wb") as fh:
            fh.write(to_save)
        return str(file_path)

