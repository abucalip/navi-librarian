"""Artist-page network sections: bio and missing albums (contract sections 3.3 and 3.8)."""

import time
import unittest

from discovery.search.artist_page import artist_page
from discovery.search.artist_sections import ArtistNetwork, missing_albums, network_sections, resolve_identity
from discovery.search.index import IndexView, STATE_FRESH, build_owned_data
from discovery.search.merge import OwnedKeys
from discovery.search.providers import ProviderError, album_candidate, artist_candidate


class Store:
    def __init__(self):
        self.data = {}

    def read(self, key):
        return self.data.get(key)

    def write(self, key, payload):
        self.data[key] = payload


class FakeMusicBrainz:
    def __init__(self, artists=(), albums=(), fail=None):
        self._artists = list(artists)
        self._albums = list(albums)
        self._fail = fail

    def artists(self, query, *, remaining, cancelled):
        if self._fail:
            raise ProviderError(self._fail)
        return self._artists

    def albums_by_artist(self, mbid, *, remaining, cancelled):
        if self._fail:
            raise ProviderError(self._fail)
        return self._albums


def network(musicbrainz=None, popularity=None, bio=None, store=None, deadline=3.0):
    store = store or Store()
    return ArtistNetwork(
        musicbrainz=musicbrainz or FakeMusicBrainz(),
        popularity=popularity or (lambda mbids, can_cache: {}),
        bio=bio or (lambda name: None),
        cache_read=store.read,
        cache_write=store.write,
        deadline_seconds=deadline,
    )


def radiohead_owned():
    return build_owned_data(
        generation=1, built_at=0,
        artists=[{"id": "ar1", "name": "Radiohead", "album_count": 1}],
        albums=[{"id": "al1", "artist": "Radiohead", "artist_id": "ar1",
                 "album": "OK Computer", "year": 1997, "song_count": 12}],
        songs=[],
    )


RADIOHEAD = [artist_candidate("musicbrainz", "Radiohead", "mb-rh")]
ALBUMS = [
    album_candidate("musicbrainz", "OK Computer", "Radiohead", 1997, "rg-owned"),
    album_candidate("musicbrainz", "Pablo Honey", "Radiohead", 1993, "rg-2"),
    album_candidate("musicbrainz", "The Bends", "Radiohead", 1995, "rg-3"),
    album_candidate("musicbrainz", "Pablo Honey", "Radiohead", 1993, "rg-dup"),
]


def never_cancelled():
    import threading
    return threading.Event()


class MissingAlbumsTests(unittest.TestCase):
    def run_missing(self, net, owned=None):
        return missing_albums(
            net, "Radiohead", None, OwnedKeys(owned or radiohead_owned()),
            remaining=lambda: 10.0, cancelled=never_cancelled(),
        )

    def test_identity_is_the_exact_name_match(self):
        net = network(FakeMusicBrainz(artists=[
            artist_candidate("musicbrainz", "Radiohead Tribute", "mb-x"),
            artist_candidate("musicbrainz", "Radiohead", "mb-rh"),
        ]))
        mbid = resolve_identity(net, "Radiohead", None, remaining=lambda: 10.0, cancelled=never_cancelled())
        self.assertEqual(mbid, "mb-rh")

    def test_no_identity_is_a_valid_empty_list(self):
        net = network(FakeMusicBrainz(artists=[artist_candidate("musicbrainz", "Someone Else", "mb-9")]))
        self.assertEqual(self.run_missing(net), [])

    def test_owned_and_duplicate_albums_are_removed_and_the_rest_ordered_by_listens(self):
        net = network(
            FakeMusicBrainz(artists=RADIOHEAD, albums=ALBUMS),
            popularity=lambda mbids, can_cache: {"rg-3": {"playcount": 900, "listeners": 50},
                                      "rg-2": {"playcount": 100, "listeners": 80}},
        )
        items = self.run_missing(net)
        self.assertEqual([i["name"] for i in items], ["The Bends", "Pablo Honey"])
        self.assertEqual(items[0]["popularity"], 900)
        self.assertEqual(items[0]["sources"], ["musicbrainz", "listenbrainz"])
        self.assertNotIn("OK Computer", [i["name"] for i in items])

    def test_ordering_is_by_listen_count_not_by_listener_count(self):
        # rg-2 has more users (listeners) but fewer listens (playcount); the listen count decides.
        net = network(
            FakeMusicBrainz(artists=RADIOHEAD, albums=ALBUMS),
            popularity=lambda mbids, can_cache: {"rg-2": {"playcount": 100, "listeners": 500},
                                      "rg-3": {"playcount": 900, "listeners": 40}},
        )
        items = self.run_missing(net)
        self.assertEqual([i["name"] for i in items], ["The Bends", "Pablo Honey"])
        self.assertEqual(items[0]["popularity"], 900)
        self.assertEqual(items[1]["popularity"], 100)

    def test_listenbrainz_failure_keeps_the_albums_without_popularity(self):
        def broken(mbids, can_cache):
            raise RuntimeError("listenbrainz down")

        net = network(FakeMusicBrainz(artists=RADIOHEAD, albums=ALBUMS), popularity=broken)
        items = self.run_missing(net)
        self.assertEqual(len(items), 2)
        self.assertTrue(all(i["popularity"] is None for i in items))
        self.assertTrue(all(i["sources"] == ["musicbrainz"] for i in items))

    def test_list_is_capped_at_fifty(self):
        many = [album_candidate("musicbrainz", f"Album {i}", "Radiohead", 2000, f"rg-{i}") for i in range(80)]
        net = network(FakeMusicBrainz(artists=RADIOHEAD, albums=many))
        self.assertEqual(len(self.run_missing(net)), 50)


