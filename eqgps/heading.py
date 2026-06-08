from __future__ import annotations

from dataclasses import dataclass
import math

from .coordinates import MapPoint, loc_to_map_point
from .parser import Loc

SENSE_HEADING_DEGREES = {
    "East": 0.0,
    "North East": 45.0,
    "Northeast": 45.0,
    "North": 90.0,
    "North West": 135.0,
    "Northwest": 135.0,
    "West": 180.0,
    "South West": 225.0,
    "Southwest": 225.0,
    "South": 270.0,
    "South East": 315.0,
    "Southeast": 315.0,
}


@dataclass
class HeadingTracker:
    min_distance: float = 3.0
    previous_point: MapPoint | None = None
    heading_degrees: float | None = None

    def add_sample(self, loc: Loc) -> float | None:
        point = loc_to_map_point(loc)
        if self.previous_point is None:
            self.previous_point = point
            return self.heading_degrees

        dx = point.x - self.previous_point.x
        dy = point.y - self.previous_point.y
        distance = math.hypot(dx, dy)
        self.previous_point = point
        if distance >= self.min_distance:
            self.heading_degrees = math.degrees(math.atan2(dy, dx)) % 360.0
        return self.heading_degrees

    def set_sense_heading(self, heading_text: str) -> float | None:
        heading = SENSE_HEADING_DEGREES.get(heading_text)
        if heading is not None:
            self.heading_degrees = heading
        return self.heading_degrees
