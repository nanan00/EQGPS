from __future__ import annotations

from dataclasses import dataclass


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class ZoneCalibration:
    offset_x: float = 0.0
    offset_y: float = 0.0

    @classmethod
    def from_dict(cls, data: dict | None) -> "ZoneCalibration":
        if not isinstance(data, dict):
            return cls()
        return cls(offset_x=_safe_float(data.get("offset_x", 0.0)), offset_y=_safe_float(data.get("offset_y", 0.0)))

    def to_dict(self) -> dict[str, float]:
        return {"offset_x": self.offset_x, "offset_y": self.offset_y}

    def nudged(self, dx: float, dy: float) -> "ZoneCalibration":
        return ZoneCalibration(self.offset_x + dx, self.offset_y + dy)


def apply_calibration_to_bounds(
    bounds: tuple[float, float, float, float] | None,
    calibration: ZoneCalibration,
) -> tuple[float, float, float, float] | None:
    if bounds is None:
        return None
    min_x, min_y, max_x, max_y = bounds
    return (
        min_x + calibration.offset_x,
        min_y + calibration.offset_y,
        max_x + calibration.offset_x,
        max_y + calibration.offset_y,
    )