class NetworkSectionTests(unittest.TestCase):
    def test_both_sections_complete_when_sources_answer(self):
        net = network(
            FakeMusicBrainz(artists=RADIOHEAD, albums=ALBUMS),
            bio=lambda name: "English rock band.",
        )
        sections = network_sections(net, "Radiohead", None, radiohead_owned())
        self.assertEqual(sections["bio"]["bio"], {"text": "English rock band.", "source": "wikidata"})
        self.assertTrue(sections["bio"]["complete"])
        self.assertTrue(sections["missing_albums"]["complete"])
        self.assertEqual(len(sections["missing_albums"]["items"]), 2)

    def test_empty_bio_is_a_valid_empty_result(self):
        sections = network_sections(network(), "Radiohead", None, radiohead_owned())
        self.assertEqual(sections["bio"], {"section": "bio", "available": True, "complete": True,
                                           "reason": None, "bio": None})

    def test_musicbrainz_failure_is_source_failed_and_bio_still_answers(self):
        net = network(FakeMusicBrainz(fail="failed"), bio=lambda name: "Bio.")
        sections = network_sections(net, "Radiohead", None, radiohead_owned())
        self.assertEqual(sections["missing_albums"]["reason"], "source_failed")
        self.assertFalse(sections["missing_albums"]["available"])
        self.assertEqual(sections["missing_albums"]["items"], [])
        self.assertTrue(sections["bio"]["complete"])

    def test_bio_failure_is_source_failed(self):
        def broken(name):
            raise RuntimeError("wikidata down")

        sections = network_sections(network(bio=broken), "Radiohead", None, radiohead_owned())
        self.assertEqual(sections["bio"]["reason"], "source_failed")
        self.assertEqual(sections["bio"]["bio"], None)

    def test_missing_albums_that_runs_out_of_time_keeps_the_albums_it_has(self):
        def slow_popularity(mbids, can_cache):
            time.sleep(1.0)
            return {}

        net = network(FakeMusicBrainz(artists=RADIOHEAD, albums=ALBUMS), popularity=slow_popularity, deadline=0.3)
        sections = network_sections(net, "Radiohead", None, radiohead_owned())
        missing = sections["missing_albums"]
        self.assertTrue(missing["available"])
        self.assertFalse(missing["complete"])
        self.assertEqual(missing["reason"], "deadline")
        # Without popularity the list falls back to year order.
        self.assertEqual([i["name"] for i in missing["items"]], ["Pablo Honey", "The Bends"])
        self.assertTrue(all(i["popularity"] is None for i in missing["items"]))

    def test_a_section_that_misses_the_deadline_is_reported_deadline(self):
        def slow(name):
            time.sleep(1.0)
            return "late"

        started = time.monotonic()
        sections = network_sections(network(bio=slow, deadline=0.2), "Radiohead", None, radiohead_owned())
        self.assertLess(time.monotonic() - started, 0.9)
        self.assertEqual(sections["bio"]["reason"], "deadline")
        self.assertFalse(sections["bio"]["complete"])
        self.assertTrue(sections["missing_albums"]["complete"])


