import hashlib
import json
import os
import random
import shutil
import sqlite3
import time
import unicodedata
import discovery_store
from music_paths import default_music_dir as _default_music_dir_from_environment
import navidrome_client as _navidrome_client
from settings_persistence import SettingsPersistence
from metadata_cache import MetadataCache
from service_settings import (
    get_lastfm_settings as _service_get_lastfm_settings,
    set_lastfm_settings as _service_set_lastfm_settings,
    get_navidrome_settings as _service_get_navidrome_settings,
    listenbrainz_username as _service_listenbrainz_username,
    navidrome_config as _service_navidrome_config,
    set_listenbrainz_settings as _service_set_listenbrainz_settings,
    set_navidrome_settings as _service_set_navidrome_settings,
    get_slskd_settings as _service_get_slskd_settings,
    set_slskd_settings as _service_set_slskd_settings,
    slskd_config as _service_slskd_config,
    test_navidrome_connection as _service_test_navidrome_connection,
    test_lastfm_connection as _service_test_lastfm_connection,
    test_listenbrainz_connection as _service_test_listenbrainz_connection,
)
import acquisition_lifecycle as _acquisition_lifecycle
from acquisition_candidate_start import candidate_start_state as _module_candidate_start_state
from acquisition_monitor_payload import prepare_candidate_for_monitor as _prepare_candidate_for_monitor
import acquisition_orchestration
from acquisition_request_coordinator import acquire_album_request as _acquire_album_request
import acquisition_state as _acquisition_state
from acquisition_source_switch import switch_to_next_source_locked as _switch_to_next_source_locked
from acquisition_recovery import reconcile_interrupted_import as _reconcile_interrupted_import
from acquisition_cleanup import clean_acquisition_source as _clean_acquisition_source
import discovery_refresh
from acquisition_import import import_matched_album_files as _acquisition_import_matched_album_files
from acquisition_completion import (
    filename_key as _acquisition_filename_key,
    inspect_completed_album,
    match_completed_album_files as _acquisition_match_completed_album_files,
    safe_folder_name as _acquisition_safe_folder_name,
)
from pathlib import Path
from urllib.parse import urlparse
from data_directory import resolve_data_dir

import httpx
from dotenv import load_dotenv
from mutagen import File
load_dotenv(Path(__file__).with_name(".env"))

# Mutable application state lives outside the source tree when configured (e.g. Docker /data).
DATA_DIR = resolve_data_dir(os.environ, __file__)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Persistent MusicBrainz metadata cache.
METADATA_CACHE_DB = DATA_DIR / "navidrome_metadata_cache.sqlite3"
_metadata_cache = MetadataCache(METADATA_CACHE_DB)


def _metadata_cache_get(key, ttl_seconds):
    """Compatibility adapter for the extracted metadata cache service."""
    return _metadata_cache.get(key, ttl_seconds)


def _metadata_cache_set(key, value):
    """Compatibility adapter for the extracted metadata cache service."""
    _metadata_cache.set(key, value)

# Environment variables provide first-run defaults; service settings are persistent.

def _default_music_dir():
    """Compatibility adapter for the extracted music-path default policy."""
    return _default_music_dir_from_environment(os.environ, lambda path: path.is_dir())


MUSIC_DIR = _default_music_dir()



def api_call(method, **params):
    """Compatibility adapter for the extracted Navidrome API client."""
    return _navidrome_client.api_call(
        method,
        _navidrome_config,
        **params,
    )


def items(value):
    """Compatibility adapter for Subsonic collection normalization."""
    return _navidrome_client.items(value)


def get_server_source(start_line: int = 1, end_line: int = 200) -> str:
    """Read a bounded section of this MCP server's own source code.

    Read-only. Only reads this Python file; does not accept file paths.
    Returns at most 250 lines per request.
    """
    import json
    import re
    from pathlib import Path

    source_path = Path(__file__).resolve()
    lines = source_path.read_text(encoding="utf-8").splitlines()

    if start_line < 1 or end_line < start_line:
        return json.dumps({"error": "Invalid line range."})

    if end_line - start_line + 1 > 250:
        return json.dumps({
            "error": "Maximum 250 lines per request.",
            "hint": "Request a smaller line range."
        })

    end_line = min(end_line, len(lines))
    secret_pattern = re.compile(
        r"(password|passwd|secret|api[_-]?key|access[_-]?token|"
        r"client[_-]?secret)",
        re.IGNORECASE,
    )
    assignment_pattern = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=")

    result = []
    for number in range(start_line, end_line + 1):
        line = lines[number - 1]
        match = assignment_pattern.match(line)
        if match and secret_pattern.search(match.group(1)):
            line = match.group(1) + " = '[REDACTED]'"
        result.append(f"{number:4}: {line}")

    return json.dumps({
        "file": source_path.name,
        "total_lines": len(lines),
        "start_line": start_line,
        "end_line": end_line,
        "source": "\n".join(result),
    }, ensure_ascii=False, indent=2)


def library_overview() -> str:
    """Summarize the artists and albums recently added to Navidrome."""
    artists_root = api_call("getArtists")
    indexes = artists_root.get("artists", {}).get("index", [])
    artists = [
        artist
        for index in indexes
        for artist in items(index.get("artist"))
    ]

    albums_root = api_call(
        "getAlbumList2",
        type="newest",
        size=20,
        offset=0,
    )
    albums = items(
        albums_root.get("albumList2", {}).get("album")
    )

    return json.dumps({
        "artist_count": len(artists),
        "artist_count_note": (
            "Count reflects artists returned by Navidrome's artist index."
        ),
        "recent_albums": [
            {
                "id": a.get("id"),
                "name": a.get("name"),
                "artist": a.get("artist"),
                "year": a.get("year"),
                "songCount": a.get("songCount"),
            }
            for a in albums
        ],
    }, ensure_ascii=False, indent=2)


def search_music(query: str, category: str = "all") -> str:
    """Search Navidrome for artists, albums, or tracks.

    category must be all, artist, album, or track.
    """
    if not query.strip():
        return "Please provide a search query."

    if category not in {"all", "artist", "album", "track"}:
        return "Invalid category. Use all, artist, album, or track."

    root = api_call(
        "search3",
        query=query.strip(),
        artistCount=10,
        albumCount=10,
        songCount=20,
    )
    result = root.get("searchResult3", {})

    fields = {
        "artist": "artist",
        "album": "album",
        "track": "song",
    }

    output = {}

    for kind, key in fields.items():
        if category not in ("all", kind):
            continue

        records = items(result.get(key))
        output[key] = [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "artist": item.get("artist"),
                "album": item.get("album"),
                "year": item.get("year"),
                "duration": item.get("duration"),
                "playCount": item.get("playCount"),
            }
            for item in records
        ]

    return json.dumps(output, ensure_ascii=False, indent=2)


def get_album_details(album_id: str) -> str:
    """Get album metadata and track listings using an album ID from search_music."""
    if not album_id.strip():
        return "Please provide an album ID."

    root = api_call("getAlbum", id=album_id)
    album = root.get("album", {})

    return json.dumps({
        "id": album.get("id"),
        "name": album.get("name"),
        "artist": album.get("artist"),
        "year": album.get("year"),
        "genre": album.get("genre"),
        "songCount": album.get("songCount"),
        "songs": [
            {
                "id": song.get("id"),
                "title": song.get("title"),
                "artist": song.get("artist"),
                "track": song.get("track"),
                "duration": song.get("duration"),
                "playCount": song.get("playCount"),
            }
            for song in items(album.get("song"))
        ],
    }, ensure_ascii=False, indent=2)


def find_missing_mbids(max_files: int = 1000, offset: int = 0) -> str:
    """Read audio tags and report missing MusicBrainz IDs.

    Scans a bounded number of audio files in sorted path order.
    Does not modify files. Use offset to inspect later batches.
    """
    if not MUSIC_DIR.is_dir():
        return f"Music directory is unavailable: {MUSIC_DIR}"

    if not 1 <= max_files <= 5000:
        return "max_files must be between 1 and 5000."

    if offset < 0:
        return "offset must be non-negative."

    extensions = {
        ".flac", ".mp3", ".m4a", ".mp4", ".ogg",
        ".opus", ".wma", ".aiff", ".aif", ".wav",
    }

    files = sorted(
        p for p in MUSIC_DIR.rglob("*")
        if p.is_file() and p.suffix.lower() in extensions
    )

    batch = files[offset:offset + max_files]
    missing = []
    unreadable = 0

    id_fields = {
        "track_mbid": {
            "musicbrainz_trackid",
            "musicbrainz_track_id",
        },
        "album_mbid": {
            "musicbrainz_albumid",
            "musicbrainz_album_id",
        },
        "artist_mbid": {
            "musicbrainz_artistid",
            "musicbrainz_artist_id",
        },
        "albumartist_mbid": {
            "musicbrainz_albumartistid",
            "musicbrainz_album_artist_id",
        },
    }

    for path in batch:
        try:
            audio = File(path, easy=False)
            if audio is None:
                unreadable += 1
                continue

            tags = audio.tags or {}
            normalized = {
                str(key).casefold(): value
                for key, value in tags.items()
            }

            absent = []

            for field, keys in id_fields.items():
                values = [
                    normalized[key]
                    for key in keys
                    if key in normalized
                ]
                has_value = any(
                    str(value).strip()
                    for group in values
                    for value in (
                        group if isinstance(group, (list, tuple))
                        else [group]
                    )
                )
                if not has_value:
                    absent.append(field)

            if absent:
                missing.append({
                    "file": str(path.relative_to(MUSIC_DIR)),
                    "missing_ids": absent,
                })

        except Exception:
            unreadable += 1

    return json.dumps({
        "directory": str(MUSIC_DIR),
        "total_audio_files_found": len(files),
        "offset": offset,
        "files_in_batch": len(batch),
        "files_with_missing_ids": len(missing),
        "unreadable_files": unreadable,
        "next_offset": offset + len(batch),
        "more_files_remaining": offset + len(batch) < len(files),
        "results": missing,
        "read_only": True,
    }, ensure_ascii=False, indent=2)


def _listenbrainz_recent(days=30, page_limit=3):
    """Fetch recent public ListenBrainz listens in smaller, bounded pages."""
    import time
    import httpx

    min_ts = int(time.time()) - days * 86400
    max_ts = None
    listens = []
    page_size = 100

    headers = {"User-Agent": "NavidromeLibrarian/1.0"}

    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for _ in range(page_limit):
            params = {"min_ts": min_ts, "count": page_size}
            if max_ts is not None:
                params["max_ts"] = max_ts

            response = client.get(
                f"https://api.listenbrainz.org/1/user/{_listenbrainz_username()}/listens",
                params=params,
                headers=headers,
            )
            response.raise_for_status()

            page = response.json().get("payload", {}).get("listens", [])
            if not page:
                break

            listens.extend(page)

            if len(page) < page_size:
                break

            oldest = min(
                int(item.get("listened_at", 0))
                for item in page
            )
            if oldest <= min_ts:
                break

            max_ts = oldest - 1
            time.sleep(0.2)

    return listens


def _artist_identity(candidate):
    from discovery_recommendations import artist_identity
    return artist_identity(candidate)
def _music_key(value):
    from discovery_recommendations import music_key
    return music_key(value)
def _discovery_is_album_candidate(item):
    from discovery_recommendations import is_album_candidate
    return is_album_candidate(item)


LASTFM_LAST_ERROR = None


