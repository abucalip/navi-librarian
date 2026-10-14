"""Regression tests for retryable artwork-provider failures."""
import unittest
from unittest.mock import patch

from app.api import metadata


class FailingArtworkProvider:
    def get(self, _url):
        raise TimeoutError("simulated Deezer timeout")


class ArtworkRetryTests(unittest.TestCase):
    def test_provider_timeout_is_retryable_and_not_negative_cached(self):
        cache = {}
        with patch.object(metadata, "_EXTERNAL_HTTP", FailingArtworkProvider()), \
             patch.object(metadata, "_artwork_cache", cache):
            result = metadata.album_artwork(
                artist="Example Artist",
                album="Example Album",
            )

        self.assertIsNone(result["artwork_url"])
        self.assertTrue(result["retryable"])
        self.assertEqual(cache, {})


if __name__ == "__main__":
    unittest.main()
