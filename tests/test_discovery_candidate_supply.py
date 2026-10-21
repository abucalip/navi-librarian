"""Deterministic, aggregate-only candidate-supply diagnostics tests."""
import json
import unittest
from unittest import mock

from discovery.candidate_gathering import RecommendationProviders, gather_recommendation_candidates
from discovery.candidate_supply import (
    candidate_supply_report,
    classify_error,
    cf_records_from_tape,
    summarize_candidate_stages,
    summarize_cf_albums,
    summarize_cf_recordings,
    summarize_supplementary_tape,
    summarize_supplementary_yield,
)

ARTIST_A = "Fixture Artist Alpha"
ARTIST_B = "Fixture Artist Beta"


def _key(value):
    return "".join(str(value).casefold().split())


class HTTPStatusError(Exception):
    """Named like the httpx exception so the bounded classifier reports it."""


class SecretUrlError(Exception):
    """Unknown exception name: must collapse to 'other' without its message."""


class CandidateSupplySummaryTests(unittest.TestCase):
    def test_empty_pool_reports_zeros_and_null_shares(self):
        cf = summarize_cf_recordings([], returned=0)
        self.assertEqual(cf["cf_recordings_resolved"], 0)
        self.assertIsNone(cf["cf_top2_artist_recording_share"])
        self.assertEqual(cf["cf_top_artist_recording_shares"], [])
        self.assertEqual(summarize_cf_albums([], _key)["cf_albums"], 0)
        stages = summarize_candidate_stages([], [])
        self.assertEqual((stages["candidates_total"], stages["selected"]), (0, 0))
        supplementary = summarize_supplementary_yield([], planned=0)
        self.assertEqual(supplementary["supplementary_queries_attempted"], 0)

    def test_single_artist_pool_has_full_concentration(self):
        records = [{"resolved": True, "artist_key": "alpha", "error_class": None}] * 3
        cf = summarize_cf_recordings(records, returned=3)
        self.assertEqual(cf["cf_distinct_recording_artists"], 1)
        self.assertEqual(cf["cf_top2_artist_recording_share"], 1.0)
        self.assertEqual(cf["cf_top_artist_recording_shares"], [1.0])

    def test_provider_failure_pool_reports_bounded_classes_only(self):
        records = [
            {"resolved": False, "artist_key": None, "error_class": classify_error(HTTPStatusError("503 https://host/x"))},
            {"resolved": False, "artist_key": None, "error_class": classify_error(SecretUrlError("token=abc"))},
        ]
        cf = summarize_cf_recordings(records, returned=2)
        self.assertEqual(cf["cf_recordings_failed"], 2)
        self.assertEqual(cf["cf_failure_classes"], {"HTTPStatusError": 1, "other": 1})
        self.assertIsNone(cf["cf_top2_artist_recording_share"])
        rendered = json.dumps(cf)
        self.assertNotIn("token", rendered)
        self.assertNotIn("https://", rendered)

    def test_common_transport_errors_keep_their_class_not_other(self):
        names = ["ConnectTimeout", "PoolTimeout", "ReadError", "RemoteProtocolError", "TransportError"]
        for name in names:
            exc = type(name, (Exception,), {})("https://host/x token=abc")
            self.assertEqual(classify_error(exc), name)
        self.assertEqual(classify_error(SecretUrlError("x")), "other")

    def test_error_in_record_after_resolution_counts_as_failed(self):
        records = [{"resolved": True, "artist_key": "alpha", "error_class": "ValueError"}]
        cf = summarize_cf_recordings(records, returned=1)
        self.assertEqual((cf["cf_recordings_resolved"], cf["cf_recordings_failed"]), (0, 1))

    def test_album_shares_count_only_listenbrainz_cf_albums(self):
        albums = [
            {"primary_artist": ARTIST_A, "discovery_sources": ["listenbrainz_cf"]},
            {"primary_artist": ARTIST_A, "discovery_sources": ["listenbrainz_cf"]},
            {"primary_artist": ARTIST_B, "discovery_sources": ["listenbrainz_cf"]},
            {"primary_artist": "Fixture Artist Gamma", "discovery_sources": ["profile_tag_search"]},
        ]
        result = summarize_cf_albums(albums, _key)
        self.assertEqual(result["cf_albums"], 3)
        self.assertEqual(result["cf_album_artists"], 2)
        self.assertEqual(result["cf_top_artist_album_shares"], [0.666667, 0.333333])

    def test_stage_counts_separate_owned_duplicate_and_cap_rejections(self):
        albums = [
            {"artist": ARTIST_A, "primary_artist": ARTIST_A, "album": "One", "artist_mbid": "m1"},
            {"artist": ARTIST_A, "primary_artist": ARTIST_A, "album": "Two", "artist_mbid": "m1"},
            {"artist": ARTIST_B, "primary_artist": ARTIST_B, "album": "Three", "artist_mbid": "m2"},
            {"artist": ARTIST_B, "primary_artist": ARTIST_B, "album": "Four", "artist_mbid": "m2"},
        ]
        debug_rows = [
            {"artist": ARTIST_A, "album": "One", "exact_owned": True, "selection_decision": "already_owned"},
            {"artist": ARTIST_A, "album": "Two", "exact_owned": False, "selection_decision": "selected"},
            {"artist": ARTIST_B, "album": "Three", "exact_owned": False, "selection_decision": "selected"},
            {"artist": ARTIST_B, "album": "Four", "exact_owned": False, "selection_decision": "artist_already_selected"},
        ]
        stages = summarize_candidate_stages(albums, debug_rows)
        self.assertEqual(stages["owned_candidates"], 1)
        self.assertEqual(stages["unowned_before_dedupe"], 3)
        self.assertEqual(stages["unowned_unique_after_dedupe"], 3)
        self.assertEqual(stages["duplicate_identity_rows"], 0)
        self.assertEqual(stages["artist_cap_rejections"], 1)
        self.assertEqual(stages["unowned_unique_after_artist_cap"], 2)
        self.assertEqual(stages["distinct_artists_unowned"], 2)
        self.assertEqual(stages["selected"], 2)

    def test_artist_cap_relabelled_as_duplicate_is_still_counted_as_cap(self):
        # Mirrors the allocator: a later phase re-visits a cap-blocked candidate and
        # overwrites its label with "duplicate_candidate". The cap must still count.
        albums = [
            {"artist": ARTIST_A, "primary_artist": ARTIST_A, "album": "Picked", "artist_mbid": "m1"},
            {"artist": ARTIST_A, "primary_artist": ARTIST_A, "album": "Blocked", "artist_mbid": "m1"},
        ]
        debug_rows = [
            {"artist": ARTIST_A, "album": "Picked", "exact_owned": False, "selection_decision": "selected"},
            {"artist": ARTIST_A, "album": "Blocked", "exact_owned": False, "selection_decision": "duplicate_candidate"},
        ]
        stages = summarize_candidate_stages(albums, debug_rows)
        self.assertEqual(stages["artist_cap_rejections"], 1)
        self.assertEqual(stages["duplicate_identity_rows"], 0)
        self.assertEqual(stages["unowned_unique_after_artist_cap"], 1)

    def test_duplicate_identity_is_counted_once_after_dedupe(self):
        albums = [
            {"artist": ARTIST_A, "primary_artist": ARTIST_A, "album": "Same", "artist_mbid": "m1"},
            {"artist": "Alias", "primary_artist": "Alias", "album": "Same", "artist_mbid": "m1"},
        ]
        debug_rows = [
            {"artist": ARTIST_A, "album": "Same", "exact_owned": False, "selection_decision": "selected"},
            {"artist": "Alias", "album": "Same", "exact_owned": False, "selection_decision": "duplicate_candidate"},
        ]
        stages = summarize_candidate_stages(albums, debug_rows)
        self.assertEqual(stages["unowned_before_dedupe"], 2)
        self.assertEqual(stages["unowned_unique_after_dedupe"], 1)
        self.assertEqual(stages["duplicate_identity_rows"], 1)

    def test_supplementary_yield_separates_zero_yield_failed_and_unattempted(self):
        outcomes = [(2, None), (0, None), (0, "HTTPStatusError")]
        result = summarize_supplementary_yield(outcomes, planned=5)
        self.assertEqual(result["supplementary_queries_attempted"], 3)
        self.assertEqual(result["supplementary_queries_not_attempted"], 2)
        self.assertEqual(result["supplementary_queries_with_yield"], 1)
        self.assertEqual(result["supplementary_queries_zero_yield"], 1)
        self.assertEqual(result["supplementary_queries_failed"], 1)
        self.assertEqual(result["supplementary_candidates_added"], 2)


