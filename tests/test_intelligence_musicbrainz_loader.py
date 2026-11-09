import unittest

from intelligence.musicbrainz import loader
from intelligence.musicbrainz.neighbourhood import Neighbourhood
from intelligence.store import repositories as repo
from intelligence.store.db import open_store


class FakeDump:
    def __init__(self, tables):
        self.tables, self.reads = tables, 0

    def __call__(self, wanted):
        self.reads += 1
        for name in wanted:
            if name in self.tables:
                yield name, iter(self.tables[name])


def ent(i, gid, name, **extra):
    return {"id": str(i), "gid": gid, "name": name, **extra}


def lnk(a, b, link):
    return {"entity0": str(a), "entity1": str(b), "link": str(link)}


def link_row(i, type_id, y=None, m=None, d=None):
    return {"id": str(i), "link_type": str(type_id), "begin_date_year": y, "begin_date_month": m,
            "begin_date_day": d, "end_date_year": None, "end_date_month": None, "end_date_day": None}


def world():
    return FakeDump({
        "artist": [ent(1, "A-GID", "Alpha", sort_name="Alpha"), ent(2, "B-GID", "Beta"), ent(3, "C-GID", "Gamma")],
        "recording": [ent(20, "R-GID", "Song")],
        "link_type": [{"id": "100", "name": "instrument"}, {"id": "101", "name": "producer"}],
        "link_attribute_type": [{"id": "5", "name": "guitar"}, {"id": "6", "name": "additional"}],
        "l_artist_recording": [lnk(2, 20, 7), lnk(3, 20, 8), lnk(2, 20, 9)],
        "l_artist_artist": [lnk(1, 2, 10)],
        "link": [link_row(7, 100, 1971, 5), link_row(8, 101), link_row(9, 100), link_row(10, 100)],
        "link_attribute": [{"link": "7", "attribute_type": "5"}, {"link": "7", "attribute_type": "6"}],
    })


def selection(**kw):
    n = Neighbourhood()
    n.selected = {k: set(v) for k, v in kw.items()}
    return n


def facts_world():
    return FakeDump({
        "artist": [
            ent(1, "A-GID", "Alpha", begin_date_year="1926", begin_date_month="5", begin_date_day="26",
                end_date_year="1991", end_date_month="9", end_date_day="28", ended="t"),
            ent(2, "B-GID", "Beta", begin_date_year="1969", ended="f"),
            ent(3, "C-GID", "Gamma", ended="f"),
        ],
        "release": [ent(30, "REL-1", "First", status="1"), ent(31, "REL-2", "Second", status="9"),
                    ent(32, "REL-3", "Third")],
        "release_status": [{"id": "1", "name": "Official"}, {"id": "9", "name": "Surprise"}],
        "iso_3166_1": [{"area": "222", "code": "US"}, {"area": "221", "code": "GB"}, {"area": "5", "code": "XYZ"}],
        "release_country": [
            {"release": "30", "country": "222", "date_year": "1959", "date_month": "8", "date_day": "17"},
            {"release": "30", "country": "221", "date_year": "1959", "date_month": "8", "date_day": "10"},
            {"release": "31", "country": "5", "date_year": None, "date_month": None, "date_day": None},
        ],
        "release_unknown_country": [{"release": "32", "date_year": "1971", "date_month": None, "date_day": None}],
        "link_type": [], "link_attribute_type": [],
    })


