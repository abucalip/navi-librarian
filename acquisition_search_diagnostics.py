"""Pure diagnostic shaping for slskd album-search results."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping


_AUDIO_EXTENSIONS = frozenset({
    ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".aiff", ".ape",
})


def candidate_diagnostics(candidates: Iterable[Mapping[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    """Return the stable, bounded diagnostic projection for candidate records."""
    return [
        {
            "username": item.get("username"),
            "folder": item.get("folder"),
            "file_count": item.get("file_count"),
            "unique_track_count": item.get("unique_track_count"),
            "expected_track_count": item.get("expected_track_count"),
            "quality_summary": list(item.get("quality_summary") or []),
            "clear_match": bool(item.get("clear_match")),
            "eligibility_reason": item.get("eligibility_reason"),
        }
        for item in list(candidates)[:max(0, limit)]
    ]


def count_audio_files(payload_by_peer: Mapping[str, Mapping[str, Any]]) -> int:
    """Count recognized audio files in peer responses without mutating payloads."""
    return sum(
        1
        for entry in payload_by_peer.values()
        for item in (entry.get("files") or [])
        if isinstance(item, dict)
        and Path(str(item.get("filename") or item.get("path") or "")).suffix.casefold()
        in _AUDIO_EXTENSIONS
    )


def no_match_message(
    *,
    response_count: int,
    audio_file_count: int,
    reported_response_count: int,
    reported_file_count: int,
    search_attempts: Iterable[Mapping[str, Any]],
) -> str:
    """Build the established user-facing explanation for an empty candidate set."""
    attempted_queries = " -> ".join(item["query"] for item in search_attempts)
    return (
        f"No matching album folders were found among {response_count} collected peer responses "
        f"({audio_file_count} audio files). slskd reported up to {reported_response_count} "
        f"responses and {reported_file_count} files across the search attempts. "
        "If the counts are zero, no peers answered the attempted queries; otherwise "
        "the response payloads may not have been available to Librarian. "
        f"Queries tried: {attempted_queries}."
    )
