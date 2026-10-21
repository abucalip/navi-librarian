import json
import os
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from discovery_candidate_gathering import RecommendationProviders
from recommendation.replay import (
    LastFmReplay,
    ProviderTape,
    main as replay_main,
    freeze_gathered_inputs,
    load_capture,
    thaw_gathered_inputs,
    write_capture,
    write_capture_safely,
)


def _gathered():
    return {
        "listens": [{"track_metadata": {"artist_name": "Fixture Artist"}}],
        "recent_artists": Counter({"fixtureartist": 2}),
        "recent_artist_mbid_counts": Counter({"artist-mbid": 2}),
        "recent_artist_play_counts": Counter({"fixtureartist": 1}),
        "albums": {
            ("fixtureartist", "fixturealbum"): {
                "artist": "Fixture Artist",
                "primary_artist": "Fixture Artist",
                "artist_mbid": "artist-mbid",
                "album": "Fixture Album",
                "score": 0.5,
                "tracks": ["Fixture Track"],
            }
        },
        "failures": [],
        "library_albums": [{"name": "Owned Album", "artist": "Owned Artist"}],
        "library_by_title": {"ownedalbum": [{"name": "Owned Album", "artist": "Owned Artist"}]},
        "genre_cache": {"artist-mbid": ["jazz"]},
        "regional_candidates_added": 0,
        "regional_results_seen": 0,
        "cf_recording_mbids": ["recording-mbid"],
        "cf_recordings_returned": 1,
        "cf_recordings_resolved": 1,
        "supplementary_cache_hits": 0,
        "supplementary_cache_misses": 20,
        "recent_family_counts": Counter({"jazz": 2}),
        "recent_family_play_counts": Counter({"jazz": 1}),
        "core_families": {"jazz", "rock"},
        "exploration_families": {"african"},
        "profile_families": {"jazz", "rock", "african"},
    }


