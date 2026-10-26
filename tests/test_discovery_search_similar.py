"""Similar artists: fusion, ListenBrainz radio and Last.fm parsing, and the section (contract section 7)."""

import threading
import unittest

from discovery.search.artist_sections import ArtistNetwork, network_sections, similar_items
from discovery.search.cache import SIMILAR_TTL_SECONDS
from discovery.search.index import build_owned_data
from discovery.search.limiter import SourceLimiter
from discovery.search.merge import OwnedKeys
from discovery.search.providers import LastFmSearch, ListenBrainzRadio, ProviderError, artist_candidate
from discovery.search.similar import SIMILAR_LIMIT, fuse_similar


class Response:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class Store:
    def __init__(self):
        self.data = {}

    def read(self, key):
        return self.data.get(key)

    def write(self, key, payload):
        self.data[key] = payload


def never_cancelled():
    return threading.Event()


def owned_keys():
    data = build_owned_data(
        generation=1, built_at=0,
        artists=[
            {"id": "ar1", "name": "Radiohead", "album_count": 0},
            {"id": "ar2", "name": "Portishead", "album_count": 0},
        ],
        albums=[],
        songs=[],
    )
    return OwnedKeys(data)


def artist(name, mbid=None):
    return artist_candidate("test", name, mbid)


class FuseTests(unittest.TestCase):
    def test_last_fm_scores_and_listenbrainz_position_add_up_per_artist(self):
        records = [
            {"source": "lastfm", "name": "Thom Yorke", "mbid": None, "match": 0.95},
            {"source": "listenbrainz", "name": "Atoms for Peace", "mbid": "mb-afp", "match": None},
            {"source": "lastfm", "name": "Atoms for Peace", "mbid": "mb-afp", "match": 0.4},
        ]
        items = fuse_similar(records, "Radiohead", "mb-rh", OwnedKeys(None))
        self.assertEqual([i["name"] for i in items], ["Thom Yorke", "Atoms for Peace"])
        self.assertEqual(items[0]["score"], 0.95)
        self.assertEqual(items[1]["score"], 0.9)  # 1/2 from radio position one, plus 0.4 match.
        self.assertCountEqual(items[1]["reasons"], ["Last.fm similar artist", "ListenBrainz similar artist"])
        self.assertEqual(items[0]["reasons"], ["Last.fm similar artist"])

    def test_listenbrainz_only_ranks_by_position(self):
        records = [
            {"source": "listenbrainz", "name": "First", "mbid": "mb-1", "match": None},
            {"source": "listenbrainz", "name": "Second", "mbid": "mb-2", "match": None},
        ]
        items = fuse_similar(records, "Seed", None, OwnedKeys(None))
        self.assertEqual([i["name"] for i in items], ["First", "Second"])
        self.assertEqual([i["score"] for i in items], [0.5, 0.333])

    def test_the_seed_is_never_suggested(self):
        records = [
            {"source": "lastfm", "name": "Radiohead", "mbid": "mb-rh", "match": 1.0},
            {"source": "listenbrainz", "name": "Radiohead", "mbid": None, "match": None},
            {"source": "listenbrainz", "name": "Other", "mbid": "mb-o", "match": None},
        ]
        items = fuse_similar(records, "Radiohead", "mb-rh", OwnedKeys(None))
        self.assertEqual([i["name"] for i in items], ["Other"])

    def test_owned_artists_move_to_the_owned_list_after_the_unowned_ones(self):
        records = [
            {"source": "listenbrainz", "name": "Portishead", "mbid": None, "match": None},
            {"source": "listenbrainz", "name": "Massive Attack", "mbid": "mb-ma", "match": None},
            {"source": "lastfm", "name": "Thom Yorke", "mbid": None, "match": 0.2},
        ]
        items = fuse_similar(records, "Radiohead", "mb-rh", owned_keys())
        self.assertEqual([i["name"] for i in items], ["Massive Attack", "Thom Yorke", "Portishead"])
        self.assertEqual([i["owned"] for i in items], [False, False, True])

    def test_item_shape_carries_owned_and_the_library_id(self):
        records = [
            {"source": "listenbrainz", "name": "Portishead", "mbid": None, "match": None},
            {"source": "listenbrainz", "name": "Massive Attack", "mbid": "mb-ma", "match": None},
        ]
        items = fuse_similar(records, "Radiohead", "mb-rh", owned_keys())
        self.assertEqual(items[0], {
            "name": "Massive Attack", "mbid": "mb-ma", "owned": False, "id": None,
            "score": 0.333, "reasons": ["ListenBrainz similar artist"],
        })
        self.assertEqual(items[1]["owned"], True)
        self.assertEqual(items[1]["id"], "ar2")
        self.assertEqual(items[1]["name"], "Portishead")

    def test_an_owned_artist_matched_by_mbid_keeps_its_library_id(self):
        data = build_owned_data(
            generation=1, built_at=0,
            artists=[{"id": "ar9", "name": "Portishead", "album_count": 0, "mbid": "mb-p"}],
            albums=[], songs=[],
        )
        records = [{"source": "lastfm", "name": "Portishead", "mbid": "mb-p", "match": 0.7}]
        items = fuse_similar(records, "Radiohead", "mb-rh", OwnedKeys(data))
        self.assertEqual((items[0]["owned"], items[0]["id"]), (True, "ar9"))

    def test_suggestions_are_capped(self):
        records = [
            {"source": "listenbrainz", "name": f"Artist {n:02d}", "mbid": f"mb-{n}", "match": None}
            for n in range(SIMILAR_LIMIT + 5)
        ]
        self.assertEqual(len(fuse_similar(records, "Seed", None, OwnedKeys(None))), SIMILAR_LIMIT)


