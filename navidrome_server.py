import hashlib
import json
import os
import random
import secrets
import sqlite3
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from mutagen import File
from mcp.server.mcpserver import MCPServer
load_dotenv(Path(__file__).with_name(".env"))

# Persistent MusicBrainz metadata cache, stored beside this script.
METADATA_CACHE_DB = Path(__file__).with_name("navidrome_metadata_cache.sqlite3")


def _metadata_cache_get(key, ttl_seconds):
    """Return cached JSON data if it exists and has not expired."""
    try:
        with sqlite3.connect(METADATA_CACHE_DB, timeout=5) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS metadata_cache (
                    cache_key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    cached_at REAL NOT NULL
                )
            """)
            row = db.execute(
                "SELECT value_json, cached_at FROM metadata_cache "
                "WHERE cache_key = ?",
                (key,),
            ).fetchone()

        if row is None or time.time() - row[1] > ttl_seconds:
            return None

        return json.loads(row[0])
    except (sqlite3.Error, ValueError, TypeError):
        # A cache problem must never prevent recommendations from working.
        return None


def _metadata_cache_set(key, value):
    """Store JSON-compatible metadata; cache failures are non-fatal."""
    try:
        with sqlite3.connect(METADATA_CACHE_DB, timeout=5) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS metadata_cache (
                    cache_key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    cached_at REAL NOT NULL
                )
            """)
            db.execute(
                "INSERT OR REPLACE INTO metadata_cache "
                "(cache_key, value_json, cached_at) VALUES (?, ?, ?)",
                (key, json.dumps(value, ensure_ascii=False), time.time()),
            )
    except (sqlite3.Error, TypeError, ValueError):
        pass

BASE_URL = os.environ["NAVIDROME_URL"].rstrip("/")
USERNAME = os.environ["NAVIDROME_USER"]
PASSWORD = os.environ["NAVIDROME_PASSWORD"]

def _default_music_dir():
    """Choose an explicit override or the native mount path for this host."""
    configured = os.environ.get("NAVIDROME_MUSIC_DIR")
    if configured:
        return Path(configured).expanduser()

    server_path = Path("/media/library/music")
    mac_path = Path("/Volumes/media/library/music")
    if server_path.is_dir():
        return server_path
    if mac_path.is_dir():
        return mac_path
    # The production deployment is the media LXC; this is its default.
    return server_path


MUSIC_DIR = _default_music_dir()

parsed_url = urlparse(BASE_URL)
if parsed_url.scheme not in ("http", "https"):
    raise RuntimeError("NAVIDROME_URL must use HTTP or HTTPS")
if not parsed_url.hostname:
    raise RuntimeError("Invalid NAVIDROME_URL")

mcp = MCPServer("navidrome-librarian")


def api_call(method, **params):
    """Call the Subsonic-compatible API using token authentication."""
    salt = secrets.token_hex(12)
    token = hashlib.md5(
        (PASSWORD + salt).encode("utf-8")
    ).hexdigest()

    query = {
        "u": USERNAME,
        "t": token,
        "s": salt,
        "v": "1.16.1",
        "c": "navidrome-librarian",
        "f": "json",
        **params,
    }

    with httpx.Client(timeout=30, follow_redirects=False) as client:
        response = client.get(
            f"{BASE_URL}/rest/{method}.view",
            params=query,
        )
        response.raise_for_status()
        data = response.json()

    root = data.get("subsonic-response", {})

    if root.get("status") != "ok":
        error = root.get("error", {})
        raise RuntimeError(
            f"Navidrome API error {error.get('code')}: "
            f"{error.get('message', 'Unknown error')}"
        )

    return root


