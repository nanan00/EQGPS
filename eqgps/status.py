from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Protocol

from .calibration import ZoneCalibration
from .coordinates import loc_to_map_point, map_point_to_loc_xy
from .elevation import ElevationFilter
from .parser import Loc


class WaypointLike(Protocol):
    label: str
    x: float
    y: float


@dataclass(frozen=True)
class StatusSnapshot:
    prefix: str
    zone_name: str | None
    zone_key: str | None
    current_loc: Loc | None
    cursor_world: tuple[float, float] | None
    layer_count: int
    waypoint: WaypointLike | None
    elevation: ElevationFilter
    calibration: ZoneCalibration
    log_path: str

    @property
    def status_text(self) -> str:
        return self.prefix


def format_bottom_status(snapshot: StatusSnapshot) -> str:
    zone = snapshot.zone_name or "unknown"
    key = snapshot.zone_key or "unresolved"
    loc = _format_player_loc(snapshot.current_loc)
    cursor = "none"
    distance = "none"
    player = loc_to_map_point(snapshot.current_loc) if snapshot.current_loc else None

    if snapshot.cursor_world:
        cursor_loc_x, cursor_loc_y = map_point_to_loc_xy(snapshot.cursor_world)
        cursor = f"{cursor_loc_x:.1f}, {cursor_loc_y:.1f}"
        if player:
            distance = f"{math.hypot(snapshot.cursor_world[0] - player.x, snapshot.cursor_world[1] - player.y):.1f}"

    waypoint_text = "none"
    if snapshot.waypoint:
        waypoint_text = snapshot.waypoint.label
        if player:
            waypoint_text = f"{snapshot.waypoint.label} ({math.hypot(snapshot.waypoint.x - player.x, snapshot.waypoint.y - player.y):.1f})"

    elevation_text = "off"
    if snapshot.elevation.enabled:
        elevation_text = f"-{snapshot.elevation.below:.0f}/+{snapshot.elevation.above:.0f}"

    return (
        f"Zone: {zone} [{key}] | Player: {loc} | Cursor: {cursor} | Dist: {distance} | "
        f"Waypoint: {waypoint_text} | Layers: {snapshot.layer_count} | Elev: {elevation_text} | "
        f"Cal: {snapshot.calibration.offset_x:.0f},{snapshot.calibration.offset_y:.0f} | Log: {snapshot.log_path}"
    )


def _format_player_loc(loc: Loc | None) -> str:
    if not loc:
        return "none"
    return f"{loc.x:.2f}, {loc.y:.2f}, {loc.z:.2f}"
