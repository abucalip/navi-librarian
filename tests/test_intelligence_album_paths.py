import tempfile
import unittest
from pathlib import Path

from intelligence.graph.album_paths import PERSON_CAP, ROOM_CAP, build_album_path, cached_album_path
from intelligence.graph.paths import PathLimits
from intelligence.store import generations, open_store
from intelligence.store import repositories as repo

DUMP = "musicbrainz_dump"


class AlbumPathTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = open_store(Path(self._tmp.name) / "a.sqlite3")
        self.n = 0

    def tearDown(self):
        self.db.close()
        self._tmp.cleanup()

    def ent(self, kind, name, **kw):
        self.n += 1
        return repo.upsert_entity(self.db, kind, name, mbid=f"e0000000-0000-0000-0000-{self.n:012d}", **kw)[0]

    def edge(self, a, b, rel, *, ec="source_explicit", mq="exact_mbid", src=DUMP, **kw):
        return repo.add_edge(self.db, a, b, rel, source=src, evidence_class=ec, match_quality=mq, **kw)[0]

    def album(self, name, artist=None, tracks=("T",), credit=True):
        """An owned album with one owned recording per track name (``credit=False``: no credited artist)."""
        artist = artist if artist is not None else self.ent("artist", name + " Artist", owned=True)
        rel = self.ent("release", name, owned=True)
        if credit:
            self.edge(rel, artist, "credited_to", ec="library_tag", src="navidrome")
        recs = []
        for t in tracks:
            rec = self.ent("recording", f"{name}: {t}", owned=True)
            self.edge(rec, rel, "appears_on", ec="library_tag", src="navidrome")
            recs.append(rec)
        return rel, recs, artist

    def stops(self, start, kind, **kw):
        return build_album_path(self.db, start, kind, **kw)

    # --- Studio Crew ---

    def test_crew_links_albums_by_album_and_recording_scope_credits(self):
        a1, (r1,), _ = self.album("A1")
        a2, (r2,), _ = self.album("A2")
        a3, (r3,), _ = self.album("A3")
        eng, prod = self.ent("artist", "Engineer"), self.ent("artist", "Producer")
        self.edge(eng, r1, "engineer")
        self.edge(eng, r2, "engineer")      # recording scope on A2
        self.edge(prod, a1, "producer")     # album scope on the start
        self.edge(prod, a3, "producer")     # album scope on A3
        r = self.stops(a1, "album_crew")
        self.assertEqual(r["status"], "ok")
        self.assertEqual({s["entity"]["id"] for s in r["stops"]}, {a2, a3})
        by = {s["entity"]["id"]: s["reasons"][0] for s in r["stops"]}
        self.assertEqual((by[a2]["code"], by[a2]["via"]["id"], by[a2]["anchor"]["id"]), ("crew_on", eng, r1))
        self.assertEqual((by[a3]["via"]["id"], by[a3]["anchor"]["id"]), (prod, a1))
        self.assertEqual(len(by[a2]["evidence"]), 2)
        self.assertNotIn("?", by[a2]["text"])

    def test_crew_ignores_performers_and_the_start_itself(self):
        a1, (r1,), _ = self.album("A1")
        other = self.ent("release", "Not Owned")
        rec = self.ent("recording", "Elsewhere")
        self.edge(rec, other, "appears_on")
        p, player = self.ent("artist", "P"), self.ent("artist", "Player")
        self.edge(p, r1, "mix")
        self.edge(player, r1, "instrument")
        a2, (r2,), _ = self.album("A2")
        self.edge(player, r2, "instrument")  # a performer is not crew
        self.assertEqual(self.stops(a1, "album_crew")["status"], "empty")

    def test_uncertain_credits_are_never_used_not_even_as_a_bridge(self):
        a1, (r1,), _ = self.album("A1")
        a2, (r2,), _ = self.album("A2")
        a3, (r3,), _ = self.album("A3")
        a4, (r4,), _ = self.album("A4")
        shaky, fuzzy = self.ent("artist", "Shaky"), self.ent("artist", "Fuzzy")
        self.edge(shaky, r1, "producer")
        self.edge(shaky, r2, "producer", ec="inferred")
        self.edge(fuzzy, r1, "producer", mq="fuzzy_unconfirmed")
        self.edge(fuzzy, r3, "producer")
        self.edge(shaky, r4, "producer", mq="unresolved")
        self.assertEqual(self.stops(a1, "album_crew")["status"], "empty")

    def test_placeholder_artists_are_not_crew(self):
        a1, (r1,), _ = self.album("A1")
        a2, (r2,), _ = self.album("A2")
        unknown = self.ent("artist", "[unknown]")
        self.edge(unknown, r1, "producer")
        self.edge(unknown, r2, "producer")
        self.assertEqual(self.stops(a1, "album_crew")["status"], "empty")

    def test_more_shared_people_first_then_the_earlier_release(self):
        a1, (r1,), _ = self.album("A1")
        early, (re_,), _ = self.album("Early")
        late, (rl,), _ = self.album("Late")
        both, (rb,), _ = self.album("Both")
        p, q = self.ent("artist", "P"), self.ent("artist", "Q")
        for who in (p, q):
            self.edge(who, r1, "engineer")
            self.edge(who, rb, "engineer")
        self.edge(p, re_, "engineer")
        self.edge(p, rl, "engineer")
        for rel, date in ((early, "1970"), (late, "1990-05-01")):
            self.db.execute("INSERT INTO release_facts (entity_id, date) VALUES (?, ?)", (rel, date))
        r = self.stops(a1, "album_crew")
        self.assertEqual([s["entity"]["id"] for s in r["stops"]], [both, early, late])

    def test_a_hub_person_is_capped_and_the_rest_is_counted(self):
        a1, (r1,), _ = self.album("A1")
        hub = self.ent("artist", "Hub")
        self.edge(hub, r1, "producer")
        for i in range(PERSON_CAP + 3):
            rel, _, _ = self.album(f"H{i}")
            self.edge(hub, rel, "producer")
        r = self.stops(a1, "album_crew", limits=PathLimits(max_stops=500))
        self.assertEqual(len(r["stops"]), PERSON_CAP)
        self.assertEqual([(c["via"]["id"], c["more"]) for c in r["capped"]], [(hub, 3)])

    def test_stops_beyond_the_limit_mark_the_path_truncated(self):
        a1, (r1,), _ = self.album("A1")
        p = self.ent("artist", "P")
        self.edge(p, r1, "producer")
        for i in range(3):
            rel, _, _ = self.album(f"X{i}")
            self.edge(p, rel, "producer")
        r = self.stops(a1, "album_crew", limits=PathLimits(max_stops=2))
        self.assertEqual((len(r["stops"]), r["truncated"]), (2, "stops"))

    def test_an_expired_clock_is_reported_as_time(self):
        a1, (r1,), _ = self.album("A1")
        a2, (r2,), _ = self.album("A2")
        p = self.ent("artist", "P")
        self.edge(p, r1, "producer")
        self.edge(p, r2, "producer")
        ticks = iter(range(0, 1000, 10))
        r = self.stops(a1, "album_crew", clock=lambda: next(ticks))
        self.assertEqual(r["truncated"], "time")

    # --- overlap with the artist paths ---

    def test_a_stop_the_artists_own_paths_reach_is_dropped(self):
        artist = self.ent("artist", "Lead", owned=True)
        a1, (r1,), _ = self.album("A1", artist)
        a2, (r2,), _ = self.album("A2")      # reached by crew, and by the artist's label path
        a3, (r3,), _ = self.album("A3")      # reached by crew only
        p = self.ent("artist", "P")
        for rel in (a1, a2, a3):
            self.edge(p, rel, "producer")
        label = self.ent("label", "Label")
        for rel in (a1, a2):
            self.db.execute("INSERT INTO release_labels (release_id, label_id) VALUES (?, ?)", (rel, label))
        r = self.stops(a1, "album_crew")
        self.assertEqual([s["entity"]["id"] for s in r["stops"]], [a3])
        self.assertEqual(r["overlap_dropped"], 1)

    # --- Guest List ---

    def test_guests_exclude_the_albums_own_artists_and_match_any_album(self):
        lead = self.ent("artist", "Lead", owned=True)
        a1, (r1,), _ = self.album("A1", lead, credit=False)
        self.edge(a1, lead, "release_artist")   # led by Lead, but not a library credit
        a2, (r2,), _ = self.album("A2")
        a3, (r3,), _ = self.album("A3")
        guest = self.ent("artist", "Guest")
        self.edge(guest, r1, "vocal", role="lead vocals")
        self.edge(guest, r2, "vocal")
        self.edge(lead, r1, "vocal")
        self.edge(lead, r3, "vocal")        # the album's own artist is not a guest
        r = self.stops(a1, "album_guests")
        self.assertEqual([s["entity"]["id"] for s in r["stops"]], [a2])
        reason = r["stops"][0]["reasons"][0]
        self.assertEqual((reason["code"], reason["via"]["id"], reason["anchor"]["id"]), ("guest_on", guest, r1))
        self.assertEqual([e["role"] for e in reason["evidence"]], ["lead vocals", None])

    def test_guests_are_not_made_from_crew_credits(self):
        a1, (r1,), _ = self.album("A1")
        a2, (r2,), _ = self.album("A2")
        p = self.ent("artist", "P")
        self.edge(p, r1, "producer")
        self.edge(p, r2, "producer")
        self.assertEqual(self.stops(a1, "album_guests")["status"], "empty")

    def test_one_guest_on_two_tracks_is_one_stop_with_two_reasons(self):
        a1, (r1, r2), _ = self.album("A1", tracks=("one", "two"), credit=False)
        a2, (r3,), _ = self.album("A2")
        guest = self.ent("artist", "Guest")
        for rec in (r1, r2, r3):
            self.edge(guest, rec, "instrument")
        r = self.stops(a1, "album_guests")
        self.assertEqual(len(r["stops"]), 1)
        self.assertEqual((r["stops"][0]["reason_count"], {x["anchor"]["id"] for x in r["stops"][0]["reasons"]}), (2, {r1, r2}))

    # --- Covers and Sources ---

    def test_works_find_other_recordings_and_related_works(self):
        a1, (r1,), _ = self.album("A1", credit=False)
        a2, (r2,), _ = self.album("A2")
        a3, (r3,), _ = self.album("A3")
        a4, (r4,), _ = self.album("A4")
        song, source, unrelated = (self.ent("work", n) for n in ("Song", "Source Song", "Other"))
        for rec, work in ((r1, song), (r2, song), (r3, source), (r4, unrelated)):
            self.edge(rec, work, "performance")
        self.edge(song, source, "based on")
        r = self.stops(a1, "album_works")
        found = {s["entity"]["id"]: s["reasons"][0] for s in r["stops"]}
        self.assertEqual(set(found), {a2, a3})
        self.assertEqual((found[a2]["code"], found[a2]["via"]["id"], found[a2]["anchor"]["id"]), ("same_work", song, r1))
        self.assertEqual((found[a3]["code"], found[a3]["via"]["id"]), ("derived_work", source))
        self.assertEqual(len(found[a3]["evidence"]), 3)
        self.assertEqual([s["entity"]["id"] for s in r["stops"]], [a2, a3])  # same work before a derived one

    def test_an_unstated_or_uncertain_work_relation_gives_nothing(self):
        a1, (r1,), _ = self.album("A1")
        a2, (r2,), _ = self.album("A2")
        song, source = self.ent("work", "Song"), self.ent("work", "Source")
        self.edge(r1, song, "performance")
        self.edge(r2, source, "performance")
        self.edge(song, source, "based on", ec="inferred")
        self.edge(song, source, "medley of")  # not a relation the path uses
        self.assertEqual(self.stops(a1, "album_works")["status"], "empty")

    # --- Same Year, Same Scene ---

    def dated(self, rel, date):
        self.db.execute("INSERT INTO release_facts (entity_id, date) VALUES (?, ?)", (rel, date))

    def label(self, name, *releases):
        label = self.ent("label", name)
        for rel in releases:
            self.db.execute("INSERT INTO release_labels (release_id, label_id) VALUES (?, ?)", (rel, label))
        return label

    def test_moment_needs_a_stated_link_a_date_match_alone_is_nothing(self):
        a1, _, _ = self.album("A1", credit=False)
        a2, _, _ = self.album("A2", credit=False)
        self.dated(a1, "1970-03-01")
        self.dated(a2, "1970-05-01")
        self.assertEqual(self.stops(a1, "album_moment")["status"], "empty")

    def test_moment_label_within_two_years_inclusive_and_not_three(self):
        a1, _, _ = self.album("A1", credit=False)
        near, _, _ = self.album("Near", credit=False)
        edge, _, _ = self.album("Edge", credit=False)
        far, _, _ = self.album("Far", credit=False)
        undated, _, _ = self.album("Undated", credit=False)
        lab = self.label("Lab", a1, near, edge, far, undated)
        for rel, date in ((a1, "1970-06-01"), (near, "1969"), (edge, "1972-12-31"), (far, "1973-01-01")):
            self.dated(rel, date)
        r = self.stops(a1, "album_moment")
        self.assertEqual([s["entity"]["id"] for s in r["stops"]], [near, edge])   # nearer year first
        reason = r["stops"][0]["reasons"][0]
        self.assertEqual((reason["code"], reason["via"]["id"], reason["anchor"]["id"], reason["evidence"]),
                         ("same_period_label", lab, a1, []))
        self.assertIn("1969", reason["text"])
        self.assertIn("1970", reason["text"])
        self.assertNotIn("?", reason["text"])

    def test_moment_uses_the_earliest_stored_date_and_skips_a_start_without_one(self):
        a1, _, _ = self.album("A1", credit=False)
        a2, _, _ = self.album("A2", credit=False)
        self.label("Lab", a1, a2)
        self.dated(a2, "1970")
        self.assertEqual(self.stops(a1, "album_moment")["status"], "empty")    # the start has no date
        self.dated(a1, "1990")
        self.assertEqual(self.stops(a1, "album_moment")["status"], "empty")    # the dates are 20 years apart

    def test_moment_reaches_unowned_albums_and_lists_them_first(self):
        a1, _, _ = self.album("A1", credit=False)
        other = self.ent("release", "Not Owned")
        a2, _, _ = self.album("A2", credit=False)
        self.label("Lab", a1, other, a2)
        self.dated(a1, "1970")
        self.dated(other, "1970")
        self.dated(a2, "1970")
        r = self.stops(a1, "album_moment")
        self.assertEqual([(s["entity"]["id"], s["entity"]["owned"]) for s in r["stops"]], [(other, 0), (a2, 1)])
        self.assertEqual(self.stops(a1, "album_moment", owned_only=True)["stops"][0]["entity"]["id"], a2)

    def test_moment_shared_credited_artist_is_a_credit_link_with_both_edges(self):
        lead = self.ent("artist", "Lead", owned=True)
        a1, _, _ = self.album("A1", lead)
        a2, _, _ = self.album("A2", lead)
        self.dated(a1, "1970")
        self.dated(a2, "1971")
        stop = self.stops(a1, "album_moment")["stops"][0]
        reason = stop["reasons"][0]
        self.assertEqual((stop["entity"]["id"], reason["code"], reason["via"]["id"]), (a2, "same_period_credit", lead))
        self.assertEqual(len(reason["evidence"]), 2)

    def test_moment_credit_link_of_an_uncertain_edge_or_placeholder_artist_is_not_used(self):
        shaky = self.ent("artist", "Shaky")
        unknown = self.ent("artist", "[unknown]")
        a1, _, _ = self.album("A1", credit=False)
        a2, _, _ = self.album("A2", credit=False)
        for rel in (a1, a2):
            self.edge(rel, unknown, "credited_to")
        self.edge(a1, shaky, "credited_to")
        self.edge(a2, shaky, "credited_to", mq="fuzzy_unconfirmed")
        self.dated(a1, "1970")
        self.dated(a2, "1970")
        self.assertEqual(self.stops(a1, "album_moment")["status"], "empty")

    def test_moment_area_must_be_a_non_country_area_through_a_different_artist(self):
        x, y, z = (self.ent("artist", n) for n in "XYZ")
        a1, _, _ = self.album("A1", x)
        a2, _, _ = self.album("A2", y)
        a3, _, _ = self.album("A3", z)
        city, country = self.ent("area", "Chicago"), self.ent("area", "United States")
        self.db.execute("INSERT INTO area_facts (entity_id, kind) VALUES (?, 'city')", (city,))
        self.db.execute("INSERT INTO area_facts (entity_id, kind) VALUES (?, 'Country')", (country,))
        for who in (x, y):
            self.edge(who, city, "area")
        self.edge(x, country, "area")
        self.edge(z, country, "area")
        for rel in (a1, a2, a3):
            self.dated(rel, "1970")
        r = self.stops(a1, "album_moment")
        self.assertEqual([s["entity"]["id"] for s in r["stops"]], [a2])   # the shared city; not the shared country
        reason = r["stops"][0]["reasons"][0]
        self.assertEqual((reason["code"], reason["via"]["id"], len(reason["evidence"])), ("same_period_area", city, 2))

    def test_moment_more_distinct_links_first_then_the_nearer_year(self):
        a1, _, _ = self.album("A1", credit=False)
        both, _, _ = self.album("Both", credit=False)
        near, _, _ = self.album("Near", credit=False)
        far, _, _ = self.album("Far", credit=False)
        self.label("One", a1, both, near, far)
        self.label("Two", a1, both)
        for rel, d in ((a1, "1970"), (both, "1972"), (near, "1970"), (far, "1971")):
            self.dated(rel, d)
        self.assertEqual([s["entity"]["id"] for s in self.stops(a1, "album_moment")["stops"]], [both, near, far])

    def test_moment_label_stops_the_artists_label_path_reaches_are_dropped(self):
        lead = self.ent("artist", "Lead", owned=True)
        a1, _, _ = self.album("A1", lead)
        a2, _, _ = self.album("A2")
        self.label("Lab", a1, a2)
        self.dated(a1, "1970")
        self.dated(a2, "1970")
        r = self.stops(a1, "album_moment")
        self.assertEqual((r["status"], r["overlap_dropped"]), ("empty", 1))

    # --- Same Room ---

    def room(self, name, kind="place"):
        return self.ent(kind, name)

    def test_room_links_albums_with_a_recording_made_at_the_same_place(self):
        a1, (r1,), _ = self.album("A1")
        a2, (r2,), _ = self.album("A2")
        a3, (r3,), _ = self.album("A3")
        studio = self.room("Studio One")
        self.edge(studio, r1, "recorded at")
        self.edge(studio, r2, "mixed at")
        r = self.stops(a1, "album_room")
        self.assertEqual(r["status"], "ok")
        self.assertEqual([s["entity"]["id"] for s in r["stops"]], [a2])
        reason = r["stops"][0]["reasons"][0]
        self.assertEqual((reason["code"], reason["via"]["id"], reason["anchor"]["id"]), ("recorded_at", studio, r1))
        self.assertEqual(len(reason["evidence"]), 2)
        self.assertNotIn("?", reason["text"])

    def test_room_accepts_an_event_but_never_an_area(self):
        a1, (r1,), _ = self.album("A1")
        a2, (r2,), _ = self.album("A2")
        a3, (r3,), _ = self.album("A3")
        festival, city = self.room("Festival", "event"), self.room("Paris", "area")
        self.edge(festival, r1, "recorded at")
        self.edge(festival, r2, "recorded at")
        self.edge(city, r1, "recorded in")
        self.edge(city, r3, "recorded in")
        r = self.stops(a1, "album_room")
        self.assertEqual({s["entity"]["id"] for s in r["stops"]}, {a2})

    def test_room_reaches_unowned_albums_first_and_ignores_the_start_and_uncertain_edges(self):
        a1, (r1,), _ = self.album("A1")
        a2, (r2,), _ = self.album("A2")
        a3, (r3,), _ = self.album("A3")
        other = self.ent("release", "Not Owned")
        rec = self.ent("recording", "Elsewhere")
        self.edge(rec, other, "appears_on")
        studio, shaky = self.room("Studio"), self.room("Shaky")
        self.edge(studio, r1, "recorded at")
        self.edge(studio, rec, "recorded at")        # an album outside the library
        self.edge(shaky, r1, "recorded at")
        self.edge(shaky, r2, "recorded at", ec="inferred")
        self.edge(shaky, r3, "recorded at", mq="fuzzy_unconfirmed")
        r = self.stops(a1, "album_room")
        self.assertEqual([(s["entity"]["id"], s["entity"]["owned"]) for s in r["stops"]], [(other, 0)])
        reason = r["stops"][0]["reasons"][0]
        self.assertEqual(reason["target"]["id"], rec)
        self.assertEqual(reason["text"], "Studio is where A1: T from A1 was made (recorded, mixed or engineered), and where Elsewhere from Not Owned was made")
        self.assertEqual(self.stops(a1, "album_room", owned_only=True)["status"], "empty")

    def test_texts_name_albums_and_tracks_and_never_point_at_this_album(self):
        a1, (r1,), _ = self.album("A1")
        other = self.ent("release", "Elsewhere LP")
        rec = self.ent("recording", "Far Track")
        self.edge(rec, other, "appears_on")
        eng = self.ent("artist", "Engineer")
        self.edge(eng, r1, "engineer")
        self.edge(eng, rec, "engineer")
        text = self.stops(a1, "album_crew")["stops"][0]["reasons"][0]["text"]
        self.assertEqual(text, "Engineer has a production credit on A1: T from A1 and on Far Track from Elsewhere LP")
        for banned in ("this album", "started from", "a recording"):
            self.assertNotIn(banned, text)

    def test_one_stop_per_album_and_a_library_twin_is_not_a_discovery(self):
        a1, (r1,), _ = self.album("A1")
        twin, _, _ = self.album("Twin")
        pressing = self.ent("release", "Twin")          # the same title outside the library
        other = self.ent("release", "Fresh")
        again = self.ent("release", "Fresh")            # a second release of the same album
        eng = self.ent("artist", "Engineer")
        self.edge(eng, r1, "engineer")
        for rel in (pressing, other, again):
            rec = self.ent("recording", "x")
            self.edge(rec, rel, "appears_on")
            self.edge(eng, rec, "engineer")
        r = self.stops(a1, "album_crew")
        names = [(s["entity"]["canonical_name"], s["entity"]["owned"]) for s in r["stops"]]
        self.assertEqual(names, [("Fresh", 0), ("Twin", 1)])

    def test_room_merges_places_into_one_stop_and_caps_a_hub_place(self):
        a1, (r1, r1b), _ = self.album("A1", tracks=("T", "U"))
        a2, (r2,), _ = self.album("A2")
        one, two = self.room("One"), self.room("Two")
        for place in (one, two):
            self.edge(place, r1, "recorded at")
            self.edge(place, r2, "recorded at")
        r = self.stops(a1, "album_room")
        self.assertEqual(len(r["stops"]), 1)
        self.assertEqual({x["via"]["id"] for x in r["stops"][0]["reasons"]}, {one, two})
        hub = self.room("Hub")
        self.edge(hub, r1b, "recorded at")
        for i in range(ROOM_CAP + 5):
            _, (rx,), _ = self.album(f"X{i}")
            self.edge(hub, rx, "recorded at")
        r = self.stops(a1, "album_room", limits=PathLimits(max_stops=500, max_rows=5000))
        self.assertEqual([(c["via"]["id"], c["more"]) for c in r["capped"]], [(hub, 5)])

    # --- shape, errors, cache ---

    def test_unbuilt_kinds_and_non_release_starts_are_refused(self):
        a1, _, artist = self.album("A1")
        for kind in ("album_sonic_neighbours", "nonsense"):
            with self.assertRaises(ValueError):
                build_album_path(self.db, a1, kind)
        with self.assertRaises(ValueError):
            build_album_path(self.db, artist, "album_crew")
        self.assertIsNone(build_album_path(self.db, 99999, "album_crew"))

    def test_presentation_names_the_album_and_its_artist(self):
        a1, (r1,), _ = self.album("A1")
        a2, (r2,), artist2 = self.album("Second")
        p = self.ent("artist", "P")
        self.edge(p, r1, "mix")
        self.edge(p, r2, "mix")
        s = self.stops(a1, "album_crew")["stops"][0]["presentation"]
        self.assertEqual((s["album"], s["album_artist"]), ("Second", "Second Artist"))

    def test_running_out_of_time_while_measuring_overlap_still_returns_the_stops(self):
        artist = self.ent("artist", "Lead", owned=True)
        a1, (r1,), _ = self.album("A1", artist)
        a2, (r2,), _ = self.album("A2")
        p = self.ent("artist", "P")
        self.edge(p, r1, "producer")
        self.edge(p, r2, "producer")
        # the clock passes the deadline once the crew rows are read, so the overlap measure has no time left
        calls = iter([0, 0, 0, 0, 0] + [100] * 1000)
        r = self.stops(a1, "album_crew", clock=lambda: next(calls))
        self.assertEqual((r["truncated"], [s["entity"]["id"] for s in r["stops"]]), ("time", [a2]))

    def test_the_path_is_cached_until_the_slice_changes_and_not_when_cut_by_time(self):
        a1, (r1,), _ = self.album("A1")
        a2, (r2,), _ = self.album("A2")
        p = self.ent("artist", "P")
        self.edge(p, r1, "producer")
        self.edge(p, r2, "producer")
        first = cached_album_path(self.db, a1, "album_crew")
        self.edge(p, self.album("A3")[0], "producer")
        self.assertEqual(cached_album_path(self.db, a1, "album_crew"), first)
        self.assertEqual(len(first["stops"]), 1)
        generations.bump_data_version(self.db, "musicbrainz_slice")   # the slice changed: the cache is stale
        self.assertEqual(len(cached_album_path(self.db, a1, "album_crew")["stops"]), 2)
        ticks = iter(range(0, 1000, 10))
        cached_album_path(self.db, a1, "album_crew", refresh=True, clock=lambda: next(ticks))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM insights WHERE kind = 'path:album_crew'").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
