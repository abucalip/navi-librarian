"""Android client contract: recorded fixtures must still describe routes the server serves.

Fixtures live in android/contract-fixtures (docs/ANDROID_CLIENT_CONTRACT.md section 7).
"""
import json
import re
import unittest
from pathlib import Path

from app import main

FIXTURES = Path(__file__).resolve().parent.parent / "android" / "contract-fixtures"
LIBRARIAN = sorted((FIXTURES / "librarian").glob("*.json"))
NAVIDROME = sorted((FIXTURES / "navidrome").glob("*.json"))


def shape(value):
    """Reduce a JSON value to its keys and types so two payloads can be compared."""
    if isinstance(value, dict):
        return {key: shape(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [shape(value[0])] if value else []
    return type(value).__name__


def served(method, path):
    """True when the app's OpenAPI table has a template matching this method and path."""
    for template, operations in main.app.openapi()["paths"].items():
        pattern = "^" + re.sub(r"\\\{[^/]+?\\\}", "[^/]+", re.escape(template)) + "$"
        if method.lower() in operations and re.match(pattern, path):
            return True
    return False


class FixtureFilesTests(unittest.TestCase):
    def test_fixtures_are_present(self):
        self.assertGreaterEqual(len(LIBRARIAN), 40)
        self.assertGreaterEqual(len(NAVIDROME), 8)

    def test_every_fixture_records_its_request_and_response(self):
        for path in LIBRARIAN + NAVIDROME:
            with self.subTest(fixture=path.name):
                doc = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(set(doc), {"request", "response", "captured_at"})
                self.assertIn(doc["request"]["method"], {"GET", "POST"})
                self.assertIsInstance(doc["response"]["status"], int)
                self.assertIn("body", doc["response"])

    def test_no_credentials_or_signed_tokens_are_stored(self):
        for path in LIBRARIAN + NAVIDROME:
            text = path.read_text(encoding="utf-8")
            with self.subTest(fixture=path.name):
                for marker in ('"t":', '"s":', "eyJhbGci", "Set-Cookie"):
                    self.assertNotIn(marker, text)
                self.assertNotRegex(text, r'"password": "(?!<password>")')
                self.assertNotIn("ts.net", text.replace("navidrome.example.ts.net", ""))


class LibrarianRouteTests(unittest.TestCase):
    def test_every_librarian_fixture_is_served_by_a_route(self):
        for path in LIBRARIAN:
            request = json.loads(path.read_text(encoding="utf-8"))["request"]
            with self.subTest(fixture=path.name):
                self.assertTrue(
                    served(request["method"], request["path"].split("?")[0]),
                    f"{request['method']} {request['path']} is no longer served",
                )


class SubsonicEnvelopeTests(unittest.TestCase):
    def test_navidrome_json_fixtures_use_the_subsonic_envelope(self):
        for path in NAVIDROME:
            body = json.loads(path.read_text(encoding="utf-8"))["response"]["body"]
            if "bytes" in body:
                continue
            with self.subTest(fixture=path.name):
                self.assertEqual(body["subsonic-response"]["status"], "ok")


class ShapeHelperTests(unittest.TestCase):
    def test_shape_detects_a_missing_or_retyped_field(self):
        recorded = {"items": [{"id": "a", "count": 1}], "ok": True}
        self.assertEqual(shape(recorded), shape({"ok": False, "items": [{"count": 9, "id": "z"}]}))
        self.assertNotEqual(shape(recorded), shape({"ok": True, "items": [{"id": "a"}]}))
        self.assertNotEqual(shape(recorded), shape({"ok": True, "items": [{"id": "a", "count": "1"}]}))


if __name__ == "__main__":
    unittest.main()
