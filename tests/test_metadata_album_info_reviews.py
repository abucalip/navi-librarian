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

    def guardian_answers(self, *payloads):
        return [type("R", (), {"raise_for_status": lambda self: None, "json": lambda self, p=p: p})() for p in payloads]

    def test_guardian_is_skipped_without_a_key(self):
        with patch.dict(os.environ, {"GUARDIAN_API_KEY": ""}), patch.object(metadata, "_EXTERNAL_HTTP") as client:
            self.assertIsNone(metadata._guardian_review("Opeth", "Watershed"))
            client.get.assert_not_called()

    def test_guardian_asks_the_artist_s_album_reviews_and_remembers_the_tag(self):
        tags = {"response": {"results": [{"id": "music/radiohead", "webTitle": "Radiohead"}]}}
        reviews = {"response": {"results": [{
            "webTitle": "Radiohead: The King of Limbs – review", "webUrl": "https://www.theguardian.com/music/2011/feb/18/king",
            "fields": {"trailText": "After another short-notice Radiohead release, people haven't stopped talking."}}]}}
        with patch.dict(os.environ, {"GUARDIAN_API_KEY": "k"}), patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.side_effect = self.guardian_answers(tags, reviews)
            found = metadata._guardian_review("Radiohead", "The King of Limbs")
            self.assertEqual(found["source"], "The Guardian")
            self.assertEqual(found["url"], "https://www.theguardian.com/music/2011/feb/18/king")
            search = client.get.call_args_list[1]
            self.assertEqual(search.args[0], "https://content.guardianapis.com/search")
            self.assertEqual(search.kwargs["params"]["tag"], "music/radiohead,tone/albumreview")
            self.assertEqual(search.kwargs["params"]["q"], '"The King of Limbs"')
            self.assertEqual(search.kwargs["params"]["api-key"], "k")
            client.get.side_effect = self.guardian_answers(reviews)
            metadata._guardian_review("Radiohead", "The King of Limbs")
            self.assertEqual(client.get.call_count, 3, "the second visit skips the tag lookup")
        self.assertEqual(self.store.data["guardian-artist-tag:v1:radiohead"], "music/radiohead")

    def test_guardian_query_text_has_no_characters_it_rejects(self):
        self.assertEqual(metadata._guardian_text("Spiritual Jazz 2: Europe"), "Spiritual Jazz 2 Europe")
        self.assertEqual(metadata._guardian_text("(Down Home) Blues"), "Down Home Blues")
        self.assertEqual(metadata._guardian_text("Gene Harris & Jack McDuff"), "Gene Harris Jack McDuff")
        self.assertEqual(metadata._guardian_text("Don't Fear the Reaper"), "Don't Fear the Reaper")
        with patch.dict(os.environ, {"GUARDIAN_API_KEY": "k"}), patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.side_effect = self.guardian_answers({"response": {"results": []}}, {"response": {"results": []}})
            metadata._guardian_review("Albert Mangelsdorff", "Spiritual Jazz 2: Europe")
        self.assertEqual(client.get.call_args_list[1].kwargs["params"]["q"], '"Albert Mangelsdorff" "Spiritual Jazz 2 Europe"')

    def test_guardian_tries_the_first_name_of_a_collaboration_for_the_tag(self):
        tags = lambda *titles: {"response": {"results": [{"id": "music/" + t.lower().replace(" ", "-"), "webTitle": t} for t in titles]}}
        review = {"response": {"results": [{
            "webTitle": "Tony Allen and Hugh Masekela: Rejoice review – a joyous last session", "webUrl": "https://www.theguardian.com/music/r",
            "fields": {"trailText": "The late drummer's final studio session is cautious, joyful and loose."}}]}}
        with patch.dict(os.environ, {"GUARDIAN_API_KEY": "k"}), patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.side_effect = self.guardian_answers(tags(), tags("Tony Allen"), review)
            found = metadata._guardian_review("Tony Allen & Hugh Masekela", "Rejoice")
        self.assertEqual(found["source"], "The Guardian")
        self.assertEqual(client.get.call_args_list[2].kwargs["params"]["tag"], "music/tony-allen,tone/albumreview")

    def test_guardian_falls_back_to_a_text_search_when_the_artist_has_no_tag(self):
        none = {"response": {"results": [{"id": "world/acid-attack", "webTitle": "Acid attacks"}]}}
        reviews = {"response": {"results": [{
            "webTitle": "Souad Massi: O Houria review – varied but lightweight", "webUrl": "https://www.theguardian.com/music/x",
            "fields": {"trailText": "This new album is varied but lightweight: her voice is as cool as ever."}}]}}
        with patch.dict(os.environ, {"GUARDIAN_API_KEY": "k"}), patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.side_effect = self.guardian_answers(none, reviews)
            self.assertEqual(metadata._guardian_review("Souad Massi", "O Houria")["source"], "The Guardian")
            params = client.get.call_args_list[1].kwargs["params"]
        self.assertEqual(params["tag"], "tone/albumreview")
        self.assertEqual(params["q"], '"Souad Massi" "O Houria"')
        self.assertNotIn("guardian-artist-tag:v1:souad massi", self.store.data)

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


