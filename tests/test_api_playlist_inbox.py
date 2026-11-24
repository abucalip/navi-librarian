from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
from threading import Event
from types import SimpleNamespace
from urllib.error import URLError

from fastapi.testclient import TestClient
import pytest

from acquisition.state import save_job
from acquisition.track_service import track_job_album
from app import main
from app.api import playlist_inbox
from app.api.dependencies import get_librarian
from app.services.playlist_reconcile import PlaylistReconciler
from discovery import playlist_download
from discovery.playlist_inbox import SNAPSHOT_MAX_AGE
from discovery.playlist_sync import sync_edition
from discovery.recommendations import music_key
from discovery.search.index import IndexView, OwnedData
from intelligence.store import ensure_store, open_writer
from intelligence.store.playlist_editions import (
    CopyIntent, ManagedCopy, PlaylistSnapshot, publish_edition, record_copy_intent, save_managed_copy,
)
from integrations.navidrome.playlists import PlaylistClient
from test_acquisition_track import FakeLibrarian as AcquisitionLibrarian, peer
from test_playlist_sync import CONFIG, Navidrome

NOW = 1_800_000_000
URL = "/api/playlists/inbox"
MBID = "90000000-0000-4000-8000-000000000001"
EXAMPLES = json.loads((Path(__file__).parent / "fixtures" / "listenbrainz_inbox_responses.json").read_text())


class FakeLibrarian:
    def __init__(self, directory):
        self.DATA_DIR = Path(directory)
        self.DISCOVERY_DB = self.DATA_DIR / "navidrome_discovery.sqlite3"
        self.settings = {}

    def _discovery_settings_read(self):
        return dict(self.settings)

    def _discovery_settings_write(self, values):
        self.settings.update(values)

    _music_key = staticmethod(music_key)
    _navidrome_config = staticmethod(lambda: CONFIG)


@pytest.fixture
def inbox(tmp_path, monkeypatch):
    librarian = FakeLibrarian(tmp_path)
    store = tmp_path / playlist_inbox.STORE_FILE
    ensure_store(store)
    owned = OwnedData(None, NOW, (), (), (
        {"id": "owned", "name": "Owned", "artist": "Artist", "album": "Album", "recording_mbid": MBID},
        {"id": "live", "name": "Versions (Live)", "artist": "Artist", "album": "Album"},
    ))
    view = SimpleNamespace(value=IndexView("fresh", owned, None))
    monkeypatch.delenv("LISTENBRAINZ_TOKEN", raising=False)
    monkeypatch.setattr(playlist_inbox, "time", lambda: NOW)
    monkeypatch.setattr(playlist_inbox, "owned_view", lambda _: view.value)
    monkeypatch.setattr(main, "get_librarian", lambda: librarian)
    monkeypatch.setattr(main, "_AUTH_SECRET", b"inbox-test-signing-secret")
    monkeypatch.setitem(main.app.dependency_overrides, get_librarian, lambda: librarian)
    with closing(TestClient(main.app, follow_redirects=False)) as client:
        yield SimpleNamespace(client=client, librarian=librarian, store=store, view=view)


def sign_in(client):
    response = client.post("/api/auth/setup", json={
        "username": "owner",
        "password": "fixture-only-password",
        "password_confirmation": "fixture-only-password",
    })
    assert response.status_code == 200


def make_snapshot(source_kind="hosted", source_key="daily-jams"):
    tracks = tuple(
        {"position": position, "title": title, "artist": "Artist", "album": album, "recording_mbid": mbid}
        for position, (title, album, mbid) in enumerate((
            ("Owned", "Album", MBID), ("Missing", "Album", None), ("Versions", "Album", None),
            ("Owned", "Album", MBID), ("No Album", None, None), ("Name?", "Album", None),
        ))
    )
    return PlaylistSnapshot(source_kind, source_key, "edition", {"title": "A mix"}, tracks)


def publish(path, snapshot, fetched_at=NOW, expected=None):
    with closing(open_writer(path)) as db:
        return publish_edition(db, snapshot, expected_current_id=expected, fetched_at=fetched_at)


