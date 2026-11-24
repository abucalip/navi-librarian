import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from threading import Barrier

import httpx
import pytest

from integrations.listenbrainz.inbox import PlaylistInboxClient
from integrations.listenbrainz.jspf import parse_playlist
from intelligence.store import db, migrations
from intelligence.store.playlist_editions import (
    ManagedCopy,
    PlaylistEdition,
    PlaylistSnapshot,
    current_edition_id,
    get_edition,
    get_managed_copy,
    list_current_editions,
    publish_edition,
    save_managed_copy,
)


@pytest.fixture
def payload():
    return json.loads((Path(__file__).parent / "fixtures" / "listenbrainz_daily_jams.json").read_text())


@pytest.fixture
def snapshot(payload):
    return PlaylistSnapshot.from_hosted(parse_playlist(payload))


@pytest.fixture
def store(tmp_path):
    with closing(db.open_store(tmp_path / "intelligence.sqlite3")) as writer:
        yield writer


def publish(writer, snapshot, expected=None, fetched_at=100):
    return publish_edition(writer, snapshot, expected_current_id=expected, fetched_at=fetched_at)


def test_upgrade_preserves_v6_data_and_creates_same_tables_as_fresh_store(tmp_path, snapshot):
    path = tmp_path / "upgraded.sqlite3"
    with closing(db.connect(path)) as writer:
        for migration in migrations.MIGRATIONS[:6]:
            migrations._apply(writer, migration)
        with writer:
            writer.execute("INSERT INTO entities (type, canonical_name) VALUES ('artist', 'Existing artist')")
        assert migrations.current_version(writer) == 6

    with closing(db.open_store(path)) as upgraded, closing(db.open_store(":memory:")) as fresh:
        assert migrations.current_version(upgraded) == migrations.current_version(fresh) == 7
        tables = "SELECT sql FROM sqlite_master WHERE type = 'table' AND name LIKE 'playlist_%' ORDER BY name"
        assert upgraded.execute(tables).fetchall() == fresh.execute(tables).fetchall()
        assert upgraded.execute("SELECT canonical_name FROM entities").fetchone()[0] == "Existing artist"
        edition_id = publish(upgraded, snapshot)
        assert upgraded.execute("PRAGMA foreign_key_check").fetchall() == []

    with closing(db.open_readonly(path)) as reader:
        assert get_edition(reader, edition_id) == PlaylistEdition(edition_id, snapshot, 100)
        tracks = get_edition(reader, edition_id).snapshot.tracks
        assert [track["position"] for track in tracks] == [0, 1, 2, 3]
        assert tracks[0]["recording_mbid"] == tracks[3]["recording_mbid"]
        assert tracks[2]["caa_id"] == 34897349734


def test_retry_and_change_detection_with_same_or_missing_upstream_dates(store, snapshot):
    first = publish(store, snapshot)
    equivalent = replace(snapshot, metadata=dict(reversed(list(snapshot.metadata.items()))))
    assert publish(store, equivalent, fetched_at=101) == first
    assert get_edition(store, first).fetched_at == 100

    changed = replace(snapshot, metadata={**snapshot.metadata, "title": "Updated title"})
    second = publish(store, changed, expected=first)
    assert second != first
    assert publish(store, snapshot) is None
    assert publish(store, changed, expected=first) == second

    undated = replace(changed, metadata={**changed.metadata, "generated_at": None, "last_modified_at": None})
    third = publish(store, undated, expected=second)
    edited = replace(undated, tracks=({**undated.tracks[0], "title": "Edited track"}, *undated.tracks[1:]))
    fourth = publish(store, edited, expected=third)
    assert len({first, second, third, fourth}) == 4
    assert list_current_editions(store)[0].id == fourth
    assert get_edition(store, first).snapshot == snapshot

    # A freshly observed revert is a new revision. An old writer can't use it
    # to match the original head again.
    reverted = publish(store, snapshot, expected=fourth)
    assert reverted not in (None, first, second, third, fourth)
    assert publish(store, changed, expected=first) is None


def test_scheduled_editions_have_stable_recipe_and_distinct_edition_keys(store):
    snapshot = PlaylistSnapshot("local", "rediscover", "2026-11-24", {}, ({"position": 0, "title": "Track"},))
    first = publish(store, snapshot)
    next_edition = replace(snapshot, edition_key="2026-11-25")
    second = publish(store, next_edition, expected=first)
    assert second not in (None, first)
    assert get_edition(store, first).snapshot == snapshot
    assert list_current_editions(store)[0].snapshot == next_edition


