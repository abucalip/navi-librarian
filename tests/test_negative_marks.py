"""Short-lived negative marks in the metadata store (efficiency K4, K5)."""
import unittest
from unittest.mock import patch

from app.services import negative_marks


class NegativeMarksTests(unittest.TestCase):
    def setUp(self):
        self.data = {}
        self.read = lambda key, ttl: self.data.get(key)
        self.write = self.data.__setitem__

    def test_a_mark_is_live_until_its_ttl_and_then_not(self):
        now = [1_000.0]
        with patch.object(negative_marks.time, "time", lambda: now[0]):
            negative_marks.mark(self.write, "k")
            self.assertTrue(negative_marks.is_live(self.read, "k", 3600))
            now[0] += 3599
            self.assertTrue(negative_marks.is_live(self.read, "k", 3600))
            now[0] += 2
            self.assertFalse(negative_marks.is_live(self.read, "k", 3600))

    def test_a_miss_or_a_real_answer_is_not_a_mark(self):
        self.assertFalse(negative_marks.is_live(self.read, "k", 3600))
        for value in ("https://music.apple.com/x", {"review": None}, {"negative": False}, {"negative": True, "at": "x"}):
            self.data["k"] = value
            self.assertFalse(negative_marks.is_live(self.read, "k", 3600), value)

    def test_the_stored_mark_is_truthy(self):
        negative_marks.mark(self.write, "k")
        self.assertTrue(self.data["k"])
        self.assertTrue(self.data["k"]["negative"])


if __name__ == "__main__":
    unittest.main()
