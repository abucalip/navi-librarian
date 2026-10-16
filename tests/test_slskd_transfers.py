"""Direct-import regressions for slskd transfer listing and directory identity."""

import unittest
from unittest.mock import patch

from slskd_transfers import download_transfer_files, queue_download_files


class FakeResponse:
    def __init__(self, payload=None, status_code=200, error=None):
        self.payload = payload
        self.status_code = status_code
        self.error = error
        self.raise_calls = 0
        self.json_calls = 0

    def raise_for_status(self):
        self.raise_calls += 1
        if self.error:
            raise self.error

    def json(self):
        self.json_calls += 1
        return self.payload


class FakeHTTP:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


class SlskdTransferListingTests(unittest.TestCase):
    def test_queue_posts_selected_files_and_returns_success_response(self):
        response = FakeResponse(payload={"queued": True})
        calls = []

        class QueueHTTP:
            def post(self, url, **kwargs):
                calls.append((url, kwargs))
                return response

        selected = [{"filename": "Album/01.flac"}]
        result = queue_download_files(
            "http://slskd", {"X-API-KEY": "test"}, "peer", selected,
            http_client=QueueHTTP(),
        )
        self.assertIs(result, response)
        self.assertEqual(calls, [(
            "http://slskd/api/v0/transfers/downloads/peer",
            {"headers": {"X-API-KEY": "test"}, "json": selected, "timeout": 12},
        )])
        self.assertEqual(response.raise_calls, 1)

    def test_queue_http_errors_propagate(self):
        response = FakeResponse(status_code=500, error=RuntimeError("queue failed"))

        class QueueHTTP:
            def post(self, *args, **kwargs):
                return response

        with self.assertRaisesRegex(RuntimeError, "queue failed"):
            queue_download_files("http://slskd", {}, "peer", [], http_client=QueueHTTP())

    def test_legacy_queue_adapter_preserves_queue_contract(self):
        from navidrome_server import _discovery_queue_candidate_unless_dismissed
        response = FakeResponse(payload={"queued": True})
        with patch("navidrome_server.httpx.post", return_value=response) as post, patch(
            "navidrome_server.acquisition_orchestration.queue_candidate_unless_dismissed",
            side_effect=lambda artist, album, **kwargs: kwargs["queue_source"](),
        ):
            result = _discovery_queue_candidate_unless_dismissed(
                "Artist", "Album", "http://slskd", {"X-API-KEY": "test"},
                "peer", [{"filename": "01.flac"}],
            )
        self.assertEqual(result, response)
        post.assert_called_once_with(
            "http://slskd/api/v0/transfers/downloads/peer",
            headers={"X-API-KEY": "test"}, json=[{"filename": "01.flac"}], timeout=12,
        )

    def test_requests_peer_transfers_with_encoded_username_and_timeout(self):
        response = FakeResponse(payload=[])
        http = FakeHTTP(response)
        self.assertEqual(download_transfer_files(
            "http://slskd", {"X-API-KEY": "test"}, "peer/name with space", http_client=http
        ), [])
        self.assertEqual(http.calls, [(
            "http://slskd/api/v0/transfers/downloads/peer%2Fname%20with%20space",
            {"headers": {"X-API-KEY": "test"}, "timeout": 8},
        )])

    def test_404_means_no_tracked_files_without_parsing_body(self):
        response = FakeResponse(status_code=404)
        self.assertEqual(download_transfer_files("http://slskd", {}, "peer", http_client=FakeHTTP(response)), [])
        self.assertEqual(response.json_calls, 0)
        self.assertEqual(response.raise_calls, 0)

    def test_normalizes_nested_directories_without_mutating_payload(self):
        root_file = {"filename": "01.flac", "state": "Completed"}
        child_file = {"filename": "02.flac"}
        grandchild_file = {"filename": "03.flac"}
        loose_file = {"filename": "loose.flac"}
        payload = [
            {
                "directory": "Artist/Album",
                "files": [root_file, "invalid-file-record"],
                "directories": [{
                    "files": [child_file],
                    "directories": [{
                        "directory": "Artist/Album/Bonus",
                        "files": [grandchild_file],
                    }],
                }],
            },
            "invalid-directory-record",
            {"files": [loose_file]},
        ]
        result = download_transfer_files(
            "http://slskd", {}, "peer", http_client=FakeHTTP(FakeResponse(payload=payload))
        )
        self.assertEqual(result, [
            {"filename": "01.flac", "state": "Completed", "_transfer_directory": "Artist/Album"},
            {"filename": "02.flac", "_transfer_directory": "Artist/Album"},
            {"filename": "03.flac", "_transfer_directory": "Artist/Album/Bonus"},
            {"filename": "loose.flac", "_transfer_directory": None},
        ])
        self.assertNotIn("_transfer_directory", root_file)
        self.assertNotIn("_transfer_directory", child_file)
        self.assertNotIn("_transfer_directory", grandchild_file)
        self.assertNotIn("_transfer_directory", loose_file)

    def test_supports_dictionary_items_and_rejects_unexpected_payloads(self):
        http = FakeHTTP(FakeResponse(payload={"items": [{
            "directory": "Album", "files": [{"filename": "01.mp3"}],
        }]}))
        self.assertEqual(download_transfer_files("http://slskd", {}, "peer", http_client=http), [
            {"filename": "01.mp3", "_transfer_directory": "Album"},
        ])
        self.assertEqual(download_transfer_files(
            "http://slskd", {}, "peer", http_client=FakeHTTP(FakeResponse(payload="invalid"))
        ), [])

    def test_http_errors_propagate(self):
        error = RuntimeError("HTTP failure")
        response = FakeResponse(status_code=500, error=error)
        with self.assertRaisesRegex(RuntimeError, "HTTP failure"):
            download_transfer_files("http://slskd", {}, "peer", http_client=FakeHTTP(response))

    def test_legacy_server_adapter_preserves_fetch_contract(self):
        from navidrome_server import _slskd_download_transfer_files

        response = FakeResponse(payload=[{"directory": "Album", "files": [{"filename": "01.flac"}]}])
        with patch("navidrome_server.httpx.get", return_value=response) as get:
            result = _slskd_download_transfer_files("http://slskd", {"X-API-KEY": "test"}, "peer")
        self.assertEqual(result, [{"filename": "01.flac", "_transfer_directory": "Album"}])
        get.assert_called_once_with(
            "http://slskd/api/v0/transfers/downloads/peer",
            headers={"X-API-KEY": "test"}, timeout=8,
        )


if __name__ == "__main__":
    unittest.main()
