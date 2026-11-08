import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from intelligence.graph.paths import PATH_KINDS, PathLimits, build_path, cached_path
from intelligence.store import generations, open_store
from intelligence.store import repositories as repo

DUMP = "musicbrainz_dump"


class PathTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = open_store(Path(self._tmp.name) / "p.sqlite3")
        self.n = 0

    def tearDown(self):
        self.db.close()
        self._tmp.cleanup()

    def ent(self, kind, name, **kw):
        self.n += 1
        return repo.upsert_entity(self.db, kind, name, mbid=f"e0000000-0000-0000-0000-{self.n:012d}", **kw)[0]

    def edge(self, a, b, rel, *, ec="source_explicit", mq="exact_mbid", src=DUMP, **kw):
        return repo.add_edge(self.db, a, b, rel, source=src, evidence_class=ec, match_quality=mq, **kw)[0]

    def library(self, name="Anchor"):
        artist = self.ent("artist", name, owned=True)
        release = self.ent("release", name + " LP", owned=True)
        rec = self.ent("recording", name + " Song", owned=True)
        self.edge(release, artist, "credited_to", ec="library_tag", src="navidrome")
        self.edge(rec, release, "appears_on", ec="library_tag", src="navidrome")
        return artist, release, rec

    def test_kinds_without_a_builder_are_refused(self):
        a, _, _ = self.library()
        for kind in ("same_studio_different_decade", "nonsense"):
            with self.assertRaises(ValueError):
                build_path(self.db, a, kind)

    def test_sideman_to_leader_links_credited_recordings_to_release_leaders(self):
        a, _, _ = self.library()
        rec = self.ent("recording", "Session Take")
        rel = self.ent("release", "Leader LP")
        leader = self.ent("artist", "Leader")
        own_lp = self.ent("release", "Own LP")
        self.edge(a, rec, "instrument")
        self.edge(rec, rel, "track_on", src="musicbrainz_dump_releases")
        self.edge(rel, leader, "release_artist", src="musicbrainz_dump_releases")
        self.edge(rec, own_lp, "track_on", src="musicbrainz_dump_releases")
        self.edge(own_lp, a, "release_artist", src="musicbrainz_dump_releases")
        r = build_path(self.db, a, "sideman_to_leader")
        self.assertEqual(r["status"], "ok")
        self.assertEqual([s["entity"]["id"] for s in r["stops"]], [leader])
        reason = r["stops"][0]["reasons"][0]
        self.assertEqual((reason["code"], reason["via"]["id"], reason["anchor"]["id"]), ("sideman_on", rel, rec))
        self.assertEqual(len(reason["evidence"]), 3)

    def test_sideman_to_leader_skips_the_start_a_release_it_leads_and_uncertain_links(self):
        a, _, _ = self.library()
        rec = self.ent("recording", "Take")
        rel = self.ent("release", "LP")
        other = self.ent("artist", "Other")
        self.edge(a, rec, "instrument")
        self.edge(rec, rel, "track_on", ec="inferred", src="musicbrainz_dump_releases")
        self.edge(rel, other, "release_artist", src="musicbrainz_dump_releases")
        self.assertEqual(build_path(self.db, a, "sideman_to_leader")["status"], "empty")

    def test_sideman_to_leader_only_uses_performer_and_producer_credits(self):
        a, _, _ = self.library()
        leader = self.ent("artist", "Leader")
        rel = self.ent("release", "LP")
        for role, expect in (("producer", "ok"), ("writer", "empty"), ("mix", "empty")):
            with self.subTest(role=role):
                rec = self.ent("recording", "Take " + role)
                self.edge(a, rec, role)
                self.edge(rec, rel, "track_on", src="musicbrainz_dump_releases")
                self.edge(rel, leader, "release_artist", src="musicbrainz_dump_releases")
                self.assertEqual(build_path(self.db, a, "sideman_to_leader")["status"], expect)
                self.db.execute("DELETE FROM edges WHERE from_id = ?", (a,)); self.db.execute("DELETE FROM edges WHERE from_id = ?", (rec,))
                self.db.commit()

    def test_low_quality_self_credit_does_not_veto_a_leader(self):
        a, _, _ = self.library()
        rec, rel, leader = self.ent("recording", "Take"), self.ent("release", "LP"), self.ent("artist", "Leader")
        self.edge(a, rec, "instrument")
        self.edge(rec, rel, "track_on", src="musicbrainz_dump_releases")
        self.edge(rel, leader, "release_artist", src="musicbrainz_dump_releases")
        self.edge(rel, a, "release_artist", ec="inferred", src="musicbrainz_dump_releases")
        self.assertEqual([s["entity"]["id"] for s in build_path(self.db, a, "sideman_to_leader")["stops"]], [leader])

    def test_unknown_start_is_none_and_non_artist_start_is_refused(self):
        a, release, _ = self.library()
        self.assertIsNone(build_path(self.db, 9999, "scene_path"))
        with self.assertRaises(ValueError):
            build_path(self.db, release, "scene_path")

    def test_follow_the_musician_stops_have_reasons_and_skip_own_and_uncertain(self):
        a, _, rec = self.library()
        player, guessed = self.ent("artist", "Player"), self.ent("artist", "Guessed")
        self.edge(player, rec, "instrument", role="guitar")
        self.edge(guessed, rec, "instrument", ec="inferred")
        other, never = self.ent("recording", "Other"), self.ent("recording", "Never")
        self.edge(player, other, "instrument")
        self.edge(guessed, never, "instrument")
        path = build_path(self.db, a, "follow_the_musician")
        self.assertEqual(path["status"], "ok")
        self.assertEqual([s["entity"]["canonical_name"] for s in path["stops"]], ["Other"])
        self.assertEqual(path["stops"][0]["presentation"], {"title": "Player", "context": "Anchor LP", "album": None, "album_artist": None, "artist": None})
        reason = path["stops"][0]["reasons"][0]
        self.assertEqual(reason["code"], "shared_musician")
        self.assertEqual(reason["via"]["canonical_name"], "Player")
        self.assertEqual(reason["anchor"]["canonical_name"], "Anchor Song")
        self.assertEqual(len(reason["evidence"]), 2)
        self.assertEqual(reason["evidence"][0]["role"], "guitar")

    def test_follow_the_musician_reads_a_bounded_slice_of_a_hub_players_credits(self):
        a, _, rec = self.library()
        hub, rare = self.ent("artist", "Hub"), self.ent("artist", "Rare")
        self.edge(hub, rec, "instrument")
        self.edge(rare, rec, "instrument")
        keep = self.ent("recording", "RareOnly")
        self.edge(rare, keep, "instrument")
        for i in range(20):
            self.edge(hub, self.ent("recording", f"Hub{i:02d}"), "instrument")
        path = build_path(self.db, a, "follow_the_musician", limits=PathLimits(max_per_bridge=5))
        names = [s["entity"]["canonical_name"] for s in path["stops"]]
        self.assertIn("RareOnly", names)                       # the rare player is never crowded out
        self.assertEqual(sum(n.startswith("Hub") for n in names), 4)  # hub: 5 credits read, one is the shared recording
        self.assertEqual(path["truncated"], "rows")
        full = build_path(self.db, a, "follow_the_musician")
        self.assertEqual(len(full["stops"]), 21)
        self.assertIsNone(full["truncated"])

    def test_composition_path_reads_a_bounded_slice_of_a_much_recorded_work(self):
        a, _, rec = self.library()
        standard, rare = self.ent("work", "Standard"), self.ent("work", "Rare Piece")
        self.edge(rec, standard, "performance")
        who = self.ent("artist", "Cover band")
        for i in range(20):
            t = self.ent("recording", f"Take{i:02d}")
            self.edge(t, standard, "performance"); self.edge(who, t, "performer")
        rare_rec = self.ent("recording", "RareTake")
        self.edge(who, rare_rec, "performer")
        self.edge(rec, rare, "performance")
        self.edge(rare_rec, rare, "performance")
        path = build_path(self.db, a, "composition_path", limits=PathLimits(max_per_bridge=5))
        names = [s["entity"]["canonical_name"] for s in path["stops"]]
        self.assertIn("RareTake", names)
        self.assertEqual(sum(n.startswith("Take") for n in names), 4)
        self.assertEqual(path["truncated"], "rows")

    def test_no_evidence_gives_an_empty_path(self):
        a, _, _ = self.library()
        for kind in PATH_KINDS:
            path = build_path(self.db, a, kind)
            self.assertEqual((path["status"], path["stops"]), ("empty", []), kind)

    def test_stops_are_ordered_by_reason_count_then_name(self):
        a, _, rec = self.library()
        p1, p2 = self.ent("artist", "P1"), self.ent("artist", "P2")
        for p in (p1, p2):
            self.edge(p, rec, "instrument")
        both, one = self.ent("recording", "Both"), self.ent("recording", "One")
        self.edge(p1, both, "instrument")
        self.edge(p2, both, "instrument")
        self.edge(p1, one, "instrument")
        path = build_path(self.db, a, "follow_the_musician")
        self.assertEqual([(s["entity"]["canonical_name"], s["reason_count"]) for s in path["stops"]],
                         [("Both", 2), ("One", 1)])

    def test_label_path_same_and_related_label(self):
        a, release, _ = self.library()
        label, parent, sibling = self.ent("label", "L"), self.ent("label", "Parent"), self.ent("label", "Sib")
        self.edge(label, parent, "label ownership")
        self.edge(parent, sibling, "label ownership")
        same, related, own2 = self.ent("release", "Same"), self.ent("release", "Related"), self.ent("release", "Own2")
        release_artist = self.ent("artist", "Same Release Artist")
        self.edge(same, release_artist, "release_artist", src="musicbrainz_dump_releases")
        for rel_id, lab in ((release, label), (same, label), (related, parent)):
            self.db.execute("INSERT INTO release_labels (release_id, label_id, catalogue_number) VALUES (?, ?, ?)",
                            (rel_id, lab, "C-1"))
        self.db.commit()
        path = build_path(self.db, a, "label_path")
        by_name = {s["entity"]["canonical_name"]: s for s in path["stops"]}
        self.assertEqual(set(by_name), {"Same", "Related"})
        self.assertEqual(by_name["Same"]["reasons"][0]["code"], "same_label")
        self.assertEqual(by_name["Related"]["reasons"][0]["code"], "related_label")
        self.assertTrue(by_name["Same"]["reasons"][0]["evidence"])
        self.assertEqual(by_name["Same"]["presentation"], {"title": "Same", "context": "Same Release Artist", "album": "Same", "album_artist": "Same Release Artist", "artist": None})
        self.assertEqual(path["stops"][0]["entity"]["canonical_name"], "Same")

    def test_follow_the_musician_presentation_names_the_songs_own_album(self):
        a, _, rec = self.library()
        player, other = self.ent("artist", "Player"), self.ent("recording", "Other")
        album, band = self.ent("release", "Other LP"), self.ent("artist", "The Band")
        self.edge(player, rec, "instrument")
        self.edge(player, other, "instrument")
        self.edge(other, album, "track_on", src="musicbrainz_dump_releases")
        self.edge(album, band, "release_artist", src="musicbrainz_dump_releases")
        presentation = build_path(self.db, a, "follow_the_musician")["stops"][0]["presentation"]
        self.assertEqual((presentation["album"], presentation["album_artist"]), ("Other LP", "The Band"))

    def test_composition_path_other_recordings_of_the_same_work(self):
        a, _, rec = self.library()
        work, rec2 = self.ent("work", "Song"), self.ent("recording", "Cover")
        self.edge(rec, work, "performance")
        self.edge(rec2, work, "performance")
        self.assertEqual(build_path(self.db, a, "composition_path")["status"], "empty")  # no credited performer: dropped
        self.edge(self.ent("artist", "Cover artist"), rec2, "performer")
        path = build_path(self.db, a, "composition_path")
        self.assertEqual([s["entity"]["canonical_name"] for s in path["stops"]], ["Cover"])
        reason = path["stops"][0]["reasons"][0]
        self.assertEqual((reason["code"], reason["via"]["canonical_name"]), ("same_work", "Song"))
        self.assertEqual(len(reason["evidence"]), 2)
        self.assertEqual(reason["text"], "another recording of Song, the same work as Anchor Song, a recording in your library")
        self.assertEqual(path["stops"][0]["presentation"], {"title": "Cover artist", "context": "Cover", "album": None, "album_artist": None, "artist": "Cover artist"})

    def test_follow_the_musician_ignores_producers_and_collapses_one_artist(self):
        a, _, rec = self.library()
        player, producer = self.ent("artist", "Player"), self.ent("artist", "Producer")
        self.edge(player, rec, "instrument"); self.edge(producer, rec, "producer")
        lp, lead = self.ent("release", "Their LP"), self.ent("artist", "Their Band")
        for n in ("One", "Two"):
            t = self.ent("recording", n)
            self.edge(player, t, "instrument"); self.edge(producer, t, "producer")
            self.edge(t, lp, "appears_on")
        self.edge(lp, lead, "release_artist", src="musicbrainz_dump_releases")
        only_prod = self.ent("recording", "ProducedOnly"); self.edge(producer, only_prod, "producer")
        path = build_path(self.db, a, "follow_the_musician")
        names = [s["entity"]["canonical_name"] for s in path["stops"]]
        self.assertEqual(len(names), 1)  # One and Two lead to the same artist; ProducedOnly is no performer credit
        self.assertNotIn("ProducedOnly", names)
        self.assertEqual({r["via"]["canonical_name"] for r in path["stops"][0]["reasons"]}, {"Player"})

    def test_sideman_never_lists_unknown_artists(self):
        a, _, _ = self.library()
        rec, rel = self.ent("recording", "Take"), self.ent("release", "LP")
        self.edge(a, rec, "instrument"); self.edge(rec, rel, "track_on", src="musicbrainz_dump_releases")
        self.edge(rel, self.ent("artist", "[unknown]"), "release_artist", src="musicbrainz_dump_releases")
        self.assertEqual(build_path(self.db, a, "sideman_to_leader")["status"], "empty")

    def test_label_path_one_row_per_artist_and_credit_from_the_owned_twin(self):
        a, _, _ = self.library()
        label = self.ent("label", "Lab")
        own = self.db.execute("SELECT id FROM entities WHERE type='release' AND owned=1").fetchone()["id"]
        self.db.execute("INSERT INTO release_labels (release_id, label_id, catalogue_number) VALUES (?, ?, 'x')", (own, label))
        band = self.ent("artist", "Band")
        for title in ("B1", "B2"):
            r = self.ent("release", title); self.edge(r, band, "release_artist", src="musicbrainz_dump_releases")
            self.db.execute("INSERT INTO release_labels (release_id, label_id, catalogue_number) VALUES (?, ?, 'y')", (r, label))
        twin_artist = self.ent("artist", "Floyd")
        twin = self.ent("release", "Moon", owned=True); self.edge(twin, twin_artist, "credited_to", ec="library_tag", src="navidrome")
        other = self.ent("release", "Moon")  # an edition with no credit of its own
        self.db.execute("INSERT INTO release_labels (release_id, label_id, catalogue_number) VALUES (?, ?, 'z')", (other, label))
        self.db.commit()
        path = build_path(self.db, a, "label_path")
        credits = sorted(s["presentation"]["album_artist"] for s in path["stops"])
        self.assertEqual(credits, ["Band", "Floyd"])

    def test_scene_path_needs_a_stated_non_country_area_and_close_start(self):
        a, _, _ = self.library()
        city, country = self.ent("area", "City"), self.ent("area", "Country")
        self.db.execute("INSERT INTO area_facts (entity_id, kind) VALUES (?, 'City')", (city,))
        self.db.execute("INSERT INTO area_facts (entity_id, kind) VALUES (?, 'Country')", (country,))
        near, far, other_country = (self.ent("artist", n) for n in ("Near", "Far", "Abroad"))
        for who, year in ((a, "1970"), (near, "1975"), (far, "1990"), (other_country, "1972")):
            self.db.execute("INSERT INTO artist_life_span (entity_id, begin_date) VALUES (?, ?)", (who, year))
        for who in (a, near, far):
            self.edge(who, city, "area")
        for who in (a, other_country):
            self.edge(who, country, "area")
        self.db.commit()
        path = build_path(self.db, a, "scene_path")
        self.assertEqual([s["entity"]["canonical_name"] for s in path["stops"]], ["Near"])
        self.assertEqual(path["stops"][0]["reasons"][0]["via"]["canonical_name"], "City")

    def test_row_limit_truncates_and_stop_limit_truncates(self):
        a, _, rec = self.library()
        player = self.ent("artist", "Player")
        self.edge(player, rec, "instrument")
        for i in range(5):
            self.edge(player, self.ent("recording", f"R{i}"), "instrument")
        self.assertEqual(build_path(self.db, a, "follow_the_musician", limits=PathLimits(max_stops=2))["truncated"], "stops")
        path = build_path(self.db, a, "follow_the_musician", limits=PathLimits(max_rows=3))
        self.assertEqual((path["truncated"], len(path["stops"])), ("rows", 3))

    def test_time_limit_returns_an_empty_truncated_path(self):
        a, _, rec = self.library()
        player = self.ent("artist", "Player")
        self.edge(player, rec, "instrument")
        ticks = iter(range(0, 1000, 10))
        with mock.patch("intelligence.graph.paths.PROGRESS_OPS", 1):
            path = build_path(self.db, a, "follow_the_musician", clock=lambda: next(ticks))
        self.assertEqual((path["truncated"], path["status"]), ("time", "empty"))

    def test_composition_path_presents_each_recordings_album_and_its_anchors(self):
        a, _, rec = self.library()
        work, rec2 = self.ent("work", "Song"), self.ent("recording", "Cover")
        self.edge(rec, work, "performance")
        self.edge(rec2, work, "performance")
        self.edge(self.ent("artist", "Cover artist"), rec2, "performer")
        cover_lp, cover_artist = self.ent("release", "Cover LP"), self.ent("artist", "Cover LP Artist")
        self.edge(rec2, cover_lp, "track_on", src="musicbrainz_dump_releases")
        self.edge(cover_lp, cover_artist, "release_artist", src="musicbrainz_dump_releases")
        stop = build_path(self.db, a, "composition_path")["stops"][0]
        self.assertEqual((stop["presentation"]["album"], stop["presentation"]["album_artist"]), ("Cover LP", "Cover LP Artist"))
        # The library anchor is the owned recording on the owned album; its album comes with the reason.
        self.assertEqual(stop["reasons"][0]["anchor_presentation"]["album"], "Anchor LP")

    def test_label_path_presents_the_anchor_albums_artist(self):
        a, release, _ = self.library()
        label, same = self.ent("label", "L"), self.ent("release", "Same")
        for rel_id in (release, same):
            self.db.execute("INSERT INTO release_labels (release_id, label_id, catalogue_number) VALUES (?, ?, ?)", (rel_id, label, "C-1"))
        self.db.commit()
        stop = build_path(self.db, a, "label_path")["stops"][0]
        self.assertEqual(stop["reasons"][0]["anchor_presentation"], {"album": "Anchor LP", "album_artist": "Anchor"})

    def test_cache_rebuilds_when_presentation_schema_changes(self):
        a, _, rec = self.library()
        player, other = self.ent("artist", "Player"), self.ent("recording", "Other")
        self.edge(player, rec, "instrument")
        self.edge(player, other, "instrument")
        cached_path(self.db, a, "follow_the_musician")
        row = self.db.execute(
            "SELECT payload FROM insights WHERE kind = 'path:follow_the_musician' AND subject_id = ?", (a,)
        ).fetchone()
        payload = json.loads(row["payload"])
        payload.pop("presentation_version")
        self.db.execute(
            "UPDATE insights SET payload = ? WHERE kind = 'path:follow_the_musician' AND subject_id = ?",
            (json.dumps(payload), a),
        )
        self.db.commit()
        rebuilt = cached_path(self.db, a, "follow_the_musician")
        self.assertEqual(rebuilt["presentation_version"], 5)
        self.assertEqual(rebuilt["stops"][0]["presentation"]["title"], "Player")

    def test_cache_hit_refresh_and_staleness(self):
        a, _, rec = self.library()
        player, other = self.ent("artist", "Player"), self.ent("recording", "Other")
        self.edge(player, rec, "instrument")
        self.edge(player, other, "instrument")
        first = cached_path(self.db, a, "follow_the_musician")
        self.edge(player, self.ent("recording", "Later"), "instrument")
        self.assertEqual(cached_path(self.db, a, "follow_the_musician"), first)  # served from the cache
        self.assertEqual(len(cached_path(self.db, a, "follow_the_musician", refresh=True)["stops"]), 2)
        self.edge(player, self.ent("recording", "Later2"), "instrument")
        generations.bump_data_version(self.db, "musicbrainz_slice")               # slice changed: stale
        self.assertEqual(len(cached_path(self.db, a, "follow_the_musician")["stops"]), 3)
        generations.bump_generation(self.db)                                       # new generation: rebuilt
        self.assertEqual(cached_path(self.db, a, "follow_the_musician")["generation"], 2)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM insights WHERE kind = 'path:follow_the_musician'")
                         .fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
