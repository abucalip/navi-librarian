import unittest
from types import SimpleNamespace

from discovery.search.album_page import album_sections, find_album, mark_owned_tracks, owned_tracks
from discovery.search.index import build_owned_data
from discovery.search.quality_label import album_quality_label, quality_label


class QualityLabelTests(unittest.TestCase):
    def test_lossless_shows_depth_and_whole_kilohertz(self):
        self.assertEqual(quality_label("flac", 900, 16, 44100), "FLAC 16/44")
        self.assertEqual(quality_label("FLAC", 2800, 24, 96000), "FLAC 24/96")
        self.assertEqual(quality_label("flac", 0, 24, 192000), "FLAC 24/192")

    def test_lossless_with_missing_fields_is_shorter_not_guessed(self):
        self.assertEqual(quality_label("flac", None, None, None), "FLAC")
        self.assertEqual(quality_label("flac", None, 16, 0), "FLAC 16-bit")
        self.assertEqual(quality_label("wav", None, 16, 44100), "WAV 16/44")

    def test_lossy_shows_the_bitrate(self):
        self.assertEqual(quality_label("mp3", 320, 0, 44100), "MP3 320k")
        self.assertEqual(quality_label("mp3", 245, None, None), "MP3 245k")
        self.assertEqual(quality_label("opus", None, None, None), "OPUS")

    def test_m4a_is_alac_only_when_it_has_a_bit_depth(self):
        self.assertEqual(quality_label("m4a", 256, 0, 44100), "AAC 256k")
        self.assertEqual(quality_label("m4a", 900, 16, 44100), "ALAC 16/44")

    def test_unknown_or_missing_suffix(self):
        self.assertIsNone(quality_label(None, 320, 16, 44100))
        self.assertIsNone(quality_label("", 320, 16, 44100))
        self.assertEqual(quality_label(".xyz", None, None, None), "XYZ")
        self.assertEqual(quality_label("flac", True, "x", -5), "FLAC")


def _data():
    return build_owned_data(
        generation=1, built_at=0,
        artists=[{"id": "ar1", "name": "Radiohead", "album_count": 1}],
        albums=[{"id": "al1", "artist": "Radiohead", "artist_id": "ar1", "album": "Kid A", "year": 2000, "song_count": 3}],
        songs=[
            {"id": "s1", "title": "One", "artist": "Radiohead", "artistId": "ar1", "album": "Kid A", "albumId": "al1",
             "duration": 100, "track": 1, "suffix": "flac", "bitRate": 900, "bitDepth": 16, "samplingRate": 44100},
            {"id": "s2", "title": "Two", "artist": "Radiohead", "artistId": "ar1", "album": "Kid A", "albumId": "al1",
             "duration": 100, "track": 2, "suffix": "mp3", "bitRate": 320},
            {"id": "s3", "title": "Three", "artist": "Radiohead", "artistId": "ar1", "album": "Kid A", "albumId": "al1",
             "duration": 100, "track": 3},
        ],
    )


class OwnedTrackQualityTests(unittest.TestCase):
    def test_index_keeps_the_file_fields(self):
        song = _data().songs[0]
        self.assertEqual((song["suffix"], song["bit_rate"], song["bit_depth"], song["sampling_rate"]), ("flac", 900, 16, 44100))
        self.assertIsNone(_data().songs[2]["suffix"])

    def test_tracks_carry_no_per_song_tag(self):
        self.assertTrue(all("quality" not in t for t in owned_tracks(_data(), "al1")))
        provider = [{"track_number": 1, "title": "One", "duration_seconds": 100}]
        marked = mark_owned_tracks(provider, [s for s in _data().songs if s["album_id"] == "al1"])
        self.assertTrue(all("quality" not in t for t in marked))


def _song(suffix, rate=None, depth=None):
    return {"suffix": suffix, "bit_rate": rate, "bit_depth": depth, "sampling_rate": 44100}


class AlbumQualityLabelTests(unittest.TestCase):
    def test_any_flac_is_just_flac(self):
        self.assertEqual(album_quality_label([_song("flac", 900, 16), _song("flac", 2800, 24)]), "FLAC")

    def test_other_lossless_or_a_flac_mix_is_lossless(self):
        self.assertEqual(album_quality_label([_song("m4a", 900, 16), _song("m4a", 900, 16)]), "lossless")
        self.assertEqual(album_quality_label([_song("wav", None, 16)]), "lossless")
        self.assertEqual(album_quality_label([_song("flac", 900, 16), _song("alac", 900, 16)]), "lossless")

    def test_compressed_shows_the_bit_rate(self):
        self.assertEqual(album_quality_label([_song("mp3", 320), _song("mp3", 320)]), "320k")
        self.assertEqual(album_quality_label([_song("m4a", 256, 0)]), "256k")
        self.assertEqual(album_quality_label([_song("mp3", 245), _song("mp3", 255)]), "250k")

    def test_compressed_among_lossless_wins_as_the_lowest_quality(self):
        self.assertEqual(album_quality_label([_song("flac", 900, 16), _song("mp3", 320)]), "320k")

    def test_compressed_without_a_rate_shows_the_format(self):
        self.assertEqual(album_quality_label([_song("opus")]), "OPUS")

    def test_unknown_formats_give_no_tag(self):
        self.assertIsNone(album_quality_label([]))
        self.assertIsNone(album_quality_label([_song(None, 320), _song("", 320)]))

    def test_album_page_album_section_carries_the_tag(self):
        data = _data()
        album = find_album(data, "radiohead", "kid a", None)
        first = next(album_sections(SimpleNamespace(clock=lambda: 0.0, deadline_seconds=1.0), data, album=album, artist="Radiohead", artist_key="radiohead",
                                    name="Kid A", year=2000, release_group_mbid=None))
        self.assertEqual(first["section"], "album")
        self.assertEqual(first["album"]["quality"], "320k")


if __name__ == "__main__":
    unittest.main()
