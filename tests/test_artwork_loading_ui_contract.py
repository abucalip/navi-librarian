"""Contract tests for how the page schedules artwork and bio requests."""
import re
import unittest

with open("static/app.js", encoding="utf-8") as handle:
    JS = handle.read()


class BioRequestLimitTests(unittest.TestCase):
    def test_bio_requests_go_through_one_limited_queue(self):
        self.assertIn("const BIO_CONCURRENCY = 2;", JS)
        self.assertNotIn("cachedJSONRequest(artistBioRequests", JS)
        self.assertEqual(len(re.findall(r"cachedBioRequest\(bioKey, artist", JS)), 3)

    def test_the_album_dialog_bio_jumps_the_queue(self):
        dialog = JS[JS.index("function loadAlbumModalBio"):]
        self.assertIn("cachedBioRequest(bioKey, artist, true)", dialog.split("async function openAlbumModal")[0])
        self.assertIn("bioQueue.unshift(start)", JS)

    def test_a_failed_bio_is_dropped_from_the_cache_and_frees_its_slot(self):
        body = JS[JS.index("function cachedBioRequest"):JS.index("const artistBioObserver")]
        self.assertIn("bioInFlight -= 1;", body)
        self.assertIn("artistBioRequests.delete(key)", body)


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