def seed_jobs(path):
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("""CREATE TABLE discovery_acquisitions (
            artist_key TEXT, album_key TEXT, artist TEXT, album TEXT, status TEXT,
            details_json TEXT, candidate_json TEXT, settings_json TEXT, created_at REAL, updated_at REAL,
            PRIMARY KEY (artist_key, album_key)
        )""")
    services = {"init": lambda: None, "db_path": path, "music_key": music_key, "clock": lambda: NOW}
    for title, status, kind in (
        ("Owned", "imported", "track"), ("Missing", "downloading", "track"),
        ("Versions", "downloading", "track"), ("No Album", "downloading", "track"),
        ("Name!", "downloading", "track"), ("Album job", "downloading", "album"),
    ):
        save_job("Artist", track_job_album("Album", title), status, {
            "kind": kind, "album_name": "Album", "track_title": title,
        }, settings={"secret": "fixture-private"}, services=services)


def test_real_auth_middleware_protects_both_routes(inbox):
    edition = publish(inbox.store, make_snapshot())
    for url in (URL, f"{URL}/{edition}"):
        assert inbox.client.get(url).status_code == 401
    sign_in(inbox.client)
    for url in (URL, f"{URL}/{edition}"):
        assert inbox.client.get(url).status_code == 200
    assert not inbox.librarian.DISCOVERY_DB.exists()


def test_empty_unconfigured_and_missing_ids(inbox):
    sign_in(inbox.client)
    response = inbox.client.get(URL)
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json() == EXAMPLES["unconfigured"]
    inbox.librarian.settings["listenbrainz_username"] = "owner"
    assert inbox.client.get(URL).json()["state"] == "unconfigured"
    inbox.librarian.settings["listenbrainz_token"] = "fixture-token"
    assert inbox.client.get(URL).json() == EXAMPLES["empty"]
    assert inbox.client.get(f"{URL}/1").status_code == 404
    for value in ("0", str(2**63), "no-id"):
        assert inbox.client.get(f"{URL}/{value}").status_code == 422


def test_mixed_stale_and_zero_owned_contract(inbox):
    sign_in(inbox.client)
    seed_jobs(inbox.librarian.DISCOVERY_DB)
    snapshot = replace(make_snapshot(), metadata={"title": "A mix", "generated_at": "2027-01-08T08:00:00+00:00"})
    old = publish(inbox.store, snapshot, NOW - SNAPSHOT_MAX_AGE)
    assert publish(inbox.store, snapshot, expected=old) == old
    with closing(open_writer(inbox.store)) as db:
        record_copy_intent(db, "daily", CopyIntent(PlaylistClient(CONFIG).target_key, "private-token", old))
        assert save_managed_copy(db, ManagedCopy("daily", "fixture-private"), expected=None)
    zero_snapshot = replace(make_snapshot("local", "rediscover"), tracks=(
        {"position": 0, "title": "Elsewhere", "artist": "Artist", "album": "Album"},
        {"position": 1, "title": "Album job", "artist": "Artist", "album": "Album"},
    ))
    zero = publish(inbox.store, zero_snapshot)
    result = inbox.client.get(URL).json()
    assert result == EXAMPLES["list"]
    assert result["state"] == "ready"
    assert result["listenbrainz_configured"] is False
    assert [(row["edition_id"], row["owned_count"], row["stale"]) for row in result["items"]] == [
        (zero, 0, False), (old, 2, True),
    ]
    assert all("tracks" not in row for row in result["items"])
    detail = inbox.client.get(f"{URL}/{old}")
    assert detail.headers["Cache-Control"] == "no-store"
    assert "fixture-private" not in detail.text
    assert detail.json() == EXAMPLES["mixed_detail"]
    rows = detail.json()["tracks"]
    assert [row["position"] for row in rows] == list(range(6))
    assert [row["match_state"] for row in rows] == ["owned", "missing", "ambiguous", "owned", "missing", "missing"]
    assert [row["song_id"] for row in rows] == ["owned", None, None, "owned", None, None]
    assert [row["acquisition_status"] for row in rows] == ["imported", "downloading", None, "imported", None, None]
    zero_detail = inbox.client.get(f"{URL}/{zero}").json()
    assert zero_detail == EXAMPLES["zero_owned_detail"]
    assert all(row["acquisition_status"] is None for row in zero_detail["tracks"])