class PopularityDeadlineTests(unittest.TestCase):
    def test_popularity_response_after_the_deadline_is_not_cached(self):
        cached = {}

        def slow_popularity(mbids, can_cache):
            time.sleep(0.5)
            if can_cache():
                cached["rg-3"] = {"playcount": 900, "listeners": 50}
            return {"rg-3": {"playcount": 900, "listeners": 50}}

        net = network(FakeMusicBrainz(artists=RADIOHEAD, albums=ALBUMS), popularity=slow_popularity, deadline=0.2)
        sections = network_sections(net, "Radiohead", None, radiohead_owned())
        self.assertEqual(sections["missing_albums"]["reason"], "deadline")
        self.assertEqual(cached, {})

    def test_popularity_response_in_time_is_cached(self):
        cached = {}
        checks = []

        def quick_popularity(mbids, can_cache):
            checks.append(can_cache())
            if checks[-1]:
                cached["rg-3"] = {"playcount": 900, "listeners": 50}
            return cached

        net = network(FakeMusicBrainz(artists=RADIOHEAD, albums=ALBUMS), popularity=quick_popularity)
        network_sections(net, "Radiohead", None, radiohead_owned())
        self.assertEqual(checks, [True])
        self.assertIn("rg-3", cached)


class LateResultTests(unittest.TestCase):
    def test_identity_answer_that_arrives_after_the_deadline_is_not_cached(self):
        store = Store()
        net = network(FakeMusicBrainz(artists=RADIOHEAD), store=store)
        resolve_identity(net, "Radiohead", None, remaining=lambda: 0.0, cancelled=never_cancelled())
        self.assertEqual(store.data, {})


class FakeLastFm:
    def __init__(self, albums=(), fail=False):
        self._albums = list(albums)
        self._fail = fail

    def top_albums(self, name, *, remaining, cancelled):
        if self._fail:
            raise ProviderError("failed")
        return self._albums


class NavidromeIdentityTests(unittest.TestCase):
    def test_navidrome_tag_is_used_without_a_musicbrainz_name_search(self):
        class MustNotSearch(FakeMusicBrainz):
            def artists(self, query, *, remaining, cancelled):
                raise AssertionError("name search should not run when the library tags the MBID")

        net = network(MustNotSearch(albums=ALBUMS))
        net.navidrome_mbid = lambda artist_id: "mb-tagged"
        mbid = resolve_identity(net, "Radiohead", "ar1", remaining=lambda: 10.0, cancelled=never_cancelled())
        self.assertEqual(mbid, "mb-tagged")

    def test_failed_tag_read_falls_back_to_the_name_lookup(self):
        net = network(FakeMusicBrainz(artists=RADIOHEAD))

        def broken(artist_id):
            raise RuntimeError("navidrome down")

        net.navidrome_mbid = broken
        self.assertEqual(
            resolve_identity(net, "Radiohead", "ar1", remaining=lambda: 10.0, cancelled=never_cancelled()),
            "mb-rh",
        )


class LastFmAlbumsTests(unittest.TestCase):
    def run_missing(self, net):
        return missing_albums(net, "Radiohead", None, OwnedKeys(radiohead_owned()),
                              remaining=lambda: 10.0, cancelled=never_cancelled())

    def test_lastfm_album_matching_a_musicbrainz_album_is_one_item_with_both_sources(self):
        lastfm = [album_candidate("lastfm", "The Bends", "Radiohead", None, None)]
        net = network(FakeMusicBrainz(artists=RADIOHEAD, albums=ALBUMS))
        net.lastfm = FakeLastFm(albums=lastfm)
        items = {i["name"]: i for i in self.run_missing(net)}
        self.assertEqual(sorted(items), ["Pablo Honey", "The Bends"])
        self.assertEqual(items["The Bends"]["sources"], ["musicbrainz", "lastfm"])

    def test_lastfm_only_album_is_listed_with_lastfm_as_its_source(self):
        lastfm = [album_candidate("lastfm", "Hail to the Thief", "Radiohead", None, None)]
        net = network(FakeMusicBrainz(artists=[], albums=[]))
        net.lastfm = FakeLastFm(albums=lastfm)
        [item] = self.run_missing(net)
        self.assertEqual(item["name"], "Hail to the Thief")
        self.assertEqual(item["sources"], ["lastfm"])

    def test_lastfm_album_the_library_owns_is_removed(self):
        lastfm = [album_candidate("lastfm", "OK Computer", "Radiohead", None, None)]
        net = network(FakeMusicBrainz(artists=RADIOHEAD, albums=[]))
        net.lastfm = FakeLastFm(albums=lastfm)
        self.assertEqual(self.run_missing(net), [])

    def test_lastfm_failure_is_ignored_and_the_musicbrainz_list_still_answers(self):
        net = network(FakeMusicBrainz(artists=RADIOHEAD, albums=ALBUMS))
        net.lastfm = FakeLastFm(fail=True)
        sections = network_sections(net, "Radiohead", None, radiohead_owned())
        self.assertTrue(sections["missing_albums"]["complete"])
        self.assertEqual(len(sections["missing_albums"]["items"]), 2)

    def test_lastfm_alone_answers_when_the_artist_has_no_musicbrainz_identity(self):
        lastfm = [album_candidate("lastfm", "Hail to the Thief", "Radiohead", None, None)]
        net = network(FakeMusicBrainz(artists=[]))
        net.lastfm = FakeLastFm(albums=lastfm)
        self.assertEqual([i["name"] for i in self.run_missing(net)], ["Hail to the Thief"])


