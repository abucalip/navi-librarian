import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import radio
from app.api.dependencies import get_librarian
from integrations.radio import scrobble
from integrations.radio.listening import ListenTracker
from integrations.radio.store import RadioStore

CREDS = scrobble.Credentials(token="lb-token")
NO_CREDS = scrobble.Credentials(token="")
LISTENBRAINZ_ENV = ("LISTENBRAINZ_TOKEN",)


class Clock:
    def __init__(self, start=1000.0):
        self.now = start

    def __call__(self):
        return self.now


class OkPost:
    """Stands in for httpx.post: records each call and answers like ListenBrainz."""

    def __init__(self, payload=None, status_code=200):
        self.calls = []
        self.payload = payload if payload is not None else {"status": "ok"}
        self.status_code = status_code

    def __call__(self, url, json=None, headers=None, **kwargs):
        self.calls.append({"url": url, "json": json, "headers": dict(headers or {})})
        return mock.Mock(status_code=self.status_code, json=mock.Mock(return_value=self.payload))


class StoreCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = RadioStore(Path(self.dir.name) / "radio.sqlite3")
        self.play = self.store.record_play("s1", "Rock FM", "Pink Floyd - Time", "Pink Floyd", "Time", 40,
                                           now=2000.0)

    def tearDown(self):
        self.dir.cleanup()


class SubmitTests(StoreCase):
    def test_off_by_default_so_nothing_is_sent(self):
        post = OkPost()
        self.assertFalse(scrobble.enabled(self.store))
        self.assertEqual(scrobble.submit(self.store, self.play, creds=CREDS, post=post), "off")
        self.assertEqual(post.calls, [])

    def test_sends_one_listen_with_start_time_and_never_twice(self):
        scrobble.set_enabled(self.store, CREDS, True)
        self.store.set_album(self.play, "The Dark Side of the Moon", 1973)
        post = OkPost()
        self.assertEqual(scrobble.submit(self.store, self.play, creds=CREDS, post=post), "sent")
        self.assertEqual(scrobble.submit(self.store, self.play, creds=CREDS, post=post), "done")
        self.assertEqual(len(post.calls), 1)
        sent = post.calls[0]
        self.assertEqual(sent["url"], scrobble.LISTENBRAINZ_SUBMIT_URL)
        self.assertEqual(sent["headers"]["Authorization"], "Token lb-token")
        self.assertEqual(sent["json"], {
            "listen_type": "single",
            "payload": [{
                "listened_at": 1960,
                "track_metadata": {
                    "artist_name": "Pink Floyd",
                    "track_name": "Time",
                    "release_name": "The Dark Side of the Moon",
                },
            }],
        })

    def test_not_configured_or_unnamed_or_unknown_plays_send_nothing(self):
        scrobble.set_enabled(self.store, CREDS, True)
        post = OkPost()
        self.assertEqual(scrobble.submit(self.store, self.play, creds=NO_CREDS, post=post), "not_configured")
        self.assertEqual(scrobble.submit(self.store, 999, creds=CREDS, post=post), "missing")
        untitled = self.store.record_play("s1", "Rock FM", "Station jingle", None, "Station jingle", 40)
        self.assertEqual(scrobble.submit(self.store, untitled, creds=CREDS, post=post), "no_artist")
        self.assertEqual(post.calls, [])

    def test_a_failed_request_is_not_retried(self):
        scrobble.set_enabled(self.store, CREDS, True)

        def broken(url, json=None, **kwargs):
            raise httpx.ConnectError("refused")

        with self.assertRaises(scrobble.ScrobbleFailed):
            scrobble.submit(self.store, self.play, creds=CREDS, post=broken)
        post = OkPost()
        self.assertEqual(scrobble.submit(self.store, self.play, creds=CREDS, post=post), "done")
        self.assertEqual(post.calls, [])

    def test_listenbrainz_error_answer_or_http_error_is_a_failure(self):
        scrobble.set_enabled(self.store, CREDS, True)
        with self.assertRaises(scrobble.ScrobbleFailed):
            scrobble.submit(self.store, self.play, creds=CREDS, post=OkPost({"error": "Invalid token"}, status_code=401))
        other = self.store.record_play("s1", "Rock FM", "A - B", "A", "B", 40)
        with self.assertRaises(scrobble.ScrobbleFailed):
            scrobble.submit(self.store, other, creds=CREDS, post=OkPost({"error": "bad payload"}))

    def test_switch_on_needs_credentials_and_switch_off_always_works(self):
        with self.assertRaises(scrobble.ScrobbleError) as ctx:
            scrobble.set_enabled(self.store, NO_CREDS, True)
        self.assertIn("ListenBrainz", str(ctx.exception))
        self.assertIn("LISTENBRAINZ_TOKEN", str(ctx.exception))
        self.assertFalse(scrobble.enabled(self.store))
        scrobble.set_enabled(self.store, CREDS, True)
        scrobble.set_enabled(self.store, NO_CREDS, False)
        self.assertFalse(scrobble.enabled(self.store))


