"""Injected provider orchestration for new-music recommendations."""
from collections import Counter
from dataclasses import dataclass
import json
from typing import Any, Callable

@dataclass(frozen=True)
class RecommendationProviders:
    listenbrainz_recent: Callable[..., Any]
    listenbrainz_username: Callable[[], str]
    music_key: Callable[[str], str]
    metadata_cache_get: Callable[..., Any]
    metadata_cache_set: Callable[..., Any]
    is_album_candidate: Callable[..., bool]
    api_call: Callable[..., Any]
    items: Callable[..., Any]
    http_get: Callable[..., Any]
    http_client: Callable[..., Any]
    sleep: Callable[[float], Any]

def gather_recommendation_candidates(providers: RecommendationProviders) -> dict[str, Any] | str:
    """Gather providers in legacy order; early errors retain their JSON contract."""
    import time
    import httpx
    try:
        listens = providers.listenbrainz_recent(days=30)
    except Exception as exc:
        return json.dumps({
            "error": f"Could not retrieve recent listening history: {exc}"
        }, ensure_ascii=False, indent=2)

    recent_artists = Counter()
    recent_artist_mbid_counts = Counter()
    for listen in listens:
        metadata = listen.get("track_metadata", {})
        artist = metadata.get("artist_name")
        if artist:
            recent_artists[providers.music_key(artist)] += 1
        additional_info = metadata.get("additional_info", {})
        artist_mbid = additional_info.get("artist_mbid")
        artist_mbids = additional_info.get("artist_mbids", [])
        if not artist_mbid and isinstance(artist_mbids, list) and artist_mbids:
            artist_mbid = artist_mbids[0]
        if artist_mbid:
            recent_artist_mbid_counts[artist_mbid] += 1

    try:
        response = providers.http_get(
            "https://api.listenbrainz.org/1/"
            f"cf/recommendation/user/{providers.listenbrainz_username()}/recording",
            params={"count": 100},
            headers={"User-Agent": "NavidromeLibrarian/1.0"},
            timeout=30,
        )
        response.raise_for_status()
        recommendations = (
            response.json().get("payload", {}).get("mbids", [])
        )
    except Exception as exc:
        return json.dumps({
            "error": f"Could not retrieve ListenBrainz recommendations: {exc}"
        }, ensure_ascii=False, indent=2)

    if not recommendations:
        return json.dumps({
            "recommendations": [],
            "message": "ListenBrainz returned no recording recommendations."
        }, ensure_ascii=False, indent=2)

    # Resolve a bounded number of recordings through MusicBrainz.
    # Group tracks by album before checking Navidrome.
    albums = {}
    failures = []
    headers = {
        "User-Agent": "NavidromeLibrarian/1.0 (personal music discovery)"
    }

    with providers.http_client(timeout=20, follow_redirects=True) as client:
        for index, item in enumerate(recommendations[:100]):
            mbid = item.get("recording_mbid")
            if not mbid:
                continue

            try:
                recording = providers.metadata_cache_get(
                    f"mb:recording:{mbid}",
                    ttl_seconds=180 * 24 * 60 * 60,
                )

                if recording is None:
                    if index:
                        providers.sleep(1.1)

                    response = None
                    for attempt in range(3):
                        response = client.get(
                            f"https://musicbrainz.org/ws/2/recording/{mbid}",
                            params={
                                "fmt": "json",
                                "inc": "artists+releases+release-groups",
                            },
                            headers=headers,
                        )
                        if response.status_code not in (
                            429, 500, 502, 503, 504
                        ):
                            break
                        if attempt < 2:
                            providers.sleep(2 * (attempt + 1))

                    response.raise_for_status()
                    recording = response.json()
                    providers.metadata_cache_set(f"mb:recording:{mbid}", recording)

                credit = recording.get("artist-credit", [])
                artist = "".join(
                    part.get("name", "") + part.get("joinphrase", "")
                    for part in credit
                    if isinstance(part, dict)
                ).strip()
                primary_artist = next(
                    (
                        part.get("name", "")
                        for part in credit
                        if isinstance(part, dict) and part.get("name")
                    ),
                    artist,
                )
                if not artist:
                    artist = primary_artist

                primary_artist_mbid = next(
                    (
                        part.get("artist", {}).get("id")
                        for part in credit
                        if isinstance(part, dict)
                        and isinstance(part.get("artist"), dict)
                        and part["artist"].get("id")
                    ),
                    None,
                )

                releases = recording.get("releases", [])
                album_groups = {}

                # Prefer album release-groups that are not compilations,
                # soundtracks, live albums, remixes, or DJ mixes.
                excluded_types = {
                    "compilation", "soundtrack", "live", "remix", "dj-mix"
                }

                for release in releases:
                    group = release.get("release-group") or {}
                    if group.get("primary-type") != "Album":
                        continue

                    title = group.get("title", "").strip()
                    if not title or not providers.is_album_candidate({
                        "album": title,
                        "primary_type": group.get("primary-type"),
                        "secondary_types": group.get("secondary-types", []),
                    }):
                        continue

                    # Avoid sampler albums and retrospective collections.
                    normalized_title = providers.music_key(title)
                    undesirable_phrases = (
                        "album sampler",
                        " sampler",
                        "greatest hits",
                        "best of",
                        "anthology",
                        "essential collection",
                        "essential",
                        "complete collection",
                    )
                    if any(
                        phrase.strip() in normalized_title
                        for phrase in undesirable_phrases
                    ):
                        continue

                    secondary = {
                        str(value).casefold()
                        for value in group.get("secondary-types", [])
                    }
                    if secondary & excluded_types:
                        continue

                    group_id = group.get("id") or providers.music_key(title)
                    album_groups[group_id] = title

                # Do not mistake a single's title for an album title.
                if not artist or not album_groups:
                    continue

                album_title = next(iter(album_groups.values()))

                key = (providers.music_key(primary_artist), providers.music_key(album_title))
                score = item.get("score", 0)

                if key not in albums:
                    albums[key] = {
                        "artist": artist,
                        "primary_artist": primary_artist,
                        "artist_mbid": primary_artist_mbid,
                        "album": album_title,
                        "score": score,
                        "tracks": [],
                    }

                candidate = albums[key]
                candidate["score"] = max(candidate["score"], score)
                track = recording.get("title", "")
                if track and track not in candidate["tracks"]:
                    candidate["tracks"].append(track)

            except Exception as exc:
                failures.append({"recording_mbid": mbid, "error": str(exc)})

    # Supplement personalized recommendations with regional music discovery.
    # Search release groups by community tags, with cached results and a
    # conservative request rate. These candidates still pass through the
    # normal genre classification and Navidrome ownership checks.
    regional_queries = [
        # Interleave regional discovery with the genres appearing in recent
        # scrobbles, so one broad tag cannot consume the whole candidate budget.
        ('primarytype:album AND tag:rai', 'north-african-middle-eastern', 'north_african'),
        ('primarytype:album AND tag:afrobeats', 'african', 'afrobeats'),
        ('primarytype:album AND tag:"afro-jazz"', 'african', 'afro_jazz'),
        ('primarytype:album AND tag:"desert blues"', 'african', 'malian_desert_blues'),
        ('primarytype:album AND tag:"bossa nova"', 'brazilian', 'other'),
        ('primarytype:album AND tag:soul', 'rnb-soul', 'other'),
        ('primarytype:album AND tag:jazz', 'jazz', 'other'),
        ('primarytype:album AND tag:rock', 'rock', 'other'),
        ('primarytype:album AND tag:gnawa', 'north-african-middle-eastern', 'north_african'),
        ('primarytype:album AND tag:afrobeat', 'african', 'other'),
        ('primarytype:album AND tag:"acid jazz"', 'jazz', 'other'),
        ('primarytype:album AND tag:samba', 'brazilian', 'other'),
        ('primarytype:album AND tag:"malian blues"', 'african', 'malian_desert_blues'),
        ('primarytype:album AND tag:"neo-soul"', 'rnb-soul', 'other'),
        ('primarytype:album AND tag:chaabi', 'north-african-middle-eastern', 'north_african'),
        ('primarytype:album AND tag:mpb', 'brazilian', 'other'),
        ('primarytype:album AND tag:highlife', 'african', 'other'),
        ('primarytype:album AND tag:wassoulou', 'african', 'malian_desert_blues'),
        ('primarytype:album AND tag:amazigh', 'north-african-middle-eastern', 'north_african'),
        ('primarytype:album AND tag:"north african"', 'north-african-middle-eastern', 'north_african'),
    ]
    regional_candidates_added = 0
    regional_results_seen = 0
    regional_request_index = 0

    with providers.http_client(timeout=20, follow_redirects=True) as client:
        for query, regional_family, regional_style in regional_queries:
            if regional_candidates_added >= 60:
                break
            regional_query_added = 0
            cache_key = f"mb:release-group-search:{query}"
            try:
                search_data = providers.metadata_cache_get(
                    cache_key,
                    ttl_seconds=30 * 24 * 60 * 60,
                )

                if search_data is None:
                    if regional_request_index:
                        providers.sleep(1.1)

                    response = client.get(
                        "https://musicbrainz.org/ws/2/release-group/",
                        params={
                            "query": query,
                            "fmt": "json",
                            "limit": 10,
                        },
                        headers=headers,
                    )
                    regional_request_index += 1
                    response.raise_for_status()
                    search_data = response.json()
                    providers.metadata_cache_set(cache_key, search_data)

                for group in search_data.get("release-groups", []):
                    regional_results_seen += 1

                    if group.get("primary-type") != "Album":
                        continue

                    secondary_types = {
                        str(value).casefold()
                        for value in group.get("secondary-types", [])
                    }
                    if secondary_types & {
                        "compilation", "soundtrack", "live",
                        "remix", "dj-mix",
                    }:
                        continue

                    album_title = group.get("title", "").strip()
                    if not album_title or not providers.is_album_candidate({
                        "album": album_title,
                        "primary_type": group.get("primary-type"),
                        "secondary_types": group.get("secondary-types", []),
                    }):
                        continue

                    credit = group.get("artist-credit", [])
                    artist = "".join(
                        part.get("name", "") + part.get("joinphrase", "")
                        for part in credit
                        if isinstance(part, dict)
                    ).strip()

                    primary_artist = next(
                        (
                            part.get("name", "")
                            for part in credit
                            if isinstance(part, dict) and part.get("name")
                        ),
                        artist,
                    )

                    artist_mbid = next(
                        (
                            part.get("artist", {}).get("id")
                            for part in credit
                            if isinstance(part, dict)
                            and isinstance(part.get("artist"), dict)
                            and part["artist"].get("id")
                        ),
                        None,
                    )

                    if not artist or not primary_artist:
                        continue

                    key = (
                        providers.music_key(primary_artist),
                        providers.music_key(album_title),
                    )

                    if key in albums:
                        albums[key]["discovery_source"] = (
                            albums[key].get("discovery_source", "listenbrainz")
                        )
                        regional_families = albums[key].setdefault(
                            "regional_families", []
                        )
                        if regional_family not in regional_families:
                            regional_families.append(regional_family)
                        regional_styles = albums[key].setdefault("regional_styles", [])
                        if regional_style not in regional_styles:
                            regional_styles.append(regional_style)
                        continue

                    if regional_candidates_added >= 60:
                        break

                    albums[key] = {
                        "artist": artist,
                        "primary_artist": primary_artist,
                        "artist_mbid": artist_mbid,
                        "album": album_title,
                        "score": 0.035,
                        "tracks": [],
                        "discovery_source": "musicbrainz_tag_search",
                        "regional_families": [regional_family],
                        "regional_styles": [regional_style],
                    }
                    regional_candidates_added += 1
                    regional_query_added += 1
                    if regional_query_added >= 5:
                        break

                if regional_candidates_added >= 60:
                    break

            except Exception as exc:
                failures.append({
                    "source": "musicbrainz_tag_search",
                    "query": query,
                    "error": str(exc),
                })

    # Build a complete, paginated Navidrome album inventory.

    from discovery_library_snapshot import (
        AlbumInventoryLimitError,
        fetch_album_inventory,
    )

    try:
        library_albums = fetch_album_inventory(providers.api_call, providers.items)
    except AlbumInventoryLimitError as exc:
        return json.dumps({
            "error": "Album inventory exceeded the safety limit.",
            "albums_retrieved": exc.albums_retrieved,
            "recommendations": [],
        }, ensure_ascii=False, indent=2)
    except Exception as exc:
        return json.dumps({
            "error": "Could not retrieve the Navidrome album inventory.",
            "details": str(exc),
            "recommendations": [],
        }, ensure_ascii=False, indent=2)

    library_by_title = {}
    for album in library_albums:
        title_key = providers.music_key(album.get("name", ""))
        if title_key:
            library_by_title.setdefault(title_key, []).append(album)

    # Retrieve MusicBrainz genre tags for a bounded number of artists.
    # Cache results by artist MBID and respect the public API rate limit.
    genre_cache = {}
    artist_ids = []
    seen_artist_ids = set()

    for candidate in sorted(
        albums.values(), key=lambda album: album["score"], reverse=True
    ):
        artist_id = candidate.get("artist_mbid")
        if artist_id and artist_id not in seen_artist_ids:
            seen_artist_ids.add(artist_id)
            artist_ids.append(artist_id)
        if len(artist_ids) >= 60:
            break

    # Add recently scrobbled artists when candidate metadata leaves spare slots.
    # recently, so the genre profile follows current listening rather than
    # only the recommendation candidate pool.
    for artist_id, _listen_count in recent_artist_mbid_counts.most_common(15):
        if artist_id not in seen_artist_ids and len(artist_ids) < 75:
            seen_artist_ids.add(artist_id)
            artist_ids.append(artist_id)

    with providers.http_client(timeout=15, follow_redirects=True) as client:
        for index, artist_id in enumerate(artist_ids):
            try:
                cached_genres = providers.metadata_cache_get(
                    f"mb:artist-genres:{artist_id}",
                    ttl_seconds=90 * 24 * 60 * 60,
                )
                if cached_genres is not None:
                    genre_cache[artist_id] = cached_genres
                    continue

                if index:
                    providers.sleep(1.1)

                response = client.get(
                    f"https://musicbrainz.org/ws/2/artist/{artist_id}",
                    params={"fmt": "json", "inc": "genres"},
                    headers=headers,
                )
                if response.status_code in (429, 500, 502, 503, 504):
                    failures.append({
                        "artist_mbid": artist_id,
                        "error": f"MusicBrainz returned HTTP {response.status_code}",
                    })
                    continue
                response.raise_for_status()
                artist_data = response.json()
                genre_cache[artist_id] = sorted({
                    item.get("name", "").strip().casefold()
                    for item in artist_data.get("genres", [])
                    if item.get("name", "").strip()
                })
                providers.metadata_cache_set(
                    f"mb:artist-genres:{artist_id}",
                    genre_cache[artist_id],
                )
            except Exception as exc:
                failures.append({
                    "artist_mbid": artist_id,
                    "error": str(exc),
                })

    # Broad musical families suggested by the recent listening profile.
    # These are ranking heuristics, not definitive genre classifications.
    from discovery_recommendations import (
        classify_diversity_style,
        genre_families,
        primary_recent_family,
        recent_style_families,
    )

    # Count musical families from actual recent scrobbles. The profile is
    # dynamic: jazz, soul, rock, Brazilian music, and other families rise or
    # fall with the user's listening over the rolling 30-day window.
    recent_family_counts = Counter()
    for listen in listens:
        metadata = listen.get("track_metadata", {})
        additional_info = metadata.get("additional_info", {})
        artist_mbid = additional_info.get("artist_mbid")
        artist_mbids = additional_info.get("artist_mbids", [])
        if not artist_mbid and isinstance(artist_mbids, list) and artist_mbids:
            artist_mbid = artist_mbids[0]
        if not artist_mbid:
            continue
        for family in recent_style_families(genre_cache.get(artist_mbid, [])):
            recent_family_counts[family] += 1

    # Core interests are used to identify close recommendations.
    # African and North African/Middle Eastern music are explicit
    # exploration interests: they should be represented without making
    # every unfamiliar genre automatically count as a core match.
    core_families = {
        "jazz", "hip-hop", "alternative", "rock", "brazilian",
        "rnb-soul", "electronic", "funk",
    }
    exploration_families = {
        "african", "north-african-middle-eastern",
    }
    profile_families = core_families | exploration_families


    return {
        "listens": listens, "recent_artists": recent_artists,
        "recent_artist_mbid_counts": recent_artist_mbid_counts,
        "albums": albums, "failures": failures,
        "library_by_title": library_by_title, "genre_cache": genre_cache,
        "recent_family_counts": recent_family_counts, "core_families": core_families,
        "exploration_families": exploration_families, "profile_families": profile_families,
    }
