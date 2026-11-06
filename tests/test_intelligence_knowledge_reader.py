import ast
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from intelligence import knowledge
from intelligence.graph import Limits
from intelligence.knowledge import KnowledgeReader, slice_status
from intelligence.store import open_store
from intelligence.store import repositories as repo
from intelligence.store.db import open_readonly


def add_edge(db, a, b, relation="producer", source="musicbrainz_dump", evidence="source_explicit", match="exact_mbid", role=None):
    repo.add_edge(db, a, b, relation, role=role, evidence_class=evidence, match_quality=match, source=source,
                  source_url=f"https://musicbrainz.org/artist/{a}")


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.db = open_store(":memory:")
        self.alpha = repo.upsert_entity(self.db, "artist", "Alpha", mbid="a-gid", owned=True)[0]
        self.beta = repo.upsert_entity(self.db, "artist", "Beta", mbid="b-gid")[0]
        self.reader = KnowledgeReader(self.db, clock=lambda: 2000.0)

    def load_slice(self):
        with self.db:
            for key, value in (("dump_timestamp", "2026-11-04"), ("schema_sequence", "31"), ("loaded_at", "1000")):
                self.db.execute("INSERT INTO meta (key, value) VALUES (?, ?)", (f"musicbrainz_slice.{key}", value))

    def test_entity_lookup_forms(self):
        self.assertEqual(self.reader.entity("artist", mbid="A-GID")["canonical_name"], "Alpha")
        self.assertEqual(self.reader.entity(id=self.beta)["canonical_name"], "Beta")
        self.assertIsNone(self.reader.entity("artist", mbid="nope"))
        with self.assertRaises(ValueError):
            self.reader.entity("artist")

    def test_profile_missing_entity_is_none(self):
        self.assertIsNone(self.reader.profile("artist", mbid="nope"))

    def test_profile_pending_without_a_slice(self):
        profile = self.reader.profile("artist", mbid="a-gid")
        self.assertEqual(profile["sources"]["musicbrainz_dump"]["coverage"], "pending")
        self.assertEqual(profile["relationships"], [])

    def test_profile_with_slice_but_no_relationships(self):
        self.load_slice()
        profile = self.reader.profile("artist", mbid="a-gid")
        self.assertEqual(profile["sources"]["musicbrainz_dump"]["coverage"], "no_relationships_in_slice")

    def test_profile_carries_provenance_and_credit_flag(self):
        self.load_slice()
        add_edge(self.db, self.beta, self.alpha, "producer", role="mix")
        gamma = repo.upsert_entity(self.db, "artist", "Gamma", mbid="g-gid")[0]
        add_edge(self.db, gamma, self.alpha, "collaboration", source="derived", evidence="inferred")
        profile = self.reader.profile("artist", mbid="a-gid")
        self.assertEqual(profile["sources"]["musicbrainz_dump"]["coverage"], "loaded")
        by_name = {h["entity"]["canonical_name"]: h for h in profile["relationships"]}
        self.assertTrue(by_name["Beta"]["credit"])
        self.assertEqual(by_name["Beta"]["evidence"][0]["source"], "musicbrainz_dump")
        self.assertEqual(by_name["Beta"]["evidence"][0]["role"], "mix")
        self.assertFalse(by_name["Gamma"]["credit"])  # inferred is never a credit

    def test_connections_are_bounded_and_credits_only(self):
        add_edge(self.db, self.beta, self.alpha)
        gamma = repo.upsert_entity(self.db, "artist", "Gamma", mbid="g-gid")[0]
        add_edge(self.db, gamma, self.alpha, evidence="inferred", source="derived")
        page = self.reader.connections(self.alpha, credits_only=True, limits=Limits(max_depth=1))
        self.assertEqual([h["entity"]["canonical_name"] for h in page["hops"]], ["Beta"])

    def test_slice_status(self):
        self.assertFalse(slice_status(self.db)["loaded"])
        self.load_slice()
        status = self.reader.slice_status()
        self.assertEqual((status["loaded"], status["dump_timestamp"], status["schema_sequence"], status["age_seconds"]),
                         (True, "2026-11-04", 31, 1000.0))