class RecommendationReplayCaptureTests(unittest.TestCase):
    def test_freeze_thaw_preserves_ordered_candidates_and_counter_set_types(self):
        original = _gathered()
        frozen = freeze_gathered_inputs(original)
        restored = thaw_gathered_inputs(frozen)
        self.assertEqual(list(restored["albums"].keys()), list(original["albums"].keys()))
        self.assertEqual(list(restored["albums"].values()), list(original["albums"].values()))
        self.assertIsInstance(restored["recent_artists"], Counter)
        self.assertIsInstance(restored["recent_family_counts"], Counter)
        self.assertEqual(restored["recent_artist_play_counts"], original["recent_artist_play_counts"])
        self.assertEqual(restored["recent_family_play_counts"], original["recent_family_play_counts"])
        self.assertEqual(restored["core_families"], original["core_families"])
        self.assertEqual(restored["library_by_title"], original["library_by_title"])

    def test_freeze_and_thaw_strip_mutable_ranking_fields_from_candidates(self):
        gathered = _gathered()
        candidate = next(iter(gathered["albums"].values()))
        candidate.update({
            "discovery_score": 0.91,
            "discovery_category": "adjacent",
            "diversity_style": "jazz",
            "recent_profile_family": "jazz",
            "recent_profile_families": ["jazz"],
            "recent_profile_bonus": 1.25,
            "lastfm_listeners": 1234,
            "lastfm_playcount": 5678,
            "lastfm_tags": ["jazz"],
            "lastfm_popularity_bonus": 1.1,
            "listening_families": ["jazz"],
            "provider_specific_field": "preserve me",
        })

        frozen = freeze_gathered_inputs(gathered)
        frozen_candidate = frozen["albums"][0]["value"]
        self.assertEqual(frozen_candidate["score"], 0.5)
        self.assertEqual(frozen_candidate["provider_specific_field"], "preserve me")
        for key in (
            "discovery_score", "discovery_category", "diversity_style",
            "recent_profile_family", "recent_profile_families",
            "recent_profile_bonus", "lastfm_listeners", "lastfm_playcount",
            "lastfm_tags", "lastfm_popularity_bonus", "listening_families",
        ):
            self.assertNotIn(key, frozen_candidate)

        thawed_candidate = next(iter(thaw_gathered_inputs(frozen)["albums"].values()))
        self.assertEqual(thawed_candidate["score"], 0.5)
        self.assertEqual(thawed_candidate["provider_specific_field"], "preserve me")
        for key in (
            "discovery_score", "discovery_category", "diversity_style",
            "recent_profile_family", "recent_profile_families",
            "recent_profile_bonus", "lastfm_listeners", "lastfm_playcount",
            "lastfm_tags", "lastfm_popularity_bonus", "listening_families",
        ):
            self.assertNotIn(key, thawed_candidate)

    def test_capture_is_private_checksummed_and_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            path = root / "capture.json"
            expected = json.dumps({
                "recommendations": [{"artist": "Fixture Artist", "album": "Fixture Album"}],
                "lastfm_api_configured": False,
            })
            write_capture(
                path,
                gathered=_gathered(),
                lastfm_calls=[{"artist": "Fixture Artist", "album": "Fixture Album", "result": [None, None]}],
                provider_events=[],
                output=expected,
                count=1,
                git_sha="fixture-sha",
                ranking_context={"ranking_now": 1234.5, "history": [], "diversity_setting": 25},
            )
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            envelope = load_capture(path)
            self.assertEqual(envelope["git_sha"], "fixture-sha")
            self.assertEqual(envelope["payload"]["count"], 1)
            with self.assertRaises(FileExistsError):
                write_capture(
                    path, gathered=_gathered(), lastfm_calls=[], provider_events=[],
                    output=expected, count=1, git_sha="other-sha",
                    ranking_context={"ranking_now": 1234.5, "history": [], "diversity_setting": 25},
                )

    def test_safe_capture_is_one_shot_and_clears_capture_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            path = root / "one-shot.json"
            os.environ["LIBRARIAN_RECOMMENDATION_CAPTURE_PATH"] = str(path)
            try:
                write_capture_safely(
                    str(path),
                    _gathered(),
                    [],
                    ProviderTape("record"),
                    json.dumps({"recommendations": [], "lastfm_api_configured": False}),
                    1,
                    ranking_context={"ranking_now": 1234.5, "history": [], "diversity_setting": 0},
                )
                self.assertTrue(path.is_file())
                self.assertNotIn("LIBRARIAN_RECOMMENDATION_CAPTURE_PATH", os.environ)
            finally:
                os.environ.pop("LIBRARIAN_RECOMMENDATION_CAPTURE_PATH", None)

    def test_second_run_sharing_capture_path_does_not_warn_or_overwrite(self):
        # Two recommendation runs can both read LIBRARIAN_RECOMMENDATION_CAPTURE_PATH
        # before either finishes (e.g. /api/recommendations during a refresh). The
        # first run owns the one-shot capture; the second must neither overwrite it
        # nor log a "capture failed" warning for the file it correctly left alone.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            path = root / "shared-path.json"
            ranking_context = {"ranking_now": 1234.5, "history": [], "diversity_setting": 0}
            first_output = json.dumps({"recommendations": [{"artist": "First"}], "lastfm_api_configured": False})
            second_output = json.dumps({"recommendations": [{"artist": "Second"}], "lastfm_api_configured": False})
            write_capture_safely(
                str(path), _gathered(), [], ProviderTape("record"), first_output, 1,
                ranking_context=ranking_context,
            )
            with self.assertNoLogs("navidrome_server", level="WARNING"):
                write_capture_safely(
                    str(path), _gathered(), [], ProviderTape("record"), second_output, 1,
                    ranking_context=ranking_context,
                )
            envelope = load_capture(path)
            self.assertEqual(envelope["payload"]["expected_output"]["recommendations"], [{"artist": "First"}])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_capture_checksum_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            path = root / "capture.json"
            write_capture(
                path, gathered=_gathered(), lastfm_calls=[], provider_events=[],
                output=json.dumps({"recommendations": []}), count=1, git_sha="fixture",
                ranking_context={"ranking_now": 1234.5, "history": [], "diversity_setting": 0},
            )
            envelope = json.loads(path.read_text(encoding="utf-8"))
            envelope["payload"]["count"] = 99
            path.write_text(json.dumps(envelope), encoding="utf-8")
            path.chmod(0o600)
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                load_capture(path)

    def test_schema_v1_capture_is_rejected_as_missing_ranking_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            path = root / "capture.json"
            write_capture(
                path, gathered=_gathered(), lastfm_calls=[], provider_events=[],
                output=json.dumps({"recommendations": []}), count=1, git_sha="fixture",
                ranking_context={"ranking_now": 1234.5, "history": [], "diversity_setting": 0},
            )
            envelope = json.loads(path.read_text(encoding="utf-8"))
            envelope["schema_version"] = 1
            path.write_text(json.dumps(envelope), encoding="utf-8")
            path.chmod(0o600)
            with self.assertRaisesRegex(ValueError, "lacks frozen ranking context"):
                load_capture(path)

    def test_replay_uses_frozen_snapshot_and_ranking_context_not_provider_tape(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            path = root / "capture.json"
            expected = {"recommendations": [], "lastfm_api_configured": False}
            write_capture(
                path, gathered=_gathered(), lastfm_calls=[], provider_events=[{"operation": "provenance"}],
                output=json.dumps(expected), count=1, git_sha="fixture",
                ranking_context={"ranking_now": 1234.5, "history": [], "diversity_setting": 25},
            )
            def fake_recommend(**kwargs):
                self.assertEqual(kwargs["count"], 1)
                self.assertEqual(list(kwargs["_gathered_override"]["albums"]), [("fixtureartist", "fixturealbum")])
                self.assertEqual(kwargs["_ranking_context_override"], {"ranking_now": 1234.5, "history": [], "diversity_setting": 25})
                self.assertNotIn("_provider_tape", kwargs)
                return json.dumps(expected)
            output = StringIO()
            with patch("navidrome_server.recommend_new_music", side_effect=fake_recommend), redirect_stdout(output):
                self.assertEqual(replay_main([str(path)]), 0)
            report = json.loads(output.getvalue())
            self.assertTrue(report["reproduced"])
            self.assertEqual(report["provider_events_replayed"], 0)
            self.assertEqual(report["provider_events_provenance_only"], 1)

    def test_provider_tape_replays_cache_api_and_http_without_calling_providers(self):
        class Response:
            status_code = 200
            def __init__(self, payload):
                self.payload = payload
            def json(self):
                return self.payload
            def raise_for_status(self):
                return None

        class Client:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def get(self, url, **kwargs):
                return Response({"url": url, "params": kwargs.get("params", {})})

        def providers(raise_if_called=False):
            def value(name, result):
                def call(*args, **kwargs):
                    if raise_if_called:
                        raise AssertionError("live provider invoked during replay: " + name)
                    return result
                return call
            def http_get(url, **kwargs):
                if raise_if_called:
                    raise AssertionError("live HTTP GET invoked during replay")
                return Response({"url": url, "params": kwargs.get("params", {})})
            def http_client(**kwargs):
                if raise_if_called:
                    raise AssertionError("live HTTP client opened during replay")
                return Client()
            return RecommendationProviders(
                listenbrainz_recent=value("listens", [{"listen": 1}]),
                listenbrainz_username=value("username", "fixture-user"),
                music_key=lambda value: str(value).casefold(),
                metadata_cache_get=value("cache_get", None),
                metadata_cache_set=value("cache_set", None),
                is_album_candidate=lambda candidate: True,
                api_call=value("api_call", {"albumList2": {"album": []}}),
                items=lambda response: response,
                http_get=http_get,
                http_client=http_client,
                sleep=lambda seconds: None,
            )

        record = ProviderTape("record")
        wrapped = record.wrap(providers())
        self.assertEqual(wrapped.listenbrainz_recent(days=30), [{"listen": 1}])
        self.assertEqual(wrapped.listenbrainz_username(), "fixture-user")
        self.assertIsNone(wrapped.metadata_cache_get("cache-key", ttl_seconds=60))
        wrapped.metadata_cache_set("cache-key", {"cached": True})
        self.assertEqual(wrapped.api_call("getAlbumList2", type="newest"), {"albumList2": {"album": []}})
        self.assertEqual(wrapped.http_get("https://example.test", params={"x": 1}).json()["params"], {"x": 1})
        with wrapped.http_client(timeout=20, follow_redirects=True) as client:
            self.assertEqual(client.get("https://musicbrainz.org", params={"fmt": "json"}).json()["params"], {"fmt": "json"})

        replay = ProviderTape("replay", record.events)
        offline = replay.wrap(providers(raise_if_called=True))
        self.assertEqual(offline.listenbrainz_recent(days=30), [{"listen": 1}])
        self.assertEqual(offline.listenbrainz_username(), "fixture-user")
        self.assertIsNone(offline.metadata_cache_get("cache-key", ttl_seconds=60))
        offline.metadata_cache_set("cache-key", {"cached": True})
        self.assertEqual(offline.api_call("getAlbumList2", type="newest"), {"albumList2": {"album": []}})
        self.assertEqual(offline.http_get("https://example.test", params={"x": 1}).json()["params"], {"x": 1})
        with offline.http_client(timeout=20, follow_redirects=True) as client:
            self.assertEqual(client.get("https://musicbrainz.org", params={"fmt": "json"}).json()["params"], {"fmt": "json"})
        replay.assert_consumed()

    def test_http_error_replay_preserves_method_and_fully_resolved_url(self):
        import httpx

        request_url = "https://musicbrainz.org/ws/2/recording/abc"
        params = {"fmt": "json", "inc": "artists"}
        def live_request(url, **kwargs):
            request = httpx.Request("GET", httpx.URL(url, params=kwargs.get("params")) )
            return httpx.Response(503, json={"error": "temporarily unavailable"}, request=request)

        recorded = ProviderTape("record")
        live_response = recorded.response("http_get", live_request, request_url, params=params)
        with self.assertRaises(httpx.HTTPStatusError) as live_error:
            live_response.raise_for_status()

        replayed = ProviderTape("replay", recorded.events)
        replay_response = replayed.response(
            "http_get",
            lambda *_args, **_kwargs: self.fail("live HTTP request must not run during replay"),
            request_url,
            params=params,
        )
        with self.assertRaises(httpx.HTTPStatusError) as replay_error:
            replay_response.raise_for_status()

        self.assertEqual(replay_response.request.method, live_response.request.method)
        self.assertEqual(str(replay_response.request.url), str(live_response.request.url))
        self.assertEqual(str(replay_error.exception), str(live_error.exception))
        self.assertIn("fmt=json", str(replay_error.exception))
        replayed.assert_consumed()

    def test_lastfm_replay_requires_exact_call_order_and_full_consumption(self):
        replay = LastFmReplay([
            {"artist": "A", "album": "One", "result": [{"listeners": 3}, None]},
            {"artist": "B", "album": "Two", "result": [None, "not found"]},
        ])
        self.assertEqual(replay("A", "One"), ({"listeners": 3}, None))
        self.assertEqual(replay("B", "Two"), (None, "not found"))
        replay.assert_consumed()
        mismatch = LastFmReplay([{"artist": "A", "album": "One", "result": [None, None]}])
        with self.assertRaisesRegex(RuntimeError, "call order mismatch"):
            mismatch("B", "Two")


if __name__ == "__main__":
    unittest.main()
