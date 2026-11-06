"""Place and event pages, read from the store only (Phase 5, geographic and scene context).

Built on the :class:`KnowledgeReader` walk like the other knowledge pages: every link carries its
source, evidence class and match quality, and an inferred or unmatched edge never appears
(``credits_only``). Nothing is inferred and no provider is called.

A place page gives the place's own facts (kind, coordinates, dates), the area MusicBrainz states for
it with the containment chain above that area (city, region, country, as MusicBrainz nests them),
the recordings made there with the albums they appear on, the people tied to it, and the events held
there. An event page gives its facts (kind, dates, cancelled), the places and area MusicBrainz
states, who took part, and the recordings made at it. No nationality, scene or location is derived
from a name, a label or one recording location: a country appears only when it is in the stated
chain. Absence is reported as ``coverage`` and ``not_loaded``, never as a fact about the place.
"""
from __future__ import annotations

from typing import Any

from ..editions.grouping import REL_APPEARS_ON
from ..graph import Limits
from ..store import repositories as repo
from .pages import PERSON_TYPES, _album_for, _brief, _coverage, _ordered, _owned, _relations

MAX_CHAIN = 12
PART_OF = "part of"
PLACE_NOT_LOADED = ("address", "capacity")
EVENT_NOT_LOADED = ("setlist", "attendance")


def place_page(reader, entity: dict[str, Any], *, limit: int = 200) -> dict[str, Any]:
    """The page for a ``place`` entity; ``reader`` is a KnowledgeReader."""
    if entity["type"] != "place":
        raise ValueError("a place page needs a place entity")
    db = reader._db
    walk = _walk(reader, entity, limit)
    areas, recordings, people, events = {}, {}, {}, {}
    for hop in walk["hops"]:
        other = hop["entity"]
        row = {"entity": other, "relations": _relations(hop)}
        if other["type"] == "area":
            areas[other["id"]] = row
        elif other["type"] == "recording":
            recordings[other["id"]] = _recording_row(db, other, row["relations"])
        elif other["type"] in PERSON_TYPES:
            people[other["id"]] = row
        elif other["type"] == "event":
            events[other["id"]] = {**row, "facts": _event_facts(db, other["id"])}
    stated = [r for r in areas.values() if any(rel["relation"] == "area" and rel["direction"] == "out"
                                              for rel in r["relations"])]
    status = reader.slice_status()
    return {
        "place": entity,
        "facts": _place_facts(db, entity["id"]),
        "aliases": [{"alias": a, "kind": k} for a, k in repo.aliases(db, entity["id"])],
        "area": _area_chain(db, _ordered(stated, key=lambda r: r["entity"])),
        "recordings": _ordered(recordings.values(), key=lambda r: r["recording"]),
        "people": _ordered(people.values(), key=lambda r: r["entity"]),
        "events": _ordered(events.values(), key=lambda r: r["entity"]),
        "truncated": _truncated(walk),
        "sources": {"musicbrainz_dump": {"coverage": _coverage(status, bool(walk["hops"])),
                                         "dump_timestamp": status["dump_timestamp"]}},
        "not_loaded": list(PLACE_NOT_LOADED),
    }


def event_page(reader, entity: dict[str, Any], *, limit: int = 200) -> dict[str, Any]:
    """The page for an ``event`` entity; ``reader`` is a KnowledgeReader."""
    if entity["type"] != "event":
        raise ValueError("an event page needs an event entity")
    db = reader._db
    walk = _walk(reader, entity, limit)
    places, areas, recordings, people = {}, {}, {}, {}
    for hop in walk["hops"]:
        other = hop["entity"]
        row = {"entity": other, "relations": _relations(hop)}
        if other["type"] == "place":
            places[other["id"]] = {**row, "facts": _place_facts(db, other["id"])}
        elif other["type"] == "area":
            areas[other["id"]] = row
        elif other["type"] == "recording":
            recordings[other["id"]] = _recording_row(db, other, row["relations"])
        elif other["type"] in PERSON_TYPES:
            people[other["id"]] = row
    status = reader.slice_status()
    return {
        "event": entity,
        "facts": _event_facts(db, entity["id"]),
        "aliases": [{"alias": a, "kind": k} for a, k in repo.aliases(db, entity["id"])],
        "places": _ordered(places.values(), key=lambda r: r["entity"]),
        "area": _area_chain(db, _ordered(areas.values(), key=lambda r: r["entity"])),
        "people": _ordered(people.values(), key=lambda r: r["entity"]),
        "recordings": _ordered(recordings.values(), key=lambda r: r["recording"]),
        "truncated": _truncated(walk),
        "sources": {"musicbrainz_dump": {"coverage": _coverage(status, bool(walk["hops"])),
                                         "dump_timestamp": status["dump_timestamp"]}},
        "not_loaded": list(EVENT_NOT_LOADED),
    }


