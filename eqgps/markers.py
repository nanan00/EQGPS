from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import time
import uuid
from typing import Any

DEFAULT_TIMER_MINUTES = 18
DEFAULT_TIMER_SECONDS = DEFAULT_TIMER_MINUTES * 60
MIN_TIMER_MINUTES = 1
MAX_TIMER_MINUTES = 999
MIN_TIMER_SECONDS = 1
MAX_TIMER_SECONDS = MAX_TIMER_MINUTES * 60 + 59


def _safe_optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_timer_minutes(value: object, default: int = DEFAULT_TIMER_MINUTES) -> int:
    try:
        if value is None:
            return default
        text = str(value).strip()
        if not text:
            return default
        minutes = int(round(float(text)))
    except (TypeError, ValueError):
        return default
    return max(MIN_TIMER_MINUTES, min(MAX_TIMER_MINUTES, minutes))


def _clamp_timer_seconds(seconds: int) -> int:
    return max(MIN_TIMER_SECONDS, min(MAX_TIMER_SECONDS, seconds))


def normalize_timer_seconds(value: object, default: int = DEFAULT_TIMER_SECONDS) -> int:
    try:
        if value is None:
            return default
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return _clamp_timer_seconds(int(round(value)))
        text = str(value).strip()
        if not text:
            return default
        if ":" in text:
            parts = text.split(":")
            if len(parts) != 2:
                return default
            minutes_text, seconds_text = parts
            minutes_text = minutes_text.strip() or "0"
            minutes = int(minutes_text)
            seconds = int(seconds_text.strip())
            if minutes < 0 or seconds < 0 or seconds > 59:
                return default
            total_seconds = minutes * 60 + seconds
        else:
            # Preserve the old minute-based UX for plain numeric input: "18" is
            # still an 18-minute timer, while mm:ss unlocks second precision.
            total_seconds = int(round(float(text) * 60))
    except (TypeError, ValueError):
        return default
    return _clamp_timer_seconds(total_seconds)


def format_timer_duration(seconds: object) -> str:
    try:
        duration = _clamp_timer_seconds(int(seconds))
    except (TypeError, ValueError):
        duration = DEFAULT_TIMER_SECONDS
    minutes, remainder = divmod(duration, 60)
    return f"{minutes:02d}:{remainder:02d}"


def marker_timer_duration_seconds(marker: "Marker") -> int | None:
    if marker.timer_seconds is not None:
        return _clamp_timer_seconds(marker.timer_seconds)
    if marker.timer_minutes is not None:
        return normalize_timer_minutes(marker.timer_minutes) * 60
    return None


def _remember_timer_duration(marker: "Marker", seconds: int) -> None:
    marker.timer_seconds = seconds
    # Keep the legacy minute field populated for older settings/exports while
    # using timer_seconds as the precise mm:ss source of truth.
    marker.timer_minutes = max(MIN_TIMER_MINUTES, min(MAX_TIMER_MINUTES, int(math.ceil(seconds / 60))))


def reset_marker_timer(
    marker: "Marker",
    minutes: object | None = None,
    now: float | None = None,
    seconds: object | None = None,
) -> None:
    default_seconds = marker_timer_duration_seconds(marker) or DEFAULT_TIMER_SECONDS
    if seconds is not None:
        duration_seconds = normalize_timer_seconds(seconds, default=default_seconds)
    else:
        duration_seconds = normalize_timer_minutes(minutes, default=math.ceil(default_seconds / 60)) * 60
    _remember_timer_duration(marker, duration_seconds)
    marker.timer_started_at = time.time() if now is None else now


def reset_marker_timer_paused(marker: "Marker", minutes: object | None = None, seconds: object | None = None) -> None:
    default_seconds = marker_timer_duration_seconds(marker) or DEFAULT_TIMER_SECONDS
    if seconds is not None:
        duration_seconds = normalize_timer_seconds(seconds, default=default_seconds)
    else:
        duration_seconds = normalize_timer_minutes(minutes, default=math.ceil(default_seconds / 60)) * 60
    _remember_timer_duration(marker, duration_seconds)
    marker.timer_started_at = None


def clear_marker_timer(marker: "Marker") -> None:
    marker.timer_minutes = None
    marker.timer_seconds = None
    marker.timer_started_at = None


def _is_valid_hex_color(value: str) -> bool:
    text = value.strip()
    if not text.startswith("#") or len(text) not in (4, 7):
        return False
    return all(ch in "0123456789abcdefABCDEF" for ch in text[1:])


def normalize_marker_color(value: object, default: str = "#ffcc00") -> str:
    if isinstance(value, str) and _is_valid_hex_color(value):
        return value.strip()
    return default


