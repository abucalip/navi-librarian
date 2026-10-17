import hashlib
import json
import os
import random
import shutil
import sqlite3
import time
import unicodedata
import discovery_store
import slskd_transfers as _slskd_transfers_module
import listenbrainz_client as _listenbrainz_client
import lastfm_client as _lastfm_client_module
import musicbrainz_rating_client as _musicbrainz_rating_client
from music_paths import default_music_dir as _default_music_dir_from_environment
import navidrome_client as _navidrome_client
from acquisition_candidate_queue import normalize_reviewed_candidate_files as _normalize_reviewed_candidate_files
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
from acquisition_progress_snapshots import ProgressSnapshots as _ProgressSnapshots
from acquisition_request_coordinator import acquire_album_request as _acquire_album_request
import acquisition_state as _acquisition_state
from acquisition_source_switch import switch_to_next_source_locked as _switch_to_next_source_locked
from acquisition_recovery import reconcile_interrupted_import as _reconcile_interrupted_import
from acquisition_cleanup import clean_acquisition_source as _clean_acquisition_source
import discovery_refresh
import listening_profile
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
from music_tag_audit import scan_missing_mbids

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
    """Read a bounded section of the legacy service module's own source code.

    Read-only. Only reads this Python file; does not accept file paths.
    Returns at most 250 lines per request.
    """
    import json
    from pathlib import Path
    from server_source_redaction import redact_assignment

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
    result = []
    for number in range(start_line, end_line + 1):
        line = redact_assignment(lines[number - 1])
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

    from navidrome_client import library_overview_payload
    return json.dumps(
        library_overview_payload(artists, albums),
        ensure_ascii=False,
        indent=2,
    )


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

    from navidrome_client import search_result_payload
    return json.dumps(
        search_result_payload(result, category, items),
        ensure_ascii=False,
        indent=2,
    )


def get_album_details(album_id: str) -> str:
    """Get album metadata and track listings using an album ID from search_music."""
    if not album_id.strip():
        return "Please provide an album ID."

    root = api_call("getAlbum", id=album_id)
    album = root.get("album", {})

    from navidrome_client import album_details_payload
    return json.dumps(
        album_details_payload(album, items),
        ensure_ascii=False,
        indent=2,
    )


def find_missing_mbids(max_files: int = 1000, offset: int = 0) -> str:
    """Read audio tags and report missing MusicBrainz IDs without modifying files."""
    result = scan_missing_mbids(
        MUSIC_DIR,
        max_files=max_files,
        offset=offset,
        audio_file_reader=File,
    )
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False, indent=2)


def _listenbrainz_recent(days=30, page_limit=3):
    """Compatibility adapter for bounded ListenBrainz listen retrieval."""
    return _listenbrainz_client.recent_listens(
        _listenbrainz_username(),
        days=days,
        page_limit=page_limit,
    )


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
    """Compatibility adapter for cached Last.fm album popularity lookup."""
    global LASTFM_LAST_ERROR
    result, error = _lastfm_client.album_popularity(artist, album)
    if error is not None:
        LASTFM_LAST_ERROR = error
    return result

