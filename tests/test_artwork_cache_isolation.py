"""Regression guard for independent album-year and artwork request caches."""
import unittest
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "static" / "app.js"


def load_page_script():
    return SOURCE.read_text(encoding="utf-8")


class ArtworkCacheIsolationTests(unittest.TestCase):
    def test_album_year_and_artwork_use_distinct_request_caches(self):
        page = load_page_script()

        self.assertIn("const artworkRequests = new Map();", page)
        self.assertIn("const albumYearRequests = new Map();", page)
        self.assertIn("albumYearRequests.set(cacheKey, new Promise(", page)
        self.assertIn("'/api/album-years'", page)
        self.assertIn(
            "cachedJSONRequest(artworkRequests, cacheKey, '/api/artwork?'",
            page,
        )


if __name__ == "__main__":
    unittest.main()
