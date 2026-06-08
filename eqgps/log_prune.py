from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
from pathlib import Path
from typing import Callable

FOUR_MB = 4 * 1024 * 1024


@dataclass(frozen=True)
class LogPruneResult:
    pruned: bool
    archive_path: Path | None = None


def _safe_iso_timestamp(now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now()
    return now.isoformat(timespec="seconds").replace(":", "-")


def prune_archive_path(log_path: str | Path, now: dt.datetime | None = None) -> Path:
    path = Path(log_path)
    return path.with_name(f"{path.name}.{_safe_iso_timestamp(now)}")


def maybe_prune_log(log_path: str | Path, max_bytes: int = FOUR_MB, now: dt.datetime | None = None) -> LogPruneResult:
    path = Path(log_path)
    if not path.exists() or path.stat().st_size <= max_bytes:
        return LogPruneResult(pruned=False)

    archive = prune_archive_path(path, now)
    index = 2
    while archive.exists():
        archive = archive.with_name(f"{prune_archive_path(path, now).name}.{index}")
        index += 1

    data = path.read_bytes()
    archive.write_bytes(data)
    path.write_bytes(b"")
    return LogPruneResult(pruned=True, archive_path=archive)


def read_log_then_maybe_prune_log(
    log_path: str | Path,
    read_log: Callable[[], None],
    max_bytes: int = FOUR_MB,
    now: dt.datetime | None = None,
) -> LogPruneResult:
    read_log()
    return maybe_prune_log(log_path, max_bytes=max_bytes, now=now)


def scan_existing_then_maybe_prune_log(
    log_path: str | Path,
    scan_existing: Callable[[], None],
    max_bytes: int = FOUR_MB,
    now: dt.datetime | None = None,
) -> LogPruneResult:
    return read_log_then_maybe_prune_log(log_path, scan_existing, max_bytes=max_bytes, now=now)
