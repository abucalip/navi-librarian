"""Offline tests for the flagged ListenBrainz batch resolution path (no network)."""
import unittest
from unittest import mock

import discovery_candidate_gathering as gathering
import discovery_candidate_supply as supply
from discovery_batch_metadata import (
    BATCH_RECORDING_CHUNK,
    LISTENBRAINZ_RECORDING_BATCH_URL,
    LISTENBRAINZ_RELEASE_GROUP_URL,
    synthesize_recording,
)
from discovery_candidate_gathering import RecommendationProviders, gather_recommendation_candidates


def _mb_recording(index, *, artist="Synthetic Artist"):
    return {
        "title": f"Track {index}",
        "artist-credit": [{"name": artist, "artist": {"id": f"artist-{artist}"}}],
        "releases": [{"release-group": {
            "id": f"rg-{index}", "title": f"Album {index}",
            "primary-type": "Album", "secondary-types": [],
        }}],
    }


def _entry(index, *, artist="Synthetic Artist"):
    return {
        "recording": {"name": f"Track {index}"},
        "artist": {"name": artist, "artists": [
            {"artist_credit_name": artist, "join_phrase": "", "artist_mbid": f"artist-{artist}"},
        ]},
        "release": {"name": f"Release {index}", "release_group_mbid": f"rg-{index}"},
    }


class _Response:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("status")


class _MusicBrainzClient:
    def __init__(self, recordings):
        self.recordings = recordings
        self.requested = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, params=None, headers=None):
        mbid = url.rsplit("/", 1)[-1]
        if mbid.startswith("rec-"):
            self.requested.append(mbid)
        return _Response(self.recordings.get(mbid, {}))


class _Harness:
    """Builds providers over synthetic CF recordings with a stubbed batch surface."""

    def __init__(self, count, *, batch_status=200, batch_entries=None, rg_status=200,
                 rg_types=None, mb_recordings=None):
        self.count = count
        self.batch_status = batch_status
        self.batch_entries = batch_entries
        self.rg_status = rg_status
        self.rg_types = rg_types
        self.posts = []
        self.bodies = []
        self.rg_gets = []
        self.mb_client = _MusicBrainzClient(mb_recordings or {})
        self.sleeps = []
        self.cache_writes = []

    def _recommendations(self):
        return [{"recording_mbid": f"rec-{i}", "score": 1000 - i} for i in range(self.count)]

    def http_get(self, url, params=None, **kwargs):
        if url == LISTENBRAINZ_RELEASE_GROUP_URL:
            self.rg_gets.append(params["release_group_mbids"].split(","))
            if self.rg_status != 200:
                return _Response({}, status_code=self.rg_status)
            ids = params["release_group_mbids"].split(",")
            if self.rg_types is None:
                return _Response({
                    rg: {"release_group": {"name": f"Album {rg}", "type": "Album"}} for rg in ids
                })
            return _Response({
                rg: {"release_group": {"name": meta["title"], "type": meta["type"]}}
                for rg, meta in self.rg_types.items()
            })
        offset = params["offset"]
        items = self._recommendations()[offset:offset + 100]
        return _Response({"payload": {"mbids": items}})

    def http_post(self, url, json=None, headers=None, timeout=None):
        self.posts.append((url, list(json["recording_mbids"])))
        self.bodies.append(dict(json))
        if self.batch_status != 200:
            return _Response({}, status_code=self.batch_status)
        if self.batch_entries is not None:
            return _Response(self.batch_entries)
        return _Response({mbid: _entry(int(mbid.split("-")[1])) for mbid in json["recording_mbids"]})

    def assert_inc(self, test):
        for body in self.bodies:
            test.assertIn("release", body["inc"].split())

    def providers(self):
        return RecommendationProviders(
            listenbrainz_recent=lambda days: [],
            listenbrainz_username=lambda: "fixture-user",
            music_key=lambda value: "".join(str(value).casefold().split()),
            metadata_cache_get=lambda key, **kwargs: None,
            metadata_cache_set=lambda key, value, **kwargs: self.cache_writes.append(key),
            is_album_candidate=lambda candidate: True,
            api_call=lambda *args, **kwargs: {},
            items=lambda response: [],
            http_get=self.http_get,
            http_client=lambda *args, **kwargs: self.mb_client,
            sleep=self.sleeps.append,
            http_post=self.http_post,
        )


def _run(harness, *, batch_enabled, title_filter_enabled=True):
    with mock.patch.object(gathering, "CF_BATCH_RESOLUTION_ENABLED", batch_enabled), \
            mock.patch.object(supply, "BATCH_TITLE_FILTER_ENABLED", title_filter_enabled):
        return gather_recommendation_candidates(harness.providers())


