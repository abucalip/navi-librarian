"""Provider-neutral popularity bonus and discovery lookup wiring.

Owns the personal recommendation popularity bonus pass (backed by batched
ListenBrainz release-group popularity) and the Classics / Deep Dives lookup
bundle, detaching Last.fm client wiring from ``navidrome_server.py`` (D-016).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping

POPULARITY_CANDIDATE_LIMIT = 40


def apply_popularity_bonus(
    candidates: Iterable[dict[str, Any]],
    recent_family_counts: Mapping[str, int],
    popularity_lookup: Callable[[str, str], Mapping[str, Any] | None],
) -> int:
    """Apply the bounded popularity/profile adjustments in place.

    Writes provider-neutral ``listeners``, ``playcount``, ``popularity_tags``,
    and ``popularity_bonus`` fields alongside temporary ``lastfm_*`` aliases
    (to be removed in FirstFM F5.2).

    Returns the number of candidates with usable popularity stats.
    """
    from discovery.recommendations import primary_recent_family, recent_style_families

    checked = 0
    for candidate in sorted(
        candidates,
        key=lambda album: album["discovery_score"],
        reverse=True,
    )[:POPULARITY_CANDIDATE_LIMIT]:
        stats = popularity_lookup(
            candidate.get("primary_artist") or candidate.get("artist", ""),
            candidate.get("album", ""),
        )
        if stats is None:
            continue

        listeners = stats["listeners"]
        playcount = stats["playcount"]
        tags = stats.get("tags", [])

        candidate["listeners"] = listeners
        candidate["playcount"] = playcount
        candidate["popularity_tags"] = tags
        # Temporary aliases until FirstFM F5.2
        candidate["lastfm_listeners"] = listeners
        candidate["lastfm_playcount"] = playcount
        candidate["lastfm_tags"] = tags

        if tags:
            candidate["listening_families"] = sorted(
                recent_style_families(tags)
            )
            candidate["recent_profile_families"] = [
                family for family in candidate["listening_families"]
                if recent_family_counts.get(family, 0) > 0
            ]
            candidate["recent_profile_family"] = primary_recent_family(
                tags, recent_family_counts
            )
            old_profile_bonus = candidate.get("recent_profile_bonus", 1.0)
            matched_families = candidate["recent_profile_families"]
            if matched_families and recent_family_counts:
                max_count = max(recent_family_counts.values())
                average_count = sum(
                    recent_family_counts[family]
                    for family in matched_families
                ) / len(matched_families)
                new_profile_bonus = 1.0 + 0.25 * average_count / max_count
            else:
                new_profile_bonus = 1.0
            candidate["discovery_score"] = (
                candidate["discovery_score"]
                / old_profile_bonus
                * new_profile_bonus
            )
            candidate["recent_profile_bonus"] = new_profile_bonus

        checked += 1
        listener_signal = min(1.0, math.log10(listeners + 1) / 6.0)
        playcount_signal = min(1.0, math.log10(playcount + 1) / 7.0)
        bonus = 1.0 + 0.08 * listener_signal + 0.04 * playcount_signal
        candidate["popularity_bonus"] = bonus
        candidate["lastfm_popularity_bonus"] = bonus
        candidate["discovery_score"] *= bonus
    return checked


def run_personal_popularity_pass(
    albums: Mapping[Any, dict[str, Any]],
    recent_family_counts: Mapping[str, int],
    *,
    metadata_cache_get: Callable[[str, int], Any],
    metadata_cache_set: Callable[[str, Any], None],
    music_key: Callable[[Any], str],
    http_post: Callable[..., Any] | None = None,
    capture_path: str | None = None,
    gathered_override: Any = None,
    provider_tape: Any = None,
    popularity_fn: Callable[[str, str], Any] | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    """Run the batched ListenBrainz popularity pass for personal recommendations.

    Returns ``(albums_checked, recorded_calls)``.
    """
    from recommendation.replay import prepare_lastfm_callback

    if popularity_fn is None:
        if http_post is None:
            import httpx
            http_post = httpx.post
        from integrations.listenbrainz.client import request_headers as lb_headers
        from integrations.listenbrainz.popularity import (
            build_popularity_lookup,
            fetch_release_group_popularity,
        )
        live_popularity = build_popularity_lookup(
            albums.values(),
            POPULARITY_CANDIDATE_LIMIT,
            lambda mbids: fetch_release_group_popularity(
                http_post,
                metadata_cache_get,
                metadata_cache_set,
                mbids,
                headers=lb_headers(),
            ),
            music_key,
        )
    else:
        live_popularity = popularity_fn

    callback, calls = prepare_lastfm_callback(
        capture_path,
        gathered_override,
        provider_tape,
        popularity_fn,
        live_popularity,
    )
    checked = apply_popularity_bonus(
        albums.values(),
        recent_family_counts,
        callback,
    )
    return checked, calls


def candidate_popularity_fields(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Extract provider-neutral popularity fields with temporary ``lastfm_*`` aliases."""
    listeners = candidate.get("listeners")
    if listeners is None:
        listeners = candidate.get("lastfm_listeners")
    playcount = candidate.get("playcount")
    if playcount is None:
        playcount = candidate.get("lastfm_playcount")
    raw_bonus = candidate.get("popularity_bonus")
    if raw_bonus is None:
        raw_bonus = candidate.get("lastfm_popularity_bonus", 1.0)
    bonus = round(raw_bonus, 3)
    return {
        "listeners": listeners,
        "playcount": playcount,
        "popularity_bonus": bonus,
        "lastfm_listeners": listeners,
        "lastfm_playcount": playcount,
        "lastfm_popularity_bonus": bonus,
    }


@dataclass(frozen=True)
class DiscoveryProviderLookups:
    """Lookup callables for Classics and Deep Dives candidate collection."""

    top_albums: Callable[..., list[dict[str, Any]]]
    similar_artists: Callable[..., list[dict[str, Any]]]
    artist_genres: Callable[[str], list[str]]


def build_discovery_lookups(
    *,
    settings_reader: Callable[[], Mapping[str, Any]],
    cache_get: Callable[[str, int], Any],
    cache_set: Callable[[str, Any], None],
    is_album_candidate: Callable[[Mapping[str, Any]], bool],
) -> DiscoveryProviderLookups:
    """Build the Classics / Deep Dives lookup bundle outside ``navidrome_server.py``."""
    from integrations.lastfm import client as lastfm_client_module

    client = lastfm_client_module.LastFmClient(
        settings_reader=settings_reader,
        cache_get=cache_get,
        cache_set=cache_set,
    )

    def top_albums(artist: str, limit: int = 8) -> list[dict[str, Any]]:
        return [
            album for album in client.artist_top_albums(artist, limit=limit)
            if is_album_candidate({"album": album["album"]})
        ]

    return DiscoveryProviderLookups(
        top_albums=top_albums,
        similar_artists=client.similar_artists,
        artist_genres=client.artist_genres,
    )
