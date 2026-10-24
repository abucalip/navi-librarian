"""Adapter helpers that turn enriched candidates into immutable allocation inputs.

Ownership is decided here against the completed library inventory, so the
allocator never queries the library or receives callbacks.
"""
from __future__ import annotations

from typing import Any, Callable, Container, Iterable, Mapping

from discovery.allocation_contract import AllocationCandidate, OwnershipStatus
from discovery.derived_profile import primary_genre_family


def classify_ownership(
    candidate: Mapping[str, Any],
    library_by_title: Mapping[str, list],
    music_key: Callable[[Any], str],
) -> tuple[str, OwnershipStatus]:
    """Return the candidate's normalized title key and its ownership status.

    A same-title library album by the same normalized artist is an exact match;
    the same title under another artist credit is a conflict for manual review.
    """
    title_key = music_key(candidate["album"])
    same_title = library_by_title.get(title_key, [])
    artist_key = music_key(candidate["primary_artist"])
    if any(music_key(match.get("artist", "")) == artist_key for match in same_title):
        return title_key, OwnershipStatus.EXACT_OWNED
    if same_title:
        return title_key, OwnershipStatus.TITLE_CONFLICT
    return title_key, OwnershipStatus.CLEAR


def deep_cuts_fields(
    candidate: Mapping[str, Any],
    popularity: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Deep cuts inputs for one candidate: audience, seed and tag strength.

    Only tag-lane candidates (those carrying a seed in ``regional_styles``) are
    eligible, so the lens draws from its approved source; others get no audience.
    Audience is the album-level listener count by release MBID only: an artist's
    count is a different measure and must not pass the album gate. A candidate
    whose album did not resolve has no audience. ``tag_strength`` is the radio's
    ``tag_count`` carried by the tag lane (0 when absent, then lane order breaks
    ties).
    """
    styles = candidate.get("regional_styles") or []
    seed = str(styles[0]) if styles else None
    if seed is None or not popularity:
        return {"seed": seed}
    found = popularity.get(str(candidate.get("release_group_mbid") or ""))
    audience = found.get("album_listeners") if found else None
    strength = candidate.get("tag_strength")
    return {
        "seed": seed,
        "audience": audience if type(audience) is int and audience >= 0 else None,
        "tag_strength": float(strength) if isinstance(strength, (int, float)) else 0.0,
    }


def _library_artist_names(
    library_by_title: Mapping[str, list],
    music_key: Callable[[Any], str],
    library_artist_mbids: Mapping[str, str],
) -> dict[str, set[str | None]]:
    """{normalized artist name: MBIDs of the library artists with that name}; ``None`` marks a
    library artist whose MBID is unknown."""
    names: dict[str, set[str | None]] = {}
    for matches in library_by_title.values():
        for match in matches:
            key = music_key(match.get("artist", ""))
            if key:
                mbid = library_artist_mbids.get(str(match.get("artistId") or "")) or None
                names.setdefault(key, set()).add(mbid)
    return names


def _artist_is_known(
    candidate: Mapping[str, Any],
    music_key: Callable[[Any], str],
    known_artist_mbids: Container[str],
    library_names: Mapping[str, set[str | None]],
) -> bool:
    mbid = candidate.get("artist_mbid") or None
    if mbid and mbid in known_artist_mbids:
        return True
    library_mbids = library_names.get(music_key(candidate["primary_artist"]))
    if not library_mbids:
        return False
    if mbid is None or None in library_mbids:
        return True
    return mbid in library_mbids


def build_allocation_inputs(
    albums: Iterable[Mapping[str, Any]],
    *,
    library_by_title: Mapping[str, list],
    genre_cache: Mapping[Any, Iterable[Any]],
    music_key: Callable[[Any], str],
    artist_identity: Callable[[Mapping[str, Any]], str],
    popularity: Mapping[str, Mapping[str, Any]] | None = None,
    known_artist_mbids: Container[str] = (),
    library_artist_mbids: Mapping[str, str] | None = None,
) -> tuple[dict[str, Mapping[str, Any]], list[AllocationCandidate]]:
    """Map enriched candidates to allocation candidates, keyed by stable ID.

    ``popularity`` ({release_group_mbid: popularity}) fills the Deep cuts inputs.

    An artist is known when the candidate's artist MBID is in ``known_artist_mbids`` (for
    example the artists in the listening history), or when a library album carries the same
    normalized artist name. A name match is decided by artist MBIDs where both sides have one:
    ``library_artist_mbids`` maps a library album's ``artistId`` to its MusicBrainz ID, and
    two artists that share a name but have different MBIDs are not the same artist. When
    either side has no MBID the name decides, as it does for album ownership."""
    library_names = _library_artist_names(library_by_title, music_key, library_artist_mbids or {})
    candidate_by_id: dict[str, Mapping[str, Any]] = {}
    allocation_candidates: list[AllocationCandidate] = []
    for source_order, candidate in enumerate(albums):
        candidate_id = str(source_order)
        candidate_by_id[candidate_id] = candidate
        title_key, ownership = classify_ownership(candidate, library_by_title, music_key)
        tags = tuple(
            str(tag)
            for tag in genre_cache.get(candidate.get("artist_mbid"), [])
            if tag is not None
        )
        allocation_candidates.append(AllocationCandidate(
            candidate_id=candidate_id,
            artist_key=artist_identity(candidate),
            album_key=title_key,
            category=candidate["discovery_category"],
            score=float(candidate["discovery_score"]),
            source_order=source_order,
            diversity_style=candidate.get("diversity_style", "other"),
            recent_profile_family=candidate.get("recent_profile_family"),
            genre_family=primary_genre_family(tags),
            tags=tags,
            ownership=ownership,
            artist_known=_artist_is_known(
                candidate, music_key, known_artist_mbids, library_names),
            **deep_cuts_fields(candidate, popularity),
        ))
    return candidate_by_id, allocation_candidates
