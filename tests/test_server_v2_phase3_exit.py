import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from server_v2_phase3_exit import epoch, to_record  # noqa: E402


class Phase3ExitHelpersTests(unittest.TestCase):
    def test_epoch_reads_navidrome_timestamps(self):
        self.assertEqual(epoch("2026-10-19T09:58:03.066096989Z"), epoch("2026-10-19T09:58:03.066096Z"))
        self.assertEqual(epoch("1970-01-02T00:00:00Z"), 86400.0)

    def test_epoch_treats_never_played_and_junk_as_none(self):
        for value in (None, "", "0001-01-01T00:00:00Z", "not a date"):
            self.assertIsNone(epoch(value))

    def test_to_record_maps_play_fields(self):
        r = to_record({"id": "a1", "name": "T", "artist": "X", "playCount": 7, "played": "1970-01-02T00:00:00Z",
                       "starred": "2020-01-01T00:00:00Z", "userRating": 4})
        self.assertEqual((r.key, r.kind, r.play_count, r.last_played, r.starred, r.rating),
                         ("album:a1", "album", 7, 86400.0, True, 4))

    def test_to_record_defaults_for_unplayed_album(self):
        r = to_record({"id": "a2", "name": "U"})
        self.assertEqual((r.play_count, r.last_played, r.starred, r.rating), (0, None, False, None))


if __name__ == "__main__":
    unittest.main()