class ReadOnlyTests(unittest.TestCase):
    def test_readonly_connection_reads_both_files_and_refuses_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "intelligence.sqlite3"
            db = open_store(path)
            repo.upsert_entity(db, "artist", "Alpha", mbid="a-gid")[0]
            db.close()
            ro = open_readonly(path)
            self.assertEqual(KnowledgeReader(ro).entity("artist", mbid="a-gid")["canonical_name"], "Alpha")
            self.assertEqual(ro.execute("SELECT COUNT(*) FROM state.card_decisions").fetchone()[0], 0)
            with self.assertRaises(sqlite3.OperationalError):
                ro.execute("INSERT INTO meta (key, value) VALUES ('x', 'y')")
            with self.assertRaises(sqlite3.OperationalError):
                ro.execute("INSERT INTO state.card_decisions VALUES ('k', 'a', 'dismissed', '{}', 0)")
            ro.close()


class DossierTests(unittest.TestCase):
    def setUp(self):
        self.db = open_store(":memory:")
        self.release = repo.upsert_entity(self.db, "release", "Kind of Blue", mbid="r-gid", owned=True)[0]
        self.group = repo.upsert_entity(self.db, "release_group", "Kind of Blue", mbid="g-gid")[0]
        self.rec = repo.upsert_entity(self.db, "recording", "So What", mbid="rec-gid")[0]
        self.miles = repo.upsert_entity(self.db, "artist", "Miles Davis", mbid="m-gid")[0]
        self.label = repo.upsert_entity(self.db, "label", "Columbia", mbid="l-gid")[0]
        common = dict(evidence_class="source_explicit", match_quality="exact_mbid", source="musicbrainz_dump")
        repo.add_edge(self.db, self.release, self.group, "member_of", **{**common, "source": "musicbrainz"})
        repo.add_edge(self.db, self.rec, self.release, "appears_on", role="1/1", **{**common, "source": "musicbrainz"})
        repo.add_edge(self.db, self.miles, self.release, "producer", role="executive", **common)
        repo.add_edge(self.db, self.miles, self.rec, "instrument", role="trumpet", **common)
        repo.add_edge(self.db, self.label, self.release, "publisher", **common)
        self.reader = KnowledgeReader(self.db, clock=lambda: 2000.0)

    def load_slice(self):
        with self.db:
            for key, value in (("dump_timestamp", "2026-11-04"), ("schema_sequence", "31"), ("loaded_at", "1000")):
                self.db.execute("INSERT INTO meta (key, value) VALUES (?, ?)", (f"musicbrainz_slice.{key}", value))

    def test_unknown_album_is_none(self):
        self.assertIsNone(self.reader.album_dossier(mbid="nope"))

    def test_dossier_groups_credits_labels_and_family(self):
        self.load_slice()
        d = self.reader.album_dossier(mbid="r-gid")
        self.assertEqual(d["release_group"]["canonical_name"], "Kind of Blue")
        self.assertEqual(d["release_family"]["count"], 1)
        self.assertEqual([t["title"] for t in d["tracks"]], ["So What"])
        self.assertEqual([p["entity"]["canonical_name"] for p in d["people"]], ["Miles Davis"])
        scopes = {(c["scope"], c["relation"], c["role"], c["track"]) for c in d["people"][0]["credits"]}
        self.assertEqual(scopes, {("album", "producer", "executive", None), ("recording", "instrument", "trumpet", "So What")})
        self.assertEqual(d["people"][0]["credits"][0]["source"], "musicbrainz_dump")
        self.assertEqual([l["entity"]["canonical_name"] for l in d["labels"]], ["Columbia"])
        self.assertEqual(d["sources"]["musicbrainz_dump"]["coverage"], "loaded")
        self.assertEqual(d["not_loaded"], ["recording_places_and_dates", "cover_art_variants", "catalogue_numbers", "formats"])

    def test_dossier_catalogue_numbers_and_formats(self):
        self.load_slice()
        other = repo.upsert_entity(self.db, "label", "Other", mbid="o-gid")[0]
        for label, number in ((self.label, "CL 1355"), (other, None), (None, "ORPHAN-1")):
            self.db.execute("INSERT INTO release_labels (release_id, label_id, catalogue_number) VALUES (?, ?, ?)",
                            (self.release, label, number))
        self.db.execute("INSERT INTO release_facts (entity_id, formats) VALUES (?, '2×Vinyl')", (self.release,))
        d = self.reader.album_dossier(mbid="r-gid")
        edition = d["release_family"]["editions"][0]
        self.assertEqual(edition["formats"], "2×Vinyl")
        self.assertEqual([(c["label"] and c["label"]["name"], c["catalogue_number"]) for c in edition["catalogue"]],
                         [(None, "ORPHAN-1"), ("Columbia", "CL 1355"), ("Other", None)])
        self.assertEqual(edition["catalogue"][1]["label"], {"mbid": "l-gid", "name": "Columbia"})
        self.assertEqual(d["not_loaded"], ["recording_places_and_dates", "cover_art_variants"])

    def test_edition_facts_fall_back_from_dump_to_library_file(self):
        self.assertEqual(self.reader.album_dossier(mbid="r-gid")["release_family"]["editions"][0]["facts_source"], None)
        self.db.execute("UPDATE entities SET navidrome_id = 'nd-1' WHERE id = ?", (self.release,))
        repo.add_observation(self.db, "navidrome", {"year": 1959, "song_count": 5}, fetched_at=1.0, entity_hint="album:nd-1")
        library = self.reader.album_dossier(mbid="r-gid")["release_family"]["editions"][0]
        self.assertEqual((library["date"], library["country"], library["status"], library["track_count"], library["facts_source"]),
                         ("1959", None, None, 1, "library_file"))  # track count prefers the tracklist the store holds
        self.db.execute("INSERT INTO release_facts (entity_id, date, country, status) VALUES (?, '1959-08-17', 'US', 'official')",
                        (self.release,))
        dump = self.reader.album_dossier(mbid="r-gid")["release_family"]["editions"][0]
        self.assertEqual((dump["date"], dump["country"], dump["status"], dump["facts_source"]),
                         ("1959-08-17", "US", "official", "musicbrainz_dump"))

    def test_stored_release_document_wins_over_the_dump(self):
        self.db.execute("INSERT INTO release_facts (entity_id, date, country, status) VALUES (?, '1960', 'GB', 'bootleg')",
                        (self.release,))
        mbid = "11111111-1111-4111-8111-111111111111"
        self.db.execute("UPDATE entities SET mbid = ? WHERE id = ?", (mbid, self.release))
        repo.add_observation(self.db, "musicbrainz", {
            "id": mbid, "title": "Kind of Blue", "date": "1959-08-17", "country": "US", "status": "Official",
            "release-group": {"id": "22222222-2222-4222-8222-222222222222", "title": "Kind of Blue"}},
            fetched_at=1.0, entity_hint=f"release:{mbid}")
        edition = self.reader.album_dossier(mbid=mbid)["release_family"]["editions"][0]
        self.assertEqual((edition["date"], edition["country"], edition["facts_source"]),
                         ("1959-08-17", "US", "musicbrainz_release"))

    def test_inferred_edge_is_never_a_credit(self):
        other = repo.upsert_entity(self.db, "artist", "Guess", mbid="x-gid")[0]
        repo.add_edge(self.db, other, self.release, "producer", evidence_class="inferred",
                      match_quality="fuzzy_confirmed", source="derived")
        names = [p["entity"]["canonical_name"] for p in self.reader.album_dossier(mbid="r-gid")["people"]]
        self.assertEqual(names, ["Miles Davis"])

    def test_pending_without_slice_and_group_dossier(self):
        self.assertEqual(self.reader.album_dossier(mbid="r-gid")["sources"]["musicbrainz_dump"]["coverage"], "pending")
        d = self.reader.album_dossier(type="release_group", mbid="g-gid")
        self.assertEqual(d["album"]["mbid"], "g-gid")
        self.assertEqual(d["tracks"], [])
        self.assertEqual(d["release_family"]["count"], 1)

    def test_wrong_type_is_refused(self):
        with self.assertRaises(ValueError):
            self.reader.album_dossier(type="artist", mbid="m-gid")


