"""Metadata answers that found something are cacheable by the browser; everything else is not."""
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import http_cache


class CacheControlForTests(unittest.TestCase):
    def test_found_answers_are_cacheable(self):
        for path, payload in [
            ("/api/artwork", {"artwork_url": "https://x/c.jpg"}),
            ("/api/artist-image", {"artwork_url": "https://x/a.jpg"}),
            ("/api/album-details", {"tracks": [{"title": "t"}]}),
            ("/api/album-description", {"paragraphs": ["p"]}),
            ("/api/artist-bio", {"bio": "text"}),
            ("/api/album-year", {"year": 1994}),
            ("/api/album-links", {"deezer": "https://d"}),
        ]:
            self.assertEqual(http_cache.cache_control_for(path, payload), "private, max-age=86400", path)

    def test_empty_retryable_and_unknown_answers_are_not(self):
        self.assertIsNone(http_cache.cache_control_for("/api/artwork", {"artwork_url": None}))
        self.assertIsNone(http_cache.cache_control_for("/api/artwork", {"artwork_url": "u", "retryable": True}))
        self.assertIsNone(http_cache.cache_control_for("/api/album-links", {}))
        self.assertIsNone(http_cache.cache_control_for("/api/artist-bio", {"bio": ""}))
        self.assertIsNone(http_cache.cache_control_for("/api/other", {"bio": "x"}))
        self.assertIsNone(http_cache.cache_control_for("/api/artwork", [1]))


class MiddlewareTests(unittest.TestCase):
    def setUp(self):
        self.answer = {}
        probe = FastAPI()
        probe.middleware("http")(http_cache.add_cache_headers)
        probe.get("/api/artist-bio")(lambda: self.answer)
        probe.get("/api/unrelated")(lambda: {"bio": "x"})
        self.client = TestClient(probe)

    def test_found_answer_gets_the_header_and_keeps_its_body(self):
        self.answer = {"artist": "A", "bio": "Band."}
        response = self.client.get("/api/artist-bio")
        self.assertEqual(response.headers["cache-control"], "private, max-age=86400")
        self.assertEqual(response.json(), self.answer)

    def test_empty_answer_and_other_paths_get_none(self):
        self.answer = {"artist": "A", "bio": ""}
        self.assertNotIn("cache-control", self.client.get("/api/artist-bio").headers)
        self.assertNotIn("cache-control", self.client.get("/api/unrelated").headers)


if __name__ == "__main__":
    unittest.main()
