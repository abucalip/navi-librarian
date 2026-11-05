import copy
import tempfile
import unittest
from pathlib import Path

from intelligence.ingest import navidrome as ingest
from intelligence.resolution import unresolved as queue
from intelligence.store import open_store
from intelligence.store import repositories as repo

REL = "11111111-1111-1111-1111-111111111111"
ART = "22222222-2222-2222-2222-222222222222"
REC1 = "33333333-3333-3333-3333-333333333333"
REC2 = "44444444-4444-4444-4444-444444444444"


def album(**over):
    base = {
        "id": "al-1", "name": "Rumours", "artist": "Fleetwood Mac", "artistId": "ar-1",
        "artists": [{"id": "ar-1", "name": "Fleetwood Mac", "musicBrainzId": ART.upper()}],
        "musicBrainzId": REL, "year": 1977, "songCount": 2, "duration": 400,
        "genres": [{"name": "Rock"}, {"name": "Pop"}],
        "recordLabels": [{"name": "Warner"}], "releaseTypes": ["Album"],
        "originalReleaseDate": {"year": 1977, "month": 2},
        "discTitles": [{"disc": 1, "title": "Side A"}],
        "song": [
            {"id": "s1", "title": "Second Hand News", "artist": "Fleetwood Mac", "track": 1,
             "discNumber": 1, "duration": 163, "musicBrainzId": REC1, "isrc": ["USWB19900001"],
             "bitRate": 900, "bitDepth": 16, "samplingRate": 44100, "suffix": "flac",
             "replayGain": {"trackGain": -6.5, "trackPeak": 0.98}},
            {"id": "s2", "title": "Dreams", "artist": "Fleetwood Mac", "track": 2,
             "duration": 237, "musicBrainzId": REC2},
        ],
    }
    base.update(over)
    return base


class NormalizeTests(unittest.TestCase):
    def test_fields_are_normalized(self):
        a = ingest.normalize_album(album())
        self.assertEqual(a.mbid, REL)
        self.assertEqual(a.artist_mbid, ART)
        self.assertEqual(a.genres, ("Rock", "Pop"))
        self.assertEqual(a.record_labels, ("Warner",))
        self.assertEqual(a.original_release_date, "1977-02")
        self.assertEqual(a.disc_titles, {1: "Side A"})
        self.assertEqual(a.duration_ms, 400000)
        t = a.tracks[0]
        self.assertEqual((t.duration_ms, t.isrcs, t.bit_depth, t.replay_gain),
                         (163000, ("USWB19900001",), 16, {"trackGain": -6.5, "trackPeak": 0.98}))

    def test_missing_fields_stay_none(self):
        a = ingest.normalize_album({"id": "x", "song": [{"id": "t"}]})
        self.assertIsNone(a.mbid)
        self.assertIsNone(a.year)
        self.assertEqual(a.genres, ())
        self.assertIsNone(a.tracks[0].duration_ms)
        self.assertIsNone(a.tracks[0].replay_gain)

    def test_bad_values_are_dropped(self):
        a = ingest.normalize_album(album(musicBrainzId="nope", year="abc", song=[{"id": "t", "musicBrainzId": "x"}]))
        self.assertIsNone(a.mbid)
        self.assertIsNone(a.year)
        self.assertIsNone(a.tracks[0].mbid)

    def test_genre_string_fallback_and_single_song_object(self):
        a = ingest.normalize_album({"id": "x", "genre": "Jazz", "song": {"id": "t", "title": "A"}})
        self.assertEqual(a.genres, ("Jazz",))
        self.assertEqual(len(a.tracks), 1)

    def test_id_is_required(self):
        with self.assertRaises(ValueError):
            ingest.normalize_album({"name": "x"})


class IngestTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = open_store(Path(tmp.name) / "i.sqlite3")
        self.addCleanup(self.db.close)

    def test_tagged_album_is_resolved_and_linked(self):
        r = ingest.ingest_album(self.db, album(), now=1.0)
        self.assertTrue(r.new_observation)
        self.assertEqual((r.recordings_resolved, r.unresolved, r.deferred), (2, 0, 0))
        release = repo.get_entity(self.db, r.release_entity_id)
        self.assertEqual((release["type"], release["mbid"], release["owned"]), ("release", REL, 1))
        edges = repo.edges_from(self.db, r.release_entity_id, ingest.REL_CREDITED_TO)
        self.assertEqual(len(edges), 1)
        self.assertEqual((edges[0]["evidence_class"], edges[0]["match_quality"]), ("library_tag", "exact_mbid"))
        appears = repo.edges_to(self.db, r.release_entity_id, ingest.REL_APPEARS_ON)
        self.assertEqual(sorted(e["role"] for e in appears), ["1/1", "1/2"])
        self.assertEqual(r.edges_created, 3)

    def test_reingest_is_idempotent(self):
        ingest.ingest_album(self.db, album(), now=1.0)
        r = ingest.ingest_album(self.db, album(), now=2.0)
        self.assertFalse(r.new_observation)
        self.assertEqual(r.edges_created, 0)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM entities").fetchone()[0], 4)

    def test_changed_album_adds_observation_only(self):
        ingest.ingest_album(self.db, album(), now=1.0)
        r = ingest.ingest_album(self.db, album(year=1978), now=2.0)
        self.assertTrue(r.new_observation)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM observations").fetchone()[0], 2)

    def test_untagged_album_is_queued_without_entity_or_edge(self):
        a = album(musicBrainzId=None, artists=[], song=[{"id": "s1", "title": "T", "artist": "A"}])
        r = ingest.ingest_album(self.db, a, now=1.0)
        self.assertIsNone(r.release_entity_id)
        self.assertEqual(r.unresolved, 2)
        self.assertIsNotNone(queue.find_unresolved(self.db, "release", "al-1"))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM entities").fetchone()[0], 0)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM edges").fetchone()[0], 0)
        self.assertTrue(any("no MBID" in n for n in r.notes))

    def test_search_failure_defers_and_writes_no_queue_rows(self):
        def boom(ref):
            raise RuntimeError("provider down")
        a = album(musicBrainzId=None, artists=[], song=[])
        r = ingest.ingest_album(self.db, a, now=1.0, search=boom)
        self.assertEqual((r.deferred, r.unresolved), (1, 0))
        self.assertIsNone(queue.find_unresolved(self.db, "release", "al-1"))

    def test_unique_search_candidate_is_recorded_as_derived(self):
        def search(ref):
            return [{"mbid": REL, "artist": "Fleetwood Mac", "title": "Rumours", "track_count": 2,
                     "durations_ms": [163000, 237000]}]
        a = album(musicBrainzId=None, artists=[])
        r = ingest.ingest_album(self.db, a, now=1.0, search=search)
        self.assertIsNotNone(r.release_entity_id)
        appears = repo.edges_to(self.db, r.release_entity_id, ingest.REL_APPEARS_ON)
        self.assertEqual(len(appears), 2)

    def test_input_is_not_mutated(self):
        a = album()
        before = copy.deepcopy(a)
        ingest.ingest_album(self.db, a, now=1.0)
        self.assertEqual(a, before)


if __name__ == "__main__":
    unittest.main()