def test_copy_state_is_bound_to_target_and_exact_edition(inbox, monkeypatch):
    sign_in(inbox.client)
    snapshot = make_snapshot()
    earlier = publish(inbox.store, snapshot)
    current = publish(inbox.store, replace(snapshot, tracks=()), expected=earlier)
    target = PlaylistClient(CONFIG).target_key
    link = ManagedCopy("daily", "copy-id")
    with closing(open_writer(inbox.store)) as db:
        record_copy_intent(db, "different-server", CopyIntent("other-target", "other-token", earlier))
        assert save_managed_copy(db, ManagedCopy("different-server", "other-copy"), expected=None)
        record_copy_intent(db, "daily", CopyIntent(target, "pending-token", current))

        def state(edition):
            return inbox.client.get(f"{URL}/{edition}").json()["navidrome_sync_state"]

        assert inbox.client.get(URL).json()["items"][0]["navidrome_sync_state"] == "pending"
        assert state(current) == "pending"
        assert state(earlier) == "not_linked"
        assert save_managed_copy(db, link, expected=None)
        assert state(current) == "linked"
        assert save_managed_copy(db, replace(link, unlinked=True), expected=link)
        assert state(current) == "unlinked"

    def unconfigured():
        raise ValueError("Navidrome unconfigured")

    monkeypatch.setattr(inbox.librarian, "_navidrome_config", unconfigured)
    assert state(current) == "unconfigured"


def test_historical_and_empty_editions_and_unavailable_index(inbox):
    sign_in(inbox.client)
    snapshot = make_snapshot()
    previous = publish(inbox.store, snapshot)
    current = publish(inbox.store, replace(snapshot, tracks=()), expected=previous)
    assert [item["edition_id"] for item in inbox.client.get(URL).json()["items"]] == [current]
    assert inbox.client.get(f"{URL}/{current}").json()["tracks"] == []
    inbox.view.value = IndexView("building", None, "index_building")
    detail = inbox.client.get(f"{URL}/{previous}").json()
    assert detail["index_state"] == "building"
    assert detail["owned_count"] is None
    assert all(row["match_state"] is None for row in detail["tracks"])


def test_reads_work_under_reserved_write_locks(inbox, monkeypatch):
    sign_in(inbox.client)
    edition = publish(inbox.store, make_snapshot())
    seed_jobs(inbox.librarian.DISCOVERY_DB)
    with closing(sqlite3.connect(inbox.store)) as knowledge, closing(sqlite3.connect(inbox.librarian.DISCOVERY_DB)) as jobs:
        knowledge.execute("BEGIN IMMEDIATE")
        jobs.execute("BEGIN IMMEDIATE")
        statements = []
        connect = sqlite3.connect

        def traced_connect(*args, **kwargs):
            connection = connect(*args, **kwargs)
            connection.set_trace_callback(statements.append)
            return connection

        monkeypatch.setattr(sqlite3, "connect", traced_connect)
        assert inbox.client.get(URL).status_code == 200
        assert inbox.client.get(f"{URL}/{edition}").status_code == 200
        assert statements
        assert {sql.split()[0].upper() for sql in statements} == {"ATTACH", "SELECT"}


def test_unavailable_store_is_not_empty_and_is_not_recreated(inbox, tmp_path):
    sign_in(inbox.client)
    inbox.librarian.DATA_DIR = tmp_path / "absent"
    assert inbox.client.get(URL).status_code == 503
    assert inbox.client.get(f"{URL}/1").status_code == 503
    assert not inbox.librarian.DATA_DIR.exists()


