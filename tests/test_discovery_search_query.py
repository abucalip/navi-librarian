import unittest

from discovery.search.artist_page import artist_page, json_sections
from discovery.search.index import IndexView, STATE_BUILDING, STATE_FRESH, build_owned_data
from discovery.search.query import (
    CursorError,
    decode_cursor,
    encode_cursor,
    find_artist,
    library_page,
    owned_albums,
    search_owned,
)


def sample_data():
    artists = [
        {"id": "ar1", "name": "Ash", "album_count": 1},
        {"id": "ar2", "name": "Ash", "album_count": 3},
        {"id": "ar3", "name": "The Beatles", "album_count": 14},
        {"id": "ar4", "name": "Beyoncé", "album_count": 12},
        {"id": "ar5", "name": "Radiohead", "album_count": 9},
    ]
    albums = [
        {"id": "al1", "artist": "Radiohead", "artist_id": "ar5", "album": "Kid A", "year": 2000, "song_count": 10},
        {"id": "al2", "artist": "Radiohead", "artist_id": "ar5", "album": "Pablo Honey", "year": 1993, "song_count": 12},
        {"id": "al3", "artist": "Radiohead", "artist_id": "ar5", "album": "Amnesiac", "year": None, "song_count": 11},
        {"id": "al4", "artist": "Radiohead", "artist_id": "ar5", "album": "Airbag", "year": 1993, "song_count": 1},
        {"id": "al5", "artist": "Ash", "artist_id": "ar2", "album": "1977", "year": 1996, "song_count": 13},
    ]
    songs = [
        {"id": "s1", "title": "Karma Police", "artist": "Radiohead", "artistId": "ar5", "album": "OK Computer", "albumId": "alx", "duration": 264, "track": 6},
        {"id": "s2", "title": "Kid A", "artist": "Radiohead", "artistId": "ar5", "album": "Kid A", "albumId": "al1", "duration": 284.9, "track": "x"},
    ]
    return build_owned_data(
        generation="g", built_at=1000.0,
        artists=artists, albums=albums, songs=songs,
    )


class SearchOwnedTests(unittest.TestCase):
    def test_exact_then_prefix_then_contains_then_name(self):
        data = sample_data()
        found = search_owned(data, "ash", ["artist"], limit=10)["artist"]
        self.assertEqual([a["id"] for a in found], ["ar1", "ar2"])
        self.assertTrue(all(a["owned"] for a in found))
        self.assertEqual(found[0]["sources"], ["navidrome"])

    def test_contains_match_ranks_below_prefix_match(self):
        data = build_owned_data(
            generation="g", built_at=0,
            artists=[{"id": "x", "name": "Big Ash", "album_count": 1},
                     {"id": "y", "name": "Ashes", "album_count": 1}],
            albums=[], songs=[],
        )
        found = search_owned(data, "ash", ["artist"], limit=10)["artist"]
        self.assertEqual([a["id"] for a in found], ["y", "x"])

    def test_limit_applies_per_type(self):
        data = sample_data()
        found = search_owned(data, "a", ["artist", "album"], limit=1)
        self.assertEqual(len(found["artist"]), 1)
        self.assertEqual(len(found["album"]), 1)

    def test_album_and_song_results_carry_their_fields(self):
        data = sample_data()
        album = search_owned(data, "kid a", ["album"], limit=5)["album"][0]
        self.assertEqual(album["artist"], "Radiohead")
        self.assertEqual(album["artist_key"], "radiohead")
        self.assertEqual(album["year"], 2000)
        self.assertIsNone(album["release_group_mbid"])

        song = search_owned(data, "karma", ["song"], limit=5)["song"][0]
        self.assertEqual(song["album"], "OK Computer")
        self.assertEqual(song["duration"], 264)
        self.assertEqual(song["track_number"], 6)

    def test_song_with_non_integer_duration_or_track_is_normalized(self):
        data = sample_data()
        song = search_owned(data, "kid a", ["song"], limit=5)["song"][0]
        self.assertEqual(song["duration"], 284)
        self.assertIsNone(song["track_number"])

    def test_unknown_types_are_ignored(self):
        self.assertEqual(search_owned(sample_data(), "ash", ["podcast"], limit=5), {})

    def test_owned_genres_match_album_genres_once_per_normalized_key(self):
        data = build_owned_data(
            generation="g", built_at=0,
            artists=[{"id": "ar1", "name": "Ride", "album_count": 2}],
            albums=[
                {"id": "al1", "artist": "Ride", "artist_id": "ar1", "album": "Nowhere", "genre": "Shoegaze"},
                {"id": "al2", "artist": "Ride", "artist_id": "ar1", "album": "Going Blank Again", "genre": "shoegaze"},
                {"id": "al3", "artist": "Ride", "artist_id": "ar1", "album": "Untitled"},
            ],
            songs=[],
        )
        found = search_owned(data, "shoe", ["genre"], limit=5)["genre"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0], {
            "type": "genre", "owned": True, "id": "shoegaze", "key": "shoegaze", "name": "Shoegaze",
            "mbid": None, "tag": "shoegaze", "tag_source": "navidrome", "sources": ["navidrome"],
            "artwork_url": None,
        })
        self.assertEqual(search_owned(data, "jazz", ["genre"], limit=5)["genre"], [])


