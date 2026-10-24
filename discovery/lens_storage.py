"""Storage policy for the daily lens lists (Engine 2, Phase 4, slice 3).

Pure: no I/O, no clock, no provider call. Each lens list is stored under ``lens:<name>`` in
``discovery_lists``; a build replaces a stored list only when the snapshot policy accepts it,
and the read path drops owned albums at read time. The day boundary is 4am local time: a
build made before 4am belongs to the previous day. Lens lists never touch the personal list,
the recommendation history or the cooldown. Gated by ``engine2_lens_lists_enabled`` (default
off); see docs/engine2.md (Phase 4, slice 3).
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from typing import Any

from discovery import snapshot as discovery_snapshot
from discovery.lens_lists import LENS_LIST_ORDER

LENS_STORAGE_PREFIX = "lens:"
DAY_ROLLOVER_HOURS = 4


def lens_storage_name(lens_name: str) -> str:
    """Return the ``discovery_lists`` name of a lens list."""
    return f"{LENS_STORAGE_PREFIX}{lens_name}"


def lens_name_from_storage(list_name: str) -> str | None:
    """Return the lens name for a ``lens:<name>`` list name, or None for any other name."""
    if not list_name.startswith(LENS_STORAGE_PREFIX):
        return None
    lens_name = list_name[len(LENS_STORAGE_PREFIX):]
    return lens_name if lens_name in {lens.name for lens in LENS_LIST_ORDER} else None


def lens_day(local_now: datetime) -> str:
    """Return the ISO list day for a naive local time: the date after subtracting 4 hours."""
    if local_now.tzinfo is not None:
        raise ValueError("local_now must be a naive local datetime")
    return (local_now - timedelta(hours=DAY_ROLLOVER_HOURS)).date().isoformat()


def _as_snapshot(payload: Any) -> Any:
    """Present a lens payload to the snapshot policy, which reads ``recommendations``."""
    if not isinstance(payload, Mapping):
        return payload
    return {"recommendations": payload.get("albums"), "error": payload.get("error")}


def lens_replacement_decision(
    previous: Any,
    candidate: Any,
    *,
    is_excluded: Callable[[Mapping[str, Any]], bool] | None = None,
) -> tuple[bool, str]:
    """Return ``(replace, reason)`` for one lens build against its stored list.

    Uses the snapshot policy (``discovery.snapshot.replacement_decision``): an errored, empty
    or malformed build, or one with fewer eligible albums than the stored list, keeps the
    stored list. With no stored list, a usable build is accepted.
    """
    return discovery_snapshot.replacement_decision(
        _as_snapshot(previous), _as_snapshot(candidate), is_excluded=is_excluded,
    )


def serve_lens_list(
    payload: Mapping[str, Any],
    is_excluded: Callable[[Mapping[str, Any]], bool],
    is_dismissed: Callable[[Mapping[str, Any]], bool] | None = None,
) -> tuple[dict[str, Any], dict[str, int]]:
    """Return a copy of a stored lens payload without the albums ``is_excluded`` matches.

    ``is_dismissed`` (the listener's "Not for me" feedback) is applied first and counted under
    ``dismissed``; the owned, duplicate and unidentified counts come from the rest. Kept albums
    keep their stored ``rank``. Counts are aggregate only.
    """
    albums = payload.get("albums")
    if not isinstance(albums, list):
        return dict(payload), {"kept": 0, "owned": 0, "duplicate": 0, "unidentified": 0, "dismissed": 0}
    dismissed = 0
    remaining = albums
    if is_dismissed is not None:
        remaining = []
        for album in albums:
            if isinstance(album, Mapping) and is_dismissed(album):
                dismissed += 1
            else:
                remaining.append(album)
    kept, counts = discovery_snapshot.filter_snapshot(remaining, is_excluded)
    if is_dismissed is not None:
        counts["dismissed"] = dismissed
    served = dict(payload)
    served["albums"] = kept
    return served, counts
