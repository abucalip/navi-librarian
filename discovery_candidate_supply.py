"""Aggregate-only candidate-supply diagnostics.

Inputs may carry artist, album, and recording identities in memory, but every
function here returns counts, shares, and bounded enum labels. Nothing in this
module logs or persists an artist, album, MBID, tag, URL, or exception message.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Callable, Iterable, Mapping, Sequence

TOP_N = 5

# Exception type names that may be reported. Anything else collapses to "other"
# so that provider exception text never reaches the diagnostic record.
_BOUNDED_ERROR_CLASSES = frozenset({
    "HTTPStatusError", "TimeoutException", "ReadTimeout", "ConnectError",
    "ValueError", "KeyError", "TypeError", "AttributeError", "JSONDecodeError",
    "RuntimeError",
})


def classify_error(exc: BaseException) -> str:
    """Return a bounded error class label for a provider exception."""
    name = type(exc).__name__
    return name if name in _BOUNDED_ERROR_CLASSES else "other"


def _share(part: int, whole: int) -> float | None:
    return round(part / whole, 6) if whole else None


def _top_shares(counts: Mapping[str, int], whole: int, top_n: int) -> list[float]:
    if not whole:
        return []
    return [round(value / whole, 6) for value in sorted(counts.values(), reverse=True)[:top_n]]


def summarize_cf_recordings(
    records: Iterable[Mapping[str, Any]],
    *,
    returned: int,
    top_n: int = TOP_N,
) -> dict[str, Any]:
    """Summarize per-recording CF outcomes.

    Each record has ``resolved`` (bool), ``artist_key`` (normalized primary
    artist or None), and ``error_class`` (bounded label or None). A record
    counts as resolved only when it resolved and carries no error.
    """
    rows = list(records)
    resolved = [row for row in rows if row.get("resolved") and not row.get("error_class")]
    failed = [row for row in rows if not (row.get("resolved") and not row.get("error_class"))]
    artist_counts = Counter(str(row["artist_key"]) for row in resolved if row.get("artist_key"))
    resolved_total = len(resolved)
    top_two = sum(count for _, count in artist_counts.most_common(2))
    failure_classes = Counter(str(row.get("error_class") or "other") for row in failed)
    return {
        "cf_recordings_returned": max(0, int(returned)),
        "cf_recordings_considered": len(rows),
        "cf_recordings_resolved": resolved_total,
        "cf_recordings_failed": len(failed),
        "cf_failure_classes": dict(sorted(failure_classes.items())),
        "cf_distinct_recording_artists": len(artist_counts),
        "cf_top2_artist_recording_share": _share(top_two, resolved_total),
        "cf_top_artist_recording_shares": _top_shares(artist_counts, resolved_total, top_n),
    }


def summarize_cf_albums(
    albums: Iterable[Mapping[str, Any]],
    music_key: Callable[[Any], str],
    *,
    top_n: int = TOP_N,
) -> dict[str, Any]:
    """Summarize unique albums that ListenBrainz CF contributed, by artist share."""
    cf_albums = [
        album for album in albums
        if "listenbrainz_cf" in (album.get("discovery_sources") or [])
    ]
    per_artist = Counter(music_key(album.get("primary_artist", "")) for album in cf_albums)
    total = len(cf_albums)
    return {
        "cf_albums": total,
        "cf_album_artists": len(per_artist),
        "cf_top_artist_album_shares": _top_shares(per_artist, total, top_n),
    }


def summarize_supplementary_yield(
    outcomes: Sequence[tuple[int, str | None]],
    *,
    planned: int,
) -> dict[str, Any]:
    """Summarize supplementary tag-query yield from ``(added, error_class)`` pairs.

    Only queries that were actually attempted appear in ``outcomes``; queries
    skipped by the candidate cap are reported through ``not_attempted``.
    """
    attempted = len(outcomes)
    failed = [error for _, error in outcomes if error]
    zero_yield = sum(1 for added, error in outcomes if not error and added <= 0)
    return {
        "supplementary_queries_planned": max(0, int(planned)),
        "supplementary_queries_attempted": attempted,
        "supplementary_queries_not_attempted": max(0, int(planned) - attempted),
        "supplementary_queries_with_yield": sum(1 for added, error in outcomes if not error and added > 0),
        "supplementary_queries_zero_yield": zero_yield,
        "supplementary_queries_failed": len(failed),
        "supplementary_failure_classes": dict(sorted(Counter(failed).items())),
        "supplementary_candidates_added": sum(max(0, int(added)) for added, _ in outcomes),
    }


def summarize_candidate_stages(
    albums: Iterable[Mapping[str, Any]],
    debug_rows: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Count ownership, identity, and artist-cap stages for the candidate pool.

    ``albums`` are resolved candidate dictionaries. ``debug_rows`` are the
    per-candidate decision rows; they are joined to albums by normalized
    artist and album names. Identity follows the allocator's
    artist-identity plus normalized album-title key.
    """
    from discovery_recommendations import artist_identity, music_key

    decisions = {
        (music_key(row.get("artist", "")), music_key(row.get("album", ""))): row
        for row in debug_rows
    }
    rows = []
    for album in albums:
        title_key = music_key(album.get("album", ""))
        row = decisions.get((music_key(album.get("artist", "")), title_key), {})
        rows.append({
            "identity": (artist_identity(album), title_key),
            "artist_key": music_key(album.get("primary_artist", "")),
            "owned": bool(row.get("exact_owned")),
            "decision": str(row.get("selection_decision") or "unknown"),
        })

    unowned = [row for row in rows if not row["owned"]]
    unique_unowned = {row["identity"] for row in unowned}
    # The allocator overwrites an artist-cap rejection with "duplicate_candidate"
    # when a later phase revisits the candidate, so the cap is derived from the
    # selected set rather than from the final decision label.
    selected_identities = {row["identity"] for row in rows if row["decision"] == "selected"}
    selected_artists = {identity[0] for identity in selected_identities}
    cap_identities = {
        row["identity"] for row in unowned
        if row["identity"][0] in selected_artists and row["identity"] not in selected_identities
    }
    cap_rows = [row for row in unowned if row["identity"] in cap_identities]
    decision_counts = Counter(row["decision"] for row in rows)
    return {
        "candidates_total": len(rows),
        "owned_candidates": len(rows) - len(unowned),
        "unowned_before_dedupe": len(unowned),
        "unowned_unique_after_dedupe": len(unique_unowned),
        "duplicate_identity_rows": len(unowned) - len(unique_unowned),
        "artist_cap_rejections": len(cap_rows),
        "unowned_unique_after_artist_cap": len(unique_unowned - cap_identities),
        "distinct_artists_unowned": len({row["artist_key"] for row in unowned}),
        "selected": decision_counts.get("selected", 0),
        "decision_counts": dict(sorted(decision_counts.items())),
    }