def _lastfm_album_popularity(artist, album):
    """Return cached Last.fm album listeners/playcount, or None if unavailable."""
    global LASTFM_LAST_ERROR
    api_key = str(_discovery_settings_read().get("lastfm_api_key") or "").strip()
    if not api_key or not artist or not album:
        return None

    cache_key = (
        "lastfm:album-info-v2:"
        + _music_key(artist)
        + ":"
        + _music_key(album)
    )
    cached = _metadata_cache_get(cache_key, ttl_seconds=30 * 24 * 60 * 60)
    if cached is not None:
        return cached

    try:
        response = httpx.get(
            "https://ws.audioscrobbler.com/2.0/",
            params={
                "method": "album.getInfo",
                "api_key": api_key,
                "artist": artist,
                "album": album,
                "autocorrect": 1,
                "format": "json",
            },
            headers={"User-Agent": "NavidromeLibrarian/1.0"},
            timeout=12,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("error"):
            LASTFM_LAST_ERROR = (
                f"Last.fm API error {payload.get('error')}: "
                f"{payload.get('message', 'Unknown API error')}"
            )
            return None
        data = payload.get("album", {})
        # album.getInfo exposes listeners/playcount directly on the album
        # object; accept a nested stats object too for response compatibility.
        stats = data.get("stats") or data
        if not data or not (
            stats.get("listeners") is not None
            or stats.get("playcount") is not None
        ):
            LASTFM_LAST_ERROR = "Last.fm returned no album statistics for a lookup."
            return None
        raw_tags = items((data.get("tags") or {}).get("tag"))
        result = {
            "listeners": int(stats.get("listeners") or 0),
            "playcount": int(stats.get("playcount") or 0),
            "tags": [
                item.get("name", "").strip().casefold()
                for item in raw_tags
                if isinstance(item, dict) and item.get("name", "").strip()
            ],
        }
        _metadata_cache_set(cache_key, result)
        return result
    except httpx.HTTPStatusError as exc:
        # Album-not-found is normal for niche/poorly indexed releases.
        if exc.response.status_code != 404:
            LASTFM_LAST_ERROR = (
                f"Last.fm returned HTTP {exc.response.status_code}."
            )
        return None
    except (httpx.HTTPError, ValueError, TypeError, AttributeError) as exc:
        LASTFM_LAST_ERROR = f"{type(exc).__name__}: Last.fm lookup failed."
        return None


def recent_listening_profile(days: int = 30) -> str:
    """Summarize recent ListenBrainz listening by artist and album.

    Reads public listening history. Does not modify music files.
    """
    from collections import Counter

    if not 1 <= days <= 90:
        return "days must be between 1 and 90."

    try:
        listens = _listenbrainz_recent(days=days)
    except Exception as exc:
        return json.dumps({
            "error": f"Could not retrieve ListenBrainz history: {exc}"
        }, ensure_ascii=False, indent=2)

    artists = Counter()
    albums = Counter()

    for listen in listens:
        meta = listen.get("track_metadata", {})
        artist = meta.get("artist_name", "")
        album = meta.get("release_name", "")
        track = meta.get("track_name", "")

        if artist:
            artists[artist] += 1
        if artist and album:
            albums[(artist, album)] += 1

    return json.dumps({
        "source": "ListenBrainz",
        "username": _listenbrainz_username(),
        "period_days": days,
        "listens_retrieved": len(listens),
        "distinct_artists": len(artists),
        "top_artists": [
            {"artist": artist, "listens": count}
            for artist, count in artists.most_common(15)
        ],
        "top_albums": [
            {"artist": artist, "album": album, "listens": count}
            for (artist, album), count in albums.most_common(10)
        ],
        "note": (
            "History retrieval is bounded to three pages of up to 100 "
            "listens each. If the limit is reached, results may be incomplete."
        ),
        "read_only": True,
    }, ensure_ascii=False, indent=2)


def recommend_new_music(count: int = 10) -> str:
    """Recommend albums from ListenBrainz that do not appear to be in Navidrome.

    Uses personalized recording recommendations, MusicBrainz metadata,
    recent listening context, and Navidrome album searches.
    Does not modify files or playlists.
    """
    import time
    import httpx
    from collections import Counter

    if not 1 <= count <= 20:
        return "count must be between 1 and 20."

    try:
        listens = _listenbrainz_recent(days=30)
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
            recent_artists[_music_key(artist)] += 1
        additional_info = metadata.get("additional_info", {})
        artist_mbid = additional_info.get("artist_mbid")
        artist_mbids = additional_info.get("artist_mbids", [])
        if not artist_mbid and isinstance(artist_mbids, list) and artist_mbids:
            artist_mbid = artist_mbids[0]
        if artist_mbid:
            recent_artist_mbid_counts[artist_mbid] += 1

    try:
        response = httpx.get(
            "https://api.listenbrainz.org/1/"
            f"cf/recommendation/user/{_listenbrainz_username()}/recording",
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

    with httpx.Client(timeout=20, follow_redirects=True) as client:
        for index, item in enumerate(recommendations[:100]):
            mbid = item.get("recording_mbid")
            if not mbid:
                continue

            try:
                recording = _metadata_cache_get(
                    f"mb:recording:{mbid}",
                    ttl_seconds=180 * 24 * 60 * 60,
                )

                if recording is None:
                    if index:
                        time.sleep(1.1)

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
                            time.sleep(2 * (attempt + 1))

                    response.raise_for_status()
                    recording = response.json()
                    _metadata_cache_set(f"mb:recording:{mbid}", recording)

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
                    if not title or not _discovery_is_album_candidate({
                        "album": title,
                        "primary_type": group.get("primary-type"),
                        "secondary_types": group.get("secondary-types", []),
                    }):
                        continue

                    # Avoid sampler albums and retrospective collections.
                    normalized_title = _music_key(title)
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

                    group_id = group.get("id") or _music_key(title)
                    album_groups[group_id] = title

                # Do not mistake a single's title for an album title.
                if not artist or not album_groups:
                    continue

                album_title = next(iter(album_groups.values()))

                key = (_music_key(primary_artist), _music_key(album_title))
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

    with httpx.Client(timeout=20, follow_redirects=True) as client:
        for query, regional_family, regional_style in regional_queries:
            if regional_candidates_added >= 60:
                break
            regional_query_added = 0
            cache_key = f"mb:release-group-search:{query}"
            try:
                search_data = _metadata_cache_get(
                    cache_key,
                    ttl_seconds=30 * 24 * 60 * 60,
                )

                if search_data is None:
                    if regional_request_index:
                        time.sleep(1.1)

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
                    _metadata_cache_set(cache_key, search_data)

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
                    if not album_title or not _discovery_is_album_candidate({
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
                        _music_key(primary_artist),
                        _music_key(album_title),
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

    library_albums = []
    seen_album_ids = set()
    page_size = 500
    inventory_complete = False

    try:
        for offset in range(0, 50000, page_size):
            root = api_call(
                "getAlbumList2",
                type="alphabeticalByName",
                size=page_size,
                offset=offset,
            )
            page = items(root.get("albumList2", {}).get("album"))

            for album in page:
                album_id = album.get("id")
                if album_id and album_id in seen_album_ids:
                    continue
                if album_id:
                    seen_album_ids.add(album_id)
                library_albums.append(album)

            if len(page) < page_size:
                inventory_complete = True
                break

    except Exception as exc:
        return json.dumps({
            "error": "Could not retrieve the Navidrome album inventory.",
            "details": str(exc),
            "recommendations": [],
        }, ensure_ascii=False, indent=2)

    if not inventory_complete:
        return json.dumps({
            "error": "Album inventory exceeded the safety limit.",
            "albums_retrieved": len(library_albums),
            "recommendations": [],
        }, ensure_ascii=False, indent=2)

    library_by_title = {}
    for album in library_albums:
        title_key = _music_key(album.get("name", ""))
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

    with httpx.Client(timeout=15, follow_redirects=True) as client:
        for index, artist_id in enumerate(artist_ids):
            try:
                cached_genres = _metadata_cache_get(
                    f"mb:artist-genres:{artist_id}",
                    ttl_seconds=90 * 24 * 60 * 60,
                )
                if cached_genres is not None:
                    genre_cache[artist_id] = cached_genres
                    continue

                if index:
                    time.sleep(1.1)

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
                _metadata_cache_set(
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
    def genre_families(tags):
        families = set()
        for tag in tags:
            g = tag.casefold()
            if any(x in g for x in ("jazz", "bebop", "hard bop", "swing")):
                families.add("jazz")
            if any(x in g for x in ("hip hop", "hip-hop", "rap")):
                families.add("hip-hop")
            if any(x in g for x in ("alternative", "indie rock", "post-punk",
                                    "art rock", "garage rock")):
                families.add("alternative")
            if any(x in g for x in ("brazilian", "samba", "bossa nova",
                                    "mpb", "tropicalia", "tropicália")):
                families.add("brazilian")
            if any(x in g for x in ("african", "afrobeat", "ethiopian",
                                    "ethiopian jazz", "highlife", "soukous",
                                    "senegalese", "malian", "afropop",
                                    "mbalax", "desert blues")):
                families.add("african")
            if any(x in g for x in ("r&b", "rnb", "neo-soul", "soul")):
                families.add("rnb-soul")
            if any(x in g for x in ("electronic", "electronica", "electropop",
                                    "downtempo", "trip hop", "trip-hop")):
                families.add("electronic")
            if "funk" in g:
                families.add("funk")
            if any(x in g for x in (
                "middle eastern", "arabic", "raï", "rai", "north african",
                "north-african", "maghrebi", "maghreb", "chaabi",
                "gnawa", "gnaoua", "malouf", "andalusi", "andalusian",
                "algerian", "moroccan", "tunisian", "mawwal", "tarab",
                "maqam", "levantine", "khaliji", "khaleeji", "dabke",
                "oud music", "arab pop", "arabic pop", "shaabi",
            )):
                families.add("north-african-middle-eastern")
        return families

    def recent_style_families(tags):
        """Map tags to finer listening-profile families without changing categories."""
        text_tags = [tag.casefold() for tag in tags]
        result = set()
        joined = " ".join(text_tags)
        if any(
            ("jazz" in tag and "jazz rap" not in tag)
            or tag in {"bebop", "swing"}
            for tag in text_tags
        ):
            result.add("jazz")
        if any(term in joined for term in ("soul", "r&b", "rnb", "neo-soul")):
            result.add("soul")
        if any(
            any(term in tag for term in (
                "rock", "punk", "grunge", "metal", "shoegaze", "post-punk"
            ))
            and "electronic rock" not in tag
            for tag in text_tags
        ):
            result.add("rock")
        if any(term in joined for term in (
            "bossa nova", "samba", "mpb", "tropicalia", "tropicália", "brazilian"
        )):
            result.add("bossa_nova_brazilian")
        if any(term in joined for term in ("hip hop", "hip-hop", "rap")):
            result.add("hip-hop")
        if any(term in joined for term in (
            "electronic", "electronica", "house", "techno", "edm",
            "synth-pop", "synthpop", "idm", "trip hop", "trip-hop"
        )):
            result.add("electronic")
        if any(term in joined for term in (
            "african", "afrobeat", "afrobeats", "afropop", "highlife",
            "malian", "tuareg", "desert blues", "soukous", "mbalax"
        )):
            result.add("african")
        if any(term in joined for term in (
            "raï", "rai", "gnawa", "chaabi", "maghreb", "north african",
            "algerian", "moroccan", "tunisian", "amazigh"
        )):
            result.add("north_african")
        if "funk" in joined:
            result.add("funk")
        if any(term in joined for term in ("pop", "dance-pop", "synthpop")):
            result.add("pop")
        return result

    def primary_recent_family(tags, family_counts):
        """Choose a representative family from more album-specific tags first."""
        families = recent_style_families(tags)
        has_hiphop_tag = any(
            any(term in tag for term in ("hip hop", "hip-hop", "rap"))
            for tag in tags
        )
        has_specific_jazz_tag = any(
            any(term in tag for term in (
                "acid jazz", "afro-jazz", "afro jazz", "jazz fusion",
                "free jazz", "latin jazz", "ethiopian jazz", "ethio-jazz",
            ))
            for tag in tags
        )
        priority = ["bossa_nova_brazilian", "rock", "hip-hop", "soul",
                    "electronic", "african", "north_african", "funk", "pop"]
        if "jazz" in families and (not has_hiphop_tag or has_specific_jazz_tag):
            priority.insert(1, "jazz")
        for family in priority:
            if family in families:
                return family
        return max(
            families,
            key=lambda family: family_counts.get(family, 0),
            default=None,
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

    found = []
    possible_matches = []
    checked = 0
    artist_recommendation_counts = Counter()

    # Rank for discovery, not just ListenBrainz similarity.
    # Recent familiarity lowers priority; unfamiliar artists get a boost.
    for candidate in albums.values():
        recent_count = recent_artists.get(
            _music_key(candidate["primary_artist"]), 0
        )
        if recent_count == 0:
            familiarity_factor = 1.35
        elif recent_count <= 2:
            familiarity_factor = 1.20
        elif recent_count <= 5:
            familiarity_factor = 1.05
        elif recent_count <= 10:
            familiarity_factor = 0.90
        else:
            familiarity_factor = 0.75

        # Give the explicitly requested exploration families a modest boost.
        candidate_tags = genre_cache.get(candidate.get("artist_mbid"), [])
        candidate_families = genre_families(candidate_tags)
        exploration_bonus = (
            1.10
            if candidate_families & exploration_families
            else 1.0
        )

        candidate["discovery_score"] = (
            candidate["score"] * familiarity_factor * exploration_bonus
        )

    # Classify candidates using available MusicBrainz genres and a separate
    # regional/style label used to encourage variety in the final shortlist.
    def classify_diversity_style(candidate, tags):
        artist_key = _music_key(
            candidate.get("primary_artist") or candidate.get("artist", "")
        )
        tag_text = " ".join(tags).casefold()
        regional_style_hints = candidate.get("regional_styles", [])
        for style_hint in (
            "north_african", "afrobeats", "afro_jazz",
            "malian_desert_blues",
        ):
            if style_hint in regional_style_hints:
                return style_hint

        north_african_names = {
            "chebmami", "khaled", "chebkhaled", "faudel", "rachidtaha",
            "idir", "souadmassi", "hamidelkasri", "takfarinas", "bouchenak",
            "liliboniche", "orchestrenationaldebarbes", "chebsahraoui",
            "شابصحراوي",
        }
        desert_blues_names = {
            "vieuxfarkatoure", "alifarkatoure", "bombino", "tinariwen",
            "mdoumoctar", "imarhan",
        }

        if (
            artist_key in north_african_names
            or any(term in tag_text for term in (
                "raï", "rai", "chaabi", "gnawa", "amazigh",
                "north african", "north-african", "maghreb", "algerian",
            ))
        ):
            return "north_african"
        if any(term in tag_text for term in (
            "afrobeats", "afro-beats", "afropop", "afro-pop",
        )):
            return "afrobeats"
        if any(term in tag_text for term in (
            "afro-jazz", "afro jazz", "african jazz", "ethio-jazz",
            "ethiojazz", "south african jazz",
        )):
            return "afro_jazz"
        if (
            artist_key in desert_blues_names
            or any(term in tag_text for term in (
                "desert blues", "malian blues", "malian guitar", "tuareg",
                "assouf", "wassoulou",
            ))
        ):
            return "malian_desert_blues"
        return "other"

    candidates_by_category = {
        "adjacent": [],
        "cross_genre": [],
        "adventurous": [],
        "unclassified": [],
    }

    for candidate in albums.values():
        tags = genre_cache.get(candidate.get("artist_mbid"), [])
        candidate["diversity_style"] = classify_diversity_style(candidate, tags)
        families = genre_families(tags)
        families.update(candidate.get("regional_families", []))
        # Correct known regional artists when MusicBrainz genre tags are incomplete.
        artist_key = _music_key(candidate.get("primary_artist") or candidate.get("artist", ""))
        regional_names = {
            # Keys must match _music_key(), which removes spaces and punctuation.
            "chebmami": "north-african-middle-eastern",
            "vieuxfarkatoure": "african",
            "alifarkatoure": "african",
            "bombino": "african",
            "tinariwen": "african",
            "mdoumoctar": "african",
            "imarhan": "african",
            "khaled": "north-african-middle-eastern",
            "chebkhaled": "north-african-middle-eastern",
            "faudel": "north-african-middle-eastern",
            "rachidtaha": "north-african-middle-eastern",
            "idir": "north-african-middle-eastern",
            "souadmassi": "north-african-middle-eastern",
            "hamidelkasri": "north-african-middle-eastern",
            "takfarinas": "north-african-middle-eastern",
            "bouchenak": "north-african-middle-eastern",
            "liliboniche": "north-african-middle-eastern",
            "orchestrenationaldebarbes": "north-african-middle-eastern",
            "chebsahraoui": "north-african-middle-eastern",
            "شابصحراوي": "north-african-middle-eastern",
        }
        if artist_key in regional_names:
            families.add(regional_names[artist_key])
        core_overlap = families & core_families
        exploration_overlap = families & exploration_families

        adventurous_tags = (
            "idm", "experimental", "avant-garde", "avant garde",
            "free improvisation", "free jazz", "drone", "noise",
            "musique concrète", "musique concrete",
            "electroacoustic", "dark ambient", "glitch",
            "deconstructed club",
        )
        adventurous_signal = any(
            signal in tag.casefold()
            for tag in tags
            for signal in adventurous_tags
        )

        if not tags and not families:
            category = "unclassified"
        elif adventurous_signal:
            category = "adventurous"
        elif len(core_overlap) >= 2:
            category = "cross_genre"
        elif core_overlap or exploration_overlap:
            category = "adjacent"
        else:
            category = "adventurous"

        candidate["genres"] = tags
        candidate["genre_families"] = sorted(families)
        candidate["listening_families"] = sorted(recent_style_families(tags))
        candidate["recent_profile_families"] = [
            family for family in candidate["listening_families"]
            if recent_family_counts.get(family, 0) > 0
        ]
        candidate["recent_profile_family"] = primary_recent_family(
            tags, recent_family_counts
        )
        profile_family = candidate["recent_profile_family"]
        matched_profile_families = candidate["recent_profile_families"]
        if matched_profile_families and recent_family_counts:
            max_recent_family_count = max(recent_family_counts.values())
            average_recent_count = sum(
                recent_family_counts[family]
                for family in matched_profile_families
            ) / len(matched_profile_families)
            profile_match_bonus = (
                1.0 + 0.10 * (
                    average_recent_count / max_recent_family_count
                )
            )
            candidate["recent_profile_bonus"] = profile_match_bonus
            candidate["discovery_score"] *= profile_match_bonus
        else:
            candidate["recent_profile_bonus"] = 1.0
        candidate["discovery_category"] = category
        candidate["genre_metadata_available"] = bool(tags)

        candidates_by_category[category].append(candidate)

    # Last.fm popularity is a small confidence signal, not a replacement for
    # personalized relevance. Query a bounded top slice and cache for 30 days.
    lastfm_checked = 0
    lastfm_available = bool(_discovery_settings_read().get("lastfm_api_key"))
    for candidate in sorted(
        albums.values(),
        key=lambda album: album["discovery_score"],
        reverse=True,
    )[:40]:
        stats = _lastfm_album_popularity(
            candidate.get("primary_artist") or candidate.get("artist", ""),
            candidate.get("album", ""),
        )
        if stats is None:
            continue
        candidate["lastfm_listeners"] = stats["listeners"]
        candidate["lastfm_playcount"] = stats["playcount"]
        candidate["lastfm_tags"] = stats.get("tags", [])
        if candidate["lastfm_tags"]:
            candidate["listening_families"] = sorted(
                recent_style_families(candidate["lastfm_tags"])
            )
            candidate["recent_profile_families"] = [
                family for family in candidate["listening_families"]
                if recent_family_counts.get(family, 0) > 0
            ]
            candidate["recent_profile_family"] = primary_recent_family(
                candidate["lastfm_tags"], recent_family_counts
            )
            old_profile_bonus = candidate.get("recent_profile_bonus", 1.0)
            matched_families = candidate["recent_profile_families"]
            if matched_families and recent_family_counts:
                max_count = max(recent_family_counts.values())
                average_count = sum(
                    recent_family_counts[family]
                    for family in matched_families
                ) / len(matched_families)
                new_profile_bonus = 1.0 + 0.10 * average_count / max_count
            else:
                new_profile_bonus = 1.0
            candidate["discovery_score"] = (
                candidate["discovery_score"]
                / old_profile_bonus
                * new_profile_bonus
            )
            candidate["recent_profile_bonus"] = new_profile_bonus
        lastfm_checked += 1
        listener_signal = min(
            1.0, __import__("math").log10(stats["listeners"] + 1) / 6.0
        )
        playcount_signal = min(
            1.0, __import__("math").log10(stats["playcount"] + 1) / 7.0
        )
        candidate["lastfm_popularity_bonus"] = (
            1.0 + 0.08 * listener_signal + 0.04 * playcount_signal
        )
        candidate["discovery_score"] *= candidate["lastfm_popularity_bonus"]

    for group in candidates_by_category.values():
        group.sort(
            key=lambda album: album["discovery_score"],
            reverse=True,
        )

    # Allocate targets proportionally for non-default count values too.
    targets = {
        "adjacent": (count * 4) // 10,
        "cross_genre": (count * 3) // 10,
    }
    targets["adventurous"] = count - sum(targets.values())

    selected_counts = Counter()
    selected_styles = Counter()
    selected_profile_families = Counter()
    diversity_style_targets = {
        "north_african": 1,
        "afrobeats": 1,
        "afro_jazz": 1,
        "malian_desert_blues": 1,
    }
    processed = set()
    candidate_decisions = {}

    def record_decision(candidate, status, reason):
        previous = candidate_decisions.get(id(candidate))
        if previous and previous.get("status") == "selected":
            return
        candidate_decisions[id(candidate)] = {
            "status": status,
            "reason": reason,
        }

    def consider(
        candidate,
        allow_over_quota=False,
        allow_over_family_cap=False,
        allow_over_diversity_style=False,
    ):
        nonlocal checked
        category = candidate["discovery_category"]
        style = candidate.get("diversity_style", "other")
        if (
            not allow_over_diversity_style
            and style in diversity_style_targets
            and selected_styles[style] >= diversity_style_targets[style]
        ):
            record_decision(
                candidate,
                "diversity_style_target_filled",
                f"The target of {diversity_style_targets[style]} recommendation "
                f"for the {style} diversity slot was already filled.",
            )
            return

        profile_family = candidate.get("recent_profile_family")
        if (
            not allow_over_family_cap
            and style not in diversity_style_targets
            and profile_family
            and selected_profile_families[profile_family] >= 1
        ):
            record_decision(
                candidate,
                "recent_genre_cap_reached",
                f"The recent-listening family {profile_family} already has a "
                "recommendation; another family is preferred.",
            )
            return

        key = (
            _artist_identity(candidate),
            _music_key(candidate["album"]),
        )
        if key in processed:
            candidate_decisions.setdefault(
                id(candidate),
                {
                    "status": "duplicate_candidate",
                    "reason": (
                        "The same artist and album identity was already "
                        "processed."
                    ),
                },
            )
            return

        if checked >= 60:
            record_decision(
                candidate,
                "not_considered",
                "The candidate search limit of 60 checks was reached.",
            )
            return

        if (
            not allow_over_quota
            and category in targets
            and selected_counts[category] >= targets[category]
        ):
            record_decision(
                candidate,
                "category_quota_filled",
                f"The target of {targets[category]} recommendations "
                f"for the {category} category was already filled.",
            )
            return

        if len(found) >= count:
            record_decision(
                candidate,
                "not_considered",
                "The requested number of recommendations was already reached.",
            )
            return

        processed.add(key)

        artist_key = _artist_identity(candidate)
        if artist_recommendation_counts[artist_key] >= 1:
            record_decision(
                candidate,
                "artist_already_selected",
                "Another album by this artist has already been selected.",
            )
            return

        checked += 1
        title_key = _music_key(candidate["album"])
        same_title = library_by_title.get(title_key, [])

        exact_owned = any(
            _music_key(match.get("artist", ""))
            == _music_key(candidate["primary_artist"])
            for match in same_title
        )
        if exact_owned:
            record_decision(
                candidate,
                "already_owned",
                "A normalized album-title and artist-credit match exists "
                "in the indexed Navidrome inventory.",
            )
            return

        category = candidate["discovery_category"]
        recent_count = recent_artists.get(_music_key(candidate["primary_artist"]), 0)

        result = {
            "artist": candidate["artist"],
            "album": candidate["album"],
            "discovery_category": category,
            "diversity_style": candidate.get("diversity_style", "other"),
            "genres": candidate["genres"],
            "genre_families": candidate["genre_families"],
            "recent_profile_family": candidate.get("recent_profile_family"),
            "recent_profile_families": candidate.get("recent_profile_families", []),
            "recent_profile_bonus": round(
                candidate.get("recent_profile_bonus", 1.0), 3
            ),
            "genre_metadata_available": candidate["genre_metadata_available"],
            "listenbrainz_score": (
                candidate["score"]
                if candidate.get("discovery_source", "listenbrainz")
                == "listenbrainz"
                else None
            ),
            "discovery_source": candidate.get(
                "discovery_source", "listenbrainz"
            ),
            "discovery_score": round(candidate["discovery_score"], 6),
            "recent_artist_listens": recent_count,
            "lastfm_listeners": candidate.get("lastfm_listeners"),
            "lastfm_playcount": candidate.get("lastfm_playcount"),
            "lastfm_tags": candidate.get("lastfm_tags", []),
            "lastfm_popularity_bonus": round(
                candidate.get("lastfm_popularity_bonus", 1.0), 3
            ),
            "suggested_tracks": candidate["tracks"][:3],
            "reason": (
                {
                    "adjacent": "Genre tags connect this artist to your "
                                "established musical interests.",
                    "cross_genre": "Genre tags suggest a bridge between "
                                   "multiple musical families in your profile.",
                    "adventurous": "Available genre tags suggest a "
                                   "departure from the strongest mapped "
                                   "genre matches.",
                    "unclassified": "Genre metadata is unavailable, so this "
                                    "candidate's musical fit is uncertain."
                }[category]
                + (
                    " Genre metadata was unavailable, so this classification "
                    "has low confidence."
                    if not candidate["genre_metadata_available"]
                    else ""
                )
            ),
        }

        if same_title:
            result["ownership_note"] = (
                "A same-title album exists in Navidrome under a different "
                "artist credit. Review before treating this as new."
            )
            possible_matches.append(result)
            record_decision(
                candidate,
                "held_for_ownership_review",
                "The album title exists in Navidrome under a different "
                "artist credit; manual review is recommended.",
            )
            return

        result["ownership_check"] = (
            "No exact normalized album-title match found in the indexed "
            "Navidrome inventory; alternate editions may still exist."
        )
        found.append(result)
        record_decision(
            candidate,
            "selected",
            "Passed the ownership checks and was added to the recommendations.",
        )
        artist_recommendation_counts[artist_key] += 1
        selected_counts[category] += 1
        selected_styles[candidate.get("diversity_style", "other")] += 1
        if candidate.get("diversity_style", "other") not in diversity_style_targets:
            profile_family = candidate.get("recent_profile_family")
            if profile_family:
                selected_profile_families[profile_family] += 1

    # First reserve one slot for each requested regional/style family where
    # a suitable, unowned candidate exists and category quotas permit it.
    for style, style_target in diversity_style_targets.items():
        if len(found) >= count or checked >= 60:
            break
        if selected_styles[style] >= style_target:
            continue
        style_candidates = sorted(
            (
                candidate
                for candidate in albums.values()
                if candidate.get("diversity_style") == style
            ),
            key=lambda candidate: candidate["discovery_score"],
            reverse=True,
        )
        for candidate in style_candidates:
            if selected_styles[style] >= style_target:
                break
            consider(candidate)
            if len(found) >= count or checked >= 60:
                break

    # Fill remaining category targets after the diversity pass.
    for category in ("adjacent", "cross_genre", "adventurous"):
        for candidate in candidates_by_category[category]:
            if selected_counts[category] >= targets[category]:
                break
            consider(candidate)
            if len(found) >= count or checked >= 60:
                break
        if len(found) >= count or checked >= 60:
            break

    # If genre variety leaves a category short, relax the family cap before
    # relaxing the 4/3/3 category balance or using unclassified candidates.
    for category in ("adjacent", "cross_genre", "adventurous"):
        if len(found) >= count or checked >= 60:
            break
        for candidate in candidates_by_category[category]:
            if selected_counts[category] >= targets[category]:
                break
            consider(candidate, allow_over_family_cap=True)
            if len(found) >= count or checked >= 60:
                break

    # Do not silently exceed category targets during fallback.
    # First, try to fill any remaining target slots in their own categories.
    if len(found) < count and checked < 60:
        for category in ("adjacent", "cross_genre", "adventurous"):
            if selected_counts[category] >= targets[category]:
                continue
            for candidate in candidates_by_category[category]:
                if selected_counts[category] >= targets[category]:
                    break
                consider(candidate)
                if len(found) >= count or checked >= 60:
                    break
            if len(found) >= count or checked >= 60:
                break

    # If a genre-based category cannot fill its target, use unclassified
    # candidates for the remaining slots rather than silently exceeding the
    # adjacent or cross-genre quotas. Keep their category explicitly uncertain.
    if len(found) < count and checked < 60:
        remaining_unclassified = sorted(
            candidates_by_category["unclassified"],
            key=lambda candidate: candidate["discovery_score"],
            reverse=True,
        )
        for candidate in remaining_unclassified:
            if len(found) >= count or checked >= 60:
                break
            consider(candidate, allow_over_quota=True)

    # Final fallback: fill any remaining slots from the strongest candidates
    # across all categories, relaxing category, family, and style caps only
    # after the normal allocation attempts have been exhausted.
    if len(found) < count and checked < 60:
        remaining_candidates = sorted(
            (
                candidate
                for category in (
                    "adjacent",
                    "cross_genre",
                    "adventurous",
                    "unclassified",
                )
                for candidate in candidates_by_category[category]
            ),
            key=lambda candidate: candidate["discovery_score"],
            reverse=True,
        )
        for candidate in remaining_candidates:
            if len(found) >= count or checked >= 60:
                break
            consider(
                candidate,
                allow_over_quota=True,
                allow_over_family_cap=True,
                allow_over_diversity_style=True,
            )


    # Temporary diagnostics: inspect all resolved candidates before return.
    candidate_debug = []
    candidate_category_counts = Counter()

    for candidate in albums.values():
        tags = genre_cache.get(candidate.get("artist_mbid"), [])
        families = genre_families(tags)
        families.update(candidate.get("regional_families", []))

        # Keep diagnostic classifications consistent with the selection pass.
        artist_key = _music_key(candidate.get("primary_artist") or candidate.get("artist", ""))
        regional_names = {
            "chebmami": "north-african-middle-eastern",
            "vieuxfarkatoure": "african",
            "alifarkatoure": "african",
            "bombino": "african",
            "tinariwen": "african",
            "mdoumoctar": "african",
            "imarhan": "african",
            "khaled": "north-african-middle-eastern",
            "chebkhaled": "north-african-middle-eastern",
            "faudel": "north-african-middle-eastern",
            "rachidtaha": "north-african-middle-eastern",
            "idir": "north-african-middle-eastern",
            "souadmassi": "north-african-middle-eastern",
            "hamidelkasri": "north-african-middle-eastern",
            "takfarinas": "north-african-middle-eastern",
            "bouchenak": "north-african-middle-eastern",
            "liliboniche": "north-african-middle-eastern",
            "orchestrenationaldebarbes": "north-african-middle-eastern",
            "chebsahraoui": "north-african-middle-eastern",
            "شابصحراوي": "north-african-middle-eastern",
        }
        if artist_key in regional_names:
            families.add(regional_names[artist_key])

        adventurous_tags = (
            "idm", "experimental", "avant-garde", "avant garde",
            "free improvisation", "free jazz", "drone", "noise",
            "musique concrète", "musique concrete",
            "electroacoustic", "dark ambient", "glitch",
            "deconstructed club",
        )
        adventurous_signal = any(
            signal in tag.casefold()
            for tag in tags
            for signal in adventurous_tags
        )

        core_overlap = families & core_families
        exploration_overlap = families & exploration_families

        if not tags and not families:
            category = "unclassified"
        elif adventurous_signal:
            category = "adventurous"
        elif len(core_overlap) >= 2:
            category = "cross_genre"
        elif core_overlap or exploration_overlap:
            category = "adjacent"
        else:
            category = "adventurous"

        title_key = _music_key(candidate["album"])
        same_title = library_by_title.get(title_key, [])
        exact_owned = any(
            _music_key(match.get("artist", ""))
            == _music_key(candidate["primary_artist"])
            for match in same_title
        )

        candidate_category_counts[category] += 1

        decision = candidate_decisions.get(id(candidate))
        if decision is None:
            if category == "unclassified":
                decision = {
                    "status": "not_considered",
                    "reason": (
                        "Candidates without genre metadata are not included "
                        "in the three-category selection allocation."
                    ),
                }
            elif (
                category in targets
                and selected_counts[category] >= targets[category]
            ):
                decision = {
                    "status": "category_quota_filled",
                    "reason": (
                        f"The target of {targets[category]} recommendations "
                        f"for the {category} category was already filled."
                    ),
                }
            elif len(found) >= count:
                decision = {
                    "status": "not_considered",
                    "reason": (
                        "The requested number of recommendations was reached "
                        "before this candidate was evaluated."
                    ),
                }
            elif checked >= 60:
                decision = {
                    "status": "not_considered",
                    "reason": (
                        "The candidate search limit of 60 checks was reached "
                        "before this candidate was evaluated."
                    ),
                }
            else:
                decision = {
                    "status": "not_considered",
                    "reason": (
                        "The candidate was not reached by the selection loops."
                    ),
                }

        candidate_debug.append({
            "artist": candidate["artist"],
            "album": candidate["album"],
            "diversity_style": candidate.get("diversity_style", "other"),
            "score": candidate["score"],
            "discovery_score": round(
                candidate.get("discovery_score", 0), 6
            ),
            "genre_tags": tags,
            "genre_families": sorted(families),
            "recent_profile_family": candidate.get("recent_profile_family"),
            "recent_profile_families": candidate.get("recent_profile_families", []),
            "recent_profile_bonus": round(
                candidate.get("recent_profile_bonus", 1.0), 3
            ),
            "lastfm_listeners": candidate.get("lastfm_listeners"),
            "lastfm_playcount": candidate.get("lastfm_playcount"),
            "lastfm_popularity_bonus": round(
                candidate.get("lastfm_popularity_bonus", 1.0), 3
            ),
            "assigned_category": category,
            "genre_metadata_available": bool(tags),
            "exact_owned": exact_owned,
            "same_title_library_matches": len(same_title),
            "already_selected_artist": (
                _artist_identity(candidate)
                in artist_recommendation_counts
            ),
            "selection_decision": decision["status"],
            "selection_reason": decision["reason"],
        })

    candidate_debug.sort(
        key=lambda item: item["discovery_score"],
        reverse=True,
    )

    return json.dumps({
        "source": (
            "ListenBrainz + MusicBrainz + Last.fm + Navidrome"
        ),
        "regional_candidates_added": regional_candidates_added,
        "regional_search_results_seen": regional_results_seen,
        "recent_history_days": 30,
        "recent_listens_retrieved": len(listens),
        "recent_genre_profile_listens_classified": sum(recent_family_counts.values()),
        "recent_genre_family_counts": dict(
            recent_family_counts.most_common()
        ),
        "selected_recent_genre_families": dict(selected_profile_families),
        "lastfm_api_configured": lastfm_available,
        "lastfm_albums_checked": lastfm_checked,
        "lastfm_last_error": LASTFM_LAST_ERROR,
        "recommendations": found,
        "debug_candidate_category_counts": dict(candidate_category_counts),
        "debug_all_candidates": candidate_debug,

        "category_targets": targets,
        "category_counts": dict(selected_counts),
        "category_shortfalls": {
            category: max(0, target - selected_counts.get(category, 0))
            for category, target in targets.items()
        },
        "category_targets_met": all(
            selected_counts.get(category, 0) >= target
            for category, target in targets.items()
        ),
        "recommendations_returned": len(found),
        "unclassified_recommendations": sum(
            1 for recommendation in found
            if recommendation.get("discovery_category") == "unclassified"
        ),
        "diversity_style_targets": diversity_style_targets,
        "diversity_style_counts": {
            style: selected_styles.get(style, 0)
            for style in diversity_style_targets
        },
        "possible_library_matches": possible_matches,
        "candidate_albums_resolved": len(albums),
        "artists_genre_checked": len(genre_cache),
        "library_albums_indexed": len(library_albums),
        "metadata_lookup_errors": failures[:10],
        "limitations": [
            "Up to the first 100 ListenBrainz recording recommendations are resolved.",
            "Genre tags are community-supplied and may be missing or incomplete.",
            "Candidates without genre tags are classified as unclassified, not adventurous.",
            "MusicBrainz genres are retrieved for up to 60 candidate artists plus up to 15 recently scrobbled artists.",
            "Last.fm album listeners and playcounts are cached for 30 days and provide a capped popularity bonus; missing album data is ignored.",
            "Recent genre balance uses a rolling 30-day scrobble profile and may be limited by available artist MBIDs and genre tags.",
            "Ownership checks use normalized album titles and artist credits; "
            "alternate editions or artist aliases may need manual review.",
            "Recommendations are read-only and no files or playlists are changed."
        ],
    }, ensure_ascii=False, indent=2)


# Persistent discovery state and settings live in the configurable data directory.
DISCOVERY_DB = DATA_DIR / "navidrome_discovery.sqlite3"
_DISCOVERY_REFRESH_LOCK = __import__("threading").Lock()


def _discovery_init():
    with sqlite3.connect(DISCOVERY_DB, timeout=10) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS discovery_feedback (
                scope TEXT NOT NULL,
                artist_key TEXT NOT NULL,
                album_key TEXT NOT NULL DEFAULT '',
                artist TEXT NOT NULL,
                album TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                PRIMARY KEY (scope, artist_key, album_key)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS discovery_lists (
                name TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                generated_at REAL NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS discovery_acquisitions (
                artist_key TEXT NOT NULL,
                album_key TEXT NOT NULL,
                artist TEXT NOT NULL,
                album TEXT NOT NULL,
                status TEXT NOT NULL,
                details_json TEXT NOT NULL DEFAULT '{}',
                candidate_json TEXT NOT NULL DEFAULT '{}',
                settings_json TEXT NOT NULL DEFAULT '{}',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                PRIMARY KEY (artist_key, album_key)
            )
        """)
        db.commit()


def _discovery_read_list(name):
    # Keep schema initialization here for existing callers; persistence mechanics
    # are independently importable and tested in discovery_store.py.
    _discovery_init()
    return discovery_store.read_list(DISCOVERY_DB, name)


def _discovery_write_list(name, payload):
    _discovery_init()
    discovery_store.write_list(DISCOVERY_DB, name, payload)


def _discovery_feedback_rows():
    _discovery_init()
    with sqlite3.connect(DISCOVERY_DB, timeout=10) as db:
        rows = db.execute(
            "SELECT scope, artist_key, album_key, artist, album, status, metadata_json, created_at, updated_at "
            "FROM discovery_feedback"
        ).fetchall()
    return [
        {
            "scope": row[0], "artist_key": row[1], "album_key": row[2],
            "artist": row[3], "album": row[4], "status": row[5],
            "metadata": json.loads(row[6] or "{}"),
            "created_at": row[7], "updated_at": row[8],
        }
        for row in rows
    ]


def _discovery_save_feedback(scope, artist, album, status, metadata=None):
    now = time.time()
    artist_key = _music_key(artist)
    album_key = _music_key(album) if album else ""
    if not artist_key:
        raise ValueError("artist is required")
    if scope == "album" and not album_key:
        raise ValueError("album is required for album feedback")
    with sqlite3.connect(DISCOVERY_DB, timeout=10) as db:
        db.execute(
            "INSERT INTO discovery_feedback "
            "(scope, artist_key, album_key, artist, album, status, metadata_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(scope, artist_key, album_key) DO UPDATE SET "
            "artist=excluded.artist, album=excluded.album, status=excluded.status, "
            "metadata_json=excluded.metadata_json, updated_at=excluded.updated_at",
            (
                scope, artist_key, album_key, artist.strip(), (album or "").strip(),
                status, json.dumps(metadata or {}, ensure_ascii=False), now, now,
            ),
        )
        db.commit()


# Prevent duplicate automatic searches for the same For Me album.
_DISCOVERY_AUTO_ACQUIRE_LOCK = __import__("threading").Lock()
_DISCOVERY_AUTO_ACQUIRE_ACTIVE = set()


def _discovery_auto_acquire_for_me(artist, album):
    identity = (_music_key(artist), _music_key(album))
    with _DISCOVERY_AUTO_ACQUIRE_LOCK:
        if identity in _DISCOVERY_AUTO_ACQUIRE_ACTIVE:
            return
        _DISCOVERY_AUTO_ACQUIRE_ACTIVE.add(identity)
    try:
        rows = _discovery_feedback_rows()
        existing = next((
            row for row in rows
            if row["scope"] == "album"
            and row["artist_key"] == identity[0]
            and row["album_key"] == identity[1]
            and row["status"] == "for_me"
        ), None)
        if not existing:
            return
        metadata = existing.get("metadata") or {}
        prior = metadata.get("auto_acquisition") or {}
        if prior.get("status") == "queued":
            return
        settings = _discovery_settings_read()
        if not settings.get("auto_acquire_for_me", True):
            metadata["auto_acquisition"] = {"status": "disabled", "checked_at": time.time()}
            _discovery_save_feedback("album", artist, album, "for_me", metadata)
            return
        metadata["auto_acquisition"] = {"status": "searching", "started_at": time.time()}
        _discovery_save_feedback("album", artist, album, "for_me", metadata)
        result_text = discovery_acquire_album(
            artist, album, metadata_json=json.dumps(metadata, ensure_ascii=False),
            auto_queue=True,
        )
        try:
            result = json.loads(result_text)
        except (ValueError, TypeError):
            result = {"ok": False, "status": "invalid_response"}
        metadata["auto_acquisition"] = {
            "status": result.get("status", "error"),
            "checked_at": time.time(),
            "result": result,
        }
        _discovery_save_feedback("album", artist, album, "for_me", metadata)
    except Exception as exc:
        try:
            rows = _discovery_feedback_rows()
            existing = next((
                row for row in rows
                if row["scope"] == "album"
                and row["artist_key"] == identity[0]
                and row["album_key"] == identity[1]
                and row["status"] == "for_me"
            ), None)
            metadata = (existing or {}).get("metadata") or {}
            metadata["auto_acquisition"] = {
                "status": "error", "checked_at": time.time(),
                "message": type(exc).__name__,
            }
            _discovery_save_feedback("album", artist, album, "for_me", metadata)
        except Exception:
            pass
    finally:
        with _DISCOVERY_AUTO_ACQUIRE_LOCK:
            _DISCOVERY_AUTO_ACQUIRE_ACTIVE.discard(identity)


def _discovery_refresh_personal(count=20):
    return discovery_refresh.refresh_personal(
        _DISCOVERY_REFRESH_LOCK,
        recommend_new_music,
        _discovery_write_list,
        count=count,
    )


def discovery_set_feedback(
    artist: str,
    album: str,
    action: str,
    metadata_json: str = "{}",
) -> str:
    """Save an album to For Me, dismiss it, dismiss its artist, or remove it from For Me.

    action is save, dismiss, dismiss_artist, or remove_for_me. Dismissal is
    persisted internally and excluded from future visible recommendations.
    """
    if action not in {"save", "dismiss", "dismiss_artist", "remove_for_me"}:
        return json.dumps({
            "ok": False,
            "error": "action must be save, dismiss, dismiss_artist, or remove_for_me",
        })
    if not artist.strip() or not album.strip():
        return json.dumps({"ok": False, "error": "artist and album are required"})
    try:
        metadata = json.loads(metadata_json or "{}")
        if not isinstance(metadata, dict):
            metadata = {}
    except (ValueError, TypeError):
        metadata = {}

    try:
        if action == "save":
            _discovery_save_feedback("album", artist, album, "for_me", metadata)
            import threading
            threading.Thread(
                target=_discovery_auto_acquire_for_me,
                args=(artist.strip(), album.strip()),
                name="navidrome-auto-acquire",
                daemon=True,
            ).start()
        elif action == "dismiss":
            _discovery_save_feedback("album", artist, album, "not_for_me", metadata)
        elif action == "dismiss_artist":
            _discovery_save_feedback("album", artist, album, "not_for_me", metadata)
            _discovery_save_feedback("artist", artist, "", "not_for_me_artist", {})
        else:
            _discovery_init()
            with sqlite3.connect(DISCOVERY_DB, timeout=10) as db:
                db.execute(
                    "DELETE FROM discovery_feedback WHERE scope='album' AND artist_key=? AND album_key=? AND status='for_me'",
                    (_music_key(artist), _music_key(album)),
                )
                db.commit()
        return json.dumps({
            "ok": True,
            "action": action,
            "artist": artist.strip(),
            "album": album.strip(),
            "auto_acquisition": (
                "started_in_background"
                if action == "save" else None
            ),
            "note": (
                "For Me save triggers an slskd search. Only a clear, non-ambiguous album-folder match is queued automatically; uncertain matches require review."
                if action == "save" else None
            ),
        }, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})


_LASTFM_REQUEST_LOCK = __import__("threading").Lock()
_LASTFM_LAST_REQUEST_AT = 0.0


def _lastfm_cached_call(method, ttl_seconds=30 * 24 * 60 * 60, **params):
    global _LASTFM_LAST_REQUEST_AT
    api_key = str(_discovery_settings_read().get("lastfm_api_key") or "").strip()
    if not api_key:
        return None
    cache_identity = json.dumps(
        {"method": method, "params": params},
        sort_keys=True, ensure_ascii=False,
    )
    cache_key = "discovery:lastfm:" + hashlib.sha256(
        cache_identity.encode("utf-8")
    ).hexdigest()
    cached = _metadata_cache_get(cache_key, ttl_seconds)
    if cached is not None:
        return cached
    try:
        with _LASTFM_REQUEST_LOCK:
            wait = 0.2 - (time.monotonic() - _LASTFM_LAST_REQUEST_AT)
            if wait > 0:
                time.sleep(wait)
            _LASTFM_LAST_REQUEST_AT = time.monotonic()
        response = httpx.get(
            "https://ws.audioscrobbler.com/2.0/",
            params={
                "method": method,
                "api_key": api_key,
                "format": "json",
                "autocorrect": 1,
                **params,
            },
            headers={"User-Agent": "NavidromeLibrarian/1.0"},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("error"):
            return None
        _metadata_cache_set(cache_key, payload)
        return payload
    except (httpx.HTTPError, ValueError, TypeError):
        return None


def _discovery_library_snapshot():
    cached = _discovery_read_list("library_snapshot")
    if (
        cached
        and time.time() - cached["generated_at"] < 10 * 60
        and (
            not cached["payload"].get("albums")
            or "song_count" in cached["payload"]["albums"][0]
        )
    ):
        return cached["payload"]

    root = api_call("getArtists")
    indexes = root.get("artists", {}).get("index", [])
    artists = [
        {
            "id": artist.get("id"),
            "name": artist.get("name", "").strip(),
            "album_count": int(artist.get("albumCount") or 0),
        }
        for index in indexes
        for artist in items(index.get("artist"))
        if artist.get("name")
    ]

    albums = []
    seen_ids = set()
    complete = False
    for offset in range(0, 50000, 500):
        album_root = api_call(
            "getAlbumList2", type="alphabeticalByName", size=500, offset=offset
        )
        page = items(album_root.get("albumList2", {}).get("album"))
        for album in page:
            album_id = album.get("id")
            if album_id and album_id in seen_ids:
                continue
            if album_id:
                seen_ids.add(album_id)
            albums.append({
                "id": album_id,
                "artist": album.get("artist", ""),
                "album": album.get("name", ""),
                "year": album.get("year"),
                "song_count": int(album.get("songCount") or 0),
                "coverArt": album.get("coverArt"),
            })
        if len(page) < 500:
            complete = True
            break
    if not complete:
        raise RuntimeError("Navidrome album inventory exceeded the safety limit.")

    snapshot = {"artists": artists, "albums": albums}
    _discovery_write_list("library_snapshot", snapshot)
    return snapshot


def _lastfm_top_albums(artist, limit=8):
    payload = _lastfm_cached_call(
        "artist.getTopAlbums", ttl_seconds=30 * 24 * 60 * 60,
        artist=artist, limit=limit,
    )
    if not payload:
        return []
    records = items(payload.get("topalbums", {}).get("album"))
    output = []
    for album in records:
        title = (album.get("name") or "").strip()
        if not title or not _discovery_is_album_candidate({"album": title}):
            continue
        stats = album.get("playcount")
        output.append({
            "artist": artist,
            "album": title,
            "mbid": album.get("mbid") or None,
            "lastfm_listeners": int(album.get("listeners") or 0),
            "lastfm_playcount": int(stats or 0),
            "lastfm_url": album.get("url"),
        })
    return output


def _lastfm_artist_genres(artist):
    """Return cached Last.fm top tags for an artist, suitable for display grouping."""
    payload = _lastfm_cached_call(
        "artist.getTopTags", ttl_seconds=30 * 24 * 60 * 60,
        artist=artist,
    )
    if not payload:
        return []
    records = items(payload.get("toptags", {}).get("tag"))
    tags = []
    for record in records:
        name = str(record.get("name") or "").strip()
        if name and name.casefold() not in {tag.casefold() for tag in tags}:
            tags.append(name)
        if len(tags) >= 8:
            break
    return tags


def _deep_dive_genre_families(tags):
    from discovery_recommendations import deep_dive_genre_families
    return deep_dive_genre_families(tags)
def _lastfm_similar_artists(artist, limit=8):
    payload = _lastfm_cached_call(
        "artist.getSimilar", ttl_seconds=60 * 24 * 60 * 60,
        artist=artist, limit=limit,
    )
    if not payload:
        return []
    records = items(payload.get("similarartists", {}).get("artist"))
    output = []
    for item in records:
        name = (item.get("name") or "").strip()
        if name:
            try:
                match = float(item.get("match") or 0)
            except (ValueError, TypeError):
                match = 0.0
            output.append({"artist": name, "similarity": match})
    return output


def _musicbrainz_critical_rating(mbid, include_year=False):
    if not mbid:
        return None
    cache_key = "discovery:mb-release-group-rating:" + str(mbid)
    cached = _metadata_cache_get(cache_key, ttl_seconds=180 * 24 * 60 * 60)
    if cached is not None and (not include_year or "year" in cached):
        return cached
    try:
        # MusicBrainz requests must be spaced to respect its public API limit.
        time.sleep(1.1)
        response = httpx.get(
            f"https://musicbrainz.org/ws/2/release-group/{mbid}",
            params={"fmt": "json", "inc": "ratings"},
            headers={"User-Agent": "NavidromeLibrarian/1.0 (personal music discovery)"},
            timeout=15,
        )
        if response.status_code == 404:
            empty_result = {"rating": None, "votes": 0, "year": None}
            _metadata_cache_set(cache_key, empty_result)
            return empty_result
        response.raise_for_status()
        data = response.json()
        rating = data.get("rating") or {}
        release_date = str(data.get("first-release-date") or "")
        year_text = release_date[:4]
        result = {
            "rating": rating.get("value"),
            "votes": int(rating.get("votes-count") or 0),
            "year": int(year_text) if year_text.isdigit() and 1900 <= int(year_text) <= 2100 else None,
        }
        _metadata_cache_set(cache_key, result)
        return result
    except (httpx.HTTPError, ValueError, TypeError):
        return None


def _discovery_exact_artist_credit_matches(artist_credit, artist_name):
    from discovery_recommendations import exact_artist_credit_matches
    return exact_artist_credit_matches(artist_credit, artist_name)
def _discovery_is_various_artists(value):
    from discovery_recommendations import is_various_artists
    return is_various_artists(value)
def _build_new_releases_list():
    """Find recent full albums by library artists who own at least one full album."""
    snapshot = _discovery_library_snapshot()
    owned = {
        (_music_key(item.get("artist", "")), _music_key(item.get("album", "")))
        for item in snapshot["albums"]
    }
    full_album_artist_keys = {
        _music_key(item.get("artist", ""))
        for item in snapshot["albums"]
        if int(item.get("song_count") or 0) >= 6 and item.get("artist")
    }
    qualified_artists = [
        artist for artist in snapshot["artists"]
        if artist.get("name")
        and not _discovery_is_various_artists(artist["name"])
        and _music_key(artist["name"]) in full_album_artist_keys
    ]
    qualified_artists.sort(key=lambda item: int(item.get("album_count") or 0), reverse=True)
    from datetime import date, timedelta
    today = date.today()
    cutoff_date = (today - timedelta(days=730)).isoformat()
    current_year = today.year
    earliest_year = int(cutoff_date[:4])
    candidates = {}
    errors = []
    artist_batch = qualified_artists[:120]
    headers = {"User-Agent": "NavidromeLibrarian/1.0 (personal music discovery)"}

    for index, artist_record in enumerate(artist_batch):
        artist = artist_record["name"].strip()
        if _discovery_is_various_artists(artist):
            continue
        artist_key = _music_key(artist)
        cache_key = f"mb:new-releases:v1:{earliest_year}:{artist_key}"
        payload = _metadata_cache_get(cache_key, ttl_seconds=30 * 24 * 60 * 60)
        if payload is None:
            try:
                if index:
                    time.sleep(1.1)
                escaped_artist = artist.replace("\\", "\\\\").replace('"', '\\"')
                query = (
                    f'artist:"{escaped_artist}" AND primarytype:album '
                    f'AND firstreleasedate:[{earliest_year} TO {current_year}]'
                )
                response = httpx.get(
                    "https://musicbrainz.org/ws/2/release-group/",
                    params={"query": query, "fmt": "json", "limit": 100},
                    headers=headers,
                    timeout=20,
                )
                response.raise_for_status()
                payload = response.json().get("release-groups", [])
                if not isinstance(payload, list):
                    payload = []
                _metadata_cache_set(cache_key, payload)
            except (httpx.HTTPError, ValueError, TypeError) as exc:
                errors.append({"artist": artist, "error": type(exc).__name__})
                continue

        for group in payload if isinstance(payload, list) else []:
            if not isinstance(group, dict) or group.get("primary-type") != "Album":
                continue
            title = str(group.get("title") or "").strip()
            release_date = str(group.get("first-release-date") or "")
            year_text = release_date[:4]
            if not title or not year_text.isdigit():
                continue
            year = int(year_text)
            if release_date < cutoff_date or year > current_year:
                continue
            candidate = {
                "artist": artist, "album": title, "year": year,
                "first_release_date": release_date, "mbid": group.get("id"),
                "primary_type": group.get("primary-type"),
                "secondary_types": group.get("secondary-types") or [],
                "discovery_type": "new_release",
                "discovery_source": "MusicBrainz recent release groups",
                "reason": f"Released in {year} by an artist with a full album in your library",
                "artist_library_album_count": int(artist_record.get("album_count") or 0),
            }
            if not _discovery_is_album_candidate(candidate):
                continue
            # MusicBrainz text search can return similarly named artists (e.g.
            # "Queen Tribute") for an exact-looking artist query. Require an
            # exact artist-credit name rather than a substring match.
            artist_credit = group.get("artist-credit")
            if not _discovery_exact_artist_credit_matches(artist_credit, artist):
                continue
            if _discovery_is_various_artists(artist):
                continue
            if _discovery_is_various_artists(" ".join(
                str((part.get("artist") or {}).get("name") or part.get("name") or "")
                for part in (artist_credit or []) if isinstance(part, dict)
            )):
                continue
            identity = (_music_key(artist), _music_key(title))
            if identity in owned:
                continue
            old = candidates.get(identity)
            if old is None or release_date > old.get("first_release_date", ""):
                candidates[identity] = candidate

    items_out = sorted(
        candidates.values(),
        key=lambda item: (
            str(item.get("first_release_date") or ""),
            str(item.get("artist") or "").casefold(),
            str(item.get("album") or "").casefold(),
        ),
        reverse=True,
    )
    return {
        "list": "new_releases", "source": "MusicBrainz release groups matched against the Navidrome library",
        "generated_at": time.time(), "year_from": earliest_year, "date_from": cutoff_date,
        "qualified_library_artists": len(qualified_artists),
        "artists_scanned": len(artist_batch), "items": items_out[:200],
        "lookup_errors": errors[:20],
        "limitations": [
            "Only artists with at least one library album containing six or more tracks qualify.",
            "The release window is the previous 730 days.",
            "MusicBrainz release-group coverage and release dates may be incomplete.",
            "The initial refresh is bounded to the 120 library artists with the largest album counts.",
        ],
    }


def _build_classics_list():
    snapshot = _discovery_library_snapshot()
    library_artists = snapshot["artists"]
    owned = {
        (_music_key(item["artist"]), _music_key(item["album"]))
        for item in snapshot["albums"]
    }
    candidates = {}
    # Work through every artist in the library. Cached Last.fm responses make
    # subsequent daily runs substantially cheaper than the initial build.
    for index, artist_record in enumerate(
        sorted(library_artists, key=lambda item: item["album_count"], reverse=True)
    ):
        artist = artist_record["name"]
        for album in _lastfm_top_albums(artist, limit=8):
            key = (_music_key(album["artist"]), _music_key(album["album"]))
            if key in owned:
                continue
            old = candidates.get(key)
            if old is None or album["lastfm_listeners"] > old["lastfm_listeners"]:
                candidates[key] = {
                    **album,
                    "discovery_type": "classic",
                    "discovery_source": "Last.fm artist top albums",
                    "artist_library_album_count": artist_record["album_count"],
                }
        # Avoid a long unbounded burst to Last.fm on the first build.
        if index and index % 5 == 0:
            time.sleep(0.15)

    candidates = {
        key: item for key, item in candidates.items()
        if _discovery_is_album_candidate(item)
    }

    # Add critical-rating evidence for a rotating shortlist. Rating lookups are
    # cached; listener counts are used only to bound the number of requests.
    rating_shortlist = sorted(
        candidates.values(),
        key=lambda item: int(item.get("lastfm_listeners") or 0),
        reverse=True,
    )[:80]
    for index, candidate in enumerate(rating_shortlist):
        rating = _musicbrainz_critical_rating(
            candidate.get("mbid"), include_year=index < 30
        )
        if rating:
            candidate["musicbrainz_rating"] = rating.get("rating")
            candidate["musicbrainz_rating_votes"] = rating.get("votes", 0)
            if rating.get("year"):
                candidate["year"] = rating["year"]

    # Build a broad candidate pool before choosing the visible collection list.
    # Popularity is only a weak tie-breaker; critical recognition and rotating
    # exploration have much more influence than Last.fm listener totals.
    from discovery_recommendations import score_classic_candidates
    score_classic_candidates(candidates.values(), random.uniform)

    ranked = sorted(candidates.values(), key=lambda item: item["exploration_score"], reverse=True)

    # Genre metadata helps keep the collection lane from becoming one long
    # popularity chart. Last.fm tag results are cached between refreshes.
    genre_cache = {}
    for item in ranked[:300]:
        artist_key = _music_key(item.get("artist", ""))
        if artist_key not in genre_cache:
            genre_cache[artist_key] = _lastfm_artist_genres(item.get("artist", ""))
        item["genres"] = genre_cache[artist_key]
        item["genre_families"] = sorted(_deep_dive_genre_families(item["genres"]))
        if not item["genre_families"]:
            item["genre_families"] = ["other"]
    for item in ranked[300:]:
        item["genres"] = []
        item["genre_families"] = ["other"]

    # Re-sort after enriching the broader pool; add fresh jitter so a manual
    # refresh can rotate recommendations even when upstream API caches are warm.
    from discovery_recommendations import refresh_exploration_scores
    refresh_exploration_scores(ranked, random.uniform)
    ranked.sort(key=lambda item: item["exploration_score"], reverse=True)

    from discovery_recommendations import diversify_classic_candidates
    diversified = diversify_classic_candidates(ranked, limit=100, per_artist=2, per_family=8)
    return {
        "list": "classics",
        "source": "Exploration-weighted candidates with MusicBrainz ratings and genre/artist diversity",
        "generated_at": time.time(),
        "library_artists_considered": len(library_artists),
        "owned_albums_checked": len(owned),
        "critical_ratings_available": sum(
            1 for item in ranked if item["critical_recognition_available"]
        ),
        "items": diversified[:100],
        "diversity_strategy": "Popularity is a weak signal; rotate the pool with genre caps and at most two albums per artist.",
        "limitations": [
            "Last.fm top-album lists are popularity signals, not definitive critical consensus.",
            "MusicBrainz ratings are community-supplied and may be absent or based on few votes.",
            "Ownership checks compare normalized artist and album names; aliases and editions may need review.",
        ],
    }


def _build_artist_deep_dive_list():
    snapshot = _discovery_library_snapshot()
    artists = snapshot["artists"]
    albums = snapshot["albums"]
    owned_artists = {
        _music_key(item["name"]): item
        for item in artists
    }
    owned_albums = {
        (_music_key(item["artist"]), _music_key(item["album"]))
        for item in albums
    }
    anchors = [
        item for item in artists
        if item["album_count"] >= 3 and item["name"]
    ]
    candidates = {}

    # First find missing albums from artists with a substantial owned presence.
    for index, anchor in enumerate(
        sorted(anchors, key=lambda item: item["album_count"], reverse=True)
    ):
        for album in _lastfm_top_albums(anchor["name"], limit=8):
            key = (_music_key(album["artist"]), _music_key(album["album"]))
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
        if index and index % 5 == 0:
            time.sleep(0.15)

    # Reuse resolved candidates that were not selected for the main list.
    # Only surface albums by artists already represented by 3+ owned albums,
    # so this lane is anchored in library depth rather than listening history.
    personal_cache = _discovery_read_list("personal")
    personal_payload = personal_cache.get("payload", {}) if personal_cache else {}
    resolved_candidates = personal_payload.get("debug_all_candidates", [])
    anchors_by_key = {_music_key(item["name"]): item for item in anchors}
    for candidate in resolved_candidates if isinstance(resolved_candidates, list) else []:
        candidate_artist = str(candidate.get("artist") or "").strip()
        candidate_album = str(candidate.get("album") or "").strip()
        anchor = anchors_by_key.get(_music_key(candidate_artist))
        if not anchor or not candidate_album:
            continue
        if candidate.get("exact_owned") or candidate.get("selection_decision") == "selected":
            continue
        key = (_music_key(candidate_artist), _music_key(candidate_album))
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

    # Then discover similar artists that are not represented in the library.
    similar_artist_scores = {}
    for index, anchor in enumerate(
        sorted(anchors, key=lambda item: item["album_count"], reverse=True)
    ):
        for similar in _lastfm_similar_artists(anchor["name"], limit=15):
            similar_key = _music_key(similar["artist"])
            if similar_key in owned_artists:
                continue
            existing = similar_artist_scores.get(similar_key)
            score = similar["similarity"] * (1.0 + min(anchor["album_count"], 15) / 30)
            if existing is None or score > existing["score"]:
                similar_artist_scores[similar_key] = {
                    "artist": similar["artist"],
                    "score": score,
                    "anchor_artist": anchor["name"],
                    "anchor_album_count": anchor["album_count"],
                    "similarity": similar["similarity"],
                }
        if index and index % 5 == 0:
            time.sleep(0.15)

    for similar in similar_artist_scores.values():
        for album in _lastfm_top_albums(similar["artist"], limit=5):
            key = (_music_key(album["artist"]), _music_key(album["album"]))
            if key in owned_albums or _music_key(album["artist"]) in owned_artists:
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

    # Genre tags are presentation metadata only: they do not change candidate scores.
    # Last.fm top tags can be sparse for lesser-known artists; when that happens,
    # inherit tags from the 3+ album library artist that surfaced this candidate.
    artist_genre_cache = {}
    for item in candidates.values():
        artist_name = str(item.get("artist") or "").strip()
        anchor_name = str(item.get("anchor_artist") or "").strip()
        cache_key = _music_key(artist_name)
        if not item.get("genres") and artist_name:
            if cache_key not in artist_genre_cache:
                artist_genre_cache[cache_key] = _lastfm_artist_genres(artist_name)
            item["genres"] = artist_genre_cache[cache_key]
        if not item.get("genres") and anchor_name:
            anchor_key = _music_key(anchor_name)
            if anchor_key not in artist_genre_cache:
                artist_genre_cache[anchor_key] = _lastfm_artist_genres(anchor_name)
            item["genres"] = artist_genre_cache[anchor_key]
            item["genre_inherited_from_anchor"] = bool(item["genres"])
        if not item.get("genre_families"):
            item["genre_families"] = _deep_dive_genre_families(item.get("genres") or [])
        # Generic tags such as "seen live" can exist without identifying a genre.
        # If those tags don't classify, try the library anchor's genre tags instead.
        if not item.get("genre_families") and anchor_name:
            anchor_key = _music_key(anchor_name)
            if not artist_genre_cache.get(anchor_key):
                artist_genre_cache[anchor_key] = _lastfm_artist_genres(anchor_name)
            anchor_families = _deep_dive_genre_families(artist_genre_cache.get(anchor_key) or [])
            if anchor_families:
                item["genres"] = artist_genre_cache[anchor_key]
                item["genre_families"] = anchor_families
                item["genre_inherited_from_anchor"] = True
        import math
        popularity = math.log10(max(0, int(item.get("lastfm_listeners") or 0)) + 1)
        playcount = math.log10(max(0, int(item.get("lastfm_playcount") or 0)) + 1)
        candidate_score = float(item.get("candidate_pool_score", 0) or 0)
        # Similarity to an established library artist and candidate-pool evidence
        # should matter more than global Last.fm popularity.
        candidate_bonus = candidate_score * 2.5
        anchor_bonus = (
            min(int(item.get("anchor_album_count", 0) or 0), 15) * 0.05
            if candidate_score else 0.0
        )
        item["discovery_score"] = round(
            popularity * 0.15 + playcount * 0.03
            + float(item.get("similar_artist_score", 0)) * 2.0
            + candidate_bonus + anchor_bonus,
            4,
        )
    # Strongly penalize listener-count dominance and give genuinely lesser-known
    # artists a meaningful exploration bonus. Last.fm's top-album endpoint is
    # popularity-sorted, so cap both artist and anchor repetition afterwards.
    import math
    for item in candidates.values():
        listeners = max(0, int(item.get("lastfm_listeners") or 0))
        listener_magnitude = math.log10(listeners + 1)
        item["exploration_score"] = round(
            item["discovery_score"] - listener_magnitude * 0.65
            + max(0.0, 6.0 - listener_magnitude) * 0.35,
            4,
        )
    # Rotate otherwise-equivalent candidates on every refresh, then enforce
    # artist, anchor and genre diversity rather than letting Last.fm's default
    # popularity ordering dominate the page.
    for item in candidates.values():
        item["exploration_score"] = round(
            float(item.get("exploration_score", 0) or 0)
            + random.uniform(-1.25, 1.25),
            4,
        )
    candidates = {
        key: item for key, item in candidates.items()
        if _discovery_is_album_candidate(item)
    }
    ranked = sorted(
        candidates.values(),
        key=lambda item: (
            item["exploration_score"],
            float(item.get("similar_artist_score", 0) or 0),
        ),
        reverse=True,
    )
    diversified = []
    artist_counts = {}
    anchor_counts = {}
    genre_counts = {}
    deferred = []
    for item in ranked:
        artist_key = _music_key(item.get("artist", ""))
        anchor_key = _music_key(item.get("anchor_artist", ""))
        families = item.get("genre_families") or ["other"]
        family = next((value for value in families if genre_counts.get(value, 0) < 12), families[0])
        if artist_counts.get(artist_key, 0) >= 2 or (anchor_key and anchor_counts.get(anchor_key, 0) >= 4) or genre_counts.get(family, 0) >= 12:
            deferred.append(item)
            continue
        item["primary_genre_family"] = family
        diversified.append(item)
        artist_counts[artist_key] = artist_counts.get(artist_key, 0) + 1
        genre_counts[family] = genre_counts.get(family, 0) + 1
        if anchor_key:
            anchor_counts[anchor_key] = anchor_counts.get(anchor_key, 0) + 1
        if len(diversified) >= 150:
            break
    if len(diversified) < 150:
        for item in deferred:
            artist_key = _music_key(item.get("artist", ""))
            anchor_key = _music_key(item.get("anchor_artist", ""))
            if artist_counts.get(artist_key, 0) >= 2 or (anchor_key and anchor_counts.get(anchor_key, 0) >= 4):
                continue
            diversified.append(item)
            artist_counts[artist_key] = artist_counts.get(artist_key, 0) + 1
            if anchor_key:
                anchor_counts[anchor_key] = anchor_counts.get(anchor_key, 0) + 1
            if len(diversified) >= 150:
                break
    # Resolve years only for a bounded top slice with MusicBrainz IDs. The
    # release-group metadata is cached, so later refreshes reuse these lookups.
    for item in ranked[:25]:
        if item.get("year") or not item.get("mbid"):
            continue
        rating = _musicbrainz_critical_rating(item.get("mbid"), include_year=True)
        if rating and rating.get("year"):
            item["year"] = rating["year"]
    return {
        "list": "artist_deep_dive",
        "source": "Library depth + similar-artist candidates, exploration rotation and genre diversity",
        "generated_at": time.time(),
        "artists_with_three_or_more_owned_albums": len(anchors),
        "missing_albums_and_similar_artist_candidates": len(ranked),
        "items": diversified[:150],
        "limitations": [
            "Artist similarity is sourced from Last.fm and is not a guarantee of musical fit.",
            "Popularity is deliberately down-weighted and candidates rotate across genres and artists.",
            "Ownership checks compare normalized artist and album names; aliases and editions may need review.",
        ],
    }


def _discovery_refresh_other(list_name):
    return discovery_refresh.refresh_other(
        list_name,
        {
            "classics": _CLASSICS_REFRESH_LOCK,
            "artist_deep_dive": _DEEP_DIVE_REFRESH_LOCK,
            "new_releases": _NEW_RELEASES_REFRESH_LOCK,
        },
        {
            "classics": _build_classics_list,
            "artist_deep_dive": _build_artist_deep_dive_list,
            "new_releases": _build_new_releases_list,
        },
        _discovery_write_list,
    )


_CLASSICS_REFRESH_LOCK = __import__("threading").Lock()
_DEEP_DIVE_REFRESH_LOCK = __import__("threading").Lock()
_NEW_RELEASES_REFRESH_LOCK = __import__("threading").Lock()


_DISCOVERY_SETTINGS_DEFAULTS = {
    "navidrome_url": os.environ.get("NAVIDROME_URL", "http://192.168.1.12:4533").rstrip("/"),
    "navidrome_user": os.environ.get("NAVIDROME_USER", ""),
    "navidrome_password": os.environ.get("NAVIDROME_PASSWORD", ""),
    "lastfm_api_key": os.environ.get("LASTFM_API_KEY", ""),
    "listenbrainz_username": os.environ.get("LISTENBRAINZ_USERNAME", "copi35"),
    "music_library_path": str(MUSIC_DIR),
    "slskd_url": os.environ.get("SLSKD_URL", "http://192.168.1.12:5030"),
    "quality_priority": [
        "mp3_320",
        "mp3_193_319",
        "mp3_192",
        "flac_cd",
        "flac_16_44",
        "flac_hires",
    ],
    "auto_acquire_for_me": True,
    "slskd_downloads_path": str(Path(
        os.environ.get("SLSKD_DOWNLOADS_DIR")
        or os.environ.get("SLSKD_DOWNLOADS_MOUNT")
        or str(MUSIC_DIR.parent.parent / "downloads" / "slskd" / "complete")
    ).expanduser()),
}


_settings_persistence = SettingsPersistence(
    DISCOVERY_DB,
    _DISCOVERY_SETTINGS_DEFAULTS,
    lambda: MUSIC_DIR,
    lambda path: _set_music_dir(path),
)


def _set_music_dir(path):
    global MUSIC_DIR
    MUSIC_DIR = path


def _discovery_settings_init():
    """Compatibility wrapper for initializing the persistent settings store."""
    return _settings_persistence.initialize()


def _discovery_settings_read():
    """Compatibility wrapper for reading and migrating persisted settings."""
    return _settings_persistence.read()


def _discovery_settings_write(values):
    """Compatibility wrapper for writing persisted settings."""
    return _settings_persistence.write(values)


# Load persisted directory overrides before any library operation runs.
_discovery_settings_read()


def _navidrome_config():
    """Compatibility adapter for validated Navidrome configuration."""
    return _service_navidrome_config(_discovery_settings_read)


def _listenbrainz_username():
    """Compatibility adapter for validated ListenBrainz username."""
    return _service_listenbrainz_username(_discovery_settings_read)


def discovery_get_navidrome_settings() -> str:
    """Return Navidrome settings without exposing the saved password."""
    return _service_get_navidrome_settings(_discovery_settings_read, MUSIC_DIR)


def discovery_set_navidrome_settings(
    navidrome_url: str,
    username: str,
    password: str = "",
    music_library_path: str | None = None,
) -> str:
    """Save Navidrome connection settings; a blank password preserves the saved password."""
    def set_music_dir(path):
        global MUSIC_DIR
        MUSIC_DIR = path

    return _service_set_navidrome_settings(
        _discovery_settings_read,
        _discovery_settings_write,
        lambda: MUSIC_DIR,
        set_music_dir,
        navidrome_url,
        username,
        password,
        music_library_path,
    )


def discovery_test_navidrome_connection() -> str:
    """Compatibility adapter for the extracted Navidrome connection service."""
    return _service_test_navidrome_connection(api_call, json.dumps)


def discovery_get_lastfm_settings() -> str:
    """Return Last.fm configuration status without exposing the API key."""
    return _service_get_lastfm_settings(_discovery_settings_read)


def discovery_set_lastfm_settings(api_key: str = "") -> str:
    """Save a Last.fm API key; a blank key preserves the saved key."""
    return _service_set_lastfm_settings(
        _discovery_settings_read, _discovery_settings_write, api_key
    )


def discovery_test_lastfm_connection() -> str:
    """Compatibility adapter for the extracted Last.fm connection service."""
    return _service_test_lastfm_connection(_discovery_settings_read, httpx.get, json.dumps)


def discovery_get_listenbrainz_settings() -> str:
    """Return the configured ListenBrainz username."""
    return json.dumps({"username": _listenbrainz_username()})


def discovery_set_listenbrainz_settings(username: str) -> str:
    """Save a ListenBrainz username."""
    return _service_set_listenbrainz_settings(_discovery_settings_write, username)


def discovery_test_listenbrainz_connection() -> str:
    """Compatibility adapter for the extracted ListenBrainz connection service."""
    return _service_test_listenbrainz_connection(_listenbrainz_username, httpx.get, json.dumps)


def _slskd_config():
    """Compatibility adapter for validated slskd configuration."""
    return _service_slskd_config(_discovery_settings_read)


def discovery_get_slskd_settings() -> str:
    """Read acquisition settings without returning the stored API key."""
    return _service_get_slskd_settings(
        _discovery_settings_read, MUSIC_DIR, _DISCOVERY_SETTINGS_DEFAULTS
    )


def discovery_set_slskd_settings(
    slskd_url: str = "http://192.168.1.12:5030",
    api_key: str = "",
    quality_priority_json: str = '["mp3_320","mp3_193_319","mp3_192","flac_cd","flac_16_44","flac_hires"]',
    auto_acquire_for_me: bool | None = None,
    slskd_downloads_path: str | None = None,
    music_library_path: str | None = None,
) -> str:
    """Save acquisition settings and paths. Blank API key preserves the saved key."""
    def set_music_dir(path):
        global MUSIC_DIR
        MUSIC_DIR = path

    return _service_set_slskd_settings(
        _discovery_settings_read,
        _discovery_settings_write,
        lambda: MUSIC_DIR,
        set_music_dir,
        _DISCOVERY_SETTINGS_DEFAULTS,
        slskd_url,
        api_key,
        quality_priority_json,
        auto_acquire_for_me,
        slskd_downloads_path,
        music_library_path,
    )


def discovery_test_slskd_connection() -> str:
    """Test the configured slskd API without exposing the API key."""
    try:
        base_url, api_key, _ = _slskd_config()
        response = httpx.get(
            base_url + "/api/v0/server",
            headers={"X-API-KEY": api_key},
            timeout=8,
        )
        if response.status_code in (401, 403):
            return json.dumps({
                "ok": False, "status": "authentication_failed",
                "message": "slskd rejected the API key. Check the key in Settings.",
            })
        response.raise_for_status()
        return json.dumps({
            "ok": True, "status": "connected",
            "http_status": response.status_code,
            "message": "slskd API connection succeeded.",
        })
    except (httpx.HTTPError, ValueError) as exc:
        return json.dumps({
            "ok": False, "status": "connection_failed",
            "message": str(exc),
        })


def _slskd_quality_tier(file_record, filename, priority):
    """Compatibility wrapper for slskd audio-quality classification."""
    from slskd_quality import quality_tier

    return quality_tier(file_record, filename, priority)

def _discovery_expected_track_count(metadata):
    """Compatibility adapter for expected slskd album track-count extraction."""
    from slskd_search import expected_track_count

    return expected_track_count(metadata)
def _slskd_track_identity(filename):
    """Compatibility wrapper for slskd track identity normalization."""
    from slskd_search import track_identity

    return track_identity(filename, _music_key)

def _slskd_album_path_match(album, text):
    """Compatibility wrapper for slskd album-path matching."""
    from slskd_search import album_path_match

    return album_path_match(album, text)

def _slskd_search_queries(artist, album):
    """Compatibility wrapper for bounded slskd query generation."""
    from slskd_search import search_queries

    return search_queries(artist, album)

def _slskd_search_response_items(payload):
    """Compatibility wrapper for slskd response normalization."""
    from slskd_search import response_items

    return response_items(payload)

def _slskd_path_match_diagnostics(payload, artist, album, limit=10):
    """Compatibility wrapper for bounded slskd path diagnostics."""
    from slskd_search import path_match_diagnostics

    return path_match_diagnostics(
        payload, artist, album, limit,
        music_key=_music_key,
        album_path_match=_slskd_album_path_match,
    )

def _slskd_extract_candidates(payload, artist, album, priority, expected_track_count=None):
    """Compatibility wrapper for slskd candidate grouping and ranking."""
    from slskd_search import extract_candidates

    return extract_candidates(
        payload, artist, album, priority, expected_track_count,
        music_key=_music_key,
        album_path_match=_slskd_album_path_match,
        quality_tier=_slskd_quality_tier,
        track_identity=_slskd_track_identity,
    )

def _slskd_download_transfer_files(base_url, headers, username):
    """Return tracked files while preserving their remote-directory identity."""
    from urllib.parse import quote

    response = httpx.get(
        f"{base_url}/api/v0/transfers/downloads/"
        f"{quote(str(username), safe='')}",
        headers=headers,
        timeout=8,
    )
    # slskd can remove a peer's transfer entry after the transfers finish or
    # disappear. A 404 therefore means there are no currently tracked files for
    # this peer, not that the watcher itself failed. The caller still checks the
    # completed-download filesystem before and on every subsequent poll.
    if response.status_code == 404:
        return []
    response.raise_for_status()
    payload = response.json()

    if isinstance(payload, list):
        roots = payload
    elif isinstance(payload, dict):
        roots = payload.get("directories") or payload.get("items") or [payload]
    else:
        roots = []

    found = []

    def add_files(directory_record, fallback_directory=None):
        if not isinstance(directory_record, dict):
            return

        remote_directory = (
            directory_record.get("directory")
            or fallback_directory
        )

        for file_record in directory_record.get("files") or []:
            if not isinstance(file_record, dict):
                continue

            # Return a copy; do not mutate the API response.
            item = dict(file_record)
            item["_transfer_directory"] = (
                str(remote_directory)
                if remote_directory is not None
                else None
            )
            found.append(item)

        for child in directory_record.get("directories") or []:
            if isinstance(child, dict):
                add_files(child, remote_directory)

    for root in roots:
        if isinstance(root, dict):
            add_files(root)

    return found

def _slskd_candidate_start_state(base_url, headers, candidate, timeout=8):
    """Compatibility adapter for independently tested candidate-start validation."""
    return _module_candidate_start_state(
        base_url, headers, candidate, timeout,
        download_transfer_files=_slskd_download_transfer_files,
        http_client=httpx,
        http_error_types=(httpx.HTTPError,),
        monotonic=time.monotonic,
        sleep=time.sleep,
    )

def _discovery_safe_folder_name(value):
    """Compatibility wrapper; implementation lives in acquisition_completion."""
    return _acquisition_safe_folder_name(value)


_DISCOVERY_IMPORT_LOCK = __import__("threading").Lock()
# Serializes dismissal against the final import transition. Held only while
# committing the local import/dismiss state, never during the download.
_DISCOVERY_IMPORT_TRANSITION_LOCK = __import__("threading").RLock()
_DISCOVERY_IMPORT_ACTIVE = set()
_DISCOVERY_ACQUIRE_ACTIVE = set()


def _discovery_save_acquisition_job(artist, album, status, details=None,
                                    candidate=None, settings=None):
    """Compatibility adapter for the directly importable acquisition state store."""
    return _acquisition_state.save_job(
        artist, album, status, details, candidate=candidate, settings=settings,
        services={
            "init": _discovery_init,
            "db_path": DISCOVERY_DB,
            "music_key": _music_key,
            "clock": time.time,
        },
    )


def _discovery_update_acquisition_status(artist, album, status, details=None):
    """Persist acquisition state and best-effort mirror it to For Me.

    Return True only when the authoritative acquisition row was persisted.
    Feedback metadata is a secondary projection and must not turn a successful
    acquisition-state write into a reported persistence failure.
    """
    details = details or {}
    try:
        with _DISCOVERY_IMPORT_TRANSITION_LOCK:
            if status != "dismissed" and _discovery_is_dismissed(artist, album):
                return False
            _discovery_save_acquisition_job(artist, album, status, details)
            persisted = True

            try:
                identity = (_music_key(artist), _music_key(album))
                row = next((
                    item for item in _discovery_feedback_rows()
                    if item["scope"] == "album" and item["status"] == "for_me"
                    and item["artist_key"] == identity[0] and item["album_key"] == identity[1]
                ), None)
                if row:
                    metadata = row.get("metadata") or {}
                    metadata["auto_acquisition"] = {
                        "status": status, "updated_at": time.time(), **details
                    }
                    _discovery_save_feedback("album", artist, album, "for_me", metadata)
            except Exception:
                # Feedback is a secondary view; the acquisition row is authoritative.
                pass
            return persisted
    except Exception:
        # Callers that are about to mutate files can now stop if persistence failed.
        return False


def _discovery_list_acquisition_jobs():
    """Compatibility adapter for the directly importable acquisition state store."""
    return _acquisition_state.list_jobs(services={
        "init": _discovery_init,
        "db_path": DISCOVERY_DB,
    })


# Per-process snapshots used to calculate an instantaneous speed from byte deltas.
_DISCOVERY_PROGRESS_SNAPSHOTS = {}
_DISCOVERY_PROGRESS_SNAPSHOT_LOCK = __import__("threading").Lock()


def _discovery_live_download_progress(job):
    """Return live slskd progress and a delta-based speed estimate."""
    candidate = job.get("candidate") or {}
    expected_files = candidate.get("files") or []
    username = candidate.get("username")
    if not expected_files or not username:
        return None

    try:
        base_url, api_key, _ = _slskd_config()
        tracked = _slskd_download_transfer_files(
            base_url, {"X-API-KEY": api_key}, username
        )
    except Exception:
        return {
            "available": False,
            "total_tracks": len(expected_files),
            "remaining_tracks": len(expected_files),
            "completed_tracks": 0,
            "percent": None,
            "speed_bytes_per_second": None,
        }

    def basename(value):
        return str(value or "").replace("\\", "/").rsplit("/", 1)[-1].casefold()

    expected_by_name = {}
    for item in expected_files:
        name = basename(item.get("filename"))
        if name:
            expected_by_name[name] = item

    tracked_by_name = {}
    for item in tracked:
        name = basename(item.get("filename"))
        if name not in expected_by_name:
            continue
        prior = tracked_by_name.get(name)
        state = str(item.get("state") or "").replace("_", "").casefold()
        prior_state = str((prior or {}).get("state") or "").replace("_", "").casefold()
        rank = lambda value: 2 if value in {"succeeded", "completed"} else 1 if value in {"inprogress", "transferring", "downloading"} else 0
        if prior is None or rank(state) >= rank(prior_state):
            tracked_by_name[name] = item

    completed_states = {"succeeded", "completed"}
    completed = 0
    total_bytes = 0
    transferred_bytes = 0
    file_byte_snapshot = {}

    for name, expected in expected_by_name.items():
        item = tracked_by_name.get(name) or {}
        state = str(item.get("state") or "").replace("_", "").casefold()
        is_completed_state = state in completed_states
        if is_completed_state:
            completed += 1

        try:
            size = max(0, int(expected.get("size") or item.get("size") or 0))
        except (TypeError, ValueError):
            size = 0
        transferred = 0
        raw_transferred = 0
        has_transfer_counter = False
        for key in ("bytesTransferred", "bytesDownloaded", "downloadedBytes", "transferredBytes"):
            if item.get(key) is not None:
                try:
                    raw_transferred = max(0, int(item[key]))
                    transferred = raw_transferred
                    has_transfer_counter = True
                    break
                except (TypeError, ValueError):
                    pass
        if is_completed_state and size:
            transferred = size
        if size:
            transferred = min(transferred, size)
            total_bytes += size
            transferred_bytes += transferred
            if transferred >= size and not is_completed_state:
                completed += 1
        # Speed uses only actual counters, never an inferred completed-file size.
        file_byte_snapshot[name] = raw_transferred if has_transfer_counter else 0

    now = time.monotonic()
    snapshot_key = (
        str(job.get("artist_key") or _music_key(job.get("artist"))),
        str(job.get("album_key") or _music_key(job.get("album"))),
        str(username).casefold(),
    )
    speed = None
    with _DISCOVERY_PROGRESS_SNAPSHOT_LOCK:
        prior = _DISCOVERY_PROGRESS_SNAPSHOTS.get(snapshot_key)
        _DISCOVERY_PROGRESS_SNAPSHOTS[snapshot_key] = {
            "at": now, "files": file_byte_snapshot,
        }
        if prior:
            elapsed = now - prior["at"]
            if elapsed >= 0.5:
                delta = sum(
                    max(0, value - int(prior["files"].get(name, 0)))
                    for name, value in file_byte_snapshot.items()
                )
                speed = int(delta / elapsed)

    percent = round(min(100.0, max(0.0, transferred_bytes / total_bytes * 100.0)), 1) if total_bytes else None
    total_tracks = len(expected_by_name)
    return {
        "available": True,
        "total_tracks": total_tracks,
        "completed_tracks": min(completed, total_tracks),
        "remaining_tracks": max(0, total_tracks - completed),
        "percent": percent,
        "total_size_bytes": total_bytes if total_bytes else None,
        "remaining_size_bytes": max(0, total_bytes - transferred_bytes) if total_bytes else None,
        "speed_bytes_per_second": speed,
    }


def discovery_get_acquisition_status():
    """Return persistent acquisition state plus best-effort live download progress."""
    jobs = _discovery_list_acquisition_jobs()
    for job in jobs:
        if job["status"] == "dismissed":
            continue
        identity = (job["artist_key"], job["album_key"])
        candidate, settings = job["candidate"], job["settings"]
        if not _acquisition_lifecycle.should_resume_monitor(job["status"], candidate, False):
            continue
        with _DISCOVERY_IMPORT_LOCK:
            if identity in _DISCOVERY_IMPORT_ACTIVE:
                continue
            _DISCOVERY_IMPORT_ACTIVE.add(identity)
        import threading
        threading.Thread(
            target=_discovery_import_watcher_entry,
            args=(job["artist"], job["album"], candidate, settings, identity),
            name="navidrome-import-recovery",
            daemon=True,
        ).start()
    acquisitions = []
    for job in jobs:
        if job["status"] == "dismissed":
            continue
        public_job = {
            k: v for k, v in job.items()
            if k not in {"candidate", "settings", "artist_key", "album_key"}
        }
        if job["status"] in {"downloading", "download_complete_waiting_for_folder"}:
            progress = _discovery_live_download_progress(job)
            if progress is not None:
                public_job["details"] = dict(public_job.get("details") or {})
                public_job["details"]["live_progress"] = progress
        acquisitions.append(public_job)
    return json.dumps({"ok": True, "acquisitions": acquisitions}, ensure_ascii=False, indent=2)


def _discovery_import_watcher_entry(artist, album, candidate, settings, identity):
    try:
        _discovery_watch_and_import_album(artist, album, candidate, settings)
    except Exception as exc:
        # Failures before the watch loop's own exception handler (for example,
        # invalid configuration during watcher initialization) must not leave a
        # stale "downloading" job behind.
        _discovery_update_acquisition_status(artist, album, "monitor_error", {
            "error": type(exc).__name__,
            "message": "Acquisition watcher stopped unexpectedly.",
        })
    finally:
        with _DISCOVERY_IMPORT_LOCK:
            _DISCOVERY_IMPORT_ACTIVE.discard(identity)


def _discovery_filename_key(value):
    """Compatibility wrapper; implementation lives in acquisition_completion."""
    return _acquisition_filename_key(value)


def _discovery_match_completed_album_files(folder, candidate):
    """Compatibility wrapper for strict completion-file matching."""
    return _acquisition_match_completed_album_files(folder, candidate)



def _discovery_inspect_completed_album(download_root, candidate):
    """Return strict folder-match evidence and diagnostics for a completed transfer."""
    return inspect_completed_album(
        download_root,
        candidate,
        safe_folder_name=_discovery_safe_folder_name,
        filename_key=_discovery_filename_key,
        match_files=_discovery_match_completed_album_files,
    )


def _discovery_locate_completed_album(download_root, candidate):
    """Return a uniquely verified folder; never relax track or folder identity checks."""
    return _discovery_inspect_completed_album(download_root, candidate)["path"]

def _discovery_import_matched_album_files(source, destination, candidate, expected_music_root=None, expected_device=None):
    """Compatibility wrapper; filesystem import implementation lives in acquisition_import."""
    return _acquisition_import_matched_album_files(
        source,
        destination,
        candidate,
        expected_music_root=expected_music_root,
        expected_device=expected_device,
        match_files=_discovery_match_completed_album_files,
    )


def _discovery_is_dismissed(artist, album):
    return any(
        job["artist_key"] == _music_key(artist)
        and job["album_key"] == _music_key(album)
        and job["status"] == "dismissed"
        for job in _discovery_list_acquisition_jobs()
    )


def discovery_dismiss_acquisition(artist, album):
    """Safely stop an acquisition, clean its known download files, and dismiss its card."""
    _discovery_init()
    identity = (_music_key(artist), _music_key(album))
    with _DISCOVERY_IMPORT_TRANSITION_LOCK:
        with sqlite3.connect(DISCOVERY_DB, timeout=10) as db:
            row = db.execute(
                "SELECT status, details_json, candidate_json, settings_json "
                "FROM discovery_acquisitions WHERE artist_key=? AND album_key=?",
                identity,
            ).fetchone()
            if not row:
                return json.dumps({"ok": False, "error": "Acquisition not found."})
            if row[0] == "dismissed":
                return json.dumps({"ok": True, "status": "dismissed", "message": "Acquisition is already dismissed."})
            try:
                details = json.loads(row[1] or "{}")
                candidate = json.loads(row[2] or "{}")
                saved_settings = json.loads(row[3] or "{}")
            except (ValueError, TypeError):
                details, candidate, saved_settings = {}, {}, {}

            files = candidate.get("files") or []
            cleanup_required = _acquisition_lifecycle.cleanup_required(row[0], details)

            if files:
                try:
                    base_url, api_key, current_settings = _slskd_config()
                    download_root = (
                        current_settings.get("slskd_downloads_path")
                        or saved_settings.get("slskd_downloads_path")
                        or _DISCOVERY_SETTINGS_DEFAULTS["slskd_downloads_path"]
                    )
                    cleaned = _discovery_cancel_and_clean_source(
                        download_root, candidate, base_url, {"X-API-KEY": api_key}
                    )
                except Exception:
                    cleaned = False
                if not cleaned:
                    return json.dumps({
                        "ok": False,
                        "error": (
                            "Could not safely cancel this source and remove its download files. "
                            "Nothing was dismissed; check the download folder and acquisition settings."
                        ),
                    })
            elif cleanup_required:
                return json.dumps({
                    "ok": False,
                    "error": (
                        "The acquisition may have download files, but its source file inventory is missing. "
                        "For safety, the card was not dismissed and no files were deleted."
                    ),
                })

            details.update({"status": "dismissed", "dismissed_at": time.time(),
                            "cleanup_confirmed": True})
            db.execute(
                "UPDATE discovery_acquisitions SET status='dismissed', details_json=?, updated_at=? "
                "WHERE artist_key=? AND album_key=?",
                (json.dumps(details, ensure_ascii=False), time.time(), *identity),
            )
            db.commit()
    return json.dumps({
        "ok": True, "status": "dismissed",
        "message": "Acquisition dismissed and its safely identified download files were removed.",
    })


def _discovery_skip_requested(artist, album):
    for job in _discovery_list_acquisition_jobs():
        if job["artist_key"] == _music_key(artist) and job["album_key"] == _music_key(album):
            return bool((job.get("details") or {}).get("skip_requested"))
    return False


def discovery_skip_acquisition_source(artist, album):
    """Compatibility adapter for the importable acquisition lifecycle service."""
    return json.dumps(acquisition_orchestration.request_skip_acquisition_source(
        artist, album,
        initialize=_discovery_init,
        transition_lock=_DISCOVERY_IMPORT_TRANSITION_LOCK,
        connect=lambda: sqlite3.connect(DISCOVERY_DB, timeout=10),
        music_key=_music_key,
        lifecycle=_acquisition_lifecycle,
        now=time.time,
        json_module=json,
    ), ensure_ascii=False)

def _discovery_cancel_and_clean_source(
    download_root, candidate, base_url, headers
):
    """Compatibility adapter for the directly testable cleanup implementation."""
    return _clean_acquisition_source(
        download_root,
        candidate,
        base_url,
        headers,
        safe_folder_name=_discovery_safe_folder_name,
        download_transfer_files=_slskd_download_transfer_files,
        http_client=httpx,
    )

def _discovery_switch_to_next_source(artist, album, candidate, settings, download_root, headers, reason):
    """Compatibility adapter for dismissal-serialized fallback switching."""
    return acquisition_orchestration.switch_source_unless_dismissed(
        artist, album,
        transition_lock=_DISCOVERY_IMPORT_TRANSITION_LOCK,
        is_dismissed=_discovery_is_dismissed,
        switch_source=lambda: _discovery_switch_to_next_source_locked(
            artist, album, candidate, settings, download_root, headers, reason
        ),
    )


def _discovery_switch_to_next_source_locked(artist, album, candidate, settings, download_root, headers, reason):
    """Compatibility adapter for directly tested source-switch orchestration."""
    return _switch_to_next_source_locked(
        artist,
        album,
        candidate,
        settings,
        download_root,
        headers,
        reason,
        get_slskd_config=_slskd_config,
        lifecycle=_acquisition_lifecycle,
        cleanup_source=_discovery_cancel_and_clean_source,
        update_status=_discovery_update_acquisition_status,
        http_client=httpx,
        candidate_start_state=_slskd_candidate_start_state,
        save_job=_discovery_save_acquisition_job,
        list_jobs=_discovery_list_acquisition_jobs,
        music_key=_music_key,
    )

def _discovery_import_completed_source(artist, album, source, music_root, candidate):
    """Import a verified source only if dismissal has not won the race."""
    return _acquisition_orchestration.import_source_unless_dismissed(
        artist,
        album,
        transition_lock=_DISCOVERY_IMPORT_TRANSITION_LOCK,
        is_dismissed=_discovery_is_dismissed,
        import_source=lambda: _discovery_import_completed_source_locked(
            artist, album, source, music_root, candidate
        ),
    )


def _discovery_import_completed_source_locked(artist, album, source, music_root, candidate):
    """Perform import validation and I/O while the transition lock is held."""
    try:
        music_root = Path(music_root).expanduser().resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError):
        music_root = None

    if music_root is None or not music_root.is_dir():
        _discovery_update_acquisition_status(artist, album, "library_mount_unavailable", {
            "source_folder": str(source),
            "downloads_path": str(source.parent),
            "library_path": str(music_root),
        })
        return "failed"

    try:
        music_device = music_root.stat().st_dev
    except OSError:
        music_device = None
    if music_device is None:
        _discovery_update_acquisition_status(artist, album, "library_mount_unavailable", {
            "source_folder": str(source), "library_path": str(music_root),
        })
        return "failed"

    artist_dir = music_root / _discovery_safe_folder_name(artist)
    album_dir = artist_dir / _discovery_safe_folder_name(album)

    # Reject symlinked artist paths and non-directory filesystem objects.
    if artist_dir.is_symlink() or (
        artist_dir.exists() and not artist_dir.is_dir()
    ):
        _discovery_update_acquisition_status(
            artist, album, "download_complete_move_failed",
            {"error": "Unsafe import destination: artist path is a symlink or not a directory."},
        )
        return "failed"

    if artist_dir.exists():
        try:
            resolved_artist = artist_dir.resolve(strict=True)
        except (OSError, RuntimeError):
            resolved_artist = None

        if resolved_artist is None or resolved_artist.parent != music_root:
            _discovery_update_acquisition_status(
                artist, album, "download_complete_move_failed",
                {"error": "Unsafe import destination: artist directory is outside the music root."},
            )
            return "failed"

    # exists() alone misses broken symlinks.
    if album_dir.exists() or album_dir.is_symlink():
        _discovery_update_acquisition_status(artist, album, "destination_exists", {
            "source_folder": str(source), "destination": str(album_dir)
        })
        return "failed"

    if not _discovery_update_acquisition_status(artist, album, "importing", {
        "source_folder": str(source), "destination": str(album_dir),
        "music_root_device": music_device,
    }):
        return "failed"
    try:
        if music_root.stat().st_dev != music_device:
            raise OSError("Music-library filesystem changed before import")
        artist_dir.mkdir(parents=True, exist_ok=True)

        # Revalidate immediately before creating staging files.
        if artist_dir.is_symlink() or not artist_dir.is_dir():
            raise OSError("Artist destination is not a real directory")

        resolved_artist = artist_dir.resolve(strict=True)
        if resolved_artist.parent != music_root:
            raise OSError("Artist destination resolves outside the music root")

        if album_dir.exists() or album_dir.is_symlink():
            raise FileExistsError(str(album_dir))

        if music_root.stat().st_dev != music_device or artist_dir.stat().st_dev != music_device:
            raise OSError("Music-library filesystem changed before import")
        _discovery_import_matched_album_files(
            source, album_dir, candidate,
            expected_music_root=music_root, expected_device=music_device,
        )
    except OSError as exc:
        _discovery_update_acquisition_status(artist, album, "download_complete_move_failed", {
            "source_folder": str(source), "destination": str(album_dir),
            "error": str(exc), "downloads_path": str(source.parent),
        })
        return "failed"
    except Exception as exc:
        # Do not leave the persistent acquisition stuck in "importing" if
        # an unexpected import error occurs; retain the completed download.
        _discovery_update_acquisition_status(artist, album, "download_complete_move_failed", {
            "source_folder": str(source), "destination": str(album_dir),
            "error": f"Unexpected import error ({type(exc).__name__}): {exc}",
            "downloads_path": str(source.parent),
        })
        return "failed"

    _discovery_update_acquisition_status(artist, album, "imported", {
        "source_folder": str(source), "destination": str(album_dir),
        "source_username": candidate.get("username"), "imported_at": time.time()
    })
    return "imported"


def _discovery_reconcile_interrupted_import(artist, album, candidate):
    """Compatibility adapter for directly tested interrupted-import recovery."""
    return _reconcile_interrupted_import(
        artist,
        album,
        candidate,
        transition_lock=_DISCOVERY_IMPORT_TRANSITION_LOCK,
        is_dismissed=_discovery_is_dismissed,
        music_key=_music_key,
        list_acquisition_jobs=_discovery_list_acquisition_jobs,
        music_dir=MUSIC_DIR,
        safe_folder_name=_discovery_safe_folder_name,
        match_completed_album_files=_discovery_match_completed_album_files,
        update_status=_discovery_update_acquisition_status,
        json_module=json,
        now=time.time,
        move_file=shutil.move,
    )

def _discovery_watch_and_import_album(artist, album, candidate, settings):
    """Compatibility adapter for the importable acquisition watcher."""
    from acquisition_watcher import watch_and_import_album
    return watch_and_import_album(
        artist, album, candidate, settings,
        services={
            "music_dir": MUSIC_DIR,
            "reconcile_interrupted_import": _discovery_reconcile_interrupted_import,
            "slskd_config": _slskd_config,
            "settings_defaults": _DISCOVERY_SETTINGS_DEFAULTS,
            "is_dismissed": _discovery_is_dismissed,
            "skip_requested": _discovery_skip_requested,
            "switch_to_next_source": _discovery_switch_to_next_source,
            "locate_completed_album": _discovery_locate_completed_album,
            "import_completed_source": _discovery_import_completed_source,
            "download_transfer_files": _slskd_download_transfer_files,
            "update_status": _discovery_update_acquisition_status,
            "inspect_completed_album": _discovery_inspect_completed_album,
        },
    )

def _discovery_start_import_watcher(artist, album, candidate, settings):
    """Compatibility adapter for dependency-injected watcher startup."""
    from acquisition_watcher_startup import start_import_watcher
    start_import_watcher(
        artist, album, candidate, settings,
        services={
            "music_key": _music_key,
            "transition_lock": _DISCOVERY_IMPORT_TRANSITION_LOCK,
            "import_lock": _DISCOVERY_IMPORT_LOCK,
            "active": _DISCOVERY_IMPORT_ACTIVE,
            "is_dismissed": _discovery_is_dismissed,
            "save_job": _discovery_save_acquisition_job,
            "update_status": _discovery_update_acquisition_status,
            "watcher_entry": _discovery_import_watcher_entry,
        },
    )


def _discovery_queue_candidate_unless_dismissed(
    artist, album, base_url, headers, username, selected_files
):
    """Compatibility adapter for the directly tested queue/dismissal guard."""
    def queue_source():
        response = httpx.post(
            f"{base_url}/api/v0/transfers/downloads/{username}",
            headers=headers,
            json=selected_files,
            timeout=12,
        )
        response.raise_for_status()
        return response

    return acquisition_orchestration.queue_candidate_unless_dismissed(
        artist, album,
        transition_lock=_DISCOVERY_IMPORT_TRANSITION_LOCK,
        is_dismissed=_discovery_is_dismissed,
        queue_source=queue_source,
    )


def _slskd_queue_failure_action(exc):
    """Classify queue errors without risking duplicate downloads."""
    return _acquisition_lifecycle.queue_failure_action(exc)


def _discovery_acquire_album_impl(
    artist: str,
    album: str,
    metadata_json: str = "{}",
    auto_queue: bool = True,
) -> str:
    """Search slskd; queue the best clear match, fall back to faster/next sources if it does not start, and import on completion."""
    import uuid
    if not artist.strip() or not album.strip():
        return json.dumps({"ok": False, "error": "Artist and album are required."})
    try:
        metadata = json.loads(metadata_json or "{}")
        if not isinstance(metadata, dict):
            metadata = {}
    except (ValueError, TypeError):
        metadata = {}
    try:
        base_url, api_key, settings = _slskd_config()
    except ValueError as exc:
        message = str(exc)
        _discovery_update_acquisition_status(
            artist, album, "settings_required",
            {"message": message, "metadata": metadata},
        )
        return json.dumps({"ok": False, "status": "settings_required", "artist": artist,
                           "album": album, "message": message}, ensure_ascii=False)
    priority = settings.get("quality_priority", _DISCOVERY_SETTINGS_DEFAULTS["quality_priority"])
    headers = {"X-API-KEY": api_key}
    search_queries = _slskd_search_queries(artist, album)
    try:
        from slskd_search_polling import collect_search_responses

        search_result = collect_search_responses(
            search_queries,
            base_url,
            headers,
            http_client=httpx,
            monotonic=time.monotonic,
            sleep=time.sleep,
            new_search_id=lambda: str(uuid.uuid4()),
            response_items=_slskd_search_response_items,
        )
        search_id = search_result["search_id"]
        search_attempts = search_result["search_attempts"]
        reported_response_count = search_result["reported_response_count"]
        reported_file_count = search_result["reported_file_count"]
        payload_by_peer = search_result["payload_by_peer"]
        expected_track_count = _discovery_expected_track_count(metadata)
        candidates = _slskd_extract_candidates(
            list(payload_by_peer.values()), artist, album, priority,
            expected_track_count=expected_track_count,
        )
        candidate_diagnostics = [
            {
                "username": item.get("username"),
                "folder": item.get("folder"),
                "file_count": item.get("file_count"),
                "unique_track_count": item.get("unique_track_count"),
                "expected_track_count": item.get("expected_track_count"),
                "quality_summary": list(item.get("quality_summary") or []),
                "clear_match": bool(item.get("clear_match")),
                "eligibility_reason": item.get("eligibility_reason"),
            }
            for item in candidates[:10]
        ]
        if not candidates:
            audio_exts = {".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".aiff", ".ape"}
            response_count = len(payload_by_peer)
            audio_file_count = sum(
                1 for entry in payload_by_peer.values()
                for item in (entry.get("files") or [])
                if isinstance(item, dict)
                and Path(str(item.get("filename") or item.get("path") or "")).suffix.casefold() in audio_exts
            )
            path_diagnostics = _slskd_path_match_diagnostics(
                list(payload_by_peer.values()), artist, album
            )
            attempted_queries = " -> ".join(
                item["query"] for item in search_attempts
            )
            message = (
                f"No matching album folders were found among {response_count} collected peer responses "
                f"({audio_file_count} audio files). slskd reported up to {reported_response_count} "
                f"responses and {reported_file_count} files across the search attempts. "
                "If the counts are zero, no peers answered the attempted queries; otherwise "
                "the response payloads may not have been available to Librarian. "
                f"Queries tried: {attempted_queries}."
            )
            _discovery_update_acquisition_status(
                artist, album, "no_matches",
                {
                    "message": message, "search_id": search_id, "metadata": metadata,
                    "peer_responses_seen": response_count, "audio_files_seen": audio_file_count,
                    "slskd_reported_response_count": reported_response_count,
                    "slskd_reported_file_count": reported_file_count,
                    "search_queries_attempted": search_attempts,
                    "path_diagnostics": path_diagnostics,
                },
            )
            return json.dumps({
                "ok": True, "status": "no_matches", "artist": artist, "album": album,
                "search_id": search_id, "message": message,
                "peer_responses_seen": response_count, "audio_files_seen": audio_file_count,
                "slskd_reported_response_count": reported_response_count,
                "slskd_reported_file_count": reported_file_count,
                "search_queries_attempted": search_attempts,
                "path_diagnostics": path_diagnostics,
            }, ensure_ascii=False)
        clear_candidates = [candidate for candidate in candidates if candidate["clear_match"]]
        if not auto_queue:
            return json.dumps({
                "ok": True, "status": "review_required", "artist": artist, "album": album,
                "search_id": search_id, "candidates": candidates[:10],
                "message": "Candidate review was requested explicitly.",
            }, ensure_ascii=False)
        if not clear_candidates:
            best = candidates[0]
            message = "Potential files were found, but none met the relaxed artist, album, and track-count checks. You can try again later."
            _discovery_update_acquisition_status(
                artist, album, "no_matches",
                {"message": message, "search_id": search_id, "metadata": metadata,
                 "candidate_count": len(candidates),
                 "best_candidate_reason": best.get("eligibility_reason"),
                 "candidate_diagnostics": candidate_diagnostics},
            )
            return json.dumps({
                "ok": True, "status": "no_matches", "artist": artist, "album": album,
                "search_id": search_id, "candidate_count": len(candidates),
                "candidate_diagnostics": candidate_diagnostics,
                "message": message,
            }, ensure_ascii=False)

        failures = []
        uncertain = None
        for candidate in clear_candidates[:10]:
            selected_files = [
                {"filename": item["filename"], "size": item["size"]}
                for item in candidate["files"]
            ]
            try:
                queue = _discovery_queue_candidate_unless_dismissed(
                    artist, album, base_url, headers, candidate["username"], selected_files
                )
                if queue is None:
                    return json.dumps({
                        "ok": False, "status": "dismissed", "artist": artist, "album": album,
                        "message": "This acquisition was dismissed before a source could be queued.",
                    }, ensure_ascii=False)
            except httpx.HTTPError as exc:
                queue_error_action = _slskd_queue_failure_action(exc)
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
                if queue_error_action == "retry_source":
                    failures.append({
                        "username": candidate["username"],
                        "folder": candidate["folder"],
                        "http_status": status_code,
                        "error": "source_rejected",
                        "detail": str(exc)[:200],
                    })
                    continue
                if queue_error_action == "fatal":
                    message = (
                        f"slskd rejected the queue request with HTTP {status_code}; "
                        "check the API key and its permissions."
                    )
                    _discovery_update_acquisition_status(
                        artist, album, "slskd_error",
                        {"message": message, "http_status": status_code,
                         "metadata": metadata, "attempts": failures},
                    )
                    return json.dumps({
                        "ok": False, "status": "slskd_error", "artist": artist,
                        "album": album, "http_status": status_code,
                        "attempts": failures, "message": message,
                    }, ensure_ascii=False)
                # A timeout or server error can happen after slskd accepted
                # the queue request. Monitor this peer before considering a
                # fallback, otherwise two sources could download the album.
                candidate_for_monitor = _prepare_candidate_for_monitor(
                    candidate, clear_candidates[clear_candidates.index(candidate) + 1:10]
                )
                _discovery_start_import_watcher(
                    artist, album, candidate_for_monitor, settings
                )
                return json.dumps({
                    "ok": True, "status": "queued_unconfirmed",
                    "artist": artist, "album": album,
                    "source_username": candidate["username"],
                    "folder": candidate["folder"],
                    "message": (
                        "The queue request returned an HTTP error, so its outcome "
                        "is uncertain. Monitoring this source before attempting "
                        "another peer to avoid duplicate downloads."
                    ),
                }, ensure_ascii=False)
            except (ValueError, TypeError) as exc:
                failures.append({
                    "username": candidate["username"],
                    "folder": candidate["folder"],
                    "error": type(exc).__name__,
                })
                continue

            candidate_for_monitor = _prepare_candidate_for_monitor(
                candidate, clear_candidates[clear_candidates.index(candidate) + 1:10]
            )
            start_state = _slskd_candidate_start_state(
                base_url, headers, candidate_for_monitor, timeout=8
            )
            if start_state is False:
                # Do not try another peer until the previous queue attempt is
                # confirmed stopped and its exact partial folder is safe to clean.
                download_root = Path(str(
                    settings.get("slskd_downloads_path")
                    or _DISCOVERY_SETTINGS_DEFAULTS["slskd_downloads_path"]
                )).expanduser()
                if not _discovery_cancel_and_clean_source(
                    download_root, candidate_for_monitor, base_url, headers
                ):
                    _discovery_update_acquisition_status(
                        artist, album, "source_switch_failed", {
                            "source_username": candidate.get("username"),
                            "folder": candidate.get("folder"),
                            "error": (
                                "The queued source did not start, but its transfers "
                                "or partial files could not be safely confirmed and "
                                "cleaned. No further source was queued."
                            ),
                        },
                    )
                    return json.dumps({
                        "ok": False, "status": "source_switch_failed",
                        "artist": artist, "album": album,
                        "message": (
                            "The first source did not start, and cleanup could not "
                            "be confirmed. Check the acquisition status before retrying."
                        ),
                    }, ensure_ascii=False)
                failures.append({
                    "username": candidate["username"],
                    "folder": candidate["folder"],
                    "error": "download_did_not_start",
                })
                continue
            if start_state is None:
                uncertain = candidate
                break
            _discovery_start_import_watcher(
                artist, album, candidate_for_monitor, settings
            )
            return json.dumps({
                "ok": True, "status": "queued",
                "artist": artist, "album": album,
                "source_username": candidate["username"],
                "folder": candidate["folder"],
                "file_count": len(selected_files),
                "quality_summary": candidate["quality_summary"],
                "upload_speed": candidate["upload_speed"],
                "fallback_attempts": failures,
                "message": "Download started from the best clear match. The album will be moved into the music library when all files finish.",
            }, ensure_ascii=False)

        if uncertain is not None:
            candidate_for_monitor = _prepare_candidate_for_monitor(
                uncertain, clear_candidates[clear_candidates.index(uncertain) + 1:10]
            )
            _discovery_start_import_watcher(
                artist, album, candidate_for_monitor, settings
            )
            return json.dumps({
                "ok": True, "status": "queued_unconfirmed",
                "artist": artist, "album": album,
                "source_username": uncertain["username"],
                "folder": uncertain["folder"],
                "fallback_attempts": failures,
                "message": "slskd accepted the queue request, but its transfer state could not be verified. Monitoring this source to avoid duplicate downloads.",
            }, ensure_ascii=False)

        message = "None of the matching sources started a download. Check slskd/peer availability and try again."
        _discovery_update_acquisition_status(
            artist, album, "queue_failed",
            {"message": message, "attempts": failures, "metadata": metadata,
             "candidate_diagnostics": candidate_diagnostics},
        )
        return json.dumps({
            "ok": False, "status": "queue_failed", "artist": artist, "album": album,
            "attempts": failures, "candidate_diagnostics": candidate_diagnostics,
            "message": message,
        }, ensure_ascii=False)
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        message = f"slskd request failed: {type(exc).__name__}"
        _discovery_update_acquisition_status(
            artist, album, "slskd_error",
            {"message": message, "detail": str(exc)[:300], "metadata": metadata},
        )
        return json.dumps({
            "ok": False, "status": "slskd_error", "artist": artist, "album": album,
            "message": message, "detail": str(exc)[:300],
        }, ensure_ascii=False)


def _discovery_reactivate_dismissed_acquisition(artist, album, metadata=None):
    """Compatibility adapter for the conditional dismissed-job retry transition."""
    return _acquisition_state.reactivate_dismissed_job(
        artist, album, metadata,
        services={
            "init": _discovery_init,
            "db_path": DISCOVERY_DB,
            "music_key": _music_key,
            "clock": time.time,
        },
    )


def discovery_acquire_album(
    artist: str,
    album: str,
    metadata_json: str = "{}",
    auto_queue: bool = True,
) -> str:
    """Prevent concurrent duplicate acquisition searches for the same album."""
    return _acquire_album_request(
        artist, album, metadata_json, auto_queue,
        music_key=_music_key,
        transition_lock=_DISCOVERY_IMPORT_TRANSITION_LOCK,
        watcher_lock=_DISCOVERY_IMPORT_LOCK,
        active_watchers=_DISCOVERY_IMPORT_ACTIVE,
        active_requests=_DISCOVERY_ACQUIRE_ACTIVE,
        list_jobs=_discovery_list_acquisition_jobs,
        is_dismissed=_discovery_is_dismissed,
        reactivate=_discovery_reactivate_dismissed_acquisition,
        start_watcher=_discovery_start_import_watcher,
        lifecycle=_acquisition_lifecycle,
        json_module=json,
        acquire_impl=_discovery_acquire_album_impl,
    )


def discovery_queue_slskd_candidate(
    username: str,
    files_json: str,
    artist: str = "",
    album: str = "",
    folder: str = "",
    quality_summary_json: str = "[]",
) -> str:
    """Queue a user-reviewed slskd candidate and import it into the library when complete."""
    try:
        files = json.loads(files_json)
        if not isinstance(files, list) or not files:
            return json.dumps({"ok": False, "error": "files_json must be a non-empty JSON list."})
        try:
            quality_summary = json.loads(quality_summary_json or "[]")
            if not isinstance(quality_summary, list):
                quality_summary = []
        except (ValueError, TypeError):
            quality_summary = []
        normalized = []
        for item in files:
            if not isinstance(item, dict) or not item.get("filename"):
                return json.dumps({"ok": False, "error": "Each file requires a filename."})
            normalized.append({
                "filename": str(item["filename"]),
                "size": int(item.get("size") or 0),
            })
        base_url, api_key, settings = _slskd_config()
        response = httpx.post(
            f"{base_url}/api/v0/transfers/downloads/{username}",
            headers={"X-API-KEY": api_key},
            json=normalized,
            timeout=12,
        )
        response.raise_for_status()
        import_started = False
        if artist.strip() and album.strip():
            candidate = {
                "username": username,
                "folder": folder or Path(normalized[0]["filename"].replace("\\", "/")).parent.name,
                "files": normalized,
                "quality_summary": quality_summary,
            }
            _discovery_start_import_watcher(artist.strip(), album.strip(), candidate, settings)
            import_started = True
        return json.dumps({
            "ok": True, "status": "queued",
            "username": username, "file_count": len(normalized),
            "import_monitor_started": import_started,
            "message": "Candidate queued. The album will be moved into the library after all files finish." if import_started else "Candidate queued.",
        }, ensure_ascii=False)
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        return json.dumps({
            "ok": False, "error": f"Could not queue candidate ({type(exc).__name__}).",
            "detail": str(exc)[:300],
        }, ensure_ascii=False)

def discovery_get_list(list_name: str = "personal", count: int = 30) -> str:
    """Read saved discovery results or the For Me list.

    list_name is personal or for_me. Dismissed albums and artists are hidden
    from personal results; For Me entries are marked acquired when found in
    the current Navidrome album inventory.
    """
    if list_name not in {"personal", "for_me", "classics", "artist_deep_dive", "new_releases"}:
        return json.dumps({
            "error": "list_name must be personal, classics, artist_deep_dive, new_releases, or for_me."
        })
    if not 1 <= count <= 150:
        return json.dumps({"error": "count must be between 1 and 150"})

    feedback = _discovery_feedback_rows()
    saved = {
        (row["artist_key"], row["album_key"]): row
        for row in feedback
        if row["scope"] == "album" and row["status"] == "for_me"
    }

    if list_name == "for_me":
        try:
            snapshot = _discovery_library_snapshot()
            owned = {
                (_music_key(a.get("artist", "")), _music_key(a.get("album", "")))
                for a in snapshot["albums"]
            }
            inventory_available = True
        except Exception:
            owned = set()
            inventory_available = False

        entries = []
        for row in sorted(saved.values(), key=lambda item: item["updated_at"], reverse=True):
            entries.append({
                "artist": row["artist"],
                "album": row["album"],
                "saved_at": row["created_at"],
                "updated_at": row["updated_at"],
                "acquired": (
                    (row["artist_key"], row["album_key"]) in owned
                    if inventory_available else None
                ),
                "metadata": row["metadata"],
            })
        return json.dumps({
            "list": "for_me",
            "count": len(entries[:count]),
            "total": len(entries),
            "items": entries[:count],
            "library_inventory_available": inventory_available,
            "read_only_except_user_list": True,
        }, ensure_ascii=False, indent=2)

    cached = _discovery_read_list(list_name)
    if not cached:
        return json.dumps({
            "list": list_name,
            "generated_at": None,
            "items": [],
            "message": "No saved list yet. Use discovery_refresh_list or wait for the daily background refresh.",
        }, ensure_ascii=False, indent=2)

    payload = cached["payload"]
    source_items = payload.get("recommendations", []) if list_name == "personal" else payload.get("items", [])
    dismissed_albums = {
        (row["artist_key"], row["album_key"])
        for row in feedback
        if row["scope"] == "album" and row["status"] == "not_for_me"
    }
    dismissed_artists = {
        row["artist_key"]
        for row in feedback
        if row["scope"] == "artist" and row["status"] == "not_for_me_artist"
    }
    visible = []
    for item in source_items:
        artist_key = _music_key(item.get("artist", ""))
        album_key = _music_key(item.get("album", ""))
        identity = (artist_key, album_key)
        if list_name != "for_me" and not _discovery_is_album_candidate(item):
            continue
        if identity in dismissed_albums or artist_key in dismissed_artists:
            continue
        if identity in saved:
            continue
        visible.append(item)

    result = {
        "list": list_name,
        "generated_at": cached["generated_at"],
        "total_before_feedback": len(source_items),
        "count": min(count, len(visible)),
        "items": visible[:count],
        "source": payload.get("source"),
        "limitations": payload.get("limitations", []),
    }
    if list_name == "personal":
        result["recommendations"] = visible[:count]
        result["diagnostics"] = {
            key: payload.get(key)
            for key in (
                "source", "recent_listens_retrieved", "library_albums_indexed",
                "metadata_lookup_errors", "limitations"
            )
            if key in payload
        }
    for key in (
        "library_artists_considered", "owned_albums_checked",
        "critical_ratings_available", "artists_with_three_or_more_owned_albums",
        "missing_albums_and_similar_artist_candidates",
    ):
        if key in payload:
            result[key] = payload[key]
    return json.dumps(result, ensure_ascii=False, indent=2)


def _discovery_refresh_all():
    results = []
    results.append(_discovery_refresh_personal(20))
    results.append(_discovery_refresh_other("classics"))
    results.append(_discovery_refresh_other("artist_deep_dive"))
    results.append(_discovery_refresh_other("new_releases"))
    return results


def discovery_refresh_list(list_name: str = "personal", count: int = 10) -> str:
    """Refresh personal, classics, artist_deep_dive, new_releases, or all lists.

    Personal uses the existing ListenBrainz recommendation engine. Other lists
    use Last.fm and MusicBrainz data and refresh in a background thread.
    """
    import threading

    if list_name not in {"personal", "classics", "artist_deep_dive", "new_releases", "all"}:
        return json.dumps({
            "ok": False,
            "error": "list_name must be personal, classics, artist_deep_dive, new_releases, or all",
        })
    if not 1 <= count <= 20:
        return json.dumps({"ok": False, "error": "count must be between 1 and 20"})

    if list_name == "personal":
        return json.dumps(_discovery_refresh_personal(count), ensure_ascii=False, indent=2)

    target = _discovery_refresh_all if list_name == "all" else _discovery_refresh_other
    args = () if list_name == "all" else (list_name,)
    thread = threading.Thread(
        target=target,
        args=args,
        name="navidrome-refresh-" + list_name,
        daemon=True,
    )
    thread.start()
    return json.dumps({
        "ok": True,
        "status": "started",
        "list": list_name,
        "message": "Refresh is running in the background. Read the list again to check when fresh results are available.",
    }, ensure_ascii=False)


def _refresh_listening_profile_background():
    """Refresh and persist the 30-day ListenBrainz profile without a UI page."""
    try:
        payload = json.loads(recent_listening_profile(days=30))
        if isinstance(payload, dict) and not payload.get("error"):
            payload["background_refresh"] = True
            _discovery_write_list("listening_profile", payload)
            return {"ok": True, "listens_retrieved": payload.get("listens_retrieved", 0)}
        return {"ok": False, "error": "Listening profile returned an error payload"}
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}


def _discovery_scheduler():
    """Refresh discovery lists and the listening profile when older than 24 hours."""
    while True:
        try:
            for list_name in (
                "personal", "classics", "artist_deep_dive", "new_releases",
                "listening_profile",
            ):
                cached = _discovery_read_list(list_name)
                stale = (
                    cached is None
                    or time.time() - cached["generated_at"] >= 24 * 60 * 60
                )
                if not stale:
                    continue
                if list_name == "personal":
                    _discovery_refresh_personal(20)
                elif list_name == "listening_profile":
                    _refresh_listening_profile_background()
                else:
                    _discovery_refresh_other(list_name)
        except Exception:
            pass
        time.sleep(3600)


def _start_discovery_scheduler():
    import threading
    thread = threading.Thread(
        target=_discovery_scheduler,
        name="navidrome-discovery-scheduler",
        daemon=True,
    )
    thread.start()


def restart_server() -> str:
    """Restart only this Navidrome Librarian HTTP server and log the result."""
    import json
    import os
    import subprocess
    import sys
    from pathlib import Path

    target = Path(__file__).resolve()
    log_path = target.with_name("navidrome-restart.log")
    helper_code = r"""
import os, signal, socket, subprocess, sys, time
script, pid_text, port_text, log_path = sys.argv[1:]
pid, port = int(pid_text), int(port_text)
with open(log_path, "a", buffering=1) as log:
    log.write(f"Restart requested for PID {pid} on port {port}\\n")
    time.sleep(2)
    try:
        os.kill(pid, signal.SIGTERM)
        log.write(f"Sent SIGTERM to PID {pid}\\n")
    except ProcessLookupError:
        log.write(f"PID {pid} was already stopped\\n")
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            conn = socket.create_connection(("127.0.0.1", port), timeout=0.3)
            conn.close()
            time.sleep(0.25)
        except OSError:
            break
    else:
        log.write("ERROR: port remained occupied; did not start a second server\\n")
        raise SystemExit(2)
    time.sleep(0.5)
    child = subprocess.Popen(
        [sys.executable, script],
        cwd=os.path.dirname(script),
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    log.write(f"Launched replacement server PID {child.pid}\\n")
    deadline = time.time() + 12
    while time.time() < deadline:
        try:
            conn = socket.create_connection(("127.0.0.1", port), timeout=0.4)
            conn.close()
            log.write("SUCCESS: replacement server is listening\\n")
            break
        except OSError:
            if child.poll() is not None:
                log.write(f"ERROR: replacement process exited with code {child.returncode}\\n")
                raise SystemExit(3)
            time.sleep(0.25)
    else:
        log.write("ERROR: replacement server did not listen within 12 seconds\\n")
        raise SystemExit(4)
"""
    try:
        helper = subprocess.Popen(
            [
                sys.executable, "-c", helper_code,
                str(target), str(os.getpid()), "8000", str(log_path),
            ],
            cwd=str(target.parent),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})
    return json.dumps({
        "ok": True,
        "message": "Restart helper launched. It will stop this server after a short delay, then start the replacement and log the result.",
        "helper_pid": helper.pid,
        "log_file": str(log_path),
    })


def apply_server_patch(old_text: str, new_text: str) -> str:
    """Safely replace one exact, unique section in this server's own source."""
    import difflib
    import json
    import os
    import shutil
    import tempfile
    from datetime import datetime
    from pathlib import Path

    target = Path(__file__).resolve()

    if not old_text:
        return json.dumps({"ok": False, "error": "old_text cannot be empty."})

    if len(old_text) > 100_000 or len(new_text) > 100_000:
        return json.dumps({"ok": False, "error": "Patch exceeds the 100,000-character limit."})

    source = target.read_text(encoding="utf-8")
    matches = source.count(old_text)

    if matches != 1:
        return json.dumps({
            "ok": False,
            "error": "Patch cancelled: original text must match exactly once.",
            "matches": matches,
        })

    updated = source.replace(old_text, new_text, 1)

    try:
        compile(updated, str(target), "exec")
    except SyntaxError as exc:
        return json.dumps({
            "ok": False,
            "error": "Patch rejected: Python syntax validation failed.",
            "line": exc.lineno,
            "detail": exc.msg,
        })

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = target.with_name(f"{target.name}.bak-{stamp}")
    shutil.copy2(target, backup)

    temp_name = None
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=str(target.parent),
        )
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(updated)

        os.chmod(temp_name, target.stat().st_mode)
        os.replace(temp_name, target)
        temp_name = None

        diff = list(difflib.unified_diff(
            source.splitlines(),
            updated.splitlines(),
            fromfile=target.name,
            tofile=target.name,
            lineterm="",
        ))

        return json.dumps({
            "ok": True,
            "backup": str(backup),
            "changed_diff_lines": len(diff),
            "syntax_valid": True,
            "message": "Patch applied. Restart the MCP server to load code changes.",
        }, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({
            "ok": False,
            "error": str(exc),
            "backup": str(backup),
        })
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


if __name__ == "__main__":
    _start_discovery_scheduler()
    import sys
    from mcp_registry import create_mcp_server

    create_mcp_server(sys.modules[__name__]).run(
        transport="streamable-http", host="127.0.0.1", port=8000
    )