class TapeReplayTests(unittest.TestCase):
    def test_tape_rebuilds_recording_artists_and_failures(self):
        tape = [
            {"operation": "metadata_cache_get", "args": ["mb:recording:r1"], "result": {"artist-credit": [{"name": ARTIST_A}]}},
            {"operation": "metadata_cache_get", "args": ["mb:recording:r2"], "result": None},
            {"operation": "metadata_cache_set", "args": ["mb:recording:r2", {"artist-credit": [{"name": ARTIST_B}]}]},
            {"operation": "metadata_cache_get", "args": ["mb:recording:r3"], "result": None},
            {"operation": "http_client.get", "args": ["u"], "request_url": "https://musicbrainz.org/ws/2/recording/r3", "status_code": 503},
        ]
        records = cf_records_from_tape(tape, ["r1", "r2", "r3"], _key)
        self.assertEqual([r["resolved"] for r in records], [True, True, False])
        self.assertEqual(records[0]["artist_key"], _key(ARTIST_A))
        self.assertEqual(records[1]["artist_key"], _key(ARTIST_B))
        self.assertEqual(records[2]["error_class"], "HTTPStatusError")

    def test_tape_supplementary_counts_attempts_hits_and_failures(self):
        tape = [
            {"operation": "metadata_cache_get", "args": ["mb:release-group-search:q1"], "result": None},
            {"operation": "http_client.get", "args": [], "request_url": "https://musicbrainz.org/ws/2/release-group/", "status_code": 503},
            {"operation": "metadata_cache_get", "args": ["mb:release-group-search:q2"], "result": {"release-groups": []}},
        ]
        result = summarize_supplementary_tape(tape)
        self.assertEqual(result["supplementary_queries_attempted"], 2)
        self.assertEqual(result["supplementary_cache_hits"], 1)
        self.assertEqual(result["supplementary_queries_failed"], 1)

    def test_offline_report_on_synthetic_payload_has_no_identities(self):
        payload = {
            "gathered_inputs": {
                "cf_recording_mbids": ["r1", "r2"],
                "cf_recordings_returned": 2,
                "albums": [{"key": ["a", "b"], "value": {
                    "artist": ARTIST_A, "primary_artist": ARTIST_A, "album": "Album X",
                    "artist_mbid": "m1", "discovery_sources": ["listenbrainz_cf"]}}],
            },
            "provider_events": [
                {"operation": "metadata_cache_get", "args": ["mb:recording:r1"], "result": {"artist-credit": [{"name": ARTIST_A}]}},
                {"operation": "metadata_cache_get", "args": ["mb:recording:r2"], "result": {"artist-credit": [{"name": ARTIST_A}]}},
            ],
            "expected_output": {"debug_all_candidates": [
                {"artist": ARTIST_A, "album": "Album X", "exact_owned": False, "selection_decision": "selected"},
            ]},
        }
        report = candidate_supply_report(payload, payload["expected_output"]["debug_all_candidates"])
        self.assertEqual(report["cf_recordings"]["cf_top2_artist_recording_share"], 1.0)
        self.assertEqual(report["stages"]["selected"], 1)
        rendered = json.dumps(report)
        self.assertNotIn(ARTIST_A, rendered)
        self.assertNotIn("Album X", rendered)