def recent_listening_profile(days: int = 30) -> str:
    """Summarize recent ListenBrainz listening by artist and album.

    Reads public listening history. Does not modify music files.
    """
    if not 1 <= days <= 90:
        return "days must be between 1 and 90."

    try:
        listens = _listenbrainz_recent(days=days)
    except Exception as exc:
        return json.dumps({
            "error": f"Could not retrieve ListenBrainz history: {exc}"
        }, ensure_ascii=False, indent=2)

    from listening_profile import build_listening_profile
    return json.dumps(
        build_listening_profile(listens, _listenbrainz_username(), days),
        ensure_ascii=False,
        indent=2,
    )


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

    from discovery_recommendations import (
        apply_familiarity_exploration_bonus,
        apply_lastfm_popularity_bonus,
        classify_diversity_style,
        classify_recommendation_category,
        genre_families,
        primary_recent_family,
        recent_style_families,
    )
    from discovery_candidate_gathering import RecommendationProviders, gather_recommendation_candidates
    gathered = gather_recommendation_candidates(RecommendationProviders(
        listenbrainz_recent=_listenbrainz_recent, listenbrainz_username=_listenbrainz_username,
        music_key=_music_key, metadata_cache_get=_metadata_cache_get, metadata_cache_set=_metadata_cache_set,
        is_album_candidate=_discovery_is_album_candidate, api_call=api_call, items=items,
        http_get=httpx.get, http_client=httpx.Client, sleep=time.sleep,
    ))
    if isinstance(gathered, str):
        return gathered
    listens = gathered["listens"]
    recent_artists = gathered["recent_artists"]
    recent_artist_mbid_counts = gathered["recent_artist_mbid_counts"]
    albums = gathered["albums"]
    failures = gathered["failures"]
    library_albums = gathered["library_albums"]
    library_by_title = gathered["library_by_title"]
    genre_cache = gathered["genre_cache"]
    recent_family_counts = gathered["recent_family_counts"]
    core_families = gathered["core_families"]
    exploration_families = gathered["exploration_families"]
    profile_families = gathered["profile_families"]
    regional_candidates_added = gathered["regional_candidates_added"]
    regional_results_seen = gathered["regional_results_seen"]

    found = []
    possible_matches = []
    checked = 0
    artist_recommendation_counts = Counter()

    for candidate in albums.values():
        recent_count = recent_artists.get(
            _music_key(candidate["primary_artist"]), 0
        )
        candidate_tags = genre_cache.get(candidate.get("artist_mbid"), [])
        apply_familiarity_exploration_bonus(
            candidate, recent_count, candidate_tags, exploration_families
        )

    # Classify candidates using available MusicBrainz genres and a separate
    # regional/style label used to encourage variety in the final shortlist.
    candidates_by_category = {
        "adjacent": [],
        "cross_genre": [],
        "adventurous": [],
        "unclassified": [],
    }

    for candidate in albums.values():
        tags = genre_cache.get(candidate.get("artist_mbid"), [])
        candidate["diversity_style"] = classify_diversity_style(candidate, tags)
        category, families = classify_recommendation_category(
            candidate, tags, core_families, exploration_families,
            music_key_fn=_music_key,
        )

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

    lastfm_available = bool(_discovery_settings_read().get("lastfm_api_key"))
    lastfm_checked = apply_lastfm_popularity_bonus(
        albums.values(),
        recent_family_counts,
        _lastfm_album_popularity,
    )

    for group in candidates_by_category.values():
        group.sort(
            key=lambda album: album["discovery_score"],
            reverse=True,
        )

    from discovery_allocation_contract import (
        AllocationCandidate,
        AllocationRequest,
        OwnershipStatus,
    )
    from discovery_personal_allocator import allocate_personal_recommendations
    from discovery_recommendation_payload import (
        build_personal_recommendation_payload,
    )

    diversity_style_targets = {
        "north_african": 1,
        "afrobeats": 1,
        "afro_jazz": 1,
        "malian_desert_blues": 1,
    }
    targets = {
        "adjacent": (count * 4) // 10,
        "cross_genre": (count * 3) // 10,
    }
    targets["adventurous"] = count - sum(targets.values())

    # Prepare immutable policy inputs in original album insertion order. The
    # adapter owns identity normalization and the Navidrome ownership lookup;
    # the allocator itself has no provider/library access or mutable callbacks.
    candidate_by_id = {}
    allocation_candidates = []
    for source_order, candidate in enumerate(albums.values()):
        candidate_id = str(source_order)
        candidate_by_id[candidate_id] = candidate
        title_key = _music_key(candidate["album"])
        same_title = library_by_title.get(title_key, [])
        exact_owned = any(
            _music_key(match.get("artist", ""))
            == _music_key(candidate["primary_artist"])
            for match in same_title
        )
        ownership = (
            OwnershipStatus.EXACT_OWNED
            if exact_owned
            else OwnershipStatus.TITLE_CONFLICT
            if same_title
            else OwnershipStatus.CLEAR
        )
        allocation_candidates.append(AllocationCandidate(
            candidate_id=candidate_id,
            artist_key=_artist_identity(candidate),
            album_key=title_key,
            category=candidate["discovery_category"],
            score=float(candidate["discovery_score"]),
            source_order=source_order,
            diversity_style=candidate.get("diversity_style", "other"),
            recent_profile_family=candidate.get("recent_profile_family"),
            ownership=ownership,
        ))

    allocation = allocate_personal_recommendations(AllocationRequest(
        candidates=tuple(allocation_candidates),
        count=count,
        category_targets=targets,
        diversity_style_targets=diversity_style_targets,
        family_cap=1,
        max_checks=60,
    ))
    selected_counts = Counter(allocation.category_counts)
    selected_styles = Counter(
        candidate_by_id[candidate_id].get("diversity_style", "other")
        for candidate_id in allocation.selected_candidate_ids
    )
    selected_profile_families = Counter()
    artist_recommendation_counts = Counter()
    candidate_decisions = {
        id(candidate_by_id[decision.candidate_id]): {
            "status": decision.status,
            "reason": decision.reason,
        }
        for decision in allocation.decisions
    }
    checked = allocation.checked_count
    found = []
    possible_matches = []

    for candidate_id in allocation.selected_candidate_ids:
        candidate = candidate_by_id[candidate_id]
        result = build_personal_recommendation_payload(
            candidate,
            recent_artists.get(_music_key(candidate["primary_artist"]), 0),
        )
        result["ownership_check"] = (
            "No exact normalized album-title match found in the indexed "
            "Navidrome inventory; alternate editions may still exist."
        )
        found.append(result)
        artist_recommendation_counts[_artist_identity(candidate)] += 1
        style = candidate.get("diversity_style", "other")
        if style not in diversity_style_targets:
            family = candidate.get("recent_profile_family")
            if family:
                selected_profile_families[family] += 1

    for candidate_id in allocation.ownership_review_candidate_ids:
        candidate = candidate_by_id[candidate_id]
        result = build_personal_recommendation_payload(
            candidate,
            recent_artists.get(_music_key(candidate["primary_artist"]), 0),
        )
        result["ownership_note"] = (
            "A same-title album exists in Navidrome under a different "
            "artist credit. Review before treating this as new."
        )
        possible_matches.append(result)


    # Temporary diagnostics: inspect all resolved candidates before return.
    candidate_debug = []
    candidate_category_counts = Counter()

    for candidate in albums.values():
        tags = genre_cache.get(candidate.get("artist_mbid"), [])
        category, families = classify_recommendation_category(
            candidate, tags, core_families, exploration_families,
            music_key_fn=_music_key,
        )

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


