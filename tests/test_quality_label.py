import unittest

from discovery.search.album_page import mark_owned_tracks, owned_tracks
from discovery.search.index import build_owned_data
from discovery.search.quality_label import quality_label


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

    def test_library_tracks_carry_a_tag_only_when_the_file_has_one(self):
        tracks = owned_tracks(_data(), "al1")
        self.assertEqual([t.get("quality") for t in tracks], ["FLAC 16/44", "MP3 320k", None])
        self.assertNotIn("quality", tracks[2])

    def test_provider_tracks_get_a_tag_when_owned_and_none_when_not(self):
        data = _data()
        provider = [{"track_number": n, "title": t, "duration_seconds": 100} for n, t in ((1, "One"), (2, "Missing"), (3, "Two"))]
        marked = mark_owned_tracks(provider, [s for s in data.songs if s["album_id"] == "al1"])
        self.assertEqual([(t["title"], t["owned"], t.get("quality")) for t in marked],
                         [("One", True, "FLAC 16/44"), ("Missing", False, None), ("Two", True, "MP3 320k"),
                          ("Three", True, None)])


if __name__ == "__main__":
    unittest.main()
