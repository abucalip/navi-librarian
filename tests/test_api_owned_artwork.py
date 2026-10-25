import unittest
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_librarian
from app.api.owned_artwork import router
from integrations.navidrome import client as navidrome_client


class FakeLibrarian:
    def _navidrome_config(self):
        return "http://navidrome:4533", "owner", "stub-secret"


class OwnedArtworkRouteTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_librarian] = lambda: FakeLibrarian()
        self.client = TestClient(app)

    def test_serves_the_image_with_private_cache_headers(self):
        with mock.patch.object(navidrome_client, "cover_art", return_value=("image/png", b"png-bytes")) as fetch:
            response = self.client.get("/api/owned/artwork/al-1", params={"size": "128"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"png-bytes")
        self.assertEqual(response.headers["content-type"], "image/png")
        self.assertEqual(response.headers["cache-control"], "private, max-age=3600")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        fetch.assert_called_once()
        self.assertEqual(fetch.call_args.args[1:], ("al-1",))
        self.assertEqual(fetch.call_args.kwargs["size"], 128)

    def test_default_size_is_300(self):
        with mock.patch.object(navidrome_client, "cover_art", return_value=("image/jpeg", b"x")) as fetch:
            self.client.get("/api/owned/artwork/al-1")
        self.assertEqual(fetch.call_args.kwargs["size"], 300)

    def test_bad_id_or_size_is_400_and_never_calls_navidrome(self):
        with mock.patch.object(navidrome_client, "cover_art") as fetch:
            self.assertEqual(self.client.get("/api/owned/artwork/bad%20id").status_code, 400)
            self.assertEqual(self.client.get("/api/owned/artwork/al-1", params={"size": "32"}).status_code, 400)
            self.assertEqual(self.client.get("/api/owned/artwork/al-1", params={"size": "big"}).status_code, 400)
        fetch.assert_not_called()

    def test_missing_artwork_is_404(self):
        with mock.patch.object(navidrome_client, "cover_art",
                               side_effect=navidrome_client.CoverArtUnavailable("none")):
            self.assertEqual(self.client.get("/api/owned/artwork/al-1").status_code, 404)

    def test_unconfigured_navidrome_is_503_and_failures_are_502(self):
        with mock.patch.object(navidrome_client, "cover_art", side_effect=ValueError("no url")):
            self.assertEqual(self.client.get("/api/owned/artwork/al-1").status_code, 503)
        with mock.patch.object(navidrome_client, "cover_art", side_effect=RuntimeError("down")):
            response = self.client.get("/api/owned/artwork/al-1")
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("stub-secret", response.text)


if __name__ == "__main__":
    unittest.main()