_lastfm_client = _lastfm_client_module.LastFmClient(
    settings_reader=lambda: _discovery_settings_read(),
    cache_get=lambda key, ttl_seconds: _metadata_cache_get(key, ttl_seconds),
    cache_set=lambda key, value: _metadata_cache_set(key, value),
)


def _lastfm_cached_call(method, ttl_seconds=30 * 24 * 60 * 60, **params):
    """Compatibility adapter for the extracted Last.fm client."""
    return _lastfm_client.cached_call(method, ttl_seconds=ttl_seconds, **params)


def _discovery_library_snapshot():
    """Compatibility adapter for cached Navidrome library inventory assembly."""
    from discovery_library_snapshot import build_library_snapshot
    return build_library_snapshot(
        api_call,
        items,
        _discovery_read_list,
        _discovery_write_list,
    )


def _lastfm_top_albums(artist, limit=8):
    """Compatibility adapter retaining discovery-specific album filtering."""
    return [
        album for album in _lastfm_client.artist_top_albums(artist, limit=limit)
        if _discovery_is_album_candidate({"album": album["album"]})
    ]


def _lastfm_artist_genres(artist):
    """Compatibility adapter for cached Last.fm artist tags."""
    return _lastfm_client.artist_genres(artist)


def _deep_dive_genre_families(tags):
    from discovery_recommendations import deep_dive_genre_families
    return deep_dive_genre_families(tags)
def _lastfm_similar_artists(artist, limit=8):
    """Compatibility adapter for cached Last.fm similar-artist results."""
    return _lastfm_client.similar_artists(artist, limit=limit)


def _musicbrainz_critical_rating(mbid, include_year=False):
    """Compatibility adapter for cached MusicBrainz release-group ratings."""
    return _musicbrainz_rating_client.critical_rating(
        mbid,
        include_year=include_year,
        cache_get=_metadata_cache_get,
        cache_set=_metadata_cache_set,
    )


def _discovery_exact_artist_credit_matches(artist_credit, artist_name):
    from discovery_recommendations import exact_artist_credit_matches
    return exact_artist_credit_matches(artist_credit, artist_name)
def _discovery_is_various_artists(value):
    from discovery_recommendations import is_various_artists
    return is_various_artists(value)
