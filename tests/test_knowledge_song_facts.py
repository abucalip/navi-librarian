"""Song facts (Mac player bar): lines come only from stored MusicBrainz relationships, each with its source."""
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.knowledge as routes
from app.api.dependencies import get_librarian
from app.api.insights import STORE_FILE
from intelligence.store import open_store
from intelligence.store import repositories as repo

SRC = dict(source="musicbrainz_dump", evidence_class="source_explicit", match_quality="exact_mbid")


class FakeLibrarian:
    def __init__(self, data_dir):
        self.DATA_DIR = Path(data_dir)


class SongFacts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        api = FastAPI()
        api.include_router(routes.router)
        api.dependency_overrides[get_librarian] = lambda: FakeLibrarian(self.tmp.name)
        self.client = TestClient(api)
        db = open_store(Path(self.tmp.name) / STORE_FILE)
        up = lambda t, n, g: repo.upsert_entity(db, t, n, mbid=g)[0]
        self.rec = up("recording", "Take", "r-gid")
        producer, player = up("artist", "Pat Producer", "p1"), up("artist", "Sam Strings", "p2")
        studio, work, writer = up("place", "Wessex Studios", "pl"), up("work", "Song", "w"), up("artist", "Wanda Writer", "wr")
        other, sampler = up("recording", "Cover Take", "r2"), up("recording", "Later Track", "r3")
        group = up("artist", "The Band", "band")
        repo.add_edge(db, producer, self.rec, "producer", **SRC)
        repo.add_edge(db, player, self.rec, "instrument", role="cello", **SRC)
        repo.add_edge(db, studio, self.rec, "recording", valid_from="1986-03", **SRC)
        repo.add_edge(db, self.rec, work, "performance", **SRC)
        repo.add_edge(db, other, work, "performance", role="cover", **SRC)
        repo.add_edge(db, writer, work, "composer", **SRC)
        repo.add_edge(db, sampler, self.rec, "samples material", **SRC)
        db.execute("INSERT INTO artist_life_span (entity_id, begin_date, end_date, ended) VALUES (?, '1981', '1992', 1)", (group,))
        db.execute("INSERT INTO artist_facts (entity_id, kind) VALUES (?, 'Group')", (group,))
        db.commit()
        db.close()

    def facts(self, **params):
        r = self.client.get("/api/knowledge/song-facts", params={"mbid": "r-gid", **params})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_lines_come_from_stored_relationships_with_source(self):
        body = self.facts(artist_mbid="band")
        texts = {f["kind"]: f for f in body["facts"]}
        self.assertEqual(texts["producer"]["text"], "Produced by Pat Producer")
        self.assertEqual(texts["recorded_at"]["text"], "Recorded at Wessex Studios in 1986")
        self.assertIn("Sam Strings (cello)", texts["players"]["text"])
        self.assertEqual(texts["written_by"]["text"], "Written by Wanda Writer")
        self.assertIn("1 cover", texts["covers"]["text"])
        self.assertEqual(texts["sampled_by"]["text"], "Sampled in “Later Track”")
        self.assertEqual(texts["life_span"]["text"], "Together from 1981 until 1992")
        self.assertEqual(texts["life_span"]["scope"], "artist")
        for f in body["facts"]:
            self.assertEqual(f["source"], "MusicBrainz")
        self.assertNotIn('"id"', self.client.get("/api/knowledge/song-facts", params={"mbid": "r-gid"}).text)

    def test_absent_facts_are_not_invented(self):
        db = open_store(Path(self.tmp.name) / STORE_FILE)
        repo.upsert_entity(db, "recording", "Bare", mbid="bare")
        db.close()
        self.assertEqual(self.facts(mbid="bare")["facts"], [])

    def test_unknown_recording_is_404_and_unknown_album_is_skipped(self):
        self.assertEqual(self.client.get("/api/knowledge/song-facts", params={"mbid": "nope"}).status_code, 404)
        self.assertEqual(self.client.get("/api/knowledge/song-facts").status_code, 400)
        self.assertEqual(self.client.get("/api/knowledge/song-facts", params={"mbid": "r-gid", "album_type": "x"}).status_code, 400)
        self.assertEqual(self.facts(album_mbid="unknown")["recording"]["mbid"], "r-gid")


if __name__ == "__main__":
    unittest.main()
