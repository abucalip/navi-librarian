"""Contract tests for how the page schedules artwork and bio requests."""
import re
import unittest

with open("static/app.js", encoding="utf-8") as handle:
    JS = handle.read()


class RequestQueueTests(unittest.TestCase):
    def test_bio_requests_go_through_a_two_at_a_time_queue(self):
        self.assertIn("const bioQueue = createRequestQueue(2);", JS)
        self.assertNotIn("cachedJSONRequest(artistBioRequests", JS)
        self.assertEqual(len(re.findall(r"cachedBioRequest\(bioKey, artist", JS)), 3)

    def test_the_album_dialog_bio_jumps_the_queue(self):
        dialog = JS[JS.index("function loadAlbumModalBio"):].split("async function openAlbumModal")[0]
        self.assertIn("cachedBioRequest(bioKey, artist, true)", dialog)
        self.assertIn("if (urgent) waiting.unshift(start); else waiting.push(start);", JS)

    def test_a_failed_lookup_frees_its_slot_and_leaves_the_cache(self):
        queue = JS[JS.index("function createRequestQueue"):JS.index("const fetchJSONOrNull")]
        self.assertIn("active -= 1;", queue)
        self.assertIn(".catch(() => null)", queue)
        bio = JS[JS.index("function cachedBioRequest"):JS.index("const artistBioObserver")]
        self.assertIn("artistBioRequests.delete(key)", bio)


class AlbumYearLoadingTests(unittest.TestCase):
    """Deep Dives fired one /api/album-year per card at once, which starved artwork requests."""

    def test_year_lookups_are_sent_in_groups_through_the_batch_endpoint(self):
        self.assertIn("const YEAR_BATCH_SIZE = 15;", JS)
        self.assertIn("sendJSON('/api/album-years', 'POST'", JS)
        self.assertNotIn("/api/album-year?", JS)

    def test_year_requests_run_one_group_at_a_time(self):
        self.assertIn("const yearQueue = createRequestQueue(1);", JS)

    def test_year_lookup_waits_until_the_card_is_near_the_viewport(self):
        card = JS[JS.index("function makeAlbumCardInteractive"):JS.index("// Album years are fetched in groups")]
        self.assertIn("albumYearObserver.observe(card)", card)

    def test_a_year_the_artwork_already_supplied_skips_the_lookup(self):
        flush = JS[JS.index("function flushAlbumYears"):JS.index("function ensureAlbumYearBadge")]
        self.assertIn("if (!item.card.dataset.releaseYear) return true;", flush)

    def test_an_unanswered_album_is_released_so_it_can_retry(self):
        flush = JS[JS.index("function flushAlbumYears"):JS.index("function ensureAlbumYearBadge")]
        self.assertIn("if (!years.has(item.cacheKey)) albumYearRequests.delete(item.cacheKey);", flush)


class LaneArtworkPrefetchTests(unittest.TestCase):
    def test_each_deep_dive_lane_observes_its_own_covers_ahead_of_the_scroll(self):
        self.assertIn("root: track, rootMargin: '0px 700px 0px 700px'", JS)
        self.assertIn("laneArtworkObserver(destination).observe(art)", JS)

    def test_lane_observers_are_released_on_every_render(self):
        body = JS[JS.index("function disconnectGenreRowObservers"):]
        self.assertIn("laneArtworkObservers.clear();", body.split("}\n")[0])


if __name__ == "__main__":
    unittest.main()


class ServerTimingTests(unittest.TestCase):
    def test_api_responses_report_server_time_and_provider_connections_stay_open(self):
        with open("app/main.py", encoding="utf-8") as handle:
            main = handle.read()
        with open("app/api/metadata.py", encoding="utf-8") as handle:
            metadata = handle.read()
        self.assertIn('response.headers["Server-Timing"]', main)
        self.assertIn('request.url.path.startswith("/api/")', main)
        self.assertIn("keepalive_expiry=60.0", metadata)
