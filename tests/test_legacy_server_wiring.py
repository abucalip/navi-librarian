"""Wiring checks for navidrome_server call sites that now pass the extracted function directly.

Efficiency C2 follow-up: one-line forwarding adapters were removed from the legacy server.
Each test stubs the downstream callee and checks the callback it receives, so no
provider, slskd or filesystem work runs.
"""
import unittest
from unittest.mock import Mock, patch

import navidrome_server
from acquisition import completion
from discovery import refresh as discovery_refresh
from integrations.slskd import search as slskd_search
from recommendation import listening_profile


class _Stop(BaseException):
    """Ends a call right after the checked callee, past any ``except Exception``."""


class LegacyServerWiringTests(unittest.TestCase):
    def test_inspect_completed_album_uses_completion_filename_key(self):
        with patch.object(navidrome_server, "inspect_completed_album", return_value={"path": None}) as call:
            navidrome_server._discovery_inspect_completed_album("/downloads", {"files": []})
        self.assertIs(call.call_args.kwargs["filename_key"], completion.filename_key)

    def test_refresh_all_thread_runs_discovery_refresh_all(self):
        with patch("threading.Thread") as thread:
            navidrome_server.discovery_refresh_list("all")
        kwargs = thread.call_args.kwargs
        self.assertIs(kwargs["target"], discovery_refresh.refresh_all)
        self.assertEqual(kwargs["args"], (
            navidrome_server._discovery_refresh_personal, navidrome_server._discovery_refresh_other,
        ))
        thread.return_value.start.assert_called_once_with()

    def test_refresh_one_list_thread_runs_refresh_other(self):
        with patch("threading.Thread") as thread:
            navidrome_server.discovery_refresh_list("classics")
        self.assertIs(thread.call_args.kwargs["target"], navidrome_server._discovery_refresh_other)
        self.assertEqual(thread.call_args.kwargs["args"], ("classics",))

    def test_scheduler_listening_profile_refresh(self):
        with patch.object(listening_profile, "refresh_and_persist_background_profile",
                          return_value="done") as call:
            self.assertEqual(navidrome_server._discovery_scheduler_refresh_one("listening_profile"), "done")
        call.assert_called_once_with(
            navidrome_server.recent_listening_profile, navidrome_server._discovery_write_list,
        )

    def test_deep_dive_similar_artists_use_discovery_lookups(self):
        from discovery.popularity import DiscoveryProviderLookups
        snapshot = {"artists": [{"name": "Anchor", "album_count": 3}], "albums": []}
        collect = Mock(side_effect=_Stop)
        fake_similar = Mock()
        fake_lookups = DiscoveryProviderLookups(
            top_albums=Mock(return_value=[]),
            similar_artists=fake_similar,
            artist_genres=Mock(return_value=[]),
        )
        with patch.object(navidrome_server, "_discovery_library_snapshot", return_value=snapshot), \
                patch.object(navidrome_server, "_discovery_read_list", return_value=None), \
                patch("discovery.popularity.build_discovery_lookups", return_value=fake_lookups), \
                patch("discovery.deep_dive_candidates.collect_missing_album_candidates"), \
                patch("discovery.deep_dive_candidates.merge_resolved_pool_candidates"), \
                patch("discovery.deep_dive_candidates.collect_similar_artist_candidates", collect), \
                self.assertRaises(_Stop):
            navidrome_server._build_artist_deep_dive_list()
        self.assertIs(collect.call_args.kwargs["similar_artists_lookup"], fake_similar)

    def test_new_releases_use_exact_artist_credit_matches(self):
        from discovery.recommendations import exact_artist_credit_matches

        select = Mock(side_effect=_Stop)
        with patch.object(navidrome_server, "_discovery_library_snapshot",
                          return_value={"artists": [], "albums": []}), \
                patch("discovery.new_releases.prepare_new_release_library_scope",
                      return_value=(set(), [{"name": "Artist"}])), \
                patch("discovery.new_releases.build_new_release_lookup", return_value=("key", "query")), \
                patch("discovery.new_releases.fetch_artist_release_groups", return_value=([], None)), \
                patch("discovery.new_releases.select_artist_release_candidates", select), \
                self.assertRaises(_Stop):
            navidrome_server._build_new_releases_list()
        self.assertIs(select.call_args.kwargs["exact_artist_credit_matches"], exact_artist_credit_matches)


class AcquisitionSearchWiringTests(unittest.TestCase):
    """The slskd search step passes integrations.slskd.search functions directly."""

    def test_search_uses_slskd_search_functions(self):
        metadata = {"track_count": 9}
        collect = Mock(return_value={
            "search_id": "s", "search_attempts": [], "reported_response_count": 0,
            "reported_file_count": 0, "payload_by_peer": {},
        })
        expected = Mock(wraps=slskd_search.expected_track_count)
        extract = Mock(side_effect=_Stop)
        with patch.object(navidrome_server, "_slskd_config",
                          return_value=("http://slskd.local", "key", {})), \
                patch.object(navidrome_server, "_discovery_update_acquisition_status") as status, \
                patch.object(navidrome_server, "_discovery_save_acquisition_job") as save, \
                patch("integrations.slskd.search_polling.collect_search_responses", collect), \
                patch.object(slskd_search, "expected_track_count", expected), \
                patch.object(navidrome_server, "_slskd_extract_candidates", extract), \
                self.assertRaises(_Stop):
            navidrome_server._discovery_acquire_album_impl(
                "Artist", "Album", __import__("json").dumps(metadata),
            )
        self.assertEqual(collect.call_args.args[0], slskd_search.search_queries("Artist", "Album"))
        self.assertIs(collect.call_args.kwargs["response_items"], slskd_search.response_items)
        expected.assert_called_once_with(metadata)
        self.assertEqual(extract.call_args.kwargs["expected_track_count"], 9)
        save.assert_not_called()
        status.assert_not_called()


if __name__ == "__main__":
    unittest.main()
