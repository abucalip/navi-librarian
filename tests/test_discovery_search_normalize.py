import unittest

from discovery.search.normalize import fold, normalize_key, normalize_query


class SearchNormalizeTests(unittest.TestCase):
    def test_fold_casefolds_strips_diacritics_and_collapses_punctuation(self):
        self.assertEqual(fold("Beyoncé"), "beyonce")
        self.assertEqual(fold("  AC/DC!! "), "ac dc")

    def test_leading_the_is_dropped_only_as_a_word(self):
        self.assertEqual(normalize_key("The Beatles"), "beatles")
        self.assertEqual(normalize_key("Theremin Club"), "theremin club")
        self.assertEqual(normalize_key("The"), "the")

    def test_same_artist_with_and_without_the_shares_a_key(self):
        self.assertEqual(normalize_key("The Cure"), normalize_key("cure"))

    def test_query_uses_the_key_rules(self):
        self.assertEqual(normalize_query("  the BEYONCÉ "), "beyonce")
        self.assertEqual(normalize_query("!!!"), "")

    def test_non_latin_names_keep_their_letters(self):
        self.assertEqual(normalize_key("坂本龍一"), "坂本龍一")


if __name__ == "__main__":
    unittest.main()
