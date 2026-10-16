"""Pure cached discovery-list filtering and response projection."""
from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any


def build_cached_discovery_list_response(
    list_name: str,
    count: int,
    read_list: Callable[[str], dict[str, Any] | None],
    feedback: list[dict[str, Any]],
    saved: Mapping[tuple[str, str], dict[str, Any]],
    music_key: Callable[[Any], str],
    is_album_candidate: Callable[[Any], bool],
) -> str:
    """Build the legacy JSON response for a cached discovery list."""
    cached = read_list(list_name)
    if not cached:
        return json.dumps({
            "list": list_name,
            "generated_at": None,
            "items": [],
            "message": "No saved list yet. Use discovery_refresh_list or wait for the daily background refresh.",
        }, ensure_ascii=False, indent=2)

    payload = cached["payload"]
    source_items = payload.get("recommendations", []) if list_name == "personal" else payload.get("items", [])
    dismissed_albums = {
        (row["artist_key"], row["album_key"])
        for row in feedback
        if row["scope"] == "album" and row["status"] == "not_for_me"
    }
    dismissed_artists = {
        row["artist_key"]
        for row in feedback
        if row["scope"] == "artist" and row["status"] == "not_for_me_artist"
    }
    visible = []
    for item in source_items:
        artist_key = music_key(item.get("artist", ""))
        album_key = music_key(item.get("album", ""))
        identity = (artist_key, album_key)
        if list_name != "for_me" and not is_album_candidate(item):
            continue
        if identity in dismissed_albums or artist_key in dismissed_artists:
            continue
        if identity in saved:
            continue
        visible.append(item)

    result = {
        "list": list_name,
        "generated_at": cached["generated_at"],
        "total_before_feedback": len(source_items),
        "count": min(count, len(visible)),
        "items": visible[:count],
        "source": payload.get("source"),
        "limitations": payload.get("limitations", []),
    }
    if list_name == "personal":
        result["recommendations"] = visible[:count]
        result["diagnostics"] = {
            key: payload.get(key)
            for key in (
                "source", "recent_listens_retrieved", "library_albums_indexed",
                "metadata_lookup_errors", "limitations"
            )
            if key in payload
        }
    for key in (
        "library_artists_considered", "owned_albums_checked",
        "critical_ratings_available", "artists_with_three_or_more_owned_albums",
        "missing_albums_and_similar_artist_candidates",
    ):
        if key in payload:
            result[key] = payload[key]
    return json.dumps(result, ensure_ascii=False, indent=2)
