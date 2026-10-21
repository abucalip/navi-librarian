import ast
import unicodedata
import unittest
from pathlib import Path

from discovery import recommendations as discovery_recommendations
from recommendation.music_key import music_key


def _original_music_key(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(c for c in value if not unicodedata.combining(c))
    return "".join(c.casefold() for c in value if c.isalnum())


class MusicKeyTests(unittest.TestCase):
    SAMPLES = [None, "", "  ", 0, "Björk", "Sigur Rós", "AC/DC", "Ænima", "ＡＢＣ１２３",
               "Beyoncé — Lemonade (Deluxe)", "Mötley  Crüe", "東京事変", "ß", "İstanbul", "Ǆ"]

    def test_output_identical_to_previous_implementation(self):
        for value in self.SAMPLES:
            with self.subTest(value=value):
                self.assertEqual(music_key(value), _original_music_key(value))

    def test_discovery_reexport_is_same_function(self):
        self.assertIs(discovery_recommendations.music_key, music_key)

    def test_dependents_import_leaf_not_discovery_core(self):
        root = Path(__file__).resolve().parents[1]
        for rel in ("integrations/lastfm/client.py", "recommendation_feedback.py",
                    "recommendation/profile_comparison.py"):
            with self.subTest(module=rel):
                tree = ast.parse((root / rel).read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module == "discovery.recommendations":
                        self.assertNotIn("music_key", [a.name for a in node.names])

    def test_leaf_is_stdlib_only(self):
        root = Path(__file__).resolve().parents[1]
        tree = ast.parse((root / "recommendation" / "music_key.py").read_text(encoding="utf-8"))
        modules = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        modules |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        self.assertLessEqual(modules, {"__future__", "unicodedata", "typing"})


if __name__ == "__main__":
    unittest.main()
