import unittest

from discovery.search.album_position import library_position
from discovery.search.index import build_owned_data


def data():
    albums = [
        {"id": "a1", "artist": "Radiohead", "artist_id": "r", "album": "Kid A", "year": 2000, "song_count": 10},
        {"id": "a2", "artist": "Radiohead", "artist_id": "r", "album": "Pablo Honey", "year": 1993, "song_count": 12},
        {"id": "a3", "artist": "Ash", "artist_id": "s", "album": "1977", "year": 1996, "song_count": 13},
    ]
    artists = [{"id": "r", "name": "Radiohead", "album_count": 2}, {"id": "s", "name": "Ash", "album_count": 1}]
    return build_owned_data(generation="g", built_at=0, artists=artists, albums=albums, songs=[])


class LibraryPositionTests(unittest.TestCase):
    def test_counts_from_one_in_name_order(self):
        d = data()
        by_id = {a["id"]: a for a in d.albums}
        self.assertEqual(library_position(d, by_id["a3"]), (1, 3))
        self.assertEqual(library_position(d, by_id["a1"]), (2, 3))
        self.assertEqual(library_position(d, by_id["a2"]), (3, 3))

    def test_none_without_an_index_or_an_album_it_holds(self):
        d = data()
        self.assertIsNone(library_position(None, d.albums[0]))
        self.assertIsNone(library_position(d, None))
        stranger = {"id": "zz", "name_key": "x", "artist_key": "y"}
        self.assertIsNone(library_position(d, stranger))
