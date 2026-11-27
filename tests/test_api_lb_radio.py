"""Authenticated discovery mix contract with the real provider adapter and matcher."""

from contextlib import closing
from dataclasses import replace
from types import SimpleNamespace
from uuid import UUID

from fastapi.testclient import TestClient
import pytest

from app import main
from app.api import lb_radio
from app.api.dependencies import get_librarian
from discovery.lb_radio import radio_seed
from discovery.search.index import IndexView, OwnedData
from integrations.listenbrainz import discovery_mix as mix
from test_api_playlist_inbox import FakeLibrarian, sign_in
from test_listenbrainz_discovery_mix import MBID, Limiter, response

URL = '/api/discovery/lb-radio'


@pytest.fixture
def radio(tmp_path, monkeypatch):
    librarian = FakeLibrarian(tmp_path)
    librarian.settings.update(listenbrainz_username='owner', listenbrainz_token='fixture-token')
    cache, calls = {}, []
    librarian._discovery_read_list = lambda key: {'payload': cache[key]} if key in cache else None
    librarian._discovery_write_list = cache.__setitem__
    owned = OwnedData(None, 1, (), (), (
        {'id': 'owned', 'name': 'Owned', 'artist': 'Artist', 'album': 'Album', 'recording_mbid': MBID},
        {'id': 'live', 'name': 'Versions (Live)', 'artist': 'Artist', 'album': 'Album'},
    ))
    view = SimpleNamespace(value=IndexView('fresh', owned, None))
    upstream = SimpleNamespace(value=response())
    monkeypatch.setattr(lb_radio, '_CLIENT', mix.MixClient())
    monkeypatch.setattr(lb_radio, 'LIMITER', Limiter())
    monkeypatch.setattr(mix.httpx, 'get', lambda *a, **k: calls.append(k) or upstream.value)
    monkeypatch.setattr(lb_radio, 'owned_view', lambda _: view.value)
    monkeypatch.delenv('LISTENBRAINZ_TOKEN', raising=False)
    monkeypatch.setattr(main, 'get_librarian', lambda: librarian)
    monkeypatch.setattr(main, '_AUTH_SECRET', b'mix-test-signing-secret')
    monkeypatch.setitem(main.app.dependency_overrides, get_librarian, lambda: librarian)
    with closing(TestClient(main.app, follow_redirects=False)) as client:
        yield SimpleNamespace(client=client, librarian=librarian, cache=cache, calls=calls, view=view, upstream=upstream)


def test_auth_and_seed_validation_do_no_work(radio):
    assert radio.client.get(URL, params={'tag': 'jazz'}).status_code == 401
    sign_in(radio.client)
    for params in ({}, {'tag': 'jazz', 'artist_mbid': MBID}, {'artist_mbid': 'invalid'}, {'tag': ''},
                   {'tag': ' '}, {'tag': 'x' * 81}, {'tag': 'jazz)::hard artist:(x'},
                   {'tag': 'jazz,rock'}, {'tag': 'jazz\nrock'}, {'tag': 'jazz', 'mode': 'wrong'}):
        assert radio.client.get(URL, params=params).status_code == 422
    assert not radio.calls and not radio.cache


@pytest.mark.parametrize('mode', ['easy', 'medium', 'hard'])
def test_full_list_order_repeats_and_matching(radio, mode):
    sign_in(radio.client)
    result = radio.client.get(URL, params={'artist_mbid': MBID.upper(), 'mode': mode})
    body = result.json()
    assert result.status_code == 200 and result.headers['cache-control'] == 'no-store'
    assert body['state'] == 'ready' and body['index_state'] == 'fresh'
    assert body['seed'] == {'kind': 'artist', 'value': MBID}
    assert body['mode'] == mode and body['total_count'] == 5 and body['owned_count'] == 2
    assert [t['position'] for t in body['tracks']] == list(range(5))
    assert [t['match_state'] for t in body['tracks']] == ['owned', 'missing', 'ambiguous', 'owned', 'missing']
    assert [t['song_id'] for t in body['tracks']] == ['owned', None, None, 'owned', None]
    assert body['tracks'][4]['album'] is None
    assert body['tracks'][0]['duration_ms'] == 180000
    assert radio.calls[0]['params'] == {'prompt': f'artist:({MBID})', 'mode': mode}
    assert 'fixture-token' not in result.text


def test_ownership_rechecked_on_cache_hit_and_unknown_is_not_missing(radio):
    sign_in(radio.client)
    def fetch():
        return radio.client.get(URL, params={'tag': '  JAZZ  '}).json()
    assert fetch()['owned_count'] == 2
    data = radio.view.value.data
    radio.view.value = IndexView('fresh', replace(data, songs=(*data.songs,
        {'id': 'imported', 'name': 'Missing', 'artist': 'Artist', 'album': 'Album'})), None)
    assert fetch()['owned_count'] == 3
    radio.view.value = IndexView('building', None, None)
    body = fetch()
    assert body['state'] == 'ready' and body['total_count'] == 5
    assert body['owned_count'] is None and all(t['match_state'] is None for t in body['tracks'])
    radio.view.value = IndexView('stale', replace(data, songs=()), None)
    body = fetch()
    assert body['index_state'] == 'stale' and body['owned_count'] == 0 and body['total_count'] == 5
    assert len(radio.calls) == 1 and len(radio.cache) == 1


def test_unconfigured_empty_and_environment_token(radio, monkeypatch):
    sign_in(radio.client)
    settings = radio.librarian.settings
    for values in ({}, {'listenbrainz_username': 'owner'}, {'listenbrainz_token': 'fixture'}):
        settings.pop("listenbrainz_username", None)
        settings.pop("listenbrainz_token", None)
        settings.update(values)
        body = radio.client.get(URL, params={'tag': 'jazz'}).json()
        assert body['state'] == 'unconfigured' and body['index_state'] is None and not body['tracks']
    assert not radio.calls
    settings.pop("listenbrainz_token", None)
    settings['listenbrainz_username'] = 'owner'
    monkeypatch.setenv('LISTENBRAINZ_TOKEN', 'environment-fixture')
    radio.upstream.value = response({'payload': {'jspf': {'playlist': {'track': []}}}})
    result = radio.client.get(URL, params={'tag': 'jazz'})
    assert result.json()['state'] == 'empty' and result.json()['total_count'] == 0
    assert radio.calls[0]['headers']['Authorization'] == 'Token environment-fixture'


@pytest.mark.parametrize('code,status', [('rate_limited', 429), ('timeout', 504), ('upstream_error', 502),
                                        ('busy', 503), ('unavailable', 503)])
def test_clean_error_contract(radio, monkeypatch, code, status):
    sign_in(radio.client)
    def fail(**kw):
        raise mix.MixError(code)
    monkeypatch.setattr(lb_radio._CLIENT, 'fetch', fail)
    result = radio.client.get(URL, params={'tag': 'jazz'})
    assert result.status_code == status and result.json()['state'] == code
    assert not result.json()['tracks'] and result.json()['owned_count'] is None
    assert result.headers['cache-control'] == 'no-store'
    if code in ('rate_limited', 'busy'):
        assert result.headers['retry-after'] == '2'
    assert 'fixture-token' not in result.text


def test_unicode_tag_and_canonical_artist_prompt():
    assert radio_seed(None, '  A\u0301MBIENT   folk ')[0]['value'] == 'ámbient folk'
    assert radio_seed(None, '日本のジャズ')[1] == 'tag:(日本のジャズ)'
    assert radio_seed(UUID(MBID), None)[1] == f'artist:({MBID})'