@pytest.fixture
def download(inbox, monkeypatch):
    remote = Navidrome()
    remote.songs = [{"id": "owned", "title": "Owned", "musicBrainzId": MBID},
                    {"id": "live", "title": "Versions (Live)", "artist": "Artist", "album": "Album"}]
    monkeypatch.setattr(playlist_download, "PlaylistClient", remote.client)
    monkeypatch.setattr(inbox.librarian, "_navidrome_config", lambda: CONFIG, raising=False)
    root = inbox.librarian.DATA_DIR
    acquisition = AcquisitionLibrarian(root)
    for name in dir(acquisition):
        if name.startswith(("_discovery_", "_slskd_", "_DISCOVERY_")) and not hasattr(inbox.librarian, name):
            monkeypatch.setattr(inbox.librarian, name, getattr(acquisition, name), raising=False)
    monkeypatch.setattr(inbox.librarian, "MUSIC_DIR", acquisition.MUSIC_DIR, raising=False)
    monitor = {}
    service = playlist_download.track_service
    monkeypatch.setattr(service, "_spawn", lambda _, ctx, candidate, settings: monitor.update(
        ctx=ctx, candidate=candidate,
    ) or True)
    monkeypatch.setattr(service, "collect_search_responses", lambda *args, **kwargs: {
        "payload_by_peer": {"peer": peer("peer", ("Artist/Album/Missing.flac", 3))},
        "search_attempts": 1,
    })
    edition = publish(inbox.store, make_snapshot())
    return SimpleNamespace(client=inbox.client, root=f"{URL}/{edition}/tracks", edition=edition,
                           acquisition=acquisition, remote=remote, monitor=monitor, service=service)


def test_download_auth_positions_and_ownership_recheck(inbox, download):
    action = f"{download.root}/1/download"
    assert download.client.post(action).status_code == 401
    sign_in(download.client)
    assert inbox.client.get(f"{URL}/{download.edition}").json()["tracks"][1]["match_state"] == "missing"
    download.remote.songs.append({"id": "new", "title": "Missing", "artist": "Artist", "album": "Album"})
    response = download.client.post(action, json={"title": "Untrusted override"})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {"edition_id": download.edition, "position": 1, "ok": True,
                               "status": "owned", "song_id": "new"}
    assert download.client.post(f"{download.root}/6/download").status_code == 404
    assert download.client.post(f"{download.root}/-1/download").status_code == 422
    assert download.client.post(f"{URL}/99/tracks/0/download").status_code == 404
    assert not download.acquisition.queued


def test_download_refuses_ambiguous_unresolved_and_changing_inventory(download, monkeypatch):
    sign_in(download.client)
    monkeypatch.setattr(playlist_download, "lookup_recording", lambda *args, **kwargs: {})
    monkeypatch.setattr(playlist_download, "lookup_inbox_album", lambda *args, **kwargs: None)
    for position, code in ((2, "ambiguous_track"), (4, "unresolved_album")):
        response = download.client.post(f"{download.root}/{position}/download")
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == code
    download.remote.after_search = lambda: download.remote.scan.update(scanning=True)
    response = download.client.post(f"{download.root}/1/download")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "ownership_unavailable"
    assert not download.acquisition.queued
    assert not download.acquisition.jobs


def test_download_rechecks_ownership_with_listenbrainz_metadata(inbox, download, monkeypatch):
    sign_in(download.client)
    edition = publish(inbox.store, replace(make_snapshot(), tracks=(
        {"position": 0, "artist": "Artist", "title": "Missing", "recording_mbid": MBID},
    )), expected=download.edition)
    download.remote.songs = [{"id": "local", "title": "Missing", "artist": "Artist", "album": "Album"}]
    inbox.librarian.settings["listenbrainz_token"] = "fixture-token"
    calls = []

    def lookup(artist, title, *, token):
        calls.append((artist, title, token))
        return {"artist_credit_name": artist, "recording_name": title, "recording_mbid": MBID,
                "release_mbid": "90000000-0000-4000-8000-000000000002", "release_name": "Album"}

    monkeypatch.setattr(playlist_download, "lookup_recording", lookup)
    response = download.client.post(f"{URL}/{edition}/tracks/0/download")
    assert response.json()["song_id"] == "local"
    assert calls == [("Artist", "Missing", "fixture-token")]
    assert not download.acquisition.queued


