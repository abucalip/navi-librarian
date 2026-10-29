"""Album page sections: owned tracks, the tracklist race, and similar albums."""
import time
import unittest

from discovery.search.album_page import album_sections, find_album, mark_owned_tracks, owned_tracks
from discovery.search.artist_sections import ArtistNetwork
from discovery.search.index import build_owned_data
from discovery.search.providers import artist_candidate


class Store:
    def __init__(self):
        self.data = {}

    def read(self, key):
        return self.data.get(key)

    def write(self, key, value):
        self.data[key] = value


class FakeMusicBrainz:
    def __init__(self, tracks=(), delay=0.0):
        self.tracks = list(tracks)
        self.delay = delay

    def artists(self, query, *, remaining, cancelled):
        return []

    def artist_tags(self, mbid, *, remaining, cancelled):
        return []

    def release_group_tracks(self, mbid, *, remaining, cancelled):
        time.sleep(self.delay)
        return self.tracks


class FakeLastFm:
    def __init__(self, tracks=(), delay=0.0):
        self.tracks = list(tracks)
        self.delay = delay

    def album_tracks(self, artist, album, *, remaining, cancelled):
        time.sleep(self.delay)
        return self.tracks

    def top_albums(self, artist, *, remaining, cancelled):
        from discovery.search.providers import album_candidate
        return [album_candidate("lastfm", f"{artist} Greatest", artist, None, None)]

    def similar(self, name, *, remaining, cancelled):
        return [{"name": "Portishead", "mbid": None, "match": 0.9}]


def track(n, title, seconds=100):
    return {"track_number": n, "title": title, "duration_seconds": seconds}


def make_network(**kwargs):
    store = Store()
    values = dict(
        musicbrainz=FakeMusicBrainz(), popularity=lambda mbids, can_cache: {}, bio=lambda name: None,
        cache_read=store.read, cache_write=store.write, deadline_seconds=3.0,
    )
    values.update(kwargs)
    network = ArtistNetwork(**values)
    network.store = store
    return network


def owned():
    return build_owned_data(
        generation=1, built_at=0,
        artists=[{"id": "ar1", "name": "Radiohead", "album_count": 1}],
        albums=[{"id": "al1", "artist": "Radiohead", "artist_id": "ar1", "album": "Kid A", "year": 2000, "song_count": 2}],
        songs=[
            {"id": "s2", "title": "The National Anthem", "artist": "Radiohead", "artistId": "ar1",
             "album": "Kid A", "albumId": "al1", "duration": 351, "track": 2},
            {"id": "s1", "title": "Everything In Its Right Place", "artist": "Radiohead", "artistId": "ar1",
             "album": "Kid A", "albumId": "al1", "duration": 251, "track": 1},
        ],
    )


def run(network, data=None, album=None, **kwargs):
    values = dict(artist="Radiohead", artist_key="radiohead", name="Kid A", year=2000, release_group_mbid="rg1")
    values.update(kwargs)
    return {s["section"]: s for s in album_sections(network, data, album=album, **values)}


class OwnedAlbumTests(unittest.TestCase):
    def test_find_album_by_keys(self):
        data = owned()
        self.assertEqual(find_album(data, "radiohead", "kid a", None)["id"], "al1")
        self.assertIsNone(find_album(data, "radiohead", "ok computer", None))

    def test_an_album_id_wins_over_a_mismatched_artist_key(self):
        self.assertEqual(find_album(owned(), "various artists", "kid a", "al1")["id"], "al1")

    def test_tracks_come_from_the_index_in_track_order(self):
        tracks = owned_tracks(owned(), "al1")
        self.assertEqual([t["title"] for t in tracks], ["Everything In Its Right Place", "The National Anthem"])
        self.assertEqual(tracks[0]["duration_seconds"], 251)

    def test_owned_album_page_needs_no_tracklist_provider(self):
        data = owned()
        sections = run(make_network(), data, album=find_album(data, "radiohead", "kid a", None))
        self.assertTrue(sections["album"]["album"]["owned"])
        self.assertTrue(sections["album"]["album"]["artwork_url"].endswith("al1"))
        self.assertEqual(len(sections["tracks"]["items"]), 2)


