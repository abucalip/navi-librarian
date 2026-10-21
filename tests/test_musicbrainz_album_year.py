"""Direct-import regression tests for exact MusicBrainz album-year matching."""
import json
import unittest
from unittest.mock import patch

from integrations.musicbrainz import album_year as service


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class MusicBrainzAlbumYearTests(unittest.TestCase):
    def setUp(self):
        service.year_cache.clear()
        service._last_request = 0.0

    def test_exact_title_and_artist_credit_returns_earliest_valid_year(self):
        payload = {"release-groups": [
            {"title": "Album", "artist-credit": [{"artist": {"name": "Other"}}], "first-release-date": "1980"},
            {"title": "Album", "artist-credit": [{"artist": {"name": "Artist"}}], "first-release-date": "1998-05"},
            {"title": "Album", "artist-credit": [{"artist": {"name": "Artist"}}], "first-release-date": "1997"},
            {"title": "Album Deluxe", "artist-credit": [{"artist": {"name": "Artist"}}], "first-release-date": "1990"},
        ]}
        with patch.object(service, "urlopen", return_value=_Response(payload)), patch.object(service, "monotonic", return_value=100.0), patch.object(service, "sleep"):
            self.assertEqual(service.lookup_album_year("Artist", "Album"), 1997)

    def test_missing_inputs_do_not_request(self):
        with patch.object(service, "urlopen") as request:
            self.assertIsNone(service.lookup_album_year("", "Album"))
            self.assertIsNone(service.lookup_album_year("Artist", ""))
            request.assert_not_called()

    def test_negative_result_is_cached_for_short_ttl(self):
        payload = {"release-groups": []}
        with patch.object(service, "urlopen", return_value=_Response(payload)), patch.object(service, "monotonic", return_value=100.0), patch.object(service, "sleep"), patch.object(service, "_year_lock"):
            self.assertIsNone(service.lookup_album_year("Unknown", "Album"))
            with patch.object(service, "urlopen") as request:
                self.assertIsNone(service.lookup_album_year("Unknown", "Album"))
                request.assert_not_called()
