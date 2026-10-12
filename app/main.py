import json
import random
from html import escape
from time import monotonic, sleep
from concurrent.futures import ThreadPoolExecutor
import threading
import httpx
from urllib.parse import urlencode
from urllib.request import urlopen

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

import navidrome_server as librarian


_EXTERNAL_HTTP = httpx.Client(
    timeout=httpx.Timeout(3.0, connect=1.5),
    headers={"User-Agent": "NavidromeLibrarian/1.0 (personal music discovery; contact: local app)"},
)

app = FastAPI(
    title="Navidrome Librarian",
    description="A read-only web interface for your music library.",
    version="0.1.0",
)


def parse_result(value):
    """Convert existing MCP function results into JSON when possible."""
    if not isinstance(value, str):
        return value

    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {"message": value}


@app.get("/api/health")
def health():
    """Check whether Navidrome responds to an authenticated API request."""
    try:
        result = librarian.api_call("ping")
        return {
            "status": "ok",
            "service": "Navidrome",
            "message": result.get("status", "Connected"),
        }
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Navidrome is unavailable or authentication failed.",
        )


# Artist biographies are cached for a day. Wikidata identifies the intended
# musical entity first; Wikipedia is only used when its page points back to
# that exact Wikidata item. This prevents name collisions (e.g. Rainbow the band
# versus the optical phenomenon) from producing unrelated summaries.
_ARTIST_BIO_CACHE_TTL = 24 * 60 * 60
_artist_bio_cache = {}

_ARTIST_DESCRIPTION_RE = __import__("re").compile(
    r"\b(?:band|musical group|rock group|pop group|music group|duo|orchestra|"
    r"choir|singer|singer-songwriter|musician|rapper|vocalist|songwriter|composer|"
    r"guitarist|bassist|drummer|keyboardist|record producer|music producer|"
    r"electronic musician|disc jockey|\bdj\b|folk musician|jazz musician)\b",
    __import__("re").IGNORECASE,
)


@app.get("/api/artist-bio")
def artist_bio(artist: str):
    name = str(artist or "").strip()
    if not name or len(name) > 180:
        raise HTTPException(status_code=400, detail="A valid artist name is required.")
    key = name.casefold()
    now = monotonic()
    cached = _artist_bio_cache.get(key)
    if cached and now - cached["time"] < _ARTIST_BIO_CACHE_TTL:
        return {"artist": name, "bio": cached["bio"]}

    bio = ""
    params = {
        "action": "wbsearchentities",
        "search": name,
        "language": "en",
        "uselang": "en",
        "format": "json",
        "limit": 10,
    }
    summary_url = (
        "https://en.wikipedia.org/api/rest_v1/page/summary/"
        + __import__("urllib.parse", fromlist=["quote"]).quote(name.replace(" ", "_"), safe="")
    )

    # Start both network requests together. The summary is used only after its
    # Wikidata identity is checked, so the faster path doesn't reintroduce
    # wrong-name biographies such as Rainbow the optical phenomenon.
    with ThreadPoolExecutor(max_workers=2) as pool:
        search_future = pool.submit(
            _EXTERNAL_HTTP.get, "https://www.wikidata.org/w/api.php", params=params
        )
        summary_future = pool.submit(_EXTERNAL_HTTP.get, summary_url)
        entities = []
        page = {}
        try:
            search_response = search_future.result()
            search_response.raise_for_status()
            entities = search_response.json().get("search", [])
        except Exception:
            pass
        try:
            summary_response = summary_future.result()
            if summary_response.status_code == 200:
                page = summary_response.json()
        except Exception:
            pass

    music_entities = [
        item for item in entities
        if item.get("id")
        and _ARTIST_DESCRIPTION_RE.search(str(item.get("description") or ""))
    ]
    music_entities.sort(key=lambda item: (
        str(item.get("label") or "").casefold() != key,
        str(item.get("label") or "").casefold() != key.replace("the ", "", 1),
    ))

    page_qid = str(page.get("wikibase_item") or "")
    if page_qid and page.get("type") != "disambiguation":
        matching_entity = next(
            (item for item in music_entities if str(item.get("id") or "") == page_qid),
            None,
        )
        if matching_entity:
            extract = " ".join(str(page.get("extract") or "").split())
            if extract:
                match = __import__("re").search(r"^.*?[.!?](?=\s|$)", extract)
                bio = match.group(0) if match else extract[:240]
                if len(bio) > 280:
                    bio = bio[:277].rsplit(" ", 1)[0] + "…"

    # Fast, safe fallback: use Wikidata's own music-related description.
    if not bio and music_entities:
        bio = str(music_entities[0].get("description") or "").strip()

    _artist_bio_cache[key] = {"time": monotonic(), "bio": bio}
    return {"artist": name, "bio": bio}


@app.get("/api/dashboard-picks")
def dashboard_picks(count: int = 10):
    if not 1 <= count <= 20:
        raise HTTPException(status_code=400, detail="count must be between 1 and 20")
    combined = []
    by_category = {}
    seen = set()
    categories = (
        ("personal", "Personal discoveries"),
        ("classics", "Add to your collection"),
        ("artist_deep_dive", "Artist Deep Dives"),
    )
    for _list_name, label in categories:
        by_category[label] = []
    for list_name, label in categories:
        try:
            data = parse_result(librarian.discovery_get_list(list_name=list_name, count=150))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        items = data.get("items") or data.get("recommendations") or []
        for item in items:
            if not isinstance(item, dict):
                continue
            artist = str(item.get("artist") or item.get("album_artist") or "").strip()
            album = str(item.get("album") or item.get("title") or "").strip()
            if not librarian._discovery_is_album_candidate(item):
                continue
            identity = (artist.casefold(), album.casefold())
            if not artist or not album or identity in seen:
                continue
            seen.add(identity)
            candidate = {**item, "artist": artist, "album": album, "dashboard_category": label}
            combined.append(candidate)
            by_category[label].append(candidate)

    # Guarantee a balanced representation when all discovery lanes have data,
    # then fill the remaining slots from the whole deduplicated pool.
    random_picks = []
    quota = max(1, count // len(categories))
    for label in [entry[1] for entry in categories]:
        lane = by_category[label]
        random.shuffle(lane)
        random_picks.extend(lane[:quota])
    picked_ids = {
        (item["artist"].casefold(), item["album"].casefold())
        for item in random_picks
    }
    remainder = [
        item for item in combined
        if (item["artist"].casefold(), item["album"].casefold()) not in picked_ids
    ]
    random.shuffle(remainder)
    random_picks.extend(remainder[:max(0, count - len(random_picks))])
    random.shuffle(random_picks)
    return {"items": random_picks[:count], "count": min(count, len(random_picks)), "pool_size": len(combined)}


@app.get("/api/recommendations")
def recommendations(count: int = 10):
    if not 1 <= count <= 30:
        raise HTTPException(
            status_code=400,
            detail="count must be between 1 and 30",
        )

    try:
        data = parse_result(librarian.recommend_new_music(count=count))
        if isinstance(data, dict):
            for key in ("recommendations", "items"):
                if isinstance(data.get(key), list):
                    data[key] = [
                        item for item in data[key]
                        if librarian._discovery_is_album_candidate(item)
                    ]
        return data
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Could not generate recommendations.",
        )



@app.get("/api/discovery/{list_name}")
def discovery_list(list_name: str, count: int = 30):
    allowed = {"personal", "for_me", "classics", "artist_deep_dive", "new_releases"}
    if list_name not in allowed:
        raise HTTPException(status_code=404, detail="Unknown discovery list.")
    if not 1 <= count <= 150:
        raise HTTPException(status_code=400, detail="count must be between 1 and 150")
    try:
        return parse_result(
            librarian.discovery_get_list(list_name=list_name, count=count)
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Could not retrieve the discovery list.")


@app.post("/api/discovery/{list_name}/refresh")
def refresh_discovery_list(list_name: str, payload: dict | None = None):
    if list_name not in {"personal", "classics", "artist_deep_dive", "new_releases", "all"}:
        raise HTTPException(status_code=404, detail="Unknown discovery list.")
    payload = payload or {}
    try:
        count = int(payload.get("count", 20))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="count must be an integer")
    if not 1 <= count <= 20:
        raise HTTPException(status_code=400, detail="count must be between 1 and 20")
    try:
        return parse_result(
            librarian.discovery_refresh_list(list_name=list_name, count=count)
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Could not refresh the discovery list.")


@app.post("/api/discovery/feedback")
def discovery_feedback(payload: dict):
    artist = str(payload.get("artist") or "").strip()
    album = str(payload.get("album") or "").strip()
    action = str(payload.get("action") or "").strip()
    if not artist or not album:
        raise HTTPException(status_code=400, detail="artist and album are required")
    if action not in {"save", "dismiss", "dismiss_artist", "remove_for_me"}:
        raise HTTPException(status_code=400, detail="Unsupported feedback action")
    try:
        return parse_result(librarian.discovery_set_feedback(
            artist=artist,
            album=album,
            action=action,
            metadata_json=json.dumps(payload.get("metadata") or {}, ensure_ascii=False),
        ))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not save discovery feedback.")


@app.get("/api/acquisitions")
def acquisition_status():
    try:
        return parse_result(librarian.discovery_get_acquisition_status())
    except Exception:
        raise HTTPException(status_code=502, detail="Could not retrieve acquisition status.")


@app.post("/api/acquisitions/skip")
def skip_acquisition_source(payload: dict):
    artist = str(payload.get("artist") or "").strip()
    album = str(payload.get("album") or "").strip()
    if not artist or not album:
        raise HTTPException(status_code=400, detail="artist and album are required")
    try:
        result = parse_result(librarian.discovery_skip_acquisition_source(
            artist=artist, album=album,
        ))
        if isinstance(result, dict) and not result.get("ok"):
            raise HTTPException(status_code=409, detail=result.get("error", "Could not skip source."))
        return result
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Could not request a source switch.")


@app.post("/api/acquisitions/dismiss")
def dismiss_acquisition(payload: dict):
    artist = str(payload.get("artist") or "").strip()
    album = str(payload.get("album") or "").strip()
    if not artist or not album:
        raise HTTPException(status_code=400, detail="artist and album are required")
    try:
        result = parse_result(librarian.discovery_dismiss_acquisition(artist=artist, album=album))
        if isinstance(result, dict) and not result.get("ok"):
            message = result.get("error", "Could not dismiss acquisition.")
            status_code = 404 if message == "Acquisition not found." else 409
            raise HTTPException(status_code=status_code, detail=message)
        return result
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Could not dismiss acquisition.")


@app.get("/api/acquisitions/stream")
def acquisition_status_stream():
    def events():
        while True:
            try:
                payload = parse_result(librarian.discovery_get_acquisition_status())
                yield "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"
            except Exception:
                yield "event: error\ndata: {}\n\n"
            sleep(1)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/settings/navidrome")
def get_navidrome_settings():
    try:
        return parse_result(librarian.discovery_get_navidrome_settings())
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read Navidrome settings.")


@app.put("/api/settings/navidrome")
def set_navidrome_settings(payload: dict):
    try:
        result = parse_result(librarian.discovery_set_navidrome_settings(
            navidrome_url=str(payload.get("navidrome_url") or ""),
            username=str(payload.get("username") or ""),
            password=str(payload.get("password") or ""),
            music_library_path=str(payload.get("music_library_path") or ""),
        ))
        if isinstance(result, dict) and not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error", "Invalid settings"))
        return result
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Could not save Navidrome settings.")


@app.post("/api/settings/navidrome/test")
def test_navidrome_settings():
    try:
        return parse_result(librarian.discovery_test_navidrome_connection())
    except Exception:
        raise HTTPException(status_code=502, detail="Could not test the Navidrome connection.")


@app.get("/api/settings/lastfm")
def get_lastfm_settings():
    try:
        return parse_result(librarian.discovery_get_lastfm_settings())
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read Last.fm settings.")


@app.put("/api/settings/lastfm")
def set_lastfm_settings(payload: dict):
    try:
        return parse_result(librarian.discovery_set_lastfm_settings(api_key=str(payload.get("api_key") or "")))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not save Last.fm settings.")


@app.post("/api/settings/lastfm/test")
def test_lastfm_settings():
    try:
        return parse_result(librarian.discovery_test_lastfm_connection())
    except Exception:
        raise HTTPException(status_code=502, detail="Could not test the Last.fm connection.")


@app.get("/api/settings/listenbrainz")
def get_listenbrainz_settings():
    try:
        return parse_result(librarian.discovery_get_listenbrainz_settings())
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read ListenBrainz settings.")


@app.put("/api/settings/listenbrainz")
def set_listenbrainz_settings(payload: dict):
    try:
        result = parse_result(librarian.discovery_set_listenbrainz_settings(username=str(payload.get("username") or "")))
        if isinstance(result, dict) and not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error", "Invalid settings"))
        return result
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Could not save ListenBrainz settings.")


@app.post("/api/settings/listenbrainz/test")
def test_listenbrainz_settings():
    try:
        return parse_result(librarian.discovery_test_listenbrainz_connection())
    except Exception:
        raise HTTPException(status_code=502, detail="Could not test the ListenBrainz connection.")


@app.get("/api/settings/slskd")
def get_slskd_settings():
    try:
        return parse_result(librarian.discovery_get_slskd_settings())
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read slskd settings.")


@app.put("/api/settings/slskd")
def set_slskd_settings(payload: dict):
    url = str(payload.get("slskd_url") or "http://192.168.1.12:5030")
    api_key = str(payload.get("api_key") or "")
    quality = payload.get("quality_priority")
    if quality is None:
        quality = ["mp3_320", "mp3_193_319", "mp3_192", "flac_cd"]
    try:
        result = parse_result(librarian.discovery_set_slskd_settings(
            slskd_url=url,
            api_key=api_key,
            quality_priority_json=json.dumps(quality),
            slskd_downloads_path=(
                str(payload["slskd_downloads_path"]).strip()
                if "slskd_downloads_path" in payload
                else None
            ),
            music_library_path=(
                str(payload["music_library_path"]).strip()
                if "music_library_path" in payload
                else None
            ),
        ))
        if isinstance(result, dict) and not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error", "Invalid settings"))
        return result
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Could not save slskd settings.")


@app.post("/api/settings/slskd/test")
def test_slskd_settings():
    try:
        return parse_result(librarian.discovery_test_slskd_connection())
    except Exception:
        raise HTTPException(status_code=502, detail="Could not test the slskd connection.")


@app.post("/api/acquire")
def acquire_album(payload: dict):
    artist = str(payload.get("artist") or "").strip()
    album = str(payload.get("album") or "").strip()
    if not artist or not album:
        raise HTTPException(status_code=400, detail="artist and album are required")
    try:
        return parse_result(librarian.discovery_acquire_album(
            artist=artist,
            album=album,
            metadata_json=json.dumps(payload.get("metadata") or {}, ensure_ascii=False),
            auto_queue=bool(payload.get("auto_queue", True)),
        ))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not search slskd for this album.")


@app.post("/api/acquire/queue")
def queue_reviewed_candidate(payload: dict):
    username = str(payload.get("username") or "").strip()
    artist = str(payload.get("artist") or "").strip()
    album = str(payload.get("album") or "").strip()
    folder = str(payload.get("folder") or "").strip()
    files = payload.get("files")
    if not username or not isinstance(files, list) or not files:
        raise HTTPException(status_code=400, detail="username and a non-empty files list are required")
    try:
        return parse_result(librarian.discovery_queue_slskd_candidate(
            username=username,
            files_json=json.dumps(files, ensure_ascii=False),
            artist=artist,
            album=album,
            folder=folder,
            quality_summary_json=json.dumps(payload.get("quality_summary") or [], ensure_ascii=False),
        ))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not queue the selected candidate.")


# Artwork is optional presentation metadata; discovery works without it.
_ARTWORK_CACHE_TTL = 6 * 60 * 60
_ARTWORK_NEGATIVE_CACHE_TTL = 5 * 60
_artwork_cache = {}
_MUSICBRAINZ_YEAR_CACHE_TTL = 180 * 24 * 60 * 60
_musicbrainz_year_cache = {}
_musicbrainz_year_lock = threading.Lock()
_musicbrainz_last_request = 0.0


def _musicbrainz_album_year(artist: str, album: str):
    """Resolve a release year from an exact MusicBrainz release-group match."""
    import re
    global _musicbrainz_last_request

    def norm(value):
        return "".join(ch.casefold() for ch in str(value or "") if ch.isalnum())

    artist = str(artist or "").strip()
    album = str(album or "").strip()
    if not artist or not album:
        return None
    key = (norm(artist), norm(album))
    now = monotonic()
    cached = _musicbrainz_year_cache.get(key)
    if cached:
        ttl = _MUSICBRAINZ_YEAR_CACHE_TTL if cached.get("year") else 6 * 60 * 60
        if now - cached["time"] < ttl:
            return cached["year"]

    year = None
    try:
        with _musicbrainz_year_lock:
            cached = _musicbrainz_year_cache.get(key)
            now = monotonic()
            if cached:
                ttl = _MUSICBRAINZ_YEAR_CACHE_TTL if cached.get("year") else 6 * 60 * 60
                if now - cached["time"] < ttl:
                    return cached["year"]
            wait = 1.1 - (now - _musicbrainz_last_request)
            if wait > 0:
                sleep(wait)
            escaped_artist = artist.replace("\\", "\\\\").replace('"', '\\"')
            escaped_album = album.replace("\\", "\\\\").replace('"', '\\"')
            query = urlencode({
                "query": f'artist:"{escaped_artist}" AND releasegroup:"{escaped_album}"',
                "fmt": "json",
                "limit": 25,
            })
            request = __import__("urllib.request", fromlist=["Request"]).Request(
                "https://musicbrainz.org/ws/2/release-group/?" + query,
                headers={"User-Agent": "NavidromeLibrarian/1.0 (personal music discovery)"},
            )
            _musicbrainz_last_request = monotonic()
            with urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))

        exact_dates = []
        for group in payload.get("release-groups") or []:
            if norm(group.get("title")) != norm(album):
                continue
            credits = []
            for part in group.get("artist-credit") or []:
                if not isinstance(part, dict):
                    continue
                credit_name = (part.get("artist") or {}).get("name") or part.get("name")
                if credit_name:
                    credits.append(str(credit_name))
            # Accept an exact artist credit or an exact credited member of a
            # collaboration, never a substring such as "Queen Tribute".
            if norm(artist) not in {norm(name) for name in credits} and norm("".join(credits)) != norm(artist):
                continue
            date_text = str(group.get("first-release-date") or "")
            year_text = date_text[:4]
            if year_text.isdigit() and 1900 <= int(year_text) <= 2100:
                exact_dates.append((date_text or year_text, int(year_text)))
        if exact_dates:
            year = min(exact_dates, key=lambda entry: entry[0])[1]
    except Exception:
        # The UI can still show artwork; an unavailable catalog is not fatal.
        pass

    _musicbrainz_year_cache[key] = {"time": monotonic(), "year": year}
    return year


