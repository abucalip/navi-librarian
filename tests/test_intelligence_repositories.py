import tempfile
import unittest
from pathlib import Path

from intelligence.store import generations, open_store
from intelligence.store import repositories as repo


class RepositoryTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db = open_store(Path(self.temp_dir.name) / "intelligence.sqlite3")
        self.addCleanup(self.db.close)

    def edge(self, a, b, **kw):
        args = {"evidence_class": "source_explicit", "match_quality": "exact_mbid", "source": "musicbrainz"}
        args.update(kw)
        return repo.add_edge(self.db, a, b, "member_of", **args)


class GenerationTests(RepositoryTestCase):
    def test_generation_starts_at_one_and_bumps(self):
        self.assertEqual(generations.current_generation(self.db), 1)
        self.assertEqual(generations.bump_generation(self.db), 2)
        self.assertEqual(generations.current_generation(self.db), 2)

    def test_generation_defaults_to_one_if_meta_row_missing(self):
        self.db.execute("DELETE FROM meta WHERE key = 'generation'")
        self.assertEqual(generations.current_generation(self.db), 1)
        self.assertEqual(generations.bump_generation(self.db), 2)

    def test_data_version_counts_per_resource(self):
        self.assertEqual(generations.data_version(self.db, "health"), 0)
        self.assertEqual(generations.bump_data_version(self.db, "health"), 1)
        self.assertEqual(generations.bump_data_version(self.db, "health"), 2)
        generations.bump_data_version(self.db, "editions")
        self.assertEqual(generations.data_versions(self.db), {"health": 2, "editions": 1})

    def test_data_version_does_not_touch_generation(self):
        generations.bump_data_version(self.db, "health")
        self.assertEqual(generations.current_generation(self.db), 1)

    def test_bad_resource_names_rejected(self):
        for name in ("", " x", "a:b"):
            with self.assertRaises(ValueError):
                generations.bump_data_version(self.db, name)

    def test_counters_survive_reopen(self):
        generations.bump_generation(self.db)
        generations.bump_data_version(self.db, "health")
        path = Path(self.temp_dir.name) / "intelligence.sqlite3"
        other = open_store(path)
        self.addCleanup(other.close)
        self.assertEqual(generations.current_generation(other), 2)
        self.assertEqual(generations.data_version(other, "health"), 1)


class ObservationTests(RepositoryTestCase):
    def test_add_and_get_round_trips_payload(self):
        oid, created = repo.add_observation(self.db, "musicbrainz", {"b": 1, "a": [1, 2]}, fetched_at=10.0, entity_hint="x")
        self.assertTrue(created)
        row = repo.get_observation(self.db, oid)
        self.assertEqual(row["payload"], {"a": [1, 2], "b": 1})
        self.assertEqual(row["generation"], 1)

    def test_same_content_not_stored_twice_regardless_of_key_order(self):
        first, _ = repo.add_observation(self.db, "lb", {"a": 1, "b": 2}, fetched_at=1.0)
        second, created = repo.add_observation(self.db, "lb", {"b": 2, "a": 1}, fetched_at=2.0)
        self.assertEqual(first, second)
        self.assertFalse(created)

    def test_same_content_from_other_source_is_separate(self):
        a, _ = repo.add_observation(self.db, "lb", {"a": 1}, fetched_at=1.0)
        b, created = repo.add_observation(self.db, "mb", {"a": 1}, fetched_at=1.0)
        self.assertNotEqual(a, b)
        self.assertTrue(created)

    def test_stamped_with_current_generation(self):
        generations.bump_generation(self.db)
        oid, _ = repo.add_observation(self.db, "lb", {"a": 1}, fetched_at=1.0)
        self.assertEqual(repo.get_observation(self.db, oid)["generation"], 2)

    def test_latest_observation_prefers_newest_fetch(self):
        repo.add_observation(self.db, "lb", {"v": 1}, fetched_at=1.0, entity_hint="h")
        repo.add_observation(self.db, "lb", {"v": 2}, fetched_at=5.0, entity_hint="h")
        repo.add_observation(self.db, "lb", {"v": 3}, fetched_at=3.0, entity_hint="h")
        self.assertEqual(repo.latest_observation(self.db, "lb", "h")["payload"], {"v": 2})
        self.assertIsNone(repo.latest_observation(self.db, "lb", "other"))

    def test_expired_observations_are_bounded_and_ordered(self):
        for i, exp in enumerate((30.0, 10.0, None, 20.0, 99.0)):
            repo.add_observation(self.db, "lb", {"i": i}, fetched_at=1.0, expires_at=exp)
        got = repo.expired_observations(self.db, now=30.0, limit=2)
        self.assertEqual([o["expires_at"] for o in got], [10.0, 20.0])
        self.assertEqual(len(repo.expired_observations(self.db, now=30.0)), 3)
        self.assertEqual(repo.expired_observations(self.db, now=30.0, limit=0), [])

    def test_get_missing_returns_none(self):
        self.assertIsNone(repo.get_observation(self.db, 999))


