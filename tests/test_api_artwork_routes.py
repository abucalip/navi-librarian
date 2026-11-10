import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.artwork as routes
from app.api.dependencies import get_librarian
from app.security.app_login_middleware import create_app_login_middleware
from intelligence.artwork import ArtworkService, ArtworkStore
from intelligence.artwork.index import OK, ReleaseIndex
from tests.test_intelligence_artwork_cache import JPEG, R1, RG, FakeFetchers, image


class FakeLibrarian:
    def __init__(self, data_dir):
        self.DATA_DIR = Path(data_dir)


class ArtworkRoutes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.fetch = FakeFetchers()
        self.service = ArtworkService(ArtworkStore(Path(self.tmp.name)), self.fetch)
        self.addCleanup(self.service._pool.shutdown)
        api = FastAPI()
        api.include_router(routes.router)
        api.dependency_overrides[get_librarian] = lambda: FakeLibrarian(self.tmp.name)
        api.dependency_overrides[routes.get_service] = lambda: self.service
        self.api = api
        self.client = TestClient(api)

    def test_index_validates_ids_then_reports_not_loaded_and_ok(self):
        self.assertEqual(self.client.get("/api/artwork/index", params={"rgid": "nope"}).status_code, 400)
        self.assertEqual(self.client.get("/api/artwork/index", params={"rgid": RG, "release": "x"}).status_code, 400)
        self.assertEqual(self.client.get("/api/artwork/index").status_code, 422)
        first = self.client.get("/api/artwork/index", params={"rgid": RG}).json()
        self.assertEqual((first["status"], first["retry_after"]), ("not_loaded", 5))
        self.service._pool.submit(lambda: None).result(5)
        body = self.client.get("/api/artwork/index", params={"rgid": RG}).json()
        self.assertEqual((body["status"], body["best_front"]), ("ok", 10))

    def test_image_sizes_errors_and_headers(self):
        self.service.build_now(RG)
        ok = self.client.get("/api/artwork/image/10", params={"size": "thumb"})
        self.assertEqual((ok.status_code, ok.content, ok.headers["content-type"]), (200, JPEG, "image/jpeg"))
        self.assertEqual(ok.headers["x-content-type-options"], "nosniff")
        self.assertEqual(self.client.get("/api/artwork/image/10", params={"size": "big"}).status_code, 400)
        self.assertEqual(self.client.get("/api/artwork/image/0").status_code, 400)
        self.assertEqual(self.client.get("/api/artwork/image/abc").status_code, 422)
        self.assertEqual(self.client.get("/api/artwork/image/12345").status_code, 404)
        self.fetch.fetch_image = lambda *a, **k: ("unavailable", b"", "")
        self.assertEqual(self.client.get("/api/artwork/image/11", params={"size": "full"}).status_code, 503)

    def test_pdf_is_served_sandboxed(self):
        pdf = b"%PDF-1.6\n" + b"p" * 50
        self.service.build_now(RG)
        self.fetch.image_answer = ("ok", pdf, "pdf")
        r = self.client.get("/api/artwork/image/10", params={"size": "full"})
        self.assertEqual((r.status_code, r.headers["content-type"]), (200, "application/pdf"))
        self.assertIn("sandbox", r.headers["content-security-policy"])

    def test_both_routes_need_the_session(self):
        self.api.middleware("http")(create_app_login_middleware(
            auth_configured=lambda: True, session_username=lambda token: None, cookie_name="c"))
        client = TestClient(self.api)
        self.assertEqual(client.get("/api/artwork/index", params={"rgid": RG}).status_code, 401)
        self.assertEqual(client.get("/api/artwork/image/10").status_code, 401)
        self.assertEqual(self.fetch.release_calls, 0)


if __name__ == "__main__":
    unittest.main()
