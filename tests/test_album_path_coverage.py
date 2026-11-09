import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from album_path_coverage import run  # noqa: E402
from intelligence.store import open_store  # noqa: E402
from intelligence.store import repositories as repo  # noqa: E402

DUMP = "musicbrainz_dump"


class AlbumPathCoverageTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "c.sqlite3"
        self.db = open_store(self.path)
        self.n = 0

    def tearDown(self):
        self.db.close()
        self._tmp.cleanup()

    def ent(self, kind, name, **kw):
        self.n += 1
        mbid = f"e0000000-0000-0000-0000-{self.n:012d}"
        return repo.upsert_entity(self.db, kind, name, mbid=mbid, **kw)[0]

    def edge(self, a, b, rel, *, ec="source_explicit", mq="exact_mbid"):
        repo.add_edge(self.db, a, b, rel, source=DUMP, evidence_class=ec, match_quality=mq)

    def album(self, name, artist):
        rel = self.ent("release", name, owned=True)
        self.edge(rel, artist, "credited_to", ec="library_tag", mq="exact_mbid")
        return rel

    def measure(self, kind):
        self.db.commit()
        return run(self.path, (kind,))["kinds"][kind]

    def test_crew_links_owned_albums_by_a_shared_producer(self):
        artist = self.ent("artist", "A", owned=True)
        a1 = self.album("A1", artist)
        a2 = self.album("A2", artist)
        prod = self.ent("artist", "Producer")
        self.edge(prod, a1, "producer")
        self.edge(prod, a2, "producer")
        result = self.measure("album_crew")
        self.assertEqual(result["albums_with_stop"], 2)
        self.assertEqual(result["stops_total"], 2)

    def test_a_credit_marked_inferred_gives_no_stop(self):
        artist = self.ent("artist", "A", owned=True)
        a1 = self.album("A1", artist)
        a2 = self.album("A2", artist)
        prod = self.ent("artist", "Producer")
        self.edge(prod, a1, "producer")
        self.edge(prod, a2, "producer", ec="inferred")
        result = self.measure("album_crew")
        self.assertEqual(result["albums_with_stop"], 0)

    def test_guest_on_another_owned_album_is_a_stop_but_album_artists_are_not_guests(self):
        artist = self.ent("artist", "A", owned=True)
        a1 = self.album("A1", artist)
        a2 = self.album("A2", artist)
        rec1 = self.ent("recording", "R1")
        rec2 = self.ent("recording", "R2")
        self.edge(rec1, a1, "appears_on")
        self.edge(rec2, a2, "appears_on")
        guest = self.ent("artist", "Guest")
        self.edge(guest, rec1, "vocal")
        self.edge(guest, rec2, "vocal")
        self.edge(artist, rec1, "vocal")  # album artist, not a guest
        self.edge(artist, rec2, "vocal")
        result = self.measure("album_guests")
        self.assertEqual(result["stops_total"], 2)

    def test_empty_store_gives_zero_albums_with_stops(self):
        self.ent("artist", "Lonely", owned=True)
        result = self.measure("album_works")
        self.assertEqual((result["albums"], result["albums_with_stop"]), (0, 0))


if __name__ == "__main__":
    unittest.main()
