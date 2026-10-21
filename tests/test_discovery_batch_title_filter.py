"""Offline tests for the batch-path title filter (no provider calls)."""
import unittest

from discovery import candidate_supply as supply


class BatchTitleFilterTests(unittest.TestCase):
    def rejection(self, title):
        return supply.batch_title_marker_rejection(title)

    def test_marked_titles_are_rejected_when_enabled(self):
        for title in ("Live at the Garden", "Unplugged", "Greatest Hits",
                      "Tribute to Someone", "Best Of 1990-2000", "The Remixes",
                      "Soundtrack Vol. 2", "Bootleg Sessions"):
            with self.subTest(title=title):
                self.assertEqual(self.rejection(title), "batch_title_marker")

    def test_substrings_inside_words_are_not_rejected(self):
        for title in ("Olive Branch", "Alive and Kicking", "Delivering", "Liverpool Nights"):
            with self.subTest(title=title):
                self.assertIsNone(self.rejection(title))

    def test_ordinary_album_titles_pass(self):
        for title in ("Kind of Blue", "Abbey Road", "Rumours"):
            with self.subTest(title=title):
                self.assertIsNone(self.rejection(title))

    def test_unmarked_live_album_still_passes_known_limitation(self):
        self.assertIsNone(self.rejection("Stadium Nights"))

    def test_empty_and_none_titles_are_safe(self):
        self.assertIsNone(self.rejection(""))
        self.assertIsNone(self.rejection(None))


if __name__ == "__main__":
    unittest.main()