class PageTests(unittest.TestCase):
    def setUp(self):
        self.db = open_store(":memory:")
        c = dict(evidence_class="source_explicit", match_quality="exact_mbid", source="musicbrainz_dump")
        e = lambda t, n, g, **k: repo.upsert_entity(self.db, t, n, mbid=g, **k)[0]
        self.miles = e("artist", "Miles Davis", "m-gid")
        self.trane = e("artist", "John Coltrane", "t-gid")
        self.kob = e("release", "Kind of Blue", "kob-r", owned=True)
        self.kob_g = e("release_group", "Kind of Blue", "kob-g")
        self.sketches = e("release_group", "Sketches of Spain", "ss-g")
        self.rec = e("recording", "So What", "rec-gid")
        self.col = e("label", "Columbia", "col-gid")
        self.cbs = e("label", "CBS", "cbs-gid")
        repo.add_edge(self.db, self.kob, self.kob_g, "member_of", **{**c, "source": "musicbrainz"})
        repo.add_edge(self.db, self.rec, self.kob, "appears_on", role="1/1", **{**c, "source": "musicbrainz"})
        repo.add_edge(self.db, self.miles, self.rec, "instrument", role="trumpet", **c)
        repo.add_edge(self.db, self.miles, self.kob, "producer", **c)
        repo.add_edge(self.db, self.miles, self.sketches, "performer", **c)
        repo.add_edge(self.db, self.miles, self.trane, "collaboration", source="derived", evidence_class="inferred", match_quality="exact_mbid")
        repo.add_edge(self.db, self.col, self.kob, "publisher", **c)
        repo.add_edge(self.db, self.col, self.sketches, "publisher", **c)
        repo.add_edge(self.db, self.cbs, self.col, "label ownership", **c)
        self.reader = KnowledgeReader(self.db, clock=lambda: 2000.0)

    def load_slice(self):
        with self.db:
            for key, value in (("dump_timestamp", "2026-11-04"), ("schema_sequence", "31"), ("loaded_at", "1000")):
                self.db.execute("INSERT INTO meta (key, value) VALUES (?, ?)", (f"musicbrainz_slice.{key}", value))

    def test_person_page_splits_library_and_explains(self):
        self.load_slice()
        p = self.reader.person_page(mbid="m-gid")
        self.assertEqual([r["album"]["canonical_name"] for r in p["in_library"]], ["Kind of Blue"])
        self.assertEqual(p["in_library"][0]["album"]["type"], "release_group")  # editions fold into the group
        self.assertEqual(p["in_library"][0]["why"], "credited as producer, trumpet on So What")
        self.assertEqual([r["album"]["canonical_name"] for r in p["not_in_library"]], ["Sketches of Spain"])
        self.assertEqual(p["related_people"], [])  # an inferred edge is never shown
        self.assertEqual(p["sources"]["musicbrainz_dump"]["coverage"], "loaded")

    def test_person_page_life_span(self):
        self.assertIsNone(self.reader.person_page(mbid="m-gid")["life_span"])  # nothing stated is null, not "alive"
        self.db.execute("INSERT INTO artist_life_span (entity_id, begin_date, end_date, ended) VALUES (?, '1926-05-26', '1991-09-28', 1)",
                        (self.miles,))
        self.assertEqual(self.reader.person_page(mbid="m-gid")["life_span"],
                         {"begin": "1926-05-26", "end": "1991-09-28", "ended": True})

    def test_person_page_pending_unknown_and_wrong_type(self):
        self.assertEqual(self.reader.person_page(mbid="m-gid")["sources"]["musicbrainz_dump"]["coverage"], "pending")
        self.assertIsNone(self.reader.person_page(mbid="nope"))
        with self.assertRaises(ValueError):
            self.reader.person_page(type="label", mbid="col-gid")

    def test_person_page_no_relationships(self):
        self.load_slice()
        p = self.reader.person_page(mbid="t-gid")
        self.assertEqual(p["sources"]["musicbrainz_dump"]["coverage"], "no_relationships_in_slice")

    def test_label_page(self):
        self.load_slice()
        page = self.reader.label_page(mbid="col-gid")
        self.assertEqual([r["album"]["canonical_name"] for r in page["owned_catalogue"]], ["Kind of Blue"])
        self.assertEqual([r["album"]["canonical_name"] for r in page["not_in_library"]], ["Sketches of Spain"])
        self.assertEqual([r["entity"]["canonical_name"] for r in page["related_labels"]], ["CBS"])
        self.assertEqual(page["related_labels"][0]["relations"][0]["relation"], "label ownership")
        self.assertIn("notable_releases", page["not_loaded"])
        self.assertIsNone(self.reader.label_page(mbid="nope"))
        with self.assertRaises(ValueError):
            self.reader.label_page(id=self.miles)

    def test_label_page_parents_sub_labels_and_catalogue_numbers(self):
        self.load_slice()
        for number in ("CL 1355", "CS 8163", None):
            self.db.execute("INSERT INTO release_labels (release_id, label_id, catalogue_number) VALUES (?, ?, ?)",
                            (self.kob, self.col, number))
        self.db.execute("INSERT INTO release_labels (release_id, label_id, catalogue_number) VALUES (?, ?, 'X-9')",
                        (self.kob, self.cbs))  # another label's number on the same release is not this label's
        page = self.reader.label_page(mbid="col-gid")
        self.assertEqual([r["entity"]["canonical_name"] for r in page["parents"]], ["CBS"])
        self.assertEqual(page["sub_labels"], [])
        self.assertEqual(page["owned_catalogue"][0]["catalogue_numbers"], ["CL 1355", "CS 8163"])
        self.assertEqual(page["not_in_library"][0]["catalogue_numbers"], [])
        self.assertEqual(page["not_loaded"], ["notable_releases"])
        parent = self.reader.label_page(mbid="cbs-gid")
        self.assertEqual([r["entity"]["canonical_name"] for r in parent["sub_labels"]], ["Columbia"])
        self.assertEqual(parent["parents"], [])

    def test_label_page_catalogue_numbers_not_loaded_without_rows(self):
        self.assertEqual(self.reader.label_page(mbid="col-gid")["not_loaded"], ["notable_releases", "catalogue_numbers"])

    def test_bounded_by_limit(self):
        self.assertTrue(self.reader.person_page(mbid="m-gid", limit=1)["truncated"])


