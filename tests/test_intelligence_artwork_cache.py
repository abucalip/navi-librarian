import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from intelligence.artwork import ArtworkFetchers, ArtworkService, ArtworkStore, HostPacer
from intelligence.artwork.fetchers import MAX_IMAGE_BYTES, image_url, sniff_image
from intelligence.artwork.index import EMPTY, OK, UNAVAILABLE, ReleaseIndex
from intelligence.artwork.store import TTL_EMPTY, TTL_ERROR_FIRST, TTL_ERROR_REPEAT, TTL_OK

RG = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
R1 = "11111111-0000-0000-0000-000000000001"
R2 = "22222222-0000-0000-0000-000000000002"
JPEG = b"\xff\xd8\xff\xe0" + b"x" * 100
PNG = b"\x89PNG\r\n\x1a\n" + b"y" * 50


class Clock:
    t = 1000.0

    def now(self):
        return self.t


def image(i, types=("Front",), ext="jpg", approved=True):
    return {"id": i, "types": list(types), "approved": approved, "comment": "", "image": f"http://x/release/r/{i}.{ext}"}


def make_store(tmp, budget=10_000, clock=None):
    clock = clock or Clock()
    return ArtworkStore(Path(tmp), budget=budget, clock=clock.now, rng=lambda: 0.0), clock


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_ttls_and_error_ladder_never_become_empty(self):
        store, clock = make_store(self.tmp.name)
        store.put_release(R1, ReleaseIndex(OK, (image(1),)))
        store.put_release(R2, ReleaseIndex(EMPTY))
        clock.t += TTL_EMPTY + 1
        self.assertIsNone(store.get_release(R2))
        self.assertEqual(store.get_release(R1).state, OK)
        clock.t += TTL_OK
        self.assertIsNone(store.get_release(R1))
        self.assertEqual(store.get_release(R1, fresh_only=False).state, OK)   # stale is still readable
        store.put_release("r3", ReleaseIndex(UNAVAILABLE))
        clock.t += TTL_ERROR_FIRST - 1
        self.assertEqual(store.get_release("r3").state, UNAVAILABLE)
        clock.t += 2
        self.assertIsNone(store.get_release("r3"))
        store.put_release("r3", ReleaseIndex(UNAVAILABLE))                    # second failure in a row
        clock.t += TTL_ERROR_FIRST + 1
        self.assertEqual(store.get_release("r3").state, UNAVAILABLE)
        clock.t += TTL_ERROR_REPEAT
        self.assertIsNone(store.get_release("r3"))

    def test_image_refs_keep_the_original_extension(self):
        store, _ = make_store(self.tmp.name)
        store.put_release(R1, ReleaseIndex(OK, (image(7, ext="png"), {"id": 8})))
        self.assertEqual(store.image_refs(7), [(R1, "png")])
        self.assertEqual(store.image_refs(8), [(R1, "jpg")])
        store.put_release(R2, ReleaseIndex(OK, (image(9, ext="pdf"),)))
        self.assertEqual(store.image_refs(9), [(R2, "pdf")])

    def test_eviction_drops_full_first_then_least_recent_and_keeps_protected(self):
        store, clock = make_store(self.tmp.name, budget=1000)
        store.protect([1])
        for i, size in ((1, "thumb"), (2, "thumb"), (3, "full"), (4, "display")):
            clock.t += 1
            self.assertTrue(store.put_file(i, size, "jpg", b"a" * 300))
        # 4 x 300 > 1000: the full file goes first even though it is not the oldest
        self.assertIsNone(store.get_file(3, "full"))
        self.assertIsNotNone(store.get_file(1, "thumb"))
        clock.t += 1
        store.put_file(5, "thumb", "jpg", b"a" * 300)       # 2 (oldest unprotected) goes next
        self.assertIsNone(store.get_file(2, "thumb"))
        self.assertLessEqual(store.total_bytes(), 1000)

    def test_protected_file_goes_only_when_nothing_else_is_left(self):
        store, clock = make_store(self.tmp.name, budget=500)
        store.protect([1])
        store.put_file(1, "thumb", "jpg", b"a" * 400)
        clock.t += 1
        store.put_file(2, "thumb", "jpg", b"b" * 400)       # the new file is kept; only the protected one can go
        self.assertIsNotNone(store.get_file(2, "thumb"))
        self.assertIsNone(store.get_file(1, "thumb"))

    def test_protection_applies_to_sizes_stored_after_the_mark(self):
        store, clock = make_store(self.tmp.name, budget=700)
        store.protect([1])
        store.put_file(1, "display", "jpg", b"a" * 300)
        clock.t += 1
        store.put_file(2, "thumb", "jpg", b"b" * 300)
        clock.t += 1
        store.put_file(3, "thumb", "jpg", b"c" * 300)
        self.assertIsNotNone(store.get_file(1, "display"))
        self.assertIsNone(store.get_file(2, "thumb"))

    def test_file_larger_than_budget_is_not_stored_and_missing_file_is_a_miss(self):
        store, _ = make_store(self.tmp.name, budget=100)
        self.assertFalse(store.put_file(1, "full", "jpg", b"a" * 101))
        self.assertTrue(store.put_file(1, "thumb", "jpg", b"a" * 50))
        (Path(self.tmp.name) / "images" / "1-thumb.jpg").unlink()
        self.assertIsNone(store.get_file(1, "thumb"))
        self.assertEqual(store.total_bytes(), 0)


