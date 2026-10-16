"""Pure normalization for a user-reviewed slskd candidate before queueing."""
from __future__ import annotations

import json
from typing import Any


def normalize_reviewed_candidate_files(
    files: Any,
    quality_summary_json: str = "[]",
) -> tuple[list[dict[str, Any]] | None, list[Any], str | None]:
    """Validate the reviewed file list and normalize its queue payload.

    The caller retains JSON error mapping, slskd I/O, and watcher startup.
    Conversion errors such as a malformed size intentionally propagate so the
    compatibility adapter can preserve its existing error response.
    """
    if not isinstance(files, list) or not files:
        return None, [], "files_json must be a non-empty JSON list."

    try:
        quality_summary = json.loads(quality_summary_json or "[]")
        if not isinstance(quality_summary, list):
            quality_summary = []
    except (ValueError, TypeError):
        quality_summary = []

    normalized = []
    for item in files:
        if not isinstance(item, dict) or not item.get("filename"):
            return None, quality_summary, "Each file requires a filename."
        normalized.append({
            "filename": str(item["filename"]),
            "size": int(item.get("size") or 0),
        })
    return normalized, quality_summary, None