def test_interrupted_publish_rolls_back_both_edition_and_pointer(store, snapshot):
    previous = publish(store, snapshot)
    store.execute(
        "CREATE TEMP TRIGGER stop_publish BEFORE UPDATE ON playlist_current_editions "
        "BEGIN SELECT RAISE(ABORT, 'interrupted write'); END"
    )
    changed = replace(snapshot, metadata={**snapshot.metadata, "title": "New title"})
    with pytest.raises(sqlite3.IntegrityError, match="interrupted write"):
        publish(store, changed, expected=previous)
    assert current_edition_id(store, snapshot.source_kind, snapshot.source_key) == previous
    assert store.execute("SELECT COUNT(*) FROM playlist_editions").fetchone()[0] == 1
    store.execute("DROP TRIGGER stop_publish")
    assert publish(store, changed, expected=previous) not in (None, previous)


def test_failed_detail_keeps_prior_snapshot_while_complete_detail_advances(store, payload, snapshot):
    first = publish(store, snapshot)
    other_mbid = "00000000-0000-4000-8000-000000000009"
    other_payload = {"playlist": {
        **payload["playlist"], "identifier": f"https://listenbrainz.org/playlist/{other_mbid}",
    }}
    other = PlaylistSnapshot.from_hosted(parse_playlist(other_payload))
    previous = publish(store, other)

    def respond(request):
        if request.url.path.endswith(other_mbid):
            return httpx.Response(200, json={"playlist": {**other_payload["playlist"], "title": "New edition"}})
        return httpx.Response(200, json={"playlist": {
            key: value for key, value in payload["playlist"].items() if key != "track"
        }})

    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        client = PlaylistInboxClient(transport, "fixture", token="fixture-token", sleep=lambda _: None)
        with pytest.raises(ValueError, match="track list"):
            client.playlist_details(snapshot.source_key)
        changed = PlaylistSnapshot.from_hosted(client.playlist_details(other_mbid))
        assert publish(store, changed, expected=previous) not in (None, previous)

    assert current_edition_id(store, "hosted", snapshot.source_key) == first
    assert get_edition(store, first).snapshot == snapshot
    assert get_edition(store, previous).snapshot == other


def test_overlapping_writers_cannot_replace_the_winning_edition(tmp_path, snapshot):
    path = tmp_path / "intelligence.sqlite3"
    with closing(db.open_store(path)) as writer:
        previous = publish(writer, snapshot)
    both_read = Barrier(2, timeout=5)

    def refresh(title):
        with closing(db.open_writer(path)) as writer:
            expected = current_edition_id(writer, "hosted", snapshot.source_key)
            both_read.wait()
            changed = replace(snapshot, metadata={**snapshot.metadata, "title": title})
            return publish(writer, changed, expected=expected)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(refresh, ("Edition A", "Edition B")))
    assert results.count(None) == 1
    winner = next(result for result in results if result is not None)
    with closing(db.open_readonly(path)) as reader:
        assert current_edition_id(reader, "hosted", snapshot.source_key) == winner
        assert reader.execute("SELECT COUNT(*) FROM playlist_editions").fetchone()[0] == 2
        assert get_edition(reader, previous).snapshot == snapshot


def test_managed_link_and_unlink_survive_new_editions(store, snapshot):
    first = publish(store, snapshot)
    linked = ManagedCopy("daily-jams", "navidrome-id")
    assert save_managed_copy(store, linked, expected=None)
    assert save_managed_copy(store, linked, expected=None)
    with pytest.raises(sqlite3.IntegrityError):
        save_managed_copy(store, ManagedCopy("weekly-jams", linked.playlist_id), expected=None)

    unlinked = replace(linked, unlinked=True)
    assert save_managed_copy(store, unlinked, expected=linked)
    new_copy = replace(linked, playlist_id="new-id")
    assert not save_managed_copy(store, new_copy, expected=linked)
    changed = replace(snapshot, metadata={**snapshot.metadata, "title": "New edition"})
    assert publish(store, changed, expected=first) not in (None, first)
    assert get_managed_copy(store, linked.feed_key) == unlinked
    assert save_managed_copy(store, new_copy, expected=unlinked)


def test_rejects_missing_positions_but_stores_complete_empty_playlist(store, snapshot):
    with pytest.raises(ValueError, match="ordered by position"):
        publish(store, replace(snapshot, tracks=snapshot.tracks[1:]))
    assert list_current_editions(store) == []
    empty = replace(snapshot, tracks=())
    assert get_edition(store, publish(store, empty)).snapshot == empty
