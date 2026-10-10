import json
from html import escape
from time import monotonic, sleep
from urllib.parse import urlencode
from urllib.request import urlopen

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

import navidrome_server as librarian


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


# Cache successful listening profiles for five minutes.
_PROFILE_CACHE_TTL = 300
_profile_cache = {}


@app.get("/api/profile")
def listening_profile(days: int = 30):
    if not 1 <= days <= 365:
        raise HTTPException(
            status_code=400,
            detail="days must be between 1 and 365",
        )

    now = monotonic()
    cached = _profile_cache.get(days)

    if cached and now - cached["time"] < _PROFILE_CACHE_TTL:
        return cached["data"]

    try:
        data = parse_result(
            librarian.recent_listening_profile(days=days)
        )

        # Do not cache error responses returned by the MCP function.
        if not (isinstance(data, dict) and data.get("error")):
            _profile_cache[days] = {
                "time": monotonic(),
                "data": data,
            }

        return data
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Could not retrieve the listening profile.",
        )


@app.get("/api/recommendations")
def recommendations(count: int = 10):
    if not 1 <= count <= 30:
        raise HTTPException(
            status_code=400,
            detail="count must be between 1 and 30",
        )

    try:
        return parse_result(
            librarian.recommend_new_music(count=count)
        )
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Could not generate recommendations.",
        )



@app.get("/api/discovery/{list_name}")
def discovery_list(list_name: str, count: int = 30):
    allowed = {"personal", "for_me", "classics", "artist_deep_dive"}
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
    if list_name not in {"personal", "classics", "artist_deep_dive", "all"}:
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


@app.get("/api/acquisitions/stream")
def acquisition_status_stream():
    def events():
        while True:
            try:
                payload = parse_result(librarian.discovery_get_acquisition_status())
                yield "data: " + json.dumps(payload, ensure_ascii=False) + "\\n\\n"
            except Exception:
                yield "event: error\\ndata: {}\\n\\n"
            sleep(1)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
        ))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not queue the selected candidate.")


