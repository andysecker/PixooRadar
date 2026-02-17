"""Test helper: record Pixoo drawing API calls for golden assertions."""


class RecordingPizzoo:
    def __init__(self):
        self.ops = []

    def cls(self):
        self.ops.append({"op": "cls"})

    def draw_rectangle(self, xy, width, height, color, filled=True):
        self.ops.append(
            {
                "op": "draw_rectangle",
                "xy": [int(xy[0]), int(xy[1])],
                "width": int(width),
                "height": int(height),
                "color": str(color),
                "filled": bool(filled),
            }
        )

    def draw_text(self, text, xy, font, color):
        self.ops.append(
            {
                "op": "draw_text",
                "text": str(text),
                "xy": [int(xy[0]), int(xy[1])],
                "font": str(font),
                "color": str(color),
            }
        )

    def draw_image(self, image, xy, size, resample_method=None):
        self.ops.append(
            {
                "op": "draw_image",
                "image": str(image),
                "xy": [int(xy[0]), int(xy[1])],
                "size": [int(size[0]), int(size[1])],
                "resample_method": str(resample_method),
            }
        )

    def add_frame(self):
        self.ops.append({"op": "add_frame"})

    def render(self, frame_speed):
        self.ops.append({"op": "render", "frame_speed": int(frame_speed)})