class EntityTests(RepositoryTestCase):
    def test_create_then_find_by_each_identifier(self):
        eid, created = repo.upsert_entity(self.db, "artist", "Portishead", mbid="m1", navidrome_id="n1", owned=True)
        self.assertTrue(created)
        self.assertEqual(repo.find_entity(self.db, "artist", mbid="m1")["id"], eid)
        self.assertEqual(repo.find_entity(self.db, "artist", navidrome_id="n1")["owned"], 1)
        self.assertIsNone(repo.find_entity(self.db, "release", mbid="m1"))

    def test_upsert_is_idempotent_and_fills_missing_ids(self):
        first, _ = repo.upsert_entity(self.db, "artist", "Portishead", navidrome_id="n1")
        second, created = repo.upsert_entity(self.db, "artist", "Portishead", navidrome_id="n1", mbid="m1", sort_name="Portishead")
        self.assertEqual(first, second)
        self.assertFalse(created)
        row = repo.get_entity(self.db, first)
        self.assertEqual((row["mbid"], row["sort_name"]), ("m1", "Portishead"))

    def test_existing_identifier_is_never_overwritten(self):
        eid, _ = repo.upsert_entity(self.db, "artist", "A", navidrome_id="n1", mbid="m1")
        repo.upsert_entity(self.db, "artist", "A", navidrome_id="n1", mbid="other")
        self.assertEqual(repo.get_entity(self.db, eid)["mbid"], "m1")

    def test_owned_changes_only_when_passed(self):
        eid, _ = repo.upsert_entity(self.db, "artist", "A", mbid="m1", owned=True)
        repo.upsert_entity(self.db, "artist", "A", mbid="m1")
        self.assertEqual(repo.get_entity(self.db, eid)["owned"], 1)
        repo.upsert_entity(self.db, "artist", "A", mbid="m1", owned=False)
        self.assertEqual(repo.get_entity(self.db, eid)["owned"], 0)

    def test_same_identifier_allowed_across_types(self):
        a, _ = repo.upsert_entity(self.db, "artist", "X", mbid="m1")
        b, created = repo.upsert_entity(self.db, "release", "X", mbid="m1")
        self.assertNotEqual(a, b)
        self.assertTrue(created)

    def test_entities_without_identifiers_are_always_new(self):
        a, _ = repo.upsert_entity(self.db, "genre", "Trip hop")
        b, created = repo.upsert_entity(self.db, "genre", "Trip hop")
        self.assertNotEqual(a, b)
        self.assertTrue(created)

    def test_created_generation_recorded(self):
        generations.bump_generation(self.db)
        eid, _ = repo.upsert_entity(self.db, "artist", "A", mbid="m1")
        self.assertEqual(repo.get_entity(self.db, eid)["created_generation"], 2)

    def test_invalid_input_rejected(self):
        with self.assertRaises(ValueError):
            repo.upsert_entity(self.db, "spaceship", "A")
        with self.assertRaises(ValueError):
            repo.upsert_entity(self.db, "artist", "A", isrc="x")
        with self.assertRaises(ValueError):
            repo.find_entity(self.db, "artist", isrc="x")

    def test_find_by_name_matches_canonical_and_alias_without_duplicates(self):
        eid, _ = repo.upsert_entity(self.db, "artist", "Beyonce")
        repo.add_alias(self.db, eid, "Beyoncé")
        repo.add_alias(self.db, eid, "Beyonce", kind="search")
        self.assertEqual([e["id"] for e in repo.find_entities_by_name(self.db, "artist", "Beyoncé")], [eid])
        self.assertEqual([e["id"] for e in repo.find_entities_by_name(self.db, "artist", "Beyonce")], [eid])
        self.assertEqual(repo.find_entities_by_name(self.db, "release", "Beyonce"), [])
        self.assertEqual(repo.find_entities_by_name(self.db, "artist", "beyonce"), [])

    def test_aliases_idempotent_and_sorted(self):
        eid, _ = repo.upsert_entity(self.db, "artist", "A", mbid="m1")
        self.assertTrue(repo.add_alias(self.db, eid, "Zed"))
        self.assertFalse(repo.add_alias(self.db, eid, "Zed"))
        repo.add_alias(self.db, eid, "Abe", kind="sort")
        self.assertEqual(repo.aliases(self.db, eid), [("Abe", "sort"), ("Zed", "alias")])