@app.get("/api/album-year")
def album_year(artist: str = "", album: str = ""):
    """Return a year only when an authoritative catalog has an exact album match."""
    artist = str(artist or "").strip()[:180]
    album = str(album or "").strip()[:180]
    if not artist or not album:
        raise HTTPException(status_code=400, detail="artist and album are required")

    year = _musicbrainz_album_year(artist, album)
    source = "MusicBrainz" if year else None

    # MusicBrainz is primary. Deezer is a fallback only for an exact normalized
    # artist AND album match; fuzzy or artist-only results are never trusted.
    if not year:
        def norm(value):
            return "".join(ch.casefold() for ch in str(value or "") if ch.isalnum())
        try:
            query = urlencode({"q": f'artist:"{artist}" album:"{album}"', "limit": 20})
            response = _EXTERNAL_HTTP.get("https://api.deezer.com/search/album?" + query)
            response.raise_for_status()
            for item in response.json().get("data") or []:
                if norm((item.get("artist") or {}).get("name")) != norm(artist):
                    continue
                if norm(item.get("title")) != norm(album):
                    continue
                year_text = str(item.get("release_date") or "")[:4]
                if year_text.isdigit() and 1900 <= int(year_text) <= 2100:
                    year = int(year_text)
                    source = "Deezer"
                    break
        except Exception:
            pass

    return {"artist": artist, "album": album, "year": year, "source": source}


@app.get("/api/album-details")
def album_details(artist: str = "", album: str = ""):
    """Return a carefully matched Deezer album and its tracklist for the card popup."""
    artist = str(artist or "").strip()[:180]
    album = str(album or "").strip()[:180]
    if not artist or not album:
        raise HTTPException(status_code=400, detail="artist and album are required")

    def key(value):
        return "".join(char.casefold() for char in str(value or "") if char.isalnum())

    result = {"artist": artist, "album": album, "year": None, "artwork_url": None, "tracks": []}
    try:
        query = urlencode({"q": f'artist:"{artist}" album:"{album}"', "limit": 12})
        response = _EXTERNAL_HTTP.get("https://api.deezer.com/search/album?" + query)
        response.raise_for_status()
        albums = response.json().get("data") or []
        exact = [
            item for item in albums
            if key((item.get("artist") or {}).get("name")) == key(artist)
            and key(item.get("title")) == key(album)
        ]
        if not exact:
            result["message"] = "No exact catalog match was found, so the tracklist is unavailable."
            return result

        match = exact[0]
        release_date = str(match.get("release_date") or "")
        year_text = release_date[:4]
        result.update({
            "matched_artist": (match.get("artist") or {}).get("name"),
            "matched_album": match.get("title"),
            "year": int(year_text) if year_text.isdigit() and 1900 <= int(year_text) <= 2100 else None,
            "artwork_url": (match.get("cover_xl") or match.get("cover_big") or match.get("cover_medium") or "").replace("http://", "https://", 1) or None,
        })
        album_id = match.get("id")
        if not album_id:
            result["message"] = "Album artwork found, but the catalog did not provide a tracklist ID."
            return result

        detail_response = _EXTERNAL_HTTP.get(f"https://api.deezer.com/album/{album_id}")
        detail_response.raise_for_status()
        details = detail_response.json()
        result["tracks"] = [
            {
                "track_number": int(track.get("track_position") or index + 1),
                "title": str(track.get("title") or "").strip(),
                "duration_seconds": int(track.get("duration") or 0),
            }
            for index, track in enumerate(details.get("tracks", {}).get("data") or [])
            if str(track.get("title") or "").strip()
        ]
        if not result["tracks"]:
            result["message"] = "The album was found, but its tracklist is unavailable."
        return result
    except Exception:
        result["message"] = "The album catalog is temporarily unavailable."
        return result


@app.get("/api/artwork")
def album_artwork(artist: str = "", album: str = ""):
    artist = artist.strip()[:180]
    album = album.strip()[:180]
    if not artist and not album:
        raise HTTPException(status_code=400, detail="artist or album is required")

    key = (artist.casefold(), album.casefold())
    now = monotonic()
    cached = _artwork_cache.get(key)
    if cached:
        ttl = _ARTWORK_CACHE_TTL if cached["data"].get("artwork_url") else _ARTWORK_NEGATIVE_CACHE_TTL
        if now - cached["time"] < ttl:
            return cached["data"]

    result = {"artwork_url": None, "image_kind": "album", "source": "Deezer"}
    try:
        if artist and album:
            query = urlencode({"q": f'artist:"{artist}" album:"{album}"', "limit": 8})
        else:
            query = urlencode({"q": artist or album, "limit": 8})
        endpoint = "https://api.deezer.com/search/album?" + query
        response = _EXTERNAL_HTTP.get(endpoint)
        response.raise_for_status()
        payload = response.json()
        albums = payload.get("data") or []

        def match_score(item):
            candidate_artist = str((item.get("artist") or {}).get("name") or "").casefold()
            candidate_album = str(item.get("title") or "").casefold()
            score = 0
            if artist.casefold() == candidate_artist:
                score += 5
            elif artist and artist.casefold() in candidate_artist:
                score += 2
            if album.casefold() == candidate_album:
                score += 8
            elif album and (album.casefold() in candidate_album or candidate_album in album.casefold()):
                score += 4
            return score

        if albums:
            match = max(albums, key=match_score)
            if match_score(match) >= 9:
                # Prefer Deezer's XL artwork for crisp large cards and high-DPI displays.
                artwork = match.get("cover_xl") or match.get("cover_big") or match.get("cover_medium")
                release_date = str(match.get("release_date") or "")
                year_text = release_date[:4]
                result = {
                    "artwork_url": artwork.replace("http://", "https://", 1) if artwork else None,
                    "image_kind": "album",
                    "source": "Deezer",
                    "matched_artist": (match.get("artist") or {}).get("name"),
                    "matched_album": match.get("title"),
                    "year": int(year_text) if year_text.isdigit() and 1900 <= int(year_text) <= 2100 else None,
                }

        # Do not perform a serialized MusicBrainz lookup here: it rate-limits
        # requests and can delay artwork by several seconds. Deezer release dates
        # are shown when available; missing years must never delay the cover.
        # If the album is not in the catalog, use a matching artist photo instead.
        if not result["artwork_url"] and artist:
            artist_query = urlencode({"q": artist, "limit": 8})
            response = _EXTERNAL_HTTP.get("https://api.deezer.com/search/artist?" + artist_query)
            response.raise_for_status()
            artist_payload = response.json()
            artists = artist_payload.get("data") or []
            exact = next(
                (item for item in artists if str(item.get("name") or "").casefold() == artist.casefold()),
                None,
            )
            if exact:
                # Prefer high-resolution artist portraits; fall back if unavailable.
                photo = exact.get("picture_xl") or exact.get("picture_big") or exact.get("picture_medium")
                if photo:
                    result = {
                        "artwork_url": photo.replace("http://", "https://", 1),
                        "image_kind": "artist",
                        "source": "Deezer",
                        "matched_artist": exact.get("name"),
                        "year": result.get("year"),
                    }
    except Exception:
        # A catalog outage must never break discovery or recommendation results.
        pass

    _artwork_cache[key] = {"time": monotonic(), "data": result}
    return result


@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse(PAGE)


