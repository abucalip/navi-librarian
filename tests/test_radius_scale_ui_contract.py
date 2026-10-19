"""Regression contract for the radius scale (DESIGN_SYSTEM.md sections 7 and 16.2 row 8).

Radii are 2px chips and artwork, 4px controls, 6px panels and modal, plus the pill (999px)
and circle (50%) that section 9.2 keeps for Get. A 3px literal is off the scale. These tests
read the stylesheet only; they do not render the page.
"""
import re
import unittest
from pathlib import Path


APP_CSS = Path(__file__).resolve().parents[1] / "static" / "app.css"


def rule_bodies(css, selector):
    pattern = r"(?m)^" + re.escape(selector) + r"\s*\{([^}]*)\}"
    return [match.group(1) for match in re.finditer(pattern, css)]


class RadiusScaleUIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = APP_CSS.read_text(encoding="utf-8")

    def test_stylesheet_has_no_three_pixel_radius(self):
        self.assertIsNone(re.search(r"border-radius:[^;}]*\b3px\b", self.css))

    def test_rail_items_and_indicator_use_the_chip_radius(self):
        self.assertTrue(any("border-radius: var(--radius-chip);" in body for body in rule_bodies(self.css, "nav button")))
        self.assertIn("border-radius: 0 var(--radius-chip) var(--radius-chip) 0;", rule_bodies(self.css, ".nav-indicator")[0])

    def test_header_menu_items_use_the_chip_radius(self):
        self.assertIn("border-radius: var(--radius-chip);", rule_bodies(self.css, ".header-menu-panel button")[0])

    def test_get_pill_and_circle_radii_are_kept(self):
        self.assertIn("border-radius: 999px;", self.css)
        self.assertIn("border-radius: 50%;", self.css)


if __name__ == "__main__":
    unittest.main()
