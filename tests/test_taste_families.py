import unittest

from discovery.taste_families import deep_dive_row, family_label


class DeepDiveRowTests(unittest.TestCase):
    def test_server_family_wins_and_is_normalized(self):
        self.assertEqual(
            deep_dive_row({"genre_families": ["bossa_nova_brazilian"]}),
            {"genre_row": "bossa-nova-brazilian", "genre_row_label": "Brazilian / Bossa Nova"},
        )

    def test_falls_back_to_genre_tags(self):
        self.assertEqual(deep_dive_row({"genres": ["Hard Bop", "Swing"]})["genre_row"], "jazz")
        self.assertEqual(deep_dive_row({"genres": ["afrobeat"]})["genre_row_label"], "African Music")

    def test_unknown_goes_to_other(self):
        row = deep_dive_row({"genres": ["classical"]})
        self.assertEqual(row, {"genre_row": "other", "genre_row_label": "Other Discoveries"})
        self.assertEqual(deep_dive_row({}), row)

    def test_unlisted_family_label_is_title_cased(self):
        self.assertEqual(family_label("death-metal"), "Death Metal")


if __name__ == "__main__":
    unittest.main()
