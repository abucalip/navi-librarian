"""Similar-artist fusion for the artist page (contract section 7). Pure: no provider calls.

Last.fm reports a match score, so its contribution is that score. ListenBrainz radio reports
only an order, so its contribution is position based: the first result counts 1/2, the second
1/3, and so on. An artist listed by both sources adds both contributions.

Records arrive as one flat list, each with a ``source`` field, in the order the source returned
them. The list is what the cache stores, so owned filtering and ranking run on every read.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from discovery.search.merge import OwnedKeys, same_entity
from discovery.search.normalize import normalize_key

SIMILAR_LIMIT = 20
LASTFM = "lastfm"
LISTENBRAINZ = "listenbrainz"
REASONS = {
    LASTFM: "Last.fm similar artist",
    LISTENBRAINZ: "ListenBrainz similar artist",
}


def _artist(name: str, mbid: str | None) -> dict[str, Any]:
    """The candidate shape ``same_entity`` and ``OwnedKeys`` compare."""
    return {"type": "artist", "name": name, "key": normalize_key(name), "mbid": mbid or None, "year": None}


def fuse_similar(
    records: Iterable[Mapping[str, Any]],
    seed_name: str,
    seed_mbid: str | None,
    owned: OwnedKeys,
    limit: int = SIMILAR_LIMIT,
) -> list[dict[str, Any]]:
    """Fused suggestions, best first. The seed and owned artists are never suggested."""
    seed = _artist(seed_name, seed_mbid)
    positions: dict[str, int] = {}
    merged: list[dict[str, Any]] = []
    for record in records:
        source = record["source"]
        candidate = _artist(str(record["name"]), record.get("mbid"))
        if same_entity(candidate, seed):
            continue
        if source == LISTENBRAINZ:
            # Position within this source's own list; the seed was already removed upstream.
            position = positions.get(source, 0)
            positions[source] = position + 1
            contribution = 1 / (position + 2)
        else:
            contribution = float(record.get("match") or 0.0)

        entry = next((m for m in merged if same_entity(m["candidate"], candidate)), None)
        if entry is None:
            entry = {"candidate": candidate, "score": 0.0, "reasons": []}
            merged.append(entry)
        entry["score"] += contribution
        reason = REASONS[source]
        if reason not in entry["reasons"]:
            entry["reasons"].append(reason)

    ranked = sorted(merged, key=lambda m: (-m["score"], m["candidate"]["name"].casefold()))
    items = []
    for entry in ranked:
        if owned.owns(entry["candidate"]):
            continue
        items.append({
            "name": entry["candidate"]["name"],
            "mbid": entry["candidate"]["mbid"],
            "score": round(entry["score"], 3),
            "reasons": entry["reasons"],
        })
        if len(items) == limit:
            break
    return items
