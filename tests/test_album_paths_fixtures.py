"""Album paths fixtures keep the contract the builders promise (docs/ALBUM_PATHS_PROPOSAL.md, "Rules").

Recorded through GET /api/knowledge/paths (type=release) and GET /api/sonic/album-neighbours
in android/contract-fixtures/librarian. These tests read the recorded responses only; they do not
call the server or the store.
"""
import json
import unittest
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "android" / "contract-fixtures" / "librarian"

ALBUM_CODES = {
    "album_crew": {"crew_on"},
    "album_guests": {"guest_on"},
    "album_works": {"same_work", "derived_work"},
    "album_room": {"recorded_at"},
    "album_moment": {"same_period_label", "same_period_area", "same_period_credit"},
}
ARTIST_KINDS = {"follow_the_musician", "sideman_to_leader", "label_path", "composition_path", "scene_path"}
LEAKS = ("navidrome_id", "built_from", "generation_id", "presentation_version", "similarity")


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def body(name):
    return load(name)["response"]["body"]


class AlbumPathFixtures(unittest.TestCase):
    def test_ok_fixtures_hold_only_their_kinds_credit_grade_reasons(self):
        for kind, codes in ALBUM_CODES.items():
            with self.subTest(kind=kind):
                doc = body(f"paths_{kind}.json")
                self.assertEqual((doc["kind"], doc["status"]), (kind, "ok"))
                self.assertEqual(doc["start"]["type"], "release")
                self.assertTrue(doc["stops"], "an ok answer has at least one stop")
                for stop in doc["stops"]:
                    self.assertEqual(stop["entity"]["type"], "release")
                    self.assertTrue(stop["entity"]["owned"], "every stop is an owned album")
                    self.assertTrue(stop["reasons"])
                    for reason in stop["reasons"]:
                        self.assertIn(reason["code"], codes)
                        self.assertNotIn(reason["code"], ARTIST_KINDS)
                        if reason["code"] != "same_period_label":
                            self.assertTrue(reason["evidence"], "credit-grade reasons carry evidence")

    @unittest.expectedFailure
    def test_same_period_label_reasons_carry_evidence(self):
        # Known gap: the recorded same_period_label reasons have no evidence rows, while the
        # artist label_path reasons do (same_label, 2 rows). Remove the decorator once the builder fixes it.
        for stop in body("paths_album_moment.json")["stops"]:
            for reason in stop["reasons"]:
                if reason["code"] == "same_period_label":
                    self.assertTrue(reason["evidence"])

    def test_no_stop_is_the_album_itself(self):
        for kind in ALBUM_CODES:
            doc = body(f"paths_{kind}.json")
            start = doc["start"]["mbid"]
            with self.subTest(kind=kind):
                self.assertNotIn(start, [s["entity"]["mbid"] for s in doc["stops"]])

    def test_stops_are_unique_per_album(self):
        for kind in ALBUM_CODES:
            doc = body(f"paths_{kind}.json")
            mbids = [s["entity"]["mbid"] for s in doc["stops"]]
            with self.subTest(kind=kind):
                self.assertEqual(len(mbids), len(set(mbids)))

    def test_empty_fixtures_are_empty_not_padded(self):
        for kind in ALBUM_CODES:
            doc = body(f"paths_{kind}_empty.json")
            with self.subTest(kind=kind):
                self.assertEqual((doc["kind"], doc["status"], doc["stops"]), (kind, "empty", []))

    def test_moment_stops_need_a_stated_link_not_a_date_alone(self):
        for stop in body("paths_album_moment.json")["stops"]:
            codes = {r["code"] for r in stop["reasons"]}
            with self.subTest(stop=stop["entity"]["mbid"]):
                self.assertTrue(codes & set(ALBUM_CODES["album_moment"]))
                self.assertNotEqual(codes, {"same_period_date"})

    def test_public_shape_has_no_internal_fields(self):
        names = [p.name for p in FIXTURES.glob("paths_album_*.json")]
        for name in names:
            text = (FIXTURES / name).read_text(encoding="utf-8")
            for leak in LEAKS:
                if name.startswith("sonic_") and leak == "navidrome_id":
                    continue  # the Sonic route returns Navidrome track ids by design (seeds, matches)
                with self.subTest(fixture=name, leak=leak):
                    self.assertNotIn(f'"{leak}"', text)


class AlbumPathErrorFixtures(unittest.TestCase):
    def test_error_statuses(self):
        expected = {
            "paths_error_album_kind_artist_type.json": 400,
            "paths_error_artist_kind_album_type.json": 400,
            "paths_error_album_unknown_entity.json": 404,
            "sonic_album_neighbours_error_not_found.json": 404,
        }
        for name, status in expected.items():
            with self.subTest(fixture=name):
                response = load(name)["response"]
                self.assertEqual(response["status"], status)
                self.assertIn("detail", response["body"])


class AlbumNeighbourFixtures(unittest.TestCase):
    def test_seed_cap_and_skips_are_reported(self):
        doc = body("sonic_album_neighbours.json")
        self.assertEqual(doc["status"], "ok")
        self.assertLessEqual(len(doc["seeds"]), 8, "the owner's cap is 8 seeds per album")
        self.assertIsInstance(doc["skipped"], list)

    def test_every_neighbour_is_a_count_not_a_similarity(self):
        doc = body("sonic_album_neighbours.json")
        self.assertTrue(doc["stops"])
        for stop in doc["stops"]:
            self.assertTrue(stop["owned"])
            self.assertIn("album_id", stop)
            self.assertNotIn("similarity", str(stop))
            for reason in stop["reasons"]:
                self.assertEqual(reason["code"], "sonic_neighbour")
                self.assertEqual(reason["count"], stop["match_count"])

    def test_empty_neighbours_are_empty(self):
        doc = body("sonic_album_neighbours_empty.json")
        self.assertEqual((doc["status"], doc["stops"]), ("empty", []))


if __name__ == "__main__":
    unittest.main()
