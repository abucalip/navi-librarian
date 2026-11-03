"""Ledger Room layout (D-023, docs/BRUT_LAYOUTS_PLAN.md, phase P2): its three palettes and the scoping of its rules."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
LEDGER_THEMES = ["ledgerslate", "ledgerplum", "ledgermono"]


def _lum(hex_color):
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a, b):
    x, y = _lum(a), _lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


class LedgerLayoutTests(unittest.TestCase):
    def setUp(self):
        self.script = (STATIC / "appearance.js").read_text(encoding="utf-8")
        self.themes = (STATIC / "themes.css").read_text(encoding="utf-8")
        self.layouts = (STATIC / "layouts.css").read_text(encoding="utf-8")
        self.ledger = self.layouts.split('==== Ledger Room ("ledger")')[1].split("*/", 1)[1]

    def _block(self, theme):
        return self.themes.split(f':root[data-theme="{theme}"]')[1].split("\n}")[0]

    def _token(self, block, name):
        return re.search(rf"--{name}: (#[0-9a-fA-F]{{6}})", block).group(1)

    def test_the_three_ledger_themes_declare_the_ledger_layout_and_are_light_neobrut(self):
        entries = self.script.split("var THEMES = [")[1].split("];")[0]
        for theme in LEDGER_THEMES:
            line = next(l for l in entries.splitlines() if f"id: '{theme}'" in l)
            for field in ("layout: 'ledger'", "brut: true", "dark: false", "group: 'Ledger Room'"):
                self.assertIn(field, line, theme)

    def test_every_ledger_selector_is_scoped_and_the_layout_applies_only_above_900px(self):
        css = re.sub(r"/\*.*?\*/", "", self.ledger, flags=re.S)
        self.assertTrue(css.lstrip().startswith("@media (min-width: 901px) {"))
        selectors = []
        for chunk in re.findall(r"([^{}]+)\{", css):
            text = chunk.strip()
            if text.startswith("@"):
                continue
            selectors.extend(part.strip() for part in text.split(","))
        self.assertGreater(len(selectors), 40)
        for selector in selectors:
            self.assertTrue(selector.startswith(':root[data-layout="ledger"]'), selector)

    def test_the_sidebar_takes_the_ink_colour_and_the_active_tab_is_the_accent(self):
        self.assertIn(':root[data-layout="ledger"] nav { background: var(--ledger-side);', self.ledger)
        self.assertIn("background: var(--accent);", self.ledger.split("nav button.active")[1].split("}")[0])

    def test_rows_never_clip_text_and_the_small_shelf_cover_shows_no_placeholder_text(self):
        self.assertIn('.ranked-row .row-main { height: auto; min-height: var(--row-art); overflow: visible;', self.ledger)
        self.assertIn('.shelf-card .card-art-placeholder { padding: 0; font-size: 0; }', self.ledger)
        self.assertIn('.shelf-card .card-art-placeholder::before { content: none; }', self.ledger)
        self.assertIn(".shelf-card .card-art > .about-toggle", self.ledger)
        # the last row of a group drops its rule so the frame is not doubled
        self.assertIn(".ranked-row:last-child { border-bottom: 0; }", self.ledger)

    def test_each_palette_defines_the_full_token_set_and_every_text_pair_meets_aa(self):
        for theme in LEDGER_THEMES:
            block = self._block(theme)
            for token in ("ink-rail", "ink", "surface", "surface-raised", "surface-hover", "edge", "text", "text-muted", "text-subtle",
                          "accent", "accent-text", "focus", "accent-hover", "accent-dim", "on-accent", "chart-red", "ok", "caution",
                          "ledger-side", "ledger-side-text", "ledger-side-muted"):
                self.assertIn(f"--{token}:", block, f"{theme} {token}")
            for token in ("--bw:", "--radius-control:", "--brut-sh:", "--brut-shadow-color:", "--slider-fade: #141211"):
                self.assertIn(token, block, f"{theme} {token}")
            surface, raised, ground = (self._token(block, n) for n in ("surface", "surface-raised", "ink"))
            for text_token in ("text", "text-muted", "text-subtle", "accent-text"):
                for bg in (surface, raised):
                    self.assertGreaterEqual(_contrast(self._token(block, text_token), bg), 4.5, f"{theme} {text_token} on {bg}")
            self.assertGreaterEqual(_contrast(self._token(block, "on-accent"), self._token(block, "accent")), 4.5, f"{theme} text on the accent")
            self.assertGreaterEqual(_contrast(self._token(block, "text"), self._token(block, "surface-hover")), 4.5, f"{theme} text on a hovered row")
            self.assertGreaterEqual(_contrast(self._token(block, "focus"), ground), 3.0, f"{theme} focus on the page")
            side = self._token(block, "ledger-side")
            for text_token in ("ledger-side-text", "ledger-side-muted"):
                self.assertGreaterEqual(_contrast(self._token(block, text_token), side), 4.5, f"{theme} {text_token} on the sidebar")
            self.assertGreaterEqual(_contrast(self._token(block, "on-accent"), self._token(block, "accent")), 4.5)
            # the active tab (accent) must stand out from the sidebar
            self.assertGreaterEqual(_contrast(self._token(block, "accent"), side), 3.0, f"{theme} active tab on the sidebar")
            self.assertEqual(self._token(block, "ink-rail"), surface, f"{theme} header shares the surface colour")

    def test_the_default_theme_is_still_ink(self):
        self.assertIn("ink", self.script.split("var THEMES = [")[1].split("\n")[1])


if __name__ == "__main__":
    unittest.main()