class ListenBrainzRadioTests(unittest.TestCase):
    def radio(self, get, limiter=None):
        return ListenBrainzRadio(
            get=get,
            limiter=limiter or SourceLimiter({"listenbrainz": 0.0}),
            headers={"User-Agent": "test"},
        )

    def test_flattens_in_order_removes_the_seed_and_duplicates(self):
        payload = {
            "mb-rh": [
                {"similar_artist_mbid": "mb-rh", "similar_artist_name": "Radiohead"},
                {"similar_artist_mbid": "mb-a", "similar_artist_name": "A"},
            ],
            "mb-a": [
                {"similar_artist_mbid": "mb-b", "similar_artist_name": "B"},
                {"similar_artist_mbid": "mb-a", "similar_artist_name": "A"},
            ],
        }
        calls = []

        def get(url, **kwargs):
            calls.append((url, kwargs))
            return Response(payload)

        result = self.radio(get).similar("mb-rh", remaining=lambda: 10.0, cancelled=never_cancelled())
        self.assertEqual([r["name"] for r in result], ["A", "B"])
        self.assertTrue(all(r["match"] is None for r in result))
        url, kwargs = calls[0]
        self.assertEqual(url, "https://api.listenbrainz.org/1/lb-radio/artist/mb-rh")
        self.assertEqual(kwargs["params"]["max_similar_artists"], 5)

    def test_the_seed_mbid_is_escaped_in_the_path(self):
        calls = []

        def get(url, **kwargs):
            calls.append(url)
            return Response({})

        self.radio(get).similar("a/../b", remaining=lambda: 10.0, cancelled=never_cancelled())
        self.assertEqual(calls, ["https://api.listenbrainz.org/1/lb-radio/artist/a%2F..%2Fb"])

    def test_a_body_that_is_not_an_object_is_a_failure(self):
        radio = self.radio(lambda url, **kwargs: Response([]))
        with self.assertRaises(ProviderError):
            radio.similar("mb-rh", remaining=lambda: 10.0, cancelled=never_cancelled())

    def test_http_errors_propagate_as_failures(self):
        radio = self.radio(lambda url, **kwargs: Response({}, status=429))
        with self.assertRaises(RuntimeError):
            radio.similar("mb-rh", remaining=lambda: 10.0, cancelled=never_cancelled())

    def test_a_call_that_would_wait_past_the_deadline_is_rate_limited(self):
        clock = [0.0]
        limiter = SourceLimiter({"listenbrainz": 2.0}, clock=lambda: clock[0], sleep=lambda s: None)
        radio = self.radio(lambda url, **kwargs: Response({}), limiter=limiter)
        radio.similar("mb-1", remaining=lambda: 10.0, cancelled=never_cancelled())
        with self.assertRaises(ProviderError) as raised:
            radio.similar("mb-2", remaining=lambda: 0.5, cancelled=never_cancelled())
        self.assertEqual(str(raised.exception), "rate_limited")


class LastFmSimilarTests(unittest.TestCase):
    def test_parses_names_mbids_and_clamped_match_scores(self):
        payload = {"similarartists": {"artist": [
            {"name": "Thom Yorke", "mbid": "", "match": "0.9"},
            {"name": "Nameless", "match": "not a number"},
            {"name": "", "match": "1"},
            {"name": "Overshoot", "mbid": "mb-o", "match": "1.7"},
        ]}}
        lastfm = LastFmSearch(
            get=lambda url, **kwargs: Response(payload),
            limiter=SourceLimiter({}),
            api_key="key",
        )
        result = lastfm.similar("Radiohead", remaining=lambda: 10.0, cancelled=never_cancelled())
        self.assertEqual(result, [
            {"name": "Thom Yorke", "mbid": None, "match": 0.9},
            {"name": "Nameless", "mbid": None, "match": 0.0},
            {"name": "Overshoot", "mbid": "mb-o", "match": 1.0},
        ])