class FetchImageTests(unittest.TestCase):
    def fetchers(self, response):
        urls = []

        def opener(req, limit):
            urls.append((req.full_url, limit))
            return response

        clock = Clock()
        return ArtworkFetchers(pacer=HostPacer(clock=clock.now, sleep=lambda s: None), image_opener=opener), urls

    def test_sizes_map_to_caa_urls(self):
        self.assertTrue(image_url(R1, 5, "thumb").endswith(f"/release/{R1}/5-250.jpg"))
        self.assertTrue(image_url(R1, 5, "display").endswith("/5-500.jpg"))
        self.assertTrue(image_url(R1, 5, "full", "png").endswith("/5.png"))
        self.assertTrue(image_url(R1, 5, "full", "pdf").endswith("/5.pdf"))
        self.assertTrue(image_url(R1, 5, "full", "exe").endswith("/5.jpg"))       # odd extension falls back
        self.assertIsNone(image_url(R1, 5, "huge"))

    def test_good_bytes_are_ok_and_use_the_size_limit(self):
        f, urls = self.fetchers((200, PNG, None))
        self.assertEqual(f.fetch_image(R1, 5, "full", "png"), ("ok", PNG, "png"))
        self.assertEqual(urls[0][1], MAX_IMAGE_BYTES["full"])

    def test_non_image_bytes_are_rejected(self):
        for body in (b"<html>not an image</html>", b"PK\x03\x04zip", b""):
            f, _ = self.fetchers((200, body, None))
            self.assertEqual(f.fetch_image(R1, 5, "thumb")[0], "missing")

    def test_pdf_original_is_kept_but_never_as_a_thumbnail(self):
        pdf = b"%PDF-1.6\n" + b"p" * 100
        f, urls = self.fetchers((200, pdf, None))
        self.assertEqual(f.fetch_image(R1, 5, "full", "pdf"), ("ok", pdf, "pdf"))
        self.assertTrue(urls[0][0].endswith("/5.pdf"))
        self.assertEqual(f.fetch_image(R1, 5, "thumb")[0], "missing")
        self.assertEqual(sniff_image(pdf), ("application/pdf", "pdf"))

    def test_oversize_is_unavailable_and_404_is_missing(self):
        f, _ = self.fetchers((200, JPEG + b"z" * MAX_IMAGE_BYTES["thumb"], None))
        self.assertEqual(f.fetch_image(R1, 5, "thumb")[0], UNAVAILABLE)
        f, _ = self.fetchers((404, b"", None))
        self.assertEqual(f.fetch_image(R1, 5, "thumb")[0], "missing")

    def test_throttle_closes_the_host(self):
        f, urls = self.fetchers((429, b"", 30.0))
        self.assertEqual(f.fetch_image(R1, 5, "thumb")[0], UNAVAILABLE)
        self.assertEqual(f.fetch_image(R1, 6, "thumb")[0], UNAVAILABLE)
        self.assertEqual(len(urls), 1)

    def test_sniffing_uses_the_signature_only(self):
        self.assertEqual(sniff_image(JPEG)[0], "image/jpeg")
        self.assertEqual(sniff_image(b"RIFF\x00\x00\x00\x00WEBPVP8 ")[0], "image/webp")
        self.assertIsNone(sniff_image(b"GIF"))


