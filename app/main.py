import json
from html import escape
from time import monotonic

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

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
:root {
  color-scheme: dark;
  --bg: #111318;
  --panel: #1b1e26;
  --border: #303440;
  --text: #eef0f6;
  --muted: #a5abba;
  --accent: #a8b8ff;
  --green: #8cdda9;
  --red: #ff9999;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 15px/1.55 -apple-system, BlinkMacSystemFont, sans-serif;
}
header {
  padding: 30px max(22px, calc((100% - 1050px)/2));
  border-bottom: 1px solid var(--border);
}
header h1 { margin: 0; font-size: 27px; }
header p { color: var(--muted); margin: 5px 0 0; }
main {
  max-width: 1050px;
  margin: 26px auto;
  padding: 0 22px 50px;
}
nav { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 22px; }
button, select {
  background: var(--panel);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 10px 14px;
  border-radius: 9px;
  font: inherit;
}
button { cursor: pointer; }
button:hover { border-color: var(--accent); }
button.active { background: #292f48; border-color: var(--accent); }
.panel {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 22px;
  margin-bottom: 18px;
  min-width: 0;
}
h2 { margin-top: 0; font-size: 20px; }
h3 { margin-bottom: 5px; }
.muted { color: var(--muted); }
.status { font-weight: 600; }
.ok { color: var(--green); }
.error { color: var(--red); }
.controls { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }
#result {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font: 13px/1.6 ui-monospace, SFMono-Regular, monospace;
  color: #d8dbea;
}
.discovery-controls {
  display: grid;
  grid-template-columns: minmax(180px, 2fr) repeat(2, minmax(150px, 1fr));
  gap: 10px;
  margin: 18px 0 8px;
}

.discovery-controls input,
.discovery-controls select {
  width: 100%;
  min-width: 0;
  background: var(--bg);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 10px 12px;
  border-radius: 9px;
  font: inherit;
}

.discovery-controls input:focus,
.discovery-controls select:focus {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

#recommendationCount {
  margin: 8px 0 14px;
  font-size: 13px;
}

@media (max-width: 650px) {
  .discovery-controls {
    grid-template-columns: 1fr;
  }
}

.cards { display: grid; grid-template-columns: repeat(auto-fit,minmax(230px,1fr)); gap: 12px; }
.card { border: 1px solid var(--border); border-radius: 10px; padding: 15px; }
.card-category {
  display: inline-block;
  margin: 0 0 10px;
  padding: 3px 9px;
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--accent);
  font-size: 12px;
  text-transform: capitalize;
}

.card h3 {
  margin: 0 0 4px;
  font-size: 18px;
  line-height: 1.35;
}

.card-artist {
  margin: 0 0 14px;
  color: var(--muted);
}

.genre-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.genre-tag {
  padding: 3px 8px;
  border-radius: 6px;
  background: #292d38;
  color: var(--text);
  font-size: 12px;
}

.card-meta,
.card-source {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 12px;
  overflow-wrap: anywhere;
}
.card h3 { font-size: 16px; }
.card p { margin: 5px 0; color: var(--muted); }
.hidden { display: none; }
footer { color: var(--muted); font-size: 12px; margin-top: 28px; }

.discovery-settings {display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
#settings label {display:block;margin:12px 0}
#settings input,#settings select {display:block;width:100%;max-width:480px;padding:9px;margin-top:5px}
.card-actions {display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.card-actions button {font-size:13px;padding:7px 10px}

</style>
</head>
<body>
<header>
  <h1>Navidrome Librarian</h1>
  <p>Your music library, listening history and discovery recommendations.</p>
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
    Read-only interface. It does not modify music files or playlists.
    Recommendation metadata may be cached by the existing engine.
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
