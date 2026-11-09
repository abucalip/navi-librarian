"""Listen-through Gaps (``album_gaps``): the Studio Crew and Guest List stops the owner has played little or never.

Owner decision, 2026-11-09 (docs/ALBUM_PATHS_PROPOSAL.md, "Open decisions resolved", item 3): play history may
*select and label* stops that already have a credit-grade reason. It never adds a stop, never reorders stops
by affinity, and never feeds recommendation ranking.

How that is kept:

* The stops come from :func:`album_paths.build_album_path` for ``album_crew`` and ``album_guests`` (the base
  paths read no play data at all). A stop appears here only if a base path produced it; its ``reasons[]`` are the
  base path's, merged, and nothing is added to them.
* Order is the base order: crew stops first, then guest-only stops, each in the base path's own order. Play
  counts are never a sort key. The filter is a yes/no test (:data:`LITTLE_PLAYS`), not a score.
* The play label sits in its own ``play`` field, not in ``reasons[]``, so a reason always means a credit.
* Thin or unavailable history returns every base stop unfiltered with ``history.state`` ``thin`` or
  ``unavailable`` and ``play: null`` on each stop, never an empty "unplayed" claim. Same when the state is
  adequate but one album has no play record: that album is left out and counted in ``history.unknown``,
  since an absent record is not evidence of "never played".

Pure over the store and the play records the caller passes in; no write, no provider call.
"""
from __future__ import annotations

import sqlite3
import time
from dataclasses import replace
from typing import Any, Callable, Iterable, Mapping

from ..insights.forgotten_gems import PlayRecord
from ..store import generations
from ..store import repositories as repo
from . import album_paths
from .paths import PathLimits, _Names

GAPS_KIND = "album_gaps"
SOURCE_KINDS = ("album_crew", "album_guests")
LITTLE_PLAYS = 2      # fewer plays than this (0 or 1) counts as "played little or never"
MIN_PLAYED_ALBUMS = 20  # albums with any play before the history is treated as usable (as Forgotten Gems)
SOURCE_STOP_CAP = 500   # base stops read before filtering, so the base path's own cap cannot hide a gap


def _label(plays: int) -> dict[str, Any]:
    state = "never" if plays == 0 else "little"
    return {"state": state, "play_count": plays, "text": "Not played" if plays == 0 else f"Played {plays} time"}


def build_gaps_path(db: sqlite3.Connection, start_id: int, records: Iterable[PlayRecord] | None, *,
                    limits: PathLimits = PathLimits(), generation: int | None = None,
                    clock: Callable[[], float] = time.monotonic) -> dict[str, Any] | None:
    """The Listen-through Gaps path from an album; None when the start is unknown.

    ``records`` are album play records keyed ``album:<navidrome id>`` (see ``insights.runtime.album_to_record``),
    or None when the play data could not be read. Raises ``ValueError`` when the start is not a release.
    """
    gen = generation if generation is not None else generations.current_generation(db)
    wide = replace(limits, max_stops=max(limits.max_stops, SOURCE_STOP_CAP))
    bases = []
    for kind in SOURCE_KINDS:
        base = album_paths.build_album_path(db, start_id, kind, limits=wide, generation=gen, clock=clock)
        if base is None:
            return None
        bases.append(base)

    merged: dict[int, dict[str, Any]] = {}
    for base in bases:
        for stop in base["stops"]:
            sid = stop["entity"]["id"]
            if sid not in merged:
                merged[sid] = {"entity": stop["entity"], "presentation": stop["presentation"],
                               "reason_count": 0, "reasons": []}
            m = merged[sid]
            m["reason_count"] += stop["reason_count"]
            m["reasons"].extend(stop["reasons"])
    for m in merged.values():
        m["reasons"] = m["reasons"][:limits.max_reasons]

    by_key = {r.key: r for r in records or ()}
    played_albums = sum(1 for r in by_key.values() if r.play_count > 0)
    if records is None:
        state = "unavailable"
    elif played_albums < MIN_PLAYED_ALBUMS:
        state = "thin"
    else:
        state = "ok"

    unknown = 0
    stops: list[dict[str, Any]] = []
    for sid, m in merged.items():
        if state != "ok":
            stops.append({**m, "play": None})
            continue
        entity = repo.get_entity(db, sid) or {}
        rec = by_key.get(f"album:{entity.get('navidrome_id')}") if entity.get("navidrome_id") else None
        if rec is None:
            unknown += 1
        elif rec.play_count < LITTLE_PLAYS:
            stops.append({**m, "play": _label(rec.play_count)})
    filtered_out = len(merged) - len(stops) - unknown if state == "ok" else 0

    truncated = next((b["truncated"] for b in bases if b["truncated"] == "time"), None) \
        or next((b["truncated"] for b in bases if b["truncated"]), None)
    if len(stops) > limits.max_stops:
        stops, truncated = stops[:limits.max_stops], truncated or "stops"
    names = _Names(db)
    return {
        "kind": GAPS_KIND,
        "start": names.get(start_id),
        "generation": gen,
        "status": "ok" if stops else "empty",
        "stops": stops,
        "truncated": truncated,
        "overlap_dropped": sum(b["overlap_dropped"] for b in bases),
        "capped": [c for b in bases for c in b["capped"]],
        "history": {"state": state, "played_albums": played_albums if records is not None else None,
                    "filtered_out": filtered_out, "unknown": unknown, "little_plays_below": LITTLE_PLAYS,
                    "filtered": state == "ok"},
        "built_from": bases[0]["built_from"],
        "presentation_version": album_paths.PRESENTATION_VERSION,
    }