class FactsTests(unittest.TestCase):
    def setUp(self):
        self.db = open_store(":memory:")
        self.result = loader.load_neighbourhood(
            self.db, facts_world(), selection(artist={1, 2, 3}, release={30, 31, 32}),
            dump_timestamp="2026-11-04", schema_sequence=31)

    def span(self, mbid):
        entity = repo.find_entity(self.db, "artist", mbid=mbid)
        row = self.db.execute("SELECT * FROM artist_life_span WHERE entity_id = ?", (entity["id"],)).fetchone()
        return None if row is None else (row["begin_date"], row["end_date"], row["ended"])

    def release(self, mbid):
        entity = repo.find_entity(self.db, "release", mbid=mbid)
        row = self.db.execute("SELECT * FROM release_facts WHERE entity_id = ?", (entity["id"],)).fetchone()
        return None if row is None else (row["date"], row["country"], row["status"])

    def test_artist_life_span_keeps_partial_dates_and_ended(self):
        self.assertEqual(self.span("a-gid"), ("1926-05-26", "1991-09-28", 1))
        self.assertEqual(self.span("b-gid"), ("1969", None, 0))
        self.assertIsNone(self.span("c-gid"))  # nothing stated, nothing stored
        self.assertEqual(self.result.life_spans, 2)

    def test_release_takes_earliest_dated_row_with_its_country_and_status(self):
        self.assertEqual(self.release("rel-1"), ("1959-08-10", "GB", "official"))

    def test_unknown_country_and_unreadable_values_are_dropped_not_guessed(self):
        self.assertEqual(self.release("rel-3"), ("1971", None, None))
        self.assertIsNone(self.release("rel-2"))  # undated, bad country code, status not in MusicBrainz's list
        self.assertEqual(self.result.release_facts, 2)

    def test_rerun_overwrites_and_keeps_one_row(self):
        loader.load_neighbourhood(self.db, facts_world(), selection(artist={1, 2, 3}, release={30, 31, 32}),
                                  dump_timestamp="2026-11-04", schema_sequence=31)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM artist_life_span").fetchone()[0], 2)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM release_facts").fetchone()[0], 2)

    def test_fact_tables_add_no_pass(self):
        self.assertEqual(self.result.passes, 3)  # entities, (empty) links, and the context pass


