"""The atlas: every place with stated coordinates and the recordings made there (Phase 7 client gate).

Read from the store only, no provider call. A place is listed only when MusicBrainz states both
coordinates; nothing is geocoded or inferred from a name. Only firmly matched, non-inferred
place -> recording edges count (the same rule as ``credits_only`` on the other pages). A recording
is owned when it is owned itself or appears on an owned release, or on a release whose group is owned.
"""
from __future__ import annotations

from typing import Any

from ..editions.grouping import REL_APPEARS_ON
from ..editions.release_groups import REL_MEMBER_OF
from .pages import _coverage

MAX_PLACES = 2000

_PLACES = f"""
SELECT p.id AS id, p.mbid AS mbid, p.canonical_name AS name, f.kind AS kind,
       f.latitude AS latitude, f.longitude AS longitude,
       COUNT(DISTINCT r.id) AS recordings,
       COUNT(DISTINCT CASE WHEN r.owned = 1
              OR EXISTS (SELECT 1 FROM edges a JOIN entities rel ON rel.id = a.to_id
                         WHERE a.from_id = r.id AND a.relation = '{REL_APPEARS_ON}'
                           AND (rel.owned = 1 OR EXISTS (
                                SELECT 1 FROM edges m JOIN entities g ON g.id = m.to_id
                                WHERE m.from_id = rel.id AND m.relation = '{REL_MEMBER_OF}' AND g.owned = 1)))
              THEN r.id END) AS owned_recordings
FROM entities p
JOIN place_facts f ON f.entity_id = p.id
JOIN edges e ON e.from_id = p.id
JOIN entities r ON r.id = e.to_id AND r.type = 'recording'
WHERE p.type = 'place' AND f.latitude IS NOT NULL AND f.longitude IS NOT NULL
  AND e.evidence_class != 'inferred' AND e.match_quality NOT IN ('fuzzy_unconfirmed', 'unresolved')
GROUP BY p.id
ORDER BY owned_recordings DESC, recordings DESC, p.canonical_name, p.mbid
LIMIT ?
"""


def atlas_page(reader, *, limit: int = 500) -> dict[str, Any]:
    """Places with coordinates, most owned recordings first; ``reader`` is a KnowledgeReader."""
    limit = max(1, min(int(limit), MAX_PLACES))
    db = reader._db
    rows = db.execute(_PLACES, (limit + 1,)).fetchall()
    status = reader.slice_status()
    return {
        "places": [{"entity": {"mbid": r["mbid"], "canonical_name": r["name"], "type": "place", "owned": False},
                    "kind": r["kind"], "latitude": r["latitude"], "longitude": r["longitude"],
                    "recordings": r["recordings"], "owned_recordings": r["owned_recordings"]}
                   for r in rows[:limit]],
        "truncated": len(rows) > limit,
        "sources": {"musicbrainz_dump": {"coverage": _coverage(status, bool(rows)),
                                         "dump_timestamp": status["dump_timestamp"]}},
    }
