"""Deterministic upstream, cache, pacing and concurrency checks for LB-18."""

from concurrent.futures import Future, ThreadPoolExecutor
from threading import Event
import time

import httpx
import pytest

from integrations.listenbrainz import discovery_mix as mix

MBID = "90000000-0000-4000-8000-000000000001"


def jspf():
    return {"playlist": {"title": "Discovery", "track": [
        {"title": "Owned", "creator": "Artist", "album": "Album", "duration": 180000,
         "identifier": [f"https://musicbrainz.org/recording/{MBID}"]},
        {"title": "Missing", "creator": "Artist", "album": "Album"},
        {"title": "Versions", "creator": "Artist", "album": "Album"},
        {"title": "Owned", "creator": "Artist", "album": "Album", "duration": 180000,
         "identifier": [f"https://musicbrainz.org/recording/{MBID}"]},
        {"title": "Sparse", "creator": "Artist"},
    ]}}


def response(body=None, status=200):
    return httpx.Response(status, json={"payload": {"jspf": jspf()}} if body is None else body,
                          request=httpx.Request("GET", mix.URL))


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
    key = mix.cache_key("tag:(jazz)", "easy", "owner", "secret")
    kwargs = dict(key=key, prompt="tag:(jazz)", mode="easy", read=cache.get, write=cache.__setitem__,
                  headers={"Authorization": "Token secret"}, limiter=limiter, get=get)
    return mix.MixClient(), cache, limiter, kwargs


def test_cache_expiry_empty_expiry_and_request_parameters():
    calls = []
    client, cache, limiter, kw = harness(lambda *a, **k: calls.append((a, k)) or response())
    first = client.fetch(**kw)
    assert client.fetch(**kw) == first
    assert len(first.tracks) == 5
    assert len(calls) == len(limiter.calls) == 1
    args, params = calls[0]
    assert args == (mix.URL,)
    assert params['params'] == {"prompt": "tag:(jazz)", "mode": "easy"}
    assert params['headers'] == kw['headers']
    assert params['follow_redirects'] is False and 0 < params['timeout'] <= 10
    assert "secret" not in kw['key']
    empty = {"payload": {"jspf": {"playlist": {"track": []}}}}
    kw['get'] = lambda *a, **k: calls.append(1) or response(empty)
    cache[kw['key']]['at'] = time.time() - mix.TTL - 1
    assert not client.fetch(**kw).tracks
    assert not client.fetch(**kw).tracks
    assert len(calls) == 2
    cache[kw['key']]['at'] -= mix.TTL + 1
    client.fetch(**kw)
    assert len(calls) == 3


def test_cache_identity_includes_seed_mode_and_credentials():
    base = ["tag:(jazz)", "easy", "owner", "secret"]
    keys = {mix.cache_key(*base)}
    for index, value in enumerate(["tag:(rock)", "hard", "another", "rotated"]):
        args = list(base)
        args[index] = value
        keys.add(mix.cache_key(*args))
    assert len(keys) == 5


@pytest.mark.parametrize('body,status,code', [
    ({}, 200, 'upstream_error'), ({"payload": {"jspf": {"playlist": {"track": [None]}}}}, 200, 'upstream_error'),
    ({"payload": {"jspf": {"playlist": {"track": [{}] * (mix.MAX_TRACKS + 1)}}}}, 200, 'upstream_error'),
    ({}, 401, 'upstream_error'), ({}, 429, 'rate_limited'), ({}, 500, 'upstream_error'),
    ({}, 302, 'upstream_error'),
])
def test_upstream_failures_do_not_poison_cache(body, status, code):
    client, cache, _, kw = harness(lambda *a, **k: response(body, status))
    with pytest.raises(mix.MixError, match=code):
        client.fetch(**kw)
    assert not cache and not client._inflight
    kw['get'] = lambda *a, **k: response()
    assert client.fetch(**kw).tracks


