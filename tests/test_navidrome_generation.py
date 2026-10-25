import json
import unittest
from pathlib import Path

from settings import service


class NavidromeGenerationTests(unittest.TestCase):
    def setUp(self):
        self.state = {
            "navidrome_url": "http://navidrome:4533",
            "navidrome_user": "owner",
            "navidrome_password": "secret-one",
        }
        self.music_dir = Path("/music")

    def read(self):
        return dict(self.state)

    def write(self, values):
        self.state.update(values)

    def save(self, url="http://navidrome:4533", user="owner", password=""):
        return json.loads(service.set_navidrome_settings(
            self.read, self.write, lambda: self.music_dir, lambda _path: None,
            url, user, password,
        ))

    def test_generation_starts_at_zero_and_is_not_a_credential(self):
        self.assertEqual(service.navidrome_generation(self.read), 0)

    def test_changing_url_user_or_password_bumps_the_generation(self):
        self.save(url="http://other:4533")
        self.assertEqual(service.navidrome_generation(self.read), 1)
        self.save(url="http://other:4533", user="someone")
        self.assertEqual(service.navidrome_generation(self.read), 2)
        self.save(url="http://other:4533", user="someone", password="secret-two")
        self.assertEqual(service.navidrome_generation(self.read), 3)

    def test_saving_identical_settings_keeps_the_generation(self):
        self.save()
        self.assertEqual(service.navidrome_generation(self.read), 0)

    def test_blank_password_preserves_the_secret_without_a_bump(self):
        result = self.save(password="")
        self.assertTrue(result["ok"])
        self.assertEqual(service.navidrome_generation(self.read), 0)
        self.assertEqual(self.state["navidrome_password"], "secret-one")

    def test_generation_is_never_returned_with_the_password(self):
        self.save(password="secret-two")
        self.assertNotIn("secret-two", json.dumps(self.save(password="")))


if __name__ == "__main__":
    unittest.main()
