"""The timeline of one artist, person or group: albums and events in date order (Phase 7 client gate).

Read from the store only, no provider call. Albums are the ones the person page lists (credited, firmly
matched, editions folded into the release group). An album's date is the earliest date MusicBrainz
states for any of its editions; an event's date is its stated begin date. Nothing is dated from a tag
year or guessed: an item with no stated date is counted in ``undated`` and listed last, never placed.
"""
from __future__ import annotations

import json
from typing import Any

from ..editions.release_groups import REL_MEMBER_OF
from ..graph import Limits
from ..store import repositories as repo
from .context_pages import _event_facts
from .pages import PERSON_TYPES, _brief, _coverage, _life_span, _relations, person_page

NOT_LOADED = ("recording_dates",)


def timeline_page(reader, entity: dict[str, Any], *, limit: int = 200) -> dict[str, Any]:
    """Dated albums and events for a person entity; ``reader`` is a KnowledgeReader."""
    if entity["type"] not in PERSON_TYPES:
        raise ValueError("a timeline needs an artist, person or group entity")
    db = reader._db
    page = person_page(reader, entity, limit=limit)
    items = []
    for row in page["in_library"] + page["not_in_library"]:
        album = row["album"]
        items.append({"kind": "album", "entity": _brief(album), "owned": row["owned"], "date": _album_date(db, album),
                      "release_type": _release_type(db, album),
                      "why": row["why"], "relations": [c["relation"] for c in row["credits"]],
                      "evidence": _evidence(row["credits"])})
    walk = reader.connections(entity["id"], credits_only=True, limits=Limits(max_depth=1, max_rows=limit, page_size=limit))
    for hop in walk["hops"]:
        if hop["entity"]["type"] != "event":
            continue
        facts = _event_facts(db, hop["entity"]["id"]) or {}
        rels = _relations(hop)
        items.append({"kind": "event", "entity": _brief(hop["entity"]), "owned": False, "date": facts.get("begin"),
                      "event_kind": facts.get("kind"), "cancelled": facts.get("cancelled", False),
                      "why": ", ".join(sorted({r["role"] or r["relation"] for r in rels})),
                      "relations": [r["relation"] for r in rels], "evidence": _evidence(rels)})
    dated = sorted((i for i in items if i["date"]), key=lambda i: (i["date"], i["entity"]["canonical_name"] or "", i["entity"]["id"]))
    undated = sorted((i for i in items if not i["date"]), key=lambda i: ((i["entity"]["canonical_name"] or "").casefold(), i["entity"]["id"]))
    status = reader.slice_status()
    return {
        "person": entity,
        "life_span": _life_span(db, entity["id"]),
        "items": dated + undated,
        "undated": len(undated),
        "truncated": page["truncated"] or walk["truncated"] is not None or walk["next_cursor"] is not None,
        "sources": {"musicbrainz_dump": {"coverage": _coverage(status, bool(items)),
                                         "dump_timestamp": status["dump_timestamp"]}},
        "not_loaded": list(NOT_LOADED),
    }


def _release_type(db, album: dict[str, Any]) -> dict[str, Any] | None:
    """MusicBrainz primary and secondary type of the album's release group, or None when none is stored."""
    ids = [album["id"]]
    if album["type"] != "release_group":
        ids = [e["to_id"] for e in repo.edges_from(db, album["id"], REL_MEMBER_OF)]
    for entity_id in ids:
        row = db.execute("SELECT primary_type, secondary_types FROM release_group_facts WHERE entity_id = ?", (entity_id,)).fetchone()
        if row and (row["primary_type"] or row["secondary_types"] != "[]"):
            return {"primary": row["primary_type"], "secondary": json.loads(row["secondary_types"] or "[]")}
    return None


def _album_date(db, album: dict[str, Any]) -> str | None:
    """Earliest stated date of the album or of any edition in its release group (partial dates compare as text)."""
    ids = [album["id"]]
    if album["type"] == "release_group":
        ids += [e["from_id"] for e in repo.edges_to(db, album["id"], REL_MEMBER_OF)]
    marks = ",".join("?" * len(ids))
    row = db.execute(f"SELECT MIN(date) FROM release_facts WHERE date IS NOT NULL AND date != '' AND entity_id IN ({marks})", ids).fetchone()
    return row[0] if row and row[0] else None


def _evidence(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        ev = {k: r.get(k) for k in ("source", "evidence_class", "match_quality")}
        if ev not in out:
            out.append(ev)
    return out
