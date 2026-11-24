"""Focused tests for ListenBrainz playlist detail parsing."""

from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from integrations.listenbrainz.jspf import PlaylistTrack, parse_playlist


FIRST_MBID = "00000000-0000-4000-8000-000000000002"
THIRD_MBID = "00000000-0000-4000-8000-000000000004"
RECORDING_URL = "https://musicbrainz.org/recording/"


def test_sanitized_daily_jams():
    # Public Daily Jams detail shape with synthetic identities and metadata.
    fixture = Path(__file__).with_name("fixtures") / "listenbrainz_daily_jams.json"
    playlist = parse_playlist(json.loads(fixture.read_text(encoding="utf-8")))

    assert playlist.identifier == (
        "https://listenbrainz.org/playlist/00000000-0000-4000-8000-000000000001"
    )
    assert playlist.title == "Daily Jams for fixture-listener"
    assert playlist.generated_at == datetime(2025, 1, 2, 3, 4, 5, 123456, tzinfo=timezone.utc)
    assert playlist.tracks == (
        PlaylistTrack(0, FIRST_MBID, "Fixture track 1", "Fixture artist 1", "Fixture album 1", 60000),
        PlaylistTrack(1, None, "Fixture track 2", "Fixture artist 2", "Fixture album 2", 120000),
        PlaylistTrack(2, THIRD_MBID, "Fixture track 3", "Fixture artist 3", "Fixture album 3", 180000),
        PlaylistTrack(3, FIRST_MBID, "Fixture track 1", "Fixture artist 1", "Fixture album 1", 60000),
    )


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
