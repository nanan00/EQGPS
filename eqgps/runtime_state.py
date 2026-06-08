from __future__ import annotations

from dataclasses import dataclass

from .parser import Loc


@dataclass
class RuntimeState:
    current_zone_name: str | None = None
    current_zone_key: str | None = None
    current_loc: Loc | None = None

    def update_zone(self, zone_name: str, zone_key: str | None) -> None:
        if zone_name != self.current_zone_name or zone_key != self.current_zone_key:
            self.current_loc = None
        self.current_zone_name = zone_name
        self.current_zone_key = zone_key

    def update_loc(self, loc: Loc) -> None:
        self.current_loc = loc
