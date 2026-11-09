"""ListenBrainz listens reader for the taste refresh. Fake get, no network."""
import unittest

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

    def test_failed_batch_fails_instead_of_returning_a_gap(self):
        listens = [{"listened_at": NOW - 86400 * d, "track_metadata": {"track_name": str(d)}} for d in (1, 2)]
        with self.assertRaises(RuntimeError):
            self.read(fake_get(listens, fail=lambda p: p["max_ts"] < NOW - 86400 // 2))

    def test_heavy_history_is_read_in_full_in_large_batches(self):
        listens = [{"listened_at": NOW - i * 60, "track_metadata": {"track_name": str(i)}} for i in range(12_345)]
        listens += [{"listened_at": NOW - 3000 * 86400 - i, "track_metadata": {"track_name": f"old{i}"}} for i in range(50)]
        get = fake_get(listens)
        out = self.read(get)
        self.assertEqual(len(out), len(listens))
        self.assertTrue(all(c[1]["count"] == 1000 for c in get.calls))
        self.assertLess(len(get.calls), 20)

    def test_all_windows_failing_raises(self):
        with self.assertRaises(RuntimeError):
            self.read(fake_get([], fail=lambda p: True))


if __name__ == "__main__":
    unittest.main()