class LoveTests(StoreCase):
    def test_love_sends_recording_feedback_and_marks_the_play(self):
        post = OkPost({"status": "ok"})
        sent = scrobble.love(
            self.store,
            self.play,
            creds=CREDS,
            post=post,
            lookup_mbid=lambda artist, title: "mbid-time-123",
        )
        self.assertTrue(sent)
        self.assertEqual(len(post.calls), 1)
        self.assertEqual(post.calls[0]["url"], scrobble.LISTENBRAINZ_FEEDBACK_URL)
        self.assertEqual(post.calls[0]["headers"]["Authorization"], "Token lb-token")
        self.assertEqual(post.calls[0]["json"], {"recording_mbid": "mbid-time-123", "score": 1})
        self.assertEqual(self.store.get_play(self.play)["loved"], 1)

    def test_love_falls_back_to_local_store_when_mbid_cannot_be_resolved(self):
        post = OkPost({"status": "ok"})
        sent = scrobble.love(self.store, self.play, creds=CREDS, post=post, lookup_mbid=lambda artist, title: None)
        self.assertFalse(sent)
        self.assertEqual(post.calls, [])
        self.assertEqual(self.store.get_play(self.play)["loved"], 1)

    def test_love_falls_back_to_local_store_when_mbid_lookup_errors(self):
        post = OkPost({"status": "ok"})

        def broken_lookup(artist, title):
            raise OSError("rate limited")

        sent = scrobble.love(self.store, self.play, creds=CREDS, post=post, lookup_mbid=broken_lookup)
        self.assertFalse(sent)
        self.assertEqual(post.calls, [])
        self.assertEqual(self.store.get_play(self.play)["loved"], 1)

    def test_love_refuses_without_artist_credentials_or_play(self):
        untitled = self.store.record_play("s1", "Rock FM", "Station jingle", None, "Station jingle", 40)
        post = OkPost({})
        with self.assertRaises(scrobble.ScrobbleError):
            scrobble.love(self.store, untitled, creds=CREDS, post=post, lookup_mbid=lambda a, t: "mbid-1")
        with self.assertRaises(scrobble.ScrobbleError) as ctx:
            scrobble.love(self.store, self.play, creds=NO_CREDS, post=post, lookup_mbid=lambda a, t: "mbid-1")
        self.assertIn("ListenBrainz", str(ctx.exception))
        with self.assertRaises(LookupError):
            scrobble.love(self.store, 999, creds=CREDS, post=post, lookup_mbid=lambda a, t: "mbid-1")
        self.assertEqual(post.calls, [])
        self.assertEqual(self.store.get_play(self.play)["loved"], 0)


class MigrationTests(unittest.TestCase):
    def test_a_database_from_before_the_columns_gets_them_and_keeps_its_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "radio.sqlite3"
            old = sqlite3.connect(path)
            old.executescript(
                "CREATE TABLE radio_plays (id INTEGER PRIMARY KEY AUTOINCREMENT, station_id TEXT NOT NULL,"
                " station_name TEXT NOT NULL, raw_title TEXT NOT NULL, artist TEXT, title TEXT NOT NULL,"
                " album TEXT, year INTEGER, listened_seconds INTEGER NOT NULL, heard_at REAL NOT NULL,"
                " last_heard_at REAL NOT NULL, grabbed INTEGER NOT NULL DEFAULT 0);"
                "INSERT INTO radio_plays (station_id, station_name, raw_title, artist, title,"
                " listened_seconds, heard_at, last_heard_at) VALUES ('s1','Rock FM','A - B','A','B',40,1,1);")
            old.commit()
            old.close()
            store = RadioStore(path)
            RadioStore(path)  # opening again must not fail on the existing columns
            row = store.list_plays()[0]
            self.assertEqual((row["title"], row["scrobbled"], row["loved"]), ("B", 0, 0))


