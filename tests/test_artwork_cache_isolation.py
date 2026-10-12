"""Regression guard for independent album-year and artwork request caches."""
import ast
import unittest
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "app" / "main.py"


def load_page_script():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    page = next(
        node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "PAGE" for target in node.targets)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )
    return page


class ArtworkCacheIsolationTests(unittest.TestCase):
    def test_album_year_and_artwork_use_distinct_request_caches(self):
        page = load_page_script()

        self.assertIn("const artworkRequests = new Map();", page)
        self.assertIn("const albumYearRequests = new Map();", page)
        self.assertIn(
            "cachedJSONRequest(albumYearRequests, cacheKey, '/api/album-year?'",
            page,
        )
        self.assertIn(
            "cachedJSONRequest(artworkRequests, cacheKey, '/api/artwork?'",
            page,
        )


if __name__ == "__main__":
    unittest.main()
