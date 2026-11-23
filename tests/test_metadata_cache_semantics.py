"""Characterization of the eight metadata route caches: memory TTLs, what is stored, and what is not cached.

Written against the hand-rolled dict caches before efficiency P4 moved them onto
`app.services.layered_cache`, and kept unchanged afterwards, so both versions answer the same way.
"""
import contextlib
import threading
import unittest
from unittest.mock import patch

from app.api import metadata
from app.services import album_page_sources, persistent_metadata

HOUR = 60 * 60
DAY = 24 * HOUR


class _Store:
    def __init__(self):
        self.data = {}
        self.reads = []

    def get(self, key, ttl_seconds):
        self.reads.append((key, ttl_seconds))
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value


class _Clock:
    """One clock for the route module and for the cache helper, whichever owns the TTL check."""

    def __init__(self):
        self.now = 1000.0

    @contextlib.contextmanager
    def patched(self):
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(album_page_sources, "monotonic", lambda: self.now))
            try:
                from app.services import layered_cache
            except ImportError:
                layered_cache = None
            if layered_cache is not None:
                stack.enter_context(patch.object(layered_cache, "monotonic", lambda: self.now))
            yield


class _Resp:
    def __init__(self, payload=None, status_code=200, text=""):
        self._payload, self.status_code, self.text = payload, status_code, text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("provider error")

    def json(self):
        return self._payload


def _clear_all():
    for cache in (metadata._artist_bio_cache, metadata._artwork_cache, metadata._album_details_cache,
                  metadata._artist_image_cache, metadata._album_links_cache, metadata._apple_url_cache,
                  metadata._album_description_cache, metadata._review_cache):
        cache.clear()


class _Case(unittest.TestCase):
    attach_store = True

    def setUp(self):
        self.store = _Store()
        if self.attach_store:
            persistent_metadata.attach(self.store.get, self.store.set)
        else:
            persistent_metadata.detach()
        self.addCleanup(persistent_metadata.detach)
        _clear_all()
        self.addCleanup(_clear_all)
        self.clock = _Clock()
        clock = self.clock.patched()
        clock.__enter__()
        self.addCleanup(clock.__exit__, None, None, None)


class AppleUrlTests(_Case):
    attach_store = False

    def test_a_miss_is_not_kept_and_a_found_page_is_kept_for_an_hour(self):
        answers = {"results": []}
        with patch.object(metadata, "_json_or_none", side_effect=lambda *a, **k: answers) as ask:
            self.assertIsNone(metadata._apple_album_url("A", "B"))
            self.assertIsNone(metadata._apple_album_url("A", "B"))
            self.assertEqual(ask.call_count, 2)
            answers = {"results": [{"artistName": "A", "collectionName": "B",
                                    "collectionViewUrl": "https://music.apple.com/us/album/b/1"}]}
            self.assertEqual(metadata._apple_album_url("A", "B"), "https://music.apple.com/us/album/b/1")
            self.clock.now += HOUR - 1
            metadata._apple_album_url("A", "B")
            self.assertEqual(ask.call_count, 3)
            self.clock.now += 2
            metadata._apple_album_url("A", "B")
            self.assertEqual(ask.call_count, 4)


class AppleUrlStoreTests(_Case):
    def test_a_found_page_is_stored_under_its_key_and_read_with_the_links_ttl(self):
        found = {"results": [{"artistName": "A", "collectionName": "B",
                              "collectionViewUrl": "https://music.apple.com/us/album/b/1"}]}
        with patch.object(metadata, "_json_or_none", return_value=found) as ask:
            metadata._apple_album_url("A", "B")
            self.clock.now += HOUR + 1
            self.assertEqual(metadata._apple_album_url("A", "B"), "https://music.apple.com/us/album/b/1")
        self.assertEqual(ask.call_count, 1)
        self.assertEqual(self.store.data, {"apple-album-url:v1:a:b": "https://music.apple.com/us/album/b/1"})
        self.assertIn(("apple-album-url:v1:a:b", persistent_metadata.LINKS_TTL), self.store.reads)