def _build_new_releases_list():
    """Find recent full albums by library artists who own at least one full album."""
    snapshot = _discovery_library_snapshot()
    from discovery_new_releases import prepare_new_release_library_scope
    owned, qualified_artists = prepare_new_release_library_scope(
        snapshot["artists"],
        snapshot["albums"],
        music_key=_music_key,
        is_various_artists=_discovery_is_various_artists,
    )
    from datetime import date
    from discovery_new_releases import new_release_window
    cutoff_date, earliest_year, current_year = new_release_window(date.today())
    candidates = {}
    errors = []
    artist_batch = qualified_artists[:120]
    headers = {"User-Agent": "NavidromeLibrarian/1.0 (personal music discovery)"}

    for index, artist_record in enumerate(artist_batch):
        artist = artist_record["name"].strip()
        if _discovery_is_various_artists(artist):
            continue
        artist_key = _music_key(artist)
        from discovery_new_releases import build_new_release_lookup
        cache_key, query = build_new_release_lookup(
            artist,
            artist_key=artist_key,
            earliest_year=earliest_year,
            current_year=current_year,
        )
        from discovery_new_releases import fetch_artist_release_groups
        payload, lookup_error = fetch_artist_release_groups(
            cache_key,
            query,
            cache_get=_metadata_cache_get,
            cache_set=_metadata_cache_set,
            http_get=httpx.get,
            sleep=time.sleep,
            headers=headers,
            pause_before_request=bool(index),
        )
        if lookup_error is not None:
            errors.append({"artist": artist, "error": lookup_error})
            continue

        from discovery_new_releases import select_artist_release_candidates
        artist_candidates = select_artist_release_candidates(
            payload if isinstance(payload, list) else [],
            artist=artist,
            artist_record=artist_record,
            owned=owned,
            cutoff_date=cutoff_date,
            current_year=current_year,
            music_key=_music_key,
            is_album_candidate=_discovery_is_album_candidate,
            exact_artist_credit_matches=_discovery_exact_artist_credit_matches,
            is_various_artists=_discovery_is_various_artists,
        )
        from discovery_new_releases import merge_release_candidates
        candidates = merge_release_candidates(candidates, artist_candidates)

    from discovery_new_releases import build_new_release_response
    return build_new_release_response(
        candidates,
        qualified_library_artists=len(qualified_artists),
        artists_scanned=len(artist_batch),
        lookup_errors=errors,
        earliest_year=earliest_year,
        cutoff_date=cutoff_date,
        generated_at=time.time(),
    )