# Artwork is optional presentation metadata; discovery works without it.
_ARTWORK_CACHE_TTL = 6 * 60 * 60
_ARTWORK_NEGATIVE_CACHE_TTL = 5 * 60
_artwork_cache = {}


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
        with urlopen(endpoint, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
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
            if match_score(match) >= 5:
                artwork = match.get("cover_xl") or match.get("cover_big") or match.get("cover_medium")
                if artwork:
                    result = {
                        "artwork_url": artwork.replace("http://", "https://", 1),
                        "image_kind": "album",
                        "source": "Deezer",
                        "matched_artist": (match.get("artist") or {}).get("name"),
                        "matched_album": match.get("title"),
                    }

        # If the album is not in the catalog, use a matching artist photo instead.
        if not result["artwork_url"] and artist:
            artist_query = urlencode({"q": artist, "limit": 8})
            with urlopen("https://api.deezer.com/search/artist?" + artist_query, timeout=3) as response:
                artist_payload = json.loads(response.read().decode("utf-8"))
            artists = artist_payload.get("data") or []
            exact = next(
                (item for item in artists if str(item.get("name") or "").casefold() == artist.casefold()),
                None,
            )
            if exact:
                photo = exact.get("picture_xl") or exact.get("picture_big") or exact.get("picture_medium")
                if photo:
                    result = {
                        "artwork_url": photo.replace("http://", "https://", 1),
                        "image_kind": "artist",
                        "source": "Deezer",
                        "matched_artist": exact.get("name"),
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
nav button.active { color: var(--text); background: #2b2d29; box-shadow: inset 3px 0 var(--yellow); }
nav button.active::after { content: ""; position: absolute; top: 9px; right: 10px; width: 5px; height: 5px; background: var(--red); border-radius: 50%; }
.panel { min-width: 0; margin: 0 0 36px; padding: 0; background: transparent; border: 0; border-radius: 0; }
.panel h2 { margin: 0 0 9px; font: 600 34px/1.05 var(--display); letter-spacing: .01em; }
.panel h2::after { content: ""; display: block; width: 34px; height: 3px; margin-top: 11px; background: var(--red); }
h3 { margin: 0 0 5px; font-size: 16px; line-height: 1.3; }
p { line-height: 1.55; }
.panel > p { max-width: 760px; }
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
    <button data-page="profile">Listening profile</button>
    <button data-page="forMe">For Me</button>
    <button data-page="personalDiscoveries">Personal Discoveries</button>
    <button data-page="classics">Classics</button>
    <button data-page="artistDeepDive">Artist Deep Dives</button>
    <button data-page="acquisitions">Acquisitions</button>
    <button data-page="settings">Settings</button>
  </nav>

  <section id="dashboard" class="page">
    <div class="panel">
      <h2>Connection</h2>
      <p id="connection" class="status">Checking Navidrome…</p>
      <p class="muted">The web app uses your existing Navidrome Librarian engine.</p>
      <button id="checkConnection">Check connection</button>
    </div>
    <div class="panel">
      <h2>Quick start</h2>
      <p>Generate music recommendations or explore your recent listening profile.</p>
      <p class="muted">Requests may take a little while while metadata and discovery sources are checked.</p>
      <button data-go="recommendations">Explore recommendations</button>
      <button data-go="profile">View listening profile</button>
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

  <section id="profile" class="page hidden">
    <div class="panel">
      <h2>Recent listening profile</h2>
      <div class="controls">
        <label for="days">Period</label>
        <select id="days">
          <option value="7">7 days</option>
          <option value="30" selected>30 days</option>
          <option value="90">90 days</option>
        </select>
        <button id="loadProfile">Load profile</button>
      </div>
      <pre id="profileResult" class="muted"></pre>
    </div>
  </section>

  <footer>
    Discovery, feedback and acquisition controls use your existing Librarian backend. Artwork is optional and never blocks recommendations.
  </footer>

<section id="forMe" class="page hidden">
  <div class="panel">
    <h2>For Me</h2>
    <p>Albums saved for later.</p>
    <button data-load-discovery="for_me">Reload saved albums</button>
    <p id="forMeStatus"></p>
    <div id="forMeCards" class="cards"></div>
  </div>
</section>

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
    <h2>Classics</h2>
    <p>Popular albums worth exploring. Popularity does not necessarily indicate critical acclaim.</p>
    <button data-load-discovery="classics">Load classics</button>
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
    <h2>slskd Settings</h2>
    <p>The API key is never displayed. Leave the key field blank to retain the configured key.</p>
    <label>slskd URL
      <input id="slskdUrl" type="url" value="http://192.168.1.12:5030">
    </label>
    <label>API key
      <input id="slskdApiKey" type="password"
             placeholder="Enter key to set or replace it"
             autocomplete="new-password">
    </label>
    <label>Music library directory visible to the Librarian backend
      <input id="musicLibraryPath" type="text" placeholder="/media/library/music">
    </label>
    <p class="muted">This directory is used for library scans and importing completed albums. Use an absolute path on the machine running the Librarian backend.</p>
    <label>slskd completed-download directory visible to the Librarian backend
      <input id="slskdDownloadsPath" type="text" placeholder="/media/downloads/slskd/complete">
    </label>
    <p class="muted">Use an absolute path on the machine running the Librarian backend, not a path inside the slskd container. The default is detected by the backend for the current host.</p>
    <h3>Audio quality priority</h3>
    <label>First choice <select class="quality-priority"></select></label>
    <label>Second choice <select class="quality-priority"></select></label>
    <label>Third choice <select class="quality-priority"></select></label>
    <label>Fourth choice <select class="quality-priority"></select></label>
    <p>
      <button id="saveSlskd">Save settings</button>
      <button id="testSlskd">Test connection</button>
    </p>
    <p id="slskdStatus"></p>
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

<section id="acquireReview" class="page hidden">
  <div class="panel">
    <h2>Review download candidates</h2>
    <p id="acquireStatus"></p>
    <div id="acquireCards" class="cards"></div>
    <button data-page="personalDiscoveries">Back to discoveries</button>
  </div>
</section>

</main>

<script>
const $ = id => document.getElementById(id);

function showPage(name) {
  document.querySelectorAll('.page').forEach(el =>
    el.classList.toggle('hidden', el.id !== name));
  document.querySelectorAll('nav button[data-page]').forEach(el =>
    el.classList.toggle('active', el.dataset.page === name));
}

document.querySelectorAll('nav button[data-page]').forEach(button =>
  button.addEventListener('click', () => {
    showPage(button.dataset.page);
    if (button.dataset.page === 'settings') loadSlskdSettings();
    if (button.dataset.page === 'acquisitions') startAcquisitionStream();
    else stopAcquisitionStream();
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

function renderAcquisitions(data) {
  const target = $('acquisitionCards');
  try {
    target.replaceChildren();
    const jobs = Array.isArray(data.acquisitions) ? data.acquisitions : [];
    const dismissed = new Set(JSON.parse(localStorage.getItem('navidrome-dismissed-acquisitions') || '[]'));
    $('acquisitionsStatus').textContent = jobs.length
      ? `${jobs.length} acquisition record(s).`
      : 'No acquisition records yet.';
    for (const job of jobs) {
      const dismissalKey = [job.artist || '', job.album || ''].join('::').toLocaleLowerCase();
      if (job.status === 'imported' && dismissed.has(dismissalKey)) continue;
      const card = document.createElement('article');
      card.className = 'card';
      addTextElement(card, 'p', 'card-category', String(job.status || 'unknown').replaceAll('_', ' '));
      addTextElement(card, 'h3', '', job.album || 'Unknown album');
      addTextElement(card, 'p', 'card-artist', job.artist || 'Unknown artist');
      const details = job.details || {};
      const progress = details.live_progress;
      if (job.status === 'downloading' && progress) {
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
        addTextElement(copy, 'p', 'download-progress-stat', speedText);
        const remaining = Number.isFinite(Number(progress.remaining_tracks)) ? Math.max(0, Number(progress.remaining_tracks)) : null;
        const totalTracks = Number.isFinite(Number(progress.total_tracks)) ? Math.max(0, Number(progress.total_tracks)) : null;
        addTextElement(copy, 'p', 'download-progress-stat',
          remaining === null ? 'Tracks remaining unavailable' :
          String(remaining) + ' of ' + (totalTracks === null ? '?' : totalTracks) + ' tracks remaining');
        progressRow.append(ring, copy);
        card.append(progressRow);
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
        job.updated_at ? 'Updated: ' + new Date(job.updated_at * 1000).toLocaleString() : ''
      ].filter(Boolean);
      for (const line of lines) addTextElement(card, 'p', 'card-meta', line);
      if (job.status === 'imported') {
        const actions = document.createElement('div');
        actions.className = 'card-actions';
        const dismiss = document.createElement('button');
        dismiss.type = 'button';
        dismiss.textContent = 'Dismiss';
        dismiss.addEventListener('click', () => {
          const stored = new Set(JSON.parse(localStorage.getItem('navidrome-dismissed-acquisitions') || '[]'));
          stored.add(dismissalKey);
          localStorage.setItem('navidrome-dismissed-acquisitions', JSON.stringify([...stored]));
          card.remove();
          const visibleCards = target.querySelectorAll('.card').length;
          $('acquisitionsStatus').textContent = visibleCards
            ? visibleCards + ' acquisition record(s).'
            : 'No acquisition records to show.';
        });
        actions.append(dismiss);
        card.append(actions);
      }
      if (details.status && details.status !== job.status) {
        addTextElement(card, 'pre', 'debug', pretty(details));
      }
      target.append(card);
    }
  } catch (error) {
    $('acquisitionsStatus').textContent = error.message;
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
  return el;
}

const artworkLoaders = new WeakMap();
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

function attachArtwork(card, artist, album) {
  const art = document.createElement('div');
  art.className = 'card-art';
  art.setAttribute('aria-hidden', 'true');

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
    fetch('/api/artwork?' + query.toString())
      .then(response => response.ok ? response.json() : null)
      .then(data => {
        if (!data || !data.artwork_url) return;
        image.onload = () => art.classList.add('has-image');
        image.onerror = () => art.classList.remove('has-image');
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
  allRecommendations = getRecommendations(data);
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

    return (!query || searchable.includes(query)) &&
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
    card.className = 'card';
    attachArtwork(card, item.artist || item.album_artist || '', item.album || item.title || item.name || '');

    const categoryName = (item.discovery_category || 'Unclassified')
      .replaceAll('_', ' ');

    addTextElement(card, 'p', 'card-category', categoryName);

    addTextElement(
      card, 'h3', '',
      item.album || item.title || item.name || 'Untitled album'
    );

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

$('checkConnection').addEventListener('click', checkConnection);

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

$('loadProfile').addEventListener('click', async () => {
  const output = $('profileResult');
  output.textContent = 'Loading listening profile…';
  try {
    const data = await requestJSON(
      '/api/profile?days=' + encodeURIComponent($('days').value));
    output.textContent = pretty(data);
  } catch (error) {
    output.textContent = error.message;
  }
});


const discoveryViews = {
  for_me: ['forMeCards','forMeStatus'],
  personal: ['personalCards','personalStatus'],
  classics: ['classicsCards','classicsStatus'],
  artist_deep_dive: ['artistDeepDiveCards','artistDeepDiveStatus']
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

async function loadDiscovery(name) {
  discoveryStatus(name, 'Loading…');
  const target = $(discoveryViews[name][0]);
  target.replaceChildren();

  try {
    const data = await requestJSON(`/api/discovery/${name}?count=30`);
    const items = data.items || data.recommendations || [];

    discoveryStatus(name, `${items.length} item(s)`);

    for (const item of items) {
      const artist = item.artist || item.album_artist || 'Unknown artist';
      const album = item.album || item.title || 'Untitled album';
      const card = document.createElement('article');
      card.className = 'card';
      attachArtwork(card, artist, album);

      addTextElement(card, 'p', 'card-category',
        (item.discovery_type || item.discovery_category || name).replaceAll('_',' '));
      addTextElement(card, 'h3', '', album);
      addTextElement(card, 'p', 'card-artist', artist);

      if (item.reason) addTextElement(card, 'p', 'card-meta', item.reason);
      if (item.anchor_artist) addTextElement(card, 'p', 'card-meta',
        `Similar to ${item.anchor_artist}`);
      if (item.lastfm_playcount) addTextElement(card, 'p', 'card-meta',
        `Last.fm playcount: ${Number(item.lastfm_playcount).toLocaleString()}`);

      if (name === 'for_me') {
        addTextElement(card, 'p', 'card-meta',
          item.acquired === true ? '✓ In your library' :
          item.acquired === false ? 'Not found in the library index' :
          'Library presence not confirmed');
      }

      const actions = document.createElement('div');
      actions.className = 'card-actions';

      const button = (label, callback) => {
        const b = document.createElement('button');
        b.textContent = label;
        b.addEventListener('click', callback);
        actions.append(b);
      };

      button(name === 'for_me' ? 'Remove from For Me' : '＋ For Me',
        () => sendFeedback(name === 'for_me' ? 'remove_for_me' : 'save',
                           artist, album, item, name));

      button('Dismiss album',
        () => sendFeedback('dismiss', artist, album, item, name));

      button('Dismiss artist',
        () => sendFeedback('dismiss_artist', artist, album, item, name));

      button('Search slskd', () => searchAlbum(artist, album, item));

      card.append(actions);
      target.append(card);
    }

    if (!items.length) addTextElement(target, 'p', '',
      name === 'for_me' ? 'No saved albums yet.' : 'No results. Try refreshing this list.');
  } catch (error) {
    discoveryStatus(name, error.message);
  }
}

async function sendFeedback(action, artist, album, metadata, listName) {
  try {
    await sendJSON('/api/discovery/feedback', 'POST',
      {action, artist, album, metadata});
    await loadDiscovery(listName);
    if (listName !== 'for_me') await loadDiscovery('for_me');
  } catch (error) {
    discoveryStatus(listName, error.message);
  }
}

async function refreshDiscovery(name) {
  discoveryStatus(name, 'Refreshing…');
  try {
    await sendJSON(`/api/discovery/${name}/refresh`, 'POST', {count:20});
    setTimeout(() => loadDiscovery(name), 1200);
  } catch (error) {
    discoveryStatus(name, error.message);
  }
}

document.querySelectorAll('[data-load-discovery]').forEach(button =>
  button.addEventListener('click', () => loadDiscovery(button.dataset.loadDiscovery)));

document.querySelectorAll('[data-refresh-discovery]').forEach(button =>
  button.addEventListener('click', () => refreshDiscovery(button.dataset.refreshDiscovery)));

async function searchAlbum(artist, album, metadata) {
  showPage('acquireReview');
  $('acquireStatus').textContent =
    `Searching for ${artist} — ${album}. A clear match will be queued automatically; review is only needed when the match criteria are not met.`;
  const target = $('acquireCards');
  target.replaceChildren();

  try {
    const data = await sendJSON('/api/acquire', 'POST',
      {artist, album, metadata, auto_queue:true});

    $('acquireStatus').textContent = data.message || data.status || 'Search complete.';

    if (data.status === 'review_required') {
      for (const candidate of data.candidates || []) {
        const card = document.createElement('article');
        card.className = 'card';
        addTextElement(card, 'h3', '', candidate.folder || candidate.username);
        addTextElement(card, 'p', 'card-meta',
          `${candidate.file_count} files · ${(candidate.quality_summary || []).join(', ')}`);

        for (const file of (candidate.files || []).slice(0, 10)) {
          addTextElement(card, 'p', 'card-meta', file.filename);
        }

        const queue = document.createElement('button');
        queue.textContent = 'Queue this candidate';
        queue.addEventListener('click', async () => {
          if (!confirm(`Queue ${candidate.file_count} files from ${candidate.username}?`)) return;
          queue.disabled = true;
          try {
            const files = (candidate.files || []).map(f =>
              ({filename:f.filename, size:f.size}));
            const result = await sendJSON('/api/acquire/queue', 'POST',
              {username:candidate.username, artist, album, folder:candidate.folder, files});
            $('acquireStatus').textContent = result.message || result.status;
            queue.textContent = 'Queue requested';
          } catch (error) {
            $('acquireStatus').textContent = error.message;
            queue.disabled = false;
          }
        });
        card.append(queue);
        target.append(card);
      }
    } else {
      addTextElement(target, 'p', '', data.message || data.status || pretty(data));
    }
  } catch (error) {
    $('acquireStatus').textContent = error.message;
  }
}

async function loadSlskdSettings() {
  try {
    const data = await requestJSON('/api/settings/slskd');
    $('slskdUrl').value = data.slskd_url || '';
    $('musicLibraryPath').value = data.music_library_path || '';
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
    music_library_path: $('musicLibraryPath').value.trim(),
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


checkConnection();
</script>
</body>
</html>
"""
