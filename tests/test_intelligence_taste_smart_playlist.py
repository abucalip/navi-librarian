import unittest

from intelligence.taste.smart_playlist import evaluate, validate_rule_set

NOW = 1_800_000_000.0
DAY = 86400


def song(i, **kw):
    base = {"id": i, "artist": "Björk", "title": f"T{i}", "genre": "Rock", "format": "flac", "year": 2000,
            "plays": 0, "rating": 0, "bitrate": 900, "added_at": NOW - 10 * DAY, "played_at": None}
    base.update(kw)
    return base


def rs(rules, **kw):
    raw = {"name": "x", "match": "all", "rules": rules, "order": "title"}
    raw.update(kw)
    out, errs = validate_rule_set(raw)
    assert out is not None, errs
    return out


def r(field, op, value):
    return {"field": field, "op": op, "value": value}


def ids(ev):
    return list(ev.song_ids)


class ValidationTests(unittest.TestCase):
    def test_valid_defaults(self):
        out, errs = validate_rule_set({"name": " Mix ", "rules": []})
        self.assertEqual(errs, ())
        self.assertEqual((out.name, out.match, out.order, out.limit), ("Mix", "all", "random", None))

    def test_errors_listed_with_paths(self):
        _, errs = validate_rule_set({"name": "", "match": "some", "order": "x", "limit": 5,
                                     "rules": [r("nope", "equals", "a"), r("artist", "at_least", "a"), "z"]})
        self.assertEqual({(e.path, e.reason) for e in errs}, {
            ("name", "bad_name"), ("match", "bad_match"), ("order", "bad_order"), ("limit", "bad_limit"),
            ("rules[0].field", "bad_field"), ("rules[1].op", "bad_op"), ("rules[2]", "not_an_object")})

    def test_limit_bounds_and_bool(self):
        for bad in (24, 251, True, "30"):
            self.assertIsNone(validate_rule_set({"name": "a", "limit": bad})[0])
        for ok in (25, 250, None):
            self.assertIsNotNone(validate_rule_set({"name": "a", "limit": ok})[0])

    def test_non_object(self):
        self.assertEqual(validate_rule_set([])[1][0].reason, "not_an_object")