class BatchFlagGateTests(unittest.TestCase):
    def test_flag_off_by_default_uses_per_recording_lookups_only(self):
        self.assertFalse(gathering.CF_BATCH_RESOLUTION_ENABLED)
        harness = _Harness(3)

        _run(harness, batch_enabled=False)

        self.assertEqual(harness.posts, [])
        self.assertEqual(harness.rg_gets, [])
        self.assertEqual(len(harness.mb_client.requested), 3)

    def test_flag_on_without_title_filter_does_not_batch(self):
        harness = _Harness(3)

        _run(harness, batch_enabled=True, title_filter_enabled=False)

        self.assertEqual(harness.posts, [])
        self.assertEqual(len(harness.mb_client.requested), 3)

    def test_flag_on_without_post_client_does_not_batch(self):
        harness = _Harness(3)
        providers = harness.providers()
        providers = RecommendationProviders(**{**providers.__dict__, "http_post": None})
        with mock.patch.object(gathering, "CF_BATCH_RESOLUTION_ENABLED", True), \
                mock.patch.object(supply, "BATCH_TITLE_FILTER_ENABLED", True):
            gathering.gather_recommendation_candidates(providers)

        self.assertEqual(harness.posts, [])


class BatchResolutionPathTests(unittest.TestCase):
    def test_batch_replaces_per_recording_calls_and_skips_spacing_sleeps(self):
        harness = _Harness(5)

        result = _run(harness, batch_enabled=True)

        self.assertEqual(len(harness.posts), 1)
        self.assertEqual(harness.posts[0][0], LISTENBRAINZ_RECORDING_BATCH_URL)
        harness.assert_inc(self)
        self.assertEqual(len(harness.posts[0][1]), 5)
        self.assertEqual(harness.mb_client.requested, [])
        self.assertEqual(harness.sleeps, [])
        self.assertEqual(len(harness.rg_gets), 1)
        self.assertEqual(len(result["albums"]), 5)
        self.assertEqual([k for k in harness.cache_writes if k.startswith("mb:recording:")], [])
        self.assertEqual(result["candidate_supply"]["cf_recordings"]["cf_recordings_resolved"], 5)

    def test_batch_hits_do_not_spend_the_musicbrainz_budget(self):
        harness = _Harness(150)

        with mock.patch.object(gathering, "CF_MAX_UNCACHED_RESOLUTIONS", 100):
            result = _run(harness, batch_enabled=True)

        requested = [mbid for _url, batch in harness.posts for mbid in batch]
        self.assertEqual(requested, [f"rec-{i}" for i in range(150)])
        self.assertEqual([len(batch) for _url, batch in harness.posts], [100, 50])
        self.assertEqual(harness.mb_client.requested, [])
        paging = result["candidate_supply"]["cf_paging"]
        self.assertEqual(paging["uncached_resolution_calls"], 0)
        self.assertEqual(paging["resolution_budget_skipped"], 0)
        self.assertEqual(result["candidate_supply"]["cf_recordings"]["cf_recordings_resolved"], 150)

    def test_batch_misses_still_obey_the_musicbrainz_budget(self):
        harness = _Harness(6, batch_entries={"rec-0": _entry(0)},
                           mb_recordings={f"rec-{i}": _mb_recording(i) for i in range(1, 6)})

        with mock.patch.object(gathering, "CF_MAX_UNCACHED_RESOLUTIONS", 3):
            result = _run(harness, batch_enabled=True)

        self.assertEqual(len(harness.mb_client.requested), 3)
        paging = result["candidate_supply"]["cf_paging"]
        self.assertEqual(paging["uncached_resolution_calls"], 3)
        self.assertEqual(paging["resolution_budget_skipped"], 2)

    def test_large_request_is_split_into_bounded_chunks(self):
        harness = _Harness(BATCH_RECORDING_CHUNK + 1)
        with mock.patch.object(gathering, "CF_MAX_UNCACHED_RESOLUTIONS", 1000):
            _run(harness, batch_enabled=True)

        self.assertEqual([len(batch) for _url, batch in harness.posts], [BATCH_RECORDING_CHUNK, 1])

    def test_batch_post_failure_falls_back_to_per_recording_lookups(self):
        harness = _Harness(3, batch_status=503, mb_recordings={
            f"rec-{i}": _mb_recording(i) for i in range(3)
        })

        result = _run(harness, batch_enabled=True)

        self.assertEqual(len(harness.mb_client.requested), 3)
        self.assertEqual(len(result["albums"]), 3)

    def test_release_group_failure_falls_back_to_per_recording_lookups(self):
        harness = _Harness(2, rg_status=503, mb_recordings={
            f"rec-{i}": _mb_recording(i) for i in range(2)
        })

        _run(harness, batch_enabled=True)

        self.assertEqual(len(harness.mb_client.requested), 2)

    def test_missing_batch_entry_is_resolved_per_recording(self):
        harness = _Harness(2, batch_entries={"rec-0": _entry(0)},
                           mb_recordings={"rec-1": _mb_recording(1)})

        _run(harness, batch_enabled=True)

        self.assertEqual(harness.mb_client.requested, ["rec-1"])


