import unittest

from intelligence.musicbrainz import context, loader
from intelligence.musicbrainz.neighbourhood import Neighbourhood
from intelligence.store import repositories as repo
from intelligence.store.db import open_store
from tests.test_intelligence_musicbrainz_loader import FakeDump, ent, link_row, lnk


def selection(**kw):
    n = Neighbourhood()
    n.selected = {k: set(v) for k, v in kw.items()}
    return n


def SEL():
    return selection(artist={1}, label={5}, recording={20, 21}, release={30}, release_group={40}, work={60})


def world():
    """Artist 1 (area Paris, begun in Dallas), label 5 (area Paris), recording 20 cut at place 70 in Paris."""
    return FakeDump({
        "artist": [ent(1, "A-GID", "Alpha", area="4434", begin_area="900", type="2"),
                   ent(2, "B-GID", "Beta", area="", type="1")],
        "artist_type": [{"id": "1", "name": "Person"}, {"id": "2", "name": "Group"}],
        "recording": [ent(20, "R-GID", "Song"), ent(21, "R2-GID", "Song (remix)")],
        "release": [ent(30, "REL-GID", "Album")],
        "release_group": [ent(40, "RG-GID", "Album RG")],
        "work": [ent(60, "W-GID", "Tune")],
        "area": [
            ent(4434, "AREA-PARIS", "Paris", type="3"), ent(1839, "AREA-IDF", "Île-de-France", type="2"),
            ent(73, "AREA-FR", "France", type="1"), ent(900, "AREA-DAL", "Dallas", type="3"),
            ent(222, "AREA-US", "United States", type="1"), ent(999, "AREA-UNUSED", "Unused", type="3"),
        ],
        "area_type": [{"id": "1", "name": "Country"}, {"id": "2", "name": "Subdivision"}, {"id": "3", "name": "City"}],
        "place": [ent(70, "PLACE-STUDIO", "Studio Davout", type="1", area="4434", coordinates="(48.85,2.41)",
                      begin_date_year="1970"),
                  ent(71, "PLACE-OTHER", "Elsewhere", type="2", area="999", coordinates="")],
        "place_type": [{"id": "1", "name": "Studio"}, {"id": "2", "name": "Venue"}],
        "iso_3166_1": [{"area": "73", "code": "FR"}, {"area": "222", "code": "US"}],
        "l_area_area": [lnk(73, 1839, 41), lnk(1839, 4434, 42), lnk(222, 900, 43), lnk(73, 999, 44)],
        "l_place_recording": [lnk(70, 20, 50), lnk(71, 777, 51)],
        "l_artist_place": [lnk(1, 70, 52)],
        "l_area_recording": [lnk(4434, 20, 53)],
        "l_artist_url": [{"entity0": "1", "entity1": "801"}, {"entity0": "1", "entity1": "802"},
                         {"entity0": "2", "entity1": "803"}, {"entity0": "1", "entity1": "808"}],
        "l_label_url": [{"entity0": "5", "entity1": "804"}],
        "l_area_url": [{"entity0": "4434", "entity1": "805"}],
        "l_place_url": [{"entity0": "70", "entity1": "806"}],
        "url": [{"id": "801", "url": "https://www.wikidata.org/wiki/Q42"},
                {"id": "802", "url": "https://www.wikidata.org/wiki/Q7"},
                {"id": "803", "url": "https://www.wikidata.org/wiki/Q9"},
                {"id": "804", "url": "https://www.wikidata.org/wiki/Q11"},
                {"id": "805", "url": "https://www.wikidata.org/wiki/Q90"},
                {"id": "806", "url": "https://www.wikidata.org/entity/Q5"},
                {"id": "808", "url": "https://www.discogs.com/artist/777-Alpha"},
                {"id": "807", "url": "https://www.discogs.com/master/12345-Album"}],
        "event": [ent(300, "EV-GID", "Jazz Night", begin_date_year="1971", begin_date_month="6", type="2",
                      cancelled="f"),
                  ent(301, "EV-OTHER", "Unrelated", type="2", cancelled="t")],
        "event_type": [{"id": "1", "name": "Concert"}, {"id": "2", "name": "Festival"}],
        "l_artist_event": [lnk(1, 300, 60)],
        "l_event_place": [lnk(300, 70, 61), lnk(301, 71, 62)],
        "l_area_event": [lnk(4434, 300, 63)],
        "l_event_recording": [lnk(300, 20, 64)],
        "genre": [ent(500, "G-JAZZ", "jazz"), ent(501, "G-BEBOP", "bebop")],
        "l_genre_genre": [lnk(500, 501, 65)],
        "l_area_genre": [lnk(222, 500, 66)],
        "release_label": [{"release": "30", "label": "5", "catalog_number": "BN 1577"},
                          {"release": "30", "label": "6", "catalog_number": "[none]"},
                          {"release": "30", "label": None, "catalog_number": "XX-1"}],
        "label": [ent(5, "L-GID", "Label One", area="4434"), ent(6, "L2-GID", "Parent Label", area="73")],
        "l_label_label": [lnk(6, 5, 67)],
        "medium": [{"release": "30", "position": "1", "format": "1"}, {"release": "30", "position": "2", "format": "1"},
                   {"release": "30", "position": "3", "format": "2"}],
        "medium_format": [{"id": "1", "name": "CD"}, {"id": "2", "name": "DVD-Video"}],
        "isrc": [{"recording": "20", "isrc": "frz039800212"}, {"recording": "21", "isrc": "FRZ039800213"}],
        "iswc": [{"work": "60", "iswc": "T-034.524.680-1"}],
        "l_recording_recording": [lnk(21, 20, 68), lnk(21, 999, 69)],
        "artist_alias": [{"artist": "1", "name": "Alpha"}, {"artist": "1", "name": "Alfa"}],
        "label_alias": [{"label": "5", "name": "L One"}],
        "area_alias": [{"area": "73", "name": "Frankreich"}],
        "place_alias": [{"place": "70", "name": "Davout"}],
        "l_release_group_url": [{"entity0": "40", "entity1": "807"}],
        "link_type": [{"id": "1", "name": "part of"}, {"id": "2", "name": "recording location"},
                      {"id": "3", "name": "owner"}, {"id": "4", "name": "recorded in"},
                      {"id": "5", "name": "main performer"}, {"id": "6", "name": "held at"},
                      {"id": "7", "name": "subgenre"}, {"id": "8", "name": "label ownership"},
                      {"id": "9", "name": "remix of"}, {"id": "10", "name": "genre origin"}],
        "link_attribute_type": [],
        "link": [link_row(41, 1), link_row(42, 1), link_row(43, 1), link_row(44, 1), link_row(50, 2),
                 link_row(52, 3, 1969), link_row(53, 4), link_row(60, 5, 1971), link_row(61, 6),
                 link_row(63, 4), link_row(64, 4), link_row(65, 7), link_row(66, 10), link_row(67, 8),
                 link_row(68, 9)],
    })


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.db = open_store(":memory:")
        self.result = loader.load_neighbourhood(
            self.db, world(), SEL(),
            dump_timestamp="2026-11-04", schema_sequence=31)

    def find(self, kind, gid):
        return repo.find_entity(self.db, kind, mbid=gid)

    def edges(self, kind, gid):
        entity = self.find(kind, gid)
        return {(e["relation"], e["from_id"] == entity["id"]): e for e in
                list(repo.edges_from(self.db, entity["id"])) + list(repo.edges_to(self.db, entity["id"]))}

    def test_only_referenced_areas_and_places_load(self):
        self.assertIsNone(self.find("area", "area-unused"))
        self.assertIsNone(self.find("place", "place-other"))
        self.assertEqual((self.result.context["areas"], self.result.context["places"]), (5, 1))

    def test_own_and_begin_area_edges_carry_provenance(self):
        edges = self.edges("artist", "a-gid")
        self.assertIn(("area", True), edges)
        self.assertIn(("begin area", True), edges)
        own = edges[("area", True)]
        self.assertEqual((own["evidence_class"], own["match_quality"], own["source"]),
                         ("source_explicit", "exact_mbid", "musicbrainz_dump"))
        self.assertEqual(own["source_url"], "https://musicbrainz.org/artist/a-gid")
        self.assertIsNotNone(own["observation_id"])

    def test_artist_without_area_gets_no_edge(self):
        self.assertIsNone(self.find("artist", "b-gid"))  # not selected, so absent
        db = open_store(":memory:")
        loader.load_neighbourhood(db, world(), selection(artist={2}), dump_timestamp="x", schema_sequence=31)
        artist = repo.find_entity(db, "artist", mbid="b-gid")
        self.assertEqual(list(repo.edges_from(db, artist["id"])), [])

    def test_label_area_edge(self):
        self.assertIn(("area", True), self.edges("label", "l-gid"))

    def test_containment_chain_is_child_part_of_parent(self):
        paris = self.edges("area", "area-paris")
        self.assertIn(("part of", True), paris)  # Paris -> Ile-de-France
        idf = self.edges("area", "area-idf")
        self.assertIn(("part of", True), idf)   # Ile-de-France -> France
        self.assertIn(("part of", False), idf)  # Paris is part of it
        self.assertIn(("part of", False), self.edges("area", "area-fr"))
        self.assertIn(("part of", True), self.edges("area", "area-dal"))  # Dallas -> United States

    def test_area_facts_kind_and_iso(self):
        fr = self.find("area", "area-fr")
        row = self.db.execute("SELECT kind, iso_code FROM area_facts WHERE entity_id = ?", (fr["id"],)).fetchone()
        self.assertEqual((row["kind"], row["iso_code"]), ("country", "FR"))
        paris = self.find("area", "area-paris")
        row = self.db.execute("SELECT kind, iso_code FROM area_facts WHERE entity_id = ?", (paris["id"],)).fetchone()
        self.assertEqual((row["kind"], row["iso_code"]), ("city", None))

    def test_place_facts_and_recording_location(self):
        place = self.find("place", "place-studio")
        row = self.db.execute("SELECT * FROM place_facts WHERE entity_id = ?", (place["id"],)).fetchone()
        self.assertEqual((row["kind"], row["latitude"], row["longitude"], row["begin_date"]),
                         ("studio", 48.85, 2.41, "1970"))
        edges = self.edges("place", "place-studio")
        self.assertIn(("recording location", True), edges)
        self.assertIn(("area", True), edges)
        self.assertEqual(edges[("owner", False)]["valid_from"], "1969")  # artist -> place

    def test_events_come_from_selected_artists_with_their_place_and_area(self):
        self.assertIsNone(self.find("event", "ev-other"))
        edges = self.edges("event", "ev-gid")
        self.assertIn(("main performer", False), edges)
        self.assertIn(("held at", True), edges)
        self.assertIn(("recorded in", False), edges)  # area of the event
        self.assertIn(("recorded in", True), edges)   # live recording
        row = self.db.execute("SELECT * FROM event_facts").fetchone()
        self.assertEqual((row["kind"], row["begin_date"], row["cancelled"]), ("festival", "1971-06", 0))
        self.assertEqual(self.result.context["events"], 1)

    def test_genres_with_parent_and_origin(self):
        self.assertIn(("subgenre", True), self.edges("genre", "g-jazz"))
        self.assertIn(("genre origin", False), self.edges("genre", "g-jazz"))
        self.assertIsNotNone(self.find("area", "area-us"))

    def test_release_labels_catalogue_numbers_and_late_label(self):
        parent = self.find("label", "l2-gid")
        self.assertIsNotNone(parent)  # reached only through a release and a label relationship
        rows = self.db.execute("SELECT l.mbid, r.catalogue_number FROM release_labels r "
                               "LEFT JOIN entities l ON l.id = r.label_id ORDER BY 1, 2").fetchall()
        self.assertEqual([(r[0], r[1]) for r in rows], [(None, "XX-1"), ("l-gid", "BN 1577"), ("l2-gid", None)])
        self.assertIn(("release label", True), self.edges("label", "l-gid"))
        self.assertIn(("label ownership", True), self.edges("label", "l2-gid"))  # parent -> sub-label
        self.assertIn(("area", True), self.edges("label", "l2-gid"))

    def test_release_formats(self):
        release = self.find("release", "rel-gid")
        row = self.db.execute("SELECT formats FROM release_facts WHERE entity_id = ?", (release["id"],)).fetchone()
        self.assertEqual(row[0], "2×CD + DVD-Video")

    def test_identifiers_aliases_and_artist_kind(self):
        codes = {(r[0], r[1]) for r in self.db.execute("SELECT scheme, value FROM entity_identifiers")}
        self.assertEqual(codes, {("isrc", "FRZ039800212"), ("isrc", "FRZ039800213"), ("iswc", "T-034.524.680-1")})
        self.assertEqual(sorted(a for a, _ in repo.aliases(self.db, self.find("artist", "a-gid")["id"])), ["Alfa"])
        self.assertEqual(repo.aliases(self.db, self.find("area", "area-fr")["id"]), [("Frankreich", "mb_alias")])
        self.assertEqual(len(repo.find_entities_by_name(self.db, "place", "Davout")), 1)
        self.assertEqual(self.db.execute("SELECT kind FROM artist_facts").fetchone()[0], "group")

    def test_remix_links_need_both_ends_selected(self):
        self.assertIn(("remix of", True), self.edges("recording", "r2-gid"))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM edges WHERE relation = 'remix of'").fetchone()[0], 1)

    def test_discogs_ids_by_page_type(self):
        self.assertEqual(self.find("artist", "a-gid")["discogs_id"], "777")
        self.assertEqual(self.find("release_group", "rg-gid")["discogs_id"], "12345")
        self.assertEqual(self.find("release_group", "rg-gid")["wikidata_id"], None)

    def test_event_cap_is_reported(self):
        from unittest import mock
        db = open_store(":memory:")
        with mock.patch.object(context, "MAX_EVENTS", 0):
            result = loader.load_neighbourhood(db, world(), SEL(), dump_timestamp="x", schema_sequence=31)
        self.assertTrue(result.context["events_truncated"])
        self.assertIsNone(repo.find_entity(db, "event", mbid="ev-gid"))

    def test_area_of_recording(self):
        self.assertIn(("recorded in", True), self.edges("area", "area-paris"))

    def test_wikidata_ids_prefer_lowest_and_ignore_other_hosts(self):
        self.assertEqual(self.find("artist", "a-gid")["wikidata_id"], "Q7")  # lowest of Q42 and Q7 by number
        self.assertEqual(self.find("label", "l-gid")["wikidata_id"], "Q11")
        self.assertEqual(self.find("area", "area-paris")["wikidata_id"], "Q90")
        self.assertIsNone(self.find("place", "place-studio")["wikidata_id"])  # /entity/ form is not a page link
        self.assertEqual(self.result.context["wikidata_ids"], 3)

    def test_rerun_is_stable_and_counts_no_new_ids(self):
        before = tuple(self.db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("entities", "edges"))
        again = loader.load_neighbourhood(
            self.db, world(), SEL(), dump_timestamp="2026-11-04",
            schema_sequence=31)
        after = tuple(self.db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("entities", "edges"))
        self.assertEqual((before, again.context["wikidata_ids"], again.edges_created), (after, 0, 0))

    def test_replacement_drops_context_edges_that_left_the_dump(self):
        source = world()
        source.tables["l_place_recording"] = []
        result = loader.load_neighbourhood(
            self.db, source, SEL(), dump_timestamp="2026-11-05",
            schema_sequence=31)
        self.assertGreaterEqual(result.edges_removed, 1)
        self.assertNotIn(("recording location", True), self.edges("place", "place-studio"))


class ParsingTests(unittest.TestCase):
    def test_point_is_latitude_then_longitude_and_bounded(self):
        self.assertEqual(context.parse_point("(58.588056,16.184444)"), (58.588056, 16.184444))
        self.assertIsNone(context.parse_point("(95,10)"))
        self.assertIsNone(context.parse_point("garbage"))
        self.assertIsNone(context.parse_point(None))

    def test_wikidata_id_needs_an_item_page(self):
        self.assertEqual(context.wikidata_id("https://www.wikidata.org/wiki/Q42"), "Q42")
        self.assertIsNone(context.wikidata_id("https://www.wikidata.org/wiki/Property:P1"))
        self.assertIsNone(context.wikidata_id("https://www.wikidata.org/wiki/Q0"))
        self.assertIsNone(context.wikidata_id("https://evil.example/https://www.wikidata.org/wiki/Q42"))


if __name__ == "__main__":
    unittest.main()