class WorkTests(unittest.TestCase):
    def setUp(self):
        self.db = open_store(":memory:")
        c = dict(evidence_class="source_explicit", match_quality="exact_mbid", source="musicbrainz_dump")
        e = lambda t, n, g, **k: repo.upsert_entity(self.db, t, n, mbid=g, **k)[0]
        self.work = e("work", "My Favorite Things", "w-gid")
        self.arr = e("work", "My Favorite Things (arr.)", "w2-gid")
        self.rodgers = e("artist", "Richard Rodgers", "r-gid")
        self.trane = e("artist", "John Coltrane", "t-gid")
        self.live = e("recording", "My Favorite Things (live)", "r1-gid")
        self.studio = e("recording", "My Favorite Things", "r2-gid")
        self.cover = e("recording", "My Favorite Things (cover)", "r3-gid", owned=True)
        self.rel = e("release", "My Favorite Things", "rel-gid", owned=True)
        self.rel_g = e("release_group", "My Favorite Things", "rg-gid")
        self.other = e("release_group", "Live in Japan", "lj-gid")
        mb = {**c, "source": "musicbrainz"}
        repo.add_edge(self.db, self.rel, self.rel_g, "member_of", **mb)
        repo.add_edge(self.db, self.studio, self.rel, "appears_on", **mb)
        repo.add_edge(self.db, self.live, self.other, "appears_on", **mb)
        repo.add_edge(self.db, self.live, self.work, "performance", role="live", **c)
        repo.add_edge(self.db, self.studio, self.work, "performance", **c)
        repo.add_edge(self.db, self.cover, self.work, "performance", role="cover, live", **c)
        repo.add_edge(self.db, self.rodgers, self.work, "composer", **c)
        repo.add_edge(self.db, self.arr, self.work, "arrangement", **c)
        repo.add_edge(self.db, self.trane, self.studio, "instrument", role="soprano saxophone", **c)
        repo.add_edge(self.db, self.trane, self.work, "collaboration", source="derived", evidence_class="inferred", match_quality="exact_mbid")
        self.reader = KnowledgeReader(self.db, clock=lambda: 2000.0)

    def load_slice(self):
        with self.db:
            for key, value in (("dump_timestamp", "2026-11-04"), ("schema_sequence", "31"), ("loaded_at", "1000")):
                self.db.execute("INSERT INTO meta (key, value) VALUES (?, ?)", (f"musicbrainz_slice.{key}", value))

    def test_work_page_lists_versions_with_ownership_and_attributes(self):
        self.load_slice()
        page = self.reader.work_page(mbid="w-gid")
        self.assertEqual(page["summary"], {"recordings": 3, "in_library": 2, "covers": 1})
        by_title = {v["recording"]["canonical_name"]: v for v in page["versions"]}
        studio = by_title["My Favorite Things"]
        self.assertTrue(studio["owned"])  # owned through its release
        self.assertEqual(studio["albums"][0]["album"]["type"], "release_group")
        self.assertEqual([p["entity"]["canonical_name"] for p in studio["performers"]], ["John Coltrane"])
        self.assertEqual(by_title["My Favorite Things (live)"]["attributes"], ["live"])
        self.assertFalse(by_title["My Favorite Things (live)"]["owned"])
        self.assertEqual(by_title["My Favorite Things (cover)"]["attributes"], ["cover", "live"])
        self.assertEqual(page["sources"]["musicbrainz_dump"]["coverage"], "loaded")

    def test_work_page_writers_related_and_no_inferred_edge(self):
        self.load_slice()
        page = self.reader.work_page(mbid="w-gid")
        self.assertEqual([w["entity"]["canonical_name"] for w in page["written_by"]], ["Richard Rodgers"])
        self.assertEqual(page["written_by"][0]["relations"][0]["relation"], "composer")  # the inferred Coltrane edge is absent
        self.assertEqual(page["related_works"][0]["relations"][0]["relation"], "arrangement")
        self.assertIn("recording_artist_credit", page["not_loaded"])

    def test_work_page_pending_unknown_and_wrong_type(self):
        self.assertEqual(self.reader.work_page(mbid="w-gid")["sources"]["musicbrainz_dump"]["coverage"], "pending")
        self.assertIsNone(self.reader.work_page(mbid="nope"))
        with self.assertRaises(ValueError):
            self.reader.work_page(id=self.live)

    def test_work_page_no_relationships_and_bounded(self):
        self.load_slice()
        lonely = repo.upsert_entity(self.db, "work", "Lonely", mbid="l-gid")[0]
        self.assertEqual(self.reader.work_page(id=lonely)["sources"]["musicbrainz_dump"]["coverage"], "no_relationships_in_slice")
        self.assertTrue(self.reader.work_page(mbid="w-gid", limit=1)["truncated"])

    def test_works_of_recording_counts_other_recordings(self):
        self.load_slice()
        r = self.reader.works_of_recording(mbid="r2-gid")
        self.assertEqual([w["work"]["canonical_name"] for w in r["works"]], ["My Favorite Things"])
        self.assertEqual(r["works"][0]["other_recordings"], 2)
        self.assertEqual(self.reader.works_of_recording(mbid="r3-gid")["works"][0]["other_recordings"], 2)
        self.assertIsNone(self.reader.works_of_recording(mbid="nope"))
        with self.assertRaises(ValueError):
            self.reader.works_of_recording(id=self.work)


