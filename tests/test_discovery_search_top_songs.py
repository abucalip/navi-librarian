"""Artist-page ``top_songs`` section (docs/SEARCH_CONTRACT.md section 14.3)."""

import threading
import unittest

from discovery.search.artist_sections import ArtistNetwork
from discovery.search.index import build_owned_data
from discovery.search.providers import LastFmSearch, ListenBrainzRadio, ProviderError, SourceLimiter
from discovery.search.top_songs import TOP_SONGS_LIMIT, top_songs


class Store:
    def __init__(self):
        self.data = {}

    def read(self, key):
        return self.data.get(key)

    def write(self, key, payload):
        self.data[key] = payload


class FakeListenBrainz:
    def __init__(self, records=(), fail=False):
        self.records, self.fail, self.calls = list(records), fail, 0

    def top_recordings(self, mbid, *, remaining, cancelled):
        self.calls += 1
        if self.fail:
            raise ProviderError("failed")
        return list(self.records)


class FakeLastFm:
    def __init__(self, records=(), fail=False):
        self.records, self.fail, self.calls = list(records), fail, 0

    def top_tracks(self, name, *, remaining, cancelled):
        self.calls += 1
        if self.fail:
            raise ProviderError("failed")
        return list(self.records)


def song(name, count, album=None):
    return {"name": name, "listen_count": count, "recording_mbid": None, "album": album}


def make_network(listenbrainz=None, lastfm=None, store=None):
    store = store or Store()
    return ArtistNetwork(
        musicbrainz=None, popularity=lambda mbids, can_cache: {}, bio=lambda name: None,
        cache_read=store.read, cache_write=store.write, listenbrainz=listenbrainz, lastfm=lastfm,
    )


def owned():
    return build_owned_data(
        generation=1, built_at=0,
        artists=[{"id": "ar1", "name": "Radiohead", "album_count": 1}],
        albums=[{"id": "al1", "artist": "Radiohead", "artist_id": "ar1", "album": "OK Computer", "year": 1997, "song_count": 2}],
        songs=[
            {"id": "s1", "title": "Karma Police", "artist": "Radiohead", "artistId": "ar1", "album": "OK Computer", "albumId": "al1"},
            {"id": "s2", "title": "Karma Police", "artist": "Someone Else", "artistId": "ar2", "album": "X", "albumId": "al2"},
        ],
    )


def run(network, data=None, artist_id="ar1", mbid="mb-rh"):
    return top_songs(network, "Radiohead", artist_id, data, mbid=mbid, remaining=lambda: 5.0, cancelled=threading.Event())


