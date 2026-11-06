"""Album dossier: one album's release family, credits and labels, read from the store only.

Built on the :class:`KnowledgeReader` walk, so every credit carries its source, evidence class and
match quality, and an inferred or unmatched edge never appears as a credit (``credits_only``).
Nothing is inferred and no provider is called.

What the store holds today is what is shown: editions (from the release-group link and the stored
MusicBrainz release document), people and labels related to the release, its release group or its
recordings, and the slice's dump date. Fields no loader fills yet (catalogue numbers, formats,
recording places and dates, Cover Art Archive variants) are listed in ``not_loaded`` instead of
being left out silently, so a client can say "not loaded" rather than "none". A missing credit list
is reported as ``coverage`` (``pending``, ``loaded`` or ``no_relationships_in_slice``), never as a
fact about the album.
"""
from __future__ import annotations

from typing import Any

from ..editions.grouping import group_editions, tracklist
from ..editions.release_groups import REL_MEMBER_OF
from ..graph import Limits
from ..store import repositories as repo

PERSON_TYPES = ("artist", "person", "group")
MAX_RECORDINGS = 100
NOT_LOADED = ("catalogue_numbers", "formats", "recording_places_and_dates", "cover_art_variants")


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
    truncated = False
    for scope, track_title, target in targets:
        walk = reader.connections(target["id"], credits_only=True, limits=Limits(max_depth=1, max_rows=limit, page_size=limit))
        truncated = truncated or walk["truncated"] is not None or walk["next_cursor"] is not None
        for hop in walk["hops"]:
            other = hop["entity"]
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
            editions.append({
                "release": {"id": e.release_id, "mbid": e.mbid, "title": e.title, "owned": e.owned},
                "date": e.info.date if e.info else None, "country": e.info.country if e.info else None,
                "status": e.info.status if e.info else None, "labels": list(e.labels), "relation": e.relation,
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
        "credits_truncated": truncated or len(tracks) > MAX_RECORDINGS,
        "sources": {"musicbrainz_dump": {"coverage": coverage, "dump_timestamp": status["dump_timestamp"]}},
        "not_loaded": list(NOT_LOADED),
    }
