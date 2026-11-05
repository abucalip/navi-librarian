"""Job framework wrapper for Server V2 background work (docs/ServerV2.md Phase 1 item 7)."""
from .runner import (
    JobContext,
    RunResult,
    cancel,
    enqueue,
    last_good,
    list_runs,
    prune_finished,
    recover_stale,
    run_job,
    status,
)

__all__ = [
    "JobContext",
    "RunResult",
    "cancel",
    "enqueue",
    "last_good",
    "list_runs",
    "prune_finished",
    "recover_stale",
    "run_job",
    "status",
]
