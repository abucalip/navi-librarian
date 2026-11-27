"""Deterministic queue and conservative ownership checks for LB-17."""

from collections import Counter
from dataclasses import replace

import pytest

from discovery.artist_radio import build_queue, radio_artists
from discovery.search.index import build_owned_data


def mbid(number):
    return f"90000000-0000-4000-8000-{number:012d}"


def library(artists=6, songs=70):
    return build_owned_data(
        generation=0, built_at=1, albums=[],
        artists=[{"id": str(a), "name": f"Artist {a}"} for a in range(artists)],
        identities={f"artist:{a}": {"mbid": mbid(a)} for a in range(artists)},
        songs=[{"id": f"{a}-{n:03d}", "artistId": str(a), "artist": f"Artist {a}",
                "title": f"Song {n}", "album": "Album", "duration": 180,
                "playCount": n, "musicBrainzId": mbid(1000 + a * songs + n)}
               for a in range(artists) for n in range(songs)],
    )


def related(data):
    return [{"name": a["name"], "mbid": a["mbid"]} for a in data.artists[1:]]


@pytest.mark.parametrize("mode,seed_count", [("familiar", 24), ("explore", 14), ("deep_cuts", 8)])
def test_modes_balance_seed_and_all_similars(mode, seed_count):
    data = library()
    artists = radio_artists(data, mbid(0), related(data))
    tracks = build_queue(data, artists, {}, familiarity=mode)
    counts = Counter(t["artist_id"] for t in tracks)
    assert len(tracks) == len({t["song_id"] for t in tracks}) == 40
    assert counts["0"] == seed_count
    assert len(counts) == 6
    assert max(counts[a] for a in counts if a != "0") - min(counts[a] for a in counts if a != "0") <= 1
    assert all(t["owned"] and t["song_id"] in {s["id"] for s in data.songs} for t in tracks)
    assert tracks == build_queue(data, artists, {}, familiarity=mode)
    first = next(t for t in tracks if t["artist_id"] == "0")
    assert first["song_id"] == ("0-069" if mode == "familiar" else "0-000")


def test_sparse_empty_and_seed_only_queues_are_not_padded():
    data = library(artists=2, songs=3)
    artists = radio_artists(data, mbid(0), related(data))
    assert len(build_queue(data, artists, {})) == 6
    assert len(build_queue(data, artists[:1], {})) == 3
    assert build_queue(data, [], {}) == []
    assert build_queue(replace(data, songs=()), artists, {}) == []
    assert radio_artists(data, mbid(99), related(data)) == []
    assert len(build_queue(library(1), library(1).artists, {}, count=50)) == 50


def test_artist_identity_conflicts_and_ambiguous_names_are_refused():
    data = library()
    assert len(radio_artists(data, mbid(0), [{"name": "Artist 1", "mbid": mbid(99)}])) == 1
    assert len(radio_artists(data, mbid(0), [{"name": "Artist 1"}])) == 2
    duplicate = {**data.artists[1], "id": "duplicate", "mbid": None}
    ambiguous = replace(data, artists=(*data.artists, duplicate))
    assert len(radio_artists(ambiguous, mbid(0), [{"name": "Artist 1"}])) == 1
    duplicate_seed = {**data.artists[0], "id": "other-seed"}
    assert radio_artists(replace(data, artists=(*data.artists, duplicate_seed)), mbid(0), []) == []


def test_popularity_only_ranks_owned_safe_matches_and_never_adds_tracks():
    data = library(1, 3)
    rows = [{"recording_mbid": mbid(1000), "title": "Song 0", "artist": "Artist 0", "album": "Album"},
            {"recording_mbid": mbid(9999), "title": "Missing", "artist": "Artist 0", "album": "Album"}]
    # Remove local play counts so popularity alone determines the order.
    data = replace(data, songs=tuple({**s, "plays": 0} for s in data.songs))
    tracks = build_queue(data, data.artists, {"0": rows})
    assert [t["song_id"] for t in tracks] == ["0-000", "0-001", "0-002"]
    unknown = replace(data, songs=tuple({**s, "recording_mbid": None} for s in data.songs))
    assert build_queue(unknown, unknown.artists, {"0": [rows[0]]})[0]["song_id"] == "0-000"
    wrong_version = {**rows[0], "title": "Song 2 (Live)"}
    assert build_queue(unknown, unknown.artists, {"0": [wrong_version]})[0]["song_id"] == "0-000"
    conflict = {**rows[0], "title": "Song 2", "recording_mbid": mbid(9999)}
    assert build_queue(data, data.artists, {"0": [conflict]})[0]["song_id"] == "0-000"


def test_recording_copies_deduplicate_but_versions_survive():
    data = library(1, 3)
    copy = {**data.songs[0], "id": "z-copy"}
    live = {**data.songs[0], "id": "live", "name": "Song 0 (Live)", "recording_mbid": mbid(2222)}
    data = replace(data, songs=(*data.songs, copy, live))
    tracks = build_queue(data, data.artists, {})
    assert len(tracks) == 4
    assert "z-copy" not in {t["song_id"] for t in tracks}
    assert "live" in {t["song_id"] for t in tracks}
