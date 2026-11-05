import unittest

from intelligence.insights import build_set_fetchers, set_builders

A = "11111111-1111-4111-8111-111111111111"


def gid(n):
    return f"00000000-0000-4000-8000-{n:012d}"


class Resp:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self._body = body

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


class Recorder:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, params, headers, timeout))
        return self.responses.pop(0)


def page(start, n, total):
    return {"release-group-count": total, "release-groups": [
        {"id": gid(i), "title": f"A{i}", "primary-type": "Album", "secondary-types": [],
         "first-release-date": "2001"} for i in range(start, start + n)]}


class SetFetcherTests(unittest.TestCase):
    def make(self, *responses, **kw):
        self.get = Recorder(*responses)
        self.sleeps = []
        return build_set_fetchers(self.get, headers={"User-Agent": "t"}, sleep=self.sleeps.append, **kw)

    def test_studio_single_page_and_builder_accepts_it(self):
        f = self.make(Resp(body=page(1, 4, 4)))
        doc = f.studio(A)
        url, params, headers, _ = self.get.calls[0]
        self.assertTrue(url.endswith("/release-group"))
        self.assertEqual((params["artist"], params["type"], params["offset"]), (A, "album", 0))
        self.assertEqual(headers, {"User-Agent": "t"})
        self.assertEqual(self.sleeps, [1.1])
        self.assertEqual(len(set_builders.studio_discography_set(A, "Band", doc).items), 4)

    def test_studio_pages_until_total(self):
        f = self.make(Resp(body=page(1, 100, 130)), Resp(body=page(101, 30, 130)))
        doc = f.studio(A)
        self.assertEqual(len(doc["release-groups"]), 130)
        self.assertEqual([c[1]["offset"] for c in self.get.calls], [0, 100])
        self.assertEqual(self.sleeps, [1.1, 1.1])

    def test_studio_page_cap_is_reported_not_hidden(self):
        f = self.make(Resp(body=page(1, 100, 500)), Resp(body=page(101, 100, 500)), max_pages=2)
        doc = f.studio(A)
        self.assertEqual(len(doc["release-groups"]), 200)
        self.assertEqual(doc["release-group-count"], 500)
        self.assertEqual(len(self.get.calls), 2)

    def test_404_is_none_and_other_status_raises(self):
        self.assertIsNone(self.make(Resp(404)).studio(A))
        self.assertIsNone(self.make(Resp(404)).listenbrainz(A))
        self.assertIsNone(self.make(Resp(404)).series(A))
        for status in (429, 503):
            with self.assertRaises(RuntimeError):
                self.make(Resp(status)).series(A)

    def test_failure_on_later_page_raises(self):
        f = self.make(Resp(body=page(1, 100, 200)), Resp(503))
        with self.assertRaises(RuntimeError):
            f.studio(A)

    def test_transport_error_raises_and_still_sleeps(self):
        def boom(*a, **k):
            raise ConnectionError("down")
        f = build_set_fetchers(boom, headers={}, sleep=(s := []).append)
        with self.assertRaises(ConnectionError):
            f.listenbrainz(A)
        self.assertEqual(s, [0.5])

    def test_listenbrainz_wraps_bare_list(self):
        f = self.make(Resp(body=[{"release_group_mbid": gid(1), "release_group_name": "X"}]))
        doc = f.listenbrainz(A)
        self.assertTrue(self.get.calls[0][0].endswith(f"top-release-groups-for-artist/{A}"))
        self.assertEqual(len(set_builders.listenbrainz_top_set(A, "Band", doc).items), 1)

    def test_listenbrainz_empty_list_is_none(self):
        self.assertIsNone(self.make(Resp(body=[])).listenbrainz(A))

    def test_series_asks_for_release_group_rels(self):
        f = self.make(Resp(body={"id": A, "name": "S", "relations": []}))
        f.series(A)
        url, params, _, _ = self.get.calls[0]
        self.assertTrue(url.endswith(f"/series/{A}"))
        self.assertEqual(params["inc"], "release-group-rels")

    def test_bad_max_pages(self):
        with self.assertRaises(ValueError):
            build_set_fetchers(lambda *a, **k: None, headers={}, max_pages=0)


if __name__ == "__main__":
    unittest.main()
