"""Regression tests for app account credentials and signed sessions.

The auth helpers are extracted from app/main.py so tests do not initialize the
Navidrome MCP server or require live service credentials.
"""
import ast
import base64
import hashlib
import hmac
import json
import re
import time
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "app" / "main.py"


def load_auth_helpers():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    wanted = {
        "_valid_auth_username",
        "_valid_auth_password",
        "_password_digest",
        "_make_session_token",
        "_session_username",
    }
    selected = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in wanted
    ]
    for node in selected:
        node.decorator_list = []
    found = {node.name for node in selected}
    if found != wanted:
        raise AssertionError(f"Missing auth helpers: {sorted(wanted - found)}")

    settings = {"app_auth_username": "test-user"}
    namespace = {
        "base64": base64,
        "hashlib": hashlib,
        "hmac": hmac,
        "json": json,
        "re": re,
        "time": time,
        "AUTH_SESSION_SECONDS": 43200,
        "AUTH_PASSWORD_ITERATIONS": 1000,
        "_AUTH_SECRET": b"test signing secret with enough entropy",
        "_auth_settings": lambda: dict(settings),
    }
    exec(compile(ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[])),
                 str(SOURCE), "exec"), namespace)
    return namespace, settings


class AppAuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.auth, self.settings = load_auth_helpers()

    def test_username_and_password_policy(self):
        valid_username = self.auth["_valid_auth_username"]
        valid_password = self.auth["_valid_auth_password"]
        for username in ("abc", "music.owner", "user-name_2"):
            self.assertTrue(valid_username(username))
        for username in ("ab", "bad name", "ééé", "x" * 65, ""):
            self.assertFalse(valid_username(username))
        self.assertTrue(valid_password("a sufficiently long password"))
        for password in ("short", "x" * 1025, None):
            self.assertFalse(valid_password(password))

    def test_password_digest_uses_salt_and_is_deterministic(self):
        digest = self.auth["_password_digest"]
        salt = "a1" * 16
        one = digest("correct horse battery staple", salt, iterations=1000)
        self.assertEqual(one, digest("correct horse battery staple", salt, iterations=1000))
        self.assertNotEqual(one, digest("different password", salt, iterations=1000))
        self.assertNotEqual(one, digest("correct horse battery staple", "b2" * 16, iterations=1000))

    def test_session_is_signed_and_expires(self):
        make = self.auth["_make_session_token"]
        read = self.auth["_session_username"]
        now = 1_800_000_000
        token = make("test-user", now=now)
        self.assertEqual(read(token, now=now + 60), "test-user")
        self.assertIsNone(read(token, now=now + 43200))
        self.assertIsNone(read(token + "tampered", now=now + 60))
        self.assertIsNone(read("", now=now + 60))

    def test_session_for_different_username_is_rejected(self):
        token = self.auth["_make_session_token"]("someone-else", now=1_800_000_000)
        self.assertIsNone(self.auth["_session_username"](token, now=1_800_000_010))


if __name__ == "__main__":
    unittest.main()
