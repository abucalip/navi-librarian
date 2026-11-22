"""Provider-neutral popularity bonus and discovery lookup wiring.

Owns the personal recommendation popularity bonus pass (backed by batched
ListenBrainz release-group popularity) and the Classics / Deep Dives lookup
bundle (backed by ListenBrainz, MusicBrainz, Deezer, and Discogs), detached
from ``navidrome_server.py`` (D-016).
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import quote

import httpx

POPULARITY_CANDIDATE_LIMIT = 40
_MB_ARTIST_SEARCH_URL = "https://musicbrainz.org/ws/2/artist/"
_LB_RADIO_ARTIST_URL = "https://api.listenbrainz.org/1/lb-radio/artist/"
_LOOKUP_TTL_SECONDS = 30 * 24 * 60 * 60
_LOOKUP_NEGATIVE_TTL_SECONDS = 60 * 60
_DEFAULT_HEADERS = {
    "User-Agent": "Discair/1.0 (personal music discovery; contact: local app)",
    "Accept": "application/json",
}


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
    """Extract provider-neutral popularity fields."""
    listeners = candidate.get("listeners")
    playcount = candidate.get("playcount")
    raw_bonus = candidate.get("popularity_bonus")
    if raw_bonus is None:
        raw_bonus = 1.0
    bonus = round(raw_bonus, 3)
    return {
        "listeners": listeners,
        "playcount": playcount,
        "popularity_bonus": bonus,
    }


@dataclass(frozen=True)
class DiscoveryProviderLookups:
    """Lookup callables for Classics and Deep Dives candidate collection."""

    top_albums: Callable[..., list[dict[str, Any]]]
    similar_artists: Callable[..., list[dict[str, Any]]]
    artist_genres: Callable[[str], list[str]]


def _is_fresh_negative(entry: Any, now: float) -> bool:
    if not isinstance(entry, Mapping) or not entry.get("negative"):
        return False
    at = entry.get("at")
    return isinstance(at, (int, float)) and not isinstance(at, bool) and 0 <= now - at < _LOOKUP_NEGATIVE_TTL_SECONDS


def _resolve_artist_mbid(
    artist: str,
    http_get: Callable[..., Any],
    cache_get: Callable[..., Any],
    cache_set: Callable[[str, Any], None],
    headers: Mapping[str, str],
    lane: Any,
    clock: Callable[[], float] = time.time,
) -> str | None:
    """Resolve ``artist`` to a MusicBrainz artist MBID (cached 30d; 1h negative)."""
    from discovery.search.normalize import normalize_key

    clean = " ".join(str(artist or "").split())
    norm = normalize_key(clean)
    if not norm:
        return None
    cache_key = f"mb:artist-id:{norm}"
    try:
        cached = cache_get(cache_key, _LOOKUP_TTL_SECONDS)
    except Exception:
        cached = None
    if _is_fresh_negative(cached, clock()):
        return None
    if isinstance(cached, Mapping) and cached.get("mbid"):
        return str(cached["mbid"])

    if not lane.acquire():
        return None
    try:
        response = http_get(
            _MB_ARTIST_SEARCH_URL,
            params={"query": f'artist:"{clean}"', "fmt": "json", "limit": 5},
            headers=dict(headers),
            timeout=10,
        )
        if getattr(response, "status_code", None) != 200:
            return None
        artists = (response.json() or {}).get("artists") or []
    except Exception:
        return None

    mbid = None
    for item in artists:
        if not isinstance(item, Mapping):
            continue
        candidate_id = str(item.get("id") or "").strip()
        if candidate_id and normalize_key(str(item.get("name") or "")) == norm:
            mbid = candidate_id
            break
    if not mbid and artists and isinstance(artists[0], Mapping):
        mbid = str(artists[0].get("id") or "").strip() or None

    try:
        if mbid:
            cache_set(cache_key, {"mbid": mbid})
        else:
            cache_set(cache_key, {"negative": True, "at": clock()})
    except Exception:
        pass
    return mbid


def _lb_similar_artists(
    artist_mbid: str,
    limit: int,
    http_get: Callable[..., Any],
    cache_get: Callable[..., Any],
    cache_set: Callable[[str, Any], None],
    headers: Mapping[str, str],
    clock: Callable[[], float] = time.time,
) -> list[dict[str, Any]]:
    """Fetch similar artist names from ListenBrainz ``lb-radio/artist`` (cached 30d)."""
    cache_key = f"lb:similar-records:{artist_mbid}"
    try:
        cached = cache_get(cache_key, _LOOKUP_TTL_SECONDS)
    except Exception:
        cached = None
    if _is_fresh_negative(cached, clock()):
        return []
    if isinstance(cached, list):
        return cached[:limit]

    try:
        response = http_get(
            f"{_LB_RADIO_ARTIST_URL}{quote(artist_mbid, safe='')}",
            params={
                "mode": "easy",
                "max_similar_artists": max(1, int(limit)),
                "max_recordings_per_artist": 1,
                "pop_begin": 0,
                "pop_end": 100,
            },
            headers=dict(headers),
            timeout=10,
        )
        if getattr(response, "status_code", None) != 200:
            return []
        body = response.json()
        if not isinstance(body, Mapping):
            return []
    except Exception:
        return []

    seen: set[str] = set()
    items: list[dict[str, Any]] = []
    for entries in body.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            name = str(entry.get("similar_artist_name") or "").strip()
            mbid = str(entry.get("similar_artist_mbid") or "").strip()
            if not name or mbid == artist_mbid or name in seen:
                continue
            seen.add(name)
            similarity = max(0.1, round(1.0 - len(items) * 0.05, 4))
            items.append({"artist": name, "similarity": similarity})

    try:
        if items:
            cache_set(cache_key, items)
        else:
            cache_set(cache_key, {"negative": True, "at": clock()})
    except Exception:
        pass
    return items[:limit]


def build_discovery_lookups(
    *,
    cache_get: Callable[[str, int], Any],
    cache_set: Callable[[str, Any], None],
    is_album_candidate: Callable[[Mapping[str, Any]], bool],
    settings_reader: Callable[[], Mapping[str, Any]] | None = None,
    http_get: Callable[..., Any] | None = None,
    headers: Mapping[str, str] | None = None,
    lane: Any = None,
) -> DiscoveryProviderLookups:
    """Build the Classics / Deep Dives lookup bundle outside ``navidrome_server.py``."""
    from discovery.artist_tag_fallback import fallback_artist_tags, load_genre_vocabulary
    from integrations.deezer.artist import related_artists as deezer_related_artists
    from integrations.deezer.artist import search_artist_id as deezer_search_artist_id
    from integrations.listenbrainz.popularity import fetch_artist_top_release_groups
    from integrations.provider_gate import musicbrainz_lane

    get = http_get or httpx.get
    req_headers = dict(headers or _DEFAULT_HEADERS)
    mb_lane = lane or musicbrainz_lane()
    genre_vocab_cache: list[set[str]] = []

    def _mbid(artist: str) -> str | None:
        return _resolve_artist_mbid(artist, get, cache_get, cache_set, req_headers, mb_lane)

    def top_albums(artist: str, limit: int = 8) -> list[dict[str, Any]]:
        mbid = _mbid(artist)
        if not mbid:
            return []
        items = fetch_artist_top_release_groups(
            get,
            cache_get,
            cache_set,
            mbid,
            headers=req_headers,
        )
        albums: list[dict[str, Any]] = []
        for item in items:
            name = str(item.get("name") or "").strip()
            if not name or not is_album_candidate({"album": name}):
                continue
            albums.append({
                "artist": artist,
                "album": name,
                "mbid": item.get("release_group_mbid"),
                "listeners": int(item.get("listeners") or 0),
                "playcount": int(item.get("playcount") or 0),
            })
            if len(albums) >= limit:
                break
        return albums

    def similar_artists(artist: str, limit: int = 15) -> list[dict[str, Any]]:
        mbid = _mbid(artist)
        if mbid:
            lb_items = _lb_similar_artists(
                mbid, limit, get, cache_get, cache_set, req_headers,
            )
            if lb_items:
                return lb_items
        deezer_id = deezer_search_artist_id(get, cache_get, cache_set, artist)
        if deezer_id is None:
            return []
        rows = deezer_related_artists(get, cache_get, cache_set, deezer_id, limit=limit)
        return [
            {
                "artist": str(row["name"]).strip(),
                "similarity": max(0.1, round(1.0 - idx * 0.05, 4)),
            }
            for idx, row in enumerate(rows[:limit])
            if row.get("name")
        ]

    def artist_genres(artist: str) -> list[str]:
        mbid = _mbid(artist)
        if not mbid:
            return []
        if not genre_vocab_cache:
            genre_vocab_cache.append(
                load_genre_vocabulary(get, req_headers, cache_get, cache_set, lane=mb_lane)
            )
        vocab = genre_vocab_cache[0]
        if not vocab:
            return []
        token = ""
        if settings_reader is not None:
            try:
                from settings.service import discogs_token_and_source

                token, _ = discogs_token_and_source(settings_reader)
            except Exception:
                token = str((settings_reader() or {}).get("discogs_token") or "").strip()
        tags = fallback_artist_tags(
            [mbid],
            {},
            get=get,
            discogs_token=token,
            artist_names={mbid: artist},
            vocabulary=vocab,
            cache_get=cache_get,
            cache_set=cache_set,
            headers=req_headers,
        )
        return list(tags.get(mbid, []))

    return DiscoveryProviderLookups(
        top_albums=top_albums,
        similar_artists=similar_artists,
        artist_genres=artist_genres,
    )
