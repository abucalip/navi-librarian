"""Aggregate per-run provider-call counters and stage timers.

Only host-level and call-type totals and stage durations are kept. No identities,
URLs, or exception messages are recorded.
"""

from __future__ import annotations

import threading
import time
from collections import Counter
from contextlib import contextmanager
from typing import Iterator

_lock = threading.Lock()
_calls: Counter[str] = Counter()
_stage_seconds: Counter[str] = Counter()


def record_provider_call(provider: str, call_type: str) -> None:
    """Count one outbound provider request by provider and call type."""
    with _lock:
        _calls[f"{provider}.{call_type}"] += 1


@contextmanager
def stage_timer(stage: str) -> Iterator[None]:
    """Accumulate wall-clock seconds spent in a named stage."""
    started = time.monotonic()
    try:
        yield
    finally:
        elapsed = time.monotonic() - started
        with _lock:
            _stage_seconds[stage] += elapsed


def snapshot_and_reset() -> dict[str, dict[str, object]]:
    """Return aggregate counters for one run and clear them."""
    with _lock:
        result = {
            "provider_calls": {key: int(value) for key, value in sorted(_calls.items())},
            "stage_seconds": {
                key: round(value, 3) for key, value in sorted(_stage_seconds.items())
            },
        }
        _calls.clear()
        _stage_seconds.clear()
    return result


def timed_stage(stage: str):
    """Decorator that accumulates a function's wall time under a stage name."""

    def decorate(function):
        import functools

        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            with stage_timer(stage):
                return function(*args, **kwargs)

        return wrapper

    return decorate
