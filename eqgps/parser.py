from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

ZONE_RE = re.compile(r"You have entered\s+(.+?)\.?\s*$", re.IGNORECASE)
LOC_RE = re.compile(
    r"Your Location is\s+"
    r"(-?\d+(?:\.\d+)?),\s*"
    r"(-?\d+(?:\.\d+)?),\s*"
    r"(-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
PLAYER_LOG_RE = re.compile(r"^eqlog_([^_]+)_", re.IGNORECASE)
WHO_ZONE_COUNT_RE = re.compile(
    r"There\s+(?:are\s+\d+\s+players|is\s+1\s+player)\s+in\s+(.+?)\.?\s*$",
    re.IGNORECASE,
)
SENSE_HEADING_RE = re.compile(r"You think you are heading\s+([A-Za-z ]+?)\.?\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class Loc:
    x: float
    y: float
    z: float


def parse_zone_line(line: str) -> str | None:
    """Return the entered zone name from a P99 log line, if present."""
    match = ZONE_RE.search(line.strip())
    if not match:
        return None
    return match.group(1).strip().rstrip(".").strip().strip('"\'')


def parse_loc_line(line: str) -> Loc | None:
    """Return /loc coordinates from a P99 log line, if present."""
    match = LOC_RE.search(line)
    if not match:
        return None
    x, y, z = match.groups()
    return Loc(float(x), float(y), float(z))


def parse_player_name_from_log_path(path: str | Path) -> str | None:
    """Extract the character name from an EQ log filename like eqlog_Name_Server.txt."""
    name = Path(path).name
    match = PLAYER_LOG_RE.match(name)
    if not match:
        return None
    return match.group(1).strip() or None


def is_character_who_line(line: str, character_name: str | None) -> bool:
    """Return True when a /who result row appears to describe this character."""
    if not character_name:
        return False
    escaped = re.escape(character_name)
    pattern = re.compile(rf"\[\d+\s+[^\]]+\]\s+{escaped}\s+\([^)]*\)", re.IGNORECASE)
    return bool(pattern.search(line))


def parse_who_zone_count_line(line: str) -> str | None:
    """Return zone name from the /who summary line following the character's row."""
    match = WHO_ZONE_COUNT_RE.search(line.strip())
    if not match:
        return None
    zone_name = match.group(1).strip().rstrip(".")
    if zone_name.lower() == "everquest":
        return None
    return zone_name


def parse_sense_heading_line(line: str) -> str | None:
    """Return the textual heading from a Sense Heading log line, if present."""
    match = SENSE_HEADING_RE.search(line.strip())
    if not match:
        return None
    return " ".join(word.capitalize() for word in match.group(1).split())