class ListenerHookTests(StoreCase):
    def test_a_logged_song_is_reported_and_a_repeat_after_reconnect_is_not_scrobbled_twice(self):
        scrobble.set_enabled(self.store, CREDS, True)
        clock = Clock()
        logged = []
        post = OkPost()

        def on_logged(play_id):
            logged.append(play_id)
            scrobble.submit(self.store, play_id, creds=CREDS, post=post)

        tracker = ListenTracker(self.store, "s1", "Rock FM", clock=clock, on_logged=on_logged)
        tracker.set_title("A - Song")
        clock.now += 35
        tracker.tick()
        tracker.close()
        second = ListenTracker(self.store, "s1", "Rock FM", clock=clock, on_logged=on_logged)
        second.set_title("A - Song")
        clock.now += 35
        second.tick()
        second.close()
        self.assertEqual(len(logged), 2)
        self.assertEqual(logged[0], logged[1])
        self.assertEqual(len(post.calls), 1)

    def test_a_failing_hook_never_stops_the_listen(self):
        clock = Clock()

        def broken(play_id):
            raise RuntimeError("boom")

        tracker = ListenTracker(self.store, "s2", "Jazz FM", clock=clock, on_logged=broken)
        tracker.set_title("A - Song")
        clock.now += 40
        tracker.tick()
        tracker.close()
        self.assertEqual(self.store.list_plays()[0]["listened_seconds"], 40)


class ScrobbleRouteTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        radio._STORES.clear()
        self.env = mock.patch.dict(os.environ, {name: "" for name in LISTENBRAINZ_ENV})
        self.env.start()
        self.librarian = mock.Mock(DATA_DIR=Path(self.dir.name))
        app = FastAPI()
        app.include_router(radio.router)
        app.dependency_overrides[get_librarian] = lambda: self.librarian
        self.client = TestClient(app)
        self.store = radio.get_store(self.librarian)
        self.play = self.store.record_play("s1", "Rock FM", "A - B", "A", "B", 40)

    def tearDown(self):
        self.env.stop()
        self.dir.cleanup()

    def configure(self):
        return mock.patch.dict(os.environ, {"LISTENBRAINZ_TOKEN": "lb-secret-token"})

    def test_switch_defaults_off_and_reports_whether_listenbrainz_is_set_up(self):
        self.assertEqual(self.client.get("/api/radio/scrobbling").json(), {"enabled": False, "configured": False})
        unconfigured = self.client.put("/api/radio/scrobbling", json={"enabled": True})
        self.assertEqual(unconfigured.status_code, 400)
        self.assertIn("ListenBrainz", unconfigured.json()["detail"])
        self.assertEqual(self.client.put("/api/radio/scrobbling", json={"enabled": "yes"}).status_code, 400)
        with self.configure():
            saved = self.client.put("/api/radio/scrobbling", json={"enabled": True})
            self.assertEqual(saved.json(), {"enabled": True, "configured": True})
            self.assertEqual(self.client.get("/api/radio/scrobbling").json(), {"enabled": True, "configured": True})
        self.assertNotIn("lb-secret-token", self.client.get("/api/radio/scrobbling").text)

    def test_love_route_refuses_unknown_plays_and_unconfigured_setups(self):
        self.assertEqual(self.client.post("/api/radio/plays/999/love").status_code, 404)
        unconfigured = self.client.post(f"/api/radio/plays/{self.play}/love")
        self.assertEqual(unconfigured.status_code, 400)
        self.assertIn("ListenBrainz", unconfigured.json()["detail"])
        fake = OkPost({"status": "ok"})
        with self.configure(), \
                mock.patch.object(scrobble, "lookup_recording_mbid", return_value="mbid-ab-1"), \
                mock.patch.object(scrobble.httpx, "post", fake):
            response = self.client.post(f"/api/radio/plays/{self.play}/love")
            self.assertEqual(response.json(), {"ok": True, "loved": True})
            self.assertEqual(fake.calls[0]["url"], scrobble.LISTENBRAINZ_FEEDBACK_URL)
            self.assertEqual(fake.calls[0]["json"], {"recording_mbid": "mbid-ab-1", "score": 1})
        with self.configure(), \
                mock.patch.object(scrobble, "lookup_recording_mbid", return_value="mbid-ab-1"), \
                mock.patch.object(scrobble.httpx, "post", side_effect=httpx.ConnectError("x")):
            self.assertEqual(self.client.post(f"/api/radio/plays/{self.play}/love").status_code, 502)

    def test_a_logged_song_is_scrobbled_on_a_background_thread(self):
        with mock.patch.object(radio.threading, "Thread") as thread:
            radio._scrobble_in_background(self.store, self.play)
        thread.assert_called_once_with(target=scrobble.submit_quietly, args=(self.store, self.play), daemon=True)
        thread.return_value.start.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