class ArtistPageNetworkTests(unittest.TestCase):
    def view(self):
        return IndexView(STATE_FRESH, radiohead_owned(), None)

    def test_page_with_network_reports_sections_available_and_complete(self):
        net = network(FakeMusicBrainz(artists=RADIOHEAD, albums=ALBUMS), bio=lambda name: "Bio.")
        page = artist_page(self.view(), "radiohead", None, network=net)
        self.assertTrue(page.capabilities["sections"]["bio"]["available"])
        self.assertTrue(page.capabilities["sections"]["missing_albums"]["available"])
        self.assertEqual(page.sections["missing_albums"]["section"], "missing_albums")
        self.assertFalse(page.partial)
        # This network has neither Last.fm nor ListenBrainz wired, so no source can answer.
        self.assertEqual(page.capabilities["sections"]["similar"]["reason"], "source_disabled")
        self.assertEqual(page.sections["similar"]["reason"], "source_disabled")

    def test_a_failed_source_makes_the_page_partial(self):
        net = network(FakeMusicBrainz(fail="failed"), bio=lambda name: "Bio.")
        page = artist_page(self.view(), "radiohead", None, network=net)
        self.assertTrue(page.partial)

    def test_without_network_sections_stay_not_in_this_build(self):
        page = artist_page(self.view(), "radiohead", None, network=None)
        self.assertEqual(page.sections["bio"]["reason"], "not_in_this_build")
        self.assertFalse(page.partial)

    def test_network_sections_are_unavailable_with_the_index_reason_while_the_index_builds(self):
        building = IndexView("building", None, "index_building")
        page = artist_page(building, "radiohead", None, network=network())
        self.assertEqual(page.sections["bio"]["reason"], "index_building")
        self.assertTrue(page.partial)


class NavidromeBioTests(unittest.TestCase):
    def test_owned_artist_uses_the_navidrome_bio_before_wikidata(self):
        net = network(bio=lambda name: "Wikidata text.")
        net.navidrome_bio = lambda artist_id: "Navidrome text."
        sections = network_sections(net, "Radiohead", "ar-1", radiohead_owned())
        self.assertEqual(sections["bio"]["bio"], {"text": "Navidrome text.", "source": "navidrome"})

    def test_empty_or_failed_navidrome_bio_falls_back_to_wikidata(self):
        for reader in (lambda artist_id: None, lambda artist_id: 1 / 0):
            net = network(bio=lambda name: "Wikidata text.")
            net.navidrome_bio = reader
            sections = network_sections(net, "Radiohead", "ar-1", radiohead_owned())
            self.assertEqual(sections["bio"]["bio"], {"text": "Wikidata text.", "source": "wikidata"})

    def test_unowned_artist_never_asks_navidrome(self):
        net = network(bio=lambda name: "Wikidata text.")
        net.navidrome_bio = lambda artist_id: self.fail("Navidrome must not be asked")
        sections = network_sections(net, "Radiohead", None, radiohead_owned())
        self.assertEqual(sections["bio"]["bio"]["source"], "wikidata")

    def test_unowned_artist_bio_prefers_lastfm_over_wikidata(self):
        class Lf:
            def artist_bio(self, name, *, remaining, cancelled):
                return "Last.fm text."

            def top_albums(self, name, *, remaining, cancelled):
                return []

            def similar(self, name, *, remaining, cancelled):
                return []

        net = network(bio=lambda name: "Wikidata text.")
        net.lastfm = Lf()
        sections = network_sections(net, "Radiohead", None, radiohead_owned())
        self.assertEqual(sections["bio"]["bio"], {"text": "Last.fm text.", "source": "lastfm"})


