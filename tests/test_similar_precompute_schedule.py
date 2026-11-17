"""The worker's similar-artist precompute (efficiency W2, app/services/similar_precompute.py).

Cursor progression, the not-ready retry, the synchronous owned build, and that web startup no longer starts a
precompute loop. No provider or Navidrome call is made.
"""

import inspect
import threading
import unittest
from unittest import mock

from app import worker_schedule
from app.services import similar_precompute as sp


def librarian(stored=None):
    writes = []
    lib = mock.Mock()
    lib._discovery_read_list.return_value = stored
    lib._discovery_write_list.side_effect = lambda name, payload: writes.append((name, payload))
    return lib, writes


def owned_data():
    from discovery.search.index import build_owned_data

    return build_owned_data(generation=1, built_at=0.0, songs=[],
                            artists=[{"id": n, "name": f"Artist {n}"} for n in ("a", "b", "c")], albums=[])


class RunOnceTests(unittest.TestCase):
    def run_once(self, stored, stop=None):
        lib, writes = librarian(stored)
        captured = {}

        def fake_run(artists, network, owned, **kwargs):
            captured.update(kwargs, artists=[a["id"] for a in artists])
            kwargs["on_progress"](2)
            return {"complete": 1}

        with mock.patch.object(sp, "build_owned", return_value=owned_data()), \
                mock.patch.object(sp, "precompute_network"), \
                mock.patch.object(sp, "run_precompute", side_effect=fake_run):
            result = sp.run_once(lib, stop=stop)
        return result, captured, writes

    def test_the_run_starts_where_the_last_pass_stopped_and_stores_progress(self):
        result, captured, writes = self.run_once({"payload": {"next": 2}, "generated_at": "x"})
        self.assertEqual(result, {"complete": 1})
        self.assertEqual(captured["start"], 2)
        self.assertEqual(captured["artists"], ["a", "b", "c"])
        self.assertEqual(writes, [(sp.CURSOR, {"next": 2})])

    def test_the_cursor_key_is_unchanged_from_the_web_loop(self):
        self.assertEqual(sp.CURSOR, "similar-precompute-cursor")

    def test_a_missing_or_malformed_cursor_starts_at_the_beginning(self):
        for stored in (None, "junk", {"payload": "junk"}, {"payload": {"next": "x"}}):
            _, captured, _ = self.run_once(stored)
            self.assertEqual(captured["start"], 0)

    def test_stop_is_passed_to_the_run(self):
        stop = threading.Event()
        _, captured, _ = self.run_once(None, stop=stop)
        self.assertIs(captured["stop"], stop)

    def test_an_unreadable_library_is_not_ready_and_runs_nothing(self):
        lib, _ = librarian()
        with mock.patch.object(sp, "build_owned", return_value=None), \
                mock.patch.object(sp, "run_precompute") as run:
            self.assertIs(sp.run_once(lib), worker_schedule.NOT_READY)
        run.assert_not_called()


class BuildOwnedTests(unittest.TestCase):
    def lib(self):
        lib = mock.Mock(DISCOVERY_DB="unused")
        lib._discovery_settings_read.return_value = {}
        return lib

    def test_the_build_is_synchronous_and_keeps_songs_and_identities(self):
        artists = [{"id": "ar1", "name": "Ash"}]
        songs = [{"id": "s1", "title": "One", "artistId": "ar1", "playCount": 7}]
        with mock.patch.object(sp, "navidrome_generation", return_value=3), \
                mock.patch.object(sp, "snapshot_lists", return_value=(artists, [])) as snap, \
                mock.patch.object(sp, "fetch_song_inventory", return_value=songs), \
                mock.patch.object(sp, "load_identities", return_value={"artist:ar1": {"mbid": "m-1"}}) as ids:
            data = sp.build_owned(self.lib())
        snap.assert_called_once()
        self.assertEqual(snap.call_args.args[1], 3)
        self.assertEqual(ids.call_args.args[1], 3)
        self.assertEqual(data.generation, 3)
        self.assertEqual(data.artists[0]["mbid"], "m-1")     # the cache key the web reads uses this MBID
        self.assertEqual(data.artists[0]["plays"], 7)        # the owner boost uses song plays

    def test_a_failed_library_read_returns_none(self):
        with mock.patch.object(sp, "navidrome_generation", return_value=1), \
                mock.patch.object(sp, "snapshot_lists", side_effect=RuntimeError("down")):
            self.assertIsNone(sp.build_owned(self.lib()))

    def test_the_worker_path_builds_no_shared_index_and_starts_no_identity_pass(self):
        source = inspect.getsource(sp)
        self.assertNotIn("owned_index_for", source)
        self.assertNotIn("owned_view", source)
        self.assertNotIn("IdentityJob", source)
        self.assertNotIn("from app.api", source)             # the worker imports no route module from here
        self.assertNotIn("import app.api", source)


class NetworkTests(unittest.TestCase):
    def test_precompute_network_keeps_the_page_cache_key_inputs(self):
        lib = mock.Mock()
        lib._discovery_settings_read.return_value = {"lastfm_api_key": " key "}
        with mock.patch.object(sp, "lastfm_generation", return_value=4), \
                mock.patch.object(sp, "discogs_generation", return_value=2), \
                mock.patch.object(sp, "discogs_token_and_source", return_value=("", "none")):
            kwargs = sp.network_kwargs(lib)
            network = sp.precompute_network(lib)
        self.assertEqual(kwargs["lastfm_api_key"], "key")
        self.assertEqual(network.lastfm_generation, 4)
        self.assertEqual(network.discogs_generation, 2)
        self.assertIsNotNone(network.lastfm)
        self.assertIsNone(network.discogs)
        self.assertIs(network.cache_write, lib._discovery_write_list)


class WebStartupTests(unittest.TestCase):
    def test_web_startup_starts_no_precompute_thread(self):
        import app.main as main
        from app.api import search
        from discovery import lens_service

        lib = mock.Mock()
        before = {t.name for t in threading.enumerate()}
        with mock.patch.object(main, "get_librarian", return_value=lib), \
                mock.patch.object(main, "_bump_discogs_generation_at_startup"), \
                mock.patch.object(lens_service, "start_daily_refresh"), \
                mock.patch.object(search, "owned_view") as warm:
            main._start_discovery_background()
        lib._start_discovery_scheduler.assert_called_once_with()
        warm.assert_called_once_with(lib)                     # one-shot index warm-up only
        names = {t.name for t in threading.enumerate()} - before
        self.assertNotIn("navidrome-similar-artists", names)
        self.assertFalse(hasattr(search, "start_similar_precompute"))


if __name__ == "__main__":
    unittest.main()
