"""``KnowledgeReader``: read-only access to entities, relationships and source status.

Everything here is a read of the knowledge store (and the attached state file), so a request
never waits on a provider and never writes. Answers carry their provenance: each relationship
says which source stated it, the evidence class and match quality, and whether it may be shown
as a credit (inferred or unmatched edges never are). Nothing is inferred here.

Honest absence: a profile reports the MusicBrainz slice as ``pending`` when no slice has been
loaded, ``loaded`` when the entity has relationships from it, and ``no_relationships_in_slice``
when the slice is loaded but holds none for this entity. It never presents a missing fact as a
fact about the world.

This is the facade of efficiency.md E5. It reads the store only; the legacy-cache fallback and the
profile tables (``artist_profile``, ``album_profile``) arrive with the route migrations.
"""
from __future__ import annotations

import sqlite3
import time
from typing import Any, Callable, Iterable

from .public import public
from ..graph import Limits, explore
from ..graph.traversal import Evidence, Hop
from ..store import generations
from ..store import repositories as repo

SLICE_SOURCE = "musicbrainz_dump"
SLICE_META_PREFIX = "musicbrainz_slice."
PROFILE_RELATIONSHIPS = 50


def slice_status(db: sqlite3.Connection, now: float | None = None) -> dict[str, Any]:
    """Whether a MusicBrainz slice is loaded, its dump date and age, and its size."""
    meta = {r["key"][len(SLICE_META_PREFIX):]: r["value"] for r in db.execute(
        "SELECT key, value FROM meta WHERE key LIKE ?", (SLICE_META_PREFIX + "%",))}
    edges = db.execute("SELECT COUNT(*) FROM edges WHERE source = ?", (SLICE_SOURCE,)).fetchone()[0]
    loaded_at = float(meta["loaded_at"]) if meta.get("loaded_at") else None
    now = time.time() if now is None else now
    return {
        "loaded": loaded_at is not None,
        "dump_timestamp": meta.get("dump_timestamp"),
        "schema_sequence": int(meta["schema_sequence"]) if meta.get("schema_sequence") else None,
        "loaded_at": loaded_at,
        "age_seconds": max(0.0, now - loaded_at) if loaded_at is not None else None,
        "edges": edges,
        "data_version": generations.data_version(db, "musicbrainz_slice"),
    }


