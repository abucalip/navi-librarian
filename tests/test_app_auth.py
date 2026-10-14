"""Regression tests for isolated authentication security primitives."""
import os
import tempfile
import unittest
from pathlib import Path

from app.security import auth


class AppAuthenticationTests(unittest.TestCase):
    def test_username_and_password_policy(self):
        for username in ("abc", "music.owner", "user-name_2"):
            self.assertTrue(auth.valid_auth_username(username))
        for username in ("ab", "bad name", "ééé", "x" * 65, ""):
            self.assertFalse(auth.valid_auth_username(username))
        self.assertTrue(auth.valid_auth_password("a sufficiently long password"))
        for password in ("short", "x" * 1025, None):
            self.assertFalse(auth.valid_auth_password(password))

    def test_password_digest_uses_salt_and_is_deterministic(self):
        salt = "a1" * 16
        one = auth.password_digest("correct horse battery staple", salt, iterations=1000)
        self.assertEqual(one, auth.password_digest(
            "correct horse battery staple", salt, iterations=1000
        ))
        self.assertNotEqual(one, auth.password_digest(
            "different password", salt, iterations=1000
        ))
        self.assertNotEqual(one, auth.password_digest(
            "correct horse battery staple", "b2" * 16, iterations=1000
        ))

    def test_session_is_signed_and_expires(self):
        secret = b"test signing secret with enough entropy"
        settings = lambda: {"app_auth_username": "test-user"}
        now = 1_800_000_000
        token = auth.make_session_token("test-user", secret, now=now, session_seconds=43200)
        self.assertEqual(auth.session_username(token, secret, settings, now=now + 60), "test-user")
        self.assertIsNone(auth.session_username(token, secret, settings, now=now + 43200))
        self.assertIsNone(auth.session_username(token + "tampered", secret, settings, now=now + 60))
        self.assertIsNone(auth.session_username("", secret, settings, now=now + 60))

    def test_session_for_different_username_is_rejected(self):
        secret = b"test signing secret with enough entropy"
        settings = lambda: {"app_auth_username": "test-user"}
        token = auth.make_session_token("someone-else", secret, now=1_800_000_000)
        self.assertIsNone(auth.session_username(token, secret, settings, now=1_800_000_010))

    def test_signing_secret_is_persistent_and_private(self):
        with tempfile.TemporaryDirectory() as directory:
            first = auth.load_auth_secret(directory)
            path = Path(directory) / "app_auth.key"
            self.assertEqual(len(first), 32)
            self.assertEqual(auth.load_auth_secret(directory), first)
            self.assertTrue(path.exists())
            if os.name == "posix":
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_invalid_existing_signing_secret_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "app_auth.key"
            path.write_bytes(b"short")
            with self.assertRaisesRegex(RuntimeError, "missing or invalid"):
                auth.load_auth_secret(directory)


if __name__ == "__main__":
    unittest.main()
