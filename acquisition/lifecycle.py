"""Importable acquisition lifecycle policy and orchestration decisions.

This module intentionally contains no MCP, FastAPI, database, or filesystem imports.
Adapters own I/O and pass persisted state into these deterministic decisions.
"""
from __future__ import annotations
from typing import Any

RESUMABLE_ACQUISITION_STATUSES = frozenset({
    "downloading", "download_complete_waiting_for_folder", "monitor_error", "importing",
})
CLEANUP_REQUIRED_STATUSES = frozenset({
    "downloading", "download_complete_waiting_for_folder", "monitor_error", "importing",
    "imported", "source_switch_failed", "source_switching",
})


def should_resume_monitor(status: str, candidate: dict[str, Any], active: bool) -> bool:
    """Resume only known in-flight states with sufficient source inventory."""
    return status in RESUMABLE_ACQUISITION_STATUSES and bool(
        candidate.get("files") and candidate.get("username") and not active
    )


def cleanup_required(status: str, details: dict[str, Any]) -> bool:
    """Fail closed when state or folder metadata implies files may exist."""
    return status in CLEANUP_REQUIRED_STATUSES or bool(
        details.get("source_folder") or details.get("expected_folder")
    )


def skip_request_error(status: str | None, candidate: dict[str, Any]) -> str | None:
    """Return a stable rejection reason for invalid source-skip requests."""
    if status is None:
        return "Acquisition not found."
    if status == "dismissed":
        return "This acquisition has been dismissed."
    if status != "downloading":
        return "This acquisition is not downloading."
    if not candidate.get("fallback_candidates"):
        return "No eligible fallback source remains."
    return None


def queue_failure_action(exc: BaseException) -> str:
    """Avoid duplicate downloads after outcomes where enqueue success is uncertain."""
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status in {400, 404, 422}:
        return "retry_source"
    if status in {401, 403}:
        return "fatal"
    return "uncertain"


def normalized_candidate_files(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    """Preserve the queue payload shape for a prevalidated fallback candidate."""
    return [
        {"filename": item.get("filename"), "size": int(item.get("size") or 0)}
        for item in candidate.get("files", [])
        if item.get("filename")
    ]


def fallback_candidate_is_usable(candidate: dict[str, Any]) -> bool:
    """Require a peer name and at least one named track before attempting fallback."""
    return bool(candidate.get("username") and normalized_candidate_files(candidate))