class AlbumLinksTests(_Case):
    def _links(self, complete):
        def fake(url, **kwargs):
            if "itunes" in url:
                return {"results": [{"artistName": "A", "collectionName": "B",
                                     "collectionViewUrl": "https://music.apple.com/us/album/b/1"}]}
            if "deezer" in url and complete:
                return {"data": [{"id": 7, "title": "B", "artist": {"name": "A"}}]}
            return None
        return fake

    def test_an_incomplete_answer_is_kept_ten_minutes_and_not_stored(self):
        with patch.object(metadata, "_json_or_none", side_effect=self._links(False)) as ask:
            first = metadata.album_page_links(artist="A", album="B", mbid="rg-1")
            calls = ask.call_count
            self.clock.now += 10 * 60 - 1
            self.assertEqual(metadata.album_page_links(artist="A", album="B", mbid="rg-1"), first)
            self.assertEqual(ask.call_count, calls)
            self.clock.now += 2
            metadata.album_page_links(artist="A", album="B", mbid="rg-1")
            self.assertGreater(ask.call_count, calls)
        self.assertNotIn("deezer", first)
        self.assertNotIn("album-links:v1:a|b|rg-1", self.store.data)

    def test_a_complete_answer_is_kept_a_day_and_stored_under_its_key(self):
        with patch.object(metadata, "_json_or_none", side_effect=self._links(True)) as ask:
            first = metadata.album_page_links(artist="A", album="B", mbid="rg-1")
            calls = ask.call_count
            self.clock.now += DAY - 1
            self.assertEqual(metadata.album_page_links(artist="A", album="B", mbid="rg-1"), first)
            self.assertEqual(ask.call_count, calls)
        self.assertEqual(self.store.data["album-links:v1:a|b|rg-1"], first)
        self.assertEqual(set(first), {"apple_music", "deezer", "musicbrainz", "listenbrainz"})

    def test_a_stored_answer_is_read_with_the_links_ttl_and_kept_a_day(self):
        stored = {"deezer": "https://www.deezer.com/album/7"}
        self.store.data["album-links:v1:a|b|"] = stored
        with patch.object(metadata, "_json_or_none") as ask:
            self.assertEqual(metadata.album_page_links(artist="A", album="B"), stored)
            self.store.data.clear()
            self.clock.now += DAY - 1
            self.assertEqual(metadata.album_page_links(artist="A", album="B"), stored)
        ask.assert_not_called()
        self.assertEqual(self.store.reads, [("album-links:v1:a|b|", persistent_metadata.LINKS_TTL)])


class AlbumDescriptionTests(_Case):
    NOTES = {"paragraphs": ["Notes."], "source": "Apple Music", "url": "https://music.apple.com/x"}
    NONE = {"paragraphs": [], "source": "Apple Music", "url": None}

    def test_a_miss_everywhere_is_kept_a_day_and_a_found_one_a_week(self):
        with patch.object(metadata, "_apple_description", return_value=(self.NONE, True)) as apple, \
             patch.object(metadata, "_wikipedia_description", return_value=(None, True)):
            metadata.album_description("A", "B")
            self.clock.now += DAY - 1
            metadata.album_description("A", "B")
            self.assertEqual(apple.call_count, 1)
            self.clock.now += 2
            metadata.album_description("A", "B")
            self.assertEqual(apple.call_count, 2)
        self.assertEqual(self.store.data, {})
        _clear_all()
        with patch.object(metadata, "_apple_description", return_value=(self.NOTES, True)) as apple:
            metadata.album_description("C", "D")
            self.store.data.clear()
            self.clock.now += 7 * DAY - 1
            self.assertEqual(metadata.album_description("C", "D"), self.NOTES)
            self.assertEqual(apple.call_count, 1)
            self.clock.now += 2
            metadata.album_description("C", "D")
            self.assertEqual(apple.call_count, 2)

    def test_a_found_description_is_stored_and_a_stored_empty_one_is_ignored(self):
        self.store.data["album-description:v1:a:b"] = self.NONE
        with patch.object(metadata, "_apple_description", return_value=(self.NOTES, True)) as apple:
            self.assertEqual(metadata.album_description("A", "B"), self.NOTES)
        apple.assert_called_once()
        self.assertEqual(self.store.data["album-description:v1:a:b"], self.NOTES)

    def test_a_failed_source_is_not_kept(self):
        with patch.object(metadata, "_apple_description", return_value=(self.NONE, False)) as apple, \
             patch.object(metadata, "_wikipedia_description", return_value=(None, True)):
            metadata.album_description("A", "B")
            metadata.album_description("A", "B")
        self.assertEqual(apple.call_count, 2)