class TrackOwnershipTests(unittest.TestCase):
    def test_provider_tracks_are_marked_owned_by_title(self):
        data = owned()
        provider = [track(1, "Everything In Its Right Place"), track(2, "Kid A"), track(3, "The National Anthem")]
        marked = mark_owned_tracks(provider, [s for s in data.songs if s["album_id"] == "al1"])
        self.assertEqual([(t["title"], t["owned"]) for t in marked],
                         [("Everything In Its Right Place", True), ("Kid A", False), ("The National Anthem", True)])

    def test_a_renamed_track_in_the_same_place_and_length_is_owned(self):
        data = owned()
        provider = [track(1, "Everything In Its Right Place - Remastered", 252), track(2, "The National Anthem", 351)]
        marked = mark_owned_tracks(provider, [s for s in data.songs if s["album_id"] == "al1"])
        self.assertEqual([t["owned"] for t in marked], [True, True])

    def test_a_different_track_with_the_same_number_but_another_length_is_not_owned(self):
        data = owned()
        marked = mark_owned_tracks([track(1, "Something Else", 100)], [s for s in data.songs if s["album_id"] == "al1"])
        self.assertFalse(marked[0]["owned"])

    def test_library_songs_the_provider_does_not_list_are_appended_as_owned(self):
        data = owned()
        marked = mark_owned_tracks([track(1, "Everything In Its Right Place")], [s for s in data.songs if s["album_id"] == "al1"])
        self.assertEqual([(t["title"], t["owned"]) for t in marked],
                         [("Everything In Its Right Place", True), ("The National Anthem", True)])

    def test_an_owned_album_marks_provider_tracks_and_an_unowned_album_marks_none(self):
        network = make_network(deezer_tracks=lambda a, b: [track(1, "Everything In Its Right Place"), track(2, "Kid A")])
        data = owned()
        items = run(network, data, album=find_album(data, "radiohead", "kid a", None))["tracks"]["items"]
        self.assertEqual([t["owned"] for t in items[:2]], [True, False])
        items = run(make_network(deezer_tracks=lambda a, b: [track(1, "x")]))["tracks"]["items"]
        self.assertEqual([t["owned"] for t in items], [False])

    def test_an_owned_album_falls_back_to_the_library_tracklist_when_no_provider_answers(self):
        def broken(artist, album):
            raise RuntimeError("down")
        data = owned()
        items = run(make_network(deezer_tracks=broken), data, album=find_album(data, "radiohead", "kid a", None))["tracks"]["items"]
        self.assertEqual([(t["title"], t["owned"]) for t in items],
                         [("Everything In Its Right Place", True), ("The National Anthem", True)])


class GenreTests(unittest.TestCase):
    def test_the_library_genre_is_emitted_at_once_without_a_lookup(self):
        data = build_owned_data(
            generation=1, built_at=0,
            artists=[{"id": "ar1", "name": "Radiohead", "album_count": 1}],
            albums=[{"id": "al1", "artist": "Radiohead", "artist_id": "ar1", "album": "Kid A", "year": 2000, "song_count": 0, "genre": "Electronic"}],
            songs=[],
        )
        sections = run(make_network(deezer_tracks=lambda a, b: [track(1, "x")]), data, album=find_album(data, "radiohead", "kid a", None))
        self.assertEqual(sections["genre"]["genre"], "electronic")

    def test_without_a_library_genre_the_first_artist_tag_is_used(self):
        mb = FakeMusicBrainz()
        mb.artists = lambda query, *, remaining, cancelled: [artist_candidate("musicbrainz", "Portishead", "mb-p")]
        mb.artist_tags = lambda mbid, *, remaining, cancelled: [{"name": "trip hop"}]
        network = make_network(musicbrainz=mb, deezer_tracks=lambda a, b: [track(1, "x")])
        section = run(network, artist="Portishead", artist_key="portishead", name="Dummy")["genre"]
        self.assertEqual((section["available"], section["genre"]), (True, "trip hop"))

    def test_no_known_genre_is_a_valid_empty_answer(self):
        section = run(make_network(deezer_tracks=lambda a, b: [track(1, "x")]), artist="Nobody", artist_key="nobody", name="Nothing")["genre"]
        self.assertTrue(section["available"])
        self.assertIsNone(section["genre"])


