import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from intelligence.graph.path_coverage import Criteria, KINDS, measure  # noqa: E402
from intelligence.store import open_store  # noqa: E402
from intelligence.store import repositories as repo  # noqa: E402

DUMP = "musicbrainz_dump"


def _mbid(n: int) -> str:
    return f"e0000000-0000-0000-0000-{n:012d}"


class PathCoverageTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = open_store(Path(self._tmp.name) / "c.sqlite3")
        self.n = 0

    def tearDown(self):
        self.db.close()
        self._tmp.cleanup()

    def ent(self, kind, name, **kw):
        self.n += 1
        return repo.upsert_entity(self.db, kind, name, mbid=_mbid(self.n), **kw)[0]

    def edge(self, a, b, rel, *, ec="source_explicit", mq="exact_mbid", src=DUMP):
        repo.add_edge(self.db, a, b, rel, source=src, evidence_class=ec, match_quality=mq)

    def library(self, artist_name="Anchor"):
        """An owned artist with one owned release carrying one owned recording."""
        artist = self.ent("artist", artist_name, owned=True)
        release = self.ent("release", artist_name + " LP", owned=True)
        rec = self.ent("recording", artist_name + " Song", owned=True)
        self.edge(release, artist, "credited_to", ec="library_tag", src="navidrome")
        self.edge(rec, release, "appears_on", ec="library_tag", src="navidrome")
        return artist, release, rec

    def run_kind(self, kind, **crit):
        self.db.commit()
        return measure(self.db, Criteria(**crit), (kind,))["kinds"][kind]

    def test_follow_the_musician_counts_other_recordings_of_a_shared_musician(self):
        anchor, _, rec = self.library()
        player = self.ent("artist", "Player")
        self.edge(player, rec, "instrument")
        others = [self.ent("recording", f"Other {i}") for i in range(3)]
        for o in others:
            self.edge(player, o, "instrument")
        result = self.run_kind("follow_the_musician")
        self.assertEqual((result["anchors"], result["anchors_with_a_stop"], result["anchors_usable"]), (1, 1, 1))
        self.assertEqual(result["stops_max"], 3)
        self.assertEqual(result["verdict"], "keep")

    def test_inferred_and_unmatched_edges_give_no_stops(self):
        anchor, _, rec = self.library()
        guessed, unmatched = self.ent("artist", "Guessed"), self.ent("artist", "Unmatched")
        self.edge(guessed, rec, "instrument", ec="inferred")
        self.edge(unmatched, rec, "instrument", mq="unresolved")
        for who in (guessed, unmatched):
            self.edge(who, self.ent("recording", "Elsewhere"), "instrument")
        result = self.run_kind("follow_the_musician")
        self.assertEqual(result["anchors_with_a_stop"], 0)
        self.assertEqual(result["verdict"], "drop_mostly_empty")

    def test_the_anchors_own_recordings_are_not_stops(self):
        anchor, release, rec = self.library()
        player = self.ent("artist", "Player")
        second = self.ent("recording", "Second owned")
        self.edge(second, release, "appears_on", ec="library_tag", src="navidrome")
        self.edge(player, rec, "instrument")
        self.edge(player, second, "instrument")
        self.assertEqual(self.run_kind("follow_the_musician")["anchors_with_a_stop"], 0)

    def test_sideman_to_leader_finds_the_leader_of_the_release(self):
        sideman, _, _ = self.library("Sideman")
        leader = self.ent("artist", "Leader")
        release = self.ent("release", "Leader LP")
        rec = self.ent("recording", "Leader Song")
        self.edge(release, leader, "credited_to", ec="library_tag", src="navidrome")
        self.edge(rec, release, "appears_on", ec="library_tag", src="navidrome")
        self.edge(sideman, rec, "instrument")
        result = self.run_kind("sideman_to_leader", min_stops=1)
        self.assertEqual(result["anchors_with_a_stop"], 1)

    def test_label_path_uses_other_releases_of_the_label_and_of_related_labels(self):
        anchor, release, _ = self.library()
        label, parent = self.ent("label", "Label"), self.ent("label", "Parent")
        self.edge(parent, label, "label ownership")
        own_rl = [(release, label)]
        other = [self.ent("release", f"Other {i}") for i in range(2)]
        sibling = self.ent("release", "On the parent")
        for rel, lab in own_rl + [(other[0], label), (other[1], label), (sibling, parent)]:
            self.db.execute("INSERT INTO release_labels (release_id, label_id) VALUES (?, ?)", (rel, lab))
        result = self.run_kind("label_path")
        self.assertEqual(result["stops_max"], 3)
        self.assertEqual(result["verdict"], "keep")

    def test_composition_path_follows_the_work_and_related_works(self):
        anchor, _, rec = self.library()
        work, other_work = self.ent("work", "Song"), self.ent("work", "Song (arr.)")
        self.edge(rec, work, "performance")
        self.edge(work, other_work, "arrangement")
        first = self.ent("recording", "Cover 1")
        second = self.ent("recording", "Cover 2")
        third = self.ent("recording", "Arranged")
        self.edge(first, work, "performance")
        self.edge(second, work, "performance")
        self.edge(third, other_work, "performance")
        self.assertEqual(self.run_kind("composition_path")["stops_max"], 3)

    def test_scene_path_needs_a_city_area_and_overlapping_start_years_never_a_country(self):
        anchor, _, _ = self.library()
        city, country = self.ent("area", "City"), self.ent("area", "Country")
        self.db.execute("INSERT INTO area_facts (entity_id, kind) VALUES (?, 'city')", (city,))
        self.db.execute("INSERT INTO area_facts (entity_id, kind) VALUES (?, 'country')", (country,))

        def artist(name, year, area):
            a = anchor if name == "Anchor" else self.ent("artist", name)
            self.db.execute("INSERT OR REPLACE INTO artist_life_span (entity_id, begin_date, ended) VALUES (?, ?, 0)", (a, year))
            self.edge(a, area, "area")
            return a

        artist("Anchor", "1960", city)
        artist("Peer", "1965", city)
        artist("Too late", "1990", city)
        artist("Same country", "1960", country)
        artist("Anchor-country", "1960", country)
        result = self.run_kind("scene_path", min_stops=1)
        self.assertEqual(result["stops_max"], 1)

    def test_same_studio_needs_known_and_different_decades(self):
        anchor, release, rec = self.library()
        self.db.execute("INSERT INTO release_facts (entity_id, date) VALUES (?, '1969-05-01')", (release,))
        studio = self.ent("place", "Studio A")
        self.db.execute("INSERT INTO place_facts (entity_id, kind) VALUES (?, 'studio')", (studio,))
        self.edge(studio, rec, "recorded at")
        later = self.ent("recording", "Later")
        same = self.ent("recording", "Same decade")
        undated = self.ent("recording", "Undated")
        for r, date in ((later, "1983-01-01"), (same, "1968-01-01")):
            rel = self.ent("release", f"{r} release")
            self.db.execute("INSERT INTO release_facts (entity_id, date) VALUES (?, ?)", (rel, date))
            self.edge(r, rel, "appears_on")
        for r in (later, same, undated):
            self.edge(studio, r, "recorded at")
        result = self.run_kind("same_studio_different_decade", min_stops=1)
        self.assertEqual(result["stops_max"], 1)
        self.assertEqual(result["candidates_without_a_confirmed_stop"], 2)

    def test_an_empty_slice_is_not_measurable_rather_than_dropped(self):
        self.library()
        report = measure(self.db)
        self.assertEqual(set(report["kinds"]), set(KINDS))
        for kind in ("label_path", "composition_path", "scene_path", "same_studio_different_decade"):
            self.assertEqual(report["kinds"][kind]["verdict"], "not_measurable", kind)
        self.assertIn("scene_path", report["not_measurable"])
        self.assertEqual(report["inputs"]["owned_artists"], 1)

    def test_a_slow_kind_is_dropped_by_the_precompute_budget(self):
        anchor, _, rec = self.library()
        player = self.ent("artist", "Player")
        self.edge(player, rec, "instrument")
        for i in range(3):
            self.edge(player, self.ent("recording", f"O{i}"), "instrument")
        self.db.commit()
        result = measure(self.db, Criteria(assumed_anchors=10**12, max_seconds=1.0), ("follow_the_musician",))
        self.assertEqual(result["kinds"]["follow_the_musician"]["verdict"], "drop_precompute_too_slow")
        self.assertEqual(result["drop"], ["follow_the_musician"])

    def test_the_measurement_writes_nothing_to_the_store(self):
        self.library()
        self.db.commit()
        before = self.db.execute("SELECT (SELECT COUNT(*) FROM edges), (SELECT COUNT(*) FROM entities)").fetchone()[:]
        measure(self.db)
        after = self.db.execute("SELECT (SELECT COUNT(*) FROM edges), (SELECT COUNT(*) FROM entities)").fetchone()[:]
        self.assertEqual(tuple(before), tuple(after))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM sqlite_temp_master WHERE name LIKE 'cov_%'").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
