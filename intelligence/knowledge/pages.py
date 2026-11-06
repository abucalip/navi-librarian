"""Person and label pages, read from the store only (Phase 4 items 3 and 4).

Built on the :class:`KnowledgeReader` walk like the album dossier: every credit carries its source,
evidence class and match quality, and an inferred or unmatched edge never appears (``credits_only``).
Nothing is inferred and no provider is called.

A person page lists the albums the person is credited on, split into the albums in the library and
those that are not, each with the roles and the reason it is listed ("credited as trumpet on So
What"). A recording credit is lifted to the albums that recording appears on and shown against the
release group when one is linked, so editions of one album are one row. A label page lists the same
way for releases the label published, plus related labels (parent and sub-labels) as MusicBrainz
states them. "Notable" is not loaded, so the not-in-library list is everything the slice holds for
the label, bounded, never ranked as important. Absence is reported as ``coverage`` and
``not_loaded``, never as a fact about the person or label.
"""
from __future__ import annotations

from typing import Any

from ..editions.grouping import REL_APPEARS_ON
from ..editions.release_groups import REL_MEMBER_OF
from ..graph import Limits
from ..store import repositories as repo

PERSON_TYPES = ("artist", "person", "group")
ALBUM_TYPES = ("release", "release_group")
PERSON_NOT_LOADED = ("instrument_per_track_for_unlinked_recordings",)
LABEL_NOT_LOADED = ("notable_releases", "catalogue_numbers")


def person_page(reader, entity: dict[str, Any], *, limit: int = 200) -> dict[str, Any]:
    """The page for an artist, person or group entity; ``reader`` is a KnowledgeReader."""
    if entity["type"] not in PERSON_TYPES:
        raise ValueError("a person page needs an artist, person or group entity")
    db = reader._db
    walk = reader.connections(entity["id"], credits_only=True, limits=Limits(max_depth=1, max_rows=limit, page_size=limit))
    albums: dict[int, dict[str, Any]] = {}
    people: dict[int, dict[str, Any]] = {}
    for hop in walk["hops"]:
        other = hop["entity"]
        if other["type"] in PERSON_TYPES:
            people[other["id"]] = {"entity": other, "relations": _relations(hop)}
            continue
        if other["type"] == "recording":
            targets = [(e, other["canonical_name"]) for e in _releases_of(db, other["id"])]
        elif other["type"] in ALBUM_TYPES:
            targets = [(repo.get_entity(db, other["id"]), None)]
        else:
            continue
        for target, track in targets:
            if target is None:
                continue
            album = _album_for(db, target)
            row = albums.setdefault(album["id"], {"album": album, "owned": _owned(db, album), "credits": []})
            for ev in hop["evidence"]:
                credit = {"relation": ev["relation"], "role": ev["role"], "track": track,
                          "source": ev["source"], "source_url": ev["source_url"],
                          "evidence_class": ev["evidence_class"], "match_quality": ev["match_quality"]}
                if credit not in row["credits"]:
                    row["credits"].append(credit)
    for row in albums.values():
        row["why"] = _why(entity, row["credits"])
    rows = _ordered(albums.values(), key=lambda r: r["album"])
    status = reader.slice_status()
    return {
        "person": entity,
        "aliases": [{"alias": a, "kind": k} for a, k in repo.aliases(db, entity["id"])],
        "in_library": [r for r in rows if r["owned"]],
        "not_in_library": [r for r in rows if not r["owned"]],
        "related_people": _ordered(people.values(), key=lambda r: r["entity"]),
        "truncated": walk["truncated"] is not None or walk["next_cursor"] is not None,
        "sources": {"musicbrainz_dump": {"coverage": _coverage(status, bool(albums or people)),
                                         "dump_timestamp": status["dump_timestamp"]}},
        "not_loaded": list(PERSON_NOT_LOADED),
    }