class YearTests(unittest.TestCase):
    def test_a_known_year_is_emitted_at_once_without_a_lookup(self):
        def never(artist, album):
            raise AssertionError("no lookup needed")

        sections = run(make_network(album_year=never, deezer_tracks=lambda a, b: [track(1, "x")]))
        self.assertEqual(sections["year"]["year"], 2000)

    def test_a_missing_year_is_looked_up(self):
        network = make_network(album_year=lambda artist, album: 1994, deezer_tracks=lambda a, b: [track(1, "x")])
        self.assertEqual(run(network, year=None)["year"]["year"], 1994)

    def test_a_failed_lookup_leaves_the_year_empty(self):
        def broken(artist, album):
            raise RuntimeError("down")

        network = make_network(album_year=broken, deezer_tracks=lambda a, b: [track(1, "x")])
        section = run(network, year=None)["year"]
        self.assertIsNone(section["year"])
        self.assertEqual(section["reason"], "source_failed")


class DescriptionTests(unittest.TestCase):
    def test_description_comes_from_the_network_lookup(self):
        found = {"paragraphs": ["One.", "Two."], "source": "Apple Music", "url": "https://music.apple.com/x"}
        network = make_network(album_description=lambda artist, album: found, deezer_tracks=lambda a, b: [track(1, "x")])
        self.assertEqual(run(network)["description"]["description"], found)

    def test_no_notes_is_a_valid_empty_description(self):
        network = make_network(deezer_tracks=lambda a, b: [track(1, "x")])
        section = run(network)["description"]
        self.assertTrue(section["available"])
        self.assertEqual(section["description"]["paragraphs"], [])


class TracklistRaceTests(unittest.TestCase):
    def test_fastest_non_empty_source_wins_and_is_cached(self):
        network = make_network(
            lastfm=FakeLastFm([track(1, "Slow")], delay=0.5),
            deezer_tracks=lambda artist, album: [track(1, "Fast")],
        )
        sections = run(network)
        self.assertEqual([t["title"] for t in sections["tracks"]["items"]], ["Fast"])
        self.assertTrue(network.store.data)

    def test_empty_answers_are_skipped(self):
        network = make_network(
            lastfm=FakeLastFm([]),
            deezer_tracks=lambda artist, album: [],
            musicbrainz=FakeMusicBrainz([track(1, "From MusicBrainz")], delay=0.1),
        )
        self.assertEqual(run(network)["tracks"]["items"][0]["title"], "From MusicBrainz")

    def test_all_sources_failing_is_source_failed(self):
        def broken(artist, album):
            raise RuntimeError("down")

        sections = run(make_network(deezer_tracks=broken), release_group_mbid=None)
        self.assertEqual(sections["tracks"]["reason"], "source_failed")
        self.assertFalse(sections["tracks"]["available"])

    def test_nothing_found_is_a_valid_empty_list(self):
        sections = run(make_network(deezer_tracks=lambda artist, album: []), release_group_mbid=None)
        self.assertTrue(sections["tracks"]["available"])
        self.assertEqual(sections["tracks"]["items"], [])


class SimilarTests(unittest.TestCase):
    def test_similar_albums_take_one_album_per_similar_artist(self):
        network = make_network(lastfm=FakeLastFm([track(1, "x")]), deezer_tracks=lambda a, b: [track(1, "x")])
        sections = run(network)
        self.assertEqual([i["name"] for i in sections["similar_artists"]["items"]], ["Portishead"])
        albums = sections["similar_albums"]["items"]
        self.assertEqual(albums[0]["artist"], "Portishead")
        self.assertEqual(albums[0]["key"], "portishead/portishead greatest")
        self.assertFalse(albums[0]["owned"])

    def test_without_lastfm_similar_albums_report_source_disabled(self):
        sections = run(make_network(deezer_tracks=lambda a, b: [track(1, "x")]))
        self.assertEqual(sections["similar_albums"]["reason"], "source_disabled")


if __name__ == "__main__":
    unittest.main()
