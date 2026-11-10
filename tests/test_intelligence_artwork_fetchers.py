import json
import unittest
from urllib.error import HTTPError
from urllib.request import Request

from intelligence.artwork import ArtworkFetchers, HostPacer, build_group_index
from intelligence.artwork.fetchers import _SafeRedirect

RG = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
R1 = "11111111-0000-0000-0000-000000000001"


class Clock:
    def __init__(self):
        self.t = 100.0
        self.slept = []

    def now(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s


def make(responses):
    clock = Clock()
    urls = []

    def opener(req):
        urls.append(req.full_url)
        r = responses.pop(0)
        return r if isinstance(r, tuple) else (200, json.dumps(r).encode(), None)

    return ArtworkFetchers(pacer=HostPacer(clock=clock.now, sleep=clock.sleep), opener=opener), urls, clock


class FetcherTests(unittest.TestCase):
    def test_releases_are_paged_in_one_browse_per_hundred(self):
        page1 = {"release-count": 150, "releases": [{"id": f"a{i}"} for i in range(100)]}
        page2 = {"release-count": 150, "releases": [{"id": f"b{i}"} for i in range(50)]}
        f, urls, _ = make([page1, page2])
        self.assertEqual(len(f.fetch_releases(RG)), 150)
        self.assertEqual(len(urls), 2)
        self.assertIn("inc=media", urls[0])
        self.assertIn("offset=100", urls[1])
        self.assertNotIn("cover-art-archive", urls[0])

    def test_release_browse_failure_is_none(self):
        f, _, _ = make([(500, b"", None)])
        self.assertIsNone(f.fetch_releases(RG))

    def test_caa_ok_empty_and_failure(self):
        f, urls, _ = make([{"images": [{"id": 1}]}, (404, b"", None), (500, b"", None), (200, b"not json", None)])
        first = f.fetch_release_index(R1)
        self.assertEqual((first.state, len(first.images)), ("ok", 1))
        self.assertEqual(f.fetch_release_index(R1).state, "empty")
        self.assertEqual(f.fetch_release_index(R1).state, "unavailable")
        self.assertEqual(f.fetch_release_index(R1).state, "unavailable")
        self.assertTrue(urls[0].endswith(f"/release/{R1}"))

    def test_one_request_per_second_per_host(self):
        f, _, clock = make([{"images": []}, {"images": []}])
        f.fetch_release_index(R1)
        f.fetch_release_index(R1)
        self.assertEqual(len(clock.slept), 1)
        self.assertAlmostEqual(clock.slept[0], 1.0)

    def test_429_closes_the_host_and_is_never_empty(self):
        f, urls, clock = make([(429, b"", 30.0), {"images": [{"id": 1}]}])
        self.assertEqual(f.fetch_release_index(R1).state, "unavailable")
        self.assertEqual(f.fetch_release_index(R1).state, "unavailable")  # closed: no request sent
        self.assertEqual(len(urls), 1)
        clock.t += 31
        self.assertEqual(f.fetch_release_index(R1).state, "ok")

    def test_backoff_doubles_to_a_ceiling_without_retry_after(self):
        pacer = HostPacer(clock=lambda: 0.0, sleep=lambda s: None)
        pacer.throttled("h", None)
        first = pacer._closed_until["h"]
        pacer.throttled("h", None)
        self.assertEqual((first, pacer._closed_until["h"]), (60.0, 120.0))
        for _ in range(10):
            pacer.throttled("h", None)
        self.assertEqual(pacer._closed_until["h"], 900.0)

    def test_redirect_only_to_allowed_hosts(self):
        h = _SafeRedirect()
        req = Request("https://coverartarchive.org/release/x")
        with self.assertRaises(HTTPError):
            h.redirect_request(req, None, 307, "x", {}, "https://evil.example/x.json")
        with self.assertRaises(HTTPError):
            h.redirect_request(req, None, 307, "x", {}, "http://archive.org/x.json")
        self.assertIsNotNone(h.redirect_request(req, None, 307, "x", {}, "https://ia800000.us.archive.org/x.json"))

    def test_plugs_into_build_group_index(self):
        f, _, _ = make([{"release-count": 1, "releases": [{"id": R1, "date": "1999", "country": "JP", "media": [{"format": "CD"}]}]},
                        {"images": [{"id": 7, "types": ["Front"], "approved": True}]}])
        idx = build_group_index(RG, f.fetch_releases, f.fetch_release_index)
        self.assertEqual((idx.status, [e.edition for e in idx.images]), ("ok", ["1999 JP CD"]))


if __name__ == "__main__":
    unittest.main()
