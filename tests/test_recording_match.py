"""Verify recording matches from playlist parsing through the owned index."""

import pytest

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


def source_track(**overrides):
    track = {"creator": "Élan Ensemble", "title": "Night Signal", **overrides}
    return parse_playlist({"playlist": {"track": [track]}}).tracks[0]


def local_song(**overrides):
    return {"id": "local", "artist": "  E\u0301LAN   Ensemble ", "title": "Night Signal", **overrides}


@pytest.mark.parametrize(
    ("source", "local", "expected"),
    [
        ({"album": "Night Sessions"}, {"album": " NIGHT SESSIONS "}, "owned"),
        ({"duration": 182_000}, {"duration": 180}, "owned"),
        ({"duration": 182_001}, {"duration": 180}, "ambiguous"),
        ({"duration": 0}, {"duration": 180}, "ambiguous"),
        ({"duration": 180_000}, {"duration": 0}, "ambiguous"),
        ({}, {}, "ambiguous"),
        ({"album": "Night Sessions", "duration": 180_000},
         {"album": "Other Sessions", "duration": 180}, "ambiguous"),
        ({"album": "Night Sessions", "duration": 180_000},
         {"album": "Night Sessions", "duration": 190}, "ambiguous"),
        ({"duration": 180_000}, {"duration": 180, "title": "Night Signal (Live)"}, "ambiguous"),
        ({"duration": 180_000, "title": "Night Signal — Studio Version"},
         {"duration": 180}, "ambiguous"),
        ({"duration": 180_000}, {"duration": 180, "album": "Night Sessions [Remastered]"},
         "ambiguous"),
        ({"duration": 180_000, "album": "Night Sessions (Live)"},
         {"duration": 180}, "ambiguous"),
        ({"album": "Night Sessions (Live)", "title": "Night Signal (Live)"},
         {"album": "Night Sessions (Live)", "title": "Night Signal (Live)"}, "owned"),
        ({"album": "Night Sessions"}, {"album": "Night Sessions", "title": "Night Signal II"},
         "missing"),
        ({"album": "Night Sessions"}, {"album": "Night Sessions", "artist": "Other Ensemble"},
         "missing"),
        ({"album": "Night Sessions", "creator": ""},
         {"album": "Night Sessions", "artist": ""}, "missing"),
    ],
)
def test_fallback_requires_corroboration_and_respects_version_evidence(source, local, expected):
    match, = match_recordings([source_track(**source)], owned_data(local_song(**local)))
    assert match.state == expected
    assert match.song_id == ("local" if expected == "owned" else None)


def test_alternate_versions_remain_ambiguous_in_either_candidate_order():
    track = source_track(title="Night Signal - Part II", album="Night Sessions", duration=180_000)
    original = local_song(title="Night Signal - Part II", album="Night Sessions", duration=180)
    alternate = local_song(
        id="alternate", title="Night Signal - Part II - Remastered", album="Expanded Edition",
        duration=185,
    )
    for owned in (owned_data(original, alternate), owned_data(alternate, original)):
        match, = match_recordings([track], owned)
        assert (match.state, match.song_id) == ("ambiguous", None)


def test_same_title_versions_on_different_albums_are_ambiguous():
    track = source_track(album="Night Sessions", duration=180_000)
    owned = owned_data(
        local_song(album="Night Sessions", duration=180),
        local_song(id="live", album="Live at the Hall", duration=181),
        local_song(id="remaster", album="Night Sessions (Remastered)", duration=180),
    )
    match, = match_recordings([track], owned)
    assert (match.state, match.song_id) == ("ambiguous", None)


def test_recording_identifiers_take_precedence_over_fallback():
    owned = owned_data(local_song(album="Night Sessions", musicBrainzId=OWNED_MBID))
    prefix = "https://musicbrainz.org/recording/"
    tracks = [
        source_track(identifier=prefix + OWNED_MBID, title="Different title"),
        source_track(identifier=prefix + MISSING_MBID, album="Night Sessions"),
        source_track(identifier=[prefix + OWNED_MBID, prefix + MISSING_MBID],
                     album="Night Sessions"),
    ]
    assert [(match.state, match.song_id) for match in match_recordings(tracks, owned)] == [
        ("owned", "local"), ("ambiguous", None), ("ambiguous", None),
    ]


def test_tagged_source_can_fall_back_to_an_untagged_copy_and_preserve_repeats():
    source = source_track(identifier=f"https://musicbrainz.org/recording/{OWNED_MBID}",
                          album="Night Sessions")
    matches = match_recordings([source, source], owned_data(local_song(album="Night Sessions")))
    assert [(match.track, match.state, match.song_id) for match in matches] == [
        (source, "owned", "local"), (source, "owned", "local"),
    ]
