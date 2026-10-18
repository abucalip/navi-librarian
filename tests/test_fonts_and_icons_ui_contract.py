"""Phase 1 contract: fonts and icons are self-hosted, licensed, and within the weight budget.

DESIGN_SYSTEM.md sections 5, 10 and 12; REDESIGN_ROADMAP.md Phase 1.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
FONTS = STATIC / "fonts"
TEMPLATES = ROOT / "app" / "templates"
FONT_BUDGET_BYTES = 150 * 1024
ICON_NAMES = [
    "layout-dashboard", "compass", "calendar-plus", "user-round", "library", "mic-vocal",
    "download", "settings", "log-out", "search", "chevron-left", "chevron-right", "x", "trash-2",
]


class SelfHostedFontTests(unittest.TestCase):
    def test_no_stylesheet_or_template_loads_a_third_party_font(self):
        for path in [STATIC / "app.css", STATIC / "login.css", STATIC / "fonts" / "fonts.css",
                     TEMPLATES / "index.html", TEMPLATES / "login.html"]:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("fonts.googleapis.com", text, path.name)
            self.assertNotIn("fonts.gstatic.com", text, path.name)

    def test_both_pages_link_the_self_hosted_stylesheet_and_preload_only_the_display_face(self):
        for name in ("index.html", "login.html"):
            text = (TEMPLATES / name).read_text(encoding="utf-8")
            self.assertIn('href="/static/fonts/fonts.css"', text, name)
            preloads = re.findall(r'<link rel="preload"[^>]*href="([^"]+)"', text)
            self.assertEqual(preloads, ["/static/fonts/big-shoulders-display-700.woff2"], name)
            self.assertIn("crossorigin", text.split("/static/fonts/big-shoulders-display-700.woff2")[1].split(">")[0], name)

    def test_every_face_declared_is_shipped_with_swap_and_the_total_is_within_budget(self):
        css = (FONTS / "fonts.css").read_text(encoding="utf-8")
        urls = re.findall(r'url\("([^"]+\.woff2)"\)', css)
        self.assertEqual(len(urls), 7)
        self.assertEqual(css.count("font-display: swap"), 7)
        total = 0
        for url in urls:
            path = FONTS / url
            self.assertTrue(path.is_file(), url)
            total += path.stat().st_size
        self.assertLessEqual(total, FONT_BUDGET_BYTES)

    def test_each_font_family_ships_its_ofl_licence(self):
        for family in ("big-shoulders-display", "schibsted-grotesk", "jetbrains-mono"):
            licence = (FONTS / f"LICENSE-{family}.txt").read_text(encoding="utf-8")
            self.assertIn("SIL OPEN FONT LICENSE VERSION 1.1", licence.upper(), family)


class IconSpriteTests(unittest.TestCase):
    def test_sprite_contains_the_initial_lucide_set_and_nothing_else(self):
        sprite = (STATIC / "icons.svg").read_text(encoding="utf-8")
        ids = re.findall(r'<symbol id="([^"]+)"', sprite)
        self.assertEqual(ids, ICON_NAMES)
        self.assertIn('stroke="currentColor"', sprite)
        self.assertNotIn("<script", sprite)

    def test_lucide_licence_is_vendored_beside_the_sprite(self):
        licence = (STATIC / "vendor" / "lucide" / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("ISC License", licence)


if __name__ == "__main__":
    unittest.main()
