"""Source contracts for the opt-in Listening Room shell (L2)."""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ListeningRoomShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "app/templates/index.html").read_text(encoding="utf-8")
        cls.js = (ROOT / "static/app.js").read_text(encoding="utf-8")
        cls.css = (ROOT / "static/listening-room/shell.css").read_text(encoding="utf-8")
        cls.tokens = (ROOT / "static/listening-room/tokens.css").read_text(encoding="utf-8")

    def test_rail_and_tab_bar_expose_named_navigation_and_routes(self):
        self.assertIn('href="/static/listening-room/shell.css"', self.html)
        for variant, names in (
            ("rail", ["Home", "Discover", "Library", "Saved", "Radio", "Acquisitions", "Blocklist", "Settings"]),
            ("tabbar", ["Home", "Discover", "Library", "Getting"]),
        ):
            nav = self.html.split(f'<nav class="lr-{variant}" aria-label="Main" hidden>', 1)[1].split("</nav>", 1)[0]
            labels = re.findall(r'class="lr-nav" href="#(\w+)" data-lr-page="\1" aria-label="([^"]+)"', nav)
            self.assertEqual([label for _, label in labels], names)
            for page, _ in labels:
                self.assertIn(f'<section id="{page}"', self.html)
        self.assertIn("link.setAttribute('aria-current', 'page')", self.js)
        self.assertIn("lrMore.setAttribute('aria-current', 'page')", self.js)

    def test_phone_navigation_precedes_search_in_keyboard_order(self):
        skip_link = self.html.index('class="skip-link"')
        phone_nav = self.html.index('<nav class="lr-tabbar"')
        search = self.html.index('<form id="globalSearch"')
        self.assertLess(skip_link, phone_nav)
        self.assertLess(phone_nav, search)

    def test_more_is_a_named_modal_with_the_four_secondary_destinations(self):
        self.assertIn('aria-haspopup="dialog" aria-expanded="false" aria-controls="lrMoreSheet"', self.html)
        sheet = self.html.split('<dialog class="lr-sheet" id="lrMoreSheet" aria-labelledby="lrMoreTitle">', 1)[1]
        sheet = sheet.split("</dialog>", 1)[0]
        self.assertIn('<h2 id="lrMoreTitle">More</h2>', sheet)
        self.assertEqual(re.findall(r'data-lr-page="(\w+)"', sheet), ["saved", "radio", "blocklist", "settings"])
        self.assertIn("lrSheet.showModal()", self.js)
        self.assertIn("lrMore.setAttribute('aria-expanded', 'false')", self.js)

    def test_search_and_mode_reuse_the_existing_entry_points(self):
        self.assertEqual(self.html.count('id="globalSearchInput"'), 1)
        self.assertIn('for="globalSearchInput" class="sr-only"', self.html)
        self.assertIn('aria-hidden="true">/</kbd>', self.html)
        self.assertIn('href="#content">Skip to content', self.html)
        self.assertIn('<main id="content" tabindex="-1">', self.html)
        self.assertIn('role="group" aria-labelledby="lrModeLabel"', self.html)
        self.assertEqual(
            re.findall(r'data-lr-mode="(\w+)" aria-pressed="false"', self.html),
            ["safer", "balanced", "deeper"],
        )
        self.assertIn("'/api/settings/discovery-mode'", self.js)
        self.assertIn("JSON.stringify({discovery_mode: value})", self.js)

    def test_breakpoints_focus_ring_and_target_size_come_from_spec(self):
        self.assertIn("@media (720px <= width < 1080px)", self.css)
        self.assertIn("@media (width < 720px)", self.css)
        self.assertIn("--lr-shell-rail: 72px", self.css)
        self.assertIn("--lr-target: 44px", self.tokens)
        self.assertRegex(self.css, r"\.lr-nav\s*\{[^}]*min-width: var\(--lr-target\);[^}]*min-height: var\(--lr-target\)")
        self.assertRegex(self.css, r"\.lr-segment button\s*\{[^}]*min-height: var\(--lr-target\)")
        self.assertIn("outline: 2px solid var(--lr-focus)", self.css)
        self.assertIn("animation: lr-sheet-in var(--lr-motion-sheet)", self.css)
