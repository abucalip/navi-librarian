"""One-time mix saves exercise real Navidrome transport and durable failure recovery."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from threading import Event
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import main
from acquisition.state import save_job
from acquisition.track_service import track_job_album
from app.api import radio_mixes as api
from app.api.dependencies import get_librarian
from discovery import playlist_download, radio_mixes
from discovery.search.index import IndexView, build_owned_data
from integrations.navidrome.playlists import PlaylistProviderError
from intelligence.store import ensure_store, open_writer
from intelligence.store.radio_mixes import get_preview
from test_api_playlist_inbox import FakeLibrarian, job_storage, sign_in
from test_playlist_sync import CONFIG, FIRST, SECOND, Navidrome

URL = '/api/radio-mixes'


def payload(kind='discovery'):
    return {'kind': kind, 'title': 'Discair · Test mix', 'state': 'ready', 'index_state': 'fresh',
            'tracks': [
                {'position': position, 'recording_mbid': mbid, 'title': title, 'artist': 'Band',
                 'album': 'Album', 'duration_ms': 180000, 'match_state': state, 'song_id': song_id}
                for position, mbid, title, state, song_id in (
                    (0, FIRST, 'One', 'owned', 'one'), (1, SECOND, 'Two', 'missing', None),
                    (2, FIRST, 'One', 'owned', 'one'),
                )]}


@pytest.fixture
def mix(tmp_path, monkeypatch):
    librarian = FakeLibrarian(tmp_path)
    path = tmp_path / api.STORE_FILE
    ensure_store(path)
    remote = Navidrome()
    remote.songs = [{'id': 'one', 'title': 'One', 'artist': 'Band', 'album': 'Album',
                     'duration': 180, 'musicBrainzId': FIRST}]
    factory = lambda config: remote.client(config)
    monkeypatch.setattr(radio_mixes, 'PlaylistClient', factory)
    monkeypatch.setattr(playlist_download, 'PlaylistClient', factory)
    monkeypatch.setattr(api, 'PlaylistClient', factory)
    owned = build_owned_data(generation=None, built_at=0, artists=(), albums=(), songs=remote.songs)
    view = SimpleNamespace(value=IndexView('fresh', owned, None))
    monkeypatch.setattr(api, 'owned_view', lambda _: view.value)
    preview_id = radio_mixes.store_preview(path, remote.client(), payload())
    return SimpleNamespace(librarian=librarian, path=path, remote=remote, id=preview_id, view=view)


def save(mix):
    return radio_mixes.save_preview(mix.librarian, mix.path, mix.id)


def test_private_order_repeats_idempotence_and_no_scheduled_link(mix):
    result = save(mix)
    assert result == {'state': 'saved', 'playlist_id': 'playlist-1', 'saved_count': 2}
    row = mix.remote.playlists['playlist-1']
    assert row['entry'] == [{'id': 'one'}, {'id': 'one'}]
    assert row.get('public') is not True
    assert row['name'] == payload()['title']
    with closing(open_writer(mix.path)) as db:
        assert get_preview(db, mix.id, mix.remote.client().target_key)['saved']
        assert db.execute('SELECT COUNT(*) FROM playlist_managed_copies').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM playlist_current_editions').fetchone()[0] == 0
    mix.remote.requests.clear()
    row['name'] = 'Owner edited name'
    row['entry'] = []
    assert save(mix) == result
    assert not mix.remote.requests and not row['entry']


def test_save_rechecks_full_inventory_and_includes_newly_owned_tracks(mix):
    mix.remote.songs.append({'id': 'two', 'title': 'Two', 'musicBrainzId': SECOND})
    assert save(mix)['saved_count'] == 3
    assert mix.remote.playlists['playlist-1']['entry'] == [{'id': 'one'}, {'id': 'two'}, {'id': 'one'}]


def test_zero_unknown_scanning_and_changed_inventory_never_populate(mix):
    mix.remote.scan['scanning'] = True
    with pytest.raises(radio_mixes.MixActionError, match='scanning'):
        save(mix)
    mix.remote.scan['scanning'] = False
    mix.remote.songs = []
    with pytest.raises(radio_mixes.MixActionError, match='no confirmed owned'):
        save(mix)
    mix.remote.songs = [{'title': 'Missing ID'}]
    with pytest.raises(PlaylistProviderError):
        save(mix)
    assert not mix.remote.playlists


def test_scan_change_and_account_change_refuse_writes(mix):
    mix.remote.after_search = lambda: mix.remote.scan.update(lastScan='changed')
    with pytest.raises(radio_mixes.MixActionError, match='library changed'):
        save(mix)
    assert not mix.remote.playlists
    mix.librarian._navidrome_config = lambda: (CONFIG[0], 'other-owner', CONFIG[2])
    with pytest.raises(radio_mixes.MixActionError) as error:
        save(mix)
    assert error.value.status == 404


def test_lost_create_reply_recovers_one_playlist_and_serializes(mix):
    entered, release = Event(), Event()
    def pause():
        entered.set()
        assert release.wait(5)
    mix.remote.before_create = pause
    mix.remote.drop_create_reply = True
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(save, mix)
        try:
            assert entered.wait(5)
            with pytest.raises(radio_mixes.MixActionError, match='Another mix action'):
                save(mix)
        finally:
            release.set()
        with pytest.raises(PlaylistProviderError):
            pending.result(timeout=5)
    mix.remote.songs.append({'id': 'two', 'title': 'Two', 'musicBrainzId': SECOND})
    result = save(mix)
    assert result['playlist_id'] == 'playlist-1' and result['saved_count'] == 2
    assert len(mix.remote.playlists) == 1


def test_unknown_create_does_not_create_another_and_deleted_copy_stays_deleted(mix):
    mix.remote.drop_create_reply = True
    with pytest.raises(PlaylistProviderError):
        save(mix)
    mix.remote.playlists.clear()
    with pytest.raises(radio_mixes.MixActionError, match='unconfirmed'):
        save(mix)
    assert sum(method == 'createPlaylist' for method, _ in mix.remote.requests) == 1


def test_privacy_refusal_never_adds_tracks_and_lost_update_recovers(mix):
    original = mix.remote.respond
    def public_response(request):
        response = original(request)
        if 'playlist-1' in mix.remote.playlists:
            mix.remote.playlists['playlist-1']['public'] = True
        return response
    mix.remote.respond = public_response
    with pytest.raises(radio_mixes.MixActionError, match='private playlist'):
        save(mix)
    assert mix.remote.playlists['playlist-1']['entry'] == []
    mix.remote.respond = original
    mix.remote.drop_update_reply = True
    with pytest.raises(PlaylistProviderError):
        save(mix)
    mix.remote.drop_update_reply = False
    assert save(mix)['saved_count'] == 2
    assert len(mix.remote.playlists) == 1


def test_artist_keeps_exact_untagged_file_and_refuses_changed_identity(mix):
    body = payload('artist')
    body['tracks'] = [{**body['tracks'][0], 'recording_mbid': None, 'song_id': 'one'}]
    mix.remote.songs[0].pop('musicBrainzId')
    mix.id = radio_mixes.store_preview(mix.path, mix.remote.client(), body)
    assert save(mix)['saved_count'] == 1
    mix.id = radio_mixes.store_preview(mix.path, mix.remote.client(), body)
    mix.remote.songs[0]['title'] = 'One (Live)'
    with pytest.raises(radio_mixes.MixActionError, match='no confirmed owned'):
        save(mix)


def test_ambiguous_and_conflicting_recordings_refuse_download(mix):
    body = payload()
    body['tracks'][1]['conflicting_recording_mbids'] = True
    mix.id = radio_mixes.store_preview(mix.path, mix.remote.client(), body)
    with pytest.raises(playlist_download.InboxDownloadError, match='conflicting'):
        radio_mixes.download_preview_track(mix.librarian, mix.path, mix.id, 1)
    with pytest.raises(radio_mixes.MixActionError) as error:
        radio_mixes.download_preview_track(mix.librarian, mix.path, mix.id, 199)
    assert error.value.status == 404
    assert not mix.remote.playlists


def test_download_delegates_confirmed_source_and_rechecks_owned(mix, monkeypatch):
    calls = []
    def acquire(*args, **kwargs):
        calls.append((args, kwargs))
        return {'ok': True, 'status': 'queued', 'message': 'Queued', 'artist': 'Band', 'album': 'Album::Two'}
    monkeypatch.setattr(playlist_download.track_service, 'request_track', acquire)
    assert radio_mixes.download_preview_track(mix.librarian, mix.path, mix.id, 0)['status'] == 'owned'
    assert not calls
    assert radio_mixes.download_preview_track(mix.librarian, mix.path, mix.id, 1)['status'] == 'queued'
    assert calls[0][0][1:4] == ('Band', 'Album', 'Two')
    assert calls[0][1]['recording_mbid'] == SECOND


def test_resolved_albumless_import_is_saveable_using_the_same_preview(mix):
    body = payload()
    body['tracks'] = [{**body['tracks'][0], 'album': None, 'recording_mbid': None, 'duration_ms': None}]
    mix.id = radio_mixes.store_preview(mix.path, mix.remote.client(), body)
    storage = job_storage(mix.librarian.DISCOVERY_DB)
    save_job('Band', track_job_album('Album', 'One'), 'imported', {
        'kind': 'track', 'album_name': 'Album', 'track_title': 'One',
        'inbox_source': f'radio-{mix.id}/0',
    }, services=storage)
    assert save(mix)['saved_count'] == 1


def test_pending_copy_owner_and_changed_frozen_recording_are_refused(mix):
    mix.remote.drop_update_reply = True
    with pytest.raises(PlaylistProviderError):
        save(mix)
    mix.remote.drop_update_reply = False
    mix.remote.playlists['playlist-1']['owner'] = 'unrelated-owner'
    mix.remote.requests.clear()
    with pytest.raises(radio_mixes.MixActionError, match='playlist owner'):
        save(mix)
    assert all(method not in ('updatePlaylist', 'createPlaylist') for method, _ in mix.remote.requests)
    mix.remote.songs[0]['musicBrainzId'] = SECOND
    with pytest.raises(radio_mixes.MixActionError, match='selected tracks left'):
        save(mix)


def test_unused_previews_are_bounded_but_saved_intents_survive(mix):
    save(mix)
    for _ in range(55):
        radio_mixes.store_preview(mix.path, mix.remote.client(), payload())
    with closing(open_writer(mix.path)) as db:
        assert db.execute('SELECT COUNT(*) FROM radio_mix_previews').fetchone()[0] == 51
        assert get_preview(db, mix.id, mix.remote.client().target_key)['saved']


@pytest.fixture
def client(mix, monkeypatch):
    monkeypatch.setattr(main, 'get_librarian', lambda: mix.librarian)
    monkeypatch.setattr(main, '_AUTH_SECRET', b'radio-preview-test-secret')
    monkeypatch.setitem(main.app.dependency_overrides, get_librarian, lambda: mix.librarian)
    monkeypatch.setattr(api, 'discovery_mix', lambda *a, **kw: payload())
    monkeypatch.setattr(api, 'artist_radio', lambda *a, **kw: payload('artist'))
    with closing(TestClient(main.app, follow_redirects=False)) as http:
        yield http


def test_api_auth_validation_preview_download_and_save(mix, client):
    for method, path in [('post', '/preview'), ('post', f'/{mix.id}/save'),
                         ('get', f'/{mix.id}'), ('post', f'/{mix.id}/tracks/1/download')]:
        assert getattr(client, method)(URL + path).status_code == 401
    sign_in(client)
    for body in ({'kind': 'artist', 'tag': 'jazz'}, {'kind': 'discovery', 'tag': 'jazz)::hard'},
                 {'kind': 'discovery', 'tag': 'jazz', 'artist_mbid': FIRST}):
        assert client.post(URL + '/preview', json=body).status_code == 422
    result = client.post(URL + '/preview', json={'kind': 'discovery', 'tag': 'jazz'})
    assert result.status_code == 200 and result.headers['cache-control'] == 'no-store'
    preview_id = result.json()['preview_id']
    assert result.json()['tracks'] == payload()['tracks']
    detail = client.get(f'{URL}/{preview_id}').json()
    assert detail['owned_count'] == 2 and [t['position'] for t in detail['tracks']] == [0, 1, 2]
    result = client.post(f'{URL}/{preview_id}/tracks/0/download', json={'song_id': 'attacker'})
    assert result.json()['status'] == 'owned'
    result = client.post(f'{URL}/{preview_id}/save', json={'song_ids': ['attacker']})
    assert result.status_code == 200 and result.json()['saved_count'] == 2
    assert client.post(f'{URL}/{preview_id}/tracks/-1/download').status_code == 422
    assert client.post(f'{URL}/{"0" * 32}/save').status_code == 404


def test_preview_states_and_unknown_ownership(mix, client, monkeypatch):
    sign_in(client)
    monkeypatch.setattr(api, 'discovery_mix', lambda *a, **kw: {'state': 'unconfigured', 'tracks': []})
    body = client.post(URL + '/preview', json={'kind': 'discovery', 'tag': 'jazz'}).json()
    assert body['state'] == 'unconfigured' and 'preview_id' not in body
    mix.view.value = replace(mix.view.value, state='unavailable', data=None)
    body = client.get(f'{URL}/{mix.id}').json()
    assert body['owned_count'] is None and all(t['match_state'] is None for t in body['tracks'])
