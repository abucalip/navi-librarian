"""HTTP integration contracts for app authentication routes and middleware."""
import hashlib
import subprocess
import sys
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import main

PASSWORD = "correct horse battery staple"


class FakeLibrarian:
    def __init__(self, settings):
        self.settings = settings
        self.api_error = None

    def _discovery_settings_read(self):
        return dict(self.settings)

    def _discovery_settings_write(self, values):
        self.settings.update(values)

    def api_call(self, method):
        if self.api_error:
            raise self.api_error
        return {"status": "pong"}


class AuthRouteIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.settings = {}
        self.librarian = FakeLibrarian(self.settings)
        self.patches = [
            patch.object(main, "get_librarian", return_value=self.librarian),
            patch.object(main, "_AUTH_SECRET", b"integration-test-signing-secret-32"),
            patch.object(main, "_password_digest", side_effect=lambda password, salt: hashlib.sha256((salt + password).encode()).hexdigest()),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)
        main._LOGIN_ATTEMPTS.clear()
        self.client = TestClient(main.app, follow_redirects=False)
        self.addCleanup(self.client.close)

    def setup_account(self, client=None):
        return (client or self.client).post("/api/auth/setup", json={
            "username": "owner", "password": PASSWORD, "password_confirmation": PASSWORD,
        })

    def test_importing_app_does_not_initialize_legacy_server(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; import app.main; "
                "assert 'navidrome_server' not in sys.modules",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

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
        with patch.object(self.librarian, "api_call", side_effect=RuntimeError("offline")):
            self.assertEqual(restarted_client.get("/api/health").status_code, 503)
        restarted_client.cookies.set(main.AUTH_COOKIE_NAME, token + "tampered", path="/")
        self.assertEqual(restarted_client.get("/api/health").status_code, 401)

    def test_public_paths_and_protected_page_and_api_rules(self):
        self.setup_account()
        self.client.cookies.clear()
        login = self.client.get("/login")
        self.assertEqual(login.status_code, 200)
        self.assertIn('/static/login.css', login.text)
        self.assertIn('/static/login.js', login.text)
        self.assertNotIn('<style>', login.text)
        self.assertNotIn('<script>', login.text)
        self.assertEqual(self.client.get("/static/login.css").status_code, 200)
        self.assertEqual(self.client.get("/static/login.js").status_code, 200)
        self.assertEqual(self.client.get("/assets/cassette.png").status_code, 200)
        self.assertEqual(self.client.get("/api/auth/status").status_code, 200)
        self.assertEqual(self.client.post("/api/auth/logout").status_code, 200)
        self.assertEqual(self.client.get("/").status_code, 303)
        self.assertEqual(self.client.get("/api/health").status_code, 401)
        self.assertEqual(self.client.get("/api/health").json(), {"detail": "Authentication required."})

    def test_unconfigured_installation_closes_non_auth_routes(self):
        self.assertEqual(self.client.get("/").status_code, 303)
        self.assertEqual(self.client.get("/api/health").status_code, 401)
        self.assertEqual(self.client.get("/api/auth/status").status_code, 200)
        login = self.client.get("/login")
        self.assertEqual(login.status_code, 200)
        self.assertEqual(self.client.get("/static/login.css").status_code, 200)
        self.assertEqual(self.client.get("/static/login.js").status_code, 200)
        self.assertEqual(self.client.get("/assets/cassette.png").status_code, 200)
        self.assertEqual(self.client.get("/").status_code, 303)

    def test_main_page_references_external_assets(self):
        self.setup_account()
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn('/static/app.css', response.text)
        self.assertIn('/static/app.js', response.text)
        self.assertNotIn('<style>', response.text)
        self.assertNotIn('<script>', response.text)
        self.assertEqual(self.client.get("/static/app.css").status_code, 200)
        self.assertEqual(self.client.get("/static/app.js").status_code, 200)


    def test_concurrent_login_attempts_cannot_race_past_rate_limit(self):
        self.setup_account()
        main._LOGIN_ATTEMPTS["testclient"] = [
            __import__("time").time()
        ] * (main._LOGIN_MAX_ATTEMPTS - 1)
        barrier = __import__("threading").Barrier(2)

        def blocked_digest(password, salt):
            barrier.wait(timeout=5)
            return hashlib.sha256((salt + password).encode()).hexdigest()

        payload = {"username": "owner", "password": "wrong password"}

        def attempt_login():
            with TestClient(main.app, follow_redirects=False) as client:
                return client.post("/api/auth/login", json=payload).status_code

        with patch.object(main, "_password_digest", side_effect=blocked_digest):
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=2) as executor:
                statuses = list(executor.map(lambda _: attempt_login(), range(2)))

        self.assertEqual(sorted(statuses), [401, 429])


if __name__ == "__main__":
    unittest.main()
