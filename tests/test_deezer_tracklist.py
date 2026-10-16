"""Direct-import regressions for Deezer tracklist shaping."""

import unittest

from app.services.deezer_tracklist import shape_tracklist


class DeezerTracklistTests(unittest.TestCase):
    def test_normalizes_track_fields_and_uses_position_fallback(self):
        self.assertEqual(shape_tracklist([
            {"track_position": 4, "title": " Opening ", "duration": "123"},
            {"title": "Finale", "duration": 234},
        ]), [
            {"track_number": 4, "title": "Opening", "duration_seconds": 123},
            {"track_number": 2, "title": "Finale", "duration_seconds": 234},
        ])

    def test_skips_empty_titles_and_handles_missing_numeric_fields(self):
        self.assertEqual(shape_tracklist([
            {"title": "  ", "duration": 8},
            {"title": "Interlude"},
            {},
        ]), [
            {"track_number": 2, "title": "Interlude", "duration_seconds": 0},
        ])

    def test_preserves_existing_failure_for_invalid_numeric_values(self):
        with self.assertRaises(ValueError):
            shape_tracklist([{"title": "Track", "duration": "not-a-number"}])
