"""Ownership, dedupe and result shaping for provider candidates (contract sections 4.2 and 3.8).

Provider results are emitted as they arrive, so a candidate is compared with the owned
library and with the results already emitted in this request. Owned albums and artists
are already shown as owned results, so a provider match against them is not emitted again.
"""

from __future__ import annotations

from typing import Any

from discovery.search.index import OwnedData


def _years_match(first: int | None, second: int | None) -> bool:
    """Years agree, or one of them is unknown. Unknown years never block a match."""
    return first is None or second is None or first == second


def _tier(key: str, query: str) -> int | None:
    if key == query:
        return 0
    if key.startswith(query):
        return 1
    if query in key:
        return 2
    return None


class OwnedKeys:
    """Owned artist keys and owned album keys with their years, built once per request."""

    def __init__(self, data: OwnedData | None):
        self._artists: set[str] = set()
        self._albums: dict[str, list[int | None]] = {}
        if data is None:
            return
        self._artists = {artist["key"] for artist in data.artists}
        for album in data.albums:
            self._albums.setdefault(album["key"], []).append(album["year"])

    def owns(self, candidate: dict[str, Any]) -> bool:
        if candidate["type"] == "artist":
            return candidate["key"] in self._artists
        years = self._albums.get(candidate["key"], [])
        return any(_years_match(candidate["year"], year) for year in years)


def same_entity(first: dict[str, Any], second: dict[str, Any]) -> bool:
    """Two candidates describe one entity: same MBID when both have one, else same key with compatible years.

    Two artists with different known MBIDs stay separate even when their names match.
    """
    if first["type"] != second["type"]:
        return False
    if first["mbid"] and second["mbid"]:
        return first["mbid"] == second["mbid"]
    if first["key"] != second["key"]:
        return False
    return _years_match(first["year"], second["year"])


def fresh_candidates(
    candidates: list[dict[str, Any]],
    *,
    query: str,
    owned: OwnedKeys,
    emitted: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return the candidates to emit now, best match first, skipping owned and duplicate ones.

    ``emitted`` is updated in place with every candidate that is returned, so later sources
    in the same request see it. A duplicate from a later source is dropped; the first
    emitted result keeps the sources known when it was shown.
    """
    ranked = []
    for candidate in candidates:
        tier = _tier(candidate["key"], query)
        if tier is None or owned.owns(candidate):
            continue
        ranked.append((tier, candidate["name"].casefold(), candidate))
    ranked.sort(key=lambda row: row[:2])

    fresh = []
    for _, _, candidate in ranked:
        if any(same_entity(candidate, seen) for seen in emitted):
            continue
        emitted.append(candidate)
        fresh.append(candidate)
    return fresh


def shape_result(candidate: dict[str, Any]) -> dict[str, Any]:
    """Build the contract ``result`` payload for a provider candidate (section 3.8)."""
    identifier = candidate["mbid"] or candidate["release_group_mbid"] or f"{candidate['source']}:{candidate['key']}"
    base = {
        "type": candidate["type"],
        "owned": False,
        "id": identifier,
        "key": candidate["key"],
        "name": candidate["name"],
        "mbid": candidate["mbid"],
        "sources": [candidate["source"]],
        "artwork_url": None,
    }
    if candidate["type"] == "artist":
        # Search sources do not report album counts or genres, so both are null (see PR notes).
        return {**base, "album_count": None, "genre": None}
    return {
        **base,
        "artist": candidate["artist"],
        "artist_key": candidate["artist_key"],
        "year": candidate["year"],
        "release_group_mbid": candidate["release_group_mbid"],
    }