class FakeFetchers:
    """Fetch counts and canned answers; the same interface the service uses."""

    def __init__(self):
        self.releases = [{"id": R1, "date": "1999", "country": "JP", "media": [{"format": "CD"}]}]
        self.release_index = {R1: ReleaseIndex(OK, (image(10), image(11, ("Back",))))}
        self.release_calls, self.index_calls, self.image_calls = 0, [], []
        self.image_answer = ("ok", JPEG, "jpg")
        self.gate = None

    def fetch_releases(self, rgid):
        self.release_calls += 1
        return self.releases

    def fetch_release_index(self, release):
        self.index_calls.append(release)
        return self.release_index.get(release, ReleaseIndex(UNAVAILABLE))

    def fetch_image(self, release, image_id, size, ext="jpg"):
        if self.gate:
            self.gate.wait(2)
        self.image_calls.append((release, image_id, size))
        return self.image_answer


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store, self.clock = make_store(self.tmp.name, budget=1_000_000)
        self.fetch = FakeFetchers()
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.addCleanup(self.pool.shutdown)
        self.service = ArtworkService(self.store, self.fetch, executor=self.pool)

    def wait_built(self):
        self.pool.submit(lambda: None).result(5)

    def test_not_loaded_then_ok_and_second_call_does_not_refetch(self):
        self.assertEqual(self.service.index(RG)["status"], "not_loaded")
        self.wait_built()
        body = self.service.index(RG)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["best_front"], 10)
        self.assertEqual(self.fetch.release_calls, 1)
        self.service.index(RG)
        self.assertEqual((self.fetch.release_calls, self.fetch.index_calls), (1, [R1]))

    def test_one_build_per_group_while_one_is_running(self):
        gate = threading.Event()
        self.pool.submit(gate.wait, 2)                     # occupy the single worker
        self.service.index(RG)
        self.service.index(RG)
        self.assertTrue(self.service.building(RG))
        gate.set()
        self.wait_built()
        self.assertEqual(self.fetch.release_calls, 1)

    def test_expired_group_is_served_stale_and_rebuilds_only_stale_releases(self):
        self.service.build_now(RG)
        self.clock.t += TTL_OK * 2
        body = self.service.index(RG)
        self.assertEqual(body["status"], "ok")             # stale, still served
        self.wait_built()
        self.assertEqual(self.fetch.release_calls, 2)
        self.assertEqual(self.fetch.index_calls, [R1, R1])  # the release was stale too

    def test_failed_group_is_unavailable_not_empty_and_is_not_retried_early(self):
        self.fetch.releases = None
        self.service.index(RG)
        self.wait_built()
        self.assertEqual(self.service.index(RG)["status"], "unavailable")
        self.wait_built()
        self.assertEqual(self.fetch.release_calls, 1)       # fresh error row: no new build

    def test_all_404_is_empty_and_release_failure_is_never_empty(self):
        self.fetch.release_index = {R1: ReleaseIndex(EMPTY)}
        self.service.build_now(RG)
        self.assertEqual(self.service.index(RG)["status"], "empty")
        other = "bbbbbbbb-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        self.fetch.release_index = {}
        self.service.build_now(other)
        self.assertEqual(self.service.index(other)["status"], "unavailable")

    def test_owned_release_protects_the_best_front(self):
        self.service.build_now(RG, R1)
        self.service.image(10, "thumb")
        with self.store._lock:
            row = self.store._db.execute("SELECT protected FROM image_file WHERE image_id=10").fetchone()
        self.assertEqual(row[0], 1)

    def test_image_is_fetched_once_then_served_from_disk(self):
        self.service.build_now(RG)
        self.assertEqual(self.service.image(10, "display")[:1], ("ok",))
        state, body, ctype = self.service.image(10, "display")
        self.assertEqual((state, body, ctype), ("ok", JPEG, "image/jpeg"))
        self.assertEqual(len(self.fetch.image_calls), 1)

    def test_concurrent_requests_for_one_image_fetch_once(self):
        self.service.build_now(RG)
        self.fetch.gate = threading.Event()
        results = []
        threads = [threading.Thread(target=lambda: results.append(self.service.image(10, "thumb")[0])) for _ in range(4)]
        for t in threads:
            t.start()
        self.fetch.gate.set()
        for t in threads:
            t.join(5)
        self.assertEqual(results, ["ok"] * 4)
        self.assertEqual(len(self.fetch.image_calls), 1)

    def test_unknown_image_is_not_fetched(self):
        self.assertEqual(self.service.image(999, "thumb")[0], "unknown")
        self.assertEqual(self.fetch.image_calls, [])

    def test_unavailable_image_is_not_stored_and_missing_tries_the_next_release(self):
        self.fetch.releases.append({"id": R2, "date": "2001", "media": []})
        shared = image(10)
        self.fetch.release_index = {R1: ReleaseIndex(OK, (shared,)), R2: ReleaseIndex(OK, (shared,))}
        self.service.build_now(RG)
        answers = [("missing", b"", ""), ("ok", JPEG, "jpg")]
        self.fetch.image_answer = None
        self.fetch.fetch_image = lambda r, i, s, e="jpg": (self.fetch.image_calls.append(r), answers.pop(0))[1]
        self.assertEqual(self.service.image(10, "thumb")[0], "ok")
        self.assertEqual(len(self.fetch.image_calls), 2)
        self.fetch.fetch_image = lambda *a, **k: (UNAVAILABLE, b"", "")
        self.assertEqual(self.service.image(10, "full")[0], UNAVAILABLE)
        self.assertIsNone(self.store.get_file(10, "full"))


if __name__ == "__main__":
    unittest.main()
