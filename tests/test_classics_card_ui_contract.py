"""Source-contract regressions for the Classics ("Add to your collection") card titles.

Classics titles are clamped to two lines so the four-column grid keeps its rows aligned. The
clamp hides text, so the same change must give the full album name and year on the title's
tooltip, and must not change the title of any other discovery section. These tests read the
shipped assets as source and never open a browser.
"""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "static" / "app.js"
APP_CSS = ROOT / "static" / "app.css"
INDEX_HTML = ROOT / "app" / "templates" / "index.html"


class ClassicsCardTitleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = APP_CSS.read_text(encoding="utf-8")
        cls.html = INDEX_HTML.read_text(encoding="utf-8")

    def test_classics_title_clamp_is_scoped_to_classics_cards(self):
        rule = re.search(r"#classicsCards \.card h3 \{([^}]*)\}", self.css)
        self.assertIsNotNone(rule, "clamp rule must target #classicsCards .card h3")
        body = rule.group(1)
        self.assertIn("-webkit-line-clamp: 2", body)
        self.assertIn("overflow: hidden", body)

    def test_no_other_section_gets_the_title_clamp(self):
        # Narrow update (ranked rows, DESIGN_SYSTEM.md 9.4): Discover music rows also clamp their
        # titles to two lines. The classics clamp stays the only clamp on a .card; no other
        # section may add one.
        self.assertEqual(len(re.findall(r"-webkit-line-clamp", self.css)), 2)
        self.assertIn(".ranked-row h3 {", self.css)

    def test_classics_title_carries_full_name_and_year_as_tooltip(self):
        self.assertIn("if (name === 'classics') title.title", self.js)
        self.assertIn("`${album} (${year})`", self.js)

    def test_tooltip_is_set_only_for_classics(self):
        # The title tooltip line must be guarded so other sections keep their existing titles.
        tooltip_lines = [line for line in self.js.splitlines() if "title.title = " in line]
        self.assertEqual(len(tooltip_lines), 1, tooltip_lines)
        self.assertIn("name === 'classics'", tooltip_lines[0])

    def test_classics_container_still_uses_the_four_column_grid(self):
        self.assertIn('<div id="classicsCards" class="cards"></div>', self.html)

    def test_loader_still_renders_classics_through_the_shared_path(self):
        self.assertIn("classics: ['classicsCards','classicsStatus']", self.js)


if __name__ == "__main__":
    unittest.main()
