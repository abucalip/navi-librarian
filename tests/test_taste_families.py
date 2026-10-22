import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from discovery import taste_families as tf
from discovery.taste_families import deep_dive_row, family_label

# SHA-256 of the canonical (sorted-key, unescaped) JSON of the tables as they
# were hard-coded before they moved to settings/taste_defaults.json.
ORIGINAL_TABLES_SHA256 = "34936d7bb266e1d2a20b35e9dc123c0dc55fa99239b032d81394f2669dab38d4"


def _canonical_tables():
    return {
        "category_rules": [[f, list(x)] for f, x in tf.CATEGORY_RULES],
        "deep_dive_rules": [[f, list(x)] for f, x in tf.DEEP_DIVE_RULES],
        "recent_style_terms": {k: list(v) for k, v in tf.RECENT_STYLE_TERMS.items()},
        "recent_style_jazz_exact": list(tf.RECENT_STYLE_JAZZ_EXACT),
        "recent_style_jazz_excluded": tf.RECENT_STYLE_JAZZ_EXCLUDED,
        "recent_style_rock_excluded": tf.RECENT_STYLE_ROCK_EXCLUDED,
        "primary_recent_priority": list(tf.PRIMARY_RECENT_PRIORITY),
        "primary_hiphop_terms": list(tf.PRIMARY_HIPHOP_TERMS),
        "primary_specific_jazz_terms": list(tf.PRIMARY_SPECIFIC_JAZZ_TERMS),
        "core_families": sorted(tf.CORE_FAMILIES),
        "exploration_families": sorted(tf.EXPLORATION_FAMILIES),
        "regional_artist_families": tf.REGIONAL_ARTIST_FAMILIES,
        "adventurous_tags": list(tf.ADVENTUROUS_TAGS),
        "family_labels": tf.FAMILY_LABELS,
    }


class ShippedDefaultsTests(unittest.TestCase):
    def test_shipped_file_reproduces_original_tables(self):
        text = json.dumps(_canonical_tables(), ensure_ascii=False, sort_keys=True)
        self.assertEqual(hashlib.sha256(text.encode("utf-8")).hexdigest(), ORIGINAL_TABLES_SHA256)

    def test_loader_reads_a_given_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.json"
            path.write_text(json.dumps({"core_families": ["metal"]}), encoding="utf-8")
            self.assertEqual(tf._load(path), {"core_families": ["metal"]})

    def test_shipped_file_is_utf8_with_non_ascii_terms(self):
        data = tf._load()
        self.assertIn("شابصحراوي", data["regional_artist_families"])
        self.assertIn("raï", dict(map(tuple, data["category_rules"]))["north-african-middle-eastern"])


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
