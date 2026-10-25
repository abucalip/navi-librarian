"""Capabilities, SSE framing and the owned-only search stream (contract sections 3.1, 3.6 to 3.8)."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator, Sequence
from typing import Any

from discovery.search.index import (
    STATE_FRESH,
    STATE_STALE,
    IndexView,
)
from discovery.search.query import OWNED_TYPES, SEARCH_TYPES, search_owned

SOURCE_ORDER = ("navidrome", "musicbrainz", "lastfm", "listenbrainz", "discogs")
NOT_IN_BUILD = "not_in_this_build"


def availability(available: bool, reason: str | None = None) -> dict[str, Any]:
    """Availability object (contract section 3.8). ``reason`` is null when available."""
    return {"available": available, "reason": None if available else reason}


def sse(event: str, payload: dict[str, Any]) -> str:
    """Encode one Server-Sent Event. The payload is a single JSON line."""
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def owned_index_capability(view: IndexView) -> dict[str, Any]:
    """The ``owned_index`` capability: availability, reason and state."""
    available = view.state in (STATE_FRESH, STATE_STALE)
    return {**availability(available, view.reason), "state": view.state}


def source_capabilities() -> dict[str, Any]:
    """All five sources in contract order. Only Navidrome participates in P1."""
    return {
        name: availability(True) if name == "navidrome" else availability(False, NOT_IN_BUILD)
        for name in SOURCE_ORDER
    }


def owned_type_available(view: IndexView) -> bool:
    return view.state in (STATE_FRESH, STATE_STALE)


def search_capabilities(view: IndexView) -> dict[str, Any]:
    owned_ok = owned_type_available(view)
    types = {}
    for kind in OWNED_TYPES:
        types[kind] = availability(owned_ok, view.reason)
    types["genre"] = availability(False, NOT_IN_BUILD)
    return {
        "types": types,
        "sources": source_capabilities(),
        "owned_index": owned_index_capability(view),
    }


def search_partial(view: IndexView, types: Sequence[str]) -> bool:
    """``partial`` for a search stream with no network sources (contract section 3.8)."""
    return not owned_type_available(view) and any(t in OWNED_TYPES for t in types)


def search_events(
    view: IndexView,
    *,
    query: str,
    types: Sequence[str],
    limit: int,
    elapsed_ms: Callable[[], int],
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield ``(event, payload)`` pairs for one search, in contract order.

    ``capabilities`` comes first, owned ``result`` events come next, and exactly one
    ``done`` ends a normal stream. A failure while reading the index yields one
    ``error`` event and nothing after it (invariant 4).
    """
    ordered = [t for t in SEARCH_TYPES if t in types]
    yield "capabilities", search_capabilities(view)
    try:
        if owned_type_available(view):
            owned_requested = [t for t in ordered if t in OWNED_TYPES]
            found = search_owned(view.data, query, owned_requested, limit)
            for kind in owned_requested:
                for result in found.get(kind, []):
                    yield "result", result
    except Exception:
        yield "error", {"code": "stream_failed", "message": "Owned index read failed."}
        return
    yield "done", {
        "elapsed_ms": elapsed_ms(),
        "deadline_hit": False,
        "partial": search_partial(view, ordered),
    }
