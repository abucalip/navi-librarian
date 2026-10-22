import json
import tempfile
import unittest
from pathlib import Path

from discovery import taste_families as tf
from discovery.taste_families import deep_dive_row, family_label

class ShippedDefaultsTests(unittest.TestCase):
    def test_shipped_tables_are_loaded_and_non_empty(self):
        for name in ("CATEGORY_RULES", "RECENT_STYLE_TERMS", "PRIMARY_RECENT_PRIORITY",
                     "FAMILY_LABELS"):
            self.assertTrue(getattr(tf, name), name)

    def test_loader_reads_a_given_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.json"
            path.write_text(json.dumps({"core_families": ["metal"]}), encoding="utf-8")
            self.assertEqual(tf._load(path), {"core_families": ["metal"]})

    def test_shipped_file_is_utf8_with_non_ascii_terms(self):
        data = tf._load()
        self.assertIn("raï", dict(map(tuple, data["category_rules"]))["north-african-middle-eastern"])

    def test_taste_defining_tables_are_gone(self):
        data = tf._load()
        for key in ("core_families", "exploration_families", "regional_artist_families", "adventurous_tags"):
            self.assertNotIn(key, data)
        for name in ("CORE_FAMILIES", "EXPLORATION_FAMILIES", "REGIONAL_ARTIST_FAMILIES", "ADVENTUROUS_TAGS"):
            self.assertFalse(hasattr(tf, name), name)


class DeepDiveRowTests(unittest.TestCase):
    def test_server_family_wins_and_is_normalized(self):
        self.assertEqual(
            deep_dive_row({"genre_families": ["bossa_nova_brazilian"]}),
            {"genre_row": "bossa-nova-brazilian", "genre_row_label": "Brazilian / Bossa Nova"},
        )

    def test_falls_back_to_genre_tags(self):
        self.assertEqual(deep_dive_row({"genres": ["Hard Bop", "Swing"]})["genre_row"], "jazz")
        self.assertEqual(deep_dive_row({"genres": ["afrobeat"]})["genre_row_label"], "African Music")
        self.assertEqual(deep_dive_row({"genres": ["thrash metal"]}),
                         {"genre_row": "metal", "genre_row_label": "Metal"})
        self.assertEqual(deep_dive_row({"genres": ["boom bap", "jazz rap"]})["genre_row"], "hip-hop")

    def test_unknown_goes_to_other(self):
        row = deep_dive_row({"genres": []})
        self.assertEqual(row, {"genre_row": "other", "genre_row_label": "Other Discoveries"})
        self.assertEqual(deep_dive_row({}), row)
        self.assertEqual(deep_dive_row({"genres": ["classical"]})["genre_row"], "classical")

    def test_unlisted_family_label_is_title_cased(self):
        self.assertEqual(family_label("death-metal"), "Death Metal")


if __name__ == "__main__":
    unittest.main()
