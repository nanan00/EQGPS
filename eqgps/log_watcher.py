from __future__ import annotations

from pathlib import Path
from typing import Callable

from .parser import (
    Loc,
    is_character_who_line,
    parse_loc_line,
    parse_player_name_from_log_path,
    parse_sense_heading_line,
    parse_who_zone_count_line,
    parse_zone_line,
)


class LogTailer:
    def __init__(
        self,
        path: str | Path,
        on_zone: Callable[[str], None],
        on_loc: Callable[[Loc], None],
        on_sense_heading: Callable[[str], None] | None = None,
    ) -> None:
        self.path = Path(path)
        self.character_name = parse_player_name_from_log_path(self.path)
        self.on_zone = on_zone
        self.on_loc = on_loc
        self.on_sense_heading = on_sense_heading
        self.offset = 0
        self._pending_character_who_line = False

    def set_path(self, path: str | Path) -> None:
        self.path = Path(path)
        self.character_name = parse_player_name_from_log_path(self.path)
        self.offset = 0
        self._pending_character_who_line = False

    def scan_existing(self) -> None:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                self.process_line(line)
            self.offset = handle.tell()

    def poll_new_lines(self) -> None:
        if not self.path.exists():
            return
        size = self.path.stat().st_size
        if size < self.offset:
            self.offset = 0
        with self.path.open("r", encoding="utf-8", errors="replace") as handle:
            handle.seek(self.offset)
            for line in handle:
                self.process_line(line)
            self.offset = handle.tell()

    def process_line(self, line: str) -> None:
        if self._pending_character_who_line:
            who_zone = parse_who_zone_count_line(line)
            self._pending_character_who_line = False
            if who_zone:
                self.on_zone(who_zone)

        if is_character_who_line(line, self.character_name):
            self._pending_character_who_line = True

        zone = parse_zone_line(line)
        if zone:
            self.on_zone(zone)
        loc = parse_loc_line(line)
        if loc:
            self.on_loc(loc)
        sense_heading = parse_sense_heading_line(line)
        if sense_heading and self.on_sense_heading:
            self.on_sense_heading(sense_heading)
