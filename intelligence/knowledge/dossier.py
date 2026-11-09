"""Album dossier: one album's release family, credits and labels, read from the store only.

Built on the :class:`KnowledgeReader` walk, so every credit carries its source, evidence class and
match quality, and an inferred or unmatched edge never appears as a credit (``credits_only``).
Nothing is inferred and no provider is called.

An edition's date, country and status come from the first source that has them: the stored MusicBrainz
release document, then the dump's own release facts, then (owner decision, 2026-11-06, option 3) the owned
file's year and track count from Navidrome, marked ``facts_source: "library_file"`` so a client never
shows a tag year as a MusicBrainz date. ``facts_source`` is null when nothing is known.

What the store holds today is what is shown: editions (from the release-group link and the stored
MusicBrainz release document), people and labels related to the release, its release group or its
recordings, and the slice's dump date. Catalogue numbers and formats come from the dump's release facts (``release_labels``,
``release_facts.formats``); they stay in ``not_loaded`` while the store holds none (a slice imported before
schema 4), so a client says "not loaded" and not "none". Fields no loader fills yet (recording places and dates, Cover Art Archive variants) are listed in ``not_loaded`` instead of
being left out silently, so a client can say "not loaded" rather than "none". A missing credit list
is reported as ``coverage`` (``pending``, ``loaded`` or ``no_relationships_in_slice``), never as a
fact about the album.
"""
from __future__ import annotations

from typing import Any

from ..editions.grouping import group_editions, tracklist
from ..ingest.navidrome import SOURCE as NAVIDROME_SOURCE
from ..editions.release_groups import REL_MEMBER_OF
from ..graph import Limits
from ..store import repositories as repo

PERSON_TYPES = ("artist", "person", "group")
PLACE_TYPES = ("place", "event", "area")  # where a recording was made, as MusicBrainz states it
MAX_RECORDINGS = 100
NOT_LOADED = ("recording_places_and_dates", "cover_art_variants")


def album_dossier(reader, entity: dict[str, Any], *, limit: int = 100) -> dict[str, Any]:
    """The dossier for a ``release`` or ``release_group`` entity; ``reader`` is a KnowledgeReader."""
    if entity["type"] not in ("release", "release_group"):
        raise ValueError("a dossier needs a release or release_group entity")
    db = reader._db
    if entity["type"] == "release":
        group = next(iter(repo.edges_from(db, entity["id"], REL_MEMBER_OF)), None)
        group_entity = repo.get_entity(db, group["to_id"]) if group else None
        release_entity = entity
    else:
        group_entity, release_entity = entity, None

    tracks = tracklist(db, release_entity["id"]) if release_entity else ()
    targets = [("album", None, e) for e in (release_entity, group_entity) if e]
    targets += [("recording", t.title, repo.get_entity(db, t.recording_id)) for t in tracks[:MAX_RECORDINGS]]

    people: dict[int, dict[str, Any]] = {}
    labels: dict[int, dict[str, Any]] = {}
    places: list[dict[str, Any]] = []
    truncated = False
    for scope, track_title, target in targets:
        walk = reader.connections(target["id"], credits_only=True, limits=Limits(max_depth=1, max_rows=limit, page_size=limit))
        truncated = truncated or walk["truncated"] is not None or walk["next_cursor"] is not None
        for hop in walk["hops"]:
            other = hop["entity"]
            if other["type"] in PLACE_TYPES and scope == "recording":
                for ev in hop["evidence"]:
                    row = {"entity": other, "relation": ev["relation"], "role": ev["role"], "track": track_title,
                           "valid_from": ev["valid_from"], "valid_to": ev["valid_to"], "source": ev["source"],
                           "source_url": ev["source_url"], "evidence_class": ev["evidence_class"],
                           "match_quality": ev["match_quality"]}
                    if row not in places:
                        places.append(row)
                continue
            bucket = people if other["type"] in PERSON_TYPES else labels if other["type"] == "label" else None
            if bucket is None:
                continue
            row = bucket.setdefault(other["id"], {"entity": other, "credits": []})
            for ev in hop["evidence"]:
                credit = {"relation": ev["relation"], "role": ev["role"], "scope": scope, "track": track_title,
                          "source": ev["source"], "source_url": ev["source_url"], "evidence_class": ev["evidence_class"],
                          "match_quality": ev["match_quality"], "valid_from": ev["valid_from"], "valid_to": ev["valid_to"]}
                if credit not in row["credits"]:
                    row["credits"].append(credit)

    status = reader.slice_status()
    if not status["loaded"]:
        coverage = "pending"
    else:
        coverage = "loaded" if (people or labels) else "no_relationships_in_slice"

    editions = []
    if group_entity:
        for e in group_editions(db, group_entity["id"], owned_only=False):
            facts = _edition_facts(db, e)
            editions.append({
                "release": {"id": e.release_id, "mbid": e.mbid, "title": e.title, "owned": e.owned},
                **facts, "formats": _formats(db, e.release_id), "catalogue": _catalogue(db, e.release_id),
                "labels": list(e.labels), "relation": e.relation,
            })

    if group_entity and any(e["release"]["owned"] for e in editions):
        group_entity = {**group_entity, "owned": True}  # a group is owned when any edition is

    def ordered(bucket):
        return sorted(bucket.values(), key=lambda r: ((r["entity"]["canonical_name"] or "").casefold(), r["entity"]["id"]))

    return {
        "album": release_entity or group_entity,
        "release_group": group_entity,
        "release_family": {"editions": editions, "count": len(editions)},
        "tracks": [{"position": t.position, "title": t.title, "recording_mbid": t.recording_mbid} for t in tracks],
        "people": ordered(people),
        "labels": ordered(labels),
        "recording_places": sorted(places, key=lambda p: (p["track"] or "", (p["entity"]["canonical_name"] or "").casefold(),
                                                          p["relation"], p["entity"]["id"])),
        "credits_truncated": truncated or len(tracks) > MAX_RECORDINGS,
        "sources": {"musicbrainz_dump": {"coverage": coverage, "dump_timestamp": status["dump_timestamp"]}},
        "not_loaded": [k for k in NOT_LOADED if k != "recording_places_and_dates" or not _has_recording_places(db)]
                      + _missing_release_facts(db),
    }