class KnowledgeReader:
    def __init__(self, db: sqlite3.Connection, clock: Callable[[], float] = time.time):
        self._db, self._clock = db, clock

    # ---------------------------------------------------------------- entities
    def entity(self, type: str | None = None, *, id: int | None = None, mbid: str | None = None,
               navidrome_id: str | None = None) -> dict[str, Any] | None:
        """One entity by store id, or by ``type`` plus ``mbid`` or ``navidrome_id``."""
        if id is not None:
            return repo.get_entity(self._db, id)
        ids = {k: v.lower() if k == "mbid" else v for k, v in (("mbid", mbid), ("navidrome_id", navidrome_id)) if v}
        if not type or not ids:
            raise ValueError("give an id, or a type with an mbid or navidrome_id")
        return repo.find_entity(self._db, type, **ids)

    def find_by_name(self, type: str, name: str) -> list[dict[str, Any]]:
        """Entities of ``type`` with this name; more than one means ambiguous, and callers must say so."""
        return repo.find_entities_by_name(self._db, type, name)

    # ---------------------------------------------------------------- relationships
    def connections(self, entity_id: int, *, credits_only: bool = False, relations: Iterable[str] | None = None,
                    direction: str = "both", limits: Limits = Limits(), cursor: str | None = None) -> dict[str, Any]:
        """Bounded walk from an entity (see :func:`intelligence.graph.explore`), with names and provenance."""
        page = explore(self._db, entity_id, relations=relations, direction=direction,
                       credits_only=credits_only, limits=limits, cursor=cursor)
        return {
            "hops": [self._hop(h) for h in page.hops],
            "next_cursor": page.next_cursor,
            "truncated": page.truncated,
        }

    def connections_page(self, *, id: int | None = None, mbid: str | None = None, navidrome_id: str | None = None,
                         type: str | None = None, credits_only: bool = False, relations: Iterable[str] | None = None,
                         direction: str = "both", limits: Limits = Limits(), cursor: str | None = None
                         ) -> dict[str, Any] | None:
        """Public bounded walk from one entity; each hop names the entity one step closer by ``via_mbid``.

        None when the start is unknown. A bad cursor or direction raises ``ValueError``.
        """
        start = self.entity(type, id=id, mbid=mbid, navidrome_id=navidrome_id)
        if start is None:
            return None
        walk = self.connections(start["id"], credits_only=credits_only, relations=relations, direction=direction,
                                limits=limits, cursor=cursor)
        mbids = {start["id"]: start.get("mbid")}
        hops = []
        for hop in walk["hops"]:
            via = hop["via_entity_id"]
            if via not in mbids:
                mbids[via] = (repo.get_entity(self._db, via) or {}).get("mbid")
            hops.append({**hop, "via_mbid": mbids[via]})
        return public({
            "start": {k: start.get(k) for k in ("id", "type", "mbid", "canonical_name", "owned")},
            "hops": hops,
            "next_cursor": walk["next_cursor"],
            "truncated": walk["truncated"],
            "sources": {SLICE_SOURCE: self._coverage_of(hops)},
        })

    def _coverage_of(self, hops: list[dict[str, Any]]) -> dict[str, Any]:
        status = slice_status(self._db, self._clock())
        if not status["loaded"]:
            coverage = "pending"
        else:
            from_slice = any(e["source"] == SLICE_SOURCE for h in hops for e in h["evidence"])
            coverage = "loaded" if from_slice else "no_relationships_in_slice"
        return {"coverage": coverage, "dump_timestamp": status["dump_timestamp"]}

    def profile(self, type: str, *, id: int | None = None, mbid: str | None = None,
                navidrome_id: str | None = None, limit: int = PROFILE_RELATIONSHIPS) -> dict[str, Any] | None:
        """An entity with aliases, its direct relationships and where its facts come from."""
        entity = self.entity(type, id=id, mbid=mbid, navidrome_id=navidrome_id)
        if entity is None:
            return None
        walk = self.connections(entity["id"], limits=Limits(max_depth=1, max_rows=limit, page_size=limit))
        status = slice_status(self._db, self._clock())
        from_slice = sum(1 for h in walk["hops"] for e in h["evidence"] if e["source"] == SLICE_SOURCE)
        if not status["loaded"]:
            coverage = "pending"
        else:
            coverage = "loaded" if from_slice else "no_relationships_in_slice"
        return {
            "entity": entity,
            "aliases": [{"alias": a, "kind": k} for a, k in repo.aliases(self._db, entity["id"])],
            "relationships": walk["hops"],
            "relationships_truncated": walk["truncated"] or (walk["next_cursor"] is not None),
            "sources": {SLICE_SOURCE: {"coverage": coverage, "dump_timestamp": status["dump_timestamp"]}},
        }

    def slice_status(self) -> dict[str, Any]:
        return slice_status(self._db, self._clock())

    def album_dossier(self, *, id: int | None = None, mbid: str | None = None, navidrome_id: str | None = None,
                      type: str = "release", limit: int = 100) -> dict[str, Any] | None:
        """Release family, credits and labels for a release (or release group); None when unknown."""
        from .dossier import album_dossier
        entity = self.entity(type, id=id, mbid=mbid, navidrome_id=navidrome_id)
        return None if entity is None else public(album_dossier(self, entity, limit=limit))

    def person_page(self, *, id: int | None = None, mbid: str | None = None, navidrome_id: str | None = None,
                    type: str = "artist", limit: int = 200) -> dict[str, Any] | None:
        """Credits of an artist, person or group split into in-library and not; None when unknown."""
        from .pages import person_page
        entity = self.entity(type, id=id, mbid=mbid, navidrome_id=navidrome_id)
        return None if entity is None else public(person_page(self, entity, limit=limit))

    def label_page(self, *, id: int | None = None, mbid: str | None = None, limit: int = 200) -> dict[str, Any] | None:
        """Related labels, owned catalogue and the rest of the slice for a label; None when unknown."""
        from .pages import label_page
        entity = self.entity("label", id=id, mbid=mbid)
        return None if entity is None else public(label_page(self, entity, limit=limit))

    def work_page(self, *, id: int | None = None, mbid: str | None = None, limit: int = 200) -> dict[str, Any] | None:
        """One composition with its recordings, writers and related works; None when unknown."""
        from .works import work_page
        entity = self.entity("work", id=id, mbid=mbid)
        return None if entity is None else public(work_page(self, entity, limit=limit))

    def works_of_recording(self, *, id: int | None = None, mbid: str | None = None,
                           navidrome_id: str | None = None, limit: int = 50) -> dict[str, Any] | None:
        """The works a recording is a performance of, with counts of other recordings; None when unknown."""
        from .works import works_of_recording
        entity = self.entity("recording", id=id, mbid=mbid, navidrome_id=navidrome_id)
        return None if entity is None else public(works_of_recording(self, entity, limit=limit))

    # ---------------------------------------------------------------- helpers
    def _hop(self, hop: Hop) -> dict[str, Any]:
        other = repo.get_entity(self._db, hop.entity_id) or {}
        return {
            "entity": {k: other.get(k) for k in ("id", "type", "mbid", "canonical_name", "owned")},
            "depth": hop.depth,
            "via_entity_id": hop.via_entity_id,
            "credit": hop.credit,
            "evidence": [self._evidence(e) for e in hop.evidence],
        }

    @staticmethod
    def _evidence(e: Evidence) -> dict[str, Any]:
        return {
            "relation": e.relation, "role": e.role, "direction": e.direction,
            "evidence_class": e.evidence_class, "match_quality": e.match_quality,
            "source": e.source, "source_url": e.source_url,
            "valid_from": e.valid_from, "valid_to": e.valid_to,
        }
