from __future__ import annotations

from dataclasses import dataclass

from .map_loader import MapLabel, MapLine


def _safe_nonnegative_float(value: object, default: float) -> float:
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class ElevationFilter:
    enabled: bool = False
    above: float = 50.0
    below: float = 50.0

    @classmethod
    def from_dict(cls, data: dict | None) -> "ElevationFilter":
        if not data:
            return cls()
        return cls(
            enabled=bool(data.get("enabled", False)),
            above=_safe_nonnegative_float(data.get("above", 50.0), 50.0),
            below=_safe_nonnegative_float(data.get("below", 50.0), 50.0),
        )

    def to_dict(self) -> dict[str, float | bool]:
        return {"enabled": self.enabled, "above": self.above, "below": self.below}

    def contains(self, z: float, player_z: float | None) -> bool:
        if not self.enabled or player_z is None:
            return True
        return (player_z - self.below) <= z <= (player_z + self.above)


def line_visible_at_player_z(line: MapLine, player_z: float | None, elevation: ElevationFilter) -> bool:
    if not elevation.enabled or player_z is None:
        return True
    return elevation.contains(line.z1, player_z) or elevation.contains(line.z2, player_z)


def label_visible_at_player_z(label: MapLabel, player_z: float | None, elevation: ElevationFilter) -> bool:
    return elevation.contains(label.z, player_z)
