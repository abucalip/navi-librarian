from contextlib import closing
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from app import main
from app.api import artist_radio
from app.api.dependencies import get_librarian
from discovery.search.index import IndexView
from test_api_playlist_inbox import FakeLibrarian, sign_in
from test_artist_radio import library, mbid, related

URL = "/api/artist-radio"


@pytest.fixture
def radio(tmp_path, monkeypatch):
    librarian = FakeLibrarian(tmp_path)
    librarian.settings.update(listenbrainz_username="owner", listenbrainz_token="fixture-token")
    cache = {}
    librarian._discovery_read_list = lambda key: {"payload": cache[key]} if key in cache else None
    librarian._discovery_write_list = cache.__setitem__
    data = library()
    view = SimpleNamespace(value=IndexView("fresh", data, None))
    calls = []
    monkeypatch.setattr(artist_radio, "owned_view", lambda _: view.value)
    monkeypatch.setattr(artist_radio, "top_recordings", lambda mbid, **kw: calls.append(mbid) or [])
    monkeypatch.delenv("LISTENBRAINZ_TOKEN", raising=False)
    monkeypatch.setattr(main, "get_librarian", lambda: librarian)
    monkeypatch.setattr(main, "_AUTH_SECRET", b"radio-test-signing-secret")
    monkeypatch.setitem(main.app.dependency_overrides, get_librarian, lambda: librarian)
    with closing(TestClient(main.app, follow_redirects=False)) as client:
        yield SimpleNamespace(client=client, librarian=librarian, cache=cache, view=view, calls=calls)


def request(radio, **params):
    return radio.client.get(URL, params={"artist_mbid": mbid(0), **params})


def test_auth_validation_and_ready_contract(radio):
    assert request(radio).status_code == 401
    assert not radio.calls
    sign_in(radio.client)
    for params in ({"artist_mbid": "bad"}, {"count": 24}, {"count": 51}, {"familiarity": "unknown"}):
        assert request(radio, **params).status_code == 422
    assert radio.client.get(URL).status_code == 422
    assert not radio.calls
    response = request(radio)
    body = response.json()
    assert response.headers["cache-control"] == "no-store"
    assert body["state"] == "ready"
    assert body["index_state"] == "fresh"
    assert body["similar_state"] == "unavailable"
    assert body["popularity_state"] == "ready"
    assert body["requested_count"] == len(body["tracks"]) == 40
    assert all(t["owned"] for t in body["tracks"])
    assert "fixture-token" not in response.text


def test_unconfigured_has_no_provider_calls_or_index_reads(radio, monkeypatch):
    sign_in(radio.client)
    monkeypatch.setattr(artist_radio, "owned_view", lambda _: pytest.fail("unconfigured index read"))
    for settings in ({}, {"listenbrainz_username": "owner"}, {"listenbrainz_token": "fixture"}):
        radio.librarian.settings.pop("listenbrainz_username", None)
        radio.librarian.settings.pop("listenbrainz_token", None)
        radio.librarian.settings.update(settings)
        body = request(radio).json()
        assert body["state"] == "unconfigured" and body["tracks"] == []
    assert not radio.calls


def test_index_unknown_seed_and_no_tracks_are_distinct(radio):
    sign_in(radio.client)
    data = radio.view.value.data
    radio.view.value = IndexView("building", None, None)
    assert request(radio).json()["state"] == "index_unavailable"
    assert not radio.calls
    radio.view.value = IndexView("fresh", data, None)
    assert request(radio, artist_mbid=mbid(99)).json()["state"] == "empty"
    assert not radio.calls
    radio.view.value = IndexView("fresh", library(1, 0), None)
    assert request(radio).json()["state"] == "empty"
    assert not radio.calls


def test_similars_are_cache_only_and_provider_failure_keeps_owned_queue(radio, monkeypatch):
    sign_in(radio.client)
    data = radio.view.value.data
    key = f"similar:{mbid(0)}:artist 0:deezer0:listenbrainz0"
    radio.cache[key] = {"at": artist_radio.time.time(), "results": related(data)}
    monkeypatch.setattr(artist_radio, "top_recordings", lambda *a, **k: None)
    response = request(radio, familiarity="deep_cuts", count=50)
    body = response.json()
    assert body["state"] == "ready"
    assert body["similar_state"] == "ready"
    assert body["popularity_state"] == "partial"
    assert len(body["tracks"]) == 50
    assert len({t["artist_id"] for t in body["tracks"]}) == 6
    radio.cache[key]["at"] -= 8 * 86400
    assert request(radio).json()["similar_state"] == "unavailable"
    radio.view.value = IndexView("stale", data, None)
    assert request(radio).json()["index_state"] == "stale"