class ContextPageTests(unittest.TestCase):
    """Place and event pages (Phase 5): stated area chain, recordings, people, events; nothing inferred."""

    def setUp(self):
        self.db = open_store(":memory:")
        c = dict(evidence_class="source_explicit", match_quality="exact_mbid", source="musicbrainz_dump")
        e = lambda t, n, g, **k: repo.upsert_entity(self.db, t, n, mbid=g, **k)[0]
        self.fr = e("area", "France", "fr-gid")
        self.idf = e("area", "Ile-de-France", "idf-gid")
        self.paris = e("area", "Paris", "paris-gid")
        self.place = e("place", "Studio Davout", "pl-gid")
        self.event = e("event", "Jazz Night", "ev-gid")
        self.miles = e("artist", "Miles Davis", "m-gid")
        self.rec = e("recording", "So What", "rec-gid")
        self.rel = e("release", "Kind of Blue", "rel-gid", owned=True)
        self.grp = e("release_group", "Kind of Blue", "grp-gid")
        repo.add_edge(self.db, self.paris, self.idf, "part of", **c)
        repo.add_edge(self.db, self.idf, self.fr, "part of", **c)
        repo.add_edge(self.db, self.place, self.paris, "area", **c)
        repo.add_edge(self.db, self.place, self.rec, "recording location", **c)
        repo.add_edge(self.db, self.miles, self.place, "owner", valid_from="1969", **c)
        repo.add_edge(self.db, self.event, self.place, "held at", **c)
        repo.add_edge(self.db, self.miles, self.event, "main performer", **c)
        repo.add_edge(self.db, self.paris, self.event, "recorded in", **c)
        repo.add_edge(self.db, self.event, self.rec, "recorded in", **c)
        repo.add_edge(self.db, self.rec, self.rel, "appears_on", **{**c, "source": "musicbrainz"})
        repo.add_edge(self.db, self.rel, self.grp, "member_of", **{**c, "source": "musicbrainz"})
        repo.add_edge(self.db, self.miles, self.place, "collaboration", source="derived",
                      evidence_class="inferred", match_quality="exact_mbid")
        with self.db:
            self.db.execute("INSERT INTO area_facts (entity_id, kind, iso_code) VALUES (?, 'country', 'FR')", (self.fr,))
            self.db.execute("INSERT INTO area_facts (entity_id, kind, iso_code) VALUES (?, 'city', NULL)", (self.paris,))
            self.db.execute("INSERT INTO place_facts (entity_id, kind, latitude, longitude, begin_date, end_date) "
                            "VALUES (?, 'studio', 48.85, 2.41, '1970', NULL)", (self.place,))
            self.db.execute("INSERT INTO event_facts (entity_id, kind, begin_date, end_date, cancelled) "
                            "VALUES (?, 'festival', '1971-06', NULL, 1)", (self.event,))
        self.reader = KnowledgeReader(self.db, clock=lambda: 2000.0)

    def load_slice(self):
        with self.db:
            for key, value in (("dump_timestamp", "2026-11-04"), ("schema_sequence", "31"), ("loaded_at", "1000")):
                self.db.execute("INSERT INTO meta (key, value) VALUES (?, ?)", (f"musicbrainz_slice.{key}", value))

    def test_place_page_facts_area_chain_and_recordings(self):
        self.load_slice()
        page = self.reader.place_page(mbid="pl-gid")
        self.assertEqual(page["facts"], {"kind": "studio", "latitude": 48.85, "longitude": 2.41, "begin": "1970", "end": None})
        self.assertEqual([a["entity"]["canonical_name"] for a in page["area"]], ["Paris"])
        chain = page["area"][0]["contained_in"]
        self.assertEqual([(a["canonical_name"], a["kind"], a["iso_code"]) for a in chain],
                         [("Ile-de-France", None, None), ("France", "country", "FR")])
        rec = page["recordings"][0]
        self.assertTrue(rec["owned"])
        self.assertEqual(rec["albums"][0]["album"]["type"], "release_group")
        self.assertEqual([p["entity"]["canonical_name"] for p in page["people"]], ["Miles Davis"])
        self.assertEqual([r["relation"] for r in page["people"][0]["relations"]], ["owner"])  # inferred edge dropped
        self.assertEqual(page["events"][0]["facts"]["kind"], "festival")
        self.assertEqual(page["sources"]["musicbrainz_dump"]["coverage"], "loaded")

    def test_only_the_stated_area_is_the_place_area(self):
        # An area that merely links to the place's event is not the place's area.
        page = self.reader.place_page(mbid="pl-gid")
        self.assertEqual(len(page["area"]), 1)

    def test_event_page(self):
        self.load_slice()
        page = self.reader.event_page(mbid="ev-gid")
        self.assertEqual(page["facts"], {"kind": "festival", "begin": "1971-06", "end": None, "cancelled": True})
        self.assertEqual([p["entity"]["canonical_name"] for p in page["places"]], ["Studio Davout"])
        self.assertEqual(page["places"][0]["facts"]["kind"], "studio")
        self.assertEqual([a["entity"]["canonical_name"] for a in page["area"]], ["Paris"])
        self.assertEqual(page["area"][0]["contained_in"][-1]["iso_code"], "FR")
        self.assertEqual([p["entity"]["canonical_name"] for p in page["people"]], ["Miles Davis"])
        self.assertEqual([r["recording"]["canonical_name"] for r in page["recordings"]], ["So What"])

    def test_unknown_wrong_type_and_pending(self):
        self.assertIsNone(self.reader.place_page(mbid="nope"))
        self.assertIsNone(self.reader.event_page(mbid="nope"))
        self.assertIsNone(self.reader.place_page(mbid="ev-gid"))  # an event is not a place
        from intelligence.knowledge.context_pages import event_page, place_page
        with self.assertRaises(ValueError):
            place_page(self.reader, repo.get_entity(self.db, self.event))
        with self.assertRaises(ValueError):
            event_page(self.reader, repo.get_entity(self.db, self.place))
        self.assertEqual(self.reader.place_page(mbid="pl-gid")["sources"]["musicbrainz_dump"]["coverage"], "pending")

    def test_no_relationships_and_bounded(self):
        self.load_slice()
        lone = repo.upsert_entity(self.db, "place", "Lone", mbid="lone-gid")[0]
        page = self.reader.place_page(mbid="lone-gid")
        self.assertEqual(page["sources"]["musicbrainz_dump"]["coverage"], "no_relationships_in_slice")
        self.assertIsNone(page["facts"])
        self.assertEqual(page["area"], [])
        self.assertTrue(self.reader.place_page(mbid="pl-gid", limit=1)["truncated"])

    def test_containment_loop_ends(self):
        c = dict(evidence_class="source_explicit", match_quality="exact_mbid", source="musicbrainz_dump")
        repo.add_edge(self.db, self.fr, self.paris, "part of", **c)
        page = self.reader.place_page(mbid="pl-gid")
        self.assertEqual([a["canonical_name"] for a in page["area"][0]["contained_in"]], ["Ile-de-France", "France"])

    def test_public_shape(self):
        for page in (self.reader.place_page(mbid="pl-gid"), self.reader.event_page(mbid="ev-gid")):
            text = json.dumps(page)
            self.assertNotIn('"id"', text)
            self.assertNotIn('"owned": 1', text)


