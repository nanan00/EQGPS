from __future__ import annotations

from dataclasses import asdict, dataclass, field
import time
import uuid
from typing import Any

DEFAULT_TIMER_MINUTES = 18
MIN_TIMER_MINUTES = 1
MAX_TIMER_MINUTES = 999


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


def reset_marker_timer(marker: "Marker", minutes: object | None = None, now: float | None = None) -> None:
    marker.timer_minutes = normalize_timer_minutes(minutes, default=marker.timer_minutes or DEFAULT_TIMER_MINUTES)
    marker.timer_started_at = time.time() if now is None else now


def reset_marker_timer_paused(marker: "Marker", minutes: object | None = None) -> None:
    marker.timer_minutes = normalize_timer_minutes(minutes, default=marker.timer_minutes or DEFAULT_TIMER_MINUTES)
    marker.timer_started_at = None


def clear_marker_timer(marker: "Marker") -> None:
    marker.timer_minutes = None
    marker.timer_started_at = None


def update_marker_details(marker: "Marker", label: str, category: str, notes: str) -> None:
    marker.label = label.strip() or marker.label
    marker.category = category.strip() or "Custom"
    marker.notes = notes.strip()


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
            color=str(data.get("color", "#ffcc00")),
            timer_minutes=_safe_optional_int(data.get("timer_minutes")),
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
    if marker.timer_minutes is None or marker.timer_started_at is None:
        return None
    now = time.time() if now is None else now
    remaining = marker.timer_minutes * 60 - (now - marker.timer_started_at)
    if remaining <= 0:
        return "READY"
    minutes = int(remaining // 60)
    seconds = int(remaining % 60)
    return f"{minutes}:{seconds:02d}"
