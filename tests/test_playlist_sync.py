from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from threading import Event
from urllib.parse import parse_qs

import httpx
import pytest

from app.services.playlist_reconcile import PlaylistReconciler
from app.worker_schedule import NOT_READY
from discovery.playlist_sync import SyncResult, sync_edition
from discovery.search.index import OwnedData
from integrations.navidrome.playlists import PlaylistClient, PlaylistProviderError
from intelligence.store import open_store, open_writer
from intelligence.store.playlist_editions import (
    PlaylistSnapshot,
    get_copy_intent,
    get_edition,
    get_managed_copy,
    publish_edition,
    save_managed_copy,
)

FIRST = "00000000-0000-4000-8000-000000000001"
SECOND = "00000000-0000-4000-8000-000000000002"
TITLE = "Discair · Daily Jams"
CONFIG = ("http://fixture.invalid", "fixture", "fixture-password")
LIBRARY = OwnedData(1, 0, (), (), (
    {"id": "one", "recording_mbid": FIRST},
    {"id": "two", "recording_mbid": SECOND},
    {"id": "live", "artist": "Band", "name": "Song (Live)", "album": "Live"},
    {"id": "studio", "artist": "Band", "name": "Song", "album": "Album"},
))


class Navidrome:
    """Model the 0.64.2 wire format and inject failures at the request boundary."""

    def __init__(self):
        self.playlists = {}
        self.requests = []
        self.before_create = lambda: None
        self.drop_create_reply = False
        self.drop_update_reply = False
        self.ignore_privacy = False
        self.scan = {"scanning": False, "lastScan": "2026-11-24T10:00:00Z", "count": 1}
        self.songs = [{"id": "one", "title": "One", "musicBrainzId": FIRST}]
        self.after_search = lambda: None
        self.playlist_error = None

    def client(self, config=CONFIG):
        return PlaylistClient(config, client_factory=lambda **kw: httpx.Client(
            transport=httpx.MockTransport(self.respond), **kw,
        ))

    def respond(self, request):
        assert request.method == "POST" and not request.url.query
        form = parse_qs(request.content.decode(), keep_blank_values=True)
        assert {"u", "t", "s", "v", "c", "f"} <= form.keys()
        method = request.url.path.removeprefix("/rest/").removesuffix(".view")
        self.requests.append((method, form))
        if method == "getScanStatus":
            return self.response(scanStatus=self.scan)
        if method == "search3":
            assert form["query"] == [""]
            assert form["artistCount"] == form["albumCount"] == ["0"]
            offset, count = int(form["songOffset"][0]), int(form["songCount"][0])
            self.after_search()
            return self.response(searchResult3={"song": self.songs[offset:offset + count]})
        if method == "getPlaylists":
            listing = [{key: value for key, value in row.items() if key != "entry"}
                       for row in self.playlists.values()]
            return self.response(playlists={"playlist": listing} if listing else {})
        if method == "getPlaylist":
            if self.playlist_error is not None:
                return self.response(status="failed", error={"code": self.playlist_error})
            row = self.playlists.get(form["id"][0])
            return self.response(playlist=row) if row else self.response(status="failed", error={"code": 70})
        if method == "createPlaylist" and "name" in form:
            self.before_create()
            assert "songId" not in form
            playlist_id = f"playlist-{len(self.playlists) + 1}"
            row = {
                "id": playlist_id, "owner": CONFIG[1], "name": form["name"][0],
                "songCount": 0, "entry": [],
            }
            self.playlists[playlist_id] = row
            if self.drop_create_reply:
                raise httpx.ReadTimeout("reply lost", request=request)
            return self.response(playlist=row)

        row = self.playlists[form["playlistId"][0]]
        if method == "createPlaylist":
            # No songId means Navidrome leaves old tracks alone.
            if song_ids := form.get("songId"):
                assert not row.get("public")
                row["entry"] = [{"id": track} for track in song_ids]
            row["songCount"] = len(row["entry"])
            return self.response(playlist=row)

        assert method == "updatePlaylist"
        if "name" in form:
            row["name"] = form["name"][0]
            row["comment"] = form["comment"][0]
            assert form["public"] == ["false"]
            if not self.ignore_privacy:
                row.pop("public", None)
        if "songIndexToRemove" in form:
            removed = {int(index) for index in form["songIndexToRemove"]}
            row["entry"] = [item for index, item in enumerate(row["entry"]) if index not in removed]
            row["songCount"] = len(row["entry"])
        if self.drop_update_reply:
            raise httpx.ReadTimeout("reply lost", request=request)
        return self.response()

    @staticmethod
    def response(**fields):
        return httpx.Response(200, json={"subsonic-response": {"status": "ok", **fields}})


