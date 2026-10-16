"""Direct-import regressions for the app authentication configuration policy."""
import unittest

from app.security.auth_configuration import auth_is_configured


class AuthConfigurationTests(unittest.TestCase):
    def test_requires_username_salt_and_password_hash(self):
        complete = {
            "app_auth_username": "owner",
            "app_auth_salt": "salt",
            "app_auth_hash": "hash",
        }
        self.assertTrue(auth_is_configured(complete))
        for missing in complete:
            incomplete = dict(complete)
            incomplete[missing] = ""
            self.assertFalse(auth_is_configured(incomplete))

    def test_missing_or_empty_settings_are_unconfigured(self):
        self.assertFalse(auth_is_configured({}))
        self.assertFalse(auth_is_configured({
            "app_auth_username": "owner",
            "app_auth_salt": None,
            "app_auth_hash": "hash",
        }))

    def test_truthy_legacy_values_keep_existing_behavior(self):
        self.assertTrue(auth_is_configured({
            "app_auth_username": "owner",
            "app_auth_salt": "salt",
            "app_auth_hash": "hash",
            "unrelated": False,
        }))


if __name__ == "__main__":
    unittest.main()