class EdgeTests(RepositoryTestCase):
    def setUp(self):
        super().setUp()
        self.a, _ = repo.upsert_entity(self.db, "person", "A", mbid="a")
        self.b, _ = repo.upsert_entity(self.db, "group", "B", mbid="b")

    def test_add_is_idempotent_and_null_role_counts_once(self):
        first, created = self.edge(self.a, self.b)
        again, created_again = self.edge(self.a, self.b)
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(first, again)
        _, other_role = self.edge(self.a, self.b, role="drums")
        self.assertTrue(other_role)

    def test_same_edge_from_another_source_or_generation_is_separate(self):
        self.edge(self.a, self.b)
        self.assertTrue(self.edge(self.a, self.b, source="wikidata")[1])
        generations.bump_generation(self.db)
        self.assertTrue(self.edge(self.a, self.b)[1])

    def test_queries_filter_by_relation_and_generation(self):
        self.edge(self.a, self.b)
        generations.bump_generation(self.db)
        repo.add_edge(self.db, self.a, self.b, "producer", evidence_class="derived",
                      match_quality="fuzzy_confirmed", source="x")
        self.assertEqual(len(repo.edges_from(self.db, self.a)), 2)
        self.assertEqual(len(repo.edges_from(self.db, self.a, relation="producer")), 1)
        self.assertEqual(len(repo.edges_to(self.db, self.b, generation=1)), 1)
        self.assertEqual(repo.edges_to(self.db, self.a), [])

    def test_invalid_vocabulary_rejected(self):
        with self.assertRaises(ValueError):
            self.edge(self.a, self.b, evidence_class="vibes")
        with self.assertRaises(ValueError):
            self.edge(self.a, self.b, match_quality="close_enough")

    def test_edge_keeps_provenance(self):
        oid, _ = repo.add_observation(self.db, "musicbrainz", {"x": 1}, fetched_at=1.0)
        eid, _ = self.edge(self.a, self.b, observation_id=oid, source_url="https://mb/x", valid_from="1990")
        row = repo.edges_from(self.db, self.a)[0]
        self.assertEqual((row["id"], row["observation_id"], row["source_url"], row["valid_from"]), (eid, oid, "https://mb/x", "1990"))

    def test_rebuild_cleanup_drops_old_derived_edges_but_keeps_confirmed_and_observations(self):
        oid, _ = repo.add_observation(self.db, "musicbrainz", {"x": 1}, fetched_at=1.0)
        self.edge(self.a, self.b)
        self.edge(self.a, self.b, role="kept", evidence_class="user_confirmed")
        new_gen = generations.bump_generation(self.db)
        self.edge(self.a, self.b)
        self.assertEqual(repo.delete_edges_before_generation(self.db, new_gen), 1)
        remaining = repo.edges_from(self.db, self.a)
        self.assertEqual(sorted((e["generation"], e["evidence_class"]) for e in remaining),
                         [(1, "user_confirmed"), (2, "source_explicit")])
        self.assertIsNotNone(repo.get_observation(self.db, oid))

    def test_deleting_entity_removes_its_edges(self):
        self.edge(self.a, self.b)
        self.db.execute("DELETE FROM entities WHERE id = ?", (self.a,))
        self.assertEqual(repo.edges_to(self.db, self.b), [])


if __name__ == "__main__":
    unittest.main()
