import unittest

from fastapi import HTTPException

from app.api import dashboard


class Librarian:
    def __init__(self, fail=False):
        self.fail = fail

    def api_call(self, name):
        if self.fail:
            raise RuntimeError("down")
        return {"status": "ok"}


class HealthTests(unittest.TestCase):
    def test_answers_version_and_latency_with_the_old_fields(self):
        body = dashboard.health(Librarian())
        self.assertEqual((body["status"], body["service"], body["message"]), ("ok", "Navidrome", "ok"))
        self.assertIsInstance(body["version"], str)
        self.assertTrue(body["version"])
        self.assertIsInstance(body["latency_ms"], int)
        self.assertGreaterEqual(body["latency_ms"], 0)

    def test_an_unreachable_navidrome_is_still_503(self):
        with self.assertRaises(HTTPException) as raised:
            dashboard.health(Librarian(fail=True))
        self.assertEqual(raised.exception.status_code, 503)