# ---------------------------------------------------------------- helpers
def _walk(reader, entity: dict[str, Any], limit: int) -> dict[str, Any]:
    return reader.connections(entity["id"], credits_only=True, limits=Limits(max_depth=1, max_rows=limit, page_size=limit))


def _truncated(walk: dict[str, Any]) -> bool:
    return walk["truncated"] is not None or walk["next_cursor"] is not None


def _place_facts(db, entity_id: int) -> dict[str, Any] | None:
    row = db.execute("SELECT kind, latitude, longitude, begin_date, end_date FROM place_facts WHERE entity_id = ?",
                     (entity_id,)).fetchone()
    if row is None:
        return None
    return {"kind": row["kind"], "latitude": row["latitude"], "longitude": row["longitude"],
            "begin": row["begin_date"], "end": row["end_date"]}


def _event_facts(db, entity_id: int) -> dict[str, Any] | None:
    row = db.execute("SELECT kind, begin_date, end_date, cancelled FROM event_facts WHERE entity_id = ?",
                     (entity_id,)).fetchone()
    if row is None:
        return None
    return {"kind": row["kind"], "begin": row["begin_date"], "end": row["end_date"], "cancelled": bool(row["cancelled"])}


def _area_chain(db, stated: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The stated areas, each with the containing areas MusicBrainz nests it in (nearest first).

    Containment is stored child -> parent. A chain follows the lowest-id parent at each step and stops
    at a repeat or ``MAX_CHAIN`` levels; the country is whichever link is kind ``country``, never guessed.
    """
    rows = []
    for row in stated:
        chain, seen, current = [], {row["entity"]["id"]}, row["entity"]["id"]
        while len(chain) < MAX_CHAIN:
            parents = sorted(repo.edges_from(db, current, PART_OF), key=lambda e: e["to_id"])
            parent = next((repo.get_entity(db, e["to_id"]) for e in parents if e["to_id"] not in seen), None)
            if parent is None:
                break
            seen.add(parent["id"])
            chain.append({**_brief(parent), **_area_facts(db, parent["id"])})
            current = parent["id"]
        rows.append({**row, **_area_facts(db, row["entity"]["id"]), "contained_in": chain})
    return rows


def _area_facts(db, entity_id: int) -> dict[str, Any]:
    row = db.execute("SELECT kind, iso_code FROM area_facts WHERE entity_id = ?", (entity_id,)).fetchone()
    return {"kind": row["kind"], "iso_code": row["iso_code"]} if row else {"kind": None, "iso_code": None}


def _recording_row(db, recording: dict[str, Any], relations: list[dict[str, Any]]) -> dict[str, Any]:
    """A recording with the albums it appears on (editions fold into the release group) and ownership."""
    albums: dict[int, dict[str, Any]] = {}
    for edge in repo.edges_from(db, recording["id"], REL_APPEARS_ON):
        release = repo.get_entity(db, edge["to_id"])
        if release is not None:
            album = _album_for(db, release)
            albums.setdefault(album["id"], {"album": album, "owned": _owned(db, album) or bool(release["owned"])})
    rec = repo.get_entity(db, recording["id"]) or recording
    return {
        "recording": _brief(recording),
        "owned": bool(rec.get("owned")) or any(a["owned"] for a in albums.values()),
        "relations": relations,
        "albums": _ordered(albums.values(), key=lambda r: r["album"]),
    }