def recording_artist_key(recording: Mapping[str, Any], music_key: Callable[[Any], str]) -> str | None:
    """Return the normalized primary artist of a MusicBrainz recording payload."""
    credit = recording.get("artist-credit", []) if isinstance(recording, Mapping) else []
    name = next(
        (part.get("name", "") for part in credit
         if isinstance(part, Mapping) and part.get("name")),
        "",
    )
    return music_key(name) if name else None


def cf_records_from_tape(
    provider_events: Iterable[Mapping[str, Any]],
    recording_mbids: Sequence[str],
    music_key: Callable[[Any], str],
) -> list[dict[str, Any]]:
    """Rebuild per-recording CF outcomes from a captured provider tape, offline.

    A recording is resolved when its cache read returned a payload, or when the
    cache write that followed a provider fetch stored one. Unresolved recordings
    are classified from the last captured HTTP status for that recording.
    """
    cache_reads: dict[str, Any] = {}
    cache_writes: dict[str, Any] = {}
    last_status: dict[str, int] = {}
    for event in provider_events:
        operation = event.get("operation")
        args = event.get("args") or []
        if operation == "http_client.get":
            url = str(event.get("request_url", ""))
            if "/ws/2/recording/" in url:
                last_status[url.rsplit("/", 1)[-1]] = event.get("status_code")
            continue
        if not args or not isinstance(args[0], str) or not args[0].startswith("mb:recording:"):
            continue
        if operation == "metadata_cache_get":
            cache_reads.setdefault(args[0], event.get("result"))
        elif operation == "metadata_cache_set" and len(args) >= 2:
            cache_writes[args[0]] = args[1]

    records = []
    for mbid in recording_mbids:
        key = f"mb:recording:{mbid}"
        recording = cache_reads.get(key)
        if not isinstance(recording, dict):
            recording = cache_writes.get(key)
        if isinstance(recording, dict):
            records.append({
                "resolved": True,
                "artist_key": recording_artist_key(recording, music_key),
                "error_class": None,
            })
            continue
        status = last_status.get(str(mbid))
        error = "HTTPStatusError" if isinstance(status, int) and status >= 400 else "other"
        records.append({"resolved": False, "artist_key": None, "error_class": error})
    return records


def summarize_supplementary_tape(provider_events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Count supplementary release-group searches captured on a tape.

    Per-query added-candidate counts are not recoverable from a v2 capture, so
    this reports attempts, cache hits, and failed searches only.
    """
    attempted = cache_hits = failed = 0
    pending = False
    pending_status: int | None = None

    def close_pending() -> None:
        nonlocal failed, pending, pending_status
        if pending and not (isinstance(pending_status, int) and pending_status < 400):
            failed += 1
        pending = False
        pending_status = None

    for event in provider_events:
        operation = event.get("operation")
        args = event.get("args") or []
        if operation == "metadata_cache_get" and args and str(args[0]).startswith("mb:release-group-search:"):
            close_pending()
            attempted += 1
            if event.get("result") is None:
                pending = True
            else:
                cache_hits += 1
        elif operation == "http_client.get" and pending and "/release-group/" in str(event.get("request_url", "")):
            pending_status = event.get("status_code")
    close_pending()
    return {
        "supplementary_queries_attempted": attempted,
        "supplementary_cache_hits": cache_hits,
        "supplementary_queries_failed": failed,
        "per_query_yield": "not recoverable from a v2 capture",
    }


def candidate_supply_report(
    payload: Mapping[str, Any],
    debug_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Aggregate supply diagnostics for one frozen capture, with no provider calls.

    ``debug_rows`` must come from a ranking run of the frozen inputs (for example
    the replay output). The capture's stored decisions predate later allocator
    changes and are not used. CF recording shares come from the captured
    MusicBrainz tape, album shares and stage counts from the frozen candidates.
    Identities stay in memory and are not returned.
    """
    from discovery_recommendations import music_key

    gathered_inputs = payload["gathered_inputs"]
    events = payload.get("provider_events", [])
    albums = [entry["value"] for entry in gathered_inputs["albums"]]
    return {
        "cf_recordings": summarize_cf_recordings(
            cf_records_from_tape(events, gathered_inputs.get("cf_recording_mbids", []), music_key),
            returned=gathered_inputs.get("cf_recordings_returned", 0),
        ),
        "cf_albums": summarize_cf_albums(albums, music_key),
        "supplementary": summarize_supplementary_tape(events),
        "stages": summarize_candidate_stages(albums, debug_rows),
        "source": "derived offline from the capture; v2 captures lack per-query supplementary yield",
    }
