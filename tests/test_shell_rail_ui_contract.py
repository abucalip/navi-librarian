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
        # Reason: the title attribute (icon-only tooltip) was added in slice B.
        self.assertRegex(self.rail, r'<button class="active" data-page="dashboard"[^>]*>')

    def test_rail_has_two_named_groups(self):
        groups = re.findall(r'<div class="nav-group" role="group" aria-labelledby="(\w+)">', self.rail)
        self.assertEqual(groups, ["navGroupCollection", "navGroupDiscover"])
        for group_id in groups:
            self.assertRegex(self.rail, rf'<p id="{group_id}" class="nav-group-label">')

    def test_every_rail_icon_names_a_symbol_that_exists(self):
        refs = re.findall(r'<use href="/static/icons\.svg#([\w-]+)">', self.rail)
        # Nine rail icons: Library joined Collection and shares the library symbol with Add to your collection.
        self.assertEqual(len(refs), 9)
        for name in refs:
            self.assertIn(f'<symbol id="{name}"', self.icons, msg=name)

    def test_rail_icons_are_decorative(self):
        icons = re.findall(r'<svg class="icon"[^>]*>', self.rail)
        # Nine sprite icons plus the inline More disclosure icon on the phone bottom bar
        # (UI_BACKLOG_EXECUTION section 36). The count of sprite references above is unchanged.
        self.assertEqual(len(icons), 10)
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

    def test_indicator_locates_the_active_item_inside_groups(self):
        # Reason for this change (Phase 2 slice B): the goo blob was replaced by a translateY bar.
        self.assertIn("document.querySelector('.nav-list button.active')", self.js)
        self.assertNotIn(".nav-list > button", self.js)
        self.assertIn('<div class="nav-indicator" aria-hidden="true"></div>', self.rail)
        self.assertIn("indicator.style.transform = 'translateY(' + active.offsetTop + 'px)';", self.js)

    def test_goo_filter_and_spring_easing_are_removed(self):
        self.assertNotIn("nav-goo", self.html)
        self.assertNotIn("nav-blob", self.css)
        self.assertNotIn("nav-blob", self.js)
        self.assertNotIn("cubic-bezier(.34,1.56", self.css)
        self.assertNotIn("filter: url(", self.css)

    def test_indicator_moves_with_transform_only_and_honours_reduced_motion(self):
        self.assertRegex(self.css, r"\.nav-indicator \{[^}]*transition: transform var\(--dur\) var\(--ease-out\);")
        self.assertIn(".nav-indicator { transition: none; }", self.css)

    def test_icon_only_rail_between_621_and_900px_keeps_names_hidden_not_removed(self):
        block = re.search(r"@media \(max-width: 900px\) and \(min-width: 621px\) \{(.*?)\n\}", self.css, re.S)
        self.assertIsNotNone(block)
        self.assertIn(":root { --rail-w: 72px; }", block.group(1))
        self.assertIn("nav button > span:not(.nav-count), .nav-group-label { position: absolute; width: 1px; height: 1px;", block.group(1))
        self.assertIn("clip: rect(0, 0, 0, 0);", block.group(1))
        self.assertNotIn("display: none", block.group(1))

    def test_phone_under_620px_uses_a_bottom_tab_bar(self):
        block = re.search(r"@media \(max-width: 620px\) \{\n(.*?)\n\}", self.css, re.S)
        self.assertIsNotNone(block)
        text = block.group(1)
        self.assertIn("nav { inset: auto 0 0 0;", text)
        self.assertIn("padding: 0 4px env(safe-area-inset-bottom, 0px);", text)
        self.assertIn("main { margin: 136px 14px 0;", text)
        self.assertIn(".nav-indicator { display: none; }", text)

    def test_phone_bar_is_slim_and_icon_only_with_names_kept_for_assistive_tech(self):
        block = re.search(r"@media \(max-width: 620px\) \{\n(.*?)\n\}", self.css, re.S)
        self.assertIsNotNone(block)
        text = block.group(1)
        self.assertIn("nav { inset: auto 0 0 0; width: auto; min-height: 56px;", text)
        self.assertRegex(text, r"nav button > span:not\(\.nav-count\) \{ position: absolute; width: 1px; height: 1px;[^}]*clip: rect\(0, 0, 0, 0\);")
        self.assertNotIn("display: none", re.search(r"nav button > span:not\(\.nav-count\) \{[^}]*\}", text).group(0))
        self.assertIn('title="More"', self.rail)

    def test_every_rail_item_has_a_tooltip_title_matching_its_name(self):
        for label in ["Dashboard", "Acquisitions", "Recommendations", "New releases",
                      "Personal Discoveries", "Add to your collection", "Artist Deep Dives"]:
            self.assertIn(f'title="{label}"', self.rail, msg=label)

    def test_rail_items_meet_the_44px_target_floor(self):
        self.assertRegex(self.css, r"nav button \{[^}]*min-height: 44px;")

    def test_phone_bar_keeps_six_destinations_and_a_more_disclosure(self):
        # UI_BACKLOG_EXECUTION section 36: six destinations (Library joined Collection) stay in the phone bar, and the other
        # two open from More. Each overflow destination is in the rail too, for 621px and up.
        # Daily lists took the bar slot New releases held (Discover keeps three bar destinations).
        bar_pages = ["dashboard", "library", "acquisitions", "recommendations", "personalDiscoveries", "lensLists"]
        more_pages = ["newReleases", "classics", "artistDeepDive"]
        for page in bar_pages:
            button = re.search(rf'<button[^>]*data-page="{page}"[^>]*>', self.rail).group(0)
            self.assertNotIn("nav-overflow", button, msg=page)
        for page in more_pages:
            rail_button = re.search(rf'<button[^>]*data-page="{page}"[^>]*>', self.rail).group(0)
            self.assertIn("nav-overflow", rail_button, msg=page)
            self.assertIn(f'data-page="{page}"', self.rail[self.rail.index('id="navMorePanel"'):])
        toggle = re.search(r'<button id="navMoreButton"[^>]*>', self.rail).group(0)
        self.assertIn('aria-expanded="false"', toggle)
        self.assertIn('aria-controls="navMorePanel"', toggle)
        self.assertIn('<span>More</span>', self.rail)

    def test_phone_more_panel_and_overflow_rules_only_apply_under_620px(self):
        block = re.search(r"@media \(max-width: 620px\) \{\n(.*?)\n\}", self.css, re.S)
        self.assertIsNotNone(block)
        self.assertIn("nav .nav-overflow { display: none; }", block.group(1))
        self.assertIn("nav .nav-more-toggle { display: flex; }", block.group(1))
        self.assertIn(".nav-more-toggle, .nav-more-panel { display: none; }", self.css)

    def test_more_disclosure_is_wired_to_the_shared_navigation_path(self):
        self.assertIn("const navMoreButton = $('navMoreButton');", self.js)
        self.assertIn("navMoreButton.setAttribute('aria-expanded', String(open));", self.js)
        self.assertIn("navigateTo(button.dataset.page);", self.js)
        self.assertIn("nav button[data-page], .header-menu button[data-page]", self.js)
        self.assertIn("if (event.key === 'Escape' && !navMorePanel.hidden)", self.js)


if __name__ == "__main__":
    unittest.main()