class BatchEligibilityTests(unittest.TestCase):
    def test_marked_live_release_is_rejected_on_batch_path(self):
        harness = _Harness(2, rg_types={
            "rg-0": {"title": "Live at Somewhere", "type": "Album"},
            "rg-1": {"title": "Quiet Studio", "type": "Album"},
        })

        result = _run(harness, batch_enabled=True)

        titles = {value["album"] for value in result["albums"].values()}
        self.assertEqual(titles, {"Quiet Studio"})

    def test_marked_title_makes_no_individual_lookup_and_no_album(self):
        harness = _Harness(2, rg_types={
            "rg-0": {"title": "Greatest Hits Live", "type": "Album"},
            "rg-1": {"title": "Quiet Studio", "type": "Album"},
        })

        result = _run(harness, batch_enabled=True)

        # The marked recording is rejected from the batch data alone: no per-recording
        # MusicBrainz fallback, and no album from it.
        self.assertNotIn("rec-0", harness.mb_client.requested)
        self.assertEqual(harness.mb_client.requested, [])
        titles = {value["album"] for value in result["albums"].values()}
        self.assertEqual(titles, {"Quiet Studio"})

    def test_non_album_primary_type_is_rejected_on_batch_path(self):
        harness = _Harness(1, rg_types={"rg-0": {"title": "Quiet Single", "type": "Single"}})

        result = _run(harness, batch_enabled=True)

        self.assertEqual(len(result["albums"]), 0)

    def test_release_group_without_metadata_contributes_no_album(self):
        harness = _Harness(1, rg_types={})

        result = _run(harness, batch_enabled=True)

        self.assertEqual(len(result["albums"]), 0)


class SynthesizeRecordingTests(unittest.TestCase):
    def _reject(self, title):
        with mock.patch.object(supply, "BATCH_TITLE_FILTER_ENABLED", True):
            return supply.batch_title_marker_rejection(title)

    def test_release_group_response_uses_wrapped_name_field(self):
        from discovery_batch_metadata import fetch_release_group_metadata

        def get(url, params=None, headers=None, timeout=None):
            return _Response({"rg-a": {"release_group": {"name": "Quiet Studio", "type": "Album",
                                                          "date": "2001"}}})

        meta = fetch_release_group_metadata(get, ["rg-a"], headers={})
        self.assertEqual(meta["rg-a"], {"title": "Quiet Studio", "type": "Album"})

    def test_shape_matches_per_recording_resolver_fields(self):
        recording = synthesize_recording(
            _entry(7),
            {"rg-7": {"title": "Quiet Studio", "type": "Album"}},
            title_rejection=self._reject,
        )

        self.assertEqual(recording["title"], "Track 7")
        self.assertEqual(recording["artist-credit"][0]["name"], "Synthetic Artist")
        self.assertEqual(recording["artist-credit"][0]["artist"]["id"], "artist-Synthetic Artist")
        group = recording["releases"][0]["release-group"]
        self.assertEqual((group["id"], group["title"], group["primary-type"]),
                         ("rg-7", "Quiet Studio", "Album"))
        self.assertEqual(group["secondary-types"], [])

    def test_entry_without_artist_credit_yields_none(self):
        entry = {"recording": {"name": "Untitled"}, "artist": {"artists": []},
                 "release": {"release_group_mbid": "rg-x"}}

        self.assertIsNone(synthesize_recording(entry, {}, title_rejection=self._reject))

    def test_marked_title_drops_release_group_but_keeps_recording(self):
        recording = synthesize_recording(
            _entry(1),
            {"rg-1": {"title": "Live Set", "type": "Album"}},
            title_rejection=self._reject,
        )

        self.assertIsNotNone(recording)
        self.assertEqual(recording["releases"], [])


if __name__ == "__main__":
    unittest.main()
