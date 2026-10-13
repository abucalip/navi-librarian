"""Regression tests for the extracted acquisition API router."""
import json
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from app.api import acquisitions


class AcquisitionRoutesTests(unittest.TestCase):
    def test_router_preserves_acquisition_endpoint_paths_and_methods(self):
        actual = {
            (route.path, method)
            for route in acquisitions.router.routes
            for method in getattr(route, "methods", set())
        }
        self.assertEqual(actual, {
            ("/api/acquisitions", "GET"),
            ("/api/acquisitions/skip", "POST"),
            ("/api/acquisitions/dismiss", "POST"),
            ("/api/acquisitions/stream", "GET"),
            ("/api/acquire", "POST"),
            ("/api/acquire/queue", "POST"),
        })

    def test_acquire_maps_payload_and_defaults_auto_queue(self):
        with patch.object(acquisitions.librarian, "discovery_acquire_album", return_value='{"ok": true}') as call:
            self.assertEqual(acquisitions.acquire_album({
                "artist": " Artist ", "album": " Album ", "metadata": {"year": 1999}
            }), {"ok": True})
        call.assert_called_once_with(
            artist="Artist", album="Album",
            metadata_json=json.dumps({"year": 1999}, ensure_ascii=False),
            auto_queue=True,
        )

    def test_acquire_requires_artist_and_album(self):
        with self.assertRaises(HTTPException) as raised:
            acquisitions.acquire_album({"artist": "Artist"})
        self.assertEqual(raised.exception.status_code, 400)

    def test_queue_maps_reviewed_candidate(self):
        files = [{"filename": "01 - track.flac"}]
        with patch.object(acquisitions.librarian, "discovery_queue_slskd_candidate", return_value='{"ok": true}') as call:
            self.assertEqual(acquisitions.queue_reviewed_candidate({
                "username": "peer", "artist": "Artist", "album": "Album",
                "folder": "release", "files": files, "quality_summary": ["flac_cd"],
            }), {"ok": True})
        self.assertEqual(call.call_args.kwargs["username"], "peer")
        self.assertEqual(json.loads(call.call_args.kwargs["files_json"]), files)
        self.assertEqual(json.loads(call.call_args.kwargs["quality_summary_json"]), ["flac_cd"])

    def test_queue_rejects_empty_file_list(self):
        with self.assertRaises(HTTPException) as raised:
            acquisitions.queue_reviewed_candidate({"username": "peer", "files": []})
        self.assertEqual(raised.exception.status_code, 400)

    def test_skip_maps_domain_conflict(self):
        payload = '{"ok": false, "error": "No alternate source"}'
        with patch.object(acquisitions.librarian, "discovery_skip_acquisition_source", return_value=payload):
            with self.assertRaises(HTTPException) as raised:
                acquisitions.skip_acquisition_source({"artist": "Artist", "album": "Album"})
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, "No alternate source")

    def test_dismiss_maps_missing_entry_and_conflict(self):
        with patch.object(acquisitions.librarian, "discovery_dismiss_acquisition", return_value='{"ok": false, "error": "Acquisition not found."}'):
            with self.assertRaises(HTTPException) as raised:
                acquisitions.dismiss_acquisition({"artist": "Artist", "album": "Album"})
        self.assertEqual(raised.exception.status_code, 404)
        with patch.object(acquisitions.librarian, "discovery_dismiss_acquisition", return_value='{"ok": false, "error": "Unsafe folder"}'):
            with self.assertRaises(HTTPException) as raised:
                acquisitions.dismiss_acquisition({"artist": "Artist", "album": "Album"})
        self.assertEqual(raised.exception.status_code, 409)

    def test_status_and_stream_keep_response_contracts(self):
        with patch.object(acquisitions.librarian, "discovery_get_acquisition_status", return_value='{"items": []}'):
            self.assertEqual(acquisitions.acquisition_status(), {"items": []})
            response = acquisitions.acquisition_status_stream()
        self.assertIsInstance(response, StreamingResponse)
        self.assertEqual(response.media_type, "text/event-stream")
        self.assertEqual(response.headers["cache-control"], "no-cache")

    def test_upstream_errors_are_sanitized(self):
        with patch.object(acquisitions.librarian, "discovery_acquire_album", side_effect=RuntimeError("private upstream detail")):
            with self.assertRaises(HTTPException) as raised:
                acquisitions.acquire_album({"artist": "Artist", "album": "Album"})
        self.assertEqual(raised.exception.status_code, 502)
        self.assertEqual(raised.exception.detail, "Could not search slskd for this album.")


if __name__ == "__main__":
    unittest.main()
