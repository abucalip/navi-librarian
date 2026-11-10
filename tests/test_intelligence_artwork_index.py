import json
import unittest

from intelligence.artwork import ReleaseIndex, best_front, build_group_index, parse_release, slots_view, to_response

RG = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
R1, R2, R3 = ("1" * 8 + "-0000-0000-0000-000000000001", "2" * 8 + "-0000-0000-0000-000000000002",
              "3" * 8 + "-0000-0000-0000-000000000003")


def rel(mbid, date="", country="", fmt=None):
    d = {"id": mbid, "date": date, "country": country}
    if fmt:
        d["media"] = [{"format": fmt}]
    return d


def img(i, types, approved=True, comment="", **extra):
    return {"id": i, "types": types, "approved": approved, "comment": comment, **extra}


def ok(*images):
    return ReleaseIndex("ok", tuple(images))


def build(releases, answers, **kw):
    calls = []

    def fetch(mbid):
        calls.append(mbid)
        return answers.get(mbid, ReleaseIndex("empty"))

    return build_group_index(RG, lambda _rg: releases, fetch, **kw), calls


class ParseTests(unittest.TestCase):
    def test_label_parts(self):
        self.assertEqual(parse_release(rel(R1, "1999-03-01", "JP", "CD")).label, "1999 JP CD")
        self.assertEqual(parse_release(rel(R1)).label, "")
        self.assertEqual(parse_release({"id": R1.upper(), "media": [{"format": "CD"}, {"format": "CD"}, {}]}).format, "CD")


class MergeTests(unittest.TestCase):
    def test_same_image_on_two_releases_appears_once_with_both(self):
        idx, _ = build([rel(R1, "1999"), rel(R2, "2005")],
                       {R1: ok(img(1, ["Front"])), R2: ok(img(1, ["Front"]), img(2, ["Back"]))})
        self.assertEqual(sorted(e.image_id for e in idx.images), [1, 2])
        one = next(e for e in idx.images if e.image_id == 1)
        self.assertEqual(one.releases, [R2, R1])  # newest first
        self.assertEqual(one.release, R2)

    def test_owned_release_is_fetched_first_then_newest(self):
        _, calls = build([rel(R1, "1999"), rel(R2, "2005"), rel(R3, "")], {}, owned_release=R1)
        self.assertEqual(calls, [R1, R2, R3])
        _, calls = build([rel(R1, "1999"), rel(R2, "2005"), rel(R3, "")], {})
        self.assertEqual(calls, [R2, R1, R3])

    def test_bad_image_rows_are_skipped_and_text_is_kept_plain(self):
        idx, _ = build([rel(R1)], {R1: ok({"types": ["Front"]}, img(5, ["Front"], comment="<b>x</b>"))})
        self.assertEqual([e.image_id for e in idx.images], [5])
        self.assertEqual(idx.images[0].comment, "<b>x</b>")

    def test_dimensions_only_when_integers(self):
        idx, _ = build([rel(R1)], {R1: ok(img(1, ["Front"], width=500, height=True))})
        self.assertEqual((idx.images[0].width, idx.images[0].height), (500, None))


