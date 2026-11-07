"""Sonic extension detection and its use in /api/capabilities (Server V2 Phase 7, slice 3)."""
import unittest

from intelligence.sonic.detect import SonicDetector, sonic_extension_listed


class Clock:
    now = 0.0

    def __call__(self):
        return self.now


class ListedTests(unittest.TestCase):
    def test_listed_and_not(self):
        self.assertTrue(sonic_extension_listed({"openSubsonicExtensions": [{"name": "sonicSimilarity", "versions": [1]}]}))
        self.assertTrue(sonic_extension_listed({"openSubsonicExtensions": {"name": "sonicSimilarity"}}))
        self.assertFalse(sonic_extension_listed({"openSubsonicExtensions": [{"name": "other"}]}))
        self.assertFalse(sonic_extension_listed({}))
        self.assertFalse(sonic_extension_listed(None))


class DetectorTests(unittest.TestCase):
    def test_caches_then_expires(self):
        clock, calls = Clock(), []

        def api(method):
            calls.append(method)
            return {"openSubsonicExtensions": [{"name": "sonicSimilarity"}]}

        d = SonicDetector(ttl=10, clock=clock)
        self.assertTrue(d.available(api))
        self.assertTrue(d.available(api))
        self.assertEqual(calls, ["getOpenSubsonicExtensions"])
        clock.now = 11
        d.available(api)
        self.assertEqual(len(calls), 2)

    def test_failure_is_false_and_cached(self):
        calls = []

        def api(method):
            calls.append(1)
            raise RuntimeError("down")

        d = SonicDetector(ttl=10, clock=Clock())
        self.assertFalse(d.available(api))
        self.assertFalse(d.available(api))
        self.assertEqual(len(calls), 1)


class RouteTests(unittest.TestCase):
    def test_capabilities_reports_sonic(self):
        import tempfile
        from pathlib import Path
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        import app.api.capabilities as caps
        from app.api.dependencies import get_librarian

        with tempfile.TemporaryDirectory() as tmp:
            class Lib:
                DATA_DIR = Path(tmp)
                listed = True

                def api_call(self, method, **p):
                    return {"openSubsonicExtensions": [{"name": "sonicSimilarity"}] if self.listed else []}

                def _listenbrainz_username(self):
                    return ""

            lib = Lib()
            app = FastAPI()
            app.include_router(caps.router)
            app.dependency_overrides[get_librarian] = lambda: lib
            client = TestClient(app)
            caps.SONIC = SonicDetector()
            self.assertTrue(client.get("/api/capabilities").json()["sonic_available"])
            lib.listed = False
            caps.SONIC = SonicDetector()
            self.assertFalse(client.get("/api/capabilities").json()["sonic_available"])


if __name__ == "__main__":
    unittest.main()
