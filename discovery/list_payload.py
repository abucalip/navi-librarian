"""Pure cached discovery-list filtering and response projection."""
from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

from discovery.snapshot import serve_snapshot


def _owned_predicate(
    snapshot: Mapping[str, Any],
    music_key: Callable[[Any], str],
) -> Callable[[Mapping[str, Any]], bool]:
    owned = {
        (music_key(album.get("artist", "")), music_key(album.get("album", "")))
        for album in snapshot["albums"]
    }
    return lambda item: (
        music_key(item.get("artist", "")), music_key(item.get("album", ""))
    ) in owned


def build_cached_discovery_list_response(
    list_name: str,
    count: int,
    read_list: Callable[[str], dict[str, Any] | None],
    feedback: list[dict[str, Any]],
    saved: Mapping[tuple[str, str], dict[str, Any]],
    music_key: Callable[[Any], str],
    is_album_candidate: Callable[[Any], bool],
    library_snapshot: Callable[[], Mapping[str, Any]] | None = None,
    on_stale: Callable[[Mapping[str, Any]], Any] | None = None,
    acquired: set[tuple[str, str]] | None = None,
) -> str:
    """Build the legacy JSON response for a cached discovery list.

    For the personal list, ``library_snapshot`` (when given) re-checks stored items
    against the current library on every read (roadmap 3.4). If the library cannot
    be read, the stored items are served unfiltered and the diagnostics say so.
    ``on_stale`` (personal list only) is called with the stored row so a stale snapshot
    can start a background rebuild; the stored list is served regardless of its outcome.
    ``acquired`` holds (artist_key, album_key) identities already imported by the app;
    they are hidden from every list because the library snapshot lags Navidrome's rescan.
    Non-personal lists are also re-checked against the library snapshot on read.
    """
    cached = read_list(list_name)
    if not cached:
        return json.dumps({
            "list": list_name,
            "generated_at": None,
            "items": [],
            "message": "No saved list yet. Use discovery_refresh_list or wait for the daily background refresh.",
        }, ensure_ascii=False, indent=2)

    if on_stale is not None and list_name == "personal":
        try:
            on_stale(cached)
        except Exception:
            pass
    payload = cached["payload"]
    source_items = payload.get("recommendations", []) if list_name == "personal" else payload.get("items", [])
    stored_total = len(source_items)
    read_filter = None
    if list_name == "personal" and library_snapshot is not None:
        try:
            owned = _owned_predicate(library_snapshot(), music_key)
        except Exception:
            read_filter = {"ownership_checked": False}
        else:
            served_payload, counts = serve_snapshot(payload, owned)
            payload = served_payload
            source_items = payload.get("recommendations", [])
            read_filter = {"ownership_checked": True, **counts}
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
    acquired = acquired or set()
    library_owned = None
    if list_name != "personal" and library_snapshot is not None:
        try:
            library_owned = _owned_predicate(library_snapshot(), music_key)
        except Exception:
            library_owned = None
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
        if identity in acquired or (library_owned is not None and library_owned(item)):
            continue
        visible.append(item)

    result = {
        "list": list_name,
        "generated_at": cached["generated_at"],
        "total_before_feedback": stored_total,
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
        if read_filter is not None:
            result["diagnostics"]["read_filter"] = read_filter
    for key in (
        "library_artists_considered", "owned_albums_checked",
        "critical_ratings_available", "artists_with_three_or_more_owned_albums",
        "missing_albums_and_similar_artist_candidates",
    ):
        if key in payload:
            result[key] = payload[key]
    return json.dumps(result, ensure_ascii=False, indent=2)
