"""Similar-artist fusion for the artist page (contract section 7). Pure: no provider calls.

Last.fm reports a match score, so its contribution is that score. ListenBrainz radio reports
only an order, so its contribution is position based: the first result counts 1/2, the second
1/3, and so on. An artist listed by both sources adds both contributions.

An owned artist is not dropped: it is flagged ``owned`` with its library ID and listed after the
artists the library does not have. Records arrive as one flat list, each with a ``source`` field,
in the order the source returned them. The list is what the cache stores, so owned matching and
ranking run on every read.
"""

from __future__ import annotations

import math
from collections.abc import Collection, Iterable, Mapping
from typing import Any

from discovery.search.merge import OwnedKeys, same_entity
from discovery.search.normalize import normalize_key
from discovery.search.providers import DISCOGS_ATTRIBUTION
from discovery.search.query import artwork_url

SIMILAR_LIMIT = 20
LASTFM = "lastfm"
LISTENBRAINZ = "listenbrainz"
REASONS = {
    LASTFM: "Last.fm similar artist",
    LISTENBRAINZ: "ListenBrainz similar artist",
}
# Shared tags add TAG_WEIGHT times the Jaccard overlap of the two tag sets (0 to 1).
TAG_WEIGHT = 0.5
TAG_REASON_LIMIT = 3
# An owned artist the owner plays gets up to OWNER_BOOST_WEIGHT, rising with log(plays) and
# reaching the full weight at OWNER_PLAY_SCALE plays. These are starting values, not measured.
OWNER_BOOST_WEIGHT = 0.5
OWNER_PLAY_SCALE = 100


def _artist(name: str, mbid: str | None) -> dict[str, Any]:
    """The candidate shape ``same_entity`` and ``OwnedKeys`` compare."""
    return {"type": "artist", "name": name, "key": normalize_key(name), "mbid": mbid or None, "year": None}


def owner_boost(plays: int) -> float:
    """Boost for an owned artist the owner plays: 0 at no plays, rising with log(plays) to the full weight."""
    if plays <= 0:
        return 0.0
    return OWNER_BOOST_WEIGHT * min(1.0, math.log1p(plays) / math.log1p(OWNER_PLAY_SCALE))


def fuse_similar(
    records: Iterable[Mapping[str, Any]],
    seed_name: str,
    seed_mbid: str | None,
    owned: OwnedKeys,
    limit: int = SIMILAR_LIMIT,
    *,
    seed_tags: Collection[str] = (),
    candidate_tags: Mapping[str, Collection[str]] | None = None,
    seed_styles: Collection[str] = (),
    candidate_styles: Mapping[str, Collection[str]] | None = None,
) -> list[dict[str, Any]]:
    """Fused suggestions: artists not in the library by score, then owned artists by score.

    ``seed_tags`` and ``candidate_tags`` (keyed by MBID) add the shared-tag contribution. Owned
    artists the owner plays get the owner boost (contract section 7, item 4). The seed artist is
    never suggested.
    """
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

    seed_tag_set = {tag.casefold() for tag in seed_tags}
    seed_style_set = {tag.casefold() for tag in seed_styles}
    for entry in merged:
        candidate = entry["candidate"]
        entry["owned_artist"] = owned.owned_artist(candidate)
        tags = (candidate_tags or {}).get(candidate["mbid"]) if candidate["mbid"] else None
        if tags and seed_tag_set:
            shared = sorted(seed_tag_set & {tag.casefold() for tag in tags})
            if shared:
                union = seed_tag_set | {tag.casefold() for tag in tags}
                entry["score"] += TAG_WEIGHT * len(shared) / len(union)
                entry["reasons"].append("Shared tags: " + ", ".join(shared[:TAG_REASON_LIMIT]))
                # A shared tag that Discogs supplied for the seed or for this candidate carries the Discogs
                # attribution (contract section 1). Another candidate's styles never count.
                own_styles = {tag.casefold() for tag in (candidate_styles or {}).get(candidate["mbid"], ())}
                entry["discogs"] = bool((seed_style_set | own_styles) & set(shared))
        if entry["owned_artist"] is not None:
            plays = int(entry["owned_artist"].get("plays") or 0)
            boost = owner_boost(plays)
            if boost:
                entry["score"] += boost
                entry["reasons"].append("You play this artist")
    # Owned artists go to the owned list, which follows the unowned suggestions (contract 8.1).
    ranked = sorted(
        merged,
        key=lambda m: (m["owned_artist"] is not None, -m["score"], m["candidate"]["name"].casefold()),
    )
    items = []
    for entry in ranked[:limit]:
        owned_artist = entry["owned_artist"]
        extra = {"attribution": DISCOGS_ATTRIBUTION} if entry.get("discogs") else {}
        items.append({
            **extra,
            "name": entry["candidate"]["name"],
            "key": entry["candidate"]["key"],
            "artwork_url": artwork_url(owned_artist["id"]) if owned_artist else None,
            "mbid": entry["candidate"]["mbid"],
            "owned": owned_artist is not None,
            "id": owned_artist["id"] if owned_artist else None,
            "score": round(entry["score"], 3),
            "reasons": entry["reasons"],
        })
    return items
