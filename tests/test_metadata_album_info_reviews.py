"""The album page's Info (Apple Music, else Wikipedia) and Reviews (up to three outlets) lookups."""
import os
import time
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import metadata
from app.services import persistent_metadata

APPLE = {"paragraphs": ["Apple notes."], "source": "Apple Music", "url": "https://music.apple.com/x"}
APPLE_NONE = {"paragraphs": [], "source": "Apple Music", "url": None}
WIKI = {"paragraphs": ["Wiki lead."], "source": "Wikipedia", "url": "https://en.wikipedia.org/wiki/X", "license": "CC BY-SA 4.0"}


def clear_caches():
    metadata._album_description_cache.clear()
    metadata._review_cache.clear()


class _Store:
    def __init__(self):
        self.data = {}

    def get(self, key, ttl_seconds):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value


class StoreCase(unittest.TestCase):
    def setUp(self):
        self.store = _Store()
        persistent_metadata.attach(self.store.get, self.store.set)
        self.addCleanup(persistent_metadata.detach)
        clear_caches()
        self.addCleanup(clear_caches)


class InfoTests(StoreCase):
    def test_apple_notes_win_and_wikipedia_is_not_asked(self):
        with patch.object(metadata, "_apple_description", return_value=(APPLE, True)), \
                patch.object(metadata, "_wikipedia_description") as wikipedia:
            self.assertEqual(metadata.album_description("Portishead", "Dummy"), APPLE)
        wikipedia.assert_not_called()

    def test_wikipedia_is_the_fallback_when_apple_has_no_notes(self):
        with patch.object(metadata, "_apple_description", return_value=(APPLE_NONE, True)), \
                patch.object(metadata, "_wikipedia_description", return_value=(WIKI, True)):
            self.assertEqual(metadata.album_description("Portishead", "Dummy"), WIKI)
        self.assertEqual(self.store.data["album-description:v1:portishead:dummy"], WIKI)

    def test_a_found_description_is_not_looked_up_again(self):
        with patch.object(metadata, "_apple_description", return_value=(APPLE_NONE, True)) as apple, \
                patch.object(metadata, "_wikipedia_description", return_value=(WIKI, True)):
            metadata.album_description("Portishead", "Dummy")
            metadata.album_description("Portishead", "Dummy")
        self.assertEqual(apple.call_count, 1)

    def test_a_miss_everywhere_is_remembered_but_a_failed_lookup_is_not(self):
        with patch.object(metadata, "_apple_description", return_value=(APPLE_NONE, True)) as apple, \
                patch.object(metadata, "_wikipedia_description", return_value=(None, True)):
            self.assertEqual(metadata.album_description("A", "B"), APPLE_NONE)
            metadata.album_description("A", "B")
        self.assertEqual(apple.call_count, 1)
        clear_caches()
        with patch.object(metadata, "_apple_description", return_value=(APPLE_NONE, True)) as apple, \
                patch.object(metadata, "_wikipedia_description", return_value=(None, False)):
            metadata.album_description("A", "B")
            metadata.album_description("A", "B")
        self.assertEqual(apple.call_count, 2)

    def test_wikipedia_lookup_uses_the_exact_article_and_reports_failures(self):
        responses = [
            {"pages": [{"key": "Rejoice_(album)", "title": "Rejoice (album)", "description": "2020 studio album by Tony Allen"}]},
            {"extract": "Rejoice is an album.", "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Rejoice_(album)"}}},
        ]
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.side_effect = [type("R", (), {"raise_for_status": lambda self: None, "json": lambda self, p=p: p})()
                                      for p in responses]
            value, answered = metadata._wikipedia_description("Tony Allen", "Rejoice")
        self.assertTrue(answered)
        self.assertEqual(value["paragraphs"], ["Rejoice is an album."])
        self.assertEqual(client.get.call_args_list[1].args[0], "https://en.wikipedia.org/api/rest_v1/page/summary/Rejoice_%28album%29")
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.side_effect = RuntimeError("down")
            self.assertEqual(metadata._wikipedia_description("Tony Allen", "Rejoice"), (None, False))


def review(source, n=1):
    return {"source": source, "quote": f"{source} says a thing about this record, in a line.", "url": f"https://{source.lower()}.example/{n}"}


