from pathlib import Path
from datetime import datetime
import py_compile
import shutil
import sys

source = Path("navidrome_server.py")
if not source.is_file():
    sys.exit("ERROR: navidrome_server.py not found.")

text = source.read_text(encoding="utf-8")
original = text

def replace_once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        sys.exit(
            f"ABORTED: expected exactly one match for {label}; "
            f"found {count}. No changes written."
        )
    text = text.replace(old, new, 1)
    print(f"Prepared: {label}")

# 1. Add persistent SQLite cache helpers.
replace_once(
    "import secrets\nfrom pathlib import Path\n",
    "import secrets\nimport sqlite3\nimport time\nfrom pathlib import Path\n",
    "SQLite imports",
)

replace_once(
    'load_dotenv(Path(__file__).with_name(".env"))\n',
    '''load_dotenv(Path(__file__).with_name(".env"))

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
''',
    "persistent cache helpers",
)

# 2. Use cached recording metadata before making a MusicBrainz request.
replace_once(
    '''                if index:
                    time.sleep(1.1)

                response = None
                for attempt in range(3):
                    response = client.get(
                        f"https://musicbrainz.org/ws/2/recording/{mbid}",
                        params={"fmt": "json", "inc": "artists+releases+release-groups"},
                        headers=headers,
                    )
                    if response.status_code not in (429, 500, 502, 503, 504):
                        break
                    if attempt < 2:
                        time.sleep(2 * (attempt + 1))
                response.raise_for_status()
                recording = response.json()
''',
    '''                recording = _metadata_cache_get(
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
''',
    "recording metadata cache",
)

# 3. Cache artist genres separately, for 90 days.
replace_once(
    '''            try:
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
''',
    '''            try:
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
''',
    "artist genre cache",
)

# 4. Recognize additional North African and Middle Eastern genre labels.
replace_once(
    '''            if any(x in g for x in ("middle eastern", "arabic", "raï", "rai",
                                    "north african")):
                families.add("north-african-middle-eastern")
''',
    '''            if any(x in g for x in (
                "middle eastern", "arabic", "raï", "rai", "north african",
                "north-african", "maghrebi", "maghreb", "chaabi",
                "gnawa", "gnaoua", "malouf", "andalusi", "andalusian",
                "algerian", "moroccan", "tunisian", "mawwal", "tarab",
                "maqam", "levantine", "khaliji", "khaleeji", "dabke",
                "oud music", "arab pop", "arabic pop", "shaabi",
            )):
                families.add("north-african-middle-eastern")
''',
    "North African and Middle Eastern genre recognition",
)

# 5. Separate established/core interests from deliberate exploration.
replace_once(
    '''    profile_families = {
        "jazz", "hip-hop", "alternative", "brazilian", "african",
        "rnb-soul", "electronic", "funk",
        "north-african-middle-eastern",
    }
''',
    '''    # Core interests are used to identify close recommendations.
    # African and North African/Middle Eastern music are explicit
    # exploration interests: they should be represented without making
    # every unfamiliar genre automatically count as a core match.
    core_families = {
        "jazz", "hip-hop", "alternative", "brazilian",
        "rnb-soul", "electronic", "funk",
    }
    exploration_families = {
        "african", "north-african-middle-eastern",
    }
    profile_families = core_families | exploration_families
''',
    "core and exploration profiles",
)

# 6. Use a more moderate familiarity adjustment.
replace_once(
    '''        if recent_count == 0:
            familiarity_factor = 2.0
        elif recent_count <= 2:
            familiarity_factor = 1.6
        elif recent_count <= 5:
            familiarity_factor = 1.2
        elif recent_count <= 10:
            familiarity_factor = 0.85
        else:
            familiarity_factor = 0.6

        candidate["discovery_score"] = (
            candidate["score"] * familiarity_factor
        )
''',
    '''        if recent_count == 0:
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
''',
    "discovery scoring",
)

# 7. Classify categories without calling every multi-genre artist cross-genre.
replace_once(
    '''        overlap = families & profile_families

        if len(families) >= 2 and overlap:
            category = "cross_genre"
        elif overlap:
            category = "adjacent"
        else:
            # This includes both genuinely unfamiliar genres and candidates
            # whose genre tags are missing; the output flags that uncertainty.
            category = "adventurous"
''',
    '''        core_overlap = families & core_families
        exploration_overlap = families & exploration_families

        if core_overlap and (families - core_overlap):
            category = "cross_genre"
        elif core_overlap or exploration_overlap:
            category = "adjacent"
        else:
            # Missing tags are still marked as low-confidence below.
            category = "adventurous"
''',
    "discovery category classification",
)

if text == original:
    sys.exit("ERROR: no changes prepared.")

backup = source.with_name(
    f"navidrome_server.py.bak-{datetime.now():%Y%m%d-%H%M%S}"
)
shutil.copy2(source, backup)

# Write to a temporary file first, then replace the source.
temporary = source.with_suffix(".py.tmp")
temporary.write_text(text, encoding="utf-8")

try:
    py_compile.compile(str(temporary), doraise=True)
except Exception as exc:
    temporary.unlink(missing_ok=True)
    sys.exit(
        f"Syntax validation failed; original source is untouched.\n{exc}"
    )

temporary.replace(source)

# Compile the actual final path too.
try:
    py_compile.compile(str(source), doraise=True)
except Exception as exc:
    shutil.copy2(backup, source)
    sys.exit(f"Final syntax check failed; restored backup.\n{exc}")

print("\nPatch applied successfully.")
print(f"Backup: {backup}")
print(f"Cache database will be created at: "
      f"{Path('navidrome_metadata_cache.sqlite3').resolve()}")
print("Python syntax: OK")
