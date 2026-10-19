"""Synthetic boundary tests for the gated supplementary replenishment step."""
import unittest
from unittest import mock

from discovery_candidate_gathering import (
    REPLENISH_EXTRA_QUERIES,
    RecommendationProviders,
    gather_recommendation_candidates,
)

BASE_QUERIES = [("q-base-1", "jazz", "profile:jazz"), ("q-base-2", "soul", "profile:soul")]
EXTRA_QUERIES = [("q-extra-1", "rock", "explore:rock"), ("q-extra-2", "funk", "explore:funk"),
                 ("q-extra-3", "folk", "explore:folk")]


def _music_key(value):
    return "".join(str(value).casefold().split())


def _cf_item(index):
    return {"recording_mbid": f"rec-{index}", "score": 1000 - index}


def _recording(artist, album, index):
    return {
        "title": f"Track {index}",
        "artist-credit": [{"name": artist, "artist": {"id": f"artist-{artist}"}}],
        "releases": [{"release-group": {
            "id": f"rg-{artist}-{album}",
            "title": album,
            "primary-type": "Album",
            "secondary-types": [],
        }}],
    }


def _group(artist, album, primary="Album", secondary=()):
    return {
        "title": album,
        "primary-type": primary,
        "secondary-types": list(secondary),
        "artist-credit": [{"name": artist, "artist": {"id": f"artist-{artist}"}}],
    }


class _QueryClient:
    """Serves release-group searches keyed by query; records every request in order."""

    def __init__(self, responses):
        self._responses = responses
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, params=None, headers=None):
        if "/release-group/" not in url:
            return _Response({}, status_code=200)
        query = (params or {}).get("query")
        self.queries.append(query)
        response = self._responses.get(query, [])
        if isinstance(response, int):
            return _Response({}, status_code=response)
        return _Response({"release-groups": response}, status_code=200)


class _Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("synthetic status")

    def json(self):
        return self._payload


