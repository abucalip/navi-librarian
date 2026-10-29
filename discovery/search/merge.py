"""Ownership, dedupe and result shaping for provider candidates (contract sections 4.2 and 3.8).

Provider results are emitted as they arrive, so a candidate is compared with the owned
library and with the results already emitted in this request. Owned albums and artists
are already shown as owned results, so a provider match against them is not emitted again.
"""

from __future__ import annotations

from typing import Any

from discovery.search.index import OwnedData
from discovery.search.normalize import album_match_key, normalize_key
from discovery.search.providers import DISCOGS_ATTRIBUTION


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


def _mbid_match(candidate: str | None, owned: list[str | None]) -> bool:
    """MBIDs agree, or one side has none. Unknown MBIDs fall back to name matching."""
    if candidate is None or any(mbid is None for mbid in owned):
        return True
    return candidate in owned


def _album_lookup_key(artist_key: str, name: str) -> str:
    return f"{artist_key}/{album_match_key(name)}"


class OwnedKeys:
    """Owned artists and albums with their MBIDs, built once per request.

    A candidate with an MBID matches an owned entry only when the MBIDs agree. A candidate
    or an owned entry without one matches by normalized key (and year, for albums).
    """

    def __init__(self, data: OwnedData | None):
        self._artists: dict[str, list[str | None]] = {}
        self._albums: dict[str, list[tuple[int | None, str | None]]] = {}
        self._artist_entries: dict[str, list[dict[str, Any]]] = {}
        self._genres: set[str] = set()
        if data is None:
            return
        for artist in data.artists:
            self._artists.setdefault(artist["key"], []).append(artist.get("mbid"))
            self._artist_entries.setdefault(artist["key"], []).append(artist)
        for album in data.albums:
            if album.get("genre"):
                self._genres.add(normalize_key(album["genre"]))
            entry = (album["year"], album.get("release_group_mbid"))
            for key in {album["key"], _album_lookup_key(album["artist_key"], album["name"])}:
                self._albums.setdefault(key, []).append(entry)

    def owned_artist(self, candidate: dict[str, Any]) -> dict[str, Any] | None:
        """The owned artist entry this artist candidate matches, or None. Same rule as ``owns``."""
        for entry in self._artist_entries.get(candidate["key"], []):
            if _mbid_match(candidate["mbid"], [entry.get("mbid")]):
                return entry
        return None

    def owns(self, candidate: dict[str, Any]) -> bool:
        if candidate["type"] == "genre":
            return candidate["key"] in self._genres
        if candidate["type"] == "artist":
            owned = self._artists.get(candidate["key"])
            return bool(owned) and _mbid_match(candidate["mbid"], owned)
        keys = {candidate["key"], _album_lookup_key(candidate["artist_key"], candidate["name"])}
        return any(
            _years_match(candidate["year"], year) and _mbid_match(candidate["release_group_mbid"], [mbid])
            for key in keys
            for year, mbid in self._albums.get(key, [])
        )


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
    if candidate["source"] == "discogs":
        base["attribution"] = DISCOGS_ATTRIBUTION
    if candidate["type"] == "genre":
        return {**base, "id": f"{candidate['source']}:{candidate['key']}", "tag": candidate["key"], "tag_source": candidate["source"]}
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
