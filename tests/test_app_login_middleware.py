"""Direct-import regression tests for the application authentication gate."""
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.security.app_login_middleware import create_app_login_middleware


class AppLoginMiddlewareTests(unittest.TestCase):
    def make_client(self, *, configured=True, valid_tokens=()):
        app = FastAPI()
        app.middleware("http")(create_app_login_middleware(
            auth_configured=lambda: configured,
            session_username=lambda token: "owner" if token in valid_tokens else None,
            cookie_name="test_session",
        ))

        @app.get("/api/private")
        def private_api():
            return {"ok": True}

        @app.get("/private")
        def private_page():
            return "private"

        @app.get("/login")
        def login():
            return "login"

        @app.get("/api/auth/status")
        def auth_status():
            return {"configured": configured}

        @app.get("/static/app.css")
        def static_asset():
            return "css"

        @app.get("/assets/cassette.png")
        def cassette():
            return "png"

        return TestClient(app)

    def test_configured_app_rejects_unauthenticated_api_requests(self):
        with self.make_client() as client:
            response = client.get("/api/private")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Authentication required."})

    def test_configured_app_redirects_unauthenticated_browser_requests(self):
        with self.make_client() as client:
            response = client.get("/private", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/login")

    def test_valid_session_allows_protected_routes(self):
        with self.make_client(valid_tokens={"valid"}) as client:
            response = client.get("/api/private", cookies={"test_session": "valid"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})

    def test_public_auth_and_asset_routes_bypass_login_gate(self):
        with self.make_client(configured=True) as client:
            for path in ("/login", "/api/auth/status", "/static/app.css", "/assets/cassette.png"):
                with self.subTest(path=path):
                    response = client.get(path, follow_redirects=False)
                    self.assertEqual(response.status_code, 200)

    def test_unconfigured_app_keeps_api_routes_closed(self):
        with self.make_client(configured=False) as client:
            response = client.get("/api/private")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