class ReplenishmentTests(unittest.TestCase):
    def _run(self, *, cf_artists, responses, library=(), shortlist_target=10):
        """Run gathering with CF recordings for ``cf_artists`` and scripted tag searches."""
        pages = {0: [_cf_item(i) for i in range(len(cf_artists))]}
        recordings = {
            f"rec-{i}": _recording(artist, album, i) for i, (artist, album) in enumerate(cf_artists)
        }
        cache = {f"mb:recording:{key}": value for key, value in recordings.items()}
        mb_client = _QueryClient(responses)
        library_items = [dict(item) for item in library]

        def select(_weights, _profile_tags, _pool_tags, *, profile_limit=6, exploration_limit=2):
            if profile_limit == 6:
                return list(BASE_QUERIES)
            return list(BASE_QUERIES) + list(EXTRA_QUERIES)

        providers = RecommendationProviders(
            listenbrainz_recent=lambda days: [],
            listenbrainz_username=lambda: "fixture-user",
            music_key=_music_key,
            metadata_cache_get=lambda key, **kwargs: cache.get(key),
            metadata_cache_set=lambda *args, **kwargs: None,
            is_album_candidate=lambda candidate: True,
            api_call=lambda *args, **kwargs: {"albumList2": {"album": library_items}},
            items=lambda root: list(root or []),
            http_get=lambda url, params=None, **kwargs: _Response(
                {"payload": {"mbids": pages.get(params["offset"], [])}}
            ),
            http_client=lambda *args, **kwargs: mb_client,
            sleep=lambda _seconds: None,
        )
        with mock.patch(
            "discovery_tag_queries.select_supplementary_tag_queries", side_effect=select,
        ):
            result = gather_recommendation_candidates(providers, shortlist_target=shortlist_target)
        return result, mb_client

    def _replenishment(self, result):
        return result["candidate_supply"]["replenishment"]

    def test_meeting_the_target_issues_no_extra_queries(self):
        # Three clear albums meet a target of three: the gate stays closed.
        artists = [("Alpha", "A1"), ("Beta", "B1"), ("Gamma", "G1")]
        responses = {q: [] for q, _f, _s in BASE_QUERIES + EXTRA_QUERIES}

        result, mb_client = self._run(cf_artists=artists, responses=responses, shortlist_target=3)

        summary = self._replenishment(result)
        self.assertFalse(summary["triggered"])
        self.assertEqual(summary["extra_queries_attempted"], 0)
        self.assertEqual(mb_client.queries, [q for q, _f, _s in BASE_QUERIES])

    def test_shortfall_issues_at_most_the_fixed_extra_query_cap(self):
        artists = [("Alpha", "A1")]
        responses = {q: [] for q, _f, _s in BASE_QUERIES + EXTRA_QUERIES}

        result, mb_client = self._run(cf_artists=artists, responses=responses, shortlist_target=10)

        summary = self._replenishment(result)
        self.assertTrue(summary["triggered"])
        self.assertEqual(summary["extra_queries_planned"], REPLENISH_EXTRA_QUERIES)
        self.assertEqual(summary["extra_queries_attempted"], REPLENISH_EXTRA_QUERIES)
        # Base queries are not repeated; only the next-ranked unissued queries run.
        self.assertEqual(
            mb_client.queries,
            [q for q, _f, _s in BASE_QUERIES] + [q for q, _f, _s in EXTRA_QUERIES[:REPLENISH_EXTRA_QUERIES]],
        )

    def test_owned_albums_do_not_count_toward_eligible_supply(self):
        # Both CF albums are owned, so eligible supply is zero and the gate opens.
        artists = [("Alpha", "A1"), ("Beta", "B1")]
        library = [
            {"id": "lib-1", "name": "A1", "artist": "Alpha"},
            {"id": "lib-2", "name": "B1", "artist": "Beta"},
        ]
        responses = {q: [] for q, _f, _s in BASE_QUERIES + EXTRA_QUERIES}

        result, _ = self._run(cf_artists=artists, responses=responses, library=library, shortlist_target=1)

        summary = self._replenishment(result)
        self.assertEqual(summary["eligible_unowned_before"], 0)
        self.assertTrue(summary["triggered"])

    def test_same_title_under_another_artist_is_not_eligible_supply(self):
        # A title conflict is routed to review by the caller, so it is not shortlist supply.
        artists = [("Alpha", "Shared Title")]
        library = [{"id": "lib-1", "name": "Shared Title", "artist": "Someone Else"}]
        responses = {q: [] for q, _f, _s in BASE_QUERIES + EXTRA_QUERIES}

        result, _ = self._run(cf_artists=artists, responses=responses, library=library, shortlist_target=1)

        summary = self._replenishment(result)
        self.assertEqual(summary["eligible_unowned_before"], 0)
        self.assertTrue(summary["triggered"])

    def test_replenished_duplicate_of_existing_candidate_adds_nothing(self):
        artists = [("Alpha", "A1")]
        responses = {q: [] for q, _f, _s in BASE_QUERIES + EXTRA_QUERIES}
        responses["q-extra-1"] = [_group("Alpha", "A1")]

        result, _ = self._run(cf_artists=artists, responses=responses, shortlist_target=10)

        summary = self._replenishment(result)
        self.assertEqual(summary["extra_candidates_added"], 0)
        self.assertEqual(summary["eligible_unowned_after"], summary["eligible_unowned_before"])

    def test_replenished_candidates_respect_release_type_filtering(self):
        artists = [("Alpha", "A1")]
        responses = {q: [] for q, _f, _s in BASE_QUERIES + EXTRA_QUERIES}
        responses["q-extra-1"] = [
            _group("Beta", "Single Only", primary="Single"),
            _group("Gamma", "Live Set", secondary=["Live"]),
            _group("Delta", "Studio Album"),
        ]

        result, _ = self._run(cf_artists=artists, responses=responses, shortlist_target=10)

        summary = self._replenishment(result)
        self.assertEqual(summary["extra_candidates_added"], 1)
        self.assertEqual(summary["eligible_unowned_after"], summary["eligible_unowned_before"] + 1)

    def test_lane_unavailable_in_first_pass_blocks_replenishment(self):
        artists = [("Alpha", "A1")]
        responses = {q: [] for q, _f, _s in BASE_QUERIES + EXTRA_QUERIES}
        responses["q-base-1"] = 503

        result, mb_client = self._run(cf_artists=artists, responses=responses, shortlist_target=10)

        summary = self._replenishment(result)
        self.assertFalse(summary["triggered"])
        self.assertEqual(summary["extra_queries_attempted"], 0)
        self.assertNotIn("q-extra-1", mb_client.queries)

    def test_shortfall_replenishment_adds_eligible_supply_within_caps(self):
        # Synthetic shortfall: three CF albums, one owned, against a target of 10.
        # Eligible supply before is 2 (A1, G1). The two issued extra queries add
        # D1 and Z1; the duplicate, the single, and the third query's album do not.
        artists = [("Alpha", "A1"), ("Beta", "B1"), ("Gamma", "G1")]
        library = [{"id": "lib-1", "name": "B1", "artist": "Beta"}]
        responses = {q: [] for q, _f, _s in BASE_QUERIES + EXTRA_QUERIES}
        responses["q-extra-1"] = [
            _group("Delta", "D1"),
            _group("Alpha", "A1"),
            _group("Epsilon", "E1", primary="Single"),
        ]
        responses["q-extra-2"] = [_group("Zeta", "Z1"), _group("Delta", "D1")]
        responses["q-extra-3"] = [_group("Eta", "H1")]

        result, mb_client = self._run(
            cf_artists=artists, responses=responses, library=library, shortlist_target=10,
        )

        summary = self._replenishment(result)
        self.assertTrue(summary["triggered"])
        self.assertEqual(summary["eligible_unowned_before"], 2)
        self.assertEqual(summary["extra_queries_planned"], REPLENISH_EXTRA_QUERIES)
        self.assertEqual(summary["extra_queries_attempted"], REPLENISH_EXTRA_QUERIES)
        self.assertEqual(summary["extra_candidates_added"], 2)
        self.assertEqual(summary["eligible_unowned_after"], 4)
        self.assertEqual(
            mb_client.queries,
            [q for q, _f, _s in BASE_QUERIES] + [q for q, _f, _s in EXTRA_QUERIES[:REPLENISH_EXTRA_QUERIES]],
        )
        self.assertNotIn("q-extra-3", mb_client.queries)

        # Same synthetic inputs must give the same replenishment accounting.
        rerun, _ = self._run(
            cf_artists=artists, responses=responses, library=library, shortlist_target=10,
        )
        self.assertEqual(self._replenishment(rerun), summary)

    def test_tag_lane_counters_separate_empty_cache_from_no_listens(self):
        # No listens and no cached artist genres: every tag-lane counter is zero,
        # which is the cold-cache signature the aggregate diagnostics must show.
        artists = [("Alpha", "A1"), ("Beta", "B1")]
        responses = {q: [] for q, _f, _s in BASE_QUERIES + EXTRA_QUERIES}

        result, _mb_client = self._run(cf_artists=artists, responses=responses, shortlist_target=3)

        lane = result["candidate_supply"]["tag_lane"]
        self.assertEqual(lane["listens_total"], 0)
        self.assertEqual(lane["listens_with_artist_mbid"], 0)
        self.assertEqual(lane["profile_top_artist_cache_hits"], 0)
        self.assertEqual(lane["profile_tag_count"], 0)
        self.assertEqual(lane["candidate_artist_cache_hits"], 0)
        self.assertEqual(lane["candidate_pool_tag_count"], 0)
        self.assertGreaterEqual(lane["candidate_artists_considered"], 1)


class EligibleUnownedCountTests(unittest.TestCase):
    def test_count_is_unique_per_artist_and_title_and_excludes_owned(self):
        from discovery_candidate_gathering import count_eligible_unowned_albums

        albums = {
            ("alpha", "a1"): {"album": "A1", "primary_artist": "Alpha"},
            ("beta", "b1"): {"album": "B1", "primary_artist": "Beta"},
        }
        library_by_title = {"b1": [{"artist": "Beta"}]}

        self.assertEqual(count_eligible_unowned_albums(albums, library_by_title, _music_key), 1)


if __name__ == "__main__":
    unittest.main()