class LibraryPageTests(unittest.TestCase):
    def test_name_sort_pages_and_filters(self):
        data = sample_data()
        items, next_offset, total = library_page(data, query="", sort="name", offset=0, limit=2)
        self.assertEqual([a["name"] for a in items], ["Ash", "Ash"])
        self.assertEqual(total, 5)
        self.assertEqual(next_offset, 2)

        items, next_offset, total = library_page(data, query="beyonce", sort="name", offset=0, limit=60)
        self.assertEqual([a["name"] for a in items], ["Beyoncé"])
        self.assertIsNone(next_offset)
        self.assertEqual(total, 1)

    def test_album_count_sort_is_descending(self):
        items, _, _ = library_page(sample_data(), query="", sort="album_count", offset=0, limit=60)
        self.assertEqual(items[0]["name"], "The Beatles")
        self.assertEqual(items[-1]["name"], "Ash")

    def test_cursor_round_trips_and_refuses_another_query_or_sort(self):
        cursor = encode_cursor(offset=60, query="ash", sort="name")
        self.assertEqual(decode_cursor(cursor, query="ash", sort="name"), 60)
        with self.assertRaises(CursorError):
            decode_cursor(cursor, query="", sort="name")
        with self.assertRaises(CursorError):
            decode_cursor(cursor, query="ash", sort="album_count")
        with self.assertRaises(CursorError):
            decode_cursor("not-a-cursor!!", query="", sort="name")


class ArtistLookupTests(unittest.TestCase):
    def test_unknown_key_is_unknown(self):
        status, artist, candidates = find_artist(sample_data(), "nobody", None)
        self.assertEqual((status, artist, candidates), ("unknown", None, []))

    def test_same_key_without_id_is_ambiguous_with_candidates(self):
        status, artist, candidates = find_artist(sample_data(), "ash", None)
        self.assertEqual(status, "ambiguous")
        self.assertIsNone(artist)
        self.assertEqual(candidates, [
            {"id": "ar1", "name": "Ash", "album_count": 1},
            {"id": "ar2", "name": "Ash", "album_count": 3},
        ])

    def test_id_selects_one_exact_artist(self):
        status, artist, _ = find_artist(sample_data(), "ash", "ar2")
        self.assertEqual(status, "ok")
        self.assertEqual(artist["id"], "ar2")

    def test_id_that_matches_no_artist_under_the_key_is_unknown(self):
        status, _, _ = find_artist(sample_data(), "ash", "ar5")
        self.assertEqual(status, "unknown")

    def test_owned_albums_sorted_by_year_with_unknown_last(self):
        albums = owned_albums(sample_data(), "ar5")
        self.assertEqual([a["name"] for a in albums],
                         ["Airbag", "Pablo Honey", "Kid A", "Amnesiac"])
        self.assertIsNone(albums[-1]["year"])
        self.assertEqual(albums[0]["key"], "radiohead/airbag")
        self.assertEqual(set(albums[0]), {"name", "year", "song_count", "key", "id", "artwork_url"})