def _has_recording_places(db) -> bool:
    """True once the store holds any place, event or area link to a recording (a slice imported with context)."""
    marks = ", ".join("?" * len(PLACE_TYPES))
    return db.execute(
        f"SELECT 1 FROM edges g JOIN entities f ON f.id = g.from_id JOIN entities t ON t.id = g.to_id "
        f"WHERE t.type = 'recording' AND f.type IN ({marks}) AND g.source = 'musicbrainz_dump' LIMIT 1",
        PLACE_TYPES).fetchone() is not None


def _formats(db, release_id: int) -> str | None:
    """Medium formats as MusicBrainz states them ("CD", "2×Vinyl"); null when the dump gave none."""
    row = db.execute("SELECT formats FROM release_facts WHERE entity_id = ?", (release_id,)).fetchone()
    return row["formats"] if row and row["formats"] else None


def _catalogue(db, release_id: int) -> list[dict[str, Any]]:
    """Label and catalogue number pairs of one release; either part is null when the dump states none."""
    rows = db.execute(
        "SELECT l.mbid AS mbid, l.canonical_name AS name, rl.catalogue_number AS number "
        "FROM release_labels rl LEFT JOIN entities l ON l.id = rl.label_id "
        "WHERE rl.release_id = ? ORDER BY COALESCE(l.canonical_name, '') COLLATE NOCASE, l.mbid, rl.catalogue_number",
        (release_id,)).fetchall()
    return [{"label": {"mbid": r["mbid"], "name": r["name"]} if r["name"] is not None else None,
             "catalogue_number": r["number"], "source": "musicbrainz_dump"} for r in rows]


def _missing_release_facts(db) -> list[str]:
    missing = []
    if db.execute("SELECT 1 FROM release_labels LIMIT 1").fetchone() is None:
        missing.append("catalogue_numbers")
    if db.execute("SELECT 1 FROM release_facts WHERE formats IS NOT NULL LIMIT 1").fetchone() is None:
        missing.append("formats")
    return missing


def _edition_facts(db, edition) -> dict[str, Any]:
    """``date``, ``country``, ``status``, ``track_count`` and ``facts_source`` for one edition."""
    track_count = len(edition.tracks) or None
    info = edition.info
    if info and (info.date or info.country or info.status):
        return {"date": info.date, "country": info.country, "status": info.status,
                "track_count": track_count, "facts_source": "musicbrainz_release"}
    row = db.execute("SELECT date, country, status FROM release_facts WHERE entity_id = ?", (edition.release_id,)).fetchone()
    if row and (row["date"] or row["country"] or row["status"]):
        return {"date": row["date"], "country": row["country"], "status": row["status"],
                "track_count": track_count, "facts_source": "musicbrainz_dump"}
    entity = repo.get_entity(db, edition.release_id) or {}
    observation = repo.latest_observation(db, NAVIDROME_SOURCE, f"album:{entity['navidrome_id']}") if entity.get("navidrome_id") else None
    payload = observation["payload"] if observation and isinstance(observation["payload"], dict) else {}
    year = payload.get("year")
    date = payload.get("release_date") or (f"{int(year):04d}" if isinstance(year, int) and year > 0 else None)
    count = track_count or (payload.get("song_count") if isinstance(payload.get("song_count"), int) else None)
    if payload and (date or count):
        return {"date": date, "country": None, "status": None, "track_count": count, "facts_source": "library_file"}
    return {"date": None, "country": None, "status": None, "track_count": track_count, "facts_source": None}
