"""Focused tests for service settings validation and secret redaction.

Extracts the real configuration functions from navidrome_server.py so these
tests can run without initializing MCP or requiring live service credentials.
"""
import ast
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse

SOURCE = Path(__file__).resolve().parents[1] / "navidrome_server.py"


def load_settings_functions():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    wanted = {
        "_navidrome_config",
        "_listenbrainz_username",
        "discovery_get_navidrome_settings",
        "discovery_set_navidrome_settings",
        "discovery_get_lastfm_settings",
        "discovery_set_listenbrainz_settings",
    }
    selected = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in wanted
    ]
    for node in selected:
        node.decorator_list = []
    found = {node.name for node in selected}
    if found != wanted:
        raise AssertionError(f"Missing settings functions: {sorted(wanted - found)}")

    state = {
        "navidrome_url": "http://navidrome:4533",
        "navidrome_user": "test-user",
        "navidrome_password": "super-secret",
        "lastfm_api_key": "lastfm-secret",
        "listenbrainz_username": "listener",
        "music_library_path": "",
    }
    namespace = {
        "json": json,
        "Path": Path,
        "urlparse": urlparse,
        "MUSIC_DIR": Path("/music"),
        "_discovery_settings_read": lambda: dict(state),
        "_discovery_settings_write": lambda values: state.update(values),
    }
    exec(compile(ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[])),
                 str(SOURCE), "exec"), namespace)
    return namespace, state


class ServiceSettingsTests(unittest.TestCase):
    def setUp(self):
        self.functions, self.state = load_settings_functions()

    def test_navidrome_settings_never_return_password(self):
        result = json.loads(self.functions["discovery_get_navidrome_settings"]())
        self.assertEqual(result["username"], "test-user")
        self.assertTrue(result["password_configured"])
        self.assertNotIn("password", result)
        self.assertNotIn("super-secret", json.dumps(result))

    def test_navidrome_config_requires_valid_url_and_credentials(self):
        self.assertEqual(
            self.functions["_navidrome_config"](),
            ("http://navidrome:4533", "test-user", "super-secret"),
        )
        self.state["navidrome_password"] = ""
        with self.assertRaisesRegex(ValueError, "username and password"):
            self.functions["_navidrome_config"]()
        self.state.update({
            "navidrome_url": "file:///tmp/navidrome",
            "navidrome_password": "super-secret",
        })
        with self.assertRaisesRegex(ValueError, "valid HTTP or HTTPS"):
            self.functions["_navidrome_config"]()

    def test_navidrome_save_preserves_password_and_does_not_return_it(self):
        with tempfile.TemporaryDirectory() as directory:
            result = json.loads(self.functions["discovery_set_navidrome_settings"](
                "http://navidrome:4533", "new-user", "", directory
            ))
        self.assertTrue(result["ok"])
        self.assertEqual(self.state["navidrome_password"], "super-secret")
        self.assertNotIn("super-secret", json.dumps(result))

    def test_lastfm_settings_only_return_configured_flag(self):
        result = json.loads(self.functions["discovery_get_lastfm_settings"]())
        self.assertTrue(result["api_key_configured"])
        self.assertNotIn("lastfm-secret", json.dumps(result))
        self.assertNotIn("api_key", result)

    def test_listenbrainz_username_validation_and_save(self):
        result = json.loads(self.functions["discovery_set_listenbrainz_settings"]("new.listener"))
        self.assertTrue(result["ok"])
        self.assertEqual(self.state["listenbrainz_username"], "new.listener")
        result = json.loads(self.functions["discovery_set_listenbrainz_settings"]("not a username"))
        self.assertFalse(result["ok"])
        self.assertEqual(self.state["listenbrainz_username"], "new.listener")


if __name__ == "__main__":
    unittest.main()
