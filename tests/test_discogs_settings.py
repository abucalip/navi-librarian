"""Direct-import tests for Discogs token settings (contract sections 3.5 and 5.2)."""
import json
import unittest

from settings.service import (
    bump_discogs_generation_for_environment,
    discogs_generation,
    get_discogs_settings,
    set_discogs_settings,
    test_discogs_connection,
)

SECRET = "tok_secret-123"


class DiscogsSettingsTests(unittest.TestCase):
    def setUp(self):
        self.state = {}
        self.env = {}

    def read(self):
        return dict(self.state)

    def write(self, values):
        self.state.update(values)

    def save(self, token):
        return json.loads(set_discogs_settings(self.read, self.write, self.env, token))

    def get(self):
        return json.loads(get_discogs_settings(self.read, self.env))

    def test_default_is_not_configured(self):
        self.assertEqual(self.get(), {"token_configured": False, "source": "none"})
        self.assertEqual(discogs_generation(self.read), 0)

    def test_responses_never_contain_the_token(self):
        result = self.save(SECRET)
        self.assertEqual(self.get(), {"token_configured": True, "source": "settings"})
        self.assertNotIn(SECRET, json.dumps(result))
        self.assertNotIn(SECRET, json.dumps(self.get()))

    def test_first_token_replacement_and_clear_each_bump_generation(self):
        self.save(SECRET)
        self.assertEqual(discogs_generation(self.read), 1)
        self.save(SECRET)  # unchanged: no bump
        self.assertEqual(discogs_generation(self.read), 1)
        self.save("other-token")
        self.assertEqual(discogs_generation(self.read), 2)
        self.save("")
        self.assertEqual(discogs_generation(self.read), 3)
        self.assertEqual(self.get()["source"], "none")

    def test_stored_setting_beats_environment(self):
        self.env["DISCOGS_TOKEN"] = "env-token"
        self.assertEqual(self.get(), {"token_configured": True, "source": "environment"})
        self.save(SECRET)
        self.assertEqual(self.get()["source"], "settings")

    def test_clear_falls_back_to_environment_with_bump(self):
        self.save(SECRET)
        self.env["DISCOGS_TOKEN"] = "env-token"
        before = discogs_generation(self.read)
        self.save("")
        self.assertEqual(self.get()["source"], "environment")
        self.assertEqual(discogs_generation(self.read), before + 1)

    def test_startup_bumps_once_only_when_environment_token_is_in_use(self):
        self.assertFalse(bump_discogs_generation_for_environment(self.read, self.write, self.env))
        self.env["DISCOGS_TOKEN"] = "env-token"
        self.assertTrue(bump_discogs_generation_for_environment(self.read, self.write, self.env))
        self.assertEqual(discogs_generation(self.read), 1)
        self.save(SECRET)
        before = discogs_generation(self.read)
        self.assertFalse(bump_discogs_generation_for_environment(self.read, self.write, self.env))
        self.assertEqual(discogs_generation(self.read), before)

    def test_invalid_token_is_refused_without_writing(self):
        result = self.save("bad token!")
        self.assertFalse(result["ok"])
        self.assertEqual(self.state, {})
        self.assertFalse(json.loads(set_discogs_settings(self.read, self.write, self.env, 5))["ok"])


class DiscogsConnectionTests(unittest.TestCase):
    class Response:
        def __init__(self, status):
            self.status_code = status

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError("http " + SECRET)

    def run_test(self, token, status=200, boom=False):
        seen = {}

        def get(url, headers, timeout):
            seen["headers"] = headers
            if boom:
                raise RuntimeError(SECRET)
            return self.Response(status)

        return json.loads(test_discogs_connection(token, get, json.dumps)), seen

    def test_no_token(self):
        self.assertFalse(self.run_test("")[0]["ok"])

    def test_token_goes_in_header_and_result_has_no_secret(self):
        result, seen = self.run_test(SECRET)
        self.assertEqual(result, {"ok": True})
        self.assertEqual(seen["headers"]["Authorization"], f"Discogs token={SECRET}")
        for outcome in (self.run_test(SECRET, 401)[0], self.run_test(SECRET, 500)[0], self.run_test(SECRET, boom=True)[0]):
            self.assertFalse(outcome["ok"])
            self.assertNotIn(SECRET, json.dumps(outcome))


if __name__ == "__main__":
    unittest.main()
