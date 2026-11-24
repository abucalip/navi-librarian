"""Scheduled Inbox import with real stores and simulated provider transports."""

from contextlib import closing
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from app.services import playlist_inbox_refresh as refresh
from app.services.playlist_reconcile import PlaylistReconciler
from app.worker_schedule import NOT_READY
from intelligence.store import ensure_store, open_readonly
from intelligence.store.playlist_editions import list_current_editions
from test_playlist_sync import CONFIG, Navidrome


HOSTED = "00000000-0000-4000-8000-000000000001"
RECORDING = "00000000-0000-4000-8000-000000000002"
SECOND_HOSTED = "00000000-0000-4000-8000-000000000011"
NEW_HOSTED = "00000000-0000-4000-8000-000000000012"
MISSING = "00000000-0000-4000-8000-000000000013"
JSPF = "https://musicbrainz.org/doc/jspf#playlist"
HOSTED_FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "listenbrainz_daily_jams.json").read_text())


class ListenBrainz:
    def __init__(self):
        self.requests = []
        self.hosted = {HOSTED: deepcopy(HOSTED_FIXTURE)}
        self.recommendations = [MISSING, RECORDING, RECORDING]
        self.updated = 1_800_000_000
        self.fail = set()

    def add_hosted(self, mbid, day):
        payload = deepcopy(HOSTED_FIXTURE)
        playlist = payload["playlist"]
        playlist["identifier"] = f"https://listenbrainz.org/playlist/{mbid}"
        playlist["date"] = f"2025-01-{day:02d}T00:00:00+00:00"
        playlist["extension"][JSPF]["last_modified_at"] = playlist["date"]
        self.hosted[mbid] = payload
        return playlist

    def respond(self, request):
        path = request.url.path
        self.requests.append(path)
        if path in self.fail:
            return httpx.Response(503)
        if path.endswith("/createdfor"):
            summaries = []
            for item in reversed(tuple(self.hosted.values())):
                playlist = dict(item["playlist"])
                del playlist["track"]
                summaries.append({"playlist": playlist})
            return httpx.Response(200, json={"playlists": summaries, "playlist_count": len(summaries), "offset": 0})
        if path.startswith("/1/playlist/"):
            return httpx.Response(200, json=self.hosted[path.rsplit("/", 1)[1]])
        if path.endswith("/recording") and "/cf/" in path:
            assert request.url.params["count"] == "25"
            return httpx.Response(200, json={"payload": {"last_updated": self.updated,
                "total_mbid_count": len(self.recommendations), "mbids": [
                    {"recording_mbid": mbid, "score": index} for index, mbid in enumerate(self.recommendations)
                ]}})
        assert path == "/1/metadata/recording/"
        assert request.method == "POST"
        assert json.loads(request.content)["recording_mbids"] == list(dict.fromkeys(self.recommendations))
        return httpx.Response(200, json={mbid: {
            "recording": {"name": "Recommendation", "length": 170000},
            "artist": {"name": "Artist"}, "release": {"name": "Album"},
        } for mbid in self.recommendations})


@pytest.fixture
def inbox(monkeypatch, tmp_path):
    path = tmp_path / "intelligence.sqlite3"
    ensure_store(path)
    upstream, nav = ListenBrainz(), Navidrome()
    nav.songs = [{"id": "owned", "title": "Fixture track 1", "musicBrainzId": RECORDING}]
    settings = {"listenbrainz_username": "fixture-listener", "listenbrainz_token": "test-token"}
    librarian = SimpleNamespace(_discovery_settings_read=lambda: settings, _navidrome_config=lambda: CONFIG)
    provider = refresh.PlaylistInboxClient
    monkeypatch.setattr(refresh, "PlaylistClient", nav.client)
    with httpx.Client(transport=httpx.MockTransport(upstream.respond)) as client:
        monkeypatch.setattr(refresh, "PlaylistInboxClient", lambda _, username, token:
                            provider(client, username, token=token, sleep=lambda _: None))
        yield SimpleNamespace(path=path, upstream=upstream, nav=nav, settings=settings,
                              run=lambda: refresh.refresh_once(librarian, path))


def editions(inbox):
    with closing(open_readonly(inbox.path)) as db:
        return {(e.snapshot.source_kind, e.snapshot.source_key): e for e in list_current_editions(db)}


