"""Direct-import regressions for the assembled page routes."""
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.pages import create_pages_router


class PageRoutesTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.icon_path = Path(self.temp_dir.name) / "cassette.png"
        self.icon_path.write_bytes(b"png-fixture")
        app = FastAPI()
        app.include_router(create_pages_router(
            page_html="<!doctype html><title>Page fixture</title>",
            cassette_icon_path=self.icon_path,
        ))
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_home_route_preserves_supplied_html(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "<!doctype html><title>Page fixture</title>")
        self.assertIn("text/html", response.headers["content-type"])

    def test_cassette_route_serves_injected_asset_with_cache_header(self):
        response = self.client.get("/assets/cassette.png")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"png-fixture")
        self.assertEqual(response.headers["content-type"], "image/png")
        self.assertEqual(response.headers["cache-control"], "public, max-age=86400")

    def test_routes_keep_existing_paths_and_hidden_asset_schema(self):
        app = FastAPI()
        router = create_pages_router(page_html="", cassette_icon_path=self.icon_path)
        app.include_router(router)
        visible_routes = {
            (route.path, method)
            for route in router.routes
            for method in getattr(route, "methods", set())
            if route.include_in_schema
        }
        self.assertEqual(visible_routes, {("/", "GET")})


if __name__ == "__main__":
    unittest.main()
