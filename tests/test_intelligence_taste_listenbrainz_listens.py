"""ListenBrainz listens reader for the taste refresh. Fake get, no network."""
import unittest
from unittest import mock

from intelligence.taste.listenbrainz_listens import listenbrainz_reader

NOW = 100_000_000


class Resp:
    def __init__(self, listens, status=200):
        self._l, self.status = listens, status

    def raise_for_status(self):
        if self.status != 200:
            raise RuntimeError("http")

    def json(self):
        return {"payload": {"listens": self._l}}


def fake_get(listens, fail=lambda params: False):
    calls = []

    def get(url, params, headers, timeout):
        calls.append((url, dict(params), dict(headers)))
        if fail(params):
            return Resp([], 500)
        page = [x for x in listens if x["listened_at"] <= params["max_ts"]][:params["count"]]
        return Resp(page)
    get.calls = calls
    return get


class ReaderTests(unittest.TestCase):
    def read(self, get):
        return listenbrainz_reader("someone", get=get, headers={"User-Agent": "t"}, clock=lambda: NOW,
                                   pause=lambda s: None)()

    def test_returns_whole_history_across_year_windows(self):
        listens = [{"listened_at": NOW - d * 86400, "track_metadata": {}} for d in (1, 400, 800, 3000)]
        get = fake_get(listens)
        out = self.read(get)
        self.assertEqual(sorted(x["listened_at"] for x in out), sorted(x["listened_at"] for x in listens))
        self.assertTrue(all("/user/someone/listens" in c[0] for c in get.calls))
        self.assertTrue(all(c[2] == {"User-Agent": "t"} for c in get.calls))

    def test_unanswered_window_fails_instead_of_returning_a_gap(self):
        listens = [{"listened_at": NOW - 86400, "track_metadata": {}}]
        with self.assertRaises(RuntimeError):
            self.read(fake_get(listens, fail=lambda p: p["max_ts"] < NOW - 400 * 86400))

    def test_page_capped_window_fails_instead_of_returning_partial_history(self):
        capped = {"listens": [{"listened_at": NOW, "track_metadata": {}}],
                  "windows": [{"source": "listenbrainz", "count": 5000, "truncated": True}],
                  "unanswered": 0, "stopped": "floor_reached"}
        with mock.patch("intelligence.taste.listenbrainz_listens.history_fetch.fetch_lens_history",
                        return_value=capped):
            with self.assertRaisesRegex(RuntimeError, "page limit"):
                self.read(fake_get([]))

    def test_all_windows_failing_raises(self):
        with self.assertRaises(RuntimeError):
            self.read(fake_get([], fail=lambda p: True))


if __name__ == "__main__":
    unittest.main()
