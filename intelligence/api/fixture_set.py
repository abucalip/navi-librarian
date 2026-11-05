"""Deterministic example responses for the Server V2 contract fixtures.

``build_fixtures`` seeds a throwaway store with fixed data (no clock, no network, no
provider) and returns ``{file name: document}``. ``scripts/write_intelligence_fixtures.py``
writes them to ``intelligence/contract-fixtures``; a test rebuilds them and fails when the
files drift from the builders, so a response change cannot ship without updated fixtures.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from ..health import build_report
from ..ingest.navidrome import normalize_album
from ..resolution import unresolved
from ..store import generations, open_store
from .bodies import build_health_body, build_unresolved_body
from .capabilities import ServerFacts, build_capabilities
from .changes import build_changes
from .etag import etag_for

_MB_A = "11111111-1111-1111-1111-111111111111"
_MB_B = "22222222-2222-2222-2222-222222222222"
_MB_C = "33333333-3333-3333-3333-333333333333"


def _albums() -> list:
    clean = {
        "id": "al-1", "name": "Rumours", "artist": "Fleetwood Mac", "artistId": "ar-1",
        "artists": [{"id": "ar-1", "musicBrainzId": _MB_A}], "musicBrainzId": _MB_A,
        "songCount": 2, "genres": [{"name": "Rock"}],
        "song": [
            {"id": "al-1-1", "track": 1, "discNumber": 1, "year": 1977, "musicBrainzId": _MB_A,
             "replayGain": {"trackGain": -6.0}},
            {"id": "al-1-2", "track": 2, "discNumber": 1, "year": 1977, "musicBrainzId": _MB_B,
             "replayGain": {"trackGain": -7.0}},
        ],
    }
    gappy = {
        "id": "al-2", "name": "Kind of Blue", "artist": "Miles Davis", "artistId": "ar-2",
        "artists": [], "songCount": 5, "genres": [],
        "song": [
            {"id": "al-2-1", "track": 1, "discNumber": 1, "year": 1959},
            {"id": "al-2-3", "track": 3, "discNumber": 1, "year": 1959},
        ],
    }
    return [normalize_album(clean), normalize_album(gappy)]


def build_fixtures() -> dict[str, dict[str, Any]]:
    with tempfile.TemporaryDirectory() as tmp:
        db = open_store(Path(tmp) / "intelligence.sqlite3")
        try:
            return _build(db)
        finally:
            db.close()


def _build(db) -> dict[str, dict[str, Any]]:
    empty_caps = build_capabilities(db)
    empty_changes = build_changes(db, 0)

    unresolved.queue_unresolved(
        db, "album", "al-2",
        [{"mbid": _MB_B, "title": "Kind of Blue", "artist": "Miles Davis", "score": 0.91},
         {"mbid": _MB_C, "title": "Kind of Blue (Legacy Edition)", "artist": "Miles Davis", "score": 0.88}],
        "two_close_candidates", now=1_700_000_000.0,
    )
    generations.bump_data_version(db, "health")
    caps = build_capabilities(db, ServerFacts(listenbrainz_connected=True, graph_coverage="partial"))
    version = generations.data_versions(db)["health"]
    tag = etag_for("health", version, generations.current_generation(db))
    return {
        "capabilities_empty.json": {"request": "GET /api/capabilities", "response": empty_caps},
        "capabilities_populated.json": {"request": "GET /api/capabilities", "response": caps},
        "changes_from_start.json": {"request": "GET /api/changes", "response": build_changes(db, 0)},
        "changes_caught_up.json": {
            "request": f"GET /api/changes?since={caps['cursor']}",
            "response": build_changes(db, caps["cursor"]),
        },
        "changes_reset.json": {"request": "GET /api/changes?since=999", "response": build_changes(db, 999)},
        "changes_empty_store.json": {"request": "GET /api/changes", "response": empty_changes},
        "health.json": {
            "request": "GET /api/library-health",
            "response_headers": {"ETag": tag},
            "response": build_health_body(db, build_report(_albums())),
        },
        "unresolved.json": {"request": "GET /api/unresolved", "response": build_unresolved_body(db)},
    }
