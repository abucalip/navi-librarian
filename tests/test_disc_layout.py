import unittest

from discovery.search.album_page import mark_owned_tracks, owned_tracks
from discovery.search.disc_layout import disc_of, is_multi_disc, place_unmatched
from discovery.search.index import build_owned_data


def _song(sid, title, track, disc=None):
    song = {"id": sid, "title": title, "artist": "A", "artistId": "ar1", "album": "Live", "albumId": "al1",
            "duration": 100, "track": track}
    if disc is not None:
        song["discNumber"] = disc
    return song


def _data(songs):
    return build_owned_data(
        generation=1, built_at=0,
        artists=[{"id": "ar1", "name": "A", "album_count": 1}],
        albums=[{"id": "al1", "artist": "A", "artist_id": "ar1", "album": "Live", "year": 2000, "song_count": len(songs)}],
        songs=songs,
    )


def _provider(*titles):
    return [{"track_number": n, "title": t, "duration_seconds": 100} for n, t in enumerate(titles, 1)]


class DiscLayoutTests(unittest.TestCase):
    def test_disc_of_and_is_multi_disc(self):
        self.assertEqual(disc_of({"disc_number": None}), 1)
        self.assertFalse(is_multi_disc([{"disc_number": None}, {"disc_number": 1}]))
        self.assertTrue(is_multi_disc([{"disc_number": None}, {"disc_number": 2}]))

    def test_gap_positions_count_back_from_the_next_known_track_then_forward(self):
        # Disc 1 has four tracks, disc 2 has three; the library has disc1 t1, disc1 t4 and disc2 t2.
        known = {0: (1, 1), 3: (1, 4), 5: (2, 2)}
        placed = place_unmatched(7, known)
        self.assertEqual([placed[i] for i in range(7)],
                         [(1, 1), (1, 2), (1, 3), (1, 4), (2, 1), (2, 2), (2, 3)])

    def test_nothing_known_places_nothing(self):
        self.assertEqual(place_unmatched(3, {}), {})


class OwnedTracksTests(unittest.TestCase):
    def test_a_two_disc_album_lists_each_disc_with_its_own_numbers(self):
        data = _data([_song("s4", "D2 One", 1, 2), _song("s1", "D1 One", 1, 1), _song("s3", "D1 Two", 2, 1), _song("s2", "D2 Two", 2, 2)])
        tracks = owned_tracks(data, "al1")
        self.assertEqual([(t["disc_number"], t["track_number"], t["title"]) for t in tracks],
                         [(1, 1, "D1 One"), (1, 2, "D1 Two"), (2, 1, "D2 One"), (2, 2, "D2 Two")])

    def test_a_song_with_no_disc_tag_is_on_disc_one(self):
        data = _data([_song("s1", "Untagged", 1), _song("s2", "Second Disc", 1, 2)])
        self.assertEqual([(t["disc_number"], t["title"]) for t in owned_tracks(data, "al1")],
                         [(1, "Untagged"), (2, "Second Disc")])

    def test_a_single_disc_album_is_unchanged_and_has_no_disc_key(self):
        for songs in ([_song("s1", "One", 1), _song("s2", "Two", 2)], [_song("s1", "One", 1, 1), _song("s2", "Two", 2, 1)]):
            tracks = owned_tracks(_data(songs), "al1")
            self.assertEqual([t["track_number"] for t in tracks], [1, 2])
            self.assertTrue(all("disc_number" not in t for t in tracks))


class MarkedTracksTests(unittest.TestCase):
    def test_provider_tracks_on_a_multi_disc_album_get_disc_and_number_from_the_library(self):
        songs = _data([_song("s1", "A", 1, 1), _song("s2", "B", 2, 1), _song("s3", "C", 1, 2), _song("s4", "D", 2, 2)]).songs
        marked = mark_owned_tracks(_provider("A", "B", "C", "D"), songs)
        self.assertEqual([(t["disc_number"], t["track_number"], t["owned"]) for t in marked],
                         [(1, 1, True), (1, 2, True), (2, 1, True), (2, 2, True)])

    def test_a_missing_track_is_placed_on_the_disc_between_its_neighbours(self):
        songs = _data([_song("s1", "A", 1, 1), _song("s3", "D", 2, 2)]).songs
        marked = mark_owned_tracks(_provider("A", "B", "C", "D"), songs)
        self.assertEqual([(t["title"], t["disc_number"], t["track_number"], t["owned"]) for t in marked],
                         [("A", 1, 1, True), ("B", 1, 2, False), ("C", 2, 1, False), ("D", 2, 2, True)])

    def test_library_songs_the_provider_lacks_keep_their_disc_and_sort_into_place(self):
        songs = _data([_song("s1", "A", 1, 1), _song("s2", "Bonus", 1, 2), _song("s3", "C", 2, 1)]).songs
        marked = mark_owned_tracks(_provider("A", "C"), songs)
        self.assertEqual([(t["title"], t["disc_number"], t["track_number"]) for t in marked],
                         [("A", 1, 1), ("C", 1, 2), ("Bonus", 2, 1)])

    def test_a_disc_two_song_is_not_matched_to_a_provider_track_by_number_alone(self):
        # Provider track 1 is renamed; the same-number, same-length song on disc 2 must not claim it.
        songs = _data([_song("s1", "Disc Two Opener", 1, 2), _song("s2", "Disc One Opener", 1, 1)]).songs
        provider = [{"track_number": 1, "title": "Opening Remastered", "duration_seconds": 100}]
        marked = mark_owned_tracks(provider, songs)
        self.assertEqual([(t["title"], t["disc_number"], t["track_number"]) for t in marked],
                         [("Opening Remastered", 1, 1), ("Disc Two Opener", 2, 1)])

    def test_single_disc_marking_is_unchanged(self):
        songs = _data([_song("s1", "A", 1), _song("s2", "B", 2)]).songs
        marked = mark_owned_tracks(_provider("A", "B", "C"), songs)
        self.assertTrue(all("disc_number" not in t for t in marked))
        self.assertEqual([t["owned"] for t in marked], [True, True, False])


if __name__ == "__main__":
    unittest.main()