@pytest.fixture
def inbox(tmp_path):
    path = tmp_path / "intelligence.sqlite3"
    edition_id = publish(path, (FIRST, None, SECOND, FIRST, "ambiguous"))
    return path, edition_id


def publish(path, tracks, *, source="hosting-1", previous=None):
    rows = tuple(
        {"position": index, "artist": "Band", "title": "Song", "album": "Album"}
        if track == "ambiguous" else {"position": index, "recording_mbid": track}
        for index, track in enumerate(tracks)
    )
    with closing(open_store(path)) as writer:
        return publish_edition(writer, PlaylistSnapshot("hosted", source, source, {}, rows),
                               expected_current_id=previous, fetched_at=100)


def sync(inbox, client, *, owned=LIBRARY):
    path, edition_id = inbox
    return sync_edition(path, client, feed_key="daily-jams", edition_id=edition_id, name=TITLE, owned=owned)


def assert_songs(remote, playlist_id, song_ids):
    row = remote.playlists[playlist_id]
    assert row["name"] == TITLE
    assert row.get("public") is not True
    assert row["entry"] == [{"id": value} for value in song_ids]


def test_rolls_same_private_id_in_source_order_and_clears_zero_owned(inbox):
    remote = Navidrome()
    unrelated = {"id": "personal", "owner": CONFIG[1], "name": TITLE, "songCount": 1, "entry": [{"id": "mine"}]}
    remote.playlists["personal"] = unrelated.copy()

    result = sync(inbox, remote.client())
    assert result == SyncResult("synced", "playlist-2")
    assert_songs(remote, result.playlist_id, ["one", "two", "one"])
    remote.requests.clear()
    assert sync(inbox, remote.client()) == result
    assert [method for method, _ in remote.requests] == ["getPlaylist"]

    path, _ = inbox
    next_edition = (path, publish(path, (SECOND, FIRST), source="hosting-2"))
    assert sync(next_edition, remote.client()) == result
    assert_songs(remote, result.playlist_id, ["two", "one"])
    assert sync(inbox, remote.client()) == SyncResult("superseded")
    assert_songs(remote, result.playlist_id, ["two", "one"])

    assert sync(next_edition, remote.client(), owned=replace(LIBRARY, songs=())) == result
    assert_songs(remote, result.playlist_id, [])
    assert remote.playlists["personal"] == unrelated
    assert len(remote.playlists) == 2


def test_lost_create_reply_recovers_same_copy_and_serializes_concurrent_calls(inbox):
    remote = Navidrome()
    remote.drop_create_reply = True
    entered, release = Event(), Event()

    def pause_create():
        with closing(open_writer(inbox[0])) as db:
            assert get_copy_intent(db, "daily-jams") is not None
            assert get_managed_copy(db, "daily-jams") is None
        entered.set()
        assert release.wait(5)

    remote.before_create = pause_create
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(sync, inbox, remote.client())
        try:
            assert entered.wait(5)
            assert sync(inbox, remote.client()) == SyncResult("busy")
        finally:
            release.set()
        assert first.result(timeout=5) == SyncResult("pending")

    assert sync(inbox, remote.client()) == SyncResult("synced", "playlist-1")
    assert_songs(remote, "playlist-1", ["one", "two", "one"])
    assert len(remote.playlists) == 1
    assert sum(method == "createPlaylist" and "name" in form for method, form in remote.requests) == 1


def test_unknown_create_waits_even_when_list_is_empty(inbox):
    remote = Navidrome()

    def timeout():
        raise httpx.ReadTimeout("server outcome unknown")

    remote.before_create = timeout
    assert sync(inbox, remote.client()) == SyncResult("pending")
    assert sync(inbox, remote.client()) == SyncResult("pending")
    assert sum(method == "createPlaylist" for method, _ in remote.requests) == 1
    assert not remote.playlists


