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


class MemberLineage(unittest.TestCase):
    """``member_lineage`` artist lines: stated band memberships only, one line per member, own projects skipped."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        api = FastAPI()
        api.include_router(routes.router)
        api.dependency_overrides[get_librarian] = lambda: FakeLibrarian(self.tmp.name)
        self.client = TestClient(api)
        self.db = open_store(Path(self.tmp.name) / STORE_FILE)
        self.up = lambda t, n, g: repo.upsert_entity(self.db, t, n, mbid=g)[0]
        repo.upsert_entity(self.db, "recording", "Take", mbid="r-gid")

    def member(self, who, band, begin=None, end=None, **kw):
        repo.add_edge(self.db, who, band, "member of band", valid_from=begin, valid_to=end, **{**SRC, **kw})

    def lines(self, artist_mbid):
        self.db.commit()
        r = self.client.get("/api/knowledge/song-facts", params={"mbid": "r-gid", "artist_mbid": artist_mbid})
        self.assertEqual(r.status_code, 200, r.text)
        return [f for f in r.json()["facts"] if f["kind"] == "member_lineage"]

    def test_dated_line_says_left_then_joined_and_links_the_other_band(self):
        band, other, dave = self.up("artist", "Metallica", "m"), self.up("artist", "Megadeth", "x"), self.up("artist", "Dave Mustaine", "d")
        self.member(dave, band, "1981", "1983-04")
        self.member(dave, other, "1983-06")
        (line,) = self.lines("m")
        self.assertEqual(line["text"], "Dave Mustaine was in Metallica until 1983 and joined Megadeth in 1983")
        self.assertEqual(line["scope"], "artist")
        self.assertEqual(line["source"], "MusicBrainz")
        self.assertEqual(line["link"], {"type": "artist", "mbid": "x"})

    def test_without_stated_years_the_line_only_says_also_and_dated_comes_first(self):
        band, a, b = self.up("artist", "Cream", "c"), self.up("artist", "Blind Faith", "bf"), self.up("artist", "Traffic", "tr")
        eric, steve = self.up("artist", "Eric C", "e"), self.up("artist", "Steve W", "s")
        self.member(eric, band); self.member(eric, a)
        self.member(steve, band, "1960", "1970"); self.member(steve, b, "1972")
        texts = [l["text"] for l in self.lines("c")]
        self.assertEqual(texts, ["Steve W was in Cream until 1970 and joined Traffic in 1972", "Eric C of Cream was also in Blind Faith"])

    def test_own_projects_and_the_artist_itself_are_skipped_but_the_word_the_is_not_a_match(self):
        band, trio, same, other = (self.up("artist", n, g) for n, g in
                                   (("The Beatles", "b"), ("John Lennon Trio", "t"), ("The Beatles", "b2"), ("The Headhunters", "h")))
        john = self.up("artist", "John Lennon", "j")
        for target in (band, trio, same, other):
            self.member(john, target)
        self.assertEqual([l["link"]["mbid"] for l in self.lines("b")], ["h"])

    def test_person_artist_gets_the_bands_they_belonged_to_and_the_cap_applies(self):
        person = self.up("artist", "Solo Sam", "p")
        bands = [self.up("artist", f"Band {c}", f"bd{c}") for c in "ABC"]
        for b in bands:
            self.member(person, b)
        lines = self.lines("p")
        self.assertEqual(len(lines), 1)  # one line per member: the person is the member in every row
        self.assertEqual(lines[0]["text"], "Solo Sam was also a member of Band A")

    def test_inferred_edges_and_bands_without_members_give_no_line(self):
        band, a, b = self.up("artist", "Alpha", "a"), self.up("artist", "Omega", "o"), self.up("artist", "Delta", "d")
        man = self.up("artist", "Mia", "mi")
        self.member(man, band)
        self.member(man, a, evidence_class="inferred")
        self.member(man, b, match_quality="fuzzy_unconfirmed")
        self.assertEqual(self.lines("a"), [])  # Alpha's member reaches the others only by non-credit-grade edges

    def test_a_member_with_an_open_or_returning_tenure_is_never_said_to_have_left(self):
        band, other, josh = self.up("artist", "Desert Band", "q"), self.up("artist", "Side Act", "s"), self.up("artist", "Josh H", "j")
        self.member(josh, band, "1996", "1996")
        self.member(josh, band, "1997", role="second stint")  # back in the band, no end stated
        self.member(josh, other, "1998")
        (line,) = self.lines("q")
        self.assertEqual(line["text"], "Josh H of Desert Band was also in Side Act")
