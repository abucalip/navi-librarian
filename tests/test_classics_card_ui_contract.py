"""Source-contract regressions for the Classics ("Add to your collection") titles.

Redesign Phase 3, item 4: Classics results now render as the shared ranked row, so the title clamp
and the title tooltip come from `.ranked-row h3` and `buildRecommendationRow`. The title must still
be clamped to two lines, must still carry its full name on the tooltip, and no other section may
add a clamp. These tests read the shipped assets as source and never open a browser.
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

    def test_classics_titles_clamp_through_the_ranked_row_rule(self):
        # Narrow update (Phase 3 item 4): the classics-only `#classicsCards .card h3` clamp was
        # removed with the card. Its two-line clamp now comes from `.ranked-row h3`.
        self.assertNotIn("#classicsCards .card h3", self.css)
        rule = re.search(r"\.ranked-row h3 \{([^}]*)\}", self.css)
        self.assertIsNotNone(rule, "clamp rule must target .ranked-row h3")
        body = rule.group(1)
        self.assertIn("-webkit-line-clamp: 2", body)
        self.assertIn("overflow: hidden", body)

    def test_no_other_section_gets_the_title_clamp(self):
        # Narrow update (Phase 3 item 4): the classics clamp moved to the shared ranked row, so the
        # stylesheet now has one clamp, on `.ranked-row h3`. No other section may add one.
        self.assertEqual(len(re.findall(r"-webkit-line-clamp", self.css)), 1)
        self.assertIn(".ranked-row h3 {", self.css)

    def test_classics_title_tooltip_comes_from_the_shared_row(self):
        # Narrow update (Phase 3 item 4): the classics-only tooltip line was removed. The shared
        # row sets the full album name on the title's tooltip for every ranked list.
        self.assertIn("title.setAttribute('title', album || 'Untitled album');", self.js)

    def test_no_section_sets_a_title_tooltip_outside_the_shared_row(self):
        # Narrow update (Phase 3 item 4): the single classics guard is gone; no other line may
        # set a title tooltip on a card title.
        tooltip_lines = [line for line in self.js.splitlines() if "title.title = " in line]
        self.assertEqual(tooltip_lines, [])

    def test_classics_results_use_the_ranked_list_container(self):
        # Narrow update (Phase 3 item 4): classics results moved from the four-column `.cards`
        # grid to the shared ranked list.
        self.assertIn('<div id="classicsCards" class="ranked-list"></div>', self.html)
        self.assertNotIn('<div id="classicsCards" class="cards"></div>', self.html)

    def test_loader_still_renders_classics_through_the_shared_path(self):
        self.assertIn("classics: ['classicsCards','classicsStatus']", self.js)


if __name__ == "__main__":
    unittest.main()