class StatusTests(unittest.TestCase):
    def test_all_empty_is_empty(self):
        idx, _ = build([rel(R1), rel(R2)], {})
        self.assertEqual((idx.status, idx.truncated, idx.releases_empty), ("empty", False, 2))

    def test_failure_is_unavailable_never_empty(self):
        idx, _ = build([rel(R1)], {R1: ReleaseIndex("unavailable")})
        self.assertEqual((idx.status, idx.releases_failed), ("unavailable", 1))

    def test_group_lookup_failure_is_unavailable(self):
        idx = build_group_index(RG, lambda _r: None, lambda _m: ReleaseIndex("empty"))
        self.assertEqual(idx.status, "unavailable")

    def test_partial_when_some_release_failed_but_images_exist(self):
        idx, _ = build([rel(R1), rel(R2)], {R1: ok(img(1, ["Front"])), R2: ReleaseIndex("unavailable")})
        self.assertEqual((idx.status, idx.truncated_reason), ("ok", "partial"))

    def test_release_cap_indexes_up_to_cap_and_flags(self):
        ids = [f"{n:08d}-0000-0000-0000-000000000000" for n in range(1, 6)]
        idx, calls = build([rel(i, f"20{n:02d}") for n, i in enumerate(ids)], {}, releases_cap=3)
        self.assertEqual(len(calls), 3)
        self.assertEqual((idx.releases_total, idx.truncated_reason), (5, "release_cap"))

    def test_time_bound_keeps_what_was_fetched_and_resumes_from_cache(self):
        ticks = iter([0, 0, 500, 500])
        idx, calls = build([rel(R1, "1999"), rel(R2, "2005")], {R2: ok(img(1, ["Front"]))}, clock=lambda: next(ticks))
        self.assertEqual((idx.truncated_reason, idx.releases_fetched, calls, idx.status), ("time", 1, [R2], "ok"))
        again, calls2 = build([rel(R1, "1999"), rel(R2, "2005")], {}, cached={R2: ok(img(1, ["Front"]))})
        self.assertEqual(calls2, [R1])
        self.assertFalse(again.truncated)

    def test_cached_unavailable_is_refetched(self):
        _, calls = build([rel(R1)], {}, cached={R1: ReleaseIndex("unavailable")})
        self.assertEqual(calls, [R1])


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.idx, _ = build(
            [rel(R1, "1999-01-01", "JP", "CD"), rel(R2, "1985-05-05", "US", "LP")],
            {R1: ok(img(10, ["Front"], width=500, height=500), img(11, ["Back"]), img(12, ["Booklet"]),
                    img(13, ["Booklet"]), img(14, [])),
             R2: ok(img(20, ["Front"], width=1200, height=1200), img(21, ["Spine"]), img(22, ["Booklet"]),
                    img(23, ["Booklet"]), img(24, ["Booklet"]))},
            owned_release=R1)

    def test_best_front_prefers_approved_then_larger(self):
        self.assertEqual(best_front(self.idx.images).image_id, 20)
        next(e for e in self.idx.images if e.image_id == 20).approved = False
        self.assertEqual(best_front(self.idx.images).image_id, 10)

    def test_no_front_means_none(self):
        idx, _ = build([rel(R1)], {R1: ok(img(1, []), img(2, ["Other"]))})
        self.assertIsNone(best_front(idx.images))

    def test_slots_prefer_owned_release_and_label_the_fallback(self):
        view = slots_view(self.idx)["slots"]
        self.assertEqual(view["Front"], {"image_id": 10, "release": R1, "edition": "1999 JP CD", "from_owned": True})
        self.assertEqual(view["Spine"]["image_id"], 21)
        self.assertEqual((view["Spine"]["from_owned"], view["Spine"]["edition"]), (False, "1985 US LP"))
        self.assertNotIn("Obi", view)

    def test_untyped_images_are_in_no_slot(self):
        self.assertNotIn(14, {s["image_id"] for s in slots_view(self.idx)["slots"].values()})

    def test_booklet_is_one_release_with_most_pages_in_caa_order(self):
        b = slots_view(self.idx)["booklet"]
        self.assertEqual((b["release"], b["image_ids"]), (R2, [22, 23, 24]))

    def test_booklet_tie_goes_to_owned(self):
        idx, _ = build([rel(R1, "2000"), rel(R2, "1990")],
                       {R1: ok(img(1, ["Booklet"])), R2: ok(img(2, ["Booklet"]))}, owned_release=R1)
        self.assertEqual(slots_view(idx)["booklet"]["release"], R1)


class CapTests(unittest.TestCase):
    def many(self, n):
        extra = [img(1000 + i, ["Other"], approved=False) for i in range(n)]
        return build([rel(R1, "2000")], {R1: ok(img(1, ["Front"], approved=False), img(2, ["Back"], approved=False),
                                                 img(3, ["Booklet"], approved=False), *extra)})[0]

    def test_served_cap_keeps_slot_winners_and_booklet_and_flags(self):
        out = to_response(self.many(20), served_cap=5)
        self.assertEqual((out["status"], out["truncated"], out["truncated_reason"]), ("ok", True, "served_cap"))
        self.assertEqual(len(out["images"]), 5)
        self.assertTrue({1, 2, 3} <= {i["image_id"] for i in out["images"]})
        self.assertEqual(out["best_front"], 1)
        self.assertEqual(out["booklet"]["image_ids"], [3])

    def test_stored_cap_trims_and_flags(self):
        idx = build([rel(R1, "2000")], {R1: ok(*(img(i, ["Other"]) for i in range(1, 12)))}, stored_cap=4)[0]
        self.assertEqual((len(idx.images), idx.truncated_reason), (4, "stored_cap"))

    def test_under_caps_is_not_truncated_and_json_safe(self):
        out = to_response(self.many(3))
        self.assertFalse(out["truncated"])
        json.dumps(out)

    def test_empty_and_unavailable_responses(self):
        empty = to_response(build([rel(R1)], {})[0])
        self.assertEqual((empty["status"], empty["images"], empty["best_front"], empty["booklet"]), ("empty", [], None, None))
        self.assertEqual(to_response(build([rel(R1)], {R1: ReleaseIndex("unavailable")})[0])["status"], "unavailable")

    def test_best_front_is_independent_of_release_input_order(self):
        answers = {R1: ok(img(1, ["Front"])), R2: ok(img(2, ["Front"]))}
        a = build([rel(R1, "2000"), rel(R2, "2000")], answers)[0]
        b = build([rel(R2, "2000"), rel(R1, "2000")], answers)[0]
        self.assertEqual(to_response(a)["best_front"], to_response(b)["best_front"])


if __name__ == "__main__":
    unittest.main()
