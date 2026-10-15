"""Regression tests for the extracted acquisition API router."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.params import Depends as DependsParam
from fastapi.responses import StreamingResponse

from app.api import acquisitions
from app.api.dependencies import get_librarian


class AcquisitionRoutesTests(unittest.TestCase):
    def setUp(self):
        self.service = SimpleNamespace()

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

    def test_routes_declare_lazy_service_dependency(self):
        for endpoint in (
            acquisitions.acquisition_status,
            acquisitions.skip_acquisition_source,
            acquisitions.dismiss_acquisition,
            acquisitions.acquisition_status_stream,
            acquisitions.acquire_album,
            acquisitions.queue_reviewed_candidate,
        ):
            dependency = endpoint.__defaults__[-1]
            self.assertIsInstance(dependency, DependsParam)
            self.assertIs(dependency.dependency, get_librarian)

    def test_default_service_import_is_lazy_and_resolves_legacy_adapter(self):
        fake = SimpleNamespace(marker="legacy-adapter")
        with patch.dict("sys.modules", {"navidrome_server": fake}):
            self.assertIs(get_librarian(), fake)

    def test_acquire_maps_payload_and_defaults_auto_queue(self):
        with patch.object(self.service, "discovery_acquire_album", create=True, return_value='{"ok": true}') as call:
            self.assertEqual(acquisitions.acquire_album({
                "artist": " Artist ", "album": " Album ", "metadata": {"year": 1999}
            }, self.service), {"ok": True})
        call.assert_called_once_with(
            artist="Artist", album="Album",
            metadata_json=json.dumps({"year": 1999}, ensure_ascii=False),
            auto_queue=True,
        )

    def test_acquire_preserves_explicit_false_auto_queue(self):
        with patch.object(self.service, "discovery_acquire_album", create=True, return_value='{"ok": true}') as call:
            acquisitions.acquire_album({
                "artist": "Artist", "album": "Album", "auto_queue": False
            }, self.service)
        self.assertIs(call.call_args.kwargs["auto_queue"], False)

    def test_acquire_rejects_non_boolean_auto_queue_before_service_call(self):
        for invalid in ("false", "true", 0, 1, None, [], {}):
            with self.subTest(auto_queue=invalid):
                with patch.object(self.service, "discovery_acquire_album", create=True) as call:
                    with self.assertRaises(HTTPException) as raised:
                        acquisitions.acquire_album({
                            "artist": "Artist", "album": "Album", "auto_queue": invalid
                        }, self.service)
                self.assertEqual(raised.exception.status_code, 400)
                self.assertEqual(raised.exception.detail, "auto_queue must be a boolean")
                call.assert_not_called()

    def test_acquire_requires_artist_and_album(self):
        with self.assertRaises(HTTPException) as raised:
            acquisitions.acquire_album({"artist": "Artist"}, self.service)
        self.assertEqual(raised.exception.status_code, 400)

    def test_queue_maps_reviewed_candidate(self):
        files = [{"filename": "01 - track.flac"}]
        with patch.object(self.service, "discovery_queue_slskd_candidate", create=True, return_value='{"ok": true}') as call:
            self.assertEqual(acquisitions.queue_reviewed_candidate({
                "username": "peer", "artist": "Artist", "album": "Album",
                "folder": "release", "files": files, "quality_summary": ["flac_cd"],
            }, self.service), {"ok": True})
        self.assertEqual(call.call_args.kwargs["username"], "peer")
        self.assertEqual(json.loads(call.call_args.kwargs["files_json"]), files)
        self.assertEqual(json.loads(call.call_args.kwargs["quality_summary_json"]), ["flac_cd"])

    def test_queue_rejects_empty_file_list(self):
        with self.assertRaises(HTTPException) as raised:
            acquisitions.queue_reviewed_candidate({"username": "peer", "files": []}, self.service)
        self.assertEqual(raised.exception.status_code, 400)

    def test_skip_maps_domain_conflict(self):
        with patch.object(self.service, "discovery_skip_acquisition_source", create=True, return_value='{"ok": false, "error": "No alternate source"}'):
            with self.assertRaises(HTTPException) as raised:
                acquisitions.skip_acquisition_source({"artist": "Artist", "album": "Album"}, self.service)
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, "No alternate source")

    def test_dismiss_forwards_trimmed_identity_and_returns_success(self):
        with patch.object(
            self.service,
            "discovery_dismiss_acquisition",
            create=True,
            return_value='{"ok": true, "status": "dismissed"}',
        ) as call:
            result = acquisitions.dismiss_acquisition({
                "artist": " Artist ", "album": " Album "
            }, self.service)

        self.assertEqual(result, {"ok": True, "status": "dismissed"})
        call.assert_called_once_with(artist="Artist", album="Album")

    def test_dismiss_requires_artist_and_album_before_service_call(self):
        for payload in ({"artist": "Artist"}, {"album": "Album"}, {}):
            with self.subTest(payload=payload):
                with patch.object(
                    self.service, "discovery_dismiss_acquisition", create=True
                ) as call:
                    with self.assertRaises(HTTPException) as raised:
                        acquisitions.dismiss_acquisition(payload, self.service)
                self.assertEqual(raised.exception.status_code, 400)
                call.assert_not_called()

    def test_dismiss_maps_missing_entry_and_conflict(self):
        with patch.object(self.service, "discovery_dismiss_acquisition", create=True, return_value='{"ok": false, "error": "Acquisition not found."}'):
            with self.assertRaises(HTTPException) as raised:
                acquisitions.dismiss_acquisition({"artist": "Artist", "album": "Album"}, self.service)
        self.assertEqual(raised.exception.status_code, 404)
        with patch.object(self.service, "discovery_dismiss_acquisition", create=True, return_value='{"ok": false, "error": "Unsafe folder"}'):
            with self.assertRaises(HTTPException) as raised:
                acquisitions.dismiss_acquisition({"artist": "Artist", "album": "Album"}, self.service)
        self.assertEqual(raised.exception.status_code, 409)

    def test_status_and_stream_keep_response_contracts(self):
        with patch.object(self.service, "discovery_get_acquisition_status", create=True, return_value='{"items": []}'):
            self.assertEqual(acquisitions.acquisition_status(self.service), {"items": []})
            response = acquisitions.acquisition_status_stream(self.service)
        self.assertIsInstance(response, StreamingResponse)
        self.assertEqual(response.media_type, "text/event-stream")
        self.assertEqual(response.headers["cache-control"], "no-cache")

    def test_upstream_errors_are_sanitized(self):
        with patch.object(self.service, "discovery_acquire_album", create=True, side_effect=RuntimeError("private upstream detail")):
            with self.assertRaises(HTTPException) as raised:
                acquisitions.acquire_album({"artist": "Artist", "album": "Album"}, self.service)
        self.assertEqual(raised.exception.status_code, 502)
        self.assertEqual(raised.exception.detail, "Could not search slskd for this album.")


if __name__ == "__main__":
    unittest.main()