def update_marker_details(
    marker: "Marker",
    label: str,
    category: str,
    notes: str,
    color: str | None = None,
) -> None:
    marker.label = label.strip() or marker.label
    marker.category = category.strip() or "Custom"
    marker.notes = notes.strip()
    if color is not None:
        marker.color = normalize_marker_color(color, default=marker.color)


@dataclass
class Marker:
    zone_key: str
    x: float
    y: float
    label: str
    category: str = "Custom"
    notes: str = ""
    color: str = "#ffcc00"
    timer_minutes: int | None = None
    timer_seconds: int | None = None
    timer_started_at: float | None = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Marker":
        # Marker positions are required for useful map display. Let malformed
        # coordinates raise so MarkerStore can skip only the bad record instead
        # of failing the entire persisted marker database.
        x = float(data.get("x", 0.0))
        y = float(data.get("y", 0.0))
        return cls(
            id=str(data.get("id") or uuid.uuid4().hex),
            zone_key=str(data.get("zone_key", "")),
            x=x,
            y=y,
            label=str(data.get("label", "Marker")),
            category=str(data.get("category", "Custom")),
            notes=str(data.get("notes", "")),
            color=normalize_marker_color(data.get("color", "#ffcc00")),
            timer_minutes=_safe_optional_int(data.get("timer_minutes")),
            timer_seconds=_safe_optional_int(data.get("timer_seconds")),
            timer_started_at=_safe_optional_float(data.get("timer_started_at")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MarkerStore:
    def __init__(self, markers: list[Marker] | None = None, active_waypoint_id: str | None = None) -> None:
        self.markers = markers or []
        self.active_waypoint_id = active_waypoint_id

    def add(self, marker: Marker) -> Marker:
        self.markers.append(marker)
        return marker

    def remove(self, marker_id: str) -> None:
        self.markers = [marker for marker in self.markers if marker.id != marker_id]
        if self.active_waypoint_id == marker_id:
            self.active_waypoint_id = None

    def get(self, marker_id: str) -> Marker | None:
        for marker in self.markers:
            if marker.id == marker_id:
                return marker
        return None

    def for_zone(self, zone_key: str | None) -> list[Marker]:
        if not zone_key:
            return []
        return [marker for marker in self.markers if marker.zone_key == zone_key]

    def search(self, zone_key: str | None, query: str = "", category: str | None = None) -> list[Marker]:
        markers = self.for_zone(zone_key)
        normalized_query = " ".join(query.lower().split())
        normalized_category = category.lower() if category else None
        results: list[Marker] = []
        for marker in markers:
            if normalized_category and marker.category.lower() != normalized_category:
                continue
            haystack = f"{marker.label} {marker.category} {marker.notes}".lower()
            if normalized_query and normalized_query not in haystack:
                continue
            results.append(marker)
        return results

    def categories_for_zone(self, zone_key: str | None) -> list[str]:
        return sorted({marker.category for marker in self.for_zone(zone_key) if marker.category})

    def merge_import(self, incoming: "MarkerStore") -> None:
        incoming_ids = {marker.id for marker in incoming.markers}
        self.markers = [marker for marker in self.markers if marker.id not in incoming_ids]
        self.markers.extend(incoming.markers)
        if self.active_waypoint_id and not self.get(self.active_waypoint_id):
            self.active_waypoint_id = None

    def set_waypoint(self, marker_id: str | None) -> None:
        self.active_waypoint_id = marker_id if marker_id and self.get(marker_id) else None

    def active_waypoint(self) -> Marker | None:
        if not self.active_waypoint_id:
            return None
        return self.get(self.active_waypoint_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "markers": [marker.to_dict() for marker in self.markers],
            "active_waypoint_id": self.active_waypoint_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "MarkerStore":
        if not data:
            return cls()
        markers: list[Marker] = []
        for item in data.get("markers", []):
            if not isinstance(item, dict):
                continue
            try:
                markers.append(Marker.from_dict(item))
            except (TypeError, ValueError):
                continue
        active_waypoint_id = data.get("active_waypoint_id")
        store = cls(markers=markers, active_waypoint_id=str(active_waypoint_id) if active_waypoint_id else None)
        if store.active_waypoint_id and not store.get(store.active_waypoint_id):
            store.active_waypoint_id = None
        return store


def marker_timer_state(marker: Marker, now: float | None = None) -> str | None:
    duration_seconds = marker_timer_duration_seconds(marker)
    if duration_seconds is None or marker.timer_started_at is None:
        return None
    now = time.time() if now is None else now
    remaining = duration_seconds - (now - marker.timer_started_at)
    if remaining <= 0:
        return "READY"
    minutes = int(remaining // 60)
    seconds = int(remaining % 60)
    return f"{minutes:02d}:{seconds:02d}"