class EvaluateTests(unittest.TestCase):
    def test_no_rules_matches_all_and_drops_idless(self):
        ev = evaluate(rs([]), [song("b"), song("a"), {"title": "x"}], now=NOW)
        self.assertEqual(ids(ev), ["a", "b"])

    def test_text_ops_fold_case_and_diacritics(self):
        songs = [song("a"), song("b", artist="Other")]
        self.assertEqual(ids(evaluate(rs([r("artist", "contains", "BJORK")]), songs, now=NOW)), ["a"])
        self.assertEqual(ids(evaluate(rs([r("artist", "equals", "björk")]), songs, now=NOW)), ["a"])
        self.assertEqual(ids(evaluate(rs([r("artist", "equals", "bjork")]), songs, now=NOW)), [])
        self.assertEqual(ids(evaluate(rs([r("artist", "not_contains", "bjork")]), songs, now=NOW)), ["b"])

    def test_unfinished_rules_match_everything_and_are_reported(self):
        ev = evaluate(rs([r("genre", "contains", "  "), r("plays", "at_least", "many")]), [song("a")], now=NOW)
        self.assertEqual((ids(ev), ev.unfinished, ev.missing_data), (["a"], (0, 1), ()))

    def test_numeric_unknown_never_matches(self):
        songs = [song("a", year=0), song("b", year=1999), song("c", bitrate=0), song("d", added_at=None)]
        self.assertEqual(ids(evaluate(rs([r("year", "at_most", "2000")]), songs, now=NOW)), ["b", "c", "d"])
        self.assertEqual(ids(evaluate(rs([r("bitrate", "at_least", "1")]), songs, now=NOW)), ["a", "b", "d"])
        self.assertEqual(ids(evaluate(rs([r("added_days_ago", "at_most", "99")]), songs, now=NOW)), ["a", "b", "c"])

    def test_plays_and_rating_default_to_zero(self):
        songs = [song("a", plays=None), song("b", plays=3, rating=5)]
        self.assertEqual(ids(evaluate(rs([r("plays", "equals", "0")]), songs, now=NOW)), ["a"])
        self.assertEqual(ids(evaluate(rs([r("rating", "at_least", "4")]), songs, now=NOW)), ["b"])

    def test_never_played_matches_only_at_least(self):
        songs = [song("a"), song("b", played_at=NOW - 100 * DAY), song("c", played_at=NOW - 5 * DAY)]
        self.assertEqual(ids(evaluate(rs([r("played_days_ago", "at_least", "90")]), songs, now=NOW)), ["a", "b"])
        self.assertEqual(ids(evaluate(rs([r("played_days_ago", "at_most", "90")]), songs, now=NOW)), ["c"])

    def test_days_floor_and_clamp_future(self):
        s = [song("a", added_at=NOW + 5 * DAY), song("b", added_at=NOW - 2.9 * DAY)]
        self.assertEqual(ids(evaluate(rs([r("added_days_ago", "equals", "0")]), s, now=NOW)), ["a"])
        self.assertEqual(ids(evaluate(rs([r("added_days_ago", "equals", "2")]), s, now=NOW)), ["b"])

    def test_match_any(self):
        songs = [song("a", genre="Jazz"), song("b", genre="Rock", plays=9), song("c")]
        out = evaluate(rs([r("genre", "equals", "jazz"), r("plays", "at_least", "5")], match="any"), songs, now=NOW)
        self.assertEqual(ids(out), ["a", "b"])

    def test_orders_with_id_tiebreak(self):
        songs = [song("c", plays=1, rating=2, added_at=100), song("a", plays=1, rating=2, added_at=100),
                 song("b", plays=5, rating=4, added_at=None)]
        for order, want in (("most_played", ["b", "a", "c"]), ("least_played", ["a", "c", "b"]),
                            ("highest_rated", ["b", "a", "c"]), ("newest_added", ["a", "c", "b"]),
                            ("title", ["a", "b", "c"])):
            self.assertEqual(ids(evaluate(rs([], order=order), songs, now=NOW)), want, order)

    def test_random_is_seeded_and_input_order_independent(self):
        songs = [song(str(i)) for i in range(30)]
        a = evaluate(rs([], order="random"), songs, now=NOW, seed=7)
        b = evaluate(rs([], order="random"), list(reversed(songs)), now=NOW, seed=7)
        c = evaluate(rs([], order="random"), songs, now=NOW, seed=8)
        self.assertEqual(a, b)
        self.assertNotEqual(ids(a), ids(c))

    def test_limit_keeps_matched_count(self):
        songs = [song(f"{i:03d}") for i in range(60)]
        ev = evaluate(rs([], limit=25), songs, now=NOW)
        self.assertEqual((len(ev.song_ids), ev.matched), (25, 60))

    def test_duplicate_ids_collapse(self):
        self.assertEqual(ids(evaluate(rs([]), [song("a"), song("a")], now=NOW)), ["a"])

    def test_insight_rules(self):
        songs = [song("a"), song("b"), song("c")]
        ins = {"obscurity_band": {"a": "Deep", "b": "Mainstream"}, "lens_members": {"deep_cuts": {"a", "c"}}}
        self.assertEqual(ids(evaluate(rs([r("obscurity_band", "equals", "deep")]), songs, now=NOW, insights=ins)), ["a"])
        self.assertEqual(ids(evaluate(rs([r("obscurity_band", "not_equals", "deep")]), songs, now=NOW, insights=ins)), ["b", "c"])
        self.assertEqual(ids(evaluate(rs([r("in_lens", "equals", "deep_cuts")]), songs, now=NOW, insights=ins)), ["a", "c"])
        self.assertEqual(ids(evaluate(rs([r("in_lens", "not_equals", "deep_cuts")]), songs, now=NOW, insights=ins)), ["b"])

    def test_missing_insight_is_unfinished_not_error(self):
        songs = [song("a")]
        ev = evaluate(rs([r("obscurity_band", "equals", "deep"), r("in_lens", "equals", "x")]), songs, now=NOW)
        self.assertEqual((ids(ev), ev.unfinished, ev.missing_data), (["a"], (0, 1), ("lens_members", "obscurity_band")))


if __name__ == "__main__":
    unittest.main()
