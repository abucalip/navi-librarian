"""Verify exact recording matches from playlist parsing through the owned index."""

from discovery.recording_match import match_recordings
from discovery.search.index import build_owned_data
from integrations.listenbrainz.jspf import parse_playlist


OWNED_MBID = "12345678-abcd-4321-abcd-1234567890ab"
MISSING_MBID = "abcdef01-2345-4321-abcd-1234567890ab"


def owned_data(*songs):
    return build_owned_data(generation=1, built_at=0, artists=(), albums=(), songs=songs)


def playlist(*mbids):
    return parse_playlist({"playlist": {"track": [
        {"title": "Same title", "identifier": [f"https://musicbrainz.org/recording/{mbid}"]}
        if mbid is not None else {"title": "Same title"}
        for mbid in mbids
    ]}})


def test_exact_matches_preserve_source_order_and_repeated_occurrences():
    owned = owned_data(
        {"id": "owned", "title": "Different title", "musicBrainzId": f" {OWNED_MBID.upper()} "},
        {"id": "unidentified", "title": "Same title"},
        {"id": "bad-tag", "title": "Same title", "musicBrainzId": "invalid"},
        {"id": "bad-type", "title": "Same title", "musicBrainzId": [MISSING_MBID]},
    )
    source = playlist(OWNED_MBID, MISSING_MBID, OWNED_MBID, None, "invalid")

    assert [song["recording_mbid"] for song in owned.songs] == [OWNED_MBID, None, None, None]

    matches = match_recordings(source.tracks, owned)

    assert tuple(match.track for match in matches) == source.tracks
    assert [match.track.position for match in matches] == [0, 1, 2, 3, 4]
    assert [(match.state, match.song_id) for match in matches] == [
        ("owned", "owned"),
        ("missing", None),
        ("owned", "owned"),
        ("missing", None),
        ("missing", None),
    ]


def test_duplicate_local_copies_use_the_lowest_song_id_in_either_order():
    first = {"id": "z-copy", "title": "First copy", "musicBrainzId": OWNED_MBID}
    second = {"id": "a-copy", "title": "Second copy", "musicBrainzId": OWNED_MBID}
    tracks = playlist(OWNED_MBID).tracks

    for owned in (owned_data(first, second), owned_data(second, first)):
        assert match_recordings(tracks, owned)[0].song_id == "a-copy"


def test_empty_inputs():
    owned = owned_data()
    assert match_recordings((), owned) == ()
    assert match_recordings(playlist(OWNED_MBID).tracks, owned)[0].state == "missing"
