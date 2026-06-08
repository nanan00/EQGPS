from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ViewportTransform:
    bounds: tuple[float, float, float, float]
    scale: float
    offset_x: float
    offset_y: float

    def world_to_screen(self, x: float, y: float) -> tuple[float, float]:
        min_x, _min_y, _max_x, max_y = self.bounds
        sx = (x - min_x) * self.scale + self.offset_x
        sy = (max_y - y) * self.scale + self.offset_y
        return sx, sy

    def screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        min_x, _min_y, _max_x, max_y = self.bounds
        x = ((sx - self.offset_x) / self.scale) + min_x
        y = max_y - ((sy - self.offset_y) / self.scale)
        return x, y

    @staticmethod
    def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
        return math.hypot(b[0] - a[0], b[1] - a[1])


def fit_viewport_to_bounds(
    bounds: tuple[float, float, float, float],
    canvas_width: int,
    canvas_height: int,
    padding: float = 30.0,
    min_scale: float = 0.02,
    max_scale: float = 20.0,
) -> tuple[float, float, float] | None:
    """Return scale/offsets that fit bounds into a realized canvas.

    Tk canvases report width/height of 1 before layout. Fitting against that
    unrealized size clamps to min_scale and makes the map look extremely zoomed
    out. Return None until a real canvas size exists.
    """
    if canvas_width <= padding * 2 or canvas_height <= padding * 2:
        return None
    min_x, min_y, max_x, max_y = bounds
    width = max_x - min_x or 1.0
    height = max_y - min_y or 1.0
    usable_w = max(canvas_width - padding * 2, 1.0)
    usable_h = max(canvas_height - padding * 2, 1.0)
    scale = min(usable_w / width, usable_h / height)
    scale = max(min_scale, min(scale, max_scale))
    return scale, padding, padding


def clamp_pan_units(offset_x: float, offset_y: float, scale: float, max_units: float = 10000.0) -> tuple[float, float]:
    limit = max_units * scale
    return max(-limit, min(limit, offset_x)), max(-limit, min(limit, offset_y))
