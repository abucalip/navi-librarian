"""Source-contract regressions for the left rail's structure (Redesign Phase 2, rail slice).

These read the shipped template and stylesheet as source and never open a browser, so they do
not replace the rendered checks in docs/UI_BACKLOG_EXECUTION.md. They guard the points most
likely to regress silently: the accessible names of the rail items (the page routing and the
existing tests depend on them), the icon sprite references resolving to real symbols, the
groups staying named, the 232px width and the footer offset that keeps the footer out from
under the rail, and the active-download count staying a numeral.
"""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "app" / "templates" / "index.html"
APP_JS = ROOT / "static" / "app.js"
APP_CSS = ROOT / "static" / "app.css"
ICONS_SVG = ROOT / "static" / "icons.svg"


class RailStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.css = APP_CSS.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.icons = ICONS_SVG.read_text(encoding="utf-8")
        nav_start = cls.html.index('<nav aria-label="Main">')
        nav_end = cls.html.index("</nav>", nav_start)
        cls.rail = cls.html[nav_start:nav_end]

    def test_rail_items_keep_their_accessible_names_and_routes(self):
        expected = {
            "dashboard": "Dashboard",
            "acquisitions": "Acquisitions",
            "recommendations": "Recommendations",
            "newReleases": "New releases",
            "personalDiscoveries": "Personal Discoveries",
            "classics": "Add to your collection",
            "artistDeepDive": "Artist Deep Dives",
        }
        for page, label in expected.items():
            pattern = rf'<button[^>]*data-page="{page}"[^>]*>.*?<span>{re.escape(label)}</span>'
            self.assertRegex(self.rail, pattern, msg=page)

    def test_only_dashboard_is_marked_active_in_shipped_markup(self):
        self.assertEqual(self.rail.count('class="active"'), 1)
        self.assertRegex(self.rail, r'<button class="active" data-page="dashboard">')

    def test_rail_has_two_named_groups(self):
        groups = re.findall(r'<div class="nav-group" role="group" aria-labelledby="(\w+)">', self.rail)
        self.assertEqual(groups, ["navGroupCollection", "navGroupDiscover"])
        for group_id in groups:
            self.assertRegex(self.rail, rf'<p id="{group_id}" class="nav-group-label">')

    def test_every_rail_icon_names_a_symbol_that_exists(self):
        refs = re.findall(r'<use href="/static/icons\.svg#([\w-]+)">', self.rail)
        self.assertEqual(len(refs), 7)
        for name in refs:
            self.assertIn(f'<symbol id="{name}"', self.icons, msg=name)

    def test_rail_icons_are_decorative(self):
        icons = re.findall(r'<svg class="icon"[^>]*>', self.rail)
        self.assertEqual(len(icons), 7)
        for tag in icons:
            self.assertIn('aria-hidden="true"', tag)
            self.assertIn('focusable="false"', tag)

    def test_rail_width_is_a_single_token(self):
        self.assertIn("--rail-w: 232px;", self.css)
        self.assertRegex(self.css, r"nav \{\s*position: fixed;[^}]*width: var\(--rail-w\);")
        self.assertIn("margin: 112px 34px 0 calc(var(--rail-w) + 34px);", self.css)

    def test_footer_takes_the_rail_offset_because_it_sits_outside_main(self):
        self.assertIn("footer { margin: 36px 34px 0 calc(var(--rail-w) + 34px);", self.css)
        self.assertIn("footer { margin-left: calc(var(--rail-w) + 18px); margin-right: 25px; }", self.css)

    def test_old_mono_eyebrow_heading_is_gone(self):
        self.assertNotIn('content: "YOUR COLLECTION"', self.css)

    def test_active_download_count_is_a_numeral_not_a_pill(self):
        self.assertIn('id="activeDownloadBadge" class="nav-count" hidden', self.rail)
        count_rule = re.search(r"\.nav-count \{([^}]*)\}", self.css)
        self.assertIsNotNone(count_rule)
        self.assertNotIn("background", count_rule.group(1))
        self.assertNotIn("border-radius", count_rule.group(1))

    def test_blob_indicator_locates_the_active_item_inside_groups(self):
        self.assertIn("document.querySelector('.nav-list button.active')", self.js)
        self.assertNotIn(".nav-list > button", self.js)
        self.assertIn(".nav-list button { position: relative; z-index: 1; }", self.css)

    def test_rail_items_meet_the_44px_target_floor(self):
        self.assertRegex(self.css, r"nav button \{[^}]*min-height: 44px;")


if __name__ == "__main__":
    unittest.main()