class ReviewTests(StoreCase):
    def run_with(self, sources):
        with patch.object(metadata, "_review_sources", return_value=sources):
            return metadata.album_reviews_for("Opeth", "Watershed")

    def test_the_first_three_outlets_in_order_are_kept(self):
        answer = self.run_with([lambda: review("A"), lambda: None, lambda: review("B"), lambda: review("C"), lambda: review("D")])
        self.assertEqual([r["source"] for r in answer["reviews"]], ["A", "B", "C"])
        self.assertNotIn("retryable", answer)

    def test_a_complete_answer_is_kept_and_not_fetched_again(self):
        calls = []
        source = lambda: calls.append(1) or review("A")
        self.run_with([source])
        self.run_with([source])
        self.assertEqual(len(calls), 1)
        self.assertIn("album-reviews:v1:opeth:watershed", self.store.data)
        clear_caches()
        self.run_with([source])
        self.assertEqual(len(calls), 1, "a restart reads the stored copy")

    def test_no_review_anywhere_is_an_empty_list_not_stored(self):
        self.assertEqual(self.run_with([lambda: None, lambda: None]), {"reviews": []})
        self.assertEqual(self.store.data, {})

    def test_a_failing_outlet_does_not_hide_the_others_and_the_partial_answer_is_short_lived(self):
        def boom():
            raise RuntimeError("blocked")
        calls = []
        ok = lambda: calls.append(1) or review("A")
        answer = self.run_with([boom, ok])
        self.assertEqual([r["source"] for r in answer["reviews"]], ["A"])
        self.assertTrue(answer["retryable"])
        self.assertEqual(self.store.data, {}, "a partial answer is not stored for a week")
        again = self.run_with([boom, ok])
        self.assertEqual(len(calls), 1, "but it is not re-asked on every visit")
        self.assertTrue(again["retryable"])
        with patch.object(metadata, "_REVIEWS_PARTIAL_TTL", 0):
            clear_caches()
            self.run_with([boom, ok])
            self.run_with([boom, ok])
        self.assertEqual(len(calls), 3, "and is asked again once its short life is over")

    def test_a_full_set_is_kept_even_when_another_outlet_failed(self):
        def boom():
            raise RuntimeError("blocked")
        answer = self.run_with([lambda: review("A"), boom, lambda: review("B"), lambda: review("C")])
        self.assertEqual(len(answer["reviews"]), 3)
        self.assertNotIn("retryable", answer)
        self.assertIn("album-reviews:v1:opeth:watershed", self.store.data)

    def test_a_slow_outlet_is_left_behind_at_the_deadline(self):
        with patch.object(metadata, "_REVIEWS_DEADLINE", 0.2):
            started = time.monotonic()
            answer = self.run_with([lambda: review("A"), lambda: time.sleep(1.5) or review("B")])
        self.assertLess(time.monotonic() - started, 1.0)
        self.assertEqual([r["source"] for r in answer["reviews"]], ["A"])
        self.assertTrue(answer["retryable"])

    def test_guardian_is_skipped_without_a_key_and_asked_with_one(self):
        with patch.dict(os.environ, {"GUARDIAN_API_KEY": ""}), patch.object(metadata, "_EXTERNAL_HTTP") as client:
            self.assertIsNone(metadata._guardian_review("Opeth", "Watershed"))
            client.get.assert_not_called()
        payload = {"response": {"results": [{
            "webTitle": "Opeth: Watershed review", "webUrl": "https://www.theguardian.com/x",
            "fields": {"trailText": "Swedish prog-metal greats unexpectedly fly their freak flag."}}]}}
        with patch.dict(os.environ, {"GUARDIAN_API_KEY": "k"}), patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.return_value.json.return_value = payload
            found = metadata._guardian_review("Opeth", "Watershed")
        self.assertEqual(found["source"], "The Guardian")
        self.assertEqual(client.get.call_args.kwargs["params"]["api-key"], "k")

    def test_wordpress_outlet_reads_the_dek_only_after_an_exact_headline_match(self):
        dek = "Swedish prog-metal greats unexpectedly fly their freak flag on their ninth full-length."
        search = [{"title": "Album Review: Opeth &#8211; Watershed", "url": "https://consequence.net/2008/06/album-review-watershed/"}]
        page = f'<meta property="og:description" content="{dek}"/>'
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.side_effect = [
                type("R", (), {"raise_for_status": lambda self: None, "json": lambda self: search})(),
                type("R", (), {"raise_for_status": lambda self: None, "text": page})(),
            ]
            found = metadata._wordpress_review("Consequence", "https://consequence.net", "Opeth", "Watershed")
        self.assertEqual(found, {"source": "Consequence", "quote": dek, "url": "https://consequence.net/2008/06/album-review-watershed/"})
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.return_value.json.return_value = [{"title": "Opeth share a song", "url": "https://consequence.net/x/"}]
            self.assertIsNone(metadata._wordpress_review("Consequence", "https://consequence.net", "Opeth", "Watershed"))
            self.assertEqual(client.get.call_count, 1)


class RouteTests(StoreCase):
    def setUp(self):
        super().setUp()
        app = FastAPI()
        app.include_router(metadata.router)
        self.client = TestClient(app)

    def test_reviews_route_returns_the_reviews_and_requires_both_names(self):
        with patch.object(metadata, "album_reviews_for", return_value={"reviews": [review("A")]}) as lookup:
            body = self.client.get("/api/album-reviews", params={"artist": " Opeth ", "album": "Watershed"})
        self.assertEqual(body.json(), {"reviews": [review("A")]})
        lookup.assert_called_once_with("Opeth", "Watershed")
        self.assertEqual(self.client.get("/api/album-reviews", params={"artist": "Opeth"}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
