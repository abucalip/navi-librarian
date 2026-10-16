"""Thread-safe per-process snapshots for transfer-speed estimation."""
from __future__ import annotations

import threading
from collections.abc import Callable, Hashable, Mapping
from typing import Any


class ProgressSnapshots:
    """Keep the previous byte snapshot for each acquisition identity."""

    def __init__(self) -> None:
        self._snapshots: dict[Hashable, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def estimate(
        self,
        key: Hashable,
        file_byte_snapshot: Mapping[str, Any],
        now: float,
        estimator: Callable[[Mapping[str, Any], dict[str, Any] | None, float], Any],
    ) -> Any:
        """Store the current snapshot and estimate speed against the previous one."""
        with self._lock:
            prior = self._snapshots.get(key)
            self._snapshots[key] = {"at": now, "files": file_byte_snapshot}
            return estimator(file_byte_snapshot, prior, now)
