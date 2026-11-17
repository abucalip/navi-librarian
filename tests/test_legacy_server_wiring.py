"""Wiring checks for navidrome_server call sites that now pass the extracted function directly.

Efficiency C2 follow-up: one-line forwarding adapters were removed from the legacy server.
Each test stubs the downstream callee and checks the callback it receives, so no
provider, slskd or filesystem work runs.
"""
import unittest
from unittest.mock import Mock, patch

import navidrome_server
from acquisition import completion
from integrations.slskd import search as slskd_search


class _Stop(BaseException):
    """Ends a call right after the checked callee, past any ``except Exception``."""


class LegacyServerWiringTests(unittest.TestCase):
    def test_inspect_completed_album_uses_completion_filename_key(self):
        with patch.object(navidrome_server, "inspect_completed_album", return_value={"path": None}) as call:
            navidrome_server._discovery_inspect_completed_album("/downloads", {"files": []})
        self.assertIs(call.call_args.kwargs["filename_key"], completion.filename_key)


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