def copies(inbox):
    return {playlist.name: playlist for playlist in (
        inbox.nav.client().get(row.id) for row in inbox.nav.client().list()
    )}


def test_refresh_keeps_one_rolling_copy_per_feed_and_skips_unchanged_details(inbox):
    inbox.upstream.add_hosted(SECOND_HOSTED, 5)
    assert inbox.run() is None
    initial = editions(inbox)
    assert len(initial) == 3
    cf = initial[("cf", "fixture-listener")].snapshot.tracks
    assert [track["recording_mbid"] for track in cf] == [MISSING, RECORDING, RECORDING]
    assert (cf[0]["title"], cf[0]["artist"], cf[0]["album"]) == ("Recommendation", "Artist", "Album")
    playlists = copies(inbox)
    assert set(playlists) == {"Discair · Daily Jams", refresh.CF_TITLE}
    assert all(not item.public and item.song_ids == ("owned", "owned") for item in playlists.values())
    assert inbox.upstream.requests.count("/1/metadata/recording/") == 1

    inbox.upstream.requests.clear()
    inbox.nav.requests.clear()
    assert inbox.run() is None
    assert editions(inbox) == initial
    assert len(inbox.upstream.requests) == 2
    assert not inbox.nav.requests

    newest = inbox.upstream.add_hosted(NEW_HOSTED, 6)
    newest["track"] = newest["track"][:1]
    inbox.upstream.recommendations = [RECORDING]
    inbox.upstream.updated += 1
    assert inbox.run() is None
    for name, playlist in copies(inbox).items():
        assert playlist.id == playlists[name].id
        assert not playlist.public and playlist.song_ids == ("owned",)
    assert editions(inbox)[("cf", "fixture-listener")].id != initial[("cf", "fixture-listener")].id

    current = editions(inbox)
    inbox.upstream.updated -= 1
    inbox.upstream.recommendations = [RECORDING, MISSING]
    assert inbox.run() is None
    assert editions(inbox) == current


def test_detail_failure_and_empty_recommendations_keep_prior_and_deletion_stays_unlinked(inbox):
    assert inbox.run() is None
    old = editions(inbox)
    original = copies(inbox)
    inbox.upstream.add_hosted(SECOND_HOSTED, 5)
    inbox.upstream.fail.add(f"/1/playlist/{SECOND_HOSTED}")
    inbox.upstream.recommendations = []
    assert inbox.run() is NOT_READY
    assert editions(inbox) == old
    assert copies(inbox) == original

    del inbox.nav.playlists[original["Discair · Daily Jams"].id]
    assert PlaylistReconciler(inbox.path).run_once(inbox.nav.client()) is None
    inbox.upstream.fail.clear()
    assert inbox.run() is None
    assert set(copies(inbox)) == {refresh.CF_TITLE}
    assert ("hosted", SECOND_HOSTED) in editions(inbox)


def test_cf_runs_after_hosted_failure_and_defers_writes_on_scan_change(inbox):
    inbox.upstream.fail.add("/1/user/fixture-listener/playlists/createdfor")
    inbox.nav.after_search = lambda: inbox.nav.scan.update(lastScan="another-scan")
    assert inbox.run() is NOT_READY
    assert set(editions(inbox)) == {("cf", "fixture-listener")}
    assert not inbox.nav.playlists

    inbox.nav.after_search = lambda: None
    assert inbox.run() is NOT_READY
    assert set(copies(inbox)) == {refresh.CF_TITLE}


def test_unconfigured_does_not_contact_providers(inbox, monkeypatch):
    monkeypatch.delenv("LISTENBRAINZ_TOKEN", raising=False)
    inbox.settings.pop("listenbrainz_token")
    assert inbox.run() is None
    assert not inbox.upstream.requests and not inbox.nav.requests


def test_empty_hosted_listing_still_creates_a_private_cf_copy(inbox):
    inbox.upstream.hosted.clear()
    inbox.nav.songs.clear()
    assert inbox.run() is None
    assert set(editions(inbox)) == {("cf", "fixture-listener")}
    playlist = copies(inbox)[refresh.CF_TITLE]
    assert not playlist.public and playlist.song_ids == ()
