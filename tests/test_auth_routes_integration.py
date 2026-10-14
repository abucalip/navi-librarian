"""HTTP integration contracts for app authentication routes and middleware."""
import hashlib
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import main

PASSWORD = "correct horse battery staple"


class AuthRouteIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.settings = {}
        self.patches = [
            patch.object(main.librarian, "_discovery_settings_read", side_effect=lambda: dict(self.settings)),
            patch.object(main.librarian, "_discovery_settings_write", side_effect=self.write_settings),
            patch.object(main, "_AUTH_SECRET", b"integration-test-signing-secret-32"),
            patch.object(main, "_password_digest", side_effect=lambda password, salt: hashlib.sha256((salt + password).encode()).hexdigest()),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)
        main._LOGIN_ATTEMPTS.clear()
        self.client = TestClient(main.app, follow_redirects=False)
        self.addCleanup(self.client.close)

    def write_settings(self, values):
        self.settings.update(values)

    def setup_account(self, client=None):
        return (client or self.client).post("/api/auth/setup", json={
            "username": "owner", "password": PASSWORD, "password_confirmation": PASSWORD,
        })

    def test_first_run_setup_creates_account_and_signs_in(self):
        self.assertEqual(self.client.get("/api/auth/status").json(), {"setup_required": True})
        response = self.setup_account()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(self.settings["app_auth_username"], "owner")
        self.assertIn("app_auth_salt", self.settings)
        self.assertIn("app_auth_hash", self.settings)
        self.assertIn(main.AUTH_COOKIE_NAME, response.cookies)
        self.assertEqual(self.client.get("/api/auth/status").json(), {"setup_required": False})
        self.assertEqual(self.setup_account().status_code, 409)

    def test_setup_rejects_invalid_username_password_and_confirmation(self):
        cases = [
            ({"username": "ab", "password": PASSWORD, "password_confirmation": PASSWORD}, 400),
            ({"username": "owner", "password": "short", "password_confirmation": "short"}, 400),
            ({"username": "owner", "password": PASSWORD, "password_confirmation": "different password"}, 400),
        ]
        for payload, expected in cases:
            with self.subTest(payload=payload):
                response = self.client.post("/api/auth/setup", json=payload)
                self.assertEqual(response.status_code, expected)
                self.assertEqual(self.settings, {})

    def test_login_success_failure_and_logout_cookie_clearing(self):
        self.setup_account()
        self.client.cookies.clear()
        invalid = self.client.post("/api/auth/login", json={"username": "owner", "password": "wrong password"})
        self.assertEqual(invalid.status_code, 401)
        self.assertNotIn(main.AUTH_COOKIE_NAME, invalid.cookies)
        response = self.client.post("/api/auth/login", json={"username": "owner", "password": PASSWORD})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn(main.AUTH_COOKIE_NAME, response.cookies)
        self.assertEqual(self.client.get("/").status_code, 200)
        logout = self.client.post("/api/auth/logout")
        self.assertEqual(logout.status_code, 200)
        self.assertIn(main.AUTH_COOKIE_NAME, logout.headers.get("set-cookie", ""))
        self.assertIn("Max-Age=0", logout.headers.get("set-cookie", ""))
        self.assertEqual(self.client.get("/api/health").status_code, 401)

    def test_login_rate_limit_is_per_client_and_success_clears_attempts(self):
        self.setup_account()
        self.client.cookies.clear()
        payload = {"username": "owner", "password": "not the password"}
        for _ in range(main._LOGIN_MAX_ATTEMPTS):
            self.assertEqual(self.client.post("/api/auth/login", json=payload).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/login", json=payload).status_code, 429)
        other = TestClient(main.app, client=("198.51.100.9", 12345), follow_redirects=False)
        self.addCleanup(other.close)
        self.assertEqual(other.post("/api/auth/login", json=payload).status_code, 401)
        main._LOGIN_ATTEMPTS.clear()
        self.assertEqual(self.client.post("/api/auth/login", json={"username": "owner", "password": PASSWORD}).status_code, 200)
        self.assertNotIn("testclient", main._LOGIN_ATTEMPTS)

    def test_cookie_policy_http_https_and_expiration_attributes(self):
        response = self.setup_account()
        cookie = response.headers["set-cookie"].lower()
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=strict", cookie)
        self.assertIn("path=/", cookie)
        self.assertIn(f"max-age={main.AUTH_SESSION_SECONDS}", cookie)
        self.assertNotIn("secure", cookie)
        self.client.cookies.clear()
        secure_client = TestClient(main.app, base_url="https://testserver", follow_redirects=False)
        self.addCleanup(secure_client.close)
        secure_response = secure_client.post("/api/auth/login", json={"username": "owner", "password": PASSWORD})
        self.assertEqual(secure_response.status_code, 200)
        self.assertIn("secure", secure_response.headers["set-cookie"].lower())

    def test_session_persists_across_new_client_and_invalid_cookie_is_rejected(self):
        self.setup_account()
        token = self.client.cookies.get(main.AUTH_COOKIE_NAME)
        self.assertTrue(token)
        restarted_client = TestClient(main.app, follow_redirects=False)
        self.addCleanup(restarted_client.close)
        restarted_client.cookies.set(main.AUTH_COOKIE_NAME, token, path="/")
        self.assertEqual(restarted_client.get("/").status_code, 200)
        with patch.object(main.librarian, "api_call", side_effect=RuntimeError("offline")):
            self.assertEqual(restarted_client.get("/api/health").status_code, 503)
        restarted_client.cookies.set(main.AUTH_COOKIE_NAME, token + "tampered", path="/")
        self.assertEqual(restarted_client.get("/api/health").status_code, 401)

    def test_public_paths_and_protected_page_and_api_rules(self):
        self.setup_account()
        self.client.cookies.clear()
        self.assertEqual(self.client.get("/login").status_code, 200)
        self.assertEqual(self.client.get("/api/auth/status").status_code, 200)
        self.assertEqual(self.client.post("/api/auth/logout").status_code, 200)
        self.assertEqual(self.client.get("/").status_code, 303)
        self.assertEqual(self.client.get("/api/health").status_code, 401)
        self.assertEqual(self.client.get("/api/health").json(), {"detail": "Authentication required."})

    def test_unconfigured_installation_closes_non_auth_routes(self):
        self.assertEqual(self.client.get("/").status_code, 303)
        self.assertEqual(self.client.get("/api/health").status_code, 401)
        self.assertEqual(self.client.get("/api/auth/status").status_code, 200)
        self.assertEqual(self.client.get("/login").status_code, 200)


if __name__ == "__main__":
    unittest.main()
