"""Direct-import tests for the lazy auth settings reader."""
import unittest
from unittest.mock import Mock

from app.security.auth_settings import AuthSettingsReader


class AuthSettingsReaderTests(unittest.TestCase):
    def test_reader_is_lazy_and_returns_current_settings(self):
        getter = Mock(side_effect=[{"app_auth_username": "first"}, {"app_auth_username": "second"}])
        reader = AuthSettingsReader(settings_getter=getter)

        getter.assert_not_called()
        first = reader.get()
        second = reader.get()

        self.assertEqual(first["app_auth_username"], "first")
        self.assertEqual(second["app_auth_username"], "second")
        self.assertEqual(getter.call_count, 2)

    def test_reader_propagates_owner_errors(self):
        getter = Mock(side_effect=RuntimeError("settings unavailable"))
        reader = AuthSettingsReader(settings_getter=getter)
        with self.assertRaisesRegex(RuntimeError, "settings unavailable"):
            reader.get()


if __name__ == "__main__":
    unittest.main()