def _build_classics_list():
    snapshot = _discovery_library_snapshot()
    library_artists = snapshot["artists"]
    owned = {
        (_music_key(item["artist"]), _music_key(item["album"]))
        for item in snapshot["albums"]
    }
    # Candidate collection policy is independently tested; provider/cache access
    # and pacing remain supplied by this adapter.
    from discovery_classics_candidates import collect_classic_candidates
    candidates = collect_classic_candidates(
        library_artists,
        owned,
        top_albums_lookup=_lastfm_top_albums,
        music_key=_music_key,
        is_album_candidate=_discovery_is_album_candidate,
        pause=lambda: time.sleep(0.15),
    )

    # Keep provider/cache access in the adapter; isolate shortlist policy.
    from discovery_classics_ratings import enrich_critical_ratings
    enrich_critical_ratings(candidates.values(), _musicbrainz_critical_rating)

    # Build a broad candidate pool before choosing the visible collection list.
    # Popularity is only a weak tie-breaker; critical recognition and rotating
    # exploration have much more influence than Last.fm listener totals.
    from discovery_recommendations import score_classic_candidates
    score_classic_candidates(candidates.values(), random.uniform)

    ranked = sorted(candidates.values(), key=lambda item: item["exploration_score"], reverse=True)

    # Keep provider/cache access in the adapter; isolate bounded genre policy.
    from discovery_classics_genres import enrich_classic_genres
    enrich_classic_genres(
        ranked,
        _lastfm_artist_genres,
        _deep_dive_genre_families,
    )

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
    from discovery_recommendations import rank_and_diversify_deep_dive_candidates
    ranked, diversified = rank_and_diversify_deep_dive_candidates(
        candidates.values(),
        music_key=_music_key,
        is_album_candidate=_discovery_is_album_candidate,
        jitter=random.uniform,
    )
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
    "navidrome_url": os.environ.get("NAVIDROME_URL", "").strip().rstrip("/"),
    "navidrome_user": os.environ.get("NAVIDROME_USER", ""),
    "navidrome_password": os.environ.get("NAVIDROME_PASSWORD", ""),
    "lastfm_api_key": os.environ.get("LASTFM_API_KEY", ""),
    "listenbrainz_username": os.environ.get("LISTENBRAINZ_USERNAME", "").strip(),
    "music_library_path": str(MUSIC_DIR),
    "slskd_url": os.environ.get("SLSKD_URL", "").strip().rstrip("/"),
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
    slskd_url: str = "",
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
    """Compatibility adapter for the extracted slskd connectivity probe."""
    from slskd_client import test_connection

    return test_connection(_slskd_config)


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
    """Compatibility adapter for slskd transfer listing and normalization."""
    from slskd_transfers import download_transfer_files

    return download_transfer_files(base_url, headers, username, http_client=httpx)


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
_DISCOVERY_PROGRESS_SNAPSHOTS = _ProgressSnapshots()


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

    expected_by_name, tracked_by_name = (
        _slskd_transfers_module.match_expected_transfer_records(expected_files, tracked)
    )

    progress = _slskd_transfers_module.summarize_transfer_progress(
        expected_by_name, tracked_by_name
    )
    completed = progress["completed_tracks"]
    total_bytes = progress["total_size_bytes"]
    transferred_bytes = progress["transferred_size_bytes"]
    file_byte_snapshot = progress["file_byte_snapshot"]

    now = time.monotonic()
    snapshot_key = (
        str(job.get("artist_key") or _music_key(job.get("artist"))),
        str(job.get("album_key") or _music_key(job.get("album"))),
        str(username).casefold(),
    )
    speed = _DISCOVERY_PROGRESS_SNAPSHOTS.estimate(
        snapshot_key,
        file_byte_snapshot,
        now,
        _slskd_transfers_module.estimate_transfer_speed,
    )

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
    """Compatibility adapter for directly testable import-completion orchestration."""
    from acquisition_import_service import import_completed_source_locked
    return import_completed_source_locked(
        artist, album, source, music_root, candidate,
        safe_folder_name=_discovery_safe_folder_name,
        update_status=_discovery_update_acquisition_status,
        import_matched_album_files=_discovery_import_matched_album_files,
        now=time.time,
    )

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
        return _slskd_transfers_module.queue_download_files(
            base_url, headers, username, selected_files, http_client=httpx
        )

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
    import acquisition_search_diagnostics as _acquisition_search_diagnostics
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
        candidate_diagnostics = _acquisition_search_diagnostics.candidate_diagnostics(candidates)
        if not candidates:
            response_count = len(payload_by_peer)
            audio_file_count = _acquisition_search_diagnostics.count_audio_files(payload_by_peer)
            path_diagnostics = _slskd_path_match_diagnostics(
                list(payload_by_peer.values()), artist, album
            )
            message = _acquisition_search_diagnostics.no_match_message(
                response_count=response_count,
                audio_file_count=audio_file_count,
                reported_response_count=reported_response_count,
                reported_file_count=reported_file_count,
                search_attempts=search_attempts,
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
        normalized, quality_summary, validation_error = _normalize_reviewed_candidate_files(
            files, quality_summary_json
        )
        if validation_error:
            return json.dumps({"ok": False, "error": validation_error})
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

    from discovery_list_payload import build_cached_discovery_list_response
    return build_cached_discovery_list_response(
        list_name,
        count,
        _discovery_read_list,
        feedback,
        saved,
        _music_key,
        _discovery_is_album_candidate,
    )


def _discovery_refresh_all():
    return discovery_refresh.refresh_all(
        _discovery_refresh_personal,
        _discovery_refresh_other,
    )


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
    """Compatibility adapter for the extracted background profile refresh."""
    return listening_profile.refresh_and_persist_background_profile(
        recent_listening_profile,
        _discovery_write_list,
    )


def _discovery_scheduler_refresh_one(list_name):
    if list_name == "personal":
        return _discovery_refresh_personal(20)
    if list_name == "listening_profile":
        return _refresh_listening_profile_background()
    return _discovery_refresh_other(list_name)


def _discovery_scheduler():
    """Refresh stale lists hourly and log bounded per-list failures."""
    import logging

    logger = logging.getLogger(__name__)
    list_names = (
        "personal", "classics", "artist_deep_dive", "new_releases",
        "listening_profile",
    )
    while True:
        try:
            outcomes = discovery_refresh.refresh_stale_lists(
                list_names,
                _discovery_read_list,
                _discovery_scheduler_refresh_one,
                now=time.time(),
                max_age_seconds=24 * 60 * 60,
            )
            for outcome in outcomes:
                if outcome["status"] in {"read_failed", "refresh_failed"}:
                    logger.warning(
                        "Discovery scheduler %s failed for %s (%s)",
                        outcome.get("stage", "refresh"),
                        outcome["list"],
                        outcome.get("error_type", "reported_error"),
                    )
        except Exception as exc:
            logger.error(
                "Discovery scheduler cycle failed (%s)",
                type(exc).__name__,
            )
        time.sleep(3600)


_discovery_scheduler_thread = None


def _start_discovery_scheduler():
    """Start the discovery refresh loop once for the web application process."""
    import threading

    global _discovery_scheduler_thread
    if _discovery_scheduler_thread is not None and _discovery_scheduler_thread.is_alive():
        return
    _discovery_scheduler_thread = threading.Thread(
        target=_discovery_scheduler,
        name="navidrome-discovery-scheduler",
        daemon=True,
    )
    _discovery_scheduler_thread.start()
