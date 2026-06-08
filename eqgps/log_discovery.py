from __future__ import annotations

import time
from pathlib import Path


DEFAULT_STALE_SECONDS = 5 * 60


def discover_recent_logs(log_dir: str | Path, limit: int | None = None) -> list[Path]:
    directory = Path(log_dir)
    if not directory.exists() or not directory.is_dir():
        return []
    logs = [path for path in directory.glob("eqlog_*.txt") if path.is_file()]
    logs.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    if limit is not None:
        return logs[: max(0, int(limit))]
    return logs


def latest_active_log(log_dir: str | Path) -> Path | None:
    logs = discover_recent_logs(log_dir, limit=1)
    return logs[0] if logs else None


def is_log_stale(log_path: str | Path, now: float | None = None, stale_after_seconds: int = DEFAULT_STALE_SECONDS) -> bool:
    path = Path(log_path)
    if not path.exists():
        return True
    current_time = time.time() if now is None else float(now)
    return current_time - path.stat().st_mtime > stale_after_seconds