class GatheringSupplyTests(unittest.TestCase):
    def _providers(self, mbids, recordings):
        def cache_get(key, **kwargs):
            if key.startswith("mb:recording:"):
                value = recordings[key.split(":", 2)[2]]
                if isinstance(value, Exception):
                    raise value
                return value
            if key.startswith("mb:artist-genres:"):
                return []
            return None

        return RecommendationProviders(
            listenbrainz_recent=lambda days: [],
            listenbrainz_username=lambda: "fixture-user",
            music_key=_key,
            metadata_cache_get=cache_get,
            metadata_cache_set=lambda *args, **kwargs: None,
            is_album_candidate=lambda candidate: True,
            api_call=lambda *args, **kwargs: {},
            items=lambda response: [],
            http_get=lambda *args, **kwargs: _Response({"payload": {"mbids": [{"recording_mbid": m, "score": 1} for m in mbids]}}),
            http_client=lambda *args, **kwargs: _Client(),
            sleep=lambda _seconds: None,
        )

    def _recording(self, artist, album):
        return {
            "title": "Track",
            "artist-credit": [{"name": artist, "artist": {"id": "mbid-" + _key(artist)}}],
            "releases": [{"release-group": {"id": "rg-" + _key(album), "title": album, "primary-type": "Album", "secondary-types": []}}],
        }

    def test_gathering_reports_cf_supply_for_two_artist_pool_with_failure(self):
        recordings = {
            "r1": self._recording(ARTIST_A, "Album 1"),
            "r2": self._recording(ARTIST_A, "Album 2"),
            "r3": HTTPStatusError("503"),
        }
        providers = self._providers(["r1", "r2", "r3"], recordings)
        with mock.patch("discovery.library_snapshot.fetch_album_inventory", return_value=[]):
            gathered = gather_recommendation_candidates(providers)
        supply = gathered["candidate_supply"]
        self.assertEqual(supply["cf_recordings"]["cf_recordings_returned"], 3)
        self.assertEqual(supply["cf_recordings"]["cf_recordings_resolved"], 2)
        self.assertEqual(supply["cf_recordings"]["cf_failure_classes"], {"HTTPStatusError": 1})
        self.assertEqual(supply["cf_recordings"]["cf_distinct_recording_artists"], 1)
        self.assertEqual(supply["cf_albums"]["cf_albums"], 2)
        self.assertEqual(supply["supplementary"]["supplementary_queries_attempted"], 0)
        self.assertEqual(gathered["cf_recordings_resolved"], 2)

    def test_gathering_empty_pool_reports_zero_supply(self):
        providers = self._providers([], {})
        result = json.loads(gather_recommendation_candidates(providers))
        self.assertEqual(result["recommendations"], [])


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class _Client:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, *args, **kwargs):
        raise AssertionError("fixture must not call live providers")


