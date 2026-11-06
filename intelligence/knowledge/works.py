"""Work pages: one composition and its recorded versions, read from the store only (Phase 4 item 5).

Built on the :class:`KnowledgeReader` walk like the dossier and the person and label pages: every
link carries its source, evidence class and match quality, and an inferred or unmatched edge never
appears (``credits_only``). Nothing is inferred and no provider is called.

A work page lists the recordings MusicBrainz links to the work (relation ``performance``), each
with the albums it appears on (editions fold into the release group), whether it is in the library,
and whether MusicBrainz marks it as a cover, live, instrumental and so on (the link's own
attributes, never guessed). It also lists the people credited on the work itself (composer,
lyricist, ...) and related works (arrangements, "based on", medleys, parts) as MusicBrainz states
them. The summary is a count, "one composition, N recordings, K in your library", never a ranking.
Absence is reported as ``coverage`` and ``not_loaded``, never as a fact about the work.
"""
from __future__ import annotations

from typing import Any

from ..editions.grouping import REL_APPEARS_ON
from ..editions.release_groups import REL_MEMBER_OF
from ..graph import Limits
from ..store import repositories as repo
from .pages import PERSON_TYPES, _album_for, _brief, _coverage, _ordered, _owned, _relations

MAX_VERSIONS = 100
MAX_PERFORMERS = 25
NOT_LOADED = ("recording_artist_credit", "work_languages", "iswc")
PERFORMANCE = "performance"


def work_page(reader, entity: dict[str, Any], *, limit: int = 200) -> dict[str, Any]:
    """The page for a ``work`` entity; ``reader`` is a KnowledgeReader."""
    if entity["type"] != "work":
        raise ValueError("a work page needs a work entity")
    db = reader._db
    walk = reader.connections(entity["id"], credits_only=True, limits=Limits(max_depth=1, max_rows=limit, page_size=limit))
    versions: list[dict[str, Any]] = []
    writers: dict[int, dict[str, Any]] = {}
    related: dict[int, dict[str, Any]] = {}
    for hop in walk["hops"]:
        other = hop["entity"]
        if other["type"] == "recording":
            versions.append(_version(reader, db, other, hop))
        elif other["type"] in PERSON_TYPES:
            writers[other["id"]] = {"entity": other, "relations": _relations(hop)}
        elif other["type"] == "work":
            related[other["id"]] = {"entity": other, "relations": _relations(hop)}
    versions.sort(key=lambda v: ((v["recording"]["canonical_name"] or "").casefold(), v["recording"]["id"]))
    truncated_versions = len(versions) > MAX_VERSIONS
    versions = versions[:MAX_VERSIONS]
    status = reader.slice_status()
    return {
        "work": entity,
        "aliases": [{"alias": a, "kind": k} for a, k in repo.aliases(db, entity["id"])],
        "summary": {
            "recordings": len(versions),
            "in_library": sum(1 for v in versions if v["owned"]),
            "covers": sum(1 for v in versions if "cover" in v["attributes"]),
        },
        "versions": versions,
        "written_by": _ordered(writers.values(), key=lambda r: r["entity"]),
        "related_works": _ordered(related.values(), key=lambda r: r["entity"]),
        "truncated": walk["truncated"] is not None or walk["next_cursor"] is not None or truncated_versions,
        "sources": {"musicbrainz_dump": {"coverage": _coverage(status, bool(versions or writers or related)),
                                         "dump_timestamp": status["dump_timestamp"]}},
        "not_loaded": list(NOT_LOADED),
    }


def works_of_recording(reader, entity: dict[str, Any], *, limit: int = 50) -> dict[str, Any]:
    """The works a recording is linked to, each with how many other recordings MusicBrainz links to it."""
    if entity["type"] != "recording":
        raise ValueError("works of a recording need a recording entity")
    db = reader._db
    walk = reader.connections(entity["id"], credits_only=True, limits=Limits(max_depth=1, max_rows=limit, page_size=limit))
    rows = []
    for hop in walk["hops"]:
        other = hop["entity"]
        if other["type"] != "work":
            continue
        others = [e for e in repo.edges_to(db, other["id"], PERFORMANCE) if e["from_id"] != entity["id"]]
        rows.append({"work": other, "relations": _relations(hop), "other_recordings": len({e["from_id"] for e in others})})
    status = reader.slice_status()
    return {
        "recording": entity,
        "works": _ordered(rows, key=lambda r: r["work"]),
        "truncated": walk["truncated"] is not None or walk["next_cursor"] is not None,
        "sources": {"musicbrainz_dump": {"coverage": _coverage(status, bool(rows)),
                                         "dump_timestamp": status["dump_timestamp"]}},
    }


# ---------------------------------------------------------------- helpers
def _version(reader, db, recording: dict[str, Any], hop: dict[str, Any]) -> dict[str, Any]:
    """One recording of the work: albums, ownership, MusicBrainz's own attributes and credited performers."""
    relations = _relations(hop)
    attributes = sorted({a.strip().lower() for r in relations for a in (r["role"] or "").split(",") if a.strip()})
    albums: dict[int, dict[str, Any]] = {}
    for edge in repo.edges_from(db, recording["id"], REL_APPEARS_ON):
        release = repo.get_entity(db, edge["to_id"])
        if release is None:
            continue
        album = _album_for(db, release)
        albums.setdefault(album["id"], {"album": album, "owned": _owned(db, album) or bool(release["owned"])})
    rec = repo.get_entity(db, recording["id"]) or recording
    owned = bool(rec.get("owned")) or any(a["owned"] for a in albums.values())
    walk = reader.connections(recording["id"], credits_only=True,
                              limits=Limits(max_depth=1, max_rows=MAX_PERFORMERS, page_size=MAX_PERFORMERS))
    performers = [{"entity": h["entity"], "relations": _relations(h)} for h in walk["hops"]
                  if h["entity"]["type"] in PERSON_TYPES]
    return {
        "recording": _brief(recording),
        "owned": owned,
        "attributes": attributes,
        "relations": relations,
        "albums": _ordered(albums.values(), key=lambda r: r["album"]),
        "performers": _ordered(performers, key=lambda r: r["entity"]),
    }
