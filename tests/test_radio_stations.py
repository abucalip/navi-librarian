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
        self.assertEqual(listed[0]["id"], "7")
        self.assertTrue(listed[0]["proxied"])
        self.assertEqual(listed[0]["stream_url"], "http://rock.example/live")
        self.assertEqual(listed[0]["playable_url"], url)
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

    def test_saved_app_address_beats_the_browser_address_and_moves_relayed_stations(self):
        stations.enable(self.api, self.store, "7", "http://192.168.1.5:8000")
        token = self.store.get_station("7")["token"]
        result = stations.set_app_url(self.api, self.store, "http://box.tailnet.ts.net:8000/")
        self.assertEqual(result, {"app_url": "http://box.tailnet.ts.net:8000", "moved": 1})
        self.assertEqual(self.api.rows["7"]["streamUrl"], f"http://box.tailnet.ts.net:8000/radio/stream/{token}")
        stations.disable(self.api, self.store, "7")
        stations.enable(self.api, self.store, "7", "http://192.168.1.5:8000")
        self.assertTrue(self.api.rows["7"]["streamUrl"].startswith("http://box.tailnet.ts.net:8000/radio/stream/"))

    def test_blank_app_address_falls_back_and_bad_ones_are_refused(self):
        stations.set_app_url(self.api, self.store, "http://box:8000")
        stations.set_app_url(self.api, self.store, "")
        stations.enable(self.api, self.store, "7", "http://192.168.1.5:8000")
        self.assertTrue(self.api.rows["7"]["streamUrl"].startswith("http://192.168.1.5:8000/"))
        with self.assertRaises(stations.StationError):
            stations.set_app_url(self.api, self.store, "ftp://x")

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


class StationListFieldTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = RadioStore(Path(self.dir.name) / "radio.sqlite3")
        self.api = FakeNavidrome([
            {"id": "1", "name": "Zeta Radio", "streamUrl": "http://zeta.example/live", "homepageUrl": ""},
            {"id": "2", "name": "Alpha FM", "streamUrl": "http://alpha.example/live",
             "homepageUrl": "http://alpha.example"},
            {"id": "3", "name": "Beta Jazz", "streamUrl": "http://beta.example/live", "homepageUrl": ""},
        ])

    def tearDown(self):
        self.dir.cleanup()

    def test_fields_for_a_station_that_is_not_relayed(self):
        row = stations.list_stations(self.api, self.store)[-1]
        self.assertEqual(row, {
            "id": "1", "name": "Zeta Radio", "proxied": False,
            "stream_url": "http://zeta.example/live", "playable_url": "http://zeta.example/live",
            "homepage_url": None, "logo_url": "/api/radio/stations/1/logo",
            "favourite": False, "tags": [], "last_played_at": None,
        })

    def test_relayed_station_is_playable_through_the_relay_and_keeps_its_original_address(self):
        stations.enable(self.api, self.store, "2", "https://librarian.example")
        row = next(s for s in stations.list_stations(self.api, self.store) if s["id"] == "2")
        self.assertTrue(row["proxied"])
        self.assertEqual(row["stream_url"], "http://alpha.example/live")
        self.assertTrue(row["playable_url"].startswith("https://librarian.example/radio/stream/"))
        self.assertEqual(row["homepage_url"], "http://alpha.example")

    def test_favourites_first_then_last_played_then_name(self):
        self.store.set_favourite("1", True)
        self.store.record_play("3", "Beta Jazz", "B - Song", "B", "Song", 40, now=1000.0)
        self.store.record_play("2", "Alpha FM", "A - Song", "A", "Song", 40, now=2000.0)
        order = [s["id"] for s in stations.list_stations(self.api, self.store)]
        self.assertEqual(order, ["1", "2", "3"])
        self.assertEqual(
            [s["last_played_at"] for s in stations.list_stations(self.api, self.store)],
            [None, 2000.0, 1000.0])  # last time a play was logged (last_heard_at)

    def test_unplayed_stations_sort_by_name(self):
        self.assertEqual([s["id"] for s in stations.list_stations(self.api, self.store)], ["2", "3", "1"])

    def test_set_favourite_and_tags_persist_and_show_in_the_list(self):
        self.assertEqual(stations.set_favourite(self.api, self.store, "3", True),
                         {"id": "3", "favourite": True})
        self.assertEqual(stations.set_tags(self.api, self.store, "3", [" jazz ", "Jazz", "late  night"]),
                         {"id": "3", "tags": ["jazz", "late night"]})
        row = next(s for s in stations.list_stations(self.api, self.store) if s["id"] == "3")
        self.assertTrue(row["favourite"])
        self.assertEqual(row["tags"], ["jazz", "late night"])

    def test_favourite_must_be_a_boolean_and_station_must_exist(self):
        for bad in ("yes", 1, None):
            with self.subTest(value=bad), self.assertRaises(stations.StationError):
                stations.set_favourite(self.api, self.store, "3", bad)
        with self.assertRaises(stations.StationError):
            stations.set_favourite(self.api, self.store, "99", True)

    def test_tags_are_cleaned_and_limited(self):
        self.assertEqual(stations.clean_tags(None), [])
        self.assertEqual(stations.clean_tags(["  ", ""]), [])
        with self.assertRaises(stations.StationError):
            stations.clean_tags("jazz")
        with self.assertRaises(stations.StationError):
            stations.clean_tags([1])
        with self.assertRaises(stations.StationError):
            stations.clean_tags(["x" * (stations.MAX_TAG_LENGTH + 1)])
        with self.assertRaises(stations.StationError):
            stations.clean_tags([f"t{i}" for i in range(stations.MAX_TAGS + 1)])

    def test_logo_subject_gives_the_original_address_when_relayed(self):
        stations.enable(self.api, self.store, "2", "https://librarian.example")
        subject = stations.logo_subject(self.api, self.store, "2")
        self.assertEqual(subject["stream_url"], "http://alpha.example/live")
        self.assertEqual(subject["homepage_url"], "http://alpha.example")
        self.assertIsNone(stations.logo_subject(self.api, self.store, "1")["homepage_url"])