def test_multiple_recovery_candidates_are_left_alone(inbox):
    remote = Navidrome()
    remote.drop_create_reply = True
    assert sync(inbox, remote.client()) == SyncResult("pending")
    remote.playlists["duplicate"] = {**remote.playlists["playlist-1"], "id": "duplicate"}
    remote.requests.clear()
    assert sync(inbox, remote.client()) == SyncResult("conflict")
    assert [method for method, _ in remote.requests] == ["getPlaylists"]


def test_resume_after_privacy_update_reply_is_lost(inbox):
    remote = Navidrome()
    remote.drop_update_reply = True
    with pytest.raises(PlaylistProviderError, match="did not confirm"):
        sync(inbox, remote.client())
    remote.drop_update_reply = False
    assert sync(inbox, remote.client()) == SyncResult("synced", "playlist-1")
    assert_songs(remote, "playlist-1", ["one", "two", "one"])


def test_never_writes_tracks_before_privacy_is_confirmed(inbox):
    remote = Navidrome()
    remote.ignore_privacy = True

    def respond(request):
        response = original(request)
        if "playlist-1" in remote.playlists:
            remote.playlists["playlist-1"]["public"] = True
        return response

    original, remote.respond = remote.respond, respond
    with pytest.raises(PlaylistProviderError, match="private managed playlist"):
        sync(inbox, remote.client())
    assert remote.playlists["playlist-1"]["entry"] == []


def test_missing_index_does_not_clear_and_missing_remote_copy_is_not_recreated(inbox):
    remote = Navidrome()
    assert sync(inbox, remote.client(), owned=None) == SyncResult("index_unavailable")
    assert not remote.requests
    assert sync(inbox, remote.client()) == SyncResult("synced", "playlist-1")
    remote.playlists.clear()
    assert sync(inbox, remote.client()) == SyncResult("missing")
    assert not remote.playlists
    with closing(open_writer(inbox[0])) as db:
        link = get_managed_copy(db, "daily-jams")
        assert save_managed_copy(db, replace(link, unlinked=True), expected=link)
    assert sync(inbox, remote.client()) == SyncResult("unlinked")
    assert not remote.playlists


def test_link_is_bound_to_target_and_requires_ownership_marker(inbox):
    remote = Navidrome()
    assert sync(inbox, remote.client()) == SyncResult("synced", "playlist-1")
    remote.requests.clear()
    assert sync(inbox, remote.client(("http://different.invalid", *CONFIG[1:]))) == SyncResult("conflict")
    assert not remote.requests
    assert sync(inbox, remote.client((*CONFIG[:2], "rotated-password"))) == SyncResult("synced", "playlist-1")
    remote.playlists["playlist-1"]["comment"] = "Personal playlist"
    remote.requests.clear()
    assert sync(inbox, remote.client()) == SyncResult("conflict")
    assert [method for method, _ in remote.requests] == ["getPlaylist"]


def test_first_copy_with_zero_matches_is_private_and_empty(inbox):
    remote = Navidrome()
    result = sync(inbox, remote.client(), owned=replace(LIBRARY, songs=()))
    assert result == SyncResult("synced", "playlist-1")
    assert_songs(remote, result.playlist_id, [])
    assert [method for method, _ in remote.requests].count("createPlaylist") == 1


def test_incomplete_track_read_refuses_positional_clear(inbox):
    remote = Navidrome()
    assert sync(inbox, remote.client()) == SyncResult("synced", "playlist-1")
    remote.playlists["playlist-1"]["songCount"] += 1
    remote.requests.clear()
    with pytest.raises(PlaylistProviderError, match="every playlist track"):
        sync(inbox, remote.client(), owned=replace(LIBRARY, songs=()))
    assert [method for method, _ in remote.requests] == ["getPlaylist"]