def test_download_falls_back_from_conflicting_mapper_and_keeps_polling_key(inbox, download, monkeypatch):
    sign_in(download.client)
    edition = publish(inbox.store, replace(make_snapshot(), tracks=(
        {"position": 0, "artist": "Artist", "title": "Missing"},
    )), expected=download.edition)
    calls = []

    def lookup(*args, **kwargs):
        calls.append("listenbrainz")
        return {"artist_credit_name": "Artist", "recording_name": "Missing (Live)",
                "recording_mbid": MBID, "release_name": "Wrong"}

    def fallback(artist, title, **kwargs):
        calls.append("musicbrainz")
        assert (artist, title) == ("Artist", "Missing")
        assert kwargs["mapped_release"] is None
        return "90000000-0000-4000-8000-000000000002", "Album", 2020

    monkeypatch.setattr(playlist_download, "lookup_recording", lookup)
    monkeypatch.setattr(playlist_download, "lookup_inbox_album", fallback)
    action = f"{URL}/{edition}/tracks/0/download"
    result = download.client.post(action).json()
    assert (result["status"], result["album"], result["job_album"]) == (
        "queued", "Album", track_job_album("Album", "Missing"),
    )
    assert calls == ["listenbrainz", "musicbrainz"]
    assert download.monitor["ctx"]["year"] == 2020
    assert len(download.acquisition.queued) == 1

    def unavailable(*args, **kwargs):
        raise URLError("fixture upstream unavailable")

    monkeypatch.setattr(playlist_download, "lookup_inbox_album", unavailable)
    assert download.client.post(action).json()["status"] == "recovery_started"
    response = download.client.post(f"{download.root}/4/download")
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "metadata_unavailable"
    assert len(download.acquisition.queued) == 1


def test_download_will_not_reopen_a_colliding_dismissed_job(download):
    sign_in(download.client)
    job_album = track_job_album("Album", "Name!")
    download.acquisition._discovery_save_acquisition_job("Artist", job_album, "dismissed", {
        "kind": "track", "album_name": "Album", "track_title": "Name!",
    })
    reply = download.client.post(f"{download.root}/5/download").json()
    assert reply["status"] == "identity_conflict"
    assert list(download.acquisition.jobs.values())[0]["status"] == "dismissed"
    assert not download.acquisition.queued


def test_concurrent_downloads_share_one_job_across_editions(inbox, download, monkeypatch):
    sign_in(download.client)
    second = publish(inbox.store, make_snapshot("local", "second"))
    worker_entered = Event()
    follower_waiting = Event()

    class ObservedFuture(Future):
        def result(self, timeout=None):
            follower_waiting.set()
            return super().result(timeout)

    def wait_for_follower():
        worker_entered.set()
        assert follower_waiting.wait(5)

    monkeypatch.setattr(playlist_download, "Future", ObservedFuture)
    download.remote.after_search = wait_for_follower
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(download.client.post, f"{download.root}/1/download")
        assert worker_entered.wait(5)
        other = executor.submit(download.client.post, f"{URL}/{second}/tracks/1/download")
        replies = [future.result(10) for future in (first, other)]
    assert [reply.json()["edition_id"] for reply in replies] == [download.edition, second]
    assert [reply.json()["status"] for reply in replies] == ["queued", "queued"]
    assert len(download.acquisition.queued) == len(download.acquisition.jobs) == 1
    response = download.client.post(f"{download.root}/1/download")
    assert response.json()["status"] == "recovery_started"
    assert len(download.acquisition.queued) == 1


def test_download_import_and_reconcile_disposable_fixture(inbox, download, monkeypatch):
    sign_in(download.client)
    client = download.remote.client()
    linked = sync_edition(inbox.store, client, feed_key="daily-jams", edition_id=download.edition,
                          name="Fixture playlist", owned=inbox.view.value.data)
    assert client.get(linked.playlist_id).song_ids == ("owned", "owned")
    response = download.client.post(f"{download.root}/1/download")
    assert response.json()["status"] == "queued"
    folder = download.acquisition.downloads / "Album"
    folder.mkdir()
    (folder / "Missing.flac").write_bytes(b"abc")
    monkeypatch.setattr(download.service, "notify_imported", lambda *_: None)
    assert download.service.import_completed_track(
        inbox.librarian, download.monitor["ctx"], download.monitor["candidate"], folder,
    ) == "imported"
    assert (download.acquisition.MUSIC_DIR / "Artist" / "Album" / "Missing.flac").read_bytes() == b"abc"
    download.remote.songs.append({"id": "new", "title": "Missing", "artist": "Artist", "album": "Album"})
    download.remote.scan.update(lastScan="after-import", count=3)
    PlaylistReconciler(inbox.store).run_once(client)
    playlist = client.get(linked.playlist_id)
    assert playlist.song_ids == ("owned", "new", "owned")
    assert not playlist.public
