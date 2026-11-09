import json

from intelligence.store import open_store
from intelligence.store import repositories as repo
from intelligence.taste.library_genres import genres_by_recording


def test_newest_observation_wins_and_untagged_tracks_are_skipped(tmp_path):
    db = open_store(tmp_path / "s.sqlite3")
    mbid = "11111111-1111-1111-1111-111111111111"
    repo.add_observation(db, "navidrome", {"tracks": [{"mbid": mbid, "genres": ["Rock"]}]}, fetched_at=1, entity_hint="album:a")
    repo.add_observation(db, "navidrome", {"tracks": [{"mbid": mbid.upper(), "genres": ["Jazz", "Jazz", "Blues"]},
                                                      {"mbid": "22222222-2222-2222-2222-222222222222", "genres": []}]},
                         fetched_at=2, entity_hint="album:a")
    assert dict(genres_by_recording(db)) == {mbid: ("Jazz", "Blues")}
    db.close()
