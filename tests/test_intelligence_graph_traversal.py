import tempfile
import unittest
from pathlib import Path

from intelligence.graph import Limits, explore, is_credit
from intelligence.store import open_store
from intelligence.store import repositories as repo


class TraversalTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db = open_store(Path(self.temp_dir.name) / "intelligence.sqlite3")
        self.addCleanup(self.db.close)

    def node(self, name):
        return repo.upsert_entity(self.db, "artist", name, mbid=f"mbid-{name}")[0]

    def link(self, a, b, relation="member_of", **kw):
        args = {"evidence_class": "source_explicit", "match_quality": "exact_mbid", "source": "musicbrainz"}
        args.update(kw)
        return repo.add_edge(self.db, a, b, relation, **args)[0]

    def ids(self, page):
        return [h.entity_id for h in page.hops]


class ShapeTests(TraversalTestCase):
    def test_nearest_first_with_depths(self):
        a, b, c, d = (self.node(n) for n in "abcd")
        self.link(a, b)
        self.link(b, c)
        self.link(c, d)
        page = explore(self.db, a, limits=Limits(max_depth=2))
        self.assertEqual([(h.entity_id, h.depth) for h in page.hops], [(b, 1), (c, 2)])
        self.assertIsNone(page.truncated)

    def test_cycle_visits_each_entity_once_and_never_the_start(self):
        a, b, c = (self.node(n) for n in "abc")
        self.link(a, b)
        self.link(b, c)
        self.link(c, a)
        page = explore(self.db, a, limits=Limits(max_depth=5))
        self.assertEqual(sorted(self.ids(page)), sorted([b, c]))

    def test_parallel_edges_collapse_into_one_hop_keeping_every_fact(self):
        a, b = self.node("a"), self.node("b")
        e1 = self.link(a, b, role="guitar")
        e2 = self.link(a, b, role="drums", source="discogs")
        page = explore(self.db, a)
        self.assertEqual(len(page.hops), 1)
        self.assertEqual([e.edge_id for e in page.hops[0].evidence], [e1, e2])
        self.assertEqual({e.source for e in page.hops[0].evidence}, {"musicbrainz", "discogs"})

    def test_shortest_path_wins(self):
        a, b, c = (self.node(n) for n in "abc")
        self.link(a, b)
        self.link(b, c)
        self.link(a, c)
        page = explore(self.db, a, limits=Limits(max_depth=3))
        self.assertEqual({h.entity_id: h.depth for h in page.hops}, {b: 1, c: 1})

    def test_direction_and_relation_filters(self):
        a, b, c = (self.node(n) for n in "abc")
        self.link(a, b, "member_of")
        self.link(c, a, "influenced_by")
        self.assertEqual(self.ids(explore(self.db, a, direction="out")), [b])
        self.assertEqual(self.ids(explore(self.db, a, direction="in")), [c])
        self.assertEqual(self.ids(explore(self.db, a, relations=["influenced_by"])), [c])
        with self.assertRaises(ValueError):
            explore(self.db, a, direction="sideways")

    def test_only_current_generation_is_read(self):
        a, b = self.node("a"), self.node("b")
        self.link(a, b)
        from intelligence.store import generations
        generations.bump_generation(self.db)
        self.assertEqual(explore(self.db, a).hops, ())
        self.assertEqual(self.ids(explore(self.db, a, generation=1)), [b])


class CreditTests(TraversalTestCase):
    def test_inferred_and_uncertain_edges_are_not_credits(self):
        a, b, c, d = (self.node(n) for n in "abcd")
        self.link(a, b)
        self.link(a, c, evidence_class="inferred")
        self.link(a, d, match_quality="fuzzy_unconfirmed")
        page = explore(self.db, a)
        self.assertEqual({h.entity_id: h.credit for h in page.hops}, {b: True, c: False, d: False})
        only = explore(self.db, a, credits_only=True)
        self.assertEqual(self.ids(only), [b])

    def test_uncertain_edge_cannot_bridge_to_a_credit(self):
        a, b, c = (self.node(n) for n in "abc")
        self.link(a, b, evidence_class="inferred")
        self.link(b, c)
        page = explore(self.db, a, credits_only=True, limits=Limits(max_depth=3))
        self.assertEqual(page.hops, ())

    def test_library_tag_and_user_confirmed_count_as_credits(self):
        a, b, c = (self.node(n) for n in "abc")
        self.link(a, b, evidence_class="library_tag")
        self.link(a, c, evidence_class="user_confirmed", match_quality="fuzzy_confirmed")
        self.assertTrue(all(h.credit for h in explore(self.db, a).hops))
        self.assertTrue(is_credit(explore(self.db, a).hops[0].evidence[0]))


class LimitTests(TraversalTestCase):
    def hub(self, spokes):
        centre = self.node("hub")
        for i in range(spokes):
            self.link(centre, self.node(f"s{i:02d}"))
        return centre

    def test_row_limit_truncates_and_says_so(self):
        centre = self.hub(10)
        page = explore(self.db, centre, limits=Limits(max_rows=4, page_size=50))
        self.assertEqual(len(page.hops), 4)
        self.assertEqual(page.truncated, "rows")

    def test_time_limit_returns_partial_result(self):
        a, b, c = (self.node(n) for n in "abc")
        self.link(a, b)
        self.link(b, c)
        ticks = iter([0.0, 0.0, 99.0, 99.0, 99.0, 99.0])
        page = explore(self.db, a, limits=Limits(max_depth=3, max_seconds=1.0), clock=lambda: next(ticks))
        self.assertEqual(self.ids(page), [b])
        self.assertEqual(page.truncated, "time")

    def test_cursor_pages_through_everything_without_repeats(self):
        centre = self.hub(7)
        limits = Limits(page_size=3)
        collected, cursor = [], None
        for _ in range(10):
            page = explore(self.db, centre, limits=limits, cursor=cursor)
            collected += self.ids(page)
            cursor = page.next_cursor
            if cursor is None:
                break
        self.assertEqual(len(collected), 7)
        self.assertEqual(len(set(collected)), 7)
        self.assertEqual(collected, sorted(collected))

    def test_bad_cursor_and_limits_are_refused(self):
        a = self.node("a")
        with self.assertRaises(ValueError):
            explore(self.db, a, cursor="not-a-cursor!")
        with self.assertRaises(ValueError):
            Limits(max_rows=0)

    def test_unknown_start_or_isolated_entity_is_empty(self):
        self.assertEqual(explore(self.db, 9999).hops, ())
        self.assertEqual(explore(self.db, self.node("alone")).hops, ())


class PurityTests(TraversalTestCase):
    def test_exploring_writes_nothing(self):
        a, b = self.node("a"), self.node("b")
        self.link(a, b)
        before = self.db.total_changes
        explore(self.db, a)
        self.assertEqual(self.db.total_changes, before)


if __name__ == "__main__":
    unittest.main()