def test_timeout_invalid_json_oversize_and_throttle():
    def timeout(*a, **k):
        raise httpx.ReadTimeout('secret provider error')
    client, cache, limiter, kw = harness(timeout)
    with pytest.raises(mix.MixError, match='timeout'):
        client.fetch(**kw)
    for content in (b'not json', b'x' * (mix.MAX_RESPONSE_BYTES + 1)):
        kw['get'] = lambda *a, **k: httpx.Response(200, content=content, request=httpx.Request('GET', mix.URL))
        with pytest.raises(mix.MixError, match='upstream_error'):
            client.fetch(**kw)
    limiter.allowed = False
    kw['get'] = lambda *a, **k: pytest.fail('request after throttle refusal')
    with pytest.raises(mix.MixError, match='rate_limited'):
        client.fetch(**kw)
    assert not cache


@pytest.mark.parametrize('status', [200, 429, 500])
def test_concurrent_callers_share_successes_and_failures(monkeypatch, status):
    entered, joined, release = Event(), Event(), Event()
    class ObservedFuture(Future):
        def result(self, timeout=None):
            joined.set()
            return super().result(timeout)
    monkeypatch.setattr(mix, 'Future', ObservedFuture)
    calls = []
    def get(*a, **k):
        calls.append(1)
        entered.set()
        assert release.wait(5)
        return response(status=status)
    client, _, limiter, kw = harness(get)
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(client.fetch, **kw)
        assert entered.wait(5)
        second = pool.submit(client.fetch, **kw)
        assert joined.wait(5)
        release.set()
        if status == 200:
            assert first.result(5) == second.result(5)
        else:
            for result in (first, second):
                with pytest.raises(mix.MixError):
                    result.result(5)
    assert len(calls) == len(limiter.calls) == 1
    assert not client._inflight


def test_capacity_deadlines_corrupt_cache_and_store_failure(monkeypatch):
    client, cache, limiter, kw = harness(lambda *a, **k: response())
    monkeypatch.setattr(mix, 'MAX_INFLIGHT', 0)
    with pytest.raises(mix.MixError, match='busy'):
        client.fetch(**kw)
    assert not limiter.calls
    monkeypatch.setattr(mix, 'MAX_INFLIGHT', 16)
    cache[kw['key']] = {"at": time.time(), "jspf": {}}
    client.fetch(**kw)
    cache.clear()
    monkeypatch.setattr(mix, 'REQUEST_BUDGET', 0)
    with pytest.raises(mix.MixError, match='timeout'):
        client.fetch(**kw)
    monkeypatch.setattr(mix, 'REQUEST_BUDGET', 12)
    def fail(*a):
        raise OSError('secret storage path')
    kw['write'] = fail
    with pytest.raises(mix.MixError, match='unavailable'):
        client.fetch(**kw)
    assert not client._inflight and not cache


def test_late_response_is_not_cached_and_real_limiter_refuses_exhausted_slot(monkeypatch):
    from discovery.search.limiter import SourceLimiter
    clock = [0.0]
    monkeypatch.setattr(mix.time, 'monotonic', lambda: clock[0])
    def late(*a, **k):
        clock[0] = mix.REQUEST_BUDGET + 1
        return response()
    client, cache, _, kw = harness(late)
    with pytest.raises(mix.MixError, match='timeout'):
        client.fetch(**kw)
    assert not cache
    clock[0] = 0
    limiter = SourceLimiter({'listenbrainz': 2}, clock=lambda: clock[0],
                            sleep=lambda _: pytest.fail('waiting beyond request budget'))
    assert limiter.admit('listenbrainz', 1)
    kw['limiter'] = limiter
    kw['get'] = lambda *a, **k: pytest.fail('request after slot refusal')
    monkeypatch.setattr(mix, 'REQUEST_BUDGET', 1)
    with pytest.raises(mix.MixError, match='rate_limited'):
        client.fetch(**kw)
    assert not cache


def test_waiter_timeout_does_not_cancel_leader(monkeypatch):
    entered, release = Event(), Event()
    def get(*a, **k):
        entered.set()
        assert release.wait(5)
        return response()
    client, cache, _, kw = harness(get)
    with ThreadPoolExecutor(1) as pool:
        leader = pool.submit(client.fetch, **kw)
        assert entered.wait(5)
        monkeypatch.setattr(mix, 'REQUEST_BUDGET', 0)
        with pytest.raises(mix.MixError, match='timeout'):
            client.fetch(**kw)
        release.set()
        assert leader.result(5).tracks
    assert cache and not client._inflight
