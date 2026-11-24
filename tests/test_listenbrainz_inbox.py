"""Exercise the ListenBrainz Inbox adapter at the HTTP transport boundary."""

import json
from pathlib import Path

import httpx
import pytest

from integrations.listenbrainz.inbox import (
    PlaylistInboxClient,
    RecommendationPage,
    RecordingRecommendation,
)


PLAYLIST_MBID = "00000000-0000-4000-8000-000000000001"
SECOND_PLAYLIST_MBID = "00000000-0000-4000-8000-000000000009"
FIRST_RECORDING = "00000000-0000-4000-8000-000000000002"
SECOND_RECORDING = "00000000-0000-4000-8000-000000000003"


@pytest.fixture
def playlist():
    path = Path(__file__).with_name("fixtures") / "listenbrainz_daily_jams.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_listing_details_and_recommendation_pages_share_pacing(playlist):
    metadata = {key: value for key, value in playlist["playlist"].items() if key != "track"}
    second = {**metadata, "identifier": f"https://listenbrainz.org/playlist/{SECOND_PLAYLIST_MBID}"}
    requests = []
    current_time = 0.0

    def sleep(seconds):
        nonlocal current_time
        current_time += seconds

    def handle(request):
        requests.append((request.url.raw_path, current_time))
        assert request.url.host == "api.listenbrainz.org"
        assert request.method == "GET"
        assert request.headers["Authorization"] == "Token fixture-token"
        assert request.headers["User-Agent"].startswith("Discair/")
        offset = int(request.url.params.get("offset", "0"))
        if request.url.path.endswith("/createdfor"):
            return httpx.Response(200, json={
                "playlists": [{"playlist": metadata if offset == 0 else second}],
                "playlist_count": 2, "count": 25, "offset": offset,
            })
        if request.url.path.endswith("/recording"):
            rows = [
                {"recording_mbid": FIRST_RECORDING, "score": 9.345},
                {"recording_mbid": SECOND_RECORDING, "score": 6},
            ]
            return httpx.Response(200, json={"payload": {
                "last_updated": 1588494361, "mbids": rows[offset:offset + 1],
                "total_mbid_count": len(rows),
            }})
        return httpx.Response(200, json=playlist)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        inbox = PlaylistInboxClient(
            client, "fixture user", token="fixture-token", clock=lambda: current_time, sleep=sleep,
        )
        listing = inbox.created_for_me()
        assert [item.playlist_mbid for item in listing] == [PLAYLIST_MBID, SECOND_PLAYLIST_MBID]
        assert all(item.source_patch == "daily-jams" for item in listing)
        details = inbox.playlist_details(listing[0].playlist_mbid)
        assert [track.position for track in details.tracks] == [0, 1, 2, 3]
        assert details.tracks[0].recording_mbid == details.tracks[3].recording_mbid == FIRST_RECORDING
        assert details.tracks[2].caa_id == 34897349734
        assert inbox.recording_recommendations(count=1) == RecommendationPage(
            1588494361, (RecordingRecommendation(FIRST_RECORDING, 9.345),), 2,
        )
        assert inbox.recording_recommendations(count=1, offset=1) == RecommendationPage(
            1588494361, (RecordingRecommendation(SECOND_RECORDING, 6.0),), 2,
        )

    assert [path for path, _ in requests] == [
        b"/1/user/fixture%20user/playlists/createdfor?count=25&offset=0",
        b"/1/user/fixture%20user/playlists/createdfor?count=25&offset=1",
        f"/1/playlist/{PLAYLIST_MBID}".encode(),
        b"/1/cf/recommendation/user/fixture%20user/recording?count=1&offset=0",
        b"/1/cf/recommendation/user/fixture%20user/recording?count=1&offset=1",
    ]
    assert [at for _, at in requests] == pytest.approx([0, 0.2, 0.4, 0.6, 0.8])


@pytest.mark.parametrize(("username", "token"), [(None, "token"), ("user", " ")])
def test_unconfigured_account_makes_no_requests(username, token):
    def handle(request):
        pytest.fail(f"Unexpected request to {request.url}")

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        inbox = PlaylistInboxClient(client, username, token=token)
        assert inbox.configured is False
        assert inbox.created_for_me() is None
        assert inbox.playlist_details(PLAYLIST_MBID) is None
        assert inbox.recording_recommendations() is None


def test_empty_created_for_me_and_unavailable_cf():
    def handle(request):
        if request.url.path.endswith("/createdfor"):
            return httpx.Response(200, json={"playlists": [], "playlist_count": 0, "offset": 0})
        return httpx.Response(204)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        inbox = PlaylistInboxClient(client, "user", token="token", sleep=lambda _: None)
        assert inbox.created_for_me() == ()
        assert inbox.recording_recommendations() == RecommendationPage(None, (), 0)


@pytest.mark.parametrize("status", [404, 429, 503])
def test_detail_http_error_is_not_an_empty_playlist(status):
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(status))) as client:
        inbox = PlaylistInboxClient(client, "user", token="token")
        with pytest.raises(httpx.HTTPStatusError) as error:
            inbox.playlist_details(PLAYLIST_MBID)
    assert error.value.response.status_code == status


def test_detail_timeout_propagates():
    def handle(request):
        raise httpx.ReadTimeout("timeout", request=request)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        inbox = PlaylistInboxClient(client, "user", token="token")
        with pytest.raises(httpx.ReadTimeout):
            inbox.playlist_details(PLAYLIST_MBID)


def test_detail_requires_tracks_and_matching_identity(playlist):
    def handle(_):
        return httpx.Response(200, json=playlist)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        inbox = PlaylistInboxClient(client, "user", token="token", sleep=lambda _: None)
        with pytest.raises(ValueError, match="requested MBID"):
            inbox.playlist_details(SECOND_PLAYLIST_MBID)
        del playlist["playlist"]["track"]
        with pytest.raises(ValueError, match="track list"):
            inbox.playlist_details(PLAYLIST_MBID)
        playlist["playlist"]["track"] = []
        assert inbox.playlist_details(PLAYLIST_MBID).tracks == ()


def test_incomplete_listing_fails_as_a_whole(playlist):
    def handle(request):
        offset = int(request.url.params["offset"])
        return httpx.Response(200, json={
            "playlists": [playlist] if offset == 0 else [],
            "playlist_count": 2, "offset": offset,
        })

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        inbox = PlaylistInboxClient(client, "user", token="token", sleep=lambda _: None)
        with pytest.raises(ValueError, match="ended before its reported total"):
            inbox.created_for_me()