def label_page(reader, entity: dict[str, Any], *, limit: int = 200) -> dict[str, Any]:
    """The page for a label entity: aliases, related labels, owned catalogue and the rest of the slice."""
    if entity["type"] != "label":
        raise ValueError("a label page needs a label entity")
    db = reader._db
    walk = reader.connections(entity["id"], credits_only=True, limits=Limits(max_depth=1, max_rows=limit, page_size=limit))
    albums: dict[int, dict[str, Any]] = {}
    labels: dict[int, dict[str, Any]] = {}
    for hop in walk["hops"]:
        other = hop["entity"]
        if other["type"] == "label":
            labels[other["id"]] = {"entity": other, "relations": _relations(hop)}
        elif other["type"] in ALBUM_TYPES:
            album = _album_for(db, repo.get_entity(db, other["id"]))
            row = albums.setdefault(album["id"], {"album": album, "owned": _owned(db, album), "relations": []})
            row["relations"].extend(r for r in _relations(hop) if r not in row["relations"])
    rows = _ordered(albums.values(), key=lambda r: r["album"])
    status = reader.slice_status()
    return {
        "label": entity,
        "aliases": [{"alias": a, "kind": k} for a, k in repo.aliases(db, entity["id"])],
        "related_labels": _ordered(labels.values(), key=lambda r: r["entity"]),
        "owned_catalogue": [r for r in rows if r["owned"]],
        "not_in_library": [r for r in rows if not r["owned"]],
        "truncated": walk["truncated"] is not None or walk["next_cursor"] is not None,
        "sources": {"musicbrainz_dump": {"coverage": _coverage(status, bool(albums or labels)),
                                         "dump_timestamp": status["dump_timestamp"]}},
        "not_loaded": list(LABEL_NOT_LOADED),
    }


# ---------------------------------------------------------------- helpers
def _coverage(status: dict[str, Any], any_rows: bool) -> str:
    if not status["loaded"]:
        return "pending"
    return "loaded" if any_rows else "no_relationships_in_slice"


def _relations(hop: dict[str, Any]) -> list[dict[str, Any]]:
    seen: list[dict[str, Any]] = []
    for ev in hop["evidence"]:
        rel = {"relation": ev["relation"], "role": ev["role"], "direction": ev["direction"], "source": ev["source"],
               "source_url": ev["source_url"], "evidence_class": ev["evidence_class"],
               "match_quality": ev["match_quality"], "valid_from": ev["valid_from"], "valid_to": ev["valid_to"]}
        if rel not in seen:
            seen.append(rel)
    return seen


def _releases_of(db, recording_id: int) -> list[dict[str, Any]]:
    rows = (repo.get_entity(db, e["to_id"]) for e in repo.edges_from(db, recording_id, REL_APPEARS_ON))
    return [r for r in rows if r is not None]


def _album_for(db, entity: dict[str, Any]) -> dict[str, Any]:
    """The release group of a release when linked, so editions of one album are one row."""
    if entity["type"] == "release":
        link = next(iter(repo.edges_from(db, entity["id"], REL_MEMBER_OF)), None)
        group = repo.get_entity(db, link["to_id"]) if link else None
        if group is not None:
            return _brief(group)
    return _brief(entity)


def _owned(db, album: dict[str, Any]) -> bool:
    if album["owned"]:
        return True
    if album["type"] != "release_group":
        return False
    return any((repo.get_entity(db, e["from_id"]) or {}).get("owned") for e in repo.edges_to(db, album["id"], REL_MEMBER_OF))


def _brief(e: dict[str, Any]) -> dict[str, Any]:
    return {k: e.get(k) for k in ("id", "type", "mbid", "canonical_name", "owned")}


def _why(person: dict[str, Any], credits: list[dict[str, Any]]) -> str:
    parts = []
    for c in credits:
        what = c["role"] or c["relation"]
        parts.append(f"{what} on {c['track']}" if c["track"] else what)
    return f"credited as {', '.join(sorted(set(parts)))}"


def _ordered(rows, key):
    return sorted(rows, key=lambda r: ((key(r)["canonical_name"] or "").casefold(), key(r)["id"]))
