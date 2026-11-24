"""Focused tests for ListenBrainz playlist detail parsing."""

from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from integrations.listenbrainz.jspf import PlaylistTrack, parse_playlist, parse_playlist_metadata


FIRST_MBID = "00000000-0000-4000-8000-000000000002"
THIRD_MBID = "00000000-0000-4000-8000-000000000004"
RECORDING_URL = "https://musicbrainz.org/recording/"


def test_sanitized_daily_jams():
    # Public Daily Jams detail shape with synthetic identities and metadata.
    fixture = Path(__file__).with_name("fixtures") / "listenbrainz_daily_jams.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    playlist = parse_playlist(payload)

    assert playlist.identifier == (
        "https://listenbrainz.org/playlist/00000000-0000-4000-8000-000000000001"
    )
    assert playlist.title == "Daily Jams for fixture-listener"
    assert playlist.generated_at == datetime(2025, 1, 2, 3, 4, 5, 123456, tzinfo=timezone.utc)
    assert playlist.last_modified_at == datetime(2025, 1, 3, 3, 4, 5, tzinfo=timezone.utc)
    assert playlist.creator == "troi-bot"
    assert playlist.source_patch == "daily-jams"
    assert playlist.playlist_mbid == "00000000-0000-4000-8000-000000000001"
    assert playlist.tracks == (
        PlaylistTrack(0, FIRST_MBID, "Fixture track 1", "Fixture artist 1", "Fixture album 1", 60000),
        PlaylistTrack(1, None, "Fixture track 2", "Fixture artist 2", "Fixture album 2", 120000),
        PlaylistTrack(
            2, THIRD_MBID, "Fixture track 3", "Fixture artist 3", "Fixture album 3", 180000,
            artist_mbids=(
                "00000000-0000-4000-8000-000000000005",
                "abcdef00-0000-4000-8000-000000000006",
            ),
            release_mbid="00000000-0000-4000-8000-000000000007",
            caa_id=34897349734,
            caa_release_mbid="00000000-0000-4000-8000-000000000008",
        ),
        PlaylistTrack(3, FIRST_MBID, "Fixture track 1", "Fixture artist 1", "Fixture album 1", 60000),
    )
    del payload["playlist"]["track"]
    metadata = parse_playlist_metadata(payload)
    assert vars(metadata) == {key: value for key, value in vars(playlist).items() if key != "tracks"}


def test_invalid_optional_extensions_preserve_playlist_and_track():
    playlist = parse_playlist({"playlist": {
        "creator": "Fixture bot",
        "extension": {"https://musicbrainz.org/doc/jspf#playlist": {
            "last_modified_at": "2025-01-03",
            "creator": " ",
            "additional_metadata": ["invalid"],
        }},
        "track": [{"creator": "Fixture artist", "extension": {
            "https://musicbrainz.org/doc/jspf#track": {
                "artist_identifiers": [RECORDING_URL + FIRST_MBID, None],
                "release_identifier": RECORDING_URL + FIRST_MBID,
                "additional_metadata": {"caa_id": True, "caa_release_mbid": "invalid"},
            },
        }}],
    }})
    assert playlist.creator == "Fixture bot"
    assert playlist.last_modified_at is None
    assert playlist.source_patch is None
    assert playlist.tracks == (PlaylistTrack(0, None, None, "Fixture artist", None, None),)


@pytest.mark.parametrize(
    ("identifier", "expected"),
    [
        (f"http://musicbrainz.org/recording/{FIRST_MBID}", FIRST_MBID),
        (f"{RECORDING_URL}ABCDEF00-0000-4000-8000-000000000002",
         "abcdef00-0000-4000-8000-000000000002"),
        (["https://other.example/track/123", RECORDING_URL + FIRST_MBID], FIRST_MBID),
        ([RECORDING_URL + FIRST_MBID] * 2, FIRST_MBID),
        ([RECORDING_URL + FIRST_MBID, RECORDING_URL + THIRD_MBID], None),
        ([], None),
        (None, None),
        (FIRST_MBID, None),
        (RECORDING_URL + "invalid", None),
        (f"https://musicbrainz.org/release/{FIRST_MBID}", None),
        (f"https://musicbrainz.org.example/recording/{FIRST_MBID}", None),
    ],
)
def test_recording_identifier(identifier, expected):
    playlist = parse_playlist({"playlist": {"track": [{"identifier": identifier}]}})
    assert playlist.tracks[0].recording_mbid == expected
    assert playlist.tracks[0].conflicting_recording_mbids == (
        identifier == [RECORDING_URL + FIRST_MBID, RECORDING_URL + THIRD_MBID]
    )


@pytest.mark.parametrize("date", [None, 123, "bad-date", "2025-01-02", "2025-01-02T03:04:05"])
def test_unusable_generation_date_keeps_empty_playlist(date):
    playlist = parse_playlist({"playlist": {"date": date, "track": []}})
    assert playlist.generated_at is None
    assert playlist.tracks == ()


def test_generation_date_with_utc_designator():
    playlist = parse_playlist({"playlist": {"date": "2025-01-02T03:04:05Z", "track": []}})
    assert playlist.generated_at == datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "payload", [{}, {"playlist": []}, {"playlist": {}}, {"playlist": {"track": {}}},
                {"playlist": {"track": [{}, None]}}],
)
def test_rejects_malformed_playlist_structure(payload):
    with pytest.raises(ValueError, match="JSPF"):
        parse_playlist(payload)