class ReviewsTests(_Case):
    REVIEW = {"source": "Pitchfork", "quote": "Good.", "url": "https://p/x"}

    def _sources(self, *answers):
        def make(answer):
            def ask():
                if isinstance(answer, Exception):
                    raise answer
                return answer
            return ask
        return [make(answer) for answer in answers]

    def test_a_partial_answer_is_kept_ten_minutes_and_a_full_one_an_hour(self):
        sources = self._sources(self.REVIEW, RuntimeError("down"))
        with patch.object(metadata, "_review_sources", return_value=sources) as asks:
            value = metadata.album_reviews_for("A", "B")
            self.assertTrue(value["retryable"])
            self.clock.now += 10 * 60 - 1
            metadata.album_reviews_for("A", "B")
            self.assertEqual(asks.call_count, 1)
            self.clock.now += 2
            metadata.album_reviews_for("A", "B")
            self.assertEqual(asks.call_count, 2)
        self.assertEqual(self.store.data, {})
        _clear_all()
        with patch.object(metadata, "_review_sources", return_value=self._sources(None, None)) as asks:
            self.assertEqual(metadata.album_reviews_for("A", "B"), {"reviews": []})
            self.clock.now += HOUR - 1
            metadata.album_reviews_for("A", "B")
            self.assertEqual(asks.call_count, 1)
            self.clock.now += 2
            metadata.album_reviews_for("A", "B")
            self.assertEqual(asks.call_count, 2)
        self.assertEqual(self.store.data, {})

    def test_a_full_answer_is_stored_and_a_stored_answer_is_kept_an_hour(self):
        with patch.object(metadata, "_review_sources", return_value=self._sources(self.REVIEW)):
            value = metadata.album_reviews_for("A", "B")
        self.assertEqual(self.store.data["album-reviews:v1:a:b"], value)
        _clear_all()
        with patch.object(metadata, "_review_sources") as asks:
            self.assertEqual(metadata.album_reviews_for("A", "B"), value)
            self.store.data.clear()
            self.clock.now += HOUR - 1
            self.assertEqual(metadata.album_reviews_for("A", "B"), value)
            asks.assert_not_called()
        self.assertIn(("album-reviews:v1:a:b", 7 * DAY), self.store.reads)


class ArtistImageTests(_Case):
    def test_no_match_is_kept_six_hours_and_not_stored_and_a_failure_is_not_kept(self):
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.return_value = _Resp({"data": []})
            self.assertIsNone(metadata.artist_image("Nobody")["artwork_url"])
            self.clock.now += 6 * HOUR - 1
            metadata.artist_image("Nobody")
            self.assertEqual(client.get.call_count, 1)
            self.clock.now += 2
            metadata.artist_image("Nobody")
            self.assertEqual(client.get.call_count, 2)
            client.get.side_effect = RuntimeError("down")
            self.assertTrue(metadata.artist_image("Other")["retryable"])
            self.assertTrue(metadata.artist_image("Other")["retryable"])
            self.assertEqual(client.get.call_count, 4)
        self.assertEqual(self.store.data, {})

    def test_a_found_photo_is_stored_under_its_key(self):
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.return_value = _Resp({"data": [{"name": "Portishead", "picture_xl": "http://x/xl.jpg"}]})
            result = metadata.artist_image("Portishead")
        self.assertEqual(self.store.data["artist-image:v2:portishead"], result)


class AlbumArtworkTests(_Case):
    def test_a_miss_is_kept_five_minutes_and_a_found_cover_six_hours(self):
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.return_value = _Resp({"data": []})
            self.assertIsNone(metadata.album_artwork("", "Nothing")["artwork_url"])
            self.clock.now += 5 * 60 - 1
            metadata.album_artwork("", "Nothing")
            self.assertEqual(client.get.call_count, 1)
            self.clock.now += 2
            metadata.album_artwork("", "Nothing")
            self.assertEqual(client.get.call_count, 2)
        self.assertEqual(self.store.data, {})
        found = {"data": [{"title": "Dummy", "artist": {"name": "Portishead"},
                           "cover_xl": "https://x/c.jpg", "release_date": "1994-08-22"}]}
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.return_value = _Resp(found)
            result = metadata.album_artwork("Portishead", "Dummy")
            self.assertTrue(result["artwork_url"])
            self.store.data.clear()
            self.clock.now += 6 * HOUR - 1
            self.assertEqual(metadata.album_artwork("Portishead", "Dummy"), result)
            self.assertEqual(client.get.call_count, 1)


class AlbumDetailsTests(_Case):
    def test_a_definite_miss_is_kept_an_hour_and_a_full_answer_six_hours(self):
        with patch.object(metadata, "_fetch_album_details") as fetch:
            fetch.return_value = ({"tracks": []}, True)
            metadata.album_details(artist="A", album="B")
            self.clock.now += HOUR - 1
            metadata.album_details(artist="A", album="B")
            self.assertEqual(fetch.call_count, 1)
            self.clock.now += 2
            metadata.album_details(artist="A", album="B")
            self.assertEqual(fetch.call_count, 2)
            self.assertEqual(self.store.data, {})
            full = {"tracks": [{"title": "T"}]}
            fetch.return_value = (full, False)
            metadata.album_details(artist="C", album="D")
            self.assertEqual(self.store.data, {"album-details:v1:c:d": full})
            self.store.data.clear()
            self.clock.now += 6 * HOUR - 1
            self.assertEqual(metadata.album_details(artist="C", album="D"), full)
            self.assertEqual(fetch.call_count, 3)


