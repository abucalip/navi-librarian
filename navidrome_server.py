import hashlib
import json
import os
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

MUSIC_DIR = Path("/Volumes/media/library/music")

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
    """Fetch recent public ListenBrainz listens, with bounded pagination."""
    import time
    import httpx

    min_ts = int(time.time()) - days * 86400
    max_ts = None
    listens = []

    headers = {"User-Agent": "NavidromeLibrarian/1.0"}

    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for _ in range(page_limit):
            params = {"min_ts": min_ts, "count": 1000}
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

            if len(page) < 1000:
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
            "History retrieval is bounded to three pages of up to 1,000 "
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
        candidate_decisions[id(candidate)] = {
            "status": status,
            "reason": reason,
        }

    def consider(
        candidate,
        allow_over_quota=False,
        allow_over_family_cap=False,
    ):
        nonlocal checked
        category = candidate["discovery_category"]
        style = candidate.get("diversity_style", "other")
        if (
            style in diversity_style_targets
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
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8000)