class LoaderTests(unittest.TestCase):
    def setUp(self):
        self.db = open_store(":memory:")
        self.run_load = lambda source=None, n=None: loader.load_neighbourhood(
            self.db, source or world(), n or selection(artist={1, 2, 3}, recording={20}),
            dump_timestamp="2026-11-04 00:22:22+00", schema_sequence=31)

    def test_creates_entities_and_edges_with_provenance(self):
        result = self.run_load()
        self.assertEqual((result.entities_created, result.edges_created, result.passes), (4, 4, 4))
        rec = repo.find_entity(self.db, "recording", mbid="r-gid")
        edges = repo.edges_to(self.db, rec["id"])
        by_role = {e["role"]: e for e in edges if e["relation"] == "instrument"}
        guitar = by_role["additional, guitar"]
        self.assertEqual(guitar["valid_from"], "1971-05")
        self.assertEqual((guitar["evidence_class"], guitar["match_quality"], guitar["source"]),
                         ("source_explicit", "exact_mbid", "musicbrainz_dump"))
        self.assertEqual(guitar["source_url"], "https://musicbrainz.org/artist/b-gid")
        obs = repo.get_observation(self.db, guitar["observation_id"])
        self.assertEqual(obs["payload"]["schema_sequence"], 31)
        self.assertIn(None, by_role)  # plain instrument link without attributes

    def test_edge_needs_both_ends_selected(self):
        result = self.run_load(n=selection(artist={2, 3}, recording={20}))
        self.assertEqual(result.edges_created, 3)  # the artist 1 -> 2 link is dropped

    def test_existing_owned_entity_is_reused_not_changed(self):
        owned, _ = repo.upsert_entity(self.db, "artist", "My Alpha", mbid="a-gid", owned=True)
        result = self.run_load()
        self.assertEqual(result.entities_existing, 1)
        row = repo.get_entity(self.db, owned)
        self.assertEqual((row["canonical_name"], row["owned"]), ("My Alpha", 1))

    def test_rerun_adds_nothing(self):
        self.run_load()
        again = self.run_load()
        self.assertEqual((again.entities_created, again.edges_created, again.edges_existing), (0, 0, 4))

    def test_link_without_type_is_dropped_and_counted(self):
        source = world()
        source.tables["link"] = [link_row(7, 999)]
        result = self.run_load(source)
        self.assertEqual(result.edges_created, 0)
        self.assertEqual(result.links_dropped_no_type, 4)

    def test_failure_rolls_back_everything(self):
        source = world()
        source.tables["link"] = [{"id": "7"}]  # missing columns -> KeyError in pass 3
        with self.assertRaises(KeyError):
            self.run_load(source)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM entities").fetchone()[0], 0)

    def test_fixed_passes(self):
        source = world()
        self.run_load(source)
        self.assertEqual(source.reads, 4)

    def test_no_link_detail_pass_without_links(self):
        source = world()
        result = self.run_load(source, selection(artist={3}))
        self.assertEqual((result.passes, source.reads, result.edges_created), (3, 3, 0))

    def counts(self):
        return tuple(self.db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("entities", "edges"))

    def without_artist_link(self):
        source = world()
        source.tables["l_artist_artist"] = []
        return source

    def test_replacement_removes_edges_and_orphans_that_left_the_dump(self):
        self.run_load()
        result = self.run_load(self.without_artist_link())
        self.assertEqual((result.edges_removed, result.entities_removed, result.edges_existing), (1, 1, 3))
        self.assertEqual(self.counts(), (3, 3))
        self.assertIsNone(repo.find_entity(self.db, "artist", mbid="a-gid"))
        self.assertIsNotNone(repo.find_entity(self.db, "artist", mbid="b-gid"))

    def test_replacement_keeps_owned_entities(self):
        repo.upsert_entity(self.db, "artist", "My Alpha", mbid="a-gid", owned=True)
        self.run_load()
        result = self.run_load(self.without_artist_link())
        self.assertEqual((result.edges_removed, result.entities_removed), (1, 0))
        self.assertIsNotNone(repo.find_entity(self.db, "artist", mbid="a-gid"))

    def test_replacement_keeps_other_sources_edges(self):
        self.run_load()
        a = repo.find_entity(self.db, "artist", mbid="a-gid")["id"]
        b = repo.find_entity(self.db, "artist", mbid="b-gid")["id"]
        repo.add_edge(self.db, a, b, "mentor", source="user", evidence_class="user_confirmed",
                      match_quality="exact_mbid")
        result = self.run_load(self.without_artist_link())
        self.assertEqual((result.edges_removed, result.entities_removed), (1, 0))
        self.assertIsNotNone(repo.find_entity(self.db, "artist", mbid="a-gid"))

    def test_too_small_new_dump_is_refused_and_changes_nothing(self):
        self.run_load()
        before = self.counts()
        thin = world()
        thin.tables["l_artist_recording"] = [lnk(2, 20, 7)]
        thin.tables["l_artist_artist"] = []
        with self.assertRaises(loader.SliceValidationError):
            self.run_load(thin)
        self.assertEqual(self.counts(), before)

    def test_first_load_is_never_refused(self):
        self.assertEqual(self.run_load().edges_removed, 0)


if __name__ == "__main__":
    unittest.main()


class ReleaseGroupTypeTests(unittest.TestCase):
    def test_primary_and_secondary_types_are_stored_for_selected_groups(self):
        dump = FakeDump({
            "artist": [ent(1, "A-GID", "Alpha")],
            "release_group": [ent(40, "RG-1", "Studio LP", type="1"), ent(41, "RG-2", "Live LP", type="1"), ent(42, "RG-3", "Untyped")],
            "release_group_primary_type": [{"id": "1", "name": "Album"}],
            "release_group_secondary_type": [{"id": "6", "name": "Live"}],
            "release_group_secondary_type_join": [{"release_group": "41", "secondary_type": "6"}],
            "link_type": [], "link_attribute_type": [],
        })
        db = open_store(":memory:")
        loader.load_neighbourhood(db, dump, selection(artist={1}, release_group={40, 41, 42}), dump_timestamp="2026-11-04", schema_sequence=31)

        def facts(mbid):
            e = repo.find_entity(db, "release_group", mbid=mbid)
            row = db.execute("SELECT primary_type, secondary_types FROM release_group_facts WHERE entity_id = ?", (e["id"],)).fetchone()
            return None if row is None else (row["primary_type"], row["secondary_types"])

        self.assertEqual(facts("rg-1"), ("Album", "[]"))
        self.assertEqual(facts("rg-2"), ("Album", '["Live"]'))
        self.assertIsNone(facts("rg-3"))       # nothing stated, nothing stored