class SimilarSectionTests(unittest.TestCase):
    class MusicBrainz:
        def __init__(self, mbid="mb-rh"):
            self._mbid = mbid

        def artists(self, query, *, remaining, cancelled):
            return [artist_candidate("musicbrainz", "Radiohead", self._mbid)] if self._mbid else []

        def albums_by_artist(self, mbid, *, remaining, cancelled):
            return []

    class Fake:
        def __init__(self, records=(), fail=False):
            self._records = list(records)
            self._fail = fail
            self.calls = 0

        def similar(self, seed, *, remaining, cancelled):
            self.calls += 1
            if self._fail:
                raise ProviderError("failed")
            return [dict(r) for r in self._records]

    def network(self, lastfm=None, listenbrainz=None, store=None, mbid="mb-rh"):
        store = store or Store()
        return ArtistNetwork(
            musicbrainz=self.MusicBrainz(mbid),
            popularity=lambda mbids, can_cache: {},
            bio=lambda name: None,
            cache_read=store.read,
            cache_write=store.write,
            lastfm=lastfm,
            listenbrainz=listenbrainz,
            lastfm_generation=3,
            deadline_seconds=3.0,
        )

    def run_similar(self, net):
        return similar_items(
            net, "Radiohead", None, owned_keys(),
            remaining=lambda: 10.0, cancelled=never_cancelled(),
        )

    def test_both_sources_fuse_into_a_complete_section(self):
        net = self.network(
            lastfm=self.Fake([{"name": "Thom Yorke", "mbid": None, "match": 0.9}]),
            listenbrainz=self.Fake([{"name": "Atoms for Peace", "mbid": "mb-afp", "match": None}]),
        )
        section = self.run_similar(net)
        self.assertEqual(section["section"], "similar")
        self.assertTrue(section["available"])
        self.assertTrue(section["complete"])
        self.assertEqual([i["name"] for i in section["items"]], ["Thom Yorke", "Atoms for Peace"])

    def test_a_failed_source_gives_a_partial_section_that_is_not_cached(self):
        store = Store()
        net = self.network(
            lastfm=self.Fake(fail=True),
            listenbrainz=self.Fake([{"name": "Atoms for Peace", "mbid": "mb-afp", "match": None}]),
            store=store,
        )
        section = self.run_similar(net)
        self.assertFalse(section["complete"])
        self.assertEqual(section["reason"], "source_failed")
        self.assertEqual([i["name"] for i in section["items"]], ["Atoms for Peace"])
        self.assertFalse(any(key.startswith("similar:") for key in store.data))

    def test_a_complete_answer_is_served_from_cache_without_provider_calls(self):
        store = Store()
        lastfm = self.Fake([{"name": "Thom Yorke", "mbid": None, "match": 0.9}])
        first = self.run_similar(self.network(lastfm=lastfm, store=store))
        self.assertEqual(lastfm.calls, 1)

        again = self.Fake(fail=True)
        second = self.run_similar(self.network(lastfm=again, store=store))
        self.assertEqual(again.calls, 0)
        self.assertEqual(second["items"], first["items"])
        self.assertIn("similar:mb-rh:radiohead:lastfm3:listenbrainz0", store.data)

    def test_cache_entries_for_similar_artists_last_seven_days(self):
        store = Store()
        self.run_similar(self.network(lastfm=self.Fake([{"name": "Thom Yorke", "mbid": None, "match": 0.9}]), store=store))
        entry = store.data["similar:mb-rh:radiohead:lastfm3:listenbrainz0"]
        self.assertEqual(len(entry["results"]), 1)
        self.assertEqual(SIMILAR_TTL_SECONDS, 7 * 24 * 60 * 60)

    def test_every_source_failing_is_a_source_failed_section_on_the_page(self):
        net = self.network(lastfm=self.Fake(fail=True), listenbrainz=self.Fake(fail=True))
        sections = network_sections(net, "Radiohead", None, None)
        self.assertEqual(sections["similar"]["reason"], "source_failed")
        self.assertEqual(sections["similar"]["items"], [])

    def test_no_source_able_to_answer_is_source_disabled(self):
        net = self.network(lastfm=None, listenbrainz=None)
        section = self.run_similar(net)
        self.assertFalse(section["available"])
        self.assertEqual(section["reason"], "source_disabled")

    def test_without_an_mbid_only_last_fm_answers(self):
        radio = self.Fake([{"name": "Should not be asked", "mbid": "mb-x", "match": None}])
        net = self.network(
            lastfm=self.Fake([{"name": "Thom Yorke", "mbid": None, "match": 0.9}]),
            listenbrainz=radio,
            mbid=None,
        )
        section = self.run_similar(net)
        self.assertEqual(radio.calls, 0)
        self.assertEqual([i["name"] for i in section["items"]], ["Thom Yorke"])
        self.assertTrue(section["complete"])


if __name__ == "__main__":
    unittest.main()