PAGE = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Navidrome Librarian</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
:root {
  color-scheme: dark;
  --bg: #191a1a; --surface: #222424; --surface-raised: #292b2a; --surface-hover: #30322f;
  --border: #3b3d39; --text: #f0eee5; --muted: #a5a69c; --subtle: #77796f;
  --yellow: #e9c64a; --yellow-dim: #554b26; --red: #e05b4f; --green: #a8c59a;
  --radius: 6px; --display: "Barlow Condensed", "Arial Narrow", sans-serif;
  --body: "IBM Plex Sans", sans-serif; --mono: "IBM Plex Mono", monospace;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { margin: 0; background: var(--bg); color: var(--text); font: 15px/1.55 var(--body); -webkit-font-smoothing: antialiased; }
button, input, select, textarea { font: inherit; }
button, select, input { color: var(--text); background: var(--surface); border: 1px solid var(--border); border-radius: 4px; padding: 10px 12px; }
button { cursor: pointer; transition: background .15s ease, border-color .15s ease, color .15s ease; }
button:hover { border-color: var(--yellow); background: var(--surface-hover); }
button:disabled { opacity: .55; cursor: wait; }
button:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid var(--yellow); outline-offset: 2px; }
header {
  position: fixed; inset: 0 0 auto 0; z-index: 20; min-height: 82px;
  display: flex; align-items: center; justify-content: space-between; gap: 24px;
  padding: 15px 30px; background: #1d1f1e; border-bottom: 1px solid var(--border);
}
header h1 { display: flex; align-items: center; gap: 12px; margin: 0; font: 700 29px/.95 var(--display); letter-spacing: .025em; text-transform: uppercase; }
header h1::before {
  content: "NL"; display: grid; place-items: center; width: 37px; height: 37px;
  color: #191a1a; background: var(--yellow); border-bottom: 4px solid var(--red);
  font: 700 16px/1 var(--mono); letter-spacing: -.08em;
}
header p { margin: 0; color: var(--muted); font-size: 12px; letter-spacing: .025em; text-align: right; }
main { max-width: none; margin: 112px 34px 0 254px; padding: 0 0 60px; }
nav {
  position: fixed; z-index: 15; inset: 82px auto 0 0; width: 220px;
  display: flex; flex-direction: column; align-items: stretch; gap: 4px; overflow-y: auto;
  padding: 23px 13px; background: #1d1f1e; border-right: 1px solid var(--border);
}
nav::before { content: "YOUR COLLECTION"; padding: 0 12px 10px; color: var(--subtle); font: 500 10px/1.4 var(--mono); letter-spacing: .12em; }
nav button { position: relative; width: 100%; padding: 10px 12px 10px 15px; text-align: left; color: #b7b8ae; background: transparent; border: 0; border-radius: 3px; font-size: 13px; }
nav button:hover { color: var(--text); background: var(--surface-raised); }
.nav-count { float: right; min-width: 20px; margin-left: 8px; padding: 1px 5px; border-radius: 10px; color: #191a1a; background: var(--yellow); font: 500 10px/1.6 var(--mono); text-align: center; }
.nav-count[hidden] { display: none; }
nav button.active { color: var(--text); background: #2b2d29; box-shadow: inset 3px 0 var(--yellow); }
nav button.active::after { content: ""; position: absolute; top: 9px; right: 10px; width: 5px; height: 5px; background: var(--red); border-radius: 50%; }
.panel { min-width: 0; margin: 0 0 36px; padding: 0; background: transparent; border: 0; border-radius: 0; }
.panel h2 { margin: 0 0 9px; font: 600 34px/1.05 var(--display); letter-spacing: .01em; }
.panel h2::after { content: ""; display: block; width: 34px; height: 3px; margin-top: 11px; background: var(--red); }
h3 { margin: 0 0 5px; font-size: 16px; line-height: 1.3; }
p { line-height: 1.55; }
.panel > p { max-width: 760px; }
.settings-tabs { display: flex; flex-wrap: wrap; gap: 7px; margin: 22px 0 20px; border-bottom: 1px solid var(--border); padding-bottom: 10px; }
.settings-tabs .settings-tab { padding: 9px 15px; border: 1px solid var(--border); border-radius: 4px; color: var(--muted); background: #202221; }
.settings-tabs .settings-tab.active { color: #191a1a; background: var(--yellow); border-color: var(--yellow); }
.settings-tab-panel { max-width: 760px; }
.settings-tab-panel[hidden] { display: none; }
.settings-tab-panel label { display: block; margin: 14px 0; color: var(--muted); font-size: 13px; }
.settings-tab-panel input { display: block; box-sizing: border-box; width: 100%; margin-top: 6px; padding: 10px 12px; border: 1px solid var(--border); border-radius: 4px; color: var(--text); background: #202221; }
.settings-tab-panel button { margin-right: 6px; }
#saveNavidrome, #saveLastfm, #saveListenbrainz, #saveSlskd { color: #191a1a; background: var(--yellow); border-color: var(--yellow); }
.muted { color: var(--muted); }
.status { font-weight: 600; }
.ok { color: var(--green); }
.error { color: var(--red); }
.controls { display: flex; align-items: center; gap: 9px; flex-wrap: wrap; margin: 18px 0 14px; }
.controls label { color: var(--muted); font-size: 13px; }
.controls button, .card-actions button, #settings button { font-size: 12px; font-weight: 600; letter-spacing: .015em; }
#loadRecommendations, #saveSlskd { color: #191a1a; background: var(--yellow); border-color: var(--yellow); }
#loadRecommendations:hover, #saveSlskd:hover { background: #f3d66b; border-color: #f3d66b; }
.discovery-controls { display: grid; grid-template-columns: minmax(220px, 2fr) repeat(2, minmax(145px, 1fr)); gap: 8px; margin: 17px 0 8px; }
.discovery-controls input, .discovery-controls select { width: 100%; min-width: 0; background: #202221; border: 1px solid var(--border); color: var(--text); padding: 10px 12px; border-radius: 4px; }
#recommendationCount { margin: 13px 0 16px; color: var(--muted); font: 11px/1.5 var(--mono); letter-spacing: .02em; }
.cards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; align-items: stretch; }
.cards.deep-dive-rows { display: flex; flex-direction: column; gap: 27px; }
.dashboard-carousel { display: flex; gap: 15px; overflow-x: auto; padding: 3px 2px 15px; scroll-snap-type: x proximity; scrollbar-color: #686044 #222424; scrollbar-width: thin; scroll-behavior: smooth; }
.dashboard-carousel > .card { flex: 0 0 218px; width: 218px; scroll-snap-align: start; }
.dashboard-carousel-heading { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.dashboard-carousel-heading p { margin: 0; color: var(--muted); font-size: 12px; }
.dashboard-carousel-heading button { margin-left: auto; }
.dashboard-picks-status { min-height: 18px; color: var(--muted); font-size: 11px; }
.genre-row { min-width: 0; }
.genre-row-heading { display: flex; align-items: baseline; gap: 12px; margin: 0 0 10px; }
.genre-row-heading h3 { margin: 0; color: var(--text); font: 600 23px/1.1 var(--display); text-transform: uppercase; letter-spacing: .025em; }
.genre-row-count { color: var(--subtle); font: 10px/1.4 var(--mono); }
.genre-row-arrows { display: flex; gap: 6px; margin-left: auto; }
.genre-row-arrow { display: grid; place-items: center; width: 38px; height: 34px; padding: 0; border: 0; background: transparent; color: var(--yellow); font: 700 36px/.8 var(--display); text-shadow: 0 1px 0 #9a8127; }
.genre-row-arrow:hover { background: transparent; color: #ffe477; transform: scale(1.12); }
.genre-row-track { display: flex; gap: 13px; overflow-x: auto; overflow-y: hidden; padding: 2px 2px 12px; scroll-snap-type: x proximity; scrollbar-color: #686044 #222424; scrollbar-width: thin; scroll-behavior: smooth; }
.genre-row-track > .card { flex: 0 0 218px; width: 218px; scroll-snap-align: start; }
.card { position: relative; }
.card.editorial-card, #acquisitionCards > .card, #recommendationCards > .card { cursor: pointer; }
.album-modal-backdrop { position: fixed; inset: 0; z-index: 100; display: grid; place-items: center; padding: 24px; background: rgba(0,0,0,.78); backdrop-filter: blur(5px); }
.album-modal-backdrop[hidden] { display: none; }
.album-modal { position: relative; width: min(100%, 1040px); max-height: min(90vh, 900px); overflow: auto; padding: 24px; background: #202221; border: 1px solid #55574e; border-radius: 8px; box-shadow: 0 25px 90px rgba(0,0,0,.65); }
.album-modal-close { position: sticky; top: 0; float: right; z-index: 2; width: 38px; height: 38px; padding: 0; font-size: 23px; }
.album-modal-layout { display: grid; grid-template-columns: minmax(220px, 340px) minmax(0, 1fr); gap: 26px; clear: both; }
.album-modal-art-column { min-width: 0; align-self: start; }
.album-modal-art { position: relative; overflow: hidden; aspect-ratio: 1; background: #30322e; border: 1px solid var(--border); }
.album-modal-art img { display: block; width: 100%; height: 100%; object-fit: cover; }
.album-modal-art-column .album-platform-links { position: static; display: flex; flex-flow: row nowrap; align-items: center; justify-content: center; gap: 6px; width: 100%; max-width: 100%; min-width: 0; margin: 8px 0 0; padding: 0; border: 0; background: transparent; box-shadow: none; }
.album-modal-art-column .album-platform-links a { box-sizing: border-box; display: inline-flex; flex: 0 0 30px; align-items: center; justify-content: center; width: 30px; min-width: 30px; max-width: 30px; height: 30px; min-height: 30px; max-height: 30px; padding: 5px; overflow: hidden; border: 1px solid #55574e; border-radius: 5px; color: var(--text); background: #292b28; text-decoration: none; transition: border-color .15s, background .15s; }
.album-modal-art-column .album-platform-links a img { display: block; flex: 0 0 18px; width: 18px; min-width: 18px; max-width: 18px; height: 18px; object-fit: contain; }
.album-modal-art-column .album-platform-links a:hover { border-color: var(--yellow); background: #36372f; }
.album-modal-art-column .album-platform-links a:focus-visible { outline: 2px solid var(--yellow); outline-offset: 2px; }
.album-modal-art-column .album-platform-links .platform-icon-fallback { font: 700 10px/1 var(--mono); }
.album-modal-art .get-album { position: absolute; right: 12px; bottom: 12px; width: 58px; height: 58px; border-radius: 50%; background: var(--yellow); color: #191a1a; border: 2px solid #f6e8a8; font: 700 12px/1 var(--mono); text-transform: uppercase; box-shadow: 0 3px 12px rgba(0,0,0,.55); }
.album-modal-copy h2 { margin: 0 0 7px; font: 600 34px/1.05 var(--display); overflow-wrap: anywhere; }
.album-modal-artist { margin: 0 0 20px; color: var(--muted); }
.album-modal-year { color: var(--yellow); font: 500 12px/1.4 var(--mono); }
.album-modal-tracklist { margin: 20px 0 0; padding: 0; list-style: none; border-top: 1px solid var(--border); }
.album-modal-tracklist li { display: grid; grid-template-columns: 32px minmax(0,1fr) auto; gap: 10px; align-items: baseline; padding: 9px 0; border-bottom: 1px solid #333531; font-size: 13px; }
.album-modal-tracklist .track-number, .album-modal-tracklist .track-duration { color: var(--subtle); font: 11px/1.4 var(--mono); }
.album-modal-status { color: var(--muted); font-size: 12px; }
@media (max-width: 650px) { .album-modal-backdrop { padding: 8px; } .album-modal { padding: 14px; max-height: 96vh; } .album-modal-layout { grid-template-columns: minmax(0,1fr); gap: 18px; } .album-modal-art-column { width: min(100%, 300px); margin: 0 auto; } .album-modal-copy h2 { font-size: 28px; } }
.card h3 .album-year { margin-left: 5px; color: var(--muted); font: 500 12px/1 var(--mono); white-space: nowrap; }
.card .artist-bio { margin-top: 7px; color: var(--muted); font: 400 12px/1.45 var(--body); }
.card .card-art .get-album { position: absolute; z-index: 3; right: 10px; bottom: 10px; width: 46px; height: 46px; padding: 0; display: grid; place-items: center; border-radius: 50%; background: var(--yellow); border: 2px solid #f6e8a8; color: #191a1a; box-shadow: 0 3px 12px rgba(0,0,0,.55); font: 700 11px/1 var(--mono); text-transform: uppercase; }
.card .card-art .get-album:hover { background: #f3d66b; transform: scale(1.06); }
.card .card-art .deep-dive-dismiss { position: absolute; z-index: 4; top: 5px; right: 8px; display: grid; place-items: center; width: auto; height: auto; padding: 0 3px; border: 0; border-radius: 0; background: transparent; color: #ff5148; font: 700 30px/.95 var(--body); text-shadow: 0 2px 5px #000, 0 0 10px rgba(0,0,0,.9); box-shadow: none; }
.card .card-art .deep-dive-dismiss:hover { background: transparent; color: #ff827a; border: 0; transform: scale(1.12); }
.card .card-actions { display: flex; align-items: center; gap: 7px; margin-top: auto; padding-top: 12px; }
.card .card-actions .get-album { width: 42px; height: 42px; padding: 0; display: inline-grid; place-items: center; background: var(--yellow); border: 1px solid var(--yellow); border-radius: 50%; color: #191a1a; font: 700 11px/1 var(--mono); text-transform: uppercase; }
.card .card-actions .get-album:hover { background: #f3d66b; border-color: #f3d66b; }
.get-album.requested, .card .card-art .get-album.requested, .card .card-actions .get-album.requested { background: #c83232; border-color: #f05b5b; color: #fff; cursor: default; box-shadow: 0 3px 12px rgba(120,0,0,.35); }
.get-album.requested:hover, .card .card-art .get-album.requested:hover, .card .card-actions .get-album.requested:hover { background: #c83232; border-color: #f05b5b; transform: none; }
@media (max-width: 1100px) { .cards:not(.deep-dive-rows) { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 760px) { .cards:not(.deep-dive-rows) { grid-template-columns: repeat(2, minmax(0, 1fr)); } .genre-row-track > .card { flex-basis: 185px; width: 185px; } }
.card { min-width: 0; overflow: hidden; padding: 0 0 1px; background: var(--surface); border: 1px solid #353834; border-radius: var(--radius); transition: border-color .15s ease, transform .15s ease; }
.card:hover { border-color: #686044; transform: translateY(-2px); }
.card-art {
  position: relative; display: grid; place-items: center; aspect-ratio: 1 / 1; width: 100%; overflow: hidden;
  background: linear-gradient(135deg, transparent 49.5%, rgba(233,198,74,.12) 50%, transparent 50.5%), #30322e;
  border-bottom: 1px solid var(--border);
}
.card-art::after { content: ""; position: absolute; inset: auto 0 0; height: 3px; background: var(--yellow); transform: scaleX(0); transform-origin: left; transition: transform .2s ease; }
.card:hover .card-art::after { transform: scaleX(1); }
.card-art img { position: absolute; inset: 0; display: block; width: 100%; height: 100%; object-fit: cover; opacity: 0; transition: opacity .18s ease; }
.card-art.has-image img { opacity: 1; }
.card-art.has-image .card-art-placeholder { display: none; }
.card-art-placeholder { padding: 12px; color: #b5aa79; text-align: center; font: 500 10px/1.5 var(--mono); letter-spacing: .12em; }
.card-art-placeholder::before { content: "NL / 01"; display: block; margin-bottom: 8px; color: var(--yellow); font: 600 28px/1 var(--display); letter-spacing: -.02em; }
.card > :not(.card-art) { margin-left: 13px; margin-right: 13px; }
.card-category { display: inline-block; max-width: calc(100% - 26px); margin-top: 13px; margin-bottom: 9px; padding: 3px 6px; color: var(--yellow); background: #353124; border-left: 2px solid var(--yellow); border-radius: 0; font: 500 9px/1.4 var(--mono); letter-spacing: .055em; text-transform: uppercase; }
.card h3 { margin-top: 0; margin-bottom: 4px; font: 600 20px/1.1 var(--display); letter-spacing: .005em; overflow-wrap: anywhere; }
.card-artist { margin-top: 0; margin-bottom: 13px; color: #c0c0b5; font-size: 12px; }
.genre-list { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 12px; }
.genre-tag { padding: 3px 6px; color: #bfc0b6; background: #30322e; border: 1px solid #41433d; border-radius: 2px; font: 10px/1.35 var(--mono); }
.card-meta, .card-source { margin-top: 7px; margin-bottom: 0; color: var(--muted); font-size: 11px; overflow-wrap: anywhere; }
.download-progress { display: flex; align-items: center; gap: 14px; margin: 13px; padding: 12px; background: #1c1e1d; border: 1px solid #353834; }
.progress-ring { position: relative; display: grid; place-items: center; flex: 0 0 72px; width: 72px; height: 72px; border-radius: 50%; background: conic-gradient(var(--yellow) var(--progress, 0%), #3b3d39 0); }
.progress-ring::before { content: ""; position: absolute; inset: 5px; border-radius: 50%; background: #1c1e1d; }
.progress-ring span { position: relative; z-index: 1; color: var(--text); font: 500 14px/1 var(--mono); }
.download-progress-copy { min-width: 0; }
.download-progress-speed-row { display: flex; flex-wrap: wrap; align-items: baseline; gap: 3px 12px; }
.download-progress-speed-row .download-progress-stat + .download-progress-stat { margin-top: 0; color: var(--muted); }
.download-progress-copy > .download-progress-stat { margin-top: 3px; }
.download-progress-label { margin: 0 0 4px; color: var(--yellow); font: 500 10px/1.4 var(--mono); letter-spacing: .07em; text-transform: uppercase; }
.download-progress-stat { margin: 0; color: var(--text); font-size: 12px; overflow-wrap: anywhere; }
.download-progress-stat + .download-progress-stat { margin-top: 3px; color: var(--muted); }
.card-source { padding-top: 8px; border-top: 1px solid #353834; }
.card-actions { display: flex; flex-wrap: wrap; gap: 6px; padding-top: 13px; padding-bottom: 13px; }
.card-actions button { padding: 7px 8px; background: #2a2c29; }
.card-actions button:first-child { border-color: #655b31; }
.hidden { display: none !important; }
details { margin-top: 18px; border-top: 1px solid var(--border); padding-top: 12px; }
summary { color: var(--muted); cursor: pointer; font-size: 12px; }
pre, #result { white-space: pre-wrap; overflow-wrap: anywhere; color: #c6c7bd; font: 11px/1.6 var(--mono); }
#settings label { display: block; margin: 14px 0; color: #c8c8bd; font-size: 12px; }
#settings input, #settings select { display: block; width: 100%; max-width: 520px; margin-top: 6px; }
.discovery-settings { display: grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap: 12px; }
footer { margin-top: 36px; padding-top: 14px; border-top: 1px solid var(--border); color: var(--subtle); font: 10px/1.6 var(--mono); }
@media (max-width: 1200px) { .cards { grid-template-columns: repeat(3, minmax(0, 1fr)); } main { margin-left: 238px; margin-right: 25px; } }
@media (max-width: 900px) { nav { width: 184px; } main { margin-left: 205px; margin-right: 20px; } .cards { grid-template-columns: repeat(2, minmax(0, 1fr)); } .discovery-controls { grid-template-columns: 1fr 1fr; } .discovery-controls input { grid-column: 1 / -1; } }
@media (max-width: 620px) {
  header { min-height: 70px; padding: 12px 15px; } header h1 { font-size: 24px; } header h1::before { width: 32px; height: 32px; font-size: 14px; } header p { display: none; }
  nav { inset: 70px 0 auto 0; width: auto; height: 54px; flex-direction: row; align-items: center; gap: 3px; padding: 5px 10px; overflow-x: auto; overflow-y: hidden; border-right: 0; border-bottom: 1px solid var(--border); }
  nav::before { display: none; } nav button { width: auto; flex: 0 0 auto; padding: 9px 11px; white-space: nowrap; } nav button.active { box-shadow: inset 0 -3px var(--yellow); } nav button.active::after { display: none; }
  main { margin: 148px 14px 0; padding-bottom: 36px; } .panel h2 { font-size: 30px; } .cards { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; } .card h3 { font-size: 18px; } .card > :not(.card-art) { margin-left: 10px; margin-right: 10px; } .card-category { max-width: calc(100% - 20px); } .discovery-controls { grid-template-columns: 1fr; } .discovery-controls input { grid-column: auto; }
}
@media (max-width: 360px) { .cards { grid-template-columns: 1fr; } }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { scroll-behavior: auto !important; transition-duration: .01ms !important; } }
</style>
</head>
<body>
<header>
  <h1>Navidrome Librarian</h1>
  <p>LISTENING INTELLIGENCE · DISCOVERY INDEX</p>
</header>
<main>
  <nav>
    <button class="active" data-page="dashboard">Dashboard</button>
    <button data-page="recommendations">Recommendations</button>
    <button data-page="newReleases">New releases</button>
    <button data-page="personalDiscoveries">Personal Discoveries</button>
    <button data-page="classics">Add to your collection</button>
    <button data-page="artistDeepDive">Artist Deep Dives</button>
    <button data-page="acquisitions">Acquisitions <span id="activeDownloadBadge" class="nav-count" hidden aria-label="Active downloads">0</span></button>
    <button data-page="settings">Settings</button>
  </nav>

  <section id="dashboard" class="page">
    <div class="panel">
      <div class="dashboard-carousel-heading">
        <div>
          <h2>Ten from the collection</h2>
          <p>A fresh, random mix from every discovery lane.</p>
        </div>
        <button id="shuffleDashboard">Shuffle picks ↻</button>
      </div>
      <p id="dashboardPicksStatus" class="dashboard-picks-status">Finding something unexpected…</p>
      <div id="dashboardCarousel" class="dashboard-carousel" aria-label="Random album recommendations"></div>
    </div>
  </section>

  <section id="recommendations" class="page hidden">
    <div class="panel">
      <h2>Discover music</h2>
      <div class="controls">
        <label for="count">Albums</label>
        <select id="count">
          <option>5</option><option selected>10</option><option>15</option><option>20</option>
      </select>
        <button id="loadRecommendations">Generate recommendations</button>
      </div>
      <div class="discovery-controls">
        <input
          id="recommendationSearch"
          type="search"
          placeholder="Search artist, album, or genre…"
          aria-label="Search recommendations"
        >
        <select id="categoryFilter" aria-label="Filter by discovery category">
          <option value="all">All categories</option>
          <option value="adjacent">Adjacent</option>
          <option value="cross_genre">Cross-genre</option>
          <option value="adventurous">Adventurous</option>
          <option value="unclassified">Unclassified</option>
        </select>
        <select id="recommendationSort" aria-label="Sort recommendations">
          <option value="original">Recommended order</option>
          <option value="popularity">Most popular artists</option>
          <option value="score">Highest discovery score</option>
          <option value="artist">Artist A–Z</option>
        </select>
      </div>
      <p id="recommendationCount" class="muted" aria-live="polite">
        Generate recommendations to get started.
      </p>
      <div id="recommendationCards" class="cards"></div>
      <details>
        <summary>Recommendation diagnostics</summary>
        <pre id="recommendationDebug" class="muted"></pre>
      </details>
    </div>
  </section>

  <section id="newReleases" class="page hidden">
    <div class="panel">
      <h2>New releases</h2>
      <p>Full albums released in the last 24 months by artists who already have a full album in your library.</p>
      <div class="controls">
        <button data-load-discovery="new_releases">Load new releases</button>
        <button data-refresh-discovery="new_releases">Refresh in background</button>
      </div>
      <p id="newReleasesStatus" aria-live="polite"></p>
      <div id="newReleasesCards" class="cards"></div>
    </div>
  </section>

  <footer>
    Discovery, feedback and acquisition controls use your existing Librarian backend. Artwork is optional and never blocks recommendations.
  </footer>

<section id="personalDiscoveries" class="page hidden">
  <div class="panel">
    <h2>Personal Discoveries</h2>
    <p>Recommendations based on your listening and musical interests.</p>
    <button data-load-discovery="personal">Load discoveries</button>
    <button data-refresh-discovery="personal">Refresh</button>
    <p id="personalStatus"></p>
    <div id="personalCards" class="cards"></div>
  </div>
</section>

<section id="classics" class="page hidden">
  <div class="panel">
    <h2>Add to your collection</h2>
    <p>Find acclaimed albums and less obvious discoveries to expand your library.</p>
    <button data-load-discovery="classics">Load albums</button>
    <button data-refresh-discovery="classics">Refresh</button>
    <p id="classicsStatus"></p>
    <div id="classicsCards" class="cards"></div>
  </div>
</section>

<section id="artistDeepDive" class="page hidden">
  <div class="panel">
    <h2>Artist Deep Dives</h2>
    <p>Explore missing albums by artists in your library and discover similar artists.</p>
    <button data-load-discovery="artist_deep_dive">Load albums</button>
    <button data-refresh-discovery="artist_deep_dive">Refresh</button>
    <p id="artistDeepDiveStatus"></p>
    <div id="artistDeepDiveCards" class="cards"></div>
  </div>
</section>

<section id="settings" class="page hidden">
  <div class="panel">
    <h2>Settings</h2>
    <p>Configure the services used by Navidrome Librarian. Secrets are never displayed after saving.</p>
    <div class="settings-tabs" role="tablist" aria-label="Service settings">
      <button type="button" class="settings-tab active" role="tab" aria-selected="true" aria-controls="settingsNavidrome" data-settings-tab="navidrome">Navidrome</button>
      <button type="button" class="settings-tab" role="tab" aria-selected="false" aria-controls="settingsSlskd" data-settings-tab="slskd">slskd</button>
      <button type="button" class="settings-tab" role="tab" aria-selected="false" aria-controls="settingsLastfm" data-settings-tab="lastfm">Last.fm</button>
      <button type="button" class="settings-tab" role="tab" aria-selected="false" aria-controls="settingsListenbrainz" data-settings-tab="listenbrainz">ListenBrainz</button>
    </div>
    <div id="settingsNavidrome" class="settings-tab-panel" role="tabpanel">
      <h3>Navidrome connection</h3>
      <label>Navidrome URL <input id="navidromeUrl" type="url" placeholder="http://192.168.1.12:4533"></label>
      <label>Username <input id="navidromeUser" type="text" autocomplete="username"></label>
      <label>Password <input id="navidromePassword" type="password" placeholder="Leave blank to keep the saved password" autocomplete="new-password"></label>
      <label>Music library directory visible to the Librarian backend <input id="musicLibraryPath" type="text" placeholder="/media/library/music"></label>
      <p class="muted">Use the path as seen by the Librarian process/container, not a path inside the Navidrome service.</p>
      <p id="connection" class="status">Not checked yet.</p>
      <p><button id="saveNavidrome">Save settings</button> <button id="checkConnection">Test connection</button></p>
      <p id="navidromeStatus" aria-live="polite"></p>
    </div>
    <div id="settingsSlskd" class="settings-tab-panel" role="tabpanel" hidden>
      <h3>slskd connection</h3>
      <p>The API key is never displayed. Leave the key field blank to retain the configured key.</p>
      <label>slskd URL <input id="slskdUrl" type="url" placeholder="http://192.168.1.12:5030"></label>
      <label>API key <input id="slskdApiKey" type="password" placeholder="Enter key to set or replace it" autocomplete="new-password"></label>
      <label>slskd completed-download directory visible to the Librarian backend <input id="slskdDownloadsPath" type="text" placeholder="/media/downloads/slskd/complete"></label>
      <p class="muted">Use an absolute path on the machine/container running the Librarian backend. The directory must be mounted into the container when using Docker.</p>
      <h3>Audio quality priority</h3>
      <label>First choice <select class="quality-priority"></select></label>
      <label>Second choice <select class="quality-priority"></select></label>
      <label>Third choice <select class="quality-priority"></select></label>
      <label>Fourth choice <select class="quality-priority"></select></label>
      <p><button id="saveSlskd">Save settings</button> <button id="testSlskd">Test connection</button></p>
      <p id="slskdStatus" aria-live="polite"></p>
    </div>
    <div id="settingsLastfm" class="settings-tab-panel" role="tabpanel" hidden>
      <h3>Last.fm API</h3>
      <p class="muted">Optional. Used to enrich recommendations with album popularity and artist tags. Obtain an API key from Last.fm's API page.</p>
      <label>API key <input id="lastfmApiKey" type="password" placeholder="Leave blank to keep the saved key" autocomplete="new-password"></label>
      <p id="lastfmStatus" aria-live="polite"></p>
      <p><button id="saveLastfm">Save settings</button> <button id="testLastfm">Test connection</button></p>
    </div>
    <div id="settingsListenbrainz" class="settings-tab-panel" role="tabpanel" hidden>
      <h3>ListenBrainz profile</h3>
      <p class="muted">Used for recent listening context and personalized recommendations. Only the public username is needed.</p>
      <label>Username <input id="listenbrainzUsername" type="text" autocomplete="off"></label>
      <p id="listenbrainzStatus" aria-live="polite"></p>
      <p><button id="saveListenbrainz">Save settings</button> <button id="testListenbrainz">Test connection</button></p>
    </div>
  </div>
</section>

<section id="acquisitions" class="page hidden">
  <div class="panel">
    <h2>Acquisition status</h2>
    <p class="muted">Persistent download and import status, including failures. Active jobs are resumed when this page checks in.</p>
    <p id="acquisitionsStatus"></p>
    <div id="acquisitionCards" class="cards"></div>
    <button id="refreshAcquisitions">Refresh status</button>
  </div>
</section>



</main>

<div id="albumModalBackdrop" class="album-modal-backdrop" hidden>
  <section class="album-modal" role="dialog" aria-modal="true" aria-labelledby="albumModalTitle">
    <button id="albumModalClose" class="album-modal-close" type="button" aria-label="Close album details">×</button>
    <div class="album-modal-layout">
      <div class="album-modal-art-column">
        <div class="album-modal-art"><img id="albumModalArtwork" alt="Album artwork"><button id="albumModalGet" class="get-album" type="button">get</button></div>
        <nav id="albumModalPlatformLinks" class="album-platform-links" aria-label="Find this album on music services"></nav>
      </div>
      <div class="album-modal-copy"><h2 id="albumModalTitle">Album</h2><p id="albumModalArtist" class="album-modal-artist"></p><p id="albumModalYear" class="album-modal-year"></p><p id="albumModalStatus" class="album-modal-status" aria-live="polite">Loading tracklist…</p><ol id="albumModalTracklist" class="album-modal-tracklist"></ol></div>
    </div>
  </section>
</div>
<script>
const $ = id => document.getElementById(id);

function isAlbumRecommendation(item) {
  if (!item || typeof item !== 'object') return false;
  const title = String(item.album || item.title || item.name || '').trim();
  if (!title) return false;
  const primary = String(item.primary_type || item['primary-type'] || item.album_type || item.release_type || '').trim().toLowerCase();
  if (primary && !['album', 'full length album'].includes(primary)) return false;
  const secondary = item.secondary_types || item['secondary-types'] || item.secondary_type || [];
  const types = (Array.isArray(secondary) ? secondary : String(secondary).split(/[,;/|]/))
    .map(value => String(value).toLowerCase().replace(/[^a-z]+/g, ' ').trim());
  if (types.some(value => ['compilation', 'soundtrack', 'live', 'remix', 'dj mix', 'mixtape', 'ep', 'single', 'karaoke', 'tribute'].includes(value))) return false;
  const normalized = title.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  return ![/\bcompilations?\b/, /\bremixes?\b/, /\bremixed\b/, /\bdj\s*mix(?:es)?\b/, /\bmixtapes?\b/, /\bsoundtracks?\b/, /\bkaraoke\b/, /\btribute\b/, /\bgreatest hits\b/, /\bbest of\b/, /\banthology\b/, /\bsamplers?\b/, /\blive\b/]
    .some(pattern => pattern.test(normalized));
}

function showPage(name) {
  document.querySelectorAll('.page').forEach(el =>
    el.classList.toggle('hidden', el.id !== name));
  document.querySelectorAll('nav button[data-page]').forEach(el =>
    el.classList.toggle('active', el.dataset.page === name));
}

const initializedPages = new Set(['dashboard']);

function initializePage(name) {
  if (initializedPages.has(name)) return;
  initializedPages.add(name);
  if (name === 'recommendations') $('loadRecommendations').click();
  else if (name === 'newReleases') loadDiscovery('new_releases');
  else if (name === 'personalDiscoveries') loadDiscovery('personal');
  else if (name === 'classics') loadDiscovery('classics', {rotate: true});
  else if (name === 'artistDeepDive') loadDiscovery('artist_deep_dive', {rotate: true});
  else if (name === 'settings') { loadNavidromeSettings(); loadSlskdSettings(); loadLastfmSettings(); loadListenbrainzSettings(); }
  else if (name === 'acquisitions') startAcquisitionStream();
}

document.querySelectorAll('nav button[data-page]').forEach(button =>
  button.addEventListener('click', () => {
    const name = button.dataset.page;
    showPage(name);
    initializePage(name);
    if (name !== 'acquisitions') stopAcquisitionStream();
  }));

document.querySelectorAll('button[data-go]').forEach(button =>
  button.addEventListener('click', () => showPage(button.dataset.go)));

async function requestJSON(url) {
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'Request failed');
  return data;
}

async function checkConnection() {
  const el = $('connection');
  el.textContent = 'Checking Navidrome…';
  el.className = 'status';
  try {
    const data = await requestJSON('/api/health');
    el.textContent = 'Connected to Navidrome';
    el.className = 'status ok';
  } catch (error) {
    el.textContent = error.message;
    el.className = 'status error';
  }
}

function pretty(value) {
  return JSON.stringify(value, null, 2);
}

function formatDownloadBytes(value) {
  if (value === null || value === undefined || value === '') return null;
  const bytes = Number(value);
  if (!Number.isFinite(bytes) || bytes < 0) return null;
  if (bytes < 1024) return Math.round(bytes) + ' B';
  const units = ['KB', 'MB', 'GB', 'TB'];
  let amount = bytes / 1024;
  let unit = 0;
  while (amount >= 1024 && unit < units.length - 1) {
    amount /= 1024;
    unit += 1;
  }
  return amount.toFixed(amount >= 100 ? 0 : 1) + ' ' + units[unit];
}

function renderAcquisitions(data, targetOverride = null, statusOverride = null, onlyIdentity = null) {
  const target = targetOverride || $('acquisitionCards');
  const status = statusOverride || $('acquisitionsStatus');
  try {
    target.replaceChildren();
    const jobs = Array.isArray(data.acquisitions) ? data.acquisitions : [];
    updateActiveDownloadBadge(data);
    const dismissed = new Set(JSON.parse(localStorage.getItem('navidrome-dismissed-acquisitions') || '[]'));
    status.textContent = jobs.length
      ? `${jobs.length} acquisition record(s).`
      : 'No acquisition records yet.';
    for (const job of jobs) {
      if (onlyIdentity && [job.artist || '', job.album || ''].join('::').toLocaleLowerCase() !== onlyIdentity) continue;
      const dismissalKey = [job.artist || '', job.album || ''].join('::').toLocaleLowerCase();
      if (job.status === 'imported' && dismissed.has(dismissalKey)) continue;
      const card = document.createElement('article');
      card.className = 'card';
      makeAlbumCardInteractive(card, job.artist || 'Unknown artist', job.album || 'Unknown album', job.details || {}, true);
      addTextElement(card, 'p', 'card-category', String(job.status || 'unknown').replaceAll('_', ' '));
      addTextElement(card, 'h3', '', job.album || 'Unknown album');
      const details = job.details || {};
      const metadata = details.metadata || {};
      applyAlbumYear(card, metadata.year || metadata.release_year || metadata.first_release_year || details.year || job.year);
      addTextElement(card, 'p', 'card-artist', job.artist || 'Unknown artist');
      const qualityLabels = {
        mp3_320: 'MP3 320 kbps', mp3_193_319: 'MP3 193–319 kbps',
        mp3_192: 'MP3 192 kbps', flac_cd: 'FLAC / CD quality',
      };
      const quality = Array.isArray(details.quality_summary) ? details.quality_summary : [];
      addTextElement(card, 'p', 'card-meta',
        'Quality profile: ' + (quality.length
          ? quality.map(value => qualityLabels[value] || String(value).replaceAll('_', ' ')).join(' · ')
          : 'Not reported'));
      const progress = details.live_progress;
      if (['downloading', 'download_complete_waiting_for_folder'].includes(job.status) && progress) {
        const progressRow = document.createElement('div');
        progressRow.className = 'download-progress';
        const ring = document.createElement('div');
        ring.className = 'progress-ring';
        const percent = Number.isFinite(Number(progress.percent)) && progress.percent !== null
          ? Math.max(0, Math.min(100, Number(progress.percent))) : null;
        ring.style.setProperty('--progress', percent === null ? '0%' : percent + '%');
        ring.setAttribute('role', 'img');
        ring.setAttribute('aria-label', percent === null ? 'Download progress unavailable' : 'Download ' + Math.round(percent) + ' percent complete');
        const percentText = document.createElement('span');
        percentText.textContent = percent === null ? '—' : Math.round(percent) + '%';
        ring.append(percentText);
        const copy = document.createElement('div');
        copy.className = 'download-progress-copy';
        addTextElement(copy, 'p', 'download-progress-label', 'Download progress');
        const speed = progress.speed_bytes_per_second;
        let speedText = 'Speed unavailable';
        if (Number.isFinite(Number(speed)) && speed !== null) {
          const value = Math.max(0, Number(speed));
          speedText = value >= 1024 * 1024
            ? (value / (1024 * 1024)).toFixed(1) + ' MB/s'
            : value >= 1024 ? (value / 1024).toFixed(0) + ' KB/s' : Math.round(value) + ' B/s';
        }
        const speedAndSize = document.createElement('div');
        speedAndSize.className = 'download-progress-speed-row';
        addTextElement(speedAndSize, 'p', 'download-progress-stat', speedText);
        const totalSize = formatDownloadBytes(progress.total_size_bytes);
        const remainingSize = formatDownloadBytes(progress.remaining_size_bytes);
        if (totalSize !== null && remainingSize !== null) {
          addTextElement(speedAndSize, 'p', 'download-progress-stat',
            'Total ' + totalSize + ' · ' + remainingSize + ' remaining');
        }
        copy.append(speedAndSize);
        const remaining = Number.isFinite(Number(progress.remaining_tracks)) ? Math.max(0, Number(progress.remaining_tracks)) : null;
        const totalTracks = Number.isFinite(Number(progress.total_tracks)) ? Math.max(0, Number(progress.total_tracks)) : null;
        addTextElement(copy, 'p', 'download-progress-stat',
          remaining === null ? 'Tracks remaining unavailable' :
          String(remaining) + ' of ' + (totalTracks === null ? '?' : totalTracks) + ' tracks remaining');
        progressRow.append(ring, copy);
        card.append(progressRow);
      }
      if (job.status === 'downloading' && details.stall_detected_at && Number(details.fallback_count) > 0) {
        const stallButton = document.createElement('button');
        stallButton.type = 'button';
        stallButton.className = 'skip-source-button';
        const secondsLeft = Math.max(0, 15 - Math.floor(Date.now() / 1000 - Number(details.stall_detected_at)));
        stallButton.textContent = secondsLeft > 0
          ? 'Skip to next source (' + secondsLeft + 's)'
          : 'Switching source…';
        stallButton.disabled = secondsLeft <= 0;
        stallButton.addEventListener('click', async () => {
          stallButton.disabled = true;
          stallButton.textContent = 'Requesting source switch…';
          try {
            const result = await sendJSON('/api/acquisitions/skip', 'POST', {
              artist: job.artist, album: job.album
            });
            status.textContent = result.message || 'Source switch requested.';
          } catch (error) {
            status.textContent = error.message;
            stallButton.disabled = false;
          }
        });
        card.append(stallButton);
      }
      const lines = [
        details.message,
        details.error,
        details.source_folder ? 'Source: ' + details.source_folder : '',
        details.destination ? 'Destination: ' + details.destination : '',
        details.downloads_path ? 'Downloads: ' + details.downloads_path : '',
        details.source_username ? 'Peer: ' + details.source_username : '',
        details.file_count ? 'Expected files: ' + details.file_count : '',
        details.states ? 'Transfer states: ' + details.states.join(', ') : '',
        details.transfer_states ? 'Transfer states: ' + details.transfer_states.join(', ') : '',
        details.expected_folder ? 'Expected folder: ' + details.expected_folder : '',
        details.matched_transfer_records !== undefined ? 'Matched transfer records: ' + details.matched_transfer_records + ' / ' + (details.expected_files ?? details.file_count ?? '?') : '',
        details.downloads_path_available === false ? 'Completed-download directory is not accessible to the backend.' : '',
        details.completion_evidence ? 'Completion evidence: ' + details.completion_evidence : '',
        job.updated_at ? 'Updated: ' + new Date(job.updated_at * 1000).toLocaleString() : ''
      ].filter(Boolean);
      for (const line of lines) addTextElement(card, 'p', 'card-meta', line);
      if (job.status !== 'dismissed') {
        const actions = document.createElement('div');
        actions.className = 'card-actions';
        const retryableStatuses = new Set(['no_matches', 'queue_failed', 'settings_required', 'slskd_error']);
        if (retryableStatuses.has(job.status)) {
          const retry = document.createElement('button');
          retry.type = 'button';
          retry.textContent = 'Try again';
          retry.addEventListener('click', async () => {
            retry.disabled = true;
            retry.textContent = 'Retrying…';
            try {
              await sendJSON('/api/acquire', 'POST', {
                artist: job.artist, album: job.album,
                metadata: details.metadata || {}, auto_queue: true
              });
              await loadAcquisitions();
            } catch (error) {
              status.textContent = error.message;
              retry.disabled = false;
              retry.textContent = 'Try again';
            }
          });
          actions.append(retry);
        }
        {
          const dismiss = document.createElement('button');
        dismiss.type = 'button';
        dismiss.textContent = 'Dismiss';
        dismiss.addEventListener('click', async () => {
          dismiss.disabled = true;
          try {
            await sendJSON('/api/acquisitions/dismiss', 'POST', {
              artist: job.artist, album: job.album
            });
            const stored = new Set(JSON.parse(localStorage.getItem('navidrome-dismissed-acquisitions') || '[]'));
            stored.add(dismissalKey);
            localStorage.setItem('navidrome-dismissed-acquisitions', JSON.stringify([...stored]));
            card.remove();
            const visibleCards = target.querySelectorAll('.card').length;
            status.textContent = visibleCards
              ? visibleCards + ' acquisition record(s).'
              : 'No acquisition records to show.';
          } catch (error) {
            status.textContent = error.message;
            dismiss.disabled = false;
          }
        });
          actions.append(dismiss);
        }
        if (actions.childElementCount) card.append(actions);
      }
      if (details.status && details.status !== job.status) {
        addTextElement(card, 'pre', 'debug', pretty(details));
      }
      target.append(card);
    }
  } catch (error) {
    status.textContent = error.message;
  }
}

const ACTIVE_DOWNLOAD_STATUSES = new Set([
  'searching', 'requested', 'queued', 'downloading',
  'download_complete_waiting_for_folder', 'importing',
  'queue_uncertain', 'recovery_started', 'monitoring',
]);

function updateActiveDownloadBadge(data) {
  const badge = $('activeDownloadBadge');
  if (!badge) return;
  const jobs = Array.isArray(data && data.acquisitions) ? data.acquisitions : [];
  const count = jobs.filter(job => ACTIVE_DOWNLOAD_STATUSES.has(String(job.status || '').toLowerCase())).length;
  badge.textContent = String(count);
  badge.hidden = count === 0;
  badge.setAttribute('aria-label', count + ' active download' + (count === 1 ? '' : 's'));
}

async function refreshActiveDownloadBadge() {
  try {
    updateActiveDownloadBadge(await requestJSON('/api/acquisitions'));
  } catch (_) {
    // The navigation badge is advisory; do not surface transient polling errors.
  }
}

async function loadAcquisitions() {
  $('acquisitionsStatus').textContent = 'Connecting to acquisition status…';
  try {
    renderAcquisitions(await requestJSON('/api/acquisitions'));
  } catch (error) {
    $('acquisitionsStatus').textContent = error.message;
  }
}

refreshActiveDownloadBadge();
setInterval(refreshActiveDownloadBadge, 30000);

let acquisitionStream = null;
function startAcquisitionStream() {
  if (acquisitionStream) return;
  loadAcquisitions();
  acquisitionStream = new EventSource('/api/acquisitions/stream');
  acquisitionStream.onmessage = event => {
    try {
      renderAcquisitions(JSON.parse(event.data));
    } catch (error) {
      console.error('Could not render acquisition update:', error);
    }
  };
  acquisitionStream.onerror = () => {
    $('acquisitionsStatus').textContent = 'Reconnecting to live download updates…';
  };
}
function stopAcquisitionStream() {
  if (!acquisitionStream) return;
  acquisitionStream.close();
  acquisitionStream = null;
}

$('refreshAcquisitions').addEventListener('click', loadAcquisitions);

function getRecommendations(data) {
  if (Array.isArray(data)) return data;
  return data.recommendations || [];
}

function getRecommendations(data) {
  if (Array.isArray(data)) return data;
  return Array.isArray(data.recommendations) ? data.recommendations : [];
}

function addTextElement(parent, tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  el.textContent = text ?? '';
  parent.append(el);
  // Some renderers know the year before creating the title. Preserve that
  // year in data-release-year, then attach the badge as soon as the h3 exists.
  if (String(tag).toLowerCase() === 'h3' && parent.dataset && parent.dataset.releaseYear) {
    const year = Number(parent.dataset.releaseYear);
    if (year >= 1900 && year <= 2100 && !el.querySelector('.album-year')) {
      addTextElement(el, 'span', 'album-year', String(year));
    }
  }
  return el;
}

const artworkLoaders = new WeakMap();
const bioLoaders = new WeakMap();
const artworkRequests = new Map();
const artistBioRequests = new Map();
const albumCardMetadata = new WeakMap();
let activeAlbumModal = null;

function cachedJSONRequest(cache, key, url) {
  if (!cache.has(key)) {
    const request = fetch(url)
      .then(response => response.ok ? response.json() : null)
      .then(data => {
        if (data === null) cache.delete(key);
        return data;
      })
      .catch(() => {
        cache.delete(key);
        return null;
      });
    cache.set(key, request);
  }
  return cache.get(key);
}
const artistBioObserver = 'IntersectionObserver' in window
  ? new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const load = bioLoaders.get(entry.target);
        if (load) load();
        artistBioObserver.unobserve(entry.target);
      }
    }, {rootMargin: '240px'})
  : null;
const artworkObserver = 'IntersectionObserver' in window
  ? new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const load = artworkLoaders.get(entry.target);
        if (load) load();
        artworkObserver.unobserve(entry.target);
      }
    }, {rootMargin: '220px'})
  : null;

function parseReleaseYear(value) {
  if (value === null || value === undefined || value === '') return null;
  const text = String(value).trim();
  const match = text.match(/^(\d{4})/);
  const year = Number(match ? match[1] : value);
  return Number.isInteger(year) && year >= 1900 && year <= 2100 ? year : null;
}

function firstReleaseYear(...values) {
  for (const value of values) {
    const year = parseReleaseYear(value);
    if (year !== null) return year;
  }
  return null;
}

function makeAlbumCardInteractive(card, artist, album, metadata = {}, fetchYear = true) {
  card.dataset.albumArtist = String(artist || '');
  card.dataset.albumTitle = String(album || '');
  albumCardMetadata.set(card, metadata && typeof metadata === 'object' ? metadata : {});
  card.setAttribute('tabindex', '0');
  card.setAttribute('role', 'button');
  card.setAttribute('aria-label', 'View details for ' + album + ' by ' + artist);
  const nested = metadata && typeof metadata.metadata === 'object' ? metadata.metadata : {};
  const year = firstReleaseYear(
    metadata.year, metadata.release_year, metadata.first_release_year,
    nested.year, nested.release_year, nested.first_release_year
  );
  if (year !== null) applyAlbumYear(card, year);
  else if (fetchYear && artist && album) {
    const cacheKey = String(artist).trim().toLocaleLowerCase() + '::' + String(album).trim().toLocaleLowerCase();
    const query = new URLSearchParams({artist: String(artist), album: String(album)});
    cachedJSONRequest(artworkRequests, cacheKey, '/api/album-year?' + query.toString())
      .then(data => { if (data && data.year) applyAlbumYear(card, data.year); })
      .catch(() => {});
  }
}

function ensureAlbumYearBadge(card) {
  const year = Number(card && card.dataset ? card.dataset.releaseYear : 0);
  const title = card && card.querySelector('h3');
  if (title && year >= 1900 && year <= 2100 && !title.querySelector('.album-year')) {
    addTextElement(title, 'span', 'album-year', String(year));
  }
}

function applyAlbumYear(card, value) {
  const year = parseReleaseYear(value);
  if (year === null) return;
  card.dataset.releaseYear = String(year);
  ensureAlbumYearBadge(card);
  const modalYear = $('albumModalYear');
  if (activeAlbumModal && activeAlbumModal.card === card && modalYear) modalYear.textContent = String(year);
}

function setAlbumPlatformLinks(artist, album) {
  const query = [artist, album].filter(Boolean).join(' ').trim();
  const encoded = encodeURIComponent(query);
  const links = [
    ['ListenBrainz', 'https://listenbrainz.org/search/?query=' + encoded, 'https://raw.githubusercontent.com/metabrainz/metabrainz-logos/master/logos/ListenBrainz/SVG/ListenBrainz_logo_icon.svg'],
    ['Apple Music', 'https://music.apple.com/search?term=' + encoded, 'https://cdn.simpleicons.org/applemusic/FA243C'],
    ['Spotify', 'https://open.spotify.com/search/' + encoded, 'https://cdn.simpleicons.org/spotify/1DB954'],
    ['Qobuz', 'https://www.qobuz.com/us-en/search/albums/' + encoded, 'https://community.qobuz.com/s/Qobuz_logo_black-l2kk.jpg'],
    ['Bandcamp', 'https://bandcamp.com/search?q=' + encoded, 'https://cdn.simpleicons.org/bandcamp/1DA0C3']
  ];
  const nav = $('albumModalPlatformLinks');
  nav.replaceChildren();
  for (const [label, href, iconUrl] of links) {
    const link = document.createElement('a');
    link.href = href;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.title = 'Search ' + artist + ' ' + album + ' on ' + label;
    link.setAttribute('aria-label', 'Search ' + artist + ' ' + album + ' on ' + label);
    const icon = document.createElement('img');
    icon.src = iconUrl;
    icon.alt = '';
    icon.loading = 'lazy';
    icon.width = 18;
    icon.height = 18;
    icon.onerror = () => {
      icon.remove();
      link.textContent = label.slice(0, 2);
      link.classList.add('platform-icon-fallback');
    };
    link.append(icon);
    nav.append(link);
  }
}
function closeAlbumModal() {
  $('albumModalBackdrop').hidden = true;
  activeAlbumModal = null;
}

async function openAlbumModal(card) {
  const artist = card.dataset.albumArtist || 'Unknown artist';
  const album = card.dataset.albumTitle || 'Unknown album';
  const metadata = albumCardMetadata.get(card) || {};
  const backdrop = $('albumModalBackdrop');
  const artwork = $('albumModalArtwork');
  const tracklist = $('albumModalTracklist');
  const get = $('albumModalGet');
  activeAlbumModal = {card, artist, album, metadata};
  $('albumModalTitle').textContent = album;
  $('albumModalArtist').textContent = artist;
  $('albumModalYear').textContent = String(firstReleaseYear(metadata.year, metadata.release_year, metadata.first_release_year, card.dataset.releaseYear) || '');
  setAlbumPlatformLinks(artist, album);
  $('albumModalStatus').textContent = 'Loading artwork and tracklist…';
  tracklist.replaceChildren();
  artwork.removeAttribute('src');
  get.disabled = false;
  get.classList.remove('requested');
  get.textContent = 'get';
  get.onclick = () => searchAlbum(artist, album, metadata, get);
  backdrop.hidden = false;
  $('albumModalClose').focus();
  try {
    const query = new URLSearchParams({artist, album});
    const [details, art] = await Promise.all([
      requestJSON('/api/album-details?' + query.toString()),
      requestJSON('/api/artwork?' + query.toString()).catch(() => null)
    ]);
    if (!activeAlbumModal || activeAlbumModal.card !== card) return;
    const artworkUrl = details.artwork_url || (art && art.artwork_url);
    if (artworkUrl) artwork.src = artworkUrl;
    const year = details.year || (art && art.year) || metadata.year || metadata.release_year || metadata.first_release_year || card.dataset.releaseYear;
    if (year) {
      $('albumModalYear').textContent = String(year);
      applyAlbumYear(card, year);
    }
    const tracks = Array.isArray(details.tracks) ? details.tracks : [];
    if (tracks.length) {
      tracks.forEach((track, index) => {
        const row = document.createElement('li');
        const number = document.createElement('span');
        number.className = 'track-number';
        number.textContent = String(track.track_number || index + 1).padStart(2, '0');
        const title = document.createElement('span');
        title.textContent = track.title || 'Untitled track';
        const duration = document.createElement('span');
        duration.className = 'track-duration';
        const seconds = Number(track.duration_seconds);
        duration.textContent = Number.isFinite(seconds) && seconds > 0 ? Math.floor(seconds / 60) + ':' + String(Math.floor(seconds % 60)).padStart(2, '0') : '';
        row.append(number, title, duration);
        tracklist.append(row);
      });
      $('albumModalStatus').textContent = tracks.length + ' tracks';
    } else {
      $('albumModalStatus').textContent = details.message || 'Tracklist unavailable for this release.';
    }
  } catch (error) {
    if (activeAlbumModal && activeAlbumModal.card === card) $('albumModalStatus').textContent = 'Could not load tracklist: ' + error.message;
  }
}

document.addEventListener('click', event => {
  const card = event.target.closest && event.target.closest('.card[data-album-title]');
  if (!card || event.target.closest('button, a, input, select, textarea')) return;
  openAlbumModal(card);
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && !$('albumModalBackdrop').hidden) closeAlbumModal();
  if ((event.key === 'Enter' || event.key === ' ') && event.target.matches('.card[data-album-title]')) {
    event.preventDefault(); openAlbumModal(event.target);
  }
});
$('albumModalClose').addEventListener('click', closeAlbumModal);
$('albumModalBackdrop').addEventListener('click', event => {
  if (event.target === $('albumModalBackdrop')) closeAlbumModal();
});

async function loadDashboardPicks() {
  const target = $('dashboardCarousel');
  const status = $('dashboardPicksStatus');
  target.replaceChildren();
  status.textContent = 'Picking ten albums across your discovery lists…';
  try {
    const data = await requestJSON('/api/dashboard-picks?count=10&nonce=' + Date.now());
    const items = (data.items || []).filter(isAlbumRecommendation);
    for (const item of items) {
      const artist = item.artist || item.album_artist || 'Unknown artist';
      const album = item.album || item.title || 'Untitled album';
      const card = document.createElement('article');
      card.className = 'card editorial-card';
      makeAlbumCardInteractive(card, artist, album, item);
      attachArtwork(card, artist, album);
      addTextElement(card, 'p', 'card-category', item.dashboard_category || 'Discovery');
      const title = document.createElement('h3');
      title.append(document.createTextNode(album));
      const year = firstReleaseYear(item.year, item.release_year, item.first_release_year, card.dataset.releaseYear);
      if (year !== null) addTextElement(title, 'span', 'album-year', String(year));
      card.append(title);
      ensureAlbumYearBadge(card);
      addTextElement(card, 'p', 'card-artist', artist);
      const art = card.querySelector('.card-art');
      const get = document.createElement('button');
      get.className = 'get-album';
      get.textContent = 'get';
      get.title = 'Get this album';
      get.setAttribute('aria-label', 'Get ' + album);
      get.addEventListener('click', () => searchAlbum(artist, album, item, get));
      art.append(get);
      target.append(card);
    }
    status.textContent = items.length
      ? `${items.length} randomly selected albums from ${data.pool_size || items.length} available suggestions.`
      : 'No suggestions yet. Open a discovery page and refresh its list first.';
  } catch (error) {
    status.textContent = error.message;
  }
}

$('shuffleDashboard').addEventListener('click', loadDashboardPicks);

function attachArtwork(card, artist, album) {
  const art = document.createElement('div');
  art.className = 'card-art';
  art.setAttribute('aria-label', 'Album artwork and acquisition actions');

  const placeholder = document.createElement('div');
  placeholder.className = 'card-art-placeholder';
  placeholder.textContent = 'COVER NOT FOUND';

  const image = document.createElement('img');
  image.alt = '';
  image.loading = 'lazy';
  image.decoding = 'async';
  art.append(image, placeholder);
  card.append(art);

  const loadArtwork = () => {
    if (art.dataset.requested) return;
    art.dataset.requested = 'true';
    const query = new URLSearchParams({artist: artist || '', album: album || ''});
    const cacheKey = (artist || '').trim().toLocaleLowerCase() + '::' + (album || '').trim().toLocaleLowerCase();
    cachedJSONRequest(artworkRequests, cacheKey, '/api/artwork?' + query.toString())
      .then(data => {
        if (!data) return;
        if (data.year) applyAlbumYear(card, data.year);
        if (!data.artwork_url) return;
        image.onload = () => art.classList.add('has-image');
        image.onerror = () => art.classList.remove('has-image');
        image.fetchPriority = art.getBoundingClientRect().top < window.innerHeight ? 'high' : 'auto';
        image.src = data.artwork_url;
      })
      .catch(() => {});
  };

  artworkLoaders.set(art, loadArtwork);
  if (artworkObserver) artworkObserver.observe(art);
  else loadArtwork();
}

let allRecommendations = [];
let recommendationData = null;

function renderRecommendations(data) {
  recommendationData = data;
  allRecommendations = getRecommendations(data).filter(isAlbumRecommendation);
  $('recommendationDebug').textContent = pretty(data);
  applyRecommendationFilters();
}

function applyRecommendationFilters() {
  const cards = $('recommendationCards');
  cards.replaceChildren();

  const query = $('recommendationSearch').value.trim().toLocaleLowerCase();
  const category = $('categoryFilter').value;
  const sort = $('recommendationSort').value;

  const filtered = allRecommendations.filter(item => {
    const searchable = [
      item.artist,
      item.album_artist,
      item.album,
      item.title,
      ...(Array.isArray(item.genres) ? item.genres : []),
      ...(Array.isArray(item.genre_families) ? item.genre_families : []),
      item.diversity_style,
      item.discovery_category
    ].filter(Boolean).join(' ').toLocaleLowerCase();

    const itemCategory = item.discovery_category || 'unclassified';

    const dismissed = new Set(JSON.parse(localStorage.getItem('navidrome-dismissed-recommendations') || '[]'));
    const key = [item.artist || item.album_artist || '', item.album || item.title || item.name || '']
      .map(value => String(value).trim().toLocaleLowerCase()).join('::');
    return !dismissed.has(key) && (!query || searchable.includes(query)) &&
      (category === 'all' || itemCategory === category);
  });

  const numeric = value =>
    value !== null && value !== undefined && value !== '' &&
    Number.isFinite(Number(value)) ? Number(value) : null;

  if (sort === 'popularity') {
    filtered.sort((a, b) =>
      (numeric(b.lastfm_listeners) ?? -1) -
      (numeric(a.lastfm_listeners) ?? -1));
  } else if (sort === 'score') {
    filtered.sort((a, b) =>
      (numeric(b.discovery_score) ?? -Infinity) -
      (numeric(a.discovery_score) ?? -Infinity));
  } else if (sort === 'artist') {
    filtered.sort((a, b) =>
      (a.artist || a.album_artist || '').localeCompare(
        b.artist || b.album_artist || ''
      ));
  }

  $('recommendationCount').textContent =
    `Showing ${filtered.length} of ${allRecommendations.length} recommendations`;

  for (const item of filtered) {
    const card = document.createElement('article');
    card.className = 'card editorial-card';
    const artist = item.artist || item.album_artist || '';
    const album = item.album || item.title || item.name || '';
    makeAlbumCardInteractive(card, artist, album, item);
    attachArtwork(card, artist, album);
    const artContainer = card.querySelector('.card-art');
    const getButton = document.createElement('button');
    getButton.className = 'get-album';
    getButton.textContent = 'get';
    getButton.title = 'Get this album';
    getButton.setAttribute('aria-label', 'Get ' + album);
    getButton.addEventListener('click', () => searchAlbum(artist, album, item, getButton));
    artContainer.append(getButton);
    const dismissButton = document.createElement('button');
    dismissButton.className = 'deep-dive-dismiss';
    dismissButton.textContent = '×';
    dismissButton.title = 'Not for me';
    dismissButton.setAttribute('aria-label', 'Not for me');
    dismissButton.addEventListener('click', () => {
      const key = [artist, album].map(value => String(value).trim().toLocaleLowerCase()).join('::');
      const dismissed = new Set(JSON.parse(localStorage.getItem('navidrome-dismissed-recommendations') || '[]'));
      dismissed.add(key);
      localStorage.setItem('navidrome-dismissed-recommendations', JSON.stringify([...dismissed]));
      applyRecommendationFilters();
    });
    artContainer.append(dismissButton);

    const categoryName = (item.discovery_category || 'Unclassified')
      .replaceAll('_', ' ');

    addTextElement(card, 'p', 'card-category', categoryName);

    const title = document.createElement('h3');
    title.append(document.createTextNode(item.album || item.title || item.name || 'Untitled album'));
    const year = firstReleaseYear(item.year, item.release_year, item.first_release_year, card.dataset.releaseYear);
    if (year !== null) addTextElement(title, 'span', 'album-year', String(year));
    card.append(title);
    ensureAlbumYearBadge(card);

    addTextElement(
      card, 'p', 'card-artist',
      item.artist || item.album_artist || 'Unknown artist'
    );

    const genres = [
      ...(Array.isArray(item.genres) ? item.genres : []),
      ...(Array.isArray(item.genre_families) ? item.genre_families : [])
    ];

    if (genres.length) {
      const genreList = document.createElement('div');
      genreList.className = 'genre-list';

      for (const genre of [...new Set(genres)]) {
        addTextElement(genreList, 'span', 'genre-tag', genre);
      }

      card.append(genreList);
    }

    if (item.diversity_style) {
      addTextElement(
        card, 'p', 'card-meta',
        'Style: ' + item.diversity_style.replaceAll('_', ' ')
      );
    }

    const listeners = numeric(item.lastfm_listeners);
    if (listeners !== null) {
      addTextElement(
        card, 'p', 'card-meta',
        'Last.fm artist listeners: ' + listeners.toLocaleString()
      );
    }

    const score = numeric(item.discovery_score);
    if (score !== null) {
      addTextElement(
        card, 'p', 'card-meta',
        'Discovery score: ' + score.toFixed(4)
      );
    }

    if (item.discovery_source) {
      addTextElement(
        card, 'p', 'card-source',
        'Source: ' + item.discovery_source.replaceAll('_', ' ')
      );
    }

    cards.append(card);
  }

  if (!filtered.length) {
    addTextElement(
      cards, 'p', '',
      allRecommendations.length
        ? 'No recommendations match these filters. Try another search or category.'
        : 'No recommendations returned. Generate recommendations to try again.'
    );
  }
}

$('recommendationSearch').addEventListener('input', applyRecommendationFilters);
$('categoryFilter').addEventListener('change', applyRecommendationFilters);
$('recommendationSort').addEventListener('change', applyRecommendationFilters);

$('checkConnection').addEventListener('click', async () => {
  $('connection').textContent = 'Testing Navidrome…';
  await testServiceConnection('/api/settings/navidrome/test', 'connection');
});

$('loadRecommendations').addEventListener('click', async () => {
  const button = $('loadRecommendations');
  button.disabled = true;
  button.textContent = 'Generating…';
  $('recommendationCards').replaceChildren();
  $('recommendationDebug').textContent = '';
  try {
    const data = await requestJSON(
      '/api/recommendations?count=' + encodeURIComponent($('count').value));
    renderRecommendations(data);
  } catch (error) {
    $('recommendationDebug').textContent = error.message;
  } finally {
    button.disabled = false;
    button.textContent = 'Generate recommendations';
  }
});

const discoveryViews = {
  personal: ['personalCards','personalStatus'],
  classics: ['classicsCards','classicsStatus'],
  artist_deep_dive: ['artistDeepDiveCards','artistDeepDiveStatus'],
  new_releases: ['newReleasesCards','newReleasesStatus']
};

const qualityOptions = [
  ['mp3_320','MP3 320 kbps'],
  ['mp3_193_319','MP3 193–319 kbps'],
  ['mp3_192','MP3 192 kbps'],
  ['flac_cd','FLAC (CD quality preferred)']
];

async function sendJSON(url, method='POST', body={}) {
  const response = await fetch(url, {
    method,
    headers: {'Content-Type':'application/json'},
    body: method === 'GET' ? undefined : JSON.stringify(body)
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || data.message || `HTTP ${response.status}`);
  return data;
}

function discoveryStatus(name, message) {
  $(discoveryViews[name][1]).textContent = message;
}

function deepDiveGenre(item) {
  const families = Array.isArray(item.genre_families) ? item.genre_families : [];
  const family = families.find(value => String(value || '').trim());
  if (family) return String(family).replaceAll('_', '-').toLocaleLowerCase();
  const tags = Array.isArray(item.genres) ? item.genres : [];
  const text = tags.join(' ').toLocaleLowerCase();
  const rules = [
    ['jazz', /jazz|bebop|swing/],
    ['african', /african|afrobeat|afropop|highlife|soukous|malian|tuareg|desert blues|ethiopian/],
    ['alternative', /alternative|indie rock|post-punk|art rock|garage rock|shoegaze/],
    ['brazilian', /brazilian|samba|bossa nova|\bmpb\b|tropic[aá]lia/],
    ['hip-hop', /hip.?hop|rap/],
    ['rnb-soul', /r&b|rnb|neo-soul|soul/],
    ['electronic', /electronic|electronica|house|techno|trip.?hop|downtempo/],
    ['funk', /funk/],
    ['north-african-middle-eastern', /arabic|ra[iï]|maghreb|north african|algerian|moroccan|tunisian|gnawa|chaabi|middle eastern/],
    ['rock', /rock|punk|metal|grunge/],
    ['pop', /pop/],
  ];
  const match = rules.find(([, pattern]) => pattern.test(text));
  return match ? match[0] : 'other';
}

function genreRowLabel(key) {
  const labels = {
    'jazz': 'Jazz', 'african': 'African Music', 'alternative': 'Alternative',
    'brazilian': 'Brazilian Music', 'hip-hop': 'Hip-Hop', 'rnb-soul': 'R&B / Soul',
    'electronic': 'Electronic', 'funk': 'Funk',
    'north-african-middle-eastern': 'North African & Middle Eastern',
    'north-african': 'North African', 'bossa-nova-brazilian': 'Brazilian / Bossa Nova',
    'rock': 'Rock', 'pop': 'Pop', 'other': 'Other Discoveries',
  };
  return labels[key] || key.replaceAll('-', ' ').replace(/\b\w/g, letter => letter.toUpperCase());
}

async function loadDiscovery(name, options = {}) {
  discoveryStatus(name, options.rotate ? 'Rotating suggestions…' : 'Loading…');
  const target = $(discoveryViews[name][0]);
  target.replaceChildren();
  target.classList.toggle('deep-dive-rows', name === 'artist_deep_dive');
  const destinationByItem = new Map();

  try {
    const poolCount = name === 'artist_deep_dive' ? 150 : name === 'classics' ? 100 : 30;
    const data = await requestJSON(`/api/discovery/${name}?count=${poolCount}&nonce=${Date.now()}`);
    let items = data.items || data.recommendations || [];
    if (name !== 'for_me') items = items.filter(isAlbumRecommendation);
    if ((name === 'classics' || name === 'artist_deep_dive') && options.rotate) {
      items = [...items].sort(() => Math.random() - 0.5);
    }
    if (name === 'classics') {
      if (items.length > 30) items = items.slice(0, 30);
      const artistCounts = new Map();
      items = items.filter(item => {
        const key = String(item.artist || item.album_artist || '').trim().toLocaleLowerCase();
        const count = artistCounts.get(key) || 0;
        if (count >= 3) return false;
        artistCounts.set(key, count + 1);
        return true;
      });
    }
    if (name !== 'for_me' && !data.generated_at && !items.length && !autoRefreshStarted.has(name)) {
      autoRefreshStarted.add(name);
      discoveryStatus(name, 'Building the first list in the background…');
      try {
        await sendJSON(`/api/discovery/${name}/refresh`, 'POST', {count: 20});
        pollDiscoveryUntilReady(name);
      } catch (error) {
        autoRefreshStarted.delete(name);
        discoveryStatus(name, error.message);
      }
    }

    if (name === 'artist_deep_dive') {
      const grouped = new Map();
      const artistsByGenre = new Map();
      for (const item of items) {
        const key = deepDiveGenre(item);
        const artistKey = String(item.artist || item.album_artist || '').trim().toLocaleLowerCase();
        if (!grouped.has(key)) {
          grouped.set(key, []);
          artistsByGenre.set(key, new Set());
        }
        const seenArtists = artistsByGenre.get(key);
        if (seenArtists.has(artistKey)) continue;
        seenArtists.add(artistKey);
        grouped.get(key).push(item);
      }
      // Show no more than 15 albums per genre row. Randomize the larger
      // saved pool first so Load albums can rotate choices without waiting
      // for expensive upstream metadata requests.
      for (const [genre, genreItems] of grouped) {
        if (genreItems.length > 15) {
          grouped.set(genre, genreItems.slice(0, 15));
        }
      }
      const orderedGroups = [...grouped.entries()].sort((a, b) =>
        (b[1].length - a[1].length) || a[0].localeCompare(b[0]));
      items = orderedGroups.flatMap(([, genreItems]) => genreItems);
      for (const [genre, genreItems] of orderedGroups) {
        const row = document.createElement('section');
        row.className = 'genre-row';
        const heading = document.createElement('div');
        heading.className = 'genre-row-heading';
        addTextElement(heading, 'h3', '', genreRowLabel(genre));
        addTextElement(heading, 'span', 'genre-row-count', `${genreItems.length} albums`);
        const arrows = document.createElement('div');
        arrows.className = 'genre-row-arrows';
        const track = document.createElement('div');
        track.className = 'genre-row-track';
        for (const [symbol, direction] of [['<', -1], ['>', 1]]) {
          const arrow = document.createElement('button');
          arrow.className = 'genre-row-arrow';
          arrow.type = 'button';
          arrow.textContent = symbol;
          arrow.setAttribute('aria-label', direction < 0 ? 'Scroll albums left' : 'Scroll albums right');
          arrow.addEventListener('click', () => track.scrollBy({left: direction * Math.max(250, track.clientWidth * 0.8), behavior: 'smooth'}));
          arrows.append(arrow);
        }
        heading.append(arrows);
        row.append(heading, track);
        target.append(row);
        for (const item of genreItems) destinationByItem.set(item, track);
      }
    }

    if (items.length || data.generated_at) {
      discoveryStatus(name, `${items.length} item(s)`);
    }

    for (const item of items) {
      const artist = item.artist || item.album_artist || 'Unknown artist';
      const album = item.album || item.title || 'Untitled album';
      const isDeepDive = name === 'artist_deep_dive';
      const card = document.createElement('article');
      card.className = 'card editorial-card';
      makeAlbumCardInteractive(card, artist, album, item);
      attachArtwork(card, artist, album);

      addTextElement(card, 'p', 'card-category',
        (item.discovery_type || item.discovery_category || name).replaceAll('_',' '));
      const title = document.createElement('h3');
      title.append(document.createTextNode(album));
      const year = firstReleaseYear(item.year, item.release_year, item.first_release_year, card.dataset.releaseYear);
      if (year !== null) addTextElement(title, 'span', 'album-year', String(year));
      card.append(title);
      ensureAlbumYearBadge(card);
      addTextElement(card, 'p', 'card-artist', artist);

      const needsBio = isDeepDive ||
        /Genre tags connect this artist to your established musical interests/i.test(item.reason || '');
      if (needsBio) {
        const bio = addTextElement(card, 'p', 'artist-bio', '');
        bio.hidden = true;
        const loadBio = () => {
          if (card.dataset.bioRequested) return;
          card.dataset.bioRequested = 'true';
          const bioKey = artist.trim().toLocaleLowerCase();
          cachedJSONRequest(artistBioRequests, bioKey, '/api/artist-bio?artist=' + encodeURIComponent(artist))
            .then(result => {
              if (!result || !result.bio) return;
              bio.textContent = result.bio;
              bio.hidden = false;
            })
            .catch(() => {});
        };
        bioLoaders.set(card, loadBio);
        if (artistBioObserver) artistBioObserver.observe(card);
        else loadBio();
      }

      if (item.reason && !needsBio) addTextElement(card, 'p', 'card-meta', item.reason);
      if (item.anchor_artist) addTextElement(card, 'p', 'card-meta',
        `Similar to ${item.anchor_artist}`);
      if (item.lastfm_playcount) addTextElement(card, 'p', 'card-meta',
        `Last.fm playcount: ${Number(item.lastfm_playcount).toLocaleString()}`);

        const actions = document.createElement('div');
      actions.className = 'card-actions';

      const button = (label, callback, className = '') => {
        const b = document.createElement('button');
        b.textContent = label;
        if (className) b.className = className;
        b.addEventListener('click', callback);
        actions.append(b);
      };

      const artContainer = card.querySelector('.card-art');
      const getButton = document.createElement('button');
      getButton.className = 'get-album';
      getButton.textContent = 'get';
      getButton.title = 'Get this album';
      getButton.setAttribute('aria-label', 'Get ' + album);
      getButton.addEventListener('click', () => searchAlbum(artist, album, item, getButton));
      artContainer.append(getButton);

      const notForMe = document.createElement('button');
      notForMe.className = 'deep-dive-dismiss';
      notForMe.textContent = '×';
      notForMe.title = 'Not for me';
      notForMe.setAttribute('aria-label', notForMe.title);
      notForMe.addEventListener('click', () => sendFeedback('dismiss', artist, album, item, name));
      artContainer.append(notForMe);

      if (name !== 'artist_deep_dive') {
        button('Dismiss artist',
          () => sendFeedback('dismiss_artist', artist, album, item, name));
      }

      card.append(actions);
      (destinationByItem.get(item) || target).append(card);
    }

    if (!items.length && !autoRefreshStarted.has(name)) addTextElement(target, 'p', '',
      'No results. Try refreshing this list.');
  } catch (error) {
    discoveryStatus(name, error.message);
  }
}

async function sendFeedback(action, artist, album, metadata, listName) {
  try {
    await sendJSON('/api/discovery/feedback', 'POST',
      {action, artist, album, metadata});
    await loadDiscovery(listName);
  } catch (error) {
    discoveryStatus(listName, error.message);
  }
}

async function refreshDiscovery(name) {
  discoveryStatus(name, 'Starting a fresh discovery pass…');
  try {
    const before = await requestJSON(`/api/discovery/${name}?count=1&nonce=${Date.now()}`);
    const previous = Number(before.generated_at || 0);
    const started = await sendJSON(`/api/discovery/${name}/refresh`, 'POST', {count:20});
    if (started.status === 'already_running') {
      discoveryStatus(name, 'A refresh is already running; waiting for its new results…');
    } else {
      discoveryStatus(name, 'Generating fresh suggestions. This may take a few minutes…');
    }
    const deadline = Date.now() + 5 * 60 * 1000;
    while (Date.now() < deadline) {
      await new Promise(resolve => setTimeout(resolve, 2500));
      const current = await requestJSON(`/api/discovery/${name}?count=1&nonce=${Date.now()}`);
      const stamp = Number(current.generated_at || 0);
      if (stamp > previous) {
        await loadDiscovery(name, {rotate: true});
        if ($('dashboard').classList.contains('hidden') === false) loadDashboardPicks();
        return;
      }
    }
    discoveryStatus(name, 'The refresh is still running. Try Load albums again in a little while.');
  } catch (error) {
    discoveryStatus(name, error.message);
  }
}

document.querySelectorAll('[data-load-discovery]').forEach(button =>
  button.addEventListener('click', async () => {
    const name = button.dataset.loadDiscovery;
    if (name === 'classics' || name === 'artist_deep_dive') {
      await loadDiscovery(name, {rotate: true});
    } else {
      await loadDiscovery(name);
    }
  }));

document.querySelectorAll('[data-refresh-discovery]').forEach(button =>
  button.addEventListener('click', () => refreshDiscovery(button.dataset.refreshDiscovery)));

const autoRefreshStarted = new Set();
const autoRefreshPolls = new Map();

async function pollDiscoveryUntilReady(name) {
  const attempts = autoRefreshPolls.get(name) || 0;
  if (attempts >= 60) {
    discoveryStatus(name, 'Still generating in the background. You can keep browsing; reload this list later.');
    autoRefreshStarted.delete(name);
    autoRefreshPolls.delete(name);
    return;
  }
  autoRefreshPolls.set(name, attempts + 1);
  setTimeout(async () => {
    try {
      const data = await requestJSON(`/api/discovery/${name}?count=${name === 'artist_deep_dive' ? 150 : 30}`);
      if (data.generated_at) {
        autoRefreshStarted.delete(name);
        autoRefreshPolls.delete(name);
        await loadDiscovery(name, {rotate: name === 'classics' || name === 'artist_deep_dive'});
        loadDashboardPicks();
      } else {
        await pollDiscoveryUntilReady(name);
      }
    } catch (error) {
      discoveryStatus(name, error.message);
    }
  }, 5000);
}

async function searchAlbum(artist, album, metadata, button = null) {
  if (button && button.disabled) return;
  if (button) {
    button.disabled = true;
    button.classList.add('requested');
    button.textContent = 'requested';
    button.title = 'Acquisition requested';
    button.setAttribute('aria-label', 'Acquisition requested for ' + album);
  }
  try {
    const data = await sendJSON('/api/acquire', 'POST',
      {artist, album, metadata, auto_queue:true});
    const statusTarget = document.querySelector('.page:not(.hidden) .status');
    if (statusTarget && data.message) statusTarget.textContent = data.message;
    // Keep the user on the current page. Acquisition cards are shown only in the Acquisitions view.
    await loadAcquisitions();
  } catch (error) {
    if (button) {
      button.disabled = false;
      button.classList.remove('requested');
      button.textContent = 'get';
      button.title = 'Get this album';
      button.setAttribute('aria-label', 'Get ' + album);
    }
    const statusTarget = document.querySelector('.page:not(.hidden) .status');
    if (statusTarget) statusTarget.textContent = error.message;
  }
}
async function loadNavidromeSettings() {
  try {
    const data = await requestJSON('/api/settings/navidrome');
    $('navidromeUrl').value = data.navidrome_url || '';
    $('navidromeUser').value = data.username || '';
    $('musicLibraryPath').value = data.music_library_path || '';
    $('navidromePassword').value = '';
    $('navidromeStatus').textContent = data.password_configured ? 'Password configured.' : 'Password not configured.';
  } catch (error) { $('navidromeStatus').textContent = error.message; }
}
$('saveNavidrome').addEventListener('click', async () => {
  try {
    const result = await sendJSON('/api/settings/navidrome', 'PUT', {
      navidrome_url: $('navidromeUrl').value.trim(),
      username: $('navidromeUser').value.trim(),
      password: $('navidromePassword').value,
      music_library_path: $('musicLibraryPath').value.trim()
    });
    $('navidromePassword').value = '';
    $('navidromeStatus').textContent = result.message || 'Settings saved.';
    await loadNavidromeSettings();
  } catch (error) { $('navidromeStatus').textContent = error.message; }
});

async function loadLastfmSettings() {
  try {
    const data = await requestJSON('/api/settings/lastfm');
    $('lastfmApiKey').value = '';
    $('lastfmStatus').textContent = data.api_key_configured ? 'API key configured.' : 'API key not configured (optional).';
  } catch (error) { $('lastfmStatus').textContent = error.message; }
}
$('saveLastfm').addEventListener('click', async () => {
  try {
    const result = await sendJSON('/api/settings/lastfm', 'PUT', {api_key: $('lastfmApiKey').value});
    $('lastfmApiKey').value = '';
    $('lastfmStatus').textContent = result.message || 'Settings saved.';
    await loadLastfmSettings();
  } catch (error) { $('lastfmStatus').textContent = error.message; }
});

async function loadListenbrainzSettings() {
  try {
    const data = await requestJSON('/api/settings/listenbrainz');
    $('listenbrainzUsername').value = data.username || '';
    $('listenbrainzStatus').textContent = 'Public profile username.';
  } catch (error) { $('listenbrainzStatus').textContent = error.message; }
}
$('saveListenbrainz').addEventListener('click', async () => {
  try {
    const result = await sendJSON('/api/settings/listenbrainz', 'PUT', {username: $('listenbrainzUsername').value.trim()});
    $('listenbrainzStatus').textContent = result.message || 'Settings saved.';
  } catch (error) { $('listenbrainzStatus').textContent = error.message; }
});

async function testServiceConnection(endpoint, statusId) {
  const status = $(statusId);
  status.textContent = 'Testing connection…';
  status.className = 'status';
  try {
    const data = await sendJSON(endpoint, 'POST');
    status.textContent = data.message || (data.ok ? 'Connection successful.' : 'Test failed.');
    status.className = data.ok ? 'status ok' : 'status error';
  } catch (error) {
    status.textContent = error.message;
    status.className = 'status error';
  }
}
$('testLastfm').addEventListener('click', () => testServiceConnection('/api/settings/lastfm/test', 'lastfmStatus'));
$('testListenbrainz').addEventListener('click', () => testServiceConnection('/api/settings/listenbrainz/test', 'listenbrainzStatus'));

document.querySelectorAll('[data-settings-tab]').forEach(button => {
  button.addEventListener('click', () => {
    const name = button.dataset.settingsTab;
    document.querySelectorAll('[data-settings-tab]').forEach(tab => {
      const active = tab === button;
      tab.classList.toggle('active', active);
      tab.setAttribute('aria-selected', String(active));
    });
    const panels = {navidrome: 'settingsNavidrome', slskd: 'settingsSlskd', lastfm: 'settingsLastfm', listenbrainz: 'settingsListenbrainz'};
    document.querySelectorAll('.settings-tab-panel').forEach(panel => { panel.hidden = panel.id !== panels[name]; });
  });
});

async function loadSlskdSettings() {
  try {
    const data = await requestJSON('/api/settings/slskd');
    $('slskdUrl').value = data.slskd_url || '';
    $('slskdDownloadsPath').value = data.slskd_downloads_path || '';

    document.querySelectorAll('.quality-priority').forEach((select, index) => {
      select.replaceChildren();
      for (const [value, label] of qualityOptions) {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = label;
        select.append(option);
      }
      select.value = (data.quality_priority || qualityOptions.map(x=>x[0]))[index];
    });

    $('slskdStatus').textContent =
      `API key ${data.api_key_configured ? 'configured' : 'not configured'}.`;
  } catch (error) {
    $('slskdStatus').textContent = error.message;
  }
}

$('saveSlskd').addEventListener('click', async () => {
  const priorities = [...document.querySelectorAll('.quality-priority')].map(s=>s.value);
  if (new Set(priorities).size !== 4) {
    $('slskdStatus').textContent = 'Choose four different quality preferences.';
    return;
  }

  const payload = {
    slskd_url: $('slskdUrl').value.trim(),
    slskd_downloads_path: $('slskdDownloadsPath').value.trim(),
    quality_priority: priorities
  };
  if ($('slskdApiKey').value) payload.api_key = $('slskdApiKey').value;

  try {
    await sendJSON('/api/settings/slskd', 'PUT', payload);
    $('slskdApiKey').value = '';
    $('slskdStatus').textContent = 'Settings saved.';
    await loadSlskdSettings();
  } catch (error) {
    $('slskdStatus').textContent = error.message;
  }
});

$('testSlskd').addEventListener('click', async () => {
  $('slskdStatus').textContent = 'Testing connection…';
  try {
    const data = await sendJSON('/api/settings/slskd/test');
    $('slskdStatus').textContent = data.message || (data.ok ? 'Connection successful.' : 'Test failed.');
  } catch (error) {
    $('slskdStatus').textContent = error.message;
  }
});


// Populate only the visible dashboard on startup. Other pages load on first visit
// so their API requests don't compete with the page the user is currently viewing.
loadDashboardPicks();
</script>
</body>
</html>
"""
