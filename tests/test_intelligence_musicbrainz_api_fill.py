import unittest
from urllib.parse import parse_qs, urlparse

from intelligence.musicbrainz import api_fill
from intelligence.musicbrainz.api_fill import ApiError, Paced
from intelligence.store import repositories as repo
from intelligence.store import source_state
from intelligence.store.db import open_store

ARTIST = "aaaaaaaa-0000-4000-8000-000000000001"
ARTIST2 = "aaaaaaaa-0000-4000-8000-000000000002"
REL = "bbbbbbbb-0000-4000-8000-000000000001"
REL2 = "bbbbbbbb-0000-4000-8000-000000000002"
REC = "cccccccc-0000-4000-8000-000000000001"
WORK = "dddddddd-0000-4000-8000-000000000001"
PERSON = "eeeeeeee-0000-4000-8000-000000000001"
LABEL = "ffffffff-0000-4000-8000-000000000001"
WRITER = "eeeeeeee-0000-4000-8000-000000000002"


def release_payload(mbid=REL):
    return {
        "id": mbid, "title": "Album", "date": "1999-05", "country": "gb", "status": "Official",
        "relations": [
            {"type": "producer", "target-type": "artist", "direction": "backward", "attributes": [],
             "artist": {"id": PERSON, "name": "Producer P"}},
            {"type": "publisher", "target-type": "label", "direction": "backward", "attributes": [],
             "label": {"id": LABEL, "name": "Label L"}},
            {"type": "amazon asin", "target-type": "url", "direction": "forward", "url": {"id": "u", "resource": "x"}},
        ],
        "media": [{"tracks": [{"recording": {"id": REC, "title": "Song", "relations": [
            {"type": "instrument", "target-type": "artist", "direction": "backward", "attributes": ["guitar", "additional"],
             "begin": "1998-01", "end": "bad", "artist": {"id": PERSON, "name": "Producer P"}},
            {"type": "performance", "target-type": "work", "direction": "forward", "attributes": [],
             "work": {"id": WORK, "title": "Tune", "relations": [
                 {"type": "composer", "target-type": "artist", "direction": "backward", "attributes": [],
                  "artist": {"id": WRITER, "name": "Writer W"}}]}},
        ]}}]}],
    }


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class ApiFillTests(unittest.TestCase):
    def setUp(self):
        self.db = open_store(":memory:")
        self.clock = Clock()
        self.urls = []
        self.artist_id = repo.upsert_entity(self.db, "artist", "Alpha", mbid=ARTIST, owned=True)[0]
        self.release_id = repo.upsert_entity(self.db, "release", "Album", mbid=REL, owned=True)[0]
        with self.db:
            self.db.execute("INSERT INTO meta (key, value) VALUES ('musicbrainz_slice.loaded_at', '1')")
        self.responses = {}

    def fetch(self, url):
        self.urls.append(url)
        if "/artist?" in url:
            return {"artists": [{"id": ARTIST, "life-span": {"begin": "1970-05", "end": "2001", "ended": True}}]}
        mbid = urlparse(url).path.rsplit("/", 1)[1]
        out = self.responses.get(mbid, release_payload(mbid))
        if isinstance(out, ApiError):
            raise out
        return out

    def run_fill(self, **kw):
        kw.setdefault("fetch", Paced(self.fetch, sleep=lambda s: None))
        return api_fill.run_api_fill(self.db, clock=self.clock, **kw)

    def edges(self, source=api_fill.SOURCE):
        return {(r["f"], r["t"], r["relation"], r["role"], r["source"]) for r in self.db.execute(
            "SELECT a.type||':'||a.mbid f, b.type||':'||b.mbid t, relation, role, source FROM edges "
            "JOIN entities a ON a.id = from_id JOIN entities b ON b.id = to_id WHERE source = ?", (source,))}

    def test_nothing_runs_before_a_dump_is_loaded(self):
        self.db.execute("DELETE FROM meta WHERE key = 'musicbrainz_slice.loaded_at'")
        result = self.run_fill()
        self.assertEqual(result.progress["stopped"], "no_slice")
        self.assertEqual(self.urls, [])

    def test_fills_life_span_with_one_batch_request_and_release_with_one_lookup(self):
        result = self.run_fill()
        self.assertEqual(result.state, "succeeded")
        self.assertEqual(len(self.urls), 2)
        query = parse_qs(urlparse(self.urls[0]).query)["query"][0]
        self.assertEqual(query, f"arid:({ARTIST})")
        self.assertIn("inc=artist-rels+label-rels+recordings+recording-level-rels+work-rels+work-level-rels", self.urls[1])
        span = self.db.execute("SELECT begin_date, end_date, ended FROM artist_life_span WHERE entity_id = ?",
                               (self.artist_id,)).fetchone()
        self.assertEqual(tuple(span), ("1970-05", "2001", 1))
        facts = self.db.execute("SELECT date, country, status FROM release_facts WHERE entity_id = ?",
                                (self.release_id,)).fetchone()
        self.assertEqual(tuple(facts), ("1999-05", "GB", "official"))

    def test_edges_are_oriented_like_the_dump_and_carry_provenance(self):
        self.run_fill()
        self.assertEqual(self.edges(), {
            (f"artist:{PERSON}", f"release:{REL}", "producer", None, "musicbrainz_api"),
            (f"label:{LABEL}", f"release:{REL}", "publisher", None, "musicbrainz_api"),
            (f"artist:{PERSON}", f"recording:{REC}", "instrument", "additional, guitar", "musicbrainz_api"),
            (f"recording:{REC}", f"work:{WORK}", "performance", None, "musicbrainz_api"),
            (f"artist:{WRITER}", f"work:{WORK}", "composer", None, "musicbrainz_api"),
        })
        row = self.db.execute("SELECT * FROM edges WHERE relation = 'instrument'").fetchone()
        self.assertEqual((row["evidence_class"], row["match_quality"], row["valid_from"], row["valid_to"]),
                         ("source_explicit", "exact_mbid", "1998-01", None))  # malformed date dropped
        self.assertTrue(row["observation_id"])
        self.assertTrue(row["source_url"].startswith("https://musicbrainz.org/artist/"))

    def test_second_run_makes_no_request_and_adds_nothing(self):
        self.run_fill()
        edges = self.edges()
        self.urls.clear()
        self.run_fill()
        self.assertEqual(self.urls, [])
        self.assertEqual(self.edges(), edges)

    def test_refetch_after_the_refresh_time_is_idempotent(self):
        self.run_fill()
        edges = self.edges()
        self.clock.t += api_fill.REFRESH_TTL + 1
        self.urls.clear()
        self.run_fill()
        self.assertEqual(len(self.urls), 1)  # the life span exists already; only the release is asked again
        self.assertEqual(self.edges(), edges)

    def test_release_covered_by_the_dump_costs_no_request(self):
        other = repo.upsert_entity(self.db, "artist", "P", mbid=PERSON)[0]
        repo.add_edge(self.db, other, self.release_id, "producer", evidence_class="source_explicit",
                      match_quality="exact_mbid", source="musicbrainz_dump")
        self.run_fill()
        self.assertFalse(any("/release/" in u for u in self.urls))

    def test_unowned_and_mbidless_entities_are_never_asked(self):
        repo.upsert_entity(self.db, "release", "Other", mbid=REL2)
        repo.upsert_entity(self.db, "release", "No id", owned=True, navidrome_id="n1")
        self.run_fill()
        self.assertEqual([u for u in self.urls if "/release/" in u], [u for u in self.urls if REL in u])
        self.assertFalse(any(REL2 in u for u in self.urls))
        self.assertEqual(len(self.urls), 2)

    def test_request_budget_stops_the_run_and_says_so(self):
        repo.upsert_entity(self.db, "release", "Two", mbid=REL2, owned=True)
        result = self.run_fill(max_requests=2)
        self.assertEqual(len(self.urls), 2)
        self.assertEqual(result.progress["stopped"], "request_budget")
        self.assertEqual(result.progress["pending_releases"], 1)
        self.urls.clear()
        again = self.run_fill(max_requests=2)  # resumes with what is left
        self.assertEqual(len(self.urls), 1)
        self.assertIsNone(again.progress["stopped"])

    def test_missing_release_is_recorded_not_found_and_not_retried(self):
        self.responses[REL] = ApiError(404)
        self.run_fill()
        self.assertEqual(source_state.status(self.db, "musicbrainz_api", "release_lookup", REL), "not_found")
        self.urls.clear()
        self.run_fill()
        self.assertEqual([u for u in self.urls if "/release/" in u], [])

    def test_failures_back_off_and_three_in_a_row_stop_the_run(self):
        ids = [REL2, "bbbbbbbb-0000-4000-8000-000000000003", "bbbbbbbb-0000-4000-8000-000000000004",
               "bbbbbbbb-0000-4000-8000-000000000005"]
        for m in ids:
            repo.upsert_entity(self.db, "release", m, mbid=m, owned=True)
            self.responses[m] = ApiError(500)
        self.responses[REL] = ApiError(500)
        result = self.run_fill()
        self.assertEqual(result.progress["stopped"], "failures")
        self.assertEqual(result.progress["failures"], 3)
        self.assertEqual(len([u for u in self.urls if "/release/" in u]), 3)
        state = source_state.get_state(self.db, "musicbrainz_api", "release_lookup", REL)
        self.assertEqual((state["outcome"], state["attempts"]), ("error", 1))
        self.assertGreater(state["next_refresh_at"], self.clock.t)

    def test_503_is_retried_once_after_a_pause(self):
        calls, sleeps = [], []

        def flaky(url):
            calls.append(url)
            if len(calls) == 1:
                raise ApiError(503)
            return {"artists": []}

        paced = Paced(flaky, sleep=sleeps.append, monotonic=lambda: 0.0)
        paced("u")
        self.assertEqual(len(calls), 2)
        self.assertEqual(sleeps, [api_fill.RETRY_PAUSE])

    def test_requests_are_spaced(self):
        sleeps, now = [], [0.0]
        paced = Paced(lambda u: {}, sleep=sleeps.append, monotonic=lambda: now[0])
        paced("a")
        now[0] = 0.2
        paced("b")
        self.assertEqual(len(sleeps), 1)
        self.assertAlmostEqual(sleeps[0], api_fill.MIN_INTERVAL - 0.2)

    def test_artists_are_batched_25_to_a_request(self):
        for n in range(3, 33):
            repo.upsert_entity(self.db, "artist", f"A{n}", mbid=f"aaaaaaaa-0000-4000-8000-{n:012d}", owned=True)
        self.run_fill()
        self.assertEqual(len([u for u in self.urls if "/artist?" in u]), 2)  # 31 owned artists

    def test_absorb_drops_only_api_edges_the_dump_states(self):
        self.run_fill()
        person = repo.find_entity(self.db, "artist", mbid=PERSON)["id"]
        repo.add_edge(self.db, person, self.release_id, "producer", evidence_class="source_explicit",
                      match_quality="exact_mbid", source="musicbrainz_dump")
        self.assertEqual(api_fill.absorb_api_edges(self.db), 1)
        self.assertNotIn((f"artist:{PERSON}", f"release:{REL}", "producer", None, "musicbrainz_api"), self.edges())
        self.assertEqual(len(self.edges()), 4)


if __name__ == "__main__":
    unittest.main()