class OutletCacheTests(StoreCase):
    """Each outlet's answer is stored on its own, so only an unanswered outlet is asked again."""

    def sources(self, **env):
        with patch.dict(os.environ, {"GUARDIAN_API_KEY": "", **env}):
            return metadata._review_sources("Opeth", "Watershed")

    def run_sources(self, sources):
        return [source() for source in sources]

    def test_without_a_guardian_key_the_guardian_is_not_asked_or_stored(self):
        with patch.object(metadata, "_pitchfork_review", return_value=None), \
                patch.object(metadata, "_wordpress_review", return_value=None), \
                patch.object(metadata, "_guardian_review") as guardian:
            self.run_sources(self.sources())
            self.run_sources(self.sources(GUARDIAN_API_KEY="k"))
        self.assertEqual(guardian.call_count, 1, "only the run with a key asked the Guardian")
        self.assertEqual(sum("The Guardian" in key for key in self.store.data), 1)

    def test_a_found_review_and_a_miss_are_not_asked_again_after_a_restart(self):
        found = review("Pitchfork")
        with patch.object(metadata, "_pitchfork_review", return_value=found) as pitchfork, \
                patch.object(metadata, "_wordpress_review", return_value=None) as wordpress:
            self.run_sources(self.sources())
            clear_caches()
            self.assertEqual(self.run_sources(self.sources())[0], found)
        self.assertEqual(pitchfork.call_count, 1)
        self.assertEqual(wordpress.call_count, len(metadata._WORDPRESS_REVIEW_SITES))

    def test_a_failed_outlet_is_asked_again_but_the_ones_that_answered_are_not(self):
        with patch.object(metadata, "_pitchfork_review", side_effect=[RuntimeError("down"), review("Pitchfork")]) as pitchfork, \
                patch.object(metadata, "_wordpress_review", return_value=None) as wordpress:
            first = self.sources()
            results = []
            for source in first:
                try:
                    results.append(source())
                except RuntimeError:
                    results.append("failed")
            self.assertEqual(results[0], "failed")
            self.run_sources(self.sources())
        self.assertEqual(pitchfork.call_count, 2)
        self.assertEqual(wordpress.call_count, len(metadata._WORDPRESS_REVIEW_SITES), "answered outlets are not re-asked")

    def test_a_miss_is_asked_again_after_three_days_but_a_review_is_kept_for_a_month(self):
        now = [1_000_000.0]
        with patch.object(metadata.time, "time", lambda: now[0]), \
                patch.object(metadata, "_pitchfork_review", return_value=None) as pitchfork, \
                patch.object(metadata, "_wordpress_review", return_value=None):
            self.run_sources(self.sources())
            now[0] += metadata._SOURCE_MISS_TTL - 60
            self.run_sources(self.sources())
            self.assertEqual(pitchfork.call_count, 1)
            now[0] += 120
            self.run_sources(self.sources())
            self.assertEqual(pitchfork.call_count, 2)
        found = review("Pitchfork")
        self.store.data.clear()
        with patch.object(metadata.time, "time", lambda: now[0]), \
                patch.object(metadata, "_pitchfork_review", return_value=found) as pitchfork, \
                patch.object(metadata, "_wordpress_review", return_value=None):
            self.run_sources(self.sources())
            now[0] += metadata._SOURCE_MISS_TTL * 5
            self.assertEqual(self.run_sources(self.sources())[0], found)
        self.assertEqual(pitchfork.call_count, 1)

    def test_an_album_nobody_reviewed_is_remembered_across_a_restart_without_asking_any_outlet(self):
        with patch.dict(os.environ, {"GUARDIAN_API_KEY": ""}), \
                patch.object(metadata, "_pitchfork_review", return_value=None) as pitchfork, \
                patch.object(metadata, "_wordpress_review", return_value=None) as wordpress:
            self.assertEqual(metadata.album_reviews_for("Opeth", "Watershed"), {"reviews": []})
            clear_caches()
            self.assertEqual(metadata.album_reviews_for("Opeth", "Watershed"), {"reviews": []})
        self.assertEqual(pitchfork.call_count, 1)
        self.assertEqual(wordpress.call_count, len(metadata._WORDPRESS_REVIEW_SITES))


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
