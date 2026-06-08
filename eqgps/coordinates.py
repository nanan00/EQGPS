from __future__ import annotations

from dataclasses import dataclass

from .parser import Loc


@dataclass(frozen=True)
class MapPoint:
    x: float
    y: float


def loc_to_map_point(loc: Loc) -> MapPoint:
    """Convert EQ /loc output to EQGPS map/world coordinates.

    EQ log output is effectively Y, X, Z for map purposes, and the second
    value decreases when the player moves east. EQGPS renders map X increasing
    to the right/east, so map_x is the negated second /loc value and map_y is
    the first /loc value.
    """
    return MapPoint(x=-loc.y, y=loc.x)


def raw_map_file_xy_to_map_point(raw_x: float, raw_y: float) -> MapPoint:
    """Convert raw EQ map .txt X/Y coordinates to EQGPS map/world coordinates.

    Keep map-file geometry's raw X axis, but invert raw Y for drawing. The
    player `/loc` values still need the separate loc_to_map_point transform.
    East Commonlands testing showed the raw map orientation is vertically
    mirrored in EQGPS without this top/bottom flip.
    """
    return MapPoint(x=raw_x, y=-raw_y)


def map_point_to_loc_xy(point: MapPoint | tuple[float, float]) -> tuple[float, float]:
    """Convert map/world coordinates back to the first two displayed /loc values."""
    if isinstance(point, MapPoint):
        x, y = point.x, point.y
    else:
        x, y = point
    return y, -x
