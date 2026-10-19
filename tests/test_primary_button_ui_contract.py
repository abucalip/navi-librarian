"""Regression contract for the primary button (DESIGN_SYSTEM.md sections 9.1 and 16.5 row 10).

The primary button is one class, `.btn-primary`, built from the accent tokens. It is used on
five actions that were already yellow by element id: Generate recommendations and the four
Save settings buttons, one per settings tab panel. The id-based yellow rules are removed, so
the class is the only primary rule. These tests read the markup and stylesheet only.
"""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_CSS = ROOT / "static" / "app.css"
INDEX = ROOT / "app" / "templates" / "index.html"

PRIMARY_IDS = ("loadRecommendations", "saveNavidrome", "saveSlskd", "saveLastfm", "saveListenbrainz")


class PrimaryButtonUIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = APP_CSS.read_text(encoding="utf-8")
        cls.html = INDEX.read_text(encoding="utf-8")

    def test_each_primary_action_carries_the_primary_class(self):
        for ident in PRIMARY_IDS:
            with self.subTest(ident=ident):
                self.assertRegex(self.html, rf'<button id="{ident}" class="btn-primary"')

    def test_only_the_five_primary_actions_carry_the_class(self):
        self.assertEqual(len(re.findall(r'class="btn-primary"', self.html)), len(PRIMARY_IDS))

    def test_primary_rule_uses_accent_tokens(self):
        base = re.search(r"(?m)^\.btn-primary\s*\{([^}]*)\}", self.css)
        hover = re.search(r"(?m)^\.btn-primary:hover\s*\{([^}]*)\}", self.css)
        self.assertIsNotNone(base)
        self.assertIsNotNone(hover)
        self.assertIn("background: var(--accent);", base.group(1))
        self.assertIn("color: var(--on-accent);", base.group(1))
        self.assertIn("background: var(--accent-hover);", hover.group(1))

    def test_id_based_yellow_rules_are_removed(self):
        for ident in PRIMARY_IDS:
            with self.subTest(ident=ident):
                self.assertNotRegex(self.css, rf"#{ident}\b[^{{]*\{{[^}}]*var\(--accent\)")


if __name__ == "__main__":
    unittest.main()
