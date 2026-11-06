import unittest
from urllib.parse import parse_qs, urlparse

from intelligence.musicbrainz.api_fill import ApiError, Paced
from intelligence.store import repositories as repo
from intelligence.store.db import open_store
from intelligence.wikidata import ingest


def item(qid, statement="S", rank="normal"):
    return {"id": statement, "rank": rank, "mainsnak": {"snaktype": "value", "datavalue": {"value": {"id": qid}}}}


def when(time, precision):
    return {"id": "T", "rank": "normal", "mainsnak": {"snaktype": "value",
            "datavalue": {"value": {"time": time, "precision": precision}}}}


class Clock:
    t = 1000.0

    def __call__(self):
        return self.t


class WikidataIngestTests(unittest.TestCase):
    def setUp(self):
        self.db = open_store(":memory:")
        self.clock = Clock()
        self.urls = []
        mk = repo.upsert_entity
        self.alpha = mk(self.db, "artist", "Alpha", mbid="a" * 8 + "-0000-4000-8000-000000000001", owned=True)[0]
        self.beta = mk(self.db, "artist", "Beta", mbid="a" * 8 + "-0000-4000-8000-000000000002")[0]
        self.rock = mk(self.db, "genre", "Rock", mbid="b" * 8 + "-0000-4000-8000-000000000001")[0]
        self.town = mk(self.db, "area", "Town", mbid="c" * 8 + "-0000-4000-8000-000000000001")[0]
        with self.db:
            for eid, qid in ((self.alpha, "Q1"), (self.beta, "Q2"), (self.rock, "Q3"), (self.town, "Q4")):
                self.db.execute("UPDATE entities SET wikidata_id = ? WHERE id = ?", (qid, eid))
            self.db.execute("INSERT INTO meta (key, value) VALUES ('musicbrainz_slice.loaded_at', '1')")
        self.entity = {"claims": {
            "P737": [item("Q2", "S1"), item("Q999", "S2"), item("Q2", "S3", rank="deprecated")],
            "P136": [item("Q3", "S4")], "P740": [item("Q4", "S5")],
            "P571": [when("+1970-05-00T00:00:00Z", 10)], "P576": [when("+1990-00-00T00:00:00Z", 9)]}}

    def fetch(self, url):
        self.urls.append(url)
        ids = parse_qs(urlparse(url).query)["ids"][0].split("|")
        return {"entities": {i: self.entity if i == "Q1" else {"missing": ""} for i in ids}}

    def run_it(self, **kw):
        kw.setdefault("fetch", Paced(self.fetch, sleep=lambda s: None))
        return ingest.run_wikidata_ingest(self.db, clock=self.clock, **kw)

    def edges(self):
        return {(r["relation"], r["to_id"], r["source_url"]) for r in self.db.execute(
            "SELECT relation, to_id, source_url FROM edges WHERE source = 'wikidata'")}

    def test_writes_known_targets_with_statement_provenance_and_skips_the_rest(self):
        result = self.run_it()
        self.assertEqual(result.state, "succeeded")
        self.assertEqual(len(self.urls), 1)
        stmt = "https://www.wikidata.org/entity/statement/"
        self.assertEqual(self.edges(), {("influenced by", self.beta, stmt + "S1"), ("genre", self.rock, stmt + "S4"),
                                        ("formed in", self.town, stmt + "S5")})
        self.assertEqual(result.progress["targets_unknown"], 1)
        row = self.db.execute("SELECT evidence_class, match_quality FROM edges WHERE source = 'wikidata'").fetchone()
        self.assertEqual(tuple(row), ("source_explicit", "exact_mbid"))

    def test_dates_fill_only_when_musicbrainz_stated_none(self):
        self.run_it()
        span = self.db.execute("SELECT begin_date, end_date, ended FROM artist_life_span WHERE entity_id = ?",
                               (self.alpha,)).fetchone()
        self.assertEqual(tuple(span), ("1970-05", "1990", 1))
        self.db.execute("DELETE FROM source_state")
        self.db.execute("UPDATE artist_life_span SET begin_date = '1971'")
        self.run_it()
        self.assertEqual(self.db.execute("SELECT begin_date FROM artist_life_span").fetchone()[0], "1971")

    def test_preferred_hides_normal_and_decade_precision_is_ignored(self):
        got = ingest.claims({"claims": {"P737": [item("Q2", "A"), item("Q5", "B", rank="preferred")],
                                        "P571": [when("+1970-00-00T00:00:00Z", 8)]}})
        self.assertEqual([c["qid"] for c in got["P737"]], ["Q5"])
        self.assertNotIn("P571", got)

    def test_second_run_makes_no_request(self):
        self.run_it()
        self.urls.clear()
        self.run_it()
        self.assertEqual(self.urls, [])

    def test_no_slice_no_request(self):
        self.db.execute("DELETE FROM meta")
        self.assertEqual(self.run_it().progress["stopped"], "no_slice")
        self.assertEqual(self.urls, [])

    def test_three_failures_stop_the_run_and_back_off(self):
        for i in range(120):
            e = repo.upsert_entity(self.db, "artist", f"X{i}", mbid=f"d{i:07d}-0000-4000-8000-000000000001", owned=True)[0]
            self.db.execute("UPDATE entities SET wikidata_id = ? WHERE id = ?", (f"Q{1000 + i}", e))

        def boom(url):
            self.urls.append(url)
            raise ApiError(500)
        result = self.run_it(fetch=Paced(boom, sleep=lambda s: None))
        self.assertEqual(result.progress["stopped"], "failures")
        self.assertEqual(len(self.urls), 3)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM source_state WHERE outcome = 'error'").fetchone()[0], 121)

    def test_request_budget(self):
        result = self.run_it(max_requests=0)
        self.assertEqual(self.urls, [])
        self.assertEqual(result.progress["stopped"], "request_budget")


if __name__ == "__main__":
    unittest.main()