class ArtistPageTests(unittest.TestCase):
    def test_index_building_is_200_with_owned_sections_unavailable(self):
        view = IndexView(STATE_BUILDING, None, "index_building")
        page = artist_page(view, "radiohead", None)
        self.assertEqual(page.status, "ok")
        self.assertTrue(page.partial)
        sections = json_sections(page)
        self.assertEqual(sections["artist"],
                         {"available": False, "complete": False, "reason": "index_building", "artist": None})
        self.assertEqual(sections["owned_albums"]["items"], [])
        self.assertEqual(sections["bio"]["reason"], "not_in_this_build")
        self.assertEqual(set(page.capabilities), {"sections", "sources", "owned_index"})

    def test_ready_index_builds_artist_and_owned_albums(self):
        view = IndexView(STATE_FRESH, sample_data(), None)
        page = artist_page(view, "radiohead", None)
        sections = json_sections(page)
        self.assertEqual(sections["artist"]["artist"]["name"], "Radiohead")
        self.assertIs(sections["artist"]["artist"]["owned"], True)
        self.assertEqual(sections["artist"]["artist"]["album_count"], 9)
        self.assertEqual(len(sections["owned_albums"]["items"]), 4)
        self.assertFalse(page.partial)
        self.assertEqual(sections["missing_albums"], {
            "available": False, "complete": False, "reason": "not_in_this_build", "items": [],
        })

    def test_ambiguous_key_returns_candidates_without_sections(self):
        view = IndexView(STATE_FRESH, sample_data(), None)
        page = artist_page(view, "ash", None)
        self.assertEqual(page.status, "ambiguous")
        self.assertEqual(len(page.candidates), 2)


if __name__ == "__main__":
    unittest.main()


class ArtworkUrlTests(unittest.TestCase):
    def test_owned_results_point_at_the_app_artwork_route(self):
        data = sample_data()
        artist = search_owned(data, "radiohead", ["artist"], limit=5)["artist"][0]
        self.assertEqual(artist["artwork_url"], "/api/owned/artwork/ar5")
        album = search_owned(data, "kid a", ["album"], limit=5)["album"][0]
        self.assertEqual(album["artwork_url"], "/api/owned/artwork/al1")

    def test_song_artwork_uses_its_album_id(self):
        data = sample_data()
        song = search_owned(data, "karma", ["song"], limit=5)["song"][0]
        self.assertEqual(song["artwork_url"], "/api/owned/artwork/alx")

    def test_library_items_carry_artwork_urls(self):
        items, _, _ = library_page(sample_data(), query="", sort="name", offset=0, limit=60)
        self.assertTrue(all(item["artwork_url"] == f"/api/owned/artwork/{item['id']}" for item in items))


class ArtistGenreResultTests(unittest.TestCase):
    def test_artist_results_carry_the_genre_or_null(self):
        data = build_owned_data(
            generation="g", built_at=0,
            artists=[{"id": "ar1", "name": "Ash", "album_count": 1},
                     {"id": "ar2", "name": "Ash", "album_count": 2}],
            albums=[{"id": "al1", "artist": "Ash", "artist_id": "ar1", "album": "1977", "genre": "Rock"}],
            songs=[],
        )
        found = {a["id"]: a for a in search_owned(data, "ash", ["artist"], limit=5)["artist"]}
        self.assertEqual(found["ar1"]["genre"], "Rock")
        self.assertIsNone(found["ar2"]["genre"])

