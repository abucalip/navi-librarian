"""Pure "similar to" lookup: which artists you listen to share a candidate's genres.

The profile is the recent listening history the recommendation run already has, with the genre
tags it already looked up. Nothing here calls a provider or reads a file.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Iterable, Mapping, Sequence

SIMILAR_ARTIST_LIMIT = 3
PROFILE_ARTIST_LIMIT = 75


def build_profile_artists(
    listens: Iterable[Mapping[str, Any]],
    genre_cache: Mapping[str, Sequence[str]],
    music_key: Callable[[Any], str],
    limit: int = PROFILE_ARTIST_LIMIT,
) -> list[dict[str, Any]]:
    """Most-played recent artists that have genre tags, with their display name and play count."""
    plays: Counter[str] = Counter()
    names: dict[str, str] = {}
    for listen in listens:
        metadata = listen.get("track_metadata", {})
        name = str(metadata.get("artist_name") or "").strip()
        info = metadata.get("additional_info", {}) or {}
        mbid = info.get("artist_mbid")
        mbids = info.get("artist_mbids")
        if not mbid and isinstance(mbids, list) and mbids:
            mbid = mbids[0]
        if not name or not mbid or not genre_cache.get(mbid):
            continue
        plays[mbid] += 1
        names.setdefault(mbid, name)
    return [
        {
            "name": names[mbid],
            "key": music_key(names[mbid]),
            "tags": frozenset(str(tag).casefold() for tag in genre_cache[mbid] if tag),
            "plays": count,
        }
        for mbid, count in plays.most_common(limit)
    ]


def similar_library_artists(
    candidate_tags: Iterable[str],
    candidate_artist_key: str,
    profile_artists: Sequence[Mapping[str, Any]],
    limit: int = SIMILAR_ARTIST_LIMIT,
) -> list[str]:
    """Names of profile artists sharing the most genre tags with the candidate, best first.

    Ties go to the artist you play more. The candidate's own artist is never listed, and an
    artist with no shared tag is never listed, so a candidate with no tags gets an empty list.
    """
    tags = {str(tag).casefold() for tag in candidate_tags if tag}
    if not tags:
        return []
    scored = []
    for artist in profile_artists:
        if artist["key"] == candidate_artist_key:
            continue
        shared = len(tags & artist["tags"])
        if shared:
            scored.append((shared, artist["plays"], artist["name"]))
    scored.sort(key=lambda item: (-item[0], -item[1], item[2].casefold()))
    return [name for _shared, _plays, name in scored[:limit]]
