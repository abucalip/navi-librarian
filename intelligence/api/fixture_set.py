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

from datetime import date

from ..health import build_report
from ..insights import (
    AnniversaryConfig, CanonConfig, ComparisonSet, DatedAlbum, SeriesConfig, SetItem, WorldAlbum,
    find_anniversaries, find_hidden_canon, find_series_progress, save_anniversaries, save_canon, save_series,
)
from ..insights.anniversaries import CARD_KIND as ANNIVERSARY_KIND
from ..insights.hidden_canon import CARD_KIND as CANON_KIND
from ..insights.series_completion import CARD_KIND as SERIES_KIND
from ..ingest.navidrome import normalize_album
from ..knowledge import KnowledgeReader
from ..graph import Limits
from ..resolution import unresolved
from ..store import generations, open_store
from ..store import repositories as repo
from .bodies import build_health_body, build_unresolved_body
from .insights import build_insights_body
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


def _insight_fixtures() -> dict[str, dict[str, Any]]:
    """Cards for three lenses in a store of their own, so the Phase 1 fixtures stay as they were."""
    with tempfile.TemporaryDirectory() as tmp:
        db = open_store(Path(tmp) / "insights.sqlite3")
        try:
            series = ComparisonSet("fx-series", "series", "Example label catalogue",
                                   tuple(SetItem(f"fx-{i}", f"Title {i}", 2000 + i) for i in range(4)))
            save_series(db, find_series_progress([series], ["fx-0", "fx-1"], SeriesConfig()), now=1_700_000_000.0)
            world = [WorldAlbum("fx-w1", "Loveless", "My Bloody Valentine", 1991, ("shoegaze", "dream pop"), 5000)]
            save_canon(db, find_hidden_canon(world, [], ["shoegaze", "dream pop"], CanonConfig()),
                       now=1_700_000_000.0)
            albums = [DatedAlbum("fx-a1", "Example Album", "Example Artist", "2016-06-01")]
            save_anniversaries(db, find_anniversaries(albums, [], date(2026, 6, 1), AnniversaryConfig()),
                               now=1_700_000_000.0)
            return {
                "insights_all_off.json": {
                    "request": "GET /api/insights", "response": build_insights_body(db),
                },
                "insights_three_on.json": {
                    "request": "GET /api/insights?lenses=series_completion,hidden_canon,anniversary",
                    "response": build_insights_body(db, enabled=(SERIES_KIND, CANON_KIND, ANNIVERSARY_KIND)),
                },
            }
        finally:
            db.close()


_K = {name: f"{n:08d}-0000-4000-8000-000000000000" for n, name in enumerate(
    ("artist", "second", "label", "work", "cover", "release", "group", "recording", "other"), start=1)}


def _knowledge_fixtures() -> dict[str, dict[str, Any]]:
    """Knowledge pages from a small store of their own (fixed ids and clock, no slice file needed)."""
    with tempfile.TemporaryDirectory() as tmp:
        db = open_store(Path(tmp) / "knowledge.sqlite3")
        try:
            return _knowledge(db)
        finally:
            db.close()


def _knowledge(db) -> dict[str, dict[str, Any]]:
    dump = dict(evidence_class="source_explicit", match_quality="exact_mbid", source="musicbrainz_dump")
    mb = {**dump, "source": "musicbrainz"}
    e = lambda kind, name, key, **kw: repo.upsert_entity(db, kind, name, mbid=_K[key], **kw)[0]
    artist = e("artist", "Example Artist", "artist")
    second = e("artist", "Example Guest", "second")
    label = e("label", "Example Records", "label")
    work = e("work", "Example Song", "work")
    cover = e("recording", "Example Song (cover)", "cover")
    release = e("release", "Example Album", "release", owned=True)
    group = e("release_group", "Example Album", "group")
    recording = e("recording", "Example Song", "recording")
    repo.add_edge(db, release, group, "member_of", **mb)
    repo.add_edge(db, recording, release, "appears_on", role="1/1", **mb)
    repo.add_edge(db, artist, release, "producer", role="executive", **dump)
    repo.add_edge(db, artist, recording, "instrument", role="guitar", **dump)
    repo.add_edge(db, second, recording, "vocal", role="lead vocals", **dump)
    repo.add_edge(db, label, release, "publisher", **dump)
    repo.add_edge(db, recording, work, "performance", **dump)
    repo.add_edge(db, cover, work, "performance", role="cover", **dump)
    repo.add_edge(db, artist, work, "composer", **dump)
    with db:
        db.execute("INSERT INTO release_facts (entity_id, date, country, status) VALUES (?, '2001-05-01', 'GB', 'official')",
                   (release,))
        db.execute("INSERT INTO artist_life_span (entity_id, begin_date, end_date, ended) VALUES (?, '1970', NULL, 0)", (artist,))
    pending = KnowledgeReader(db, clock=lambda: 2000.0)
    before = {"knowledge_person_slice_pending.json": ("GET /api/knowledge/person?mbid=" + _K["artist"],
                                                      pending.person_page(mbid=_K["artist"]))}
    with db:
        for key, value in (("dump_timestamp", "2026-11-04"), ("schema_sequence", "31"), ("loaded_at", "1000")):
            db.execute("INSERT INTO meta (key, value) VALUES (?, ?)", (f"musicbrainz_slice.{key}", value))
    r = KnowledgeReader(db, clock=lambda: 2000.0)
    pages = {
        "knowledge_album.json": (f"GET /api/knowledge/album?mbid={_K['release']}", r.album_dossier(mbid=_K["release"])),
        "knowledge_person.json": (f"GET /api/knowledge/person?mbid={_K['artist']}", r.person_page(mbid=_K["artist"])),
        "knowledge_label.json": (f"GET /api/knowledge/label?mbid={_K['label']}", r.label_page(mbid=_K["label"])),
        "knowledge_work.json": (f"GET /api/knowledge/work?mbid={_K['work']}", r.work_page(mbid=_K["work"])),
        "knowledge_recording_works.json": (f"GET /api/knowledge/recording-works?mbid={_K['recording']}",
                                           r.works_of_recording(mbid=_K["recording"])),
    }
    start = f"type=artist&mbid={_K['artist']}"
    first = r.connections_page(mbid=_K["artist"], type="artist", limits=Limits(max_depth=2, max_rows=200, page_size=2))
    pages["knowledge_connections.json"] = (f"GET /api/knowledge/connections?{start}&depth=2&limit=50",
                                           r.connections_page(mbid=_K["artist"], type="artist",
                                                              limits=Limits(max_depth=2, max_rows=200, page_size=50)))
    pages["knowledge_connections_page1.json"] = (f"GET /api/knowledge/connections?{start}&depth=2&limit=2", first)
    pages["knowledge_connections_page2.json"] = (
        f"GET /api/knowledge/connections?{start}&depth=2&limit=2&cursor=<next_cursor of knowledge_connections_page1.json>",
        r.connections_page(mbid=_K["artist"], type="artist", cursor=first["next_cursor"],
                           limits=Limits(max_depth=2, max_rows=200, page_size=2)))
    return {name: {"request": req, "response": body} for name, (req, body) in {**before, **pages}.items()}


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
        **_insight_fixtures(),
        **_knowledge_fixtures(),
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