class TopSongsTests(unittest.TestCase):
    def test_listenbrainz_items_are_ranked_and_owned_by_title_for_this_artist(self):
        lb = FakeListenBrainz([song("Karma Police", 300, "OK Computer"), song("Creep", 200)])
        section = run(make_network(listenbrainz=lb), owned())
        self.assertTrue(section["available"] and section["complete"])
        self.assertEqual([i["rank"] for i in section["items"]], [1, 2])
        self.assertEqual([i["source"] for i in section["items"]], ["listenbrainz", "listenbrainz"])
        self.assertEqual([i["owned"] for i in section["items"]], [True, False])
        self.assertEqual(section["items"][0]["album"], "OK Computer")
        self.assertEqual(set(section["items"][0]), {"rank", "name", "listen_count", "source", "recording_mbid", "owned", "album"})

    def test_another_artists_song_with_the_same_title_is_not_owned(self):
        section = run(make_network(listenbrainz=FakeListenBrainz([song("Karma Police", 1)])), owned(), artist_id="ar3")
        self.assertFalse(section["items"][0]["owned"])
        self.assertIs(run(make_network(listenbrainz=FakeListenBrainz([song("Karma Police", 1)])), owned(), artist_id=None)["items"][0]["owned"], False)

    def test_versions_with_one_title_collapse_and_the_list_is_capped(self):
        records = [song("Creep", 9), song("creep!", 8)] + [song(f"Song {n}", 5) for n in range(20)]
        items = run(make_network(listenbrainz=FakeListenBrainz(records)))["items"]
        self.assertEqual(len(items), TOP_SONGS_LIMIT)
        self.assertEqual([i["name"] for i in items].count("Creep"), 1)
        self.assertEqual(items[0]["listen_count"], 9)

    def test_lastfm_answers_when_listenbrainz_is_empty_or_has_no_mbid_and_scales_never_mix(self):
        lb, lf = FakeListenBrainz([]), FakeLastFm([song("Creep", 70)])
        section = run(make_network(listenbrainz=lb, lastfm=lf))
        self.assertEqual([i["source"] for i in section["items"]], ["lastfm"])
        no_mbid = run(make_network(listenbrainz=FakeListenBrainz([song("A", 1)]), lastfm=FakeLastFm([song("B", 2)])), mbid=None)
        self.assertEqual([(i["name"], i["source"]) for i in no_mbid["items"]], [("B", "lastfm")])

    def test_listenbrainz_failure_falls_back_and_total_failure_raises(self):
        section = run(make_network(listenbrainz=FakeListenBrainz(fail=True), lastfm=FakeLastFm([song("Creep", 1)])))
        self.assertEqual(section["items"][0]["source"], "lastfm")
        with self.assertRaises(ProviderError):
            run(make_network(listenbrainz=FakeListenBrainz(fail=True), lastfm=FakeLastFm(fail=True)))
        with self.assertRaises(ProviderError):
            run(make_network(listenbrainz=FakeListenBrainz(fail=True)))

    def test_both_sources_empty_is_a_valid_empty_result(self):
        section = run(make_network(listenbrainz=FakeListenBrainz([]), lastfm=FakeLastFm([])))
        self.assertEqual((section["available"], section["complete"], section["items"]), (True, True, []))

    def test_no_usable_source_reports_source_disabled(self):
        section = run(make_network(listenbrainz=FakeListenBrainz([song("A", 1)])), mbid=None)
        self.assertEqual((section["available"], section["reason"]), (False, "source_disabled"))

    def test_second_read_comes_from_the_cache_and_owned_is_recomputed(self):
        store, lb = Store(), FakeListenBrainz([song("Karma Police", 3)])
        network = make_network(listenbrainz=lb, store=store)
        first = run(network, None)
        second = run(network, owned())
        self.assertEqual(lb.calls, 1)
        self.assertFalse(first["items"][0]["owned"])
        self.assertTrue(second["items"][0]["owned"])


class Response:
    def __init__(self, body):
        self.body, self.status_code = body, 200

    def raise_for_status(self):
        pass

    def json(self):
        return self.body


class ProviderParsingTests(unittest.TestCase):
    def test_listenbrainz_top_recordings_parse(self):
        seen = {}

        def get(url, **kwargs):
            seen["url"] = url
            return Response([
                {"recording_name": "Karma Police", "total_listen_count": 5, "recording_mbid": "r1", "release_name": "OK Computer"},
                {"recording_name": "", "total_listen_count": 4},
                "junk",
                {"recording_name": "No Count"},
            ])

        radio = ListenBrainzRadio(get=get, limiter=SourceLimiter({"listenbrainz": 100.0}), headers={})
        items = radio.top_recordings("mb-rh", remaining=lambda: 5.0, cancelled=threading.Event())
        self.assertTrue(seen["url"].endswith("/top-recordings-for-artist/mb-rh"))
        self.assertEqual([i["name"] for i in items], ["Karma Police", "No Count"])
        self.assertEqual(items[0], {"name": "Karma Police", "listen_count": 5, "recording_mbid": "r1", "album": "OK Computer"})
        self.assertIsNone(items[1]["listen_count"])

    def test_lastfm_top_tracks_parse(self):
        get = lambda url, **kwargs: Response({"toptracks": {"track": [
            {"name": "Creep", "playcount": "12", "mbid": ""}, {"name": ""}, {"name": "Lucky", "playcount": "x"}]}})
        client = LastFmSearch(get=get, limiter=SourceLimiter({"lastfm": 100.0}), api_key="k")
        items = client.top_tracks("Radiohead", remaining=lambda: 5.0, cancelled=threading.Event())
        self.assertEqual([(i["name"], i["listen_count"]) for i in items], [("Creep", 12), ("Lucky", None)])


if __name__ == "__main__":
    unittest.main()