if __name__ == "__main__":
    unittest.main()


class EligibilityBoundaryTests(unittest.TestCase):
    """Synthetic boundary checks: release-type filtering, ownership, duplicates, sources."""

    def _groups(self):
        from discovery.recommendations import is_album_candidate
        return is_album_candidate, _key

    def test_release_group_predicate_labels_each_rejection(self):
        from discovery.candidate_supply import cf_release_group_rejection
        is_album, music_key = self._groups()

        def reason(group):
            return cf_release_group_rejection(group, is_album_candidate=is_album, music_key=music_key)

        self.assertIsNone(reason({"primary-type": "Album", "title": "Fixture Record One", "secondary-types": []}))
        self.assertEqual(reason({"primary-type": "Single", "title": "Fixture Single", "secondary-types": []}),
                         "not_album_primary_type")
        self.assertEqual(reason({"primary-type": "Album", "title": "Fixture Mixtape Thing", "secondary-types": ["Mixtape/Street"]}),
                         "not_album_candidate")
        self.assertEqual(reason({"primary-type": "Album", "title": "Fixture Essential Collection", "secondary-types": []}),
                         "undesirable_title")
        # The shared album check already rejects these secondaries; the explicit
        # secondary rule is then reached only when the album check accepts them.
        self.assertEqual(reason({"primary-type": "Album", "title": "Fixture Record Two", "secondary-types": ["Compilation"]}),
                         "not_album_candidate")
        self.assertEqual(
            cf_release_group_rejection(
                {"primary-type": "Album", "title": "Fixture Record Two", "secondary-types": ["DJ-mix"]},
                is_album_candidate=lambda item: True, music_key=music_key,
            ),
            "excluded_secondary_type",
        )

    def test_eligibility_counts_come_from_tape_recordings_only(self):
        from discovery.candidate_supply import summarize_cf_release_eligibility
        is_album, music_key = self._groups()
        ok = {"release-group": {"primary-type": "Album", "title": "Fixture Record One", "secondary-types": []}}
        comp = {"release-group": {"primary-type": "Album", "title": "Fixture Record Two", "secondary-types": ["Compilation"]}}
        tape = [
            {"operation": "metadata_cache_get", "args": ["mb:recording:r1"],
             "result": {"artist-credit": [{"name": ARTIST_A}], "releases": [ok, comp]}},
            {"operation": "metadata_cache_get", "args": ["mb:recording:r2"], "result": None},
        ]
        result = summarize_cf_release_eligibility(
            tape, ["r1", "r2"], is_album_candidate=is_album, music_key=music_key,
        )
        self.assertEqual(result["cf_recordings_with_payload"], 1)
        self.assertEqual(result["cf_release_groups_seen"], 2)
        self.assertEqual(result["cf_release_groups_eligible"], 1)
        self.assertEqual(result["cf_release_group_rejections"]["not_album_candidate"], 1)
        self.assertEqual(result["cf_release_group_rejections"]["not_album_primary_type"], 0)
        self.assertNotIn(ARTIST_A, json.dumps(result))

    def test_unowned_unique_counts_per_discovery_source(self):
        from discovery.candidate_supply import summarize_candidate_stages
        albums = [
            {"artist": ARTIST_A, "primary_artist": ARTIST_A, "album": "One", "artist_mbid": "m1",
             "discovery_sources": ["listenbrainz_cf", "profile_tag_search"]},
            {"artist": ARTIST_A, "primary_artist": ARTIST_A, "album": "Owned", "artist_mbid": "m1",
             "discovery_sources": ["listenbrainz_cf"]},
            {"artist": ARTIST_B, "primary_artist": ARTIST_B, "album": "Two", "artist_mbid": "m2",
             "discovery_sources": ["profile_tag_search"]},
            {"artist": "Alias", "primary_artist": "Alias", "album": "Two", "artist_mbid": "m2",
             "discovery_sources": ["listenbrainz_cf"]},
        ]
        debug_rows = [
            {"artist": ARTIST_A, "album": "One", "exact_owned": False, "selection_decision": "selected"},
            {"artist": ARTIST_A, "album": "Owned", "exact_owned": True, "selection_decision": "already_owned"},
            {"artist": ARTIST_B, "album": "Two", "exact_owned": False, "selection_decision": "selected"},
            {"artist": "Alias", "album": "Two", "exact_owned": False, "selection_decision": "duplicate_candidate"},
        ]
        stages = summarize_candidate_stages(albums, debug_rows)
        # Owned rows are excluded; the duplicate identity is counted once per source it carries.
        self.assertEqual(stages["unowned_unique_after_dedupe"], 2)
        self.assertEqual(stages["unowned_unique_by_source"], {
            "listenbrainz_cf": 2, "profile_tag_search": 2,
        })
        self.assertEqual(stages["unowned_unique_by_source_count"], {"2": 2})

    def test_replay_report_emits_release_and_source_boundaries_without_identities(self):
        payload = {
            "gathered_inputs": {
                "cf_recording_mbids": ["r1"],
                "cf_recordings_returned": 1,
                "albums": [{"key": ["a", "b"], "value": {
                    "artist": ARTIST_A, "primary_artist": ARTIST_A, "album": "Album X",
                    "artist_mbid": "m1", "discovery_sources": ["listenbrainz_cf"]}}],
            },
            "provider_events": [
                {"operation": "metadata_cache_get", "args": ["mb:recording:r1"], "result": {
                    "artist-credit": [{"name": ARTIST_A}],
                    "releases": [{"release-group": {"primary-type": "Album", "title": "Album X", "secondary-types": []}}],
                }},
            ],
            "expected_output": {"debug_all_candidates": []},
        }
        report = candidate_supply_report(payload, [])
        self.assertEqual(report["release_eligibility"]["cf_release_groups_eligible"], 1)
        self.assertEqual(report["stages"]["unowned_unique_by_source"], {"listenbrainz_cf": 1})
        rendered = json.dumps(report)
        self.assertNotIn(ARTIST_A, rendered)
        self.assertNotIn("Album X", rendered)
