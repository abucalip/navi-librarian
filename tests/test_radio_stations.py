import tempfile
import unittest
from pathlib import Path

from integrations.musicbrainz.recording_album import lookup_recording_album
from integrations.radio import stations
from integrations.radio.store import RadioStore


class FakeNavidrome:
    def __init__(self, rows):
        self.rows = {row["id"]: dict(row) for row in rows}
        self.calls = []
        self.fail_update = False

    def __call__(self, method, **params):
        self.calls.append((method, params))
        if method == "getInternetRadioStations":
            return {"internetRadioStations": {"internetRadioStation": list(self.rows.values())}}
        if self.fail_update:
            raise RuntimeError("boom")
        row = self.rows[params["id"]]
        row["streamUrl"] = params["streamUrl"]
        return {}


class StationTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = RadioStore(Path(self.dir.name) / "radio.sqlite3")
        self.api = FakeNavidrome([{"id": "7", "name": "Rock FM", "streamUrl": "http://rock.example/live",
                                   "homepageUrl": "http://rock.example"}])

    def tearDown(self):
        self.dir.cleanup()

    def test_enable_points_navidrome_at_the_relay_and_disable_restores(self):
        stations.enable(self.api, self.store, "7", "https://librarian.example/")
        url = self.api.rows["7"]["streamUrl"]
        self.assertTrue(url.startswith("https://librarian.example/radio/stream/"))
        update = [c for c in self.api.calls if c[0] == "updateInternetRadioStation"][0][1]
        self.assertEqual((update["name"], update["homepageUrl"]), ("Rock FM", "http://rock.example"))
        listed = stations.list_stations(self.api, self.store)
        self.assertEqual(listed, [{"id": "7", "name": "Rock FM", "proxied": True,
                                   "stream_url": "http://rock.example/live"}])
        stations.disable(self.api, self.store, "7")
        self.assertEqual(self.api.rows["7"]["streamUrl"], "http://rock.example/live")
        self.assertFalse(stations.list_stations(self.api, self.store)[0]["proxied"])
        self.assertIsNone(self.store.station_by_token(url.rsplit("/", 1)[1]))

    def test_enable_twice_keeps_one_token(self):
        stations.enable(self.api, self.store, "7", "https://librarian.example")
        first = self.api.rows["7"]["streamUrl"]
        stations.enable(self.api, self.store, "7", "https://librarian.example")
        self.assertEqual(self.api.rows["7"]["streamUrl"], first)

    def test_failed_update_leaves_the_relay_closed(self):
        self.api.fail_update = True
        with self.assertRaises(RuntimeError):
            stations.enable(self.api, self.store, "7", "https://librarian.example")
        token_row = self.store.get_station("7")
        self.assertIsNone(self.store.station_by_token(token_row["token"]))
        self.assertEqual(self.api.rows["7"]["streamUrl"], "http://rock.example/live")

    def test_refuses_bad_addresses_and_unknown_stations(self):
        for bad in ("", "ftp://x", "https://u:p@x", "https://x/?a=1", "not a url"):
            with self.assertRaises(stations.StationError, msg=bad):
                stations.enable(self.api, self.store, "7", bad)
        with self.assertRaises(stations.StationError):
            stations.enable(self.api, self.store, "99", "https://librarian.example")
        self.api.rows["8"] = {"id": "8", "name": "Odd", "streamUrl": "file:///etc/passwd"}
        with self.assertRaises(stations.StationError):
            stations.enable(self.api, self.store, "8", "https://librarian.example")

    def test_disable_of_a_never_enabled_station_changes_nothing(self):
        stations.disable(self.api, self.store, "7")
        self.assertFalse([c for c in self.api.calls if c[0] == "updateInternetRadioStation"])


class RecordingAlbumTests(unittest.TestCase):
    def test_prefers_the_plain_studio_album_over_compilations_and_live(self):
        recordings = [{
            "title": "Time", "artist-credit": [{"name": "Pink Floyd", "joinphrase": ""}],
            "releases": [
                {"title": "Best Of", "date": "1990", "status": "Official",
                 "release-group": {"primary-type": "Album", "secondary-types": ["Compilation"]}},
                {"title": "The Dark Side of the Moon", "date": "1973-03-01", "status": "Official",
                 "release-group": {"primary-type": "Album"}},
                {"title": "Live", "date": "1988", "release-group": {"primary-type": "Album", "secondary-types": ["Live"]}},
            ],
        }, {"title": "Time (Remix)", "artist-credit": [{"name": "Pink Floyd"}],
            "releases": [{"title": "Remixes", "date": "1970"}]}]
        found = lookup_recording_album("Pink Floyd", "Time", fetch=lambda q, n: recordings)
        self.assertEqual(found, {"album": "The Dark Side of the Moon", "year": 1973})

    def test_no_exact_match_gives_none(self):
        other = [{"title": "Time", "artist-credit": [{"name": "Someone Else"}], "releases": [{"title": "X"}]}]
        self.assertIsNone(lookup_recording_album("Pink Floyd", "Time", fetch=lambda q, n: other))


if __name__ == "__main__":
    unittest.main()
