from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .log_prune import LogPruneResult


@dataclass(frozen=True)
class LogReadPruneOutcome:
    prune_result: LogPruneResult | None = None
    read_error: OSError | None = None
    prune_error: OSError | None = None

    @property
    def succeeded(self) -> bool:
        return self.read_error is None and self.prune_error is None

    def status_text(self, operation: str) -> str | None:
        if self.read_error is not None:
            return f"Log {operation} skipped: {self.read_error}"
        if self.prune_error is not None:
            return f"Log prune skipped: {self.prune_error}"
        return None


def read_then_prune_safely(
    read_log: Callable[[], None],
    prune_log: Callable[[], LogPruneResult],
) -> LogReadPruneOutcome:
    try:
        read_log()
    except OSError as exc:
        return LogReadPruneOutcome(read_error=exc)

    try:
        prune_result = prune_log()
    except OSError as exc:
        return LogReadPruneOutcome(prune_error=exc)

    return LogReadPruneOutcome(prune_result=prune_result)
