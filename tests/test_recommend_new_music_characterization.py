"""Characterization tests for the live new-music recommendation adapter."""

import json
import unittest
from unittest.mock import patch

import navidrome_server as server


class _Response:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class RecommendNewMusicCharacterizationTests(unittest.TestCase):
    def setUp(self):
        self.recordings = {
            "recording-1": {
                "title": "Blue Train",
                "artist-credit": [{
                    "name": "John Coltrane",
                    "joinphrase": "",
                    "artist": {"id": "artist-1", "name": "John Coltrane"},
                }],
                "releases": [{
                    "release-group": {
                        "id": "release-group-1",
                        "title": "Blue Train",
                        "primary-type": "Album",
                        "secondary-types": [],
                    },
                }],
            },
            "recording-2": {
                "title": "Moanin'",
                "artist-credit": [{
                    "name": "Art Blakey",
                    "joinphrase": "",
                    "artist": {"id": "artist-2", "name": "Art Blakey"},
                }],
                "releases": [{
                    "release-group": {
                        "id": "release-group-2",
                        "title": "Moanin'",
                        "primary-type": "Album",
                        "secondary-types": [],
                    },
                }],
            },
        }

    def _run_recommendations(self, library_albums, recommendations=None):
        if recommendations is None:
            recommendations = [{"recording_mbid": "recording-1", "score": 10}]

        def cache_get(key, ttl_seconds=None):
            if key.startswith("mb:recording:"):
                return self.recordings.get(key.removeprefix("mb:recording:"))
            if key.startswith("mb:release-group-search:"):
                return {"release-groups": []}
            if key.startswith("mb:artist-genres:"):
                return ["jazz"]
            return None

        def api_call(method, **params):
            self.assertEqual(method, "getAlbumList2")
            self.assertEqual(params["type"], "alphabeticalByName")
            self.assertEqual(params["size"], 500)
            self.assertEqual(params["offset"], 0)
            return {"albumList2": {"album": library_albums}}

        with (
            patch.object(server, "_listenbrainz_recent", return_value=[]),
            patch.object(server, "_listenbrainz_username", return_value="test-user"),
            patch.object(server, "_metadata_cache_get", side_effect=cache_get),
            patch.object(server, "_metadata_cache_set"),
            patch.object(server, "_discovery_settings_read", return_value={}),
            patch.object(server, "_lastfm_album_popularity", return_value=None),
            patch.object(server, "api_call", side_effect=api_call),
            patch(
                "httpx.get",
                return_value=_Response({"payload": {"mbids": recommendations}}),
            ),
        ):
            return json.loads(server.recommend_new_music(count=10))

    def test_clear_inventory_returns_candidate_and_stable_response_shape(self):
        result = self._run_recommendations([])

        self.assertEqual(result["source"], "ListenBrainz + MusicBrainz + Last.fm + Navidrome")
        self.assertEqual(result["candidate_albums_resolved"], 1)
        self.assertEqual(result["library_albums_indexed"], 0)
        self.assertEqual(result["recommendations_returned"], 1)
        self.assertEqual(result["recommendations"][0]["album"], "Blue Train")
        self.assertEqual(result["recommendations"][0]["artist"], "John Coltrane")
        self.assertEqual(result["recommendations"][0]["ownership_check"],
                         "No exact normalized album-title match found in the indexed Navidrome inventory; alternate editions may still exist.")

    def test_exact_owned_album_is_not_recommended(self):
        result = self._run_recommendations([{
            "id": "owned-1",
            "name": "Blue Train",
            "artist": "John Coltrane",
        }])

        self.assertEqual(result["library_albums_indexed"], 1)
        self.assertEqual(result["recommendations"], [])
        self.assertEqual(result["recommendations_returned"], 0)
        self.assertTrue(result["debug_all_candidates"][0]["exact_owned"])
        self.assertEqual(result["debug_all_candidates"][0]["selection_decision"], "already_owned")

    def test_duplicate_album_ids_are_deduplicated_before_ownership_indexing(self):
        result = self._run_recommendations([
            {"id": "same-id", "name": "Different Album", "artist": "Other Artist"},
            {"id": "same-id", "name": "Blue Train", "artist": "John Coltrane"},
        ])

        self.assertEqual(result["library_albums_indexed"], 1)
        self.assertEqual(result["recommendations_returned"], 1)
        self.assertFalse(result["debug_all_candidates"][0]["exact_owned"])

    def test_candidates_are_returned_in_score_order_not_provider_order(self):
        result = self._run_recommendations(
            [],
            recommendations=[
                {"recording_mbid": "recording-2", "score": 2},
                {"recording_mbid": "recording-1", "score": 8},
            ],
        )

        self.assertEqual(result["candidate_albums_resolved"], 2)
        self.assertEqual(
            [item["album"] for item in result["recommendations"]],
            ["Blue Train", "Moanin'"],
        )
        self.assertGreater(
            result["debug_all_candidates"][0]["discovery_score"],
            result["debug_all_candidates"][1]["discovery_score"],
        )

    def test_listenbrainz_history_failure_returns_error_before_provider_lookup(self):
        with (
            patch.object(
                server, "_listenbrainz_recent",
                side_effect=RuntimeError("ListenBrainz unavailable"),
            ),
            patch("httpx.get") as provider_request,
        ):
            result = json.loads(server.recommend_new_music(count=10))

        self.assertEqual(
            result["error"],
            "Could not retrieve recent listening history: ListenBrainz unavailable",
        )
        provider_request.assert_not_called()

    def test_empty_listenbrainz_recommendations_return_existing_message(self):
        with (
            patch.object(server, "_listenbrainz_recent", return_value=[]),
            patch.object(server, "_listenbrainz_username", return_value="test-user"),
            patch("httpx.get", return_value=_Response({"payload": {"mbids": []}})),
        ):
            result = json.loads(server.recommend_new_music(count=10))

        self.assertEqual(result["recommendations"], [])
        self.assertEqual(
            result["message"],
            "ListenBrainz returned no recording recommendations.",
        )

    def test_inventory_failure_returns_error_without_recommendations(self):
        with (
            patch.object(server, "_listenbrainz_recent", return_value=[]),
            patch.object(server, "_listenbrainz_username", return_value="test-user"),
            patch(
                "httpx.get",
                return_value=_Response({
                    "payload": {"mbids": [{"recording_mbid": "recording-1", "score": 10}]}
                }),
            ),
            patch.object(server, "_metadata_cache_get", side_effect=lambda key, ttl_seconds=None: (
                self.recordings.get(key.removeprefix("mb:recording:")) if key.startswith("mb:recording:")
                else {"release-groups": []} if key.startswith("mb:release-group-search:")
                else ["jazz"] if key.startswith("mb:artist-genres:")
                else None
            )),
            patch.object(server, "_metadata_cache_set"),
            patch.object(server, "_discovery_settings_read", return_value={}),
            patch.object(server, "_lastfm_album_popularity", return_value=None),
            patch.object(server, "api_call", side_effect=RuntimeError("Navidrome unavailable")),
        ):
            result = json.loads(server.recommend_new_music(count=10))

        self.assertEqual(result["error"], "Could not retrieve the Navidrome album inventory.")
        self.assertEqual(result["details"], "Navidrome unavailable")
        self.assertEqual(result["recommendations"], [])


if __name__ == "__main__":
    unittest.main()
