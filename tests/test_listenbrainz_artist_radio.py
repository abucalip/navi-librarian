from concurrent.futures import ThreadPoolExecutor
from threading import Event

import httpx
import pytest

from integrations.listenbrainz.artist_radio import TTL, top_recordings
from test_artist_radio import mbid


class Limiter:
    def __init__(self):
        self.calls = []
        self.allowed = True

    def admit(self, source, remaining):
        self.calls.append((source, remaining))
        return self.allowed


def harness(get):
    cache = {}
    limiter = Limiter()
    return cache, limiter, dict(read=cache.get, write=cache.__setitem__, headers={"User-Agent": "test"},
                               limiter=limiter, remaining=lambda: 5, get=get)


def response(body, status=200):
    return httpx.Response(status, json=body, request=httpx.Request("GET", "https://example.test"))


def rows():
    return [{"recording_mbid": mbid(1), "recording_name": "Song", "artist_name": "Artist",
             "release_name": "Album", "length": 180000}]


def test_full_ranked_response_cached_for_thirty_days_and_empty_for_one_hour():
    calls = []
    cache, limiter, kwargs = harness(lambda url, **kw: calls.append((url, kw)) or response(rows() * 319))
    assert len(top_recordings(mbid(0), **kwargs)) == 319
    assert len(top_recordings(mbid(0), **kwargs)) == 319
    assert len(calls) == len(limiter.calls) == 1
    assert calls[0][1]["follow_redirects"] is False
    assert calls[0][1]["timeout"] <= 4
    kwargs["get"] = lambda *a, **k: response([])
    assert top_recordings(mbid(2), **kwargs) == []
    kwargs["get"] = lambda *a, **k: pytest.fail("cached empty response fetched twice")
    assert top_recordings(mbid(2), **kwargs) == []
    assert TTL == 30 * 86400
    assert len(cache) == 2


@pytest.mark.parametrize("body,status", [({}, 200), ([{}], 200), (rows(), 401), (rows(), 429), (rows(), 503)])
def test_errors_and_malformed_responses_never_poison_cache(body, status):
    cache, _, kwargs = harness(lambda *a, **k: response(body, status))
    assert top_recordings(mbid(0), **kwargs) is None
    assert not cache


def test_timeout_and_pacing_refusal_are_clean():
    def timeout(*args, **kwargs):
        raise httpx.ReadTimeout("fixture")
    cache, limiter, kwargs = harness(timeout)
    assert top_recordings(mbid(0), **kwargs) is None
    limiter.allowed = False
    kwargs["get"] = lambda *a, **k: pytest.fail("request after pacing refusal")
    assert top_recordings(mbid(0), **kwargs) is None
    assert not cache


def test_concurrent_requests_share_one_successful_fetch():
    entered, release = Event(), Event()
    calls = []

    def get(*args, **kwargs):
        calls.append(1)
        entered.set()
        assert release.wait(5)
        return response(rows())

    _, _, kwargs = harness(get)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(top_recordings, mbid(0), **kwargs)
        assert entered.wait(5)
        second = pool.submit(top_recordings, mbid(0), **kwargs)
        release.set()
        assert first.result(5) == second.result(5)
    assert len(calls) == 1


def test_expired_positive_and_negative_entries_are_refetched():
    import time
    from integrations.listenbrainz.artist_radio import TTL

    calls = []
    cache, _, kwargs = harness(lambda *a, **k: calls.append(1) or response(rows()))
    key = f"lb:popularity:top-recordings:v1:{mbid(0)}"
    for results, age in ((rows(), TTL + 1), ([], 3601)):
        cache[key] = {"at": time.time() - age, "results": results}
        assert top_recordings(mbid(0), **kwargs)[0]["title"] == "Song"
    assert len(calls) == 2


def test_exhausted_budget_never_calls_provider():
    cache, limiter, kwargs = harness(lambda *a, **k: pytest.fail("request after deadline"))
    kwargs["remaining"] = lambda: -1
    assert top_recordings(mbid(0), **kwargs) is None
    assert not cache and not limiter.calls
