"""Candidate collection policy for the artist deep-dive discovery list.

Provider access, cache access and pacing are injected by the server adapter.
"""
from collections.abc import Callable, Iterable
from typing import Any

Candidates = dict[tuple[str, str], dict[str, Any]]


def _ordered_anchors(anchors: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(anchors, key=lambda item: item["album_count"], reverse=True)


def _pace(index: int, pause: Callable[[], Any] | None) -> None:
    if pause is not None and index and index % 5 == 0:
        pause()


def collect_missing_album_candidates(
    anchors: Iterable[dict[str, Any]],
    owned_albums: set[tuple[str, str]],
    candidates: Candidates,
    *,
    top_albums_lookup: Callable[..., list[dict[str, Any]]],
    music_key: Callable[[Any], str],
    pause: Callable[[], Any] | None = None,
) -> None:
    """Add unowned top albums of well-represented artists; mutates ``candidates``.

    A duplicate identity is replaced only by a larger ``anchor_album_count``.
    """
    for index, anchor in enumerate(_ordered_anchors(anchors)):
        for album in top_albums_lookup(anchor["name"], limit=8):
            key = (music_key(album["artist"]), music_key(album["album"]))
            if key in owned_albums:
                continue
            candidate = {
                **album,
                "discovery_type": "artist_deep_dive",
                "reason": "Missing album from an artist already well represented in your library",
                "anchor_artist": anchor["name"],
                "anchor_album_count": anchor["album_count"],
                "artist_similarity": 1.0,
            }
            old = candidates.get(key)
            if old is None or candidate["anchor_album_count"] > old["anchor_album_count"]:
                candidates[key] = candidate
        _pace(index, pause)


def merge_resolved_pool_candidates(
    resolved_candidates: Any,
    anchors_by_key: dict[str, dict[str, Any]],
    owned_albums: set[tuple[str, str]],
    candidates: Candidates,
    *,
    music_key: Callable[[Any], str],
) -> None:
    """Reuse resolved personal-pool candidates not selected for the main list.

    Only artists present in ``anchors_by_key`` qualify. Mutates ``candidates``.
    """
    if not isinstance(resolved_candidates, list):
        return
    for candidate in resolved_candidates:
        candidate_artist = str(candidate.get("artist") or "").strip()
        candidate_album = str(candidate.get("album") or "").strip()
        anchor = anchors_by_key.get(music_key(candidate_artist))
        if not anchor or not candidate_album:
            continue
        if candidate.get("exact_owned") or candidate.get("selection_decision") == "selected":
            continue
        key = (music_key(candidate_artist), music_key(candidate_album))
        if key in owned_albums:
            continue
        candidate_score = candidate.get("discovery_score", candidate.get("score", 0))
        try:
            candidate_score = max(0.0, float(candidate_score or 0))
        except (TypeError, ValueError):
            candidate_score = 0.0
        enriched = {
            "artist": candidate_artist,
            "album": candidate_album,
            "mbid": candidate.get("mbid"),
            "year": candidate.get("year") or candidate.get("release_year") or candidate.get("first_release_year"),
            "lastfm_listeners": int(candidate.get("lastfm_listeners") or 0),
            "lastfm_playcount": int(candidate.get("lastfm_playcount") or 0),
            "discovery_type": "artist_deep_dive",
            "discovery_source": "resolved_candidate_pool_beyond_main_selection",
            "reason": (
                "An additional resolved candidate for an artist with at least "
                "three albums in your library; not selected for the main list."
            ),
            "anchor_artist": anchor["name"],
            "anchor_album_count": anchor["album_count"],
            "artist_similarity": 1.0,
            "candidate_pool_score": candidate_score,
            "candidate_pool_category": candidate.get("assigned_category"),
            "genres": candidate.get("genre_tags") or candidate.get("genres") or [],
            "genre_families": candidate.get("genre_families") or [],
        }
        old = candidates.get(key)
        if old is None:
            candidates[key] = enriched
        else:
            old["also_found_in_resolved_candidate_pool"] = True
            old["candidate_pool_score"] = candidate_score
            old["candidate_pool_category"] = candidate.get("assigned_category")


def collect_similar_artist_candidates(
    anchors: Iterable[dict[str, Any]],
    owned_artists: Iterable[str],
    owned_albums: set[tuple[str, str]],
    candidates: Candidates,
    *,
    similar_artists_lookup: Callable[..., list[dict[str, Any]]],
    top_albums_lookup: Callable[..., list[dict[str, Any]]],
    music_key: Callable[[Any], str],
    pause: Callable[[], Any] | None = None,
) -> None:
    """Add top albums of similar artists absent from the library; mutates ``candidates``."""
    owned_artist_keys = set(owned_artists)
    scores: dict[str, dict[str, Any]] = {}
    for index, anchor in enumerate(_ordered_anchors(anchors)):
        for similar in similar_artists_lookup(anchor["name"], limit=15):
            similar_key = music_key(similar["artist"])
            if similar_key in owned_artist_keys:
                continue
            existing = scores.get(similar_key)
            score = similar["similarity"] * (1.0 + min(anchor["album_count"], 15) / 30)
            if existing is None or score > existing["score"]:
                scores[similar_key] = {
                    "artist": similar["artist"],
                    "score": score,
                    "anchor_artist": anchor["name"],
                    "anchor_album_count": anchor["album_count"],
                    "similarity": similar["similarity"],
                }
        _pace(index, pause)

    for similar in scores.values():
        for album in top_albums_lookup(similar["artist"], limit=5):
            key = (music_key(album["artist"]), music_key(album["album"]))
            if key in owned_albums or music_key(album["artist"]) in owned_artist_keys:
                continue
            candidate = {
                **album,
                "discovery_type": "similar_artist",
                "reason": "A similar artist not currently represented in your library",
                "anchor_artist": similar["anchor_artist"],
                "anchor_album_count": similar["anchor_album_count"],
                "artist_similarity": round(similar["similarity"], 4),
                "similar_artist_score": round(similar["score"], 4),
            }
            old = candidates.get(key)
            if old is None or candidate.get("similar_artist_score", 0) > old.get("similar_artist_score", 0):
                candidates[key] = candidate


def enrich_candidate_genres(
    candidates: Iterable[dict[str, Any]],
    *,
    artist_genres: Callable[[str], list[str]],
    genre_families: Callable[[Any], list[str]],
    music_key: Callable[[Any], str],
) -> None:
    """Fill genre tags/families (presentation metadata only); mutates candidates.

    Sparse artists inherit tags from the library anchor that surfaced them.
    """
    cache: dict[str, Any] = {}
    for item in candidates:
        artist_name = str(item.get("artist") or "").strip()
        anchor_name = str(item.get("anchor_artist") or "").strip()
        cache_key = music_key(artist_name)
        if not item.get("genres") and artist_name:
            if cache_key not in cache:
                cache[cache_key] = artist_genres(artist_name)
            item["genres"] = cache[cache_key]
        if not item.get("genres") and anchor_name:
            anchor_key = music_key(anchor_name)
            if anchor_key not in cache:
                cache[anchor_key] = artist_genres(anchor_name)
            item["genres"] = cache[anchor_key]
            item["genre_inherited_from_anchor"] = bool(item["genres"])
        if not item.get("genre_families"):
            item["genre_families"] = genre_families(item.get("genres") or [])
        # Generic tags such as "seen live" may not classify; retry with the anchor.
        if not item.get("genre_families") and anchor_name:
            anchor_key = music_key(anchor_name)
            if not cache.get(anchor_key):
                cache[anchor_key] = artist_genres(anchor_name)
            anchor_families = genre_families(cache.get(anchor_key) or [])
            if anchor_families:
                item["genres"] = cache[anchor_key]
                item["genre_families"] = anchor_families
                item["genre_inherited_from_anchor"] = True
