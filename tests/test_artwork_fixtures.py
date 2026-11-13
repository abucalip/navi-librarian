"""Artwork index fixtures keep the contract the route promises (docs/artwork.md, "Contract fixtures").

The files in android/contract-fixtures/librarian/artwork_index*.json are written by
scripts/write_artwork_fixtures.py through the real route with canned provider answers. These tests read
them, and rebuild them to catch drift; they make no network calls.
"""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "android" / "contract-fixtures" / "librarian"
SLOTS = {"Front", "Back", "Spine", "Obi", "Medium", "Tray", "Sticker", "Poster"}
IMAGE_KEYS = {"image_id", "release", "releases", "edition", "types", "comment", "approved", "width", "height", "format"}
TOP_KEYS = {"status", "rgid", "truncated", "truncated_reason", "releases", "best_front", "slots", "booklet", "booklets", "images"}


def body(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))["response"]["body"]


def writer():
    spec = importlib.util.spec_from_file_location("write_artwork_fixtures", ROOT / "scripts" / "write_artwork_fixtures.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ArtworkFixtures(unittest.TestCase):
    def test_files_match_what_the_route_returns_now(self):
        for name, doc in writer().all_fixtures().items():
            with self.subTest(fixture=name):
                self.assertEqual(json.loads((FIXTURES / name).read_text(encoding="utf-8")), doc)

    def test_the_four_statuses_and_not_loaded(self):
        self.assertEqual(body("artwork_index.json")["status"], "ok")
        self.assertEqual(body("artwork_index_empty.json")["status"], "empty")
        self.assertEqual(body("artwork_index_unavailable.json")["status"], "unavailable")
        self.assertEqual(body("artwork_index_not_loaded.json")["status"], "not_loaded")
        self.assertEqual(body("artwork_index_not_loaded.json")["retry_after"], 5)

    def test_ok_has_the_full_shape(self):
        doc = body("artwork_index.json")
        self.assertEqual(set(doc), TOP_KEYS)
        self.assertFalse(doc["truncated"])
        self.assertIsNone(doc["truncated_reason"])
        self.assertTrue(doc["images"])
        for entry in doc["images"]:
            self.assertEqual(set(entry), IMAGE_KEYS)
            self.assertIn(entry["release"], entry["releases"])
            self.assertIsInstance(entry["comment"], str)

    def test_image_ids_are_unique_and_every_reference_resolves(self):
        doc = body("artwork_index.json")
        ids = [e["image_id"] for e in doc["images"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn(doc["best_front"], ids)
        for slot in doc["slots"].values():
            self.assertIn(slot["image_id"], ids)
        self.assertTrue(set(doc["booklet"]["image_ids"]) <= set(ids))

    def test_shared_image_appears_once_with_every_release(self):
        shared = [e for e in body("artwork_index.json")["images"] if len(e["releases"]) > 1]
        self.assertEqual([e["image_id"] for e in shared], [1001])
        self.assertEqual(len(shared[0]["releases"]), 2)

    def test_slots_are_known_types_and_owned_edition_wins(self):
        doc = body("artwork_index.json")
        self.assertTrue(set(doc["slots"]) <= SLOTS)
        self.assertTrue(doc["slots"]["Front"]["from_owned"])
        self.assertFalse(doc["slots"]["Obi"]["from_owned"])       # only another edition has an Obi
        self.assertEqual(doc["slots"]["Front"]["release"], "11111111-1111-4111-8111-111111111111")

    def test_best_front_is_by_rule_not_by_owner_edition(self):
        doc = body("artwork_index.json")
        self.assertEqual(doc["best_front"], 2001)                 # larger approved Front, not the owned 1001
        self.assertEqual(doc["images"][0]["image_id"], 2001)       # served order is the quality order

    def test_booklet_is_one_release_in_caa_order(self):
        booklet = body("artwork_index.json")["booklet"]
        self.assertEqual(booklet["image_ids"], [2002, 2003, 2005])
        self.assertEqual(booklet["edition"], "1999 JP CD")

    def test_empty_and_unavailable_carry_no_images_and_differ(self):
        empty, gone = body("artwork_index_empty.json"), body("artwork_index_unavailable.json")
        self.assertEqual((empty["images"], empty["best_front"], empty["slots"], empty["booklet"]), ([], None, {}, None))
        self.assertEqual(empty["releases"]["empty"], 1)
        self.assertEqual(set(gone), {"status", "rgid"})            # nothing is claimed about the album

    def test_truncated_reports_a_failed_release_and_is_not_empty(self):
        doc = body("artwork_index_truncated.json")
        self.assertEqual((doc["status"], doc["truncated"], doc["truncated_reason"]), ("ok", True, "partial"))
        self.assertEqual((doc["releases"]["failed"], doc["releases"]["empty"]), (1, 0))
        self.assertEqual([e["image_id"] for e in doc["images"]], [1001, 1002])

    def test_format_names_the_original_file_type(self):
        formats = {e["image_id"]: e["format"] for e in body("artwork_index.json")["images"]}
        self.assertEqual(formats[2005], "pdf")
        self.assertEqual({v for k, v in formats.items() if k != 2005}, {"jpg"})
        for fixture in FIXTURES.glob("artwork_index*.json"):
            for e in body(fixture.name).get("images", []):
                self.assertIn(e["format"], {"jpg", "png", "gif", "webp", "pdf"})

    def test_release_cap_truncation_leaves_the_rest_unread(self):
        doc = body("artwork_index_truncated_release_cap.json")
        self.assertEqual((doc["status"], doc["truncated"], doc["truncated_reason"]), ("ok", True, "release_cap"))
        self.assertEqual((doc["releases"]["total"], doc["releases"]["fetched"], doc["releases"]["failed"]), (3, 2, 0))

    def test_served_cap_keeps_slot_winners_first(self):
        doc = body("artwork_index_truncated_served_cap.json")
        self.assertEqual((doc["truncated"], doc["truncated_reason"]), (True, "served_cap"))
        self.assertEqual(len(doc["images"]), 3)
        kept = {e["image_id"] for e in doc["images"]}
        self.assertTrue({s["image_id"] for s in doc["slots"].values()} <= kept)
        self.assertIn(doc["best_front"], kept)

    def test_bad_group_id_is_400(self):
        recorded = json.loads((FIXTURES / "artwork_index_error_bad_rgid.json").read_text(encoding="utf-8"))
        self.assertEqual(recorded["response"]["status"], 400)

    def test_no_provider_urls_or_paths_leak(self):
        for path in FIXTURES.glob("artwork_index*.json"):
            text = path.read_text(encoding="utf-8")
            with self.subTest(fixture=path.name):
                for marker in ("coverartarchive", "archive.org", "musicbrainz.org", "/Users/", ".jpg", ".pdf", "http"):
                    self.assertNotIn(marker, text)


if __name__ == "__main__":
    unittest.main()