def items(value):
    """Normalize an optional API result to a list."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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
                "https://api.listenbrainz.org/1/user/copi35/listens",
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
    """Return a stable artist key, preferring MusicBrainz artist ID."""
    artist_id = candidate.get("artist_mbid")
    if artist_id:
        return f"mbid:{artist_id}"
    return f"name:{_music_key(candidate.get('primary_artist', ''))}"


def _music_key(value):
    """Normalize names for conservative, accent-insensitive comparisons."""
    import unicodedata
    import re

    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(c for c in value if not unicodedata.combining(c))
    return "".join(c.casefold() for c in value if c.isalnum())


LASTFM_LAST_ERROR = None


def _lastfm_album_popularity(artist, album):
    """Return cached Last.fm album listeners/playcount, or None if unavailable."""
    global LASTFM_LAST_ERROR
    api_key = os.environ.get("LASTFM_API_KEY")
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


@mcp.tool()
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
        "username": "copi35",
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


@mcp.tool()
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
            "cf/recommendation/user/copi35/recording",
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
                    if not title:
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
                    if not album_title:
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
    lastfm_available = bool(os.environ.get("LASTFM_API_KEY"))
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


# Persistent discovery state. Kept beside this server, separate from the music library.
DISCOVERY_DB = Path(__file__).with_name("navidrome_discovery.sqlite3")
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
    _discovery_init()
    with sqlite3.connect(DISCOVERY_DB, timeout=10) as db:
        row = db.execute(
            "SELECT payload_json, generated_at FROM discovery_lists WHERE name = ?",
            (name,),
        ).fetchone()
    if not row:
        return None
    try:
        payload = json.loads(row[0])
    except (ValueError, TypeError):
        return None
    return {"payload": payload, "generated_at": row[1]}


def _discovery_write_list(name, payload):
    _discovery_init()
    with sqlite3.connect(DISCOVERY_DB, timeout=10) as db:
        db.execute(
            "INSERT OR REPLACE INTO discovery_lists (name, payload_json, generated_at) VALUES (?, ?, ?)",
            (name, json.dumps(payload, ensure_ascii=False), time.time()),
        )
        db.commit()


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
    if not _DISCOVERY_REFRESH_LOCK.acquire(blocking=False):
        return {"ok": False, "status": "already_running", "list": "personal"}
    try:
        raw = recommend_new_music(count=count)
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
        except (ValueError, TypeError):
            payload = {"error": "Recommendation engine returned invalid JSON."}
        if not isinstance(payload, dict) or payload.get("error"):
            return {"ok": False, "status": "error", "details": payload}
        _discovery_write_list("personal", payload)
        return {
            "ok": True,
            "list": "personal",
            "generated_at": time.time(),
            "recommendations": len(payload.get("recommendations", [])),
        }
    finally:
        _DISCOVERY_REFRESH_LOCK.release()


@mcp.tool()
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
    api_key = os.environ.get("LASTFM_API_KEY", "").strip()
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
    if cached and time.time() - cached["generated_at"] < 10 * 60:
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
        if not title:
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
    text = " ".join(str(tag).casefold() for tag in tags)
    rules = [
        ("jazz", ("jazz", "bebop", "swing")),
        ("african", ("african", "afrobeat", "afrobeats", "afropop", "highlife",
                     "soukous", "malian", "tuareg", "desert blues", "ethiopian",
                     "mbalax", "senegalese")),
        ("alternative", ("alternative", "indie rock", "post-punk", "art rock",
                         "garage rock", "shoegaze")),
        ("brazilian", ("brazilian", "samba", "bossa nova", "mpb", "tropicalia",
                       "tropicália")),
        ("hip-hop", ("hip hop", "hip-hop", "rap")),
        ("rnb-soul", ("r&b", "rnb", "neo-soul", "soul")),
        ("electronic", ("electronic", "electronica", "house", "techno", "trip hop",
                        "trip-hop", "downtempo", "idm")),
        ("funk", ("funk",)),
        ("north-african-middle-eastern", ("arabic", "raï", "rai", "maghreb",
            "north african", "algerian", "moroccan", "tunisian", "gnawa",
            "gnaoua", "chaabi", "middle eastern", "andalusi", "malouf")),
        ("rock", ("rock", "punk", "metal", "grunge")),
        ("pop", ("pop",)),
    ]
    return [family for family, terms in rules if any(term in text for term in terms)]


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
    import math
    for item in candidates.values():
        rating = item.get("musicbrainz_rating")
        votes = int(item.get("musicbrainz_rating_votes") or 0)
        critical = (float(rating) / 5.0) if rating is not None and votes else 0.0
        listeners = max(0, int(item.get("lastfm_listeners") or 0))
        plays = max(0, int(item.get("lastfm_playcount") or 0))
        popularity_magnitude = math.log10(listeners + 1)
        play_magnitude = math.log10(plays + 1)
        item["critical_recognition_available"] = bool(rating is not None and votes)
        # Unrated and less-heard albums get room to surface; popularity alone
        # should not beat a diverse candidate pool.
        exploration_credit = 0.9 if not (rating is not None and votes) else 0.0
        item["discovery_score"] = round(
            critical * 1.6 - popularity_magnitude * 0.55
            - play_magnitude * 0.10 + exploration_credit,
            4,
        )
        item["exploration_score"] = item["discovery_score"] + random.uniform(-1.4, 1.4)

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
    for item in ranked:
        item["exploration_score"] = round(
            item["discovery_score"] + random.uniform(-1.4, 1.4), 4
        )
    ranked.sort(key=lambda item: item["exploration_score"], reverse=True)

    diversified = []
    artist_counts = {}
    family_counts = {}
    deferred = []
    for item in ranked:
        artist_key = _music_key(item.get("artist", ""))
        families = item.get("genre_families") or ["other"]
        family = next((value for value in families if family_counts.get(value, 0) < 8), families[0])
        if artist_counts.get(artist_key, 0) >= 2 or family_counts.get(family, 0) >= 8:
            deferred.append(item)
            continue
        item["primary_genre_family"] = family
        diversified.append(item)
        artist_counts[artist_key] = artist_counts.get(artist_key, 0) + 1
        family_counts[family] = family_counts.get(family, 0) + 1
        if len(diversified) >= 100:
            break
    if len(diversified) < 100:
        for item in deferred:
            artist_key = _music_key(item.get("artist", ""))
            if artist_counts.get(artist_key, 0) >= 2:
                continue
            diversified.append(item)
            artist_counts[artist_key] = artist_counts.get(artist_key, 0) + 1
            if len(diversified) >= 100:
                break
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
    lock = _CLASSICS_REFRESH_LOCK if list_name == "classics" else _DEEP_DIVE_REFRESH_LOCK
    if not lock.acquire(blocking=False):
        return {"ok": False, "status": "already_running", "list": list_name}
    try:
        if list_name == "classics":
            payload = _build_classics_list()
        elif list_name == "artist_deep_dive":
            payload = _build_artist_deep_dive_list()
        else:
            return {"ok": False, "error": "Unknown discovery list"}
        _discovery_write_list(list_name, payload)
        return {
            "ok": True, "list": list_name, "generated_at": time.time(),
            "items": len(payload.get("items", [])),
        }
    except Exception as exc:
        return {"ok": False, "list": list_name, "error": str(exc)}
    finally:
        lock.release()


_CLASSICS_REFRESH_LOCK = __import__("threading").Lock()
_DEEP_DIVE_REFRESH_LOCK = __import__("threading").Lock()


_DISCOVERY_SETTINGS_DEFAULTS = {
    "music_library_path": str(MUSIC_DIR),
    "slskd_url": "http://192.168.1.12:5030",
    "quality_priority": [
        "mp3_320",
        "mp3_193_319",
        "mp3_192",
        "flac_cd",
    ],
    "auto_acquire_for_me": True,
    "slskd_downloads_path": str(Path(
        os.environ.get("SLSKD_DOWNLOADS_DIR")
        or os.environ.get("SLSKD_DOWNLOADS_MOUNT")
        or str(MUSIC_DIR.parent.parent / "downloads" / "slskd" / "complete")
    ).expanduser()),
}


def _discovery_settings_init():
    with sqlite3.connect(DISCOVERY_DB, timeout=10) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS discovery_settings (
                setting_key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        db.commit()
    # This database now contains an API credential: restrict local file access.
    try:
        os.chmod(DISCOVERY_DB, 0o600)
    except OSError:
        pass


def _discovery_settings_read():
    global MUSIC_DIR
    _discovery_settings_init()
    settings = dict(_DISCOVERY_SETTINGS_DEFAULTS)
    with sqlite3.connect(DISCOVERY_DB, timeout=10) as db:
        rows = db.execute(
            "SELECT setting_key, value_json FROM discovery_settings"
        ).fetchall()
    for key, value in rows:
        try:
            settings[key] = json.loads(value)
        except (ValueError, TypeError):
            continue

    configured_music_path = str(settings.get("music_library_path") or "").strip()
    if configured_music_path:
        candidate_music_path = Path(configured_music_path).expanduser()
        if candidate_music_path.is_absolute():
            MUSIC_DIR = candidate_music_path

    # Migrate the former downloads-root defaults to slskd's actual completed
    # directory when that directory is available on the current host. This
    # also handles a settings DB moved from the Mac development environment
    # to the Debian media LXC without overwriting custom paths.
    saved_path = str(settings.get("slskd_downloads_path") or "")
    legacy_paths = {
        str(MUSIC_DIR.parent.parent / "downloads"),
        "/Volumes/media/downloads",
        "/media/downloads",
    }
    current_default = _DISCOVERY_SETTINGS_DEFAULTS["slskd_downloads_path"]
    if (
        saved_path in legacy_paths
        and saved_path != current_default
        and Path(current_default).is_dir()
    ):
        settings["slskd_downloads_path"] = current_default
        _discovery_settings_write({
            "slskd_downloads_path": current_default,
        })
    return settings


def _discovery_settings_write(values):
    _discovery_settings_init()
    with sqlite3.connect(DISCOVERY_DB, timeout=10) as db:
        for key, value in values.items():
            db.execute(
                "INSERT OR REPLACE INTO discovery_settings "
                "(setting_key, value_json, updated_at) VALUES (?, ?, ?)",
                (key, json.dumps(value, ensure_ascii=False), time.time()),
            )
        db.commit()


# Load persisted directory overrides before any library operation runs.
_discovery_settings_read()


def _slskd_config():
    settings = _discovery_settings_read()
    api_key = settings.get("slskd_api_key", "")
    base_url = str(settings.get("slskd_url") or "").strip().rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("slskd URL must be a valid HTTP or HTTPS URL.")
    if not api_key:
        raise ValueError("Add the slskd API key in Discovery Settings first.")
    return base_url, api_key, settings


@mcp.tool()
def discovery_get_slskd_settings() -> str:
    """Read acquisition settings without returning the stored API key."""
    settings = _discovery_settings_read()
    return json.dumps({
        "music_library_path": settings.get("music_library_path", str(MUSIC_DIR)),
        "slskd_url": settings.get("slskd_url", _DISCOVERY_SETTINGS_DEFAULTS["slskd_url"]),
        "api_key_configured": bool(settings.get("slskd_api_key")),
        "auto_acquire_for_me": bool(settings.get("auto_acquire_for_me", True)),
        "slskd_downloads_path": settings.get(
            "slskd_downloads_path", _DISCOVERY_SETTINGS_DEFAULTS["slskd_downloads_path"]
        ),
        "quality_priority": settings.get(
            "quality_priority", _DISCOVERY_SETTINGS_DEFAULTS["quality_priority"]
        ),
        "quality_labels": {
            "mp3_320": "MP3 320 kbps",
            "mp3_193_319": "MP3 193–319 kbps",
            "mp3_192": "MP3 192 kbps",
            "flac_cd": "FLAC (CD quality preferred; metadata may not verify this)",
        },
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def discovery_set_slskd_settings(
    slskd_url: str = "http://192.168.1.12:5030",
    api_key: str = "",
    quality_priority_json: str = '["mp3_320","mp3_193_319","mp3_192","flac_cd"]',
    auto_acquire_for_me: bool | None = None,
    slskd_downloads_path: str | None = None,
    music_library_path: str | None = None,
) -> str:
    """Save acquisition settings and paths. Blank API key preserves the saved key."""
    from urllib.parse import urlparse
    url = (slskd_url or "").strip().rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return json.dumps({"ok": False, "error": "Enter a valid HTTP or HTTPS slskd URL."})
    try:
        quality = json.loads(quality_priority_json)
    except (ValueError, TypeError):
        return json.dumps({"ok": False, "error": "Quality priority must be valid JSON."})
    allowed = {"mp3_320", "mp3_193_319", "mp3_192", "flac_cd"}
    if not isinstance(quality, list) or len(quality) != 4 or set(quality) != allowed:
        return json.dumps({
            "ok": False,
            "error": "Quality priority must contain each supported tier exactly once.",
        })
    values = {
        "slskd_url": url,
        "quality_priority": quality,
    }
    if music_library_path is not None:
        music_path = str(Path(music_library_path).expanduser())
        if not Path(music_path).is_absolute():
            return json.dumps({
                "ok": False,
                "error": "The music library path must be an absolute path visible to this app.",
            })
        if not Path(music_path).is_dir():
            return json.dumps({
                "ok": False,
                "error": "The music library path must exist and be a directory visible to this app.",
            })
        values["music_library_path"] = music_path
    if auto_acquire_for_me is not None:
        values["auto_acquire_for_me"] = bool(auto_acquire_for_me)
    if slskd_downloads_path is not None:
        download_path = str(Path(slskd_downloads_path).expanduser())
        if not Path(download_path).is_absolute():
            return json.dumps({
                "ok": False,
                "error": "The slskd downloads path must be an absolute path visible to this app.",
            })
        values["slskd_downloads_path"] = download_path
    if api_key.strip():
        values["slskd_api_key"] = api_key.strip()
    _discovery_settings_write(values)
    global MUSIC_DIR
    if music_library_path is not None:
        MUSIC_DIR = Path(values["music_library_path"])
    return json.dumps({
        "ok": True,
        "music_library_path": str(MUSIC_DIR),
        "slskd_url": url,
        "api_key_configured": bool(_discovery_settings_read().get("slskd_api_key")),
        "quality_priority": quality,
        "message": "Settings saved. The API key is never returned by this tool.",
    }, ensure_ascii=False)


@mcp.tool()
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
    import re
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension == "flac":
        tier = "flac_cd"
    elif extension == "mp3":
        bitrate = file_record.get("bitRate") or file_record.get("bitrate")
        try:
            bitrate = int(bitrate)
        except (ValueError, TypeError):
            match = re.search(r"(?<!\d)(320|256|224|192|160|128)\s?kbps", filename, re.I)
            bitrate = int(match.group(1)) if match else 0
        if bitrate >= 320:
            tier = "mp3_320"
        elif 193 <= bitrate <= 319:
            tier = "mp3_193_319"
        elif bitrate == 192:
            tier = "mp3_192"
        else:
            tier = "other"
    else:
        tier = "other"
    return priority.index(tier) if tier in priority else len(priority) + 1, tier


def _discovery_expected_track_count(metadata):
    """Read an expected track count from common recommendation metadata shapes."""
    if not isinstance(metadata, dict):
        return None
    keys = ("track_count", "trackCount", "number_of_tracks", "numberOfTracks",
            "total_tracks", "totalTracks", "tracks_count", "tracksCount", "trackcount")
    queue = [metadata]
    seen = set()
    while queue:
        current = queue.pop(0)
        if not isinstance(current, dict) or id(current) in seen:
            continue
        seen.add(id(current))
        for key in keys:
            value = current.get(key)
            try:
                count = int(value)
                if count > 0:
                    return count
            except (TypeError, ValueError):
                pass
        for key in ("tracks", "tracklist", "track_list", "album", "release", "metadata"):
            value = current.get(key)
            if isinstance(value, list) and value:
                # Track objects are strong evidence; don't mistake unrelated arrays for tracks.
                if all(isinstance(item, dict) for item in value):
                    return len(value)
            elif isinstance(value, dict):
                queue.append(value)
    return None


def _slskd_track_identity(filename):
    """A filename-based track identity that ignores extensions and numeric collision suffixes."""
    import re
    name = str(filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    stem = Path(name).stem.casefold()
    stem = re.sub(r"_\d+$", "", stem)
    return _music_key(stem)


def _slskd_extract_candidates(payload, artist, album, priority, expected_track_count=None):
    import re
    from collections import defaultdict
    audio_exts = {".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".aiff", ".ape"}
    def norm(value):
        return _music_key(str(value or ""))
    groups = defaultdict(list)
    for response in payload if isinstance(payload, list) else []:
        username = response.get("username") or response.get("user") or ""
        speed = response.get("uploadSpeed") or response.get("averageSpeed") or response.get("speed") or 0
        try:
            speed = int(speed)
        except (TypeError, ValueError):
            speed = 0
        files = response.get("files") or response.get("fileList") or []
        for file_record in files if isinstance(files, list) else []:
            filename = str(file_record.get("filename") or file_record.get("path") or "")
            if not filename or "/" not in filename and "\\" not in filename:
                continue
            ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext not in audio_exts:
                continue
            path_parts = re.split(r"[/\\]+", filename)
            path_text = " ".join(path_parts[:-1])
            file_text = path_parts[-1]
            # Require a useful album-level match; filenames alone are weak evidence.
            album_in_path = norm(album) in norm(path_text)
            artist_in_path = norm(artist) in norm(path_text)
            title_match = norm(album) in norm(file_text)
            artist_match = norm(artist) in norm(path_text + " " + file_text)
            if not (album_in_path or title_match):
                continue
            parent = path_parts[-2] if len(path_parts) >= 2 else path_text
            folder_key = (username, parent)
            rank, tier = _slskd_quality_tier(file_record, filename, priority)
            try:
                size = int(file_record.get("size") or 0)
            except (TypeError, ValueError):
                size = 0
            groups[folder_key].append({
                "filename": filename,
                "size": size,
                "quality_tier": tier,
                "quality_rank": rank,
                "upload_speed": speed,
                "artist_match": artist_match or artist_in_path,
                "album_match": album_in_path or title_match,
                "artist_in_path": artist_in_path,
                "album_in_path": album_in_path,
            })
    candidates = []
    for (username, folder), files in groups.items():
        # If the same track is advertised more than once in a folder, retain one
        # copy: highest-priority quality tier, then largest file size as tie-break.
        best_by_track = {}
        for item in files:
            track_key = _slskd_track_identity(item["filename"])
            if not track_key:
                continue
            previous = best_by_track.get(track_key)
            if (previous is None
                    or (item["quality_rank"], -item["size"]) <
                       (previous["quality_rank"], -previous["size"])):
                best_by_track[track_key] = item
        files = list(best_by_track.values())
        tiers = [item["quality_rank"] for item in files if item["quality_rank"] <= len(priority)]
        avg_rank = sum(tiers) / len(tiers) if tiers else len(priority) + 1
        artist_evidence = any(item["artist_match"] or item["artist_in_path"] for item in files)
        album_evidence = any(item["album_match"] for item in files)
        unique_tracks = {
            _slskd_track_identity(item["filename"])
            for item in files
            if _slskd_track_identity(item["filename"])
        }
        unique_track_count = len(unique_tracks)
        # Allow modest search/catalog mismatch: require at least 70% of an expected
        # track count (minimum 3), or 5 unique tracks when catalog count is unknown.
        # This still rejects tiny partial folders without blocking short releases.
        minimum_required = (
            max(3, (int(expected_track_count) * 7 + 9) // 10)
            if expected_track_count else 5
        )
        score = 0.55 * (1.0 if any(x["album_in_path"] for x in files) else 0.65)
        score += 0.25 * (1.0 if any(x["artist_match"] for x in files) else 0.0)
        score += 0.20 * min(unique_track_count / 8.0, 1.0)
        complete_enough = unique_track_count >= minimum_required
        candidates.append({
            "username": username,
            "folder": folder,
            "file_count": len(files),
            "unique_track_count": unique_track_count,
            "expected_track_count": expected_track_count,
            "complete_enough": complete_enough,
            "files": files,
            "average_quality_rank": round(avg_rank, 3),
            "upload_speed": max((x["upload_speed"] for x in files), default=0),
            "confidence": round(score, 3),
            "clear_match": bool(artist_evidence and album_evidence and complete_enough and score >= 0.72),
            "eligibility_reason": (
                "eligible" if artist_evidence and album_evidence and complete_enough and score >= 0.72
                else f"only {unique_track_count} unique tracks; need at least {minimum_required}"
                if not complete_enough else "album/artist match confidence below threshold"
            ),
            "quality_summary": sorted({
                item["quality_tier"] for item in files
            }),
        })
    candidates.sort(key=lambda item: (
        not item["clear_match"],
        item["average_quality_rank"],
        -item["upload_speed"],
        -item["confidence"],
        -item["file_count"],
    ))
    return candidates


def _slskd_download_transfer_files(base_url, headers, username):
    """Return tracked files while preserving their remote-directory identity."""
    from urllib.parse import quote

    response = httpx.get(
        f"{base_url}/api/v0/transfers/downloads/"
        f"{quote(str(username), safe='')}",
        headers=headers,
        timeout=8,
    )
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
    """Wait briefly for a queued candidate to start; cancel a stalled queue before fallback."""
    from urllib.parse import quote
    def normalized_remote_path(value):
        value = str(value or "").replace("\\", "/")
        parts = [part for part in value.split("/") if part not in ("", ".")]
        if any(part == ".." for part in parts):
            return None
        return "/".join(parts).casefold()

    expected = set()
    expected_directories = set()
    for item in candidate.get("files", []):
        filename = str(item.get("filename") or "").replace("\\", "/")
        normalized = normalized_remote_path(filename)
        name = filename.rsplit("/", 1)[-1].casefold()
        if not name or normalized is None or "/" not in normalized:
            return None
        expected.add(name)
        expected_directories.add(normalized.rsplit("/", 1)[0])
    if len(expected_directories) != 1:
        return None
    expected_directory = next(iter(expected_directories))

    deadline = time.monotonic() + timeout
    last_files = []
    while time.monotonic() < deadline:
        try:
            tracked = _slskd_download_transfer_files(
                base_url, headers, candidate["username"]
            )
        except (httpx.HTTPError, ValueError, TypeError):
            return None
        last_files = []
        for item in tracked:
            filename = str(item.get("filename") or "").replace("\\", "/")
            name = filename.rsplit("/", 1)[-1].casefold()
            if name not in expected:
                continue
            directory = item.get("_transfer_directory")
            if directory is None:
                normalized_filename = normalized_remote_path(filename)
                if normalized_filename is None or "/" not in normalized_filename:
                    return None
                directory = normalized_filename.rsplit("/", 1)[0]
            normalized_directory = normalized_remote_path(directory)
            if normalized_directory is None:
                return None
            if normalized_directory == expected_directory:
                last_files.append(item)
        states = {str(item.get("state") or "").replace("_", "").casefold() for item in last_files}
        if states.intersection({"inprogress", "succeeded", "completed", "transferring", "downloading"}):
            return True
        if states and states.issubset({"failed", "errored", "cancelled", "canceled"}):
            return False
        time.sleep(1)
    if not last_files:
        return False
    queued = [
        item for item in last_files
        if str(item.get("state") or "").replace("_", "").casefold() in {"queued", "initializing", "requested"}
    ]
    if not queued:
        return None
    # Do not start another source while the first one's files remain queued.
    # A failed cancellation is treated as uncertain rather than risking duplicate downloads.
    for item in queued:
        file_id = str(item.get("id") or item.get("filename") or "")
        if not file_id:
            return None
        try:
            cancelled = httpx.delete(
                f"{base_url}/api/v0/transfers/downloads/{quote(str(candidate['username']), safe='')}/{quote(file_id, safe='')}",
                headers=headers,
                timeout=6,
            )
            if cancelled.status_code not in (200, 202, 204, 404):
                return None
        except httpx.HTTPError:
            return None
    return False


def _discovery_safe_folder_name(value):
    value = str(value or "").replace("\\", "/").split("/")[-1]
    value = "".join(character for character in value if character not in "\\0")
    value = value.strip().strip(".")
    return value or "Unknown"


_DISCOVERY_IMPORT_LOCK = __import__("threading").Lock()
# Serializes dismissal against the final import transition. Held only while
# committing the local import/dismiss state, never during the download.
_DISCOVERY_IMPORT_TRANSITION_LOCK = __import__("threading").RLock()
_DISCOVERY_IMPORT_ACTIVE = set()
_DISCOVERY_ACQUIRE_ACTIVE = set()


def _discovery_save_acquisition_job(artist, album, status, details=None,
                                    candidate=None, settings=None):
    """Persist acquisition state independently of discovery recommendation lists."""
    _discovery_init()
    now = time.time()
    artist_key, album_key = _music_key(artist), _music_key(album)
    if not artist_key or not album_key:
        raise ValueError("artist and album are required")
    with sqlite3.connect(DISCOVERY_DB, timeout=10) as db:
        if not (details or {}).get("quality_summary"):
            previous = db.execute(
                "SELECT details_json FROM discovery_acquisitions "
                "WHERE artist_key=? AND album_key=?",
                (artist_key, album_key),
            ).fetchone()
            if previous:
                try:
                    previous_details = json.loads(previous[0] or "{}")
                except (ValueError, TypeError):
                    previous_details = {}
                previous_quality = previous_details.get("quality_summary")
                if previous_quality:
                    details = {**(details or {}), "quality_summary": previous_quality}
        db.execute(
            "INSERT INTO discovery_acquisitions "
            "(artist_key, album_key, artist, album, status, details_json, candidate_json, "
            "settings_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(artist_key, album_key) DO UPDATE SET "
            "artist=excluded.artist, album=excluded.album, status=excluded.status, "
            "details_json=excluded.details_json, "
            "candidate_json=CASE WHEN excluded.candidate_json='{}' THEN discovery_acquisitions.candidate_json ELSE excluded.candidate_json END, "
            "settings_json=CASE WHEN excluded.settings_json='{}' THEN discovery_acquisitions.settings_json ELSE excluded.settings_json END, "
            "updated_at=excluded.updated_at",
            (artist_key, album_key, artist.strip(), album.strip(), status,
             json.dumps({"status": status, "updated_at": now, **(details or {})}, ensure_ascii=False),
             json.dumps(candidate or {}, ensure_ascii=False),
             json.dumps(settings or {}, ensure_ascii=False), now, now),
        )
        db.commit()


def _discovery_update_acquisition_status(artist, album, status, details=None):
    """Persist acquisition state and mirror it to For Me without racing dismissal."""
    details = details or {}
    try:
        with _DISCOVERY_IMPORT_TRANSITION_LOCK:
            if status != "dismissed" and _discovery_is_dismissed(artist, album):
                return
            _discovery_save_acquisition_job(artist, album, status, details)

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
        # Acquisition state remains best-effort, as before; an unavailable
        # feedback store must not crash the download watcher.
        pass


def _discovery_list_acquisition_jobs():
    _discovery_init()
    with sqlite3.connect(DISCOVERY_DB, timeout=10) as db:
        rows = db.execute(
            "SELECT artist_key, album_key, artist, album, status, details_json, "
            "candidate_json, settings_json, created_at, updated_at "
            "FROM discovery_acquisitions ORDER BY updated_at DESC"
        ).fetchall()
    jobs = []
    for row in rows:
        try:
            details = json.loads(row[5] or "{}")
        except (ValueError, TypeError):
            details = {"status": row[4]}
        try:
            candidate = json.loads(row[6] or "{}")
        except (ValueError, TypeError):
            candidate = {}
        try:
            settings = json.loads(row[7] or "{}")
        except (ValueError, TypeError):
            settings = {}
        jobs.append({
            "artist_key": row[0], "album_key": row[1], "artist": row[2],
            "album": row[3], "status": row[4], "details": details,
            "candidate": candidate, "settings": settings,
            "created_at": row[8], "updated_at": row[9],
        })
    return jobs


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
    resumable = {
        "downloading", "download_complete_waiting_for_folder", "monitor_error",
        "importing",
    }
    for job in jobs:
        if job["status"] == "dismissed":
            continue
        identity = (job["artist_key"], job["album_key"])
        candidate, settings = job["candidate"], job["settings"]
        if job["status"] not in resumable or not candidate.get("files") or not candidate.get("username"):
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


def _discovery_match_completed_album_files(folder, candidate):
    """Match each unique expected basename to a local file.

    Collision-suffixed filenames are accepted only when their numeric suffix
    and advertised file size establish a unique match.
    """
    import re

    folder = Path(folder)
    files = [p for p in folder.iterdir() if p.is_file() and not p.is_symlink()]
    used = set()
    matched = {}

    expected_by_name = {}
    for item in candidate.get("files", []):
        name = str(item.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1]
        if not name:
            continue
        key = name.casefold()
        size = max(0, int(item.get("size") or 0))

        # Identical basenames with conflicting advertised sizes are ambiguous.
        if key in expected_by_name and expected_by_name[key][1] != size:
            return None
        expected_by_name.setdefault(key, (name, size))

    for key, (expected_name, expected_size) in expected_by_name.items():
        exact = [
            p for p in files
            if p.name.casefold() == key
            and p not in used
            and (expected_size <= 0 or p.stat().st_size == expected_size)
        ]
        selected = exact[0] if len(exact) == 1 else None

        if selected is None and expected_size > 0:
            stem, suffix = Path(expected_name).stem, Path(expected_name).suffix
            pattern = re.compile(
                r"^" + re.escape(stem) + r"_\d+" + re.escape(suffix) + r"$",
                re.IGNORECASE,
            )
            alternatives = [
                p for p in files
                if p not in used
                and pattern.match(p.name)
                and p.stat().st_size == expected_size
            ]
            if len(alternatives) == 1:
                selected = alternatives[0]

        if selected is None:
            return None

        matched[expected_name] = selected
        used.add(selected)

    return matched or None

def _discovery_locate_completed_album(download_root, candidate):
    """Find a unique completed folder whose expected tracks match names and sizes.

    slskd may append a numeric suffix to a filename to avoid collisions. Such
    files are accepted only when both the original basename and expected size
    match, and the caller imports only the matched files—not the whole folder.
    """
    import os

    root = Path(download_root).expanduser()
    if not root.is_dir():
        return None

    wanted_folder = _discovery_safe_folder_name(candidate.get("folder"))
    matches = []
    for current, directories, _filenames in os.walk(root, followlinks=False):
        directories[:] = [name for name in directories if not name.startswith(".")]
        current_path = Path(current)
        # Never treat the completed-download root itself as an album folder:
        # moving it would move every completed download into the music library.
        if current_path.resolve() == root.resolve():
            continue
        try:
            matched_files = _discovery_match_completed_album_files(current_path, candidate)
        except OSError:
            matched_files = None
        if matched_files:
            matches.append(current_path)

    if not matches:
        return None

    named_matches = [
        path for path in matches
        if path.name.casefold() == str(wanted_folder or "").casefold()
    ]
    # Matching track names and sizes do not prove source-folder ownership.
    # If the expected folder name is absent or ambiguous, refuse to import.
    if len(named_matches) == 1:
        return named_matches[0]
    return None


def _discovery_import_matched_album_files(source, destination, candidate):
    """Stage only the verified expected tracks, leaving unrelated files behind."""
    import shutil
    import uuid

    matched = _discovery_match_completed_album_files(source, candidate)
    if not matched:
        raise OSError("Expected tracks no longer match files in the completed folder")

    destination = Path(destination)
    parent = destination.parent

    # Refuse existing destinations, including broken symlinks, before
    # creating any staging directory.
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(str(destination))
    if parent.is_symlink() or not parent.is_dir():
        raise OSError("Import destination parent is not a real directory")

    staging = parent / (".navidrome-import-" + uuid.uuid4().hex)
    staging.mkdir(parents=True, exist_ok=False)
    moved = []
    try:
        for expected_name, actual_path in matched.items():
            staged_path = staging / expected_name
            shutil.move(str(actual_path), str(staged_path))
            moved.append((staged_path, actual_path))
        # Destination should not exist; rename the complete staged album into place.
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(str(destination))
        staging.rename(destination)
    except Exception:
        for staged_path, original_path in reversed(moved):
            if staged_path.exists() and not original_path.exists():
                try:
                    shutil.move(str(staged_path), str(original_path))
                except OSError:
                    pass
        try:
            staging.rmdir()
        except OSError:
            pass
        raise
def _discovery_is_dismissed(artist, album):
    return any(
        job["artist_key"] == _music_key(artist)
        and job["album_key"] == _music_key(album)
        and job["status"] == "dismissed"
        for job in _discovery_list_acquisition_jobs()
    )


def discovery_dismiss_acquisition(artist, album):
    """Dismiss an acquisition card and stop its import watcher without deleting downloaded files."""
    _discovery_init()
    identity = (_music_key(artist), _music_key(album))
    with _DISCOVERY_IMPORT_TRANSITION_LOCK:
        with sqlite3.connect(DISCOVERY_DB, timeout=10) as db:
            row = db.execute(
                "SELECT status, details_json FROM discovery_acquisitions "
                "WHERE artist_key=? AND album_key=?",
                identity,
            ).fetchone()
            if not row:
                return json.dumps({"ok": False, "error": "Acquisition not found."})
            if row[0] in {"importing", "imported"}:
                return json.dumps({
                    "ok": False,
                    "error": "The album is already being imported or has been imported; it cannot be dismissed now.",
                })
            try:
                details = json.loads(row[1] or "{}")
            except (ValueError, TypeError):
                details = {}
            details.update({"status": "dismissed", "dismissed_at": time.time()})
            db.execute(
                "UPDATE discovery_acquisitions SET status='dismissed', details_json=?, updated_at=? "
                "WHERE artist_key=? AND album_key=?",
                (json.dumps(details, ensure_ascii=False), time.time(), *identity),
            )
            db.commit()
    return json.dumps({"ok": True, "status": "dismissed", "message": "Acquisition card dismissed. Existing download files were left untouched."})


def _discovery_skip_requested(artist, album):
    for job in _discovery_list_acquisition_jobs():
        if job["artist_key"] == _music_key(artist) and job["album_key"] == _music_key(album):
            return bool((job.get("details") or {}).get("skip_requested"))
    return False


def discovery_skip_acquisition_source(artist, album):
    """Request a safe switch to the next eligible source for a stalled acquisition."""
    _discovery_init()
    # Keep the status check and skip request atomic with dismissal in this process.
    with _DISCOVERY_IMPORT_TRANSITION_LOCK:
        identity = (_music_key(artist), _music_key(album))
        with sqlite3.connect(DISCOVERY_DB, timeout=10) as db:
            row = db.execute(
                "SELECT status, details_json, candidate_json FROM discovery_acquisitions "
                "WHERE artist_key=? AND album_key=?", identity,
            ).fetchone()
            if not row:
                return json.dumps({"ok": False, "error": "Acquisition not found."})
            if row[0] == "dismissed":
                return json.dumps({"ok": False, "error": "This acquisition has been dismissed."})
            if row[0] != "downloading":
                return json.dumps({"ok": False, "error": "This acquisition is not downloading."})
            try:
                candidate = json.loads(row[2] or "{}")
                details = json.loads(row[1] or "{}")
            except (ValueError, TypeError):
                candidate, details = {}, {}
            if not candidate.get("fallback_candidates"):
                return json.dumps({"ok": False, "error": "No eligible fallback source remains."})
            details["skip_requested"] = True
            details["skip_requested_at"] = time.time()
            cursor = db.execute(
                "UPDATE discovery_acquisitions SET details_json=?, updated_at=? "
                "WHERE artist_key=? AND album_key=? AND status='downloading'",
                (json.dumps(details, ensure_ascii=False), time.time(), *identity),
            )
            if cursor.rowcount != 1:
                return json.dumps({"ok": False, "error": "Acquisition state changed; please refresh and try again."})
            db.commit()
    return json.dumps({"ok": True, "status": "skip_requested", "message": "Switch requested; cancelling the current source before starting the next one."})


def _discovery_cancel_and_clean_source(
    download_root, candidate, base_url, headers
):
    """
    Cancel only transfers belonging to the exact remote album directory.

    Preflight every local file before changing anything. Refuse cleanup if
    source identity or local file ownership is ambiguous.
    """
    import re
    from urllib.parse import quote

    def normalized_path(value):
        """Normalize separators without treating different paths as equal."""
        value = str(value or "").replace("\\", "/")
        parts = [part for part in value.split("/") if part not in ("", ".")]

        if any(part == ".." for part in parts):
            return None

        return "/".join(parts).casefold()

    def basename(value):
        return str(value or "").replace("\\", "/").rsplit("/", 1)[-1]

    username = str(candidate.get("username") or "")
    files = candidate.get("files") or []

    if not username or not files:
        return False

    # Build an unambiguous expected-track inventory.
    expected_by_name = {}
    remote_directories = set()

    for item in files:
        filename = str(item.get("filename") or "")
        name = basename(filename)

        try:
            size = int(item.get("size"))
        except (TypeError, ValueError):
            return False

        # A missing or invalid advertised size makes safe cleanup impossible.
        if not name or size <= 0:
            return False

        remote_path = normalized_path(filename)
        if remote_path is None or "/" not in remote_path:
            return False

        remote_directory = remote_path.rsplit("/", 1)[0]
        remote_directories.add(remote_directory)

        key = name.casefold()

        # Duplicate basenames make local file ownership ambiguous.
        if key in expected_by_name:
            return False

        expected_by_name[key] = {
            "name": name,
            "size": size,
        }

    # Every advertised track must belong to one identifiable remote directory.
    if len(remote_directories) != 1:
        return False

    expected_remote_directory = next(iter(remote_directories))

    # Reject a symlink at the configured path before resolving it.
    try:
        original_root = Path(download_root).expanduser()
        if original_root.is_symlink():
            return False
        root = original_root.resolve(strict=True)
    except (OSError, RuntimeError):
        return False

    if not root.is_dir():
        return False

    wanted = _discovery_safe_folder_name(candidate.get("folder"))
    if not wanted:
        return False

    direct = root / wanted

    # Do not follow a symlink, even if it points inside the download root.
    if direct.is_symlink():
        return False

    if direct.is_dir():
        targets = [direct]
    elif direct.exists():
        # A file or other object with the expected folder name is ambiguous.
        return False
    else:
        try:
            targets = [
                path
                for path in root.rglob(wanted)
                if path.name == wanted
                and path.is_dir()
                and not path.is_symlink()
            ]
        except OSError:
            return False

    # Never guess which of multiple same-named folders belongs to this job.
    if len(targets) > 1:
        return False

    target = targets[0] if targets else None

    planned_deletions = []

    # Preflight the entire local folder. Nothing has been cancelled or
    # deleted yet. Any unexpected entry aborts cleanup.
    if target is not None:
        try:
            resolved_target = target.resolve(strict=True)

            if (
                resolved_target == root
                or root not in resolved_target.parents
                or target.is_symlink()
            ):
                return False

            for actual in target.iterdir():
                # Never follow symlinks, recurse into directories, or remove
                # special files.
                if actual.is_symlink() or not actual.is_file():
                    return False

                actual_name = actual.name
                key = actual_name.casefold()

                expected = expected_by_name.get(key)

                try:
                    actual_size = actual.stat(follow_symlinks=False).st_size
                except OSError:
                    return False

                if expected is not None:
                    # Exact-name tracks may be incomplete downloads, but
                    # must not exceed their advertised size.
                    if actual_size > expected["size"]:
                        return False

                    planned_deletions.append(actual)
                    continue

                # Collision-suffixed files are identifiable only when
                # exactly one expected track matches and the size is exact.
                collision_matches = []

                for expected_item in expected_by_name.values():
                    expected_name = expected_item["name"]
                    expected_size = expected_item["size"]

                    stem = Path(expected_name).stem
                    suffix = Path(expected_name).suffix

                    pattern = re.compile(
                        r"^"
                        + re.escape(stem)
                        + r"_\d+"
                        + re.escape(suffix)
                        + r"$",
                        re.IGNORECASE,
                    )

                    if (
                        pattern.fullmatch(actual_name)
                        and actual_size == expected_size
                    ):
                        collision_matches.append(expected_item)

                if len(collision_matches) != 1:
                    # An unrelated or ambiguous file means we cannot
                    # safely claim that cleanup is complete.
                    return False

                planned_deletions.append(actual)

        except (OSError, RuntimeError):
            return False

    # Inspect the peer's current transfers. Do not cancel by basename alone.
    try:
        tracked = _slskd_download_transfer_files(
            base_url, headers, username
        )
    except Exception:
        return False

    active_states = {
        "queued",
        "initializing",
        "requested",
        "inprogress",
        "transferring",
        "downloading",
    }

    transfers_to_cancel = []

    for item in tracked:
        name = basename(item.get("filename"))
        expected = expected_by_name.get(name.casefold())

        if expected is None:
            continue

        state = (
            str(item.get("state") or "")
            .replace("_", "")
            .casefold()
        )

        if state not in active_states:
            continue

        # A tracked file's directory must be explicit. If it is missing,
        # derive it only from a full remote filename.
        tracked_directory = item.get("_transfer_directory")

        if tracked_directory is None:
            tracked_filename = str(item.get("filename") or "")
            normalized_filename = normalized_path(tracked_filename)

            if normalized_filename is None or "/" not in normalized_filename:
                return False

            tracked_directory = normalized_filename.rsplit("/", 1)[0]

        normalized_tracked_directory = normalized_path(tracked_directory)

        if normalized_tracked_directory is None:
            return False

        # A known, different directory belongs to a different remote file:
        # leave it alone.
        if normalized_tracked_directory != expected_remote_directory:
            continue

        # For the matching remote directory, require an identifiable
        # transfer ID and consistent advertised size.
        try:
            tracked_size = int(item.get("size"))
        except (TypeError, ValueError):
            return False

        if tracked_size != expected["size"]:
            return False

        file_id = str(item.get("id") or "")
        if not file_id:
            return False

        transfers_to_cancel.append((file_id, name.casefold()))

    # All checks above are read-only. Only now begin cancelling transfers.
    for file_id, _name in transfers_to_cancel:
        try:
            response = httpx.delete(
                f"{base_url}/api/v0/transfers/downloads/"
                f"{quote(username, safe='')}/"
                f"{quote(file_id, safe='')}",
                headers=headers,
                timeout=8,
            )

            if response.status_code not in (200, 202, 204, 404):
                return False

        except httpx.HTTPError:
            return False

    # Verify that no active transfer remains for this exact source directory.
    try:
        remaining = _slskd_download_transfer_files(
            base_url, headers, username
        )
    except Exception:
        return False

    for item in remaining:
        name = basename(item.get("filename"))
        expected = expected_by_name.get(name.casefold())

        if expected is None:
            continue

        state = (
            str(item.get("state") or "")
            .replace("_", "")
            .casefold()
        )

        if state not in active_states:
            continue

        directory = item.get("_transfer_directory")

        if directory is None:
            normalized_filename = normalized_path(item.get("filename"))

            if normalized_filename is None or "/" not in normalized_filename:
                return False

            directory = normalized_filename.rsplit("/", 1)[0]

        normalized_directory = normalized_path(directory)

        if normalized_directory is None:
            return False

        if normalized_directory == expected_remote_directory:
            # Cancellation is not confirmed; do not delete local files.
            return False

    # Transfers are now confirmed stopped. Remove only the preflighted files.
    try:
        for path in planned_deletions:
            if path.is_symlink() or not path.is_file():
                return False

            path.unlink()

        # Remove the folder only if it is now empty.
        # Never recursively delete a directory.
        if target is not None:
            try:
                target.rmdir()
            except OSError:
                # Do not report success if anything appeared or remained.
                return False

    except OSError:
        return False

    return True
    return True

def _discovery_switch_to_next_source(artist, album, candidate, settings, download_root, headers, reason):
    """Serialize fallback switching against dismissal so no source is queued afterward."""
    with _DISCOVERY_IMPORT_TRANSITION_LOCK:
        if _discovery_is_dismissed(artist, album):
            return None
        return _discovery_switch_to_next_source_locked(
            artist, album, candidate, settings, download_root, headers, reason
        )


def _discovery_switch_to_next_source_locked(artist, album, candidate, settings, download_root, headers, reason):
    """Switch only among prevalidated complete candidates, cleaning the previous album folder first."""
    base_url, _, _ = _slskd_config()
    fallbacks = list(candidate.get("fallback_candidates") or [])
    if not fallbacks:
        _discovery_update_acquisition_status(artist, album, "download_stalled_no_fallback", {
            "source_username": candidate.get("username"),
            "reason": reason,
            "message": "No other complete eligible source is available.",
        })
        return None
    if not _discovery_cancel_and_clean_source(download_root, candidate, base_url, headers):
        _discovery_update_acquisition_status(artist, album, "source_switch_failed", {
            "source_username": candidate.get("username"),
            "reason": reason,
            "error": "Could not safely cancel transfers or clean the previous album folder.",
        })
        return None
    for index, next_candidate in enumerate(fallbacks):
        files = [
            {"filename": item.get("filename"), "size": int(item.get("size") or 0)}
            for item in next_candidate.get("files", [])
            if item.get("filename")
        ]
        if not files or not next_candidate.get("username"):
            continue
        try:
            response = httpx.post(
                f"{base_url}/api/v0/transfers/downloads/{next_candidate['username']}",
                headers=headers, json=files, timeout=12,
            )
            response.raise_for_status()
        except (httpx.HTTPError, ValueError, TypeError):
            continue
        monitor_candidate = dict(next_candidate)
        monitor_candidate["files"] = files
        monitor_candidate["fallback_candidates"] = fallbacks[index + 1:]
        start_state = _slskd_candidate_start_state(base_url, headers, monitor_candidate, timeout=8)
        if start_state is not True:
            if start_state is None:
                # The new source may be active. Persist it and keep monitoring rather
                # than queueing another peer or abandoning a possibly live transfer.
                monitor_candidate["fallback_candidates"] = fallbacks[index + 1:]
                details = {
                    "source_username": next_candidate.get("username"),
                    "folder": next_candidate.get("folder"),
                    "file_count": len(files),
                    "quality_summary": list(next_candidate.get("quality_summary") or []),
                    "downloads_path": str(download_root),
                    "previous_source_username": candidate.get("username"),
                    "source_switch_reason": reason,
                    "message": "The next source was queued but its start could not be confirmed; monitoring it to avoid duplicate downloads.",
                }
                _discovery_save_acquisition_job(artist, album, "downloading", details,
                                                candidate=monitor_candidate, settings=settings)
                return monitor_candidate
            if not _discovery_cancel_and_clean_source(
                download_root, monitor_candidate, base_url, headers
            ):
                _discovery_update_acquisition_status(artist, album, "source_switch_failed", {
                    "source_username": next_candidate.get("username"),
                    "reason": reason,
                    "error": (
                        "Fallback source did not start and its transfers/files "
                        "could not be safely cancelled and cleaned. No further "
                        "source will be queued."
                    ),
                })
                return None
            continue
        previous_details = next(
            (job.get("details") or {} for job in _discovery_list_acquisition_jobs()
             if job["artist_key"] == _music_key(artist) and job["album_key"] == _music_key(album)),
            {},
        )
        details = {
            "source_username": next_candidate.get("username"),
            "folder": next_candidate.get("folder"),
            "file_count": len(files),
            "unique_track_count": next_candidate.get("unique_track_count"),
            "expected_track_count": next_candidate.get("expected_track_count"),
            "quality_summary": list(next_candidate.get("quality_summary") or []),
            "downloads_path": str(download_root),
            "source_switches": int(previous_details.get("source_switches") or 0) + 1,
            "previous_source_username": candidate.get("username"),
            "source_switch_reason": reason,
            "message": "Previous source stalled; switched to the next complete eligible source.",
        }
        _discovery_save_acquisition_job(artist, album, "downloading", details,
                                        candidate=monitor_candidate, settings=settings)
        return monitor_candidate
    _discovery_update_acquisition_status(artist, album, "download_stalled_no_fallback", {
        "source_username": candidate.get("username"),
        "reason": reason,
        "message": "Every remaining eligible source failed to start.",
    })
    return None


def _discovery_import_completed_source(artist, album, source, music_root, candidate):
    """Import a verified source only if dismissal has not won the race."""
    with _DISCOVERY_IMPORT_TRANSITION_LOCK:
        if _discovery_is_dismissed(artist, album):
            return "dismissed"

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

        _discovery_update_acquisition_status(artist, album, "importing", {
            "source_folder": str(source), "destination": str(album_dir)
        })
        try:
            artist_dir.mkdir(parents=True, exist_ok=True)

            # Revalidate immediately before creating staging files.
            if artist_dir.is_symlink() or not artist_dir.is_dir():
                raise OSError("Artist destination is not a real directory")

            resolved_artist = artist_dir.resolve(strict=True)
            if resolved_artist.parent != music_root:
                raise OSError("Artist destination resolves outside the music root")

            if album_dir.exists() or album_dir.is_symlink():
                raise FileExistsError(str(album_dir))

            _discovery_import_matched_album_files(source, album_dir, candidate)
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


def _discovery_watch_and_import_album(artist, album, candidate, settings):
    """Import once all expected files exist with matching sizes, even if slskd prunes transfer records."""
    import shutil
    base_url, api_key, _ = _slskd_config()
    headers = {"X-API-KEY": api_key}
    download_root = Path(str(
        settings.get("slskd_downloads_path")
        or _DISCOVERY_SETTINGS_DEFAULTS["slskd_downloads_path"]
    )).expanduser()
    music_root = MUSIC_DIR.expanduser()
    expected = {
        str(item.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1].casefold()
        for item in candidate.get("files", [])
    }
    expected_sizes = {
        str(item.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1].casefold():
            max(0, int(item.get("size") or 0))
        for item in candidate.get("files", [])
        if str(item.get("filename") or "").strip()
    }
    deadline = time.monotonic() + 48 * 60 * 60
    completed_at = None
    last_progress_at = time.monotonic()
    last_progress_bytes = 0
    stall_detected_at = None
    source_switches = 0
    while time.monotonic() < deadline:
        try:
            if _discovery_is_dismissed(artist, album):
                return
            if _discovery_skip_requested(artist, album):
                next_candidate = _discovery_switch_to_next_source(
                    artist, album, candidate, settings, download_root, headers, "manual_skip"
                )
                if next_candidate is None:
                    return
                candidate = next_candidate
                expected = {
                    str(item.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1].casefold()
                    for item in candidate.get("files", [])
                }
                expected_sizes = {
                    str(item.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1].casefold():
                        max(0, int(item.get("size") or 0))
                    for item in candidate.get("files", [])
                    if str(item.get("filename") or "").strip()
                }
                last_progress_at = time.monotonic()
                last_progress_bytes = 0
                stall_detected_at = None
                completed_at = None
                source_switches += 1
                continue
            # Filesystem completion is authoritative: slskd may prune successful
            # transfer records before this watcher polls them again.
            source = _discovery_locate_completed_album(download_root, candidate)
            if source is not None:
                result = _discovery_import_completed_source(
                    artist, album, source, music_root, candidate
                )
                if result in {"dismissed", "failed", "imported"}:
                    return

            tracked = _slskd_download_transfer_files(
                base_url, headers, candidate["username"]
            )
            matching_by_name = {}
            for item in tracked:
                name = str(item.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1].casefold()
                if name not in expected:
                    continue
                previous = matching_by_name.get(name)
                state = str(item.get("state") or "").replace("_", "").casefold()
                previous_state = str((previous or {}).get("state") or "").replace("_", "").casefold()
                if previous is None or (
                    state in {"succeeded", "completed"}
                    and previous_state not in {"succeeded", "completed"}
                ):
                    matching_by_name[name] = item

            states = {
                str(item.get("state") or "").replace("_", "").casefold()
                for item in matching_by_name.values()
            }
            current_bytes = 0
            for item in matching_by_name.values():
                for key in ("bytesTransferred", "bytesDownloaded", "downloadedBytes", "transferredBytes"):
                    try:
                        if item.get(key) is not None:
                            current_bytes += max(0, int(item[key]))
                            break
                    except (TypeError, ValueError):
                        pass
            now_mono = time.monotonic()
            if current_bytes > last_progress_bytes:
                last_progress_bytes = current_bytes
                last_progress_at = now_mono
                stall_detected_at = None
            stalled_for = now_mono - last_progress_at
            if (stalled_for >= 120 and candidate.get("fallback_candidates")
                    and not (states and states.issubset({"succeeded", "completed"}))):
                if stall_detected_at is None:
                    stall_detected_at = time.time()
                    _discovery_update_acquisition_status(artist, album, "downloading", {
                        "source_username": candidate.get("username"),
                        "folder": candidate.get("folder"),
                        "quality_summary": list(candidate.get("quality_summary") or []),
                        "zero_progress_seconds": int(stalled_for),
                        "stall_detected_at": stall_detected_at,
                        "skip_countdown_seconds": 15,
                        "fallback_count": len(candidate.get("fallback_candidates") or []),
                        "source_switches": source_switches,
                        "message": "No download progress for 2 minutes. Switching automatically in 15 seconds unless skipped manually.",
                    })
                skip_requested = _discovery_skip_requested(artist, album)
                if skip_requested or time.time() - stall_detected_at >= 15:
                    next_candidate = _discovery_switch_to_next_source(
                        artist, album, candidate, settings, download_root, headers,
                        "manual_skip" if skip_requested else "zero_progress_timeout",
                    )
                    if next_candidate is None:
                        return
                    candidate = next_candidate
                    expected = {
                        str(item.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1].casefold()
                        for item in candidate.get("files", [])
                    }
                    expected_sizes = {
                        str(item.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1].casefold():
                            max(0, int(item.get("size") or 0))
                        for item in candidate.get("files", [])
                        if str(item.get("filename") or "").strip()
                    }
                    last_progress_at = time.monotonic()
                    last_progress_bytes = 0
                    stall_detected_at = None
                    completed_at = None
                    source_switches += 1
                    continue
            if states.intersection({"failed", "errored", "cancelled", "canceled"}):
                _discovery_update_acquisition_status(artist, album, "download_failed", {
                    "source_username": candidate["username"], "states": sorted(states)
                })
                return

            # Byte counters can reach the advertised file sizes before slskd
            # switches transfers to succeeded/completed. Use them as completion
            # evidence too, while still requiring the files on disk before import.
            all_transfers_complete = bool(expected) and all(
                name in matching_by_name and (
                    str(matching_by_name[name].get("state") or "").replace("_", "").casefold()
                    in {"succeeded", "completed"}
                    or (
                        expected_sizes.get(name, 0) > 0
                        and any(
                            matching_by_name[name].get(key) is not None
                            and str(matching_by_name[name][key]).isdigit()
                            and int(matching_by_name[name][key]) >= expected_sizes[name]
                            for key in ("bytesTransferred", "bytesDownloaded", "downloadedBytes", "transferredBytes")
                        )
                    )
                )
                for name in expected
            )
            if all_transfers_complete:
                completed_at = completed_at or time.monotonic()
                source = _discovery_locate_completed_album(download_root, candidate)
                if source is None:
                    _discovery_update_acquisition_status(artist, album, "download_complete_waiting_for_folder", {
                        "source_username": candidate["username"],
                        "downloads_path": str(download_root),
                        "downloads_path_available": download_root.is_dir(),
                        "expected_folder": candidate.get("folder"),
                        "expected_files": len(expected),
                        "matched_transfer_records": len(matching_by_name),
                        "transfer_states": sorted(states),
                        "completion_evidence": "transfer byte counters or terminal states",
                    })
                else:
                    result = _discovery_import_completed_source(
                        artist, album, source, music_root, candidate
                    )
                    if result in {"dismissed", "failed", "imported"}:
                        return
                # Keep looking for the local SMB/NFS-visible folder for up to six hours.
                if time.monotonic() - completed_at > 6 * 60 * 60:
                    _discovery_update_acquisition_status(artist, album, "download_complete_move_failed", {
                        "downloads_path": str(download_root),
                        "folder": candidate.get("folder"),
                    })
                    return
        except Exception as exc:
            _discovery_update_acquisition_status(artist, album, "monitor_error", {
                "error": type(exc).__name__
            })
        time.sleep(2)
    _discovery_update_acquisition_status(artist, album, "monitor_timeout", {
        "source_username": candidate["username"]
    })


def _discovery_start_import_watcher(artist, album, candidate, settings):
    import threading
    identity = (_music_key(artist), _music_key(album))
    details = {
        "source_username": candidate.get("username"),
        "folder": candidate.get("folder"),
        "file_count": len(candidate.get("files") or []),
        "quality_summary": list(candidate.get("quality_summary") or []),
        "downloads_path": settings.get("slskd_downloads_path"),
    }
    safe_settings = {
        key: value for key, value in (settings or {}).items()
        if key not in {"slskd_api_key", "api_key"}
    }
    # Reserve the watcher before writing status so duplicate starts cannot
    # overwrite an existing job's state. Serialize reservation against dismissal.
    with _DISCOVERY_IMPORT_TRANSITION_LOCK:
        if _discovery_is_dismissed(artist, album):
            return
        with _DISCOVERY_IMPORT_LOCK:
            if identity in _DISCOVERY_IMPORT_ACTIVE:
                return
            _DISCOVERY_IMPORT_ACTIVE.add(identity)
        try:
            _discovery_save_acquisition_job(
                artist, album, "downloading", details,
                candidate=candidate, settings=safe_settings,
            )
            _discovery_update_acquisition_status(artist, album, "downloading", details)
        except Exception:
            with _DISCOVERY_IMPORT_LOCK:
                _DISCOVERY_IMPORT_ACTIVE.discard(identity)
            raise
    watcher = threading.Thread(
        target=_discovery_import_watcher_entry,
        args=(artist, album, dict(candidate), dict(settings), identity),
        name="navidrome-import-" + hashlib.sha1(
            (_music_key(artist) + "|" + _music_key(album)).encode("utf-8")
        ).hexdigest()[:10],
        daemon=True,
    )
    try:
        watcher.start()
    except Exception as exc:
        with _DISCOVERY_IMPORT_LOCK:
            _DISCOVERY_IMPORT_ACTIVE.discard(identity)
        _discovery_update_acquisition_status(artist, album, "monitor_error", {
            "error": type(exc).__name__,
            "message": "Could not start the acquisition watcher.",
        })
        return


def _discovery_queue_candidate_unless_dismissed(
    artist, album, base_url, headers, username, selected_files
):
    """Queue a source atomically with dismissal in this process."""
    with _DISCOVERY_IMPORT_TRANSITION_LOCK:
        if _discovery_is_dismissed(artist, album):
            return None
        response = httpx.post(
            f"{base_url}/api/v0/transfers/downloads/{username}",
            headers=headers,
            json=selected_files,
            timeout=12,
        )
        response.raise_for_status()
        return response


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
    search_id = str(uuid.uuid4())
    try:
        response = httpx.post(
            base_url + "/api/v0/searches",
            headers=headers,
            json={
                "id": search_id,
                "searchText": f"{artist} {album}",
                "fileLimit": 1000,
                "filterResponses": True,
                "maximumPeerQueueLength": 100,
                "minimumResponseFileCount": 1,
                "minimumPeerUploadSpeed": 0,
                "responseLimit": 100,
                "searchTimeout": 15000,
            },
            timeout=10,
        )
        response.raise_for_status()
        deadline = time.monotonic() + 18
        payload_by_peer = {}
        while time.monotonic() < deadline:
            search_state = {}
            try:
                state_response = httpx.get(
                    f"{base_url}/api/v0/searches/{search_id}",
                    params={"includeResponses": "true"},
                    headers=headers,
                    timeout=8,
                )
                state_response.raise_for_status()
                state_data = state_response.json()
                if isinstance(state_data, dict):
                    search_state = state_data
                    state_payload = state_data.get("responses")
                    if isinstance(state_payload, list):
                        for entry in state_payload:
                            identity = (
                                entry.get("username") or entry.get("user") or "",
                                json.dumps(entry.get("files") or [], sort_keys=True, ensure_ascii=False),
                            )
                            payload_by_peer[identity] = entry
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in (404, 405):
                    raise
            response_poll = httpx.get(
                f"{base_url}/api/v0/searches/{search_id}/responses",
                headers=headers,
                timeout=8,
            )
            if response_poll.status_code not in (404, 405):
                response_poll.raise_for_status()
                data = response_poll.json()
                response_items = (
                    data if isinstance(data, list)
                    else data.get("responses") or data.get("items") or []
                    if isinstance(data, dict) else []
                )
                for entry in response_items if isinstance(response_items, list) else []:
                    identity = (
                        entry.get("username") or entry.get("user") or "",
                        json.dumps(entry.get("files") or [], sort_keys=True, ensure_ascii=False),
                    )
                    payload_by_peer[identity] = entry
            state_text = str(search_state.get("state") or "").lower()
            if search_state.get("isComplete") is True or (
                state_text and ("complete" in state_text or "timedout" in state_text)
            ):
                break
            time.sleep(0.75)
        expected_track_count = _discovery_expected_track_count(metadata)
        candidates = _slskd_extract_candidates(
            list(payload_by_peer.values()), artist, album, priority,
            expected_track_count=expected_track_count,
        )
        if not candidates:
            message = "No matching album folders were found. You can try again later."
            _discovery_update_acquisition_status(
                artist, album, "no_matches",
                {"message": message, "search_id": search_id, "metadata": metadata},
            )
            return json.dumps({
                "ok": True, "status": "no_matches", "artist": artist, "album": album,
                "search_id": search_id, "message": message,
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
                 "best_candidate_reason": best.get("eligibility_reason")},
            )
            return json.dumps({
                "ok": True, "status": "no_matches", "artist": artist, "album": album,
                "search_id": search_id, "candidate_count": len(candidates),
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
                # A timeout or server error can happen after slskd accepted
                # the queue request. Monitor this peer before considering a
                # fallback, otherwise two sources could download the album.
                candidate_for_monitor = dict(candidate)
                candidate_for_monitor["files"] = selected_files
                candidate_for_monitor["quality_summary"] = list(
                    candidate.get("quality_summary") or []
                )
                candidate_for_monitor["fallback_candidates"] = [
                    {**item, "files": [
                        {"filename": file["filename"], "size": file["size"]}
                        for file in item.get("files", [])
                    ]}
                    for item in clear_candidates[clear_candidates.index(candidate) + 1:10]
                ]
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

            candidate_for_monitor = dict(candidate)
            candidate_for_monitor["files"] = selected_files
            candidate_for_monitor["quality_summary"] = list(candidate.get("quality_summary") or [])
            candidate_for_monitor["fallback_candidates"] = [
                {**item, "files": [
                    {"filename": file["filename"], "size": file["size"]}
                    for file in item.get("files", [])
                ]}
                for item in clear_candidates[clear_candidates.index(candidate) + 1:10]
            ]
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
            candidate_for_monitor = dict(uncertain)
            candidate_for_monitor["files"] = [
                {"filename": item["filename"], "size": item["size"]}
                for item in uncertain["files"]
            ]
            candidate_for_monitor["quality_summary"] = list(uncertain.get("quality_summary") or [])
            candidate_for_monitor["fallback_candidates"] = [
                {**item, "files": [
                    {"filename": file["filename"], "size": file["size"]}
                    for file in item.get("files", [])
                ]}
                for item in clear_candidates[clear_candidates.index(uncertain) + 1:10]
            ]
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
            {"message": message, "attempts": failures, "metadata": metadata},
        )
        return json.dumps({
            "ok": False, "status": "queue_failed", "artist": artist, "album": album,
            "attempts": failures, "message": message,
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


@mcp.tool()
def discovery_acquire_album(
    artist: str,
    album: str,
    metadata_json: str = "{}",
    auto_queue: bool = True,
) -> str:
    """Prevent concurrent duplicate acquisition searches for the same album."""
    if not artist.strip() or not album.strip():
        return json.dumps({"ok": False, "error": "Artist and album are required."})
    identity = (_music_key(artist), _music_key(album))
    with _DISCOVERY_IMPORT_TRANSITION_LOCK:
        if _discovery_is_dismissed(artist, album):
            return json.dumps({
                "ok": False, "status": "dismissed", "artist": artist, "album": album,
                "message": "This acquisition was dismissed. Undismiss it before retrying.",
            }, ensure_ascii=False)
        with _DISCOVERY_IMPORT_LOCK:
            watcher_active = identity in _DISCOVERY_IMPORT_ACTIVE
        existing_job = next((
            job for job in _discovery_list_acquisition_jobs()
            if job["artist_key"] == identity[0] and job["album_key"] == identity[1]
        ), None)
        existing_status = (existing_job or {}).get("status")
        if existing_status in {"importing", "imported"}:
            return json.dumps({
                "ok": False, "status": existing_status, "artist": artist, "album": album,
                "message": "This album is already being imported or is in the library.",
            }, ensure_ascii=False)
        if (
            identity in _DISCOVERY_ACQUIRE_ACTIVE
            or watcher_active
            or existing_status == "downloading"
        ):
            return json.dumps({
                "ok": False, "status": "already_in_progress", "artist": artist, "album": album,
                "message": "An acquisition request or download is already active for this album.",
            }, ensure_ascii=False)
        _DISCOVERY_ACQUIRE_ACTIVE.add(identity)
    try:
        return _discovery_acquire_album_impl(artist, album, metadata_json, auto_queue)
    finally:
        with _DISCOVERY_IMPORT_TRANSITION_LOCK:
            _DISCOVERY_ACQUIRE_ACTIVE.discard(identity)


@mcp.tool()
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

@mcp.tool()
def discovery_get_list(list_name: str = "personal", count: int = 30) -> str:
    """Read saved discovery results or the For Me list.

    list_name is personal or for_me. Dismissed albums and artists are hidden
    from personal results; For Me entries are marked acquired when found in
    the current Navidrome album inventory.
    """
    if list_name not in {"personal", "for_me", "classics", "artist_deep_dive"}:
        return json.dumps({
            "error": "list_name must be personal, classics, artist_deep_dive, or for_me."
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
    return results


@mcp.tool()
def discovery_refresh_list(list_name: str = "personal", count: int = 10) -> str:
    """Refresh personal, classics, artist_deep_dive, or all discovery lists.

    Personal uses the existing ListenBrainz recommendation engine. Classics
    and Artist Deep Dives use Last.fm and MusicBrainz data. The latter two run
    in the background because their first full refresh can take several minutes.
    """
    import threading

    if list_name not in {"personal", "classics", "artist_deep_dive", "all"}:
        return json.dumps({
            "ok": False,
            "error": "list_name must be personal, classics, artist_deep_dive, or all",
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


def _discovery_scheduler():
    """Refresh each discovery list when its stored results are older than 24 hours."""
    while True:
        try:
            for list_name in ("personal", "classics", "artist_deep_dive"):
                cached = _discovery_read_list(list_name)
                stale = (
                    cached is None
                    or time.time() - cached["generated_at"] >= 24 * 60 * 60
                )
                if not stale:
                    continue
                if list_name == "personal":
                    _discovery_refresh_personal(20)
                else:
                    _discovery_refresh_other(list_name)
        except Exception:
            # Background discovery must not take down the MCP service.
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


@mcp.tool()
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


@mcp.tool()
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
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8000)