class CatalogTests(unittest.TestCase):
    def sections(self, **kwargs):
        net = network(FakeMusicBrainz(artists=RADIOHEAD, albums=ALBUMS), **kwargs)
        owned_items = [{"name": "OK Computer", "year": 1997, "song_count": 12, "key": "radiohead/ok computer",
                        "id": "al1", "artwork_url": "/art/al1"},
                       {"name": "Live Bootleg", "year": 2001, "song_count": 3, "key": "radiohead/live bootleg",
                        "id": "al9", "artwork_url": "/art/al9"}]
        return network_sections(net, "Radiohead", "ar1", radiohead_owned(), owned_album_items=owned_items)

    def test_albums_merges_owned_and_unowned_ranked_by_popularity(self):
        stats = {"rg-owned": {"playcount": 900}, "rg-2": {"playcount": 50}, "rg-3": {"playcount": 500}}
        sections = self.sections(popularity=lambda mbids, can_cache: stats)
        items = sections["albums"]["items"]
        self.assertEqual([i["name"] for i in items], ["OK Computer", "The Bends", "Pablo Honey", "Live Bootleg"])
        self.assertEqual([i["owned"] for i in items], [True, False, False, True])
        self.assertEqual(items[0]["id"], "al1")
        self.assertEqual(items[0]["key"], "radiohead/ok computer")
        self.assertEqual(items[1]["key"], "radiohead/bends")
        self.assertIsNone(items[1]["id"])

    def test_albums_section_is_capped_at_twenty_most_popular(self):
        many = [album_candidate("musicbrainz", f"Album {i}", "Radiohead", 2000, f"rg-{i}") for i in range(40)]
        stats = {f"rg-{i}": {"playcount": i} for i in range(40)}
        net = network(FakeMusicBrainz(artists=RADIOHEAD, albums=many), popularity=lambda mbids, can_cache: stats)
        items = network_sections(net, "Radiohead", None, radiohead_owned())["albums"]["items"]
        self.assertEqual(len(items), 20)
        self.assertEqual(items[0]["name"], "Album 39")
        self.assertEqual(items[-1]["name"], "Album 20")

    def test_lastfm_play_counts_stand_in_only_when_listenbrainz_knows_none(self):
        class Lf:
            def top_albums(self, name, *, remaining, cancelled):
                return [{**album_candidate("lastfm", "Pablo Honey", "Radiohead", None, None), "playcount": 5_000_000}]

            def artist_bio(self, name, *, remaining, cancelled):
                return None

            def similar(self, name, *, remaining, cancelled):
                return []

        net = network(FakeMusicBrainz(artists=RADIOHEAD, albums=ALBUMS))
        net.lastfm = Lf()
        items = network_sections(net, "Radiohead", None, radiohead_owned())["albums"]["items"]
        honey = next(i for i in items if i["name"] == "Pablo Honey")
        self.assertEqual((honey["popularity"], honey["popularity_source"]), (5_000_000, "lastfm"))
        stats = {"rg-3": {"playcount": 900}}
        net2 = network(FakeMusicBrainz(artists=RADIOHEAD, albums=ALBUMS), popularity=lambda m, c: stats)
        net2.lastfm = Lf()
        items2 = network_sections(net2, "Radiohead", None, radiohead_owned())["albums"]["items"]
        honey2 = next(i for i in items2 if i["name"] == "Pablo Honey")
        self.assertIsNone(honey2["popularity"])

    def test_missing_albums_stays_the_unowned_subset(self):
        sections = self.sections()
        self.assertEqual(sorted(i["name"] for i in sections["missing_albums"]["items"]), ["Pablo Honey", "The Bends"])
        self.assertEqual(set(sections["missing_albums"]["items"][0]),
                         {"name", "year", "release_group_mbid", "popularity", "sources"})


class TagTests(unittest.TestCase):
    def test_tags_lead_with_the_library_genre_then_musicbrainz_tags(self):
        mb = FakeMusicBrainz(artists=RADIOHEAD, albums=ALBUMS)
        mb.artist_tags = lambda mbid, *, remaining, cancelled: [{"name": "art rock"}, {"name": "alternative rock"}]
        sections = network_sections(network(mb), "Radiohead", "ar1", radiohead_owned(), library_genre="Rock")
        self.assertEqual([t["name"] for t in sections["tags"]["items"]], ["rock", "alternative rock", "art rock"])
        self.assertTrue(sections["tags"]["complete"])


if __name__ == "__main__":
    unittest.main()
