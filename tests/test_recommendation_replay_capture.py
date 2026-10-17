import json
import os
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from discovery_candidate_gathering import RecommendationProviders
from recommendation_replay import (
    LastFmReplay,
    ProviderTape,
    freeze_gathered_inputs,
    load_capture,
    thaw_gathered_inputs,
    write_capture,
)


def _gathered():
    return {
        "listens": [{"track_metadata": {"artist_name": "Fixture Artist"}}],
        "recent_artists": Counter({"fixtureartist": 2}),
        "recent_artist_mbid_counts": Counter({"artist-mbid": 2}),
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
        self.assertEqual(restored["core_families"], original["core_families"])
        self.assertEqual(restored["library_by_title"], original["library_by_title"])

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
            )
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            envelope = load_capture(path)
            self.assertEqual(envelope["git_sha"], "fixture-sha")
            self.assertEqual(envelope["payload"]["count"], 1)
            with self.assertRaises(FileExistsError):
                write_capture(
                    path, gathered=_gathered(), lastfm_calls=[], provider_events=[],
                    output=expected, count=1, git_sha="other-sha",
                )

    def test_capture_checksum_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            path = root / "capture.json"
            write_capture(
                path, gathered=_gathered(), lastfm_calls=[], provider_events=[],
                output=json.dumps({"recommendations": []}), count=1, git_sha="fixture",
            )
            envelope = json.loads(path.read_text(encoding="utf-8"))
            envelope["payload"]["count"] = 99
            path.write_text(json.dumps(envelope), encoding="utf-8")
            path.chmod(0o600)
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                load_capture(path)

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
            return RecommendationProviders(
                listenbrainz_recent=value("listens", [{"listen": 1}]),
                listenbrainz_username=value("username", "fixture-user"),
                music_key=lambda value: str(value).casefold(),
                metadata_cache_get=value("cache_get", None),
                metadata_cache_set=value("cache_set", None),
                is_album_candidate=lambda candidate: True,
                api_call=value("api_call", {"albumList2": {"album": []}}),
                items=lambda response: response,
                http_get=lambda url, **kwargs: Response({"url": url, "params": kwargs.get("params", {})}),
                http_client=lambda **kwargs: Client(),
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