def test_reconcile_after_scan_and_worker_refresh(inbox):
    remote = Navidrome()
    unrelated = {"id": "personal", "owner": CONFIG[1], "name": TITLE, "songCount": 1, "entry": [{"id": "mine"}]}
    remote.playlists["personal"] = unrelated.copy()
    result = sync(inbox, remote.client(), owned=replace(LIBRARY, songs=LIBRARY.songs[:1]))
    playlist_id = result.playlist_id
    assert_songs(remote, playlist_id, ["one", "one"])
    worker = PlaylistReconciler(inbox[0])
    worker.run_once(remote.client())

    remote.songs.append({"id": "two", "title": "Two", "musicBrainzId": SECOND})
    remote.scan["scanning"] = True
    remote.requests.clear()
    assert worker.run_once(remote.client()) is NOT_READY
    assert [method for method, _ in remote.requests] == ["getScanStatus"]
    assert_songs(remote, playlist_id, ["one", "one"])

    remote.scan.update(scanning=False, count=2, lastScan="2026-11-24T10:01:00Z")
    assert worker.run_once(remote.client()) is None
    assert_songs(remote, playlist_id, ["one", "two", "one"])
    assert remote.playlists["personal"] == unrelated
    remote.requests.clear()
    worker.run_once(remote.client())
    assert [method for method, _ in remote.requests] == ["getScanStatus"]

    path, old_edition = inbox
    current = publish(path, (SECOND, FIRST, SECOND), previous=old_edition)
    assert worker.run_once(remote.client(), worker_refresh=True) is None
    assert_songs(remote, playlist_id, ["two", "one", "two"])
    with closing(open_writer(path)) as db:
        assert get_copy_intent(db, "daily-jams").edition_id == current


def test_reconcile_retries_if_scan_changes_during_inventory(inbox):
    remote = Navidrome()
    assert sync(inbox, remote.client()).state == "synced"
    worker = PlaylistReconciler(inbox[0])
    remote.after_search = lambda: remote.scan.update(lastScan="2026-11-24T10:01:00Z")
    remote.requests.clear()
    assert worker.run_once(remote.client()) is NOT_READY
    assert [method for method, _ in remote.requests] == ["getScanStatus", "search3", "getScanStatus"]
    assert_songs(remote, "playlist-1", ["one", "two", "one"])
    assert worker.run_once(remote.client()) is None
    assert_songs(remote, "playlist-1", ["one", "one"])


def test_reconcile_unlinks_only_confirmed_missing_and_keeps_snapshot(inbox):
    remote = Navidrome()
    client = remote.client()
    assert sync(inbox, client).state == "synced"
    worker = PlaylistReconciler(inbox[0])
    worker.run_once(client)
    remote.playlist_error = 50
    assert worker.run_once(client, worker_refresh=True) is NOT_READY
    with closing(open_writer(inbox[0])) as db:
        assert not get_managed_copy(db, "daily-jams").unlinked

    remote.playlist_error = None
    del remote.playlists["playlist-1"]
    assert worker.run_once(client) is None
    with closing(open_writer(inbox[0])) as db:
        assert get_managed_copy(db, "daily-jams").unlinked
        assert len(get_edition(db, inbox[1]).snapshot.tracks) == 5

    remote.requests.clear()
    assert worker.run_once(client, worker_refresh=True) is None
    assert sync(inbox, client).state == "unlinked"
    assert not remote.requests
    assert not remote.playlists


def test_reconcile_ignores_pending_creates_and_other_targets(inbox):
    remote = Navidrome()
    worker = PlaylistReconciler(inbox[0])
    remote.drop_create_reply = True
    assert sync(inbox, remote.client()).state == "pending"
    remote.requests.clear()
    assert worker.run_once(remote.client(), worker_refresh=True) is None
    assert not remote.requests
    assert sync(inbox, remote.client()).state == "synced"
    remote.requests.clear()
    assert worker.run_once(remote.client((CONFIG[0], "different-owner", CONFIG[2]))) is None
    assert not remote.requests


def test_reconcile_rejects_malformed_inventory_without_touching_playlist(inbox):
    remote = Navidrome()
    assert sync(inbox, remote.client()).state == "synced"
    worker = PlaylistReconciler(inbox[0])
    remote.songs = [{"title": "No ID"}]
    remote.requests.clear()
    assert worker.run_once(remote.client()) is NOT_READY
    assert [method for method, _ in remote.requests] == ["getScanStatus", "search3"]
    assert_songs(remote, "playlist-1", ["one", "two", "one"])