class ArtistBioTests(_Case):
    def test_a_found_bio_is_kept_a_day_and_stored_under_its_key(self):
        with patch.object(metadata.apple_artist_bio, "lookup_artist_biography", return_value=(None, True)), \
             patch.object(metadata, "_load_wikipedia_artist_bio", return_value=("A band.", True, "wikipedia")) as wikipedia:
            metadata.artist_bio("Portishead")
            expected = {"bio": "A band.", "source": "wikipedia"}
            self.assertEqual(self.store.data, {"artist-bio:v3:portishead": expected})
            self.store.data.clear()  # Isolate the one-day memory TTL from the longer persistent TTL.
            self.clock.now += DAY - 1
            self.assertEqual(metadata.artist_bio("Portishead")["bio"], "A band.")
            wikipedia.assert_called_once()
            self.clock.now += 2
            metadata.artist_bio("Portishead")
            self.assertEqual(wikipedia.call_count, 2)
        self.assertEqual(self.store.reads[-1], ("artist-bio:v3:portishead", persistent_metadata.FOUND_TTL))

    def test_full_bio_release_ignores_persisted_v2_wikipedia_summary(self):
        self.store.data["artist-bio:v2:portishead"] = {
            "bio": "Short Wikipedia summary.", "source": "wikipedia",
        }
        with patch.object(metadata.apple_artist_bio, "lookup_artist_biography",
                          return_value=("Full Apple Music biography.", True)) as apple, \
             patch.object(metadata, "_load_wikipedia_artist_bio") as wikipedia:
            result = metadata.artist_bio("Portishead")

        self.assertEqual(result["bio"], "Full Apple Music biography.")
        self.assertEqual(result["source"], "apple_music")
        apple.assert_called_once()
        wikipedia.assert_not_called()
        self.assertEqual(self.store.data["artist-bio:v2:portishead"]["bio"], "Short Wikipedia summary.")
        self.assertEqual(self.store.data["artist-bio:v3:portishead"], {
            "bio": "Full Apple Music biography.", "source": "apple_music",
        })
        self.assertEqual(self.store.reads[-1], ("artist-bio:v3:portishead", persistent_metadata.FOUND_TTL))

    def test_the_route_keeps_a_navidrome_bio_in_memory_only_after_external_misses(self):
        with patch.object(metadata.apple_artist_bio, "lookup_artist_biography", return_value=(None, True)), \
             patch.object(metadata, "_load_wikipedia_artist_bio", return_value=("", True, "wikidata")), \
             patch.object(metadata, "_navidrome_artist_bio", return_value="From the library.") as local:
            result = metadata.artist_bio_route("Artist", object())
            self.assertEqual(result["bio"], "From the library.")
            self.assertEqual(result["source"], "navidrome")
        local.assert_called_once()
        self.assertEqual(self.store.data, {})


class ConcurrentRequestTests(_Case):
    def test_identical_concurrent_requests_make_one_provider_call(self):
        """Efficiency P4: the second request waits for the first one's answer instead of asking again."""
        from app.services import layered_cache

        arrived = threading.Semaphore(0)

        class Done(threading.Event):
            def wait(self, timeout=None):
                arrived.release()
                return super().wait(timeout)

        class Flight(layered_cache._Flight):
            def __init__(self):
                super().__init__()
                self.done = Done()

        started, release = threading.Event(), threading.Event()
        calls, results = [], []

        def get(url):
            calls.append(url)
            started.set()
            release.wait(5)
            raise RuntimeError("down")  # a failure is not cached, so only single-flight can share it

        with patch.object(layered_cache, "_Flight", Flight), patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.side_effect = get
            first = threading.Thread(target=lambda: results.append(metadata.artist_image("Portishead")))
            first.start()
            self.assertTrue(started.wait(5))
            second = threading.Thread(target=lambda: results.append(metadata.artist_image("Portishead")))
            second.start()
            self.assertTrue(arrived.acquire(timeout=5))
            release.set()
            first.join(5)
            second.join(5)
            self.assertEqual(len(calls), 1)
            self.assertEqual([r["retryable"] for r in results], [True, True])
            metadata.artist_image("Portishead")
            self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
