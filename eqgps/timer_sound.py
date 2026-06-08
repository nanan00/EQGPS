from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Iterable

from .markers import Marker


DEFAULT_SOUND_NAMES = (
    "Windows Notify System Generic.wav",
    "Windows Notify.wav",
    "notify.wav",
    "chimes.wav",
    "ding.wav",
)


def default_windows_sound_path(
    system_root: str | None = None,
    exists: Callable[[str], bool] | None = None,
) -> str:
    root = system_root or os.environ.get("SystemRoot") or os.environ.get("WINDIR") or "C:/Windows"
    media_dir = Path(root) / "Media"
    exists = exists or (lambda candidate: Path(candidate).exists())
    for name in DEFAULT_SOUND_NAMES:
        candidate = str(media_dir / name).replace("\\", "/")
        if exists(candidate):
            return candidate
    return str(media_dir / DEFAULT_SOUND_NAMES[0]).replace("\\", "/")


class TimerSoundNotifier:
    def __init__(self) -> None:
        self._ready_tokens: dict[str, float] = {}

    def ready_marker_ids(self, markers: Iterable[Marker], now: float) -> list[str]:
        ready: list[str] = []
        active_ids: set[str] = set()
        for marker in markers:
            if marker.timer_minutes is None or marker.timer_started_at is None:
                self._ready_tokens.pop(marker.id, None)
                continue
            active_ids.add(marker.id)
            ready_at = marker.timer_started_at + marker.timer_minutes * 60
            token = marker.timer_started_at
            if now < ready_at:
                if self._ready_tokens.get(marker.id) != token:
                    self._ready_tokens.pop(marker.id, None)
                continue
            if self._ready_tokens.get(marker.id) == token:
                continue
            self._ready_tokens[marker.id] = token
            ready.append(marker.id)
        for marker_id in list(self._ready_tokens):
            if marker_id not in active_ids:
                self._ready_tokens.pop(marker_id, None)
        return ready
