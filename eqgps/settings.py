from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

APP_NAME = "EQGPS"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG_PATH = Path(os.environ.get("PUBLIC", r"C:\Users\Public")) / "EQ_P99" / "Logs" / "eqlog_Yourcharacter_P1999Green.txt"
DEFAULT_MAP_DIR = PROJECT_ROOT / "map_files"


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def user_config_dir() -> Path:
    root = os.environ.get("APPDATA")
    if root:
        return Path(root) / APP_NAME
    return Path.home() / ".eqgps"


class Settings:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else user_config_dir() / "settings.json"
        self.data: dict[str, Any] = {}
        self._defer_save = False
        self._dirty = False
        self.load()

    def load(self) -> None:
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                # Don't silently wipe a corrupt settings file: preserve it as a
                # .corrupt backup so the user (or a future migration) can try to
                # recover markers/calibration instead of losing them outright.
                self._backup_corrupt_settings()
                self.data = {}

    def _backup_corrupt_settings(self) -> None:
        try:
            backup = self.path.with_name(self.path.name + ".corrupt")
            os.replace(self.path, backup)
        except OSError:
            pass

    def save(self) -> None:
        # When deferral is active (e.g. during a slider drag) record the change
        # in memory and let the caller flush() once the burst settles, instead
        # of rewriting the whole file dozens of times per second.
        if self._defer_save:
            self._dirty = True
            return
        self._write()

    def _write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temp file in the same directory, then atomically replace
        # the real settings file. A crash mid-write can only ever leave the
        # previous good file or the temp file behind, never a half-written
        # settings.json that load() would silently discard (losing markers,
        # calibration, and window state).
        payload = json.dumps(self.data, indent=2)
        tmp_path = self.path.with_name(self.path.name + ".tmp")
        tmp_path.write_text(payload, encoding="utf-8")
        os.replace(tmp_path, self.path)
        self._dirty = False

    def begin_deferred_save(self) -> None:
        """Suspend immediate disk writes; pair every call with flush()."""
        self._defer_save = True

    def flush(self) -> None:
        """Persist any change that was staged while deferral was active."""
        self._defer_save = False
        if self._dirty:
            self._write()

    @property
    def log_path(self) -> Path:
        value = self.data.get("last_log_path")
        return Path(value) if value else DEFAULT_LOG_PATH

    @log_path.setter
    def log_path(self, value: str | Path) -> None:
        path = Path(value)
        self.data["last_log_path"] = str(path)
        self.data["last_log_dir"] = str(path.parent)
        self.save()

    @property
    def last_log_dir(self) -> Path:
        value = self.data.get("last_log_dir")
        if value:
            return Path(value)
        return self.log_path.parent

    @property
    def map_dir(self) -> Path:
        value = self.data.get("map_dir")
        return Path(value) if value else DEFAULT_MAP_DIR

    def get_layer_settings(self, zone_key: str, layer_name: str) -> dict[str, Any]:
        layers = self.data.setdefault("layer_settings", {})
        zone = layers.setdefault(zone_key, {})
        return zone.setdefault(layer_name, {"visible": True, "opacity": 100})

    def set_layer_settings(self, zone_key: str, layer_name: str, visible: bool, opacity: int) -> None:
        layers = self.data.setdefault("layer_settings", {})
        zone = layers.setdefault(zone_key, {})
        zone[layer_name] = {"visible": bool(visible), "opacity": int(opacity)}
        self.save()

    def remember_window_geometry(self, geometry: str) -> None:
        self.data["window_geometry"] = geometry
        self.save()

    @property
    def window_geometry(self) -> str | None:
        value = self.data.get("window_geometry")
        return str(value) if value else None

    def get_marker_data(self) -> dict[str, Any]:
        markers = self.data.get("marker_store")
        if not isinstance(markers, dict):
            markers = self.data.get("markers")
        return markers if isinstance(markers, dict) else {}

    def set_marker_data(self, marker_data: dict[str, Any]) -> None:
        self.data["marker_store"] = marker_data
        self.save()

    def get_zone_calibration(self, zone_key: str | None) -> dict[str, float]:
        if not zone_key:
            return {"offset_x": 0.0, "offset_y": 0.0}
        calibrations = self.data.setdefault("zone_calibrations", {})
        entry = calibrations.get(zone_key, {}) if isinstance(calibrations, dict) else {}
        return {
            "offset_x": _safe_float(entry.get("offset_x", 0.0)) if isinstance(entry, dict) else 0.0,
            "offset_y": _safe_float(entry.get("offset_y", 0.0)) if isinstance(entry, dict) else 0.0,
        }

    def set_zone_calibration(self, zone_key: str, calibration: dict[str, float]) -> None:
        calibrations = self.data.setdefault("zone_calibrations", {})
        if not isinstance(calibrations, dict):
            calibrations = {}
            self.data["zone_calibrations"] = calibrations
        calibrations[zone_key] = {"offset_x": float(calibration.get("offset_x", 0.0)), "offset_y": float(calibration.get("offset_y", 0.0))}
        self.save()

    def get_elevation_filter(self) -> dict[str, Any]:
        data = self.data.get("elevation_filter", {})
        return data if isinstance(data, dict) else {}

    def set_elevation_filter(self, enabled: bool, above: float, below: float) -> None:
        self.data["elevation_filter"] = {"enabled": bool(enabled), "above": float(above), "below": float(below)}
        self.save()

    def get_marker_timer_minutes(self, default: int = 18) -> int:
        try:
            return max(1, int(self.data.get("marker_timer_minutes", default)))
        except (TypeError, ValueError):
            return default

    def set_marker_timer_minutes(self, minutes: int) -> None:
        self.data["marker_timer_minutes"] = max(1, int(minutes))
        self.data["marker_timer_seconds"] = self.data["marker_timer_minutes"] * 60
        self.save()

    def get_marker_timer_seconds(self, default: int = 18 * 60) -> int:
        if "marker_timer_seconds" not in self.data and "marker_timer_minutes" in self.data:
            return self.get_marker_timer_minutes(math.ceil(default / 60)) * 60
        try:
            seconds = int(self.data.get("marker_timer_seconds", default))
        except (TypeError, ValueError):
            seconds = self.get_marker_timer_minutes(math.ceil(default / 60)) * 60
        return max(1, seconds)

    def set_marker_timer_seconds(self, seconds: int) -> None:
        seconds = max(1, int(seconds))
        self.data["marker_timer_seconds"] = seconds
        self.data["marker_timer_minutes"] = max(1, int(math.ceil(seconds / 60)))
        self.save()

    def get_timer_sound_settings(self, default_path: str = "") -> dict[str, Any]:
        data = self.data.get("timer_sound", {})
        if not isinstance(data, dict):
            data = {}
        return {
            "enabled": bool(data.get("enabled", True)),
            "path": str(data.get("path") or default_path),
        }

    def set_timer_sound_settings(self, enabled: bool, path: str) -> None:
        self.data["timer_sound"] = {"enabled": bool(enabled), "path": str(path)}
        self.save()

    @property
    def always_on_top(self) -> bool:
        return bool(self.data.get("always_on_top", False))

    @always_on_top.setter
    def always_on_top(self, value: bool) -> None:
        self.data["always_on_top"] = bool(value)
        self.save()

    @property
    def mini_mode(self) -> bool:
        return bool(self.data.get("mini_mode", False))

    @mini_mode.setter
    def mini_mode(self, value: bool) -> None:
        self.data["mini_mode"] = bool(value)
        self.save()

    @property
    def transparency_mode(self) -> bool:
        return bool(self.data.get("transparency_mode", False))

    @transparency_mode.setter
    def transparency_mode(self, value: bool) -> None:
        self.data["transparency_mode"] = bool(value)
        self.save()

    @property
    def ui_chrome_opacity(self) -> int:
        try:
            opacity = int(round(float(self.data.get("ui_chrome_opacity", 100))))
        except (TypeError, ValueError):
            opacity = 100
        return max(0, min(100, opacity))

    @ui_chrome_opacity.setter
    def ui_chrome_opacity(self, value: int | float | str) -> None:
        try:
            opacity = int(round(float(value)))
        except (TypeError, ValueError):
            opacity = 100
        self.data["ui_chrome_opacity"] = max(0, min(100, opacity))
        self.save()

    @property
    def borderless_overlay_mode(self) -> bool:
        return bool(self.data.get("borderless_overlay_mode", False))

    @borderless_overlay_mode.setter
    def borderless_overlay_mode(self, value: bool) -> None:
        self.data["borderless_overlay_mode"] = bool(value)
        self.save()

    @property
    def overlay_click_through(self) -> bool:
        return bool(self.data.get("overlay_click_through", False))

    @overlay_click_through.setter
    def overlay_click_through(self, value: bool) -> None:
        self.data["overlay_click_through"] = bool(value)
        self.save()

    @property
    def overlay_lock_window(self) -> bool:
        return bool(self.data.get("overlay_lock_window", False))

    @overlay_lock_window.setter
    def overlay_lock_window(self, value: bool) -> None:
        self.data["overlay_lock_window"] = bool(value)
        self.save()
