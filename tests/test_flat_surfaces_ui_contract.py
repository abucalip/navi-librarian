"""Regression contracts for flat artwork placeholders and token-only card colours.

DESIGN_SYSTEM.md sections 4.2 and 13 allow no gradients, and AGENTS.md allows no colour
value that is not a token. These tests read the stylesheet only; they do not render the page.
"""
import re
import unittest
from pathlib import Path


APP_CSS = Path(__file__).resolve().parents[1] / "static" / "app.css"


def rule_body(css, selector):
    match = re.search(r"(?m)^" + re.escape(selector) + r"\s*\{([^}]*)\}", css)
    if match is None:
        raise AssertionError(f"selector not found: {selector}")
    return match.group(1)


class FlatSurfaceUIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = APP_CSS.read_text(encoding="utf-8")

    def test_stylesheet_has_no_gradients_except_the_artist_photo_scrim(self):
        # The owner asked for the artist name over a large photo (docs/ARTIST_PAGE_REDESIGN_PROPOSAL.md).
        # The one scrim keeps the name legible on a light photo; nothing else may use a gradient except the album page backdrop below.
        scrim = rule_body(self.css, ".artist-stage::after")
        self.assertEqual(scrim.count("linear-gradient"), 1)
        # The owner asked for the album page backdrop to fade from the cover's colour to the page ground (album and artist pages).
        backdrop = rule_body(self.css, ".tint-backdrop::before")
        self.assertEqual(backdrop.count("linear-gradient"), 1)
        self.assertEqual(self.css.count("gradient"), 2)

    def test_artwork_placeholder_is_a_flat_raised_surface(self):
        self.assertIn("background: var(--surface-raised);", rule_body(self.css, ".card-art"))
        self.assertNotIn("rgba(233", self.css)

    def test_card_category_and_action_fills_use_tokens(self):
        self.assertIn("background: var(--surface-hover);", rule_body(self.css, ".card-category"))
        self.assertIn("background: var(--surface-raised);", rule_body(self.css, ".card-actions button"))
        self.assertNotIn("#353124", self.css)
        self.assertNotIn("#2a2c29", self.css)

    def test_card_artwork_keeps_its_edge(self):
        self.assertIn("border-bottom: 1px solid var(--edge);", rule_body(self.css, ".card-art"))
        self.assertIn("border: 1px solid var(--edge);", rule_body(self.css, ".ranked-row .card-art"))


if __name__ == "__main__":
    unittest.main()