class BoundaryTests(unittest.TestCase):
    FORBIDDEN = ("integrations", "requests", "httpx", "urllib", "http", "socket", "discovery", "app",
                 "navidrome_client", "navidrome_server", "acquisition", "recommendation")

    def test_knowledge_package_imports_no_provider_or_web_module(self):
        for path in Path(knowledge.__file__).parent.glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                         else [node.module or ""] if isinstance(node, ast.ImportFrom) and not node.level else [])
                for name in names:
                    self.assertNotIn(name.split(".")[0], self.FORBIDDEN, f"{path.name} imports {name}")



class PublicShapeTests(unittest.TestCase):
    """Owner decision 2026-11-06: mbid only, every owned flag a boolean, a group is owned when any edition is."""

    def setUp(self):
        self.db = open_store(":memory:")
        c = dict(evidence_class="source_explicit", match_quality="exact_mbid", source="musicbrainz_dump")
        e = lambda t, n, g, **k: repo.upsert_entity(self.db, t, n, mbid=g, **k)[0]
        self.miles = e("artist", "Miles Davis", "m-gid")
        self.rel = e("release", "Kind of Blue", "r-gid", owned=True)
        self.group = e("release_group", "Kind of Blue", "g-gid")
        self.rec = e("recording", "So What", "rec-gid")
        self.work = e("work", "So What", "w-gid")
        repo.add_edge(self.db, self.rel, self.group, "member_of", **{**c, "source": "musicbrainz"})
        repo.add_edge(self.db, self.rec, self.rel, "appears_on", role="1/1", **{**c, "source": "musicbrainz"})
        repo.add_edge(self.db, self.miles, self.rec, "instrument", role="trumpet", **c)
        repo.add_edge(self.db, self.rec, self.work, "performance", **c)
        self.reader = KnowledgeReader(self.db, clock=lambda: 2000.0)

    def pages(self):
        r = self.reader
        return [r.album_dossier(mbid="r-gid"), r.album_dossier(mbid="g-gid", type="release_group"),
                r.person_page(mbid="m-gid"), r.work_page(mbid="w-gid"), r.works_of_recording(mbid="rec-gid")]

    def walk(self, value, found):
        if isinstance(value, dict):
            for k, v in value.items():
                found.append((k, v))
                self.walk(v, found)
        elif isinstance(value, list):
            for v in value:
                self.walk(v, found)
        return found

    def test_no_internal_identifier_in_any_page(self):
        for page in self.pages():
            keys = {k for k, _ in self.walk(page, [])}
            self.assertFalse(keys & {"id", "created_generation", "navidrome_id", "discogs_id", "wikidata_id"}, keys)

    def test_every_owned_flag_is_a_boolean(self):
        for page in self.pages():
            flags = [v for k, v in self.walk(page, []) if k == "owned"]
            self.assertTrue(flags)
            self.assertTrue(all(isinstance(v, bool) for v in flags), flags)

    def test_group_is_owned_when_any_edition_is(self):
        self.assertIs(self.reader.album_dossier(mbid="r-gid")["release_group"]["owned"], True)
        self.assertIs(self.reader.album_dossier(mbid="g-gid", type="release_group")["album"]["owned"], True)
        person = self.reader.person_page(mbid="m-gid")
        self.assertEqual([r["album"]["owned"] for r in person["in_library"]], [True])
        work = self.reader.work_page(mbid="w-gid")
        self.assertIs(work["versions"][0]["albums"][0]["album"]["owned"], True)

if __name__ == "__main__":
    unittest.main()
