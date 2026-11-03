"""Crate Wall layout (D-023, docs/BRUT_LAYOUTS_PLAN.md, phase P3): its three palettes and the scoping of its rules."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
CRATE_THEMES = ["cratekraft", "cratemint", "cratenight"]


def _lum(hex_color):
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a, b):
    x, y = _lum(a), _lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


class CrateLayoutTests(unittest.TestCase):
    def setUp(self):
        self.script = (STATIC / "appearance.js").read_text(encoding="utf-8")
        self.themes = (STATIC / "themes.css").read_text(encoding="utf-8")
        self.layouts = (STATIC / "layouts.css").read_text(encoding="utf-8")
        self.app = (STATIC / "app.js").read_text(encoding="utf-8")
        self.crate = self.layouts.split('==== Crate Wall ("crate")')[1].split("*/", 1)[1].split("==== Zine Spread")[0]

    def _block(self, theme):
        return self.themes.split(f':root[data-theme="{theme}"]')[1].split("\n}")[0]

    def _token(self, block, name):
        return re.search(rf"--{name}: (#[0-9a-fA-F]{{6}})", block).group(1)

    def test_the_three_crate_themes_declare_the_layout_and_only_night_is_dark(self):
        entries = self.script.split("var THEMES = [")[1].split("];")[0]
        for theme in CRATE_THEMES:
            line = next(l for l in entries.splitlines() if f"id: '{theme}'" in l)
            for field in ("layout: 'crate'", "brut: true", "group: 'Crate Wall'"):
                self.assertIn(field, line, theme)
            self.assertIn("dark: true" if theme == "cratenight" else "dark: false", line, theme)

    def test_every_crate_selector_is_scoped_and_the_layout_applies_only_above_900px(self):
        css = re.sub(r"/\*.*?\*/", "", self.crate, flags=re.S)
        self.assertTrue(css.lstrip().startswith("@media (min-width: 901px) {"))
        selectors = []
        for chunk in re.findall(r"([^{}]+)\{", css):
            text = chunk.strip()
            if text.startswith("@") or re.fullmatch(r"(\d+%|from|to)(\s*,\s*(\d+%|from|to))*", text):
                continue
            selectors.extend(part.strip() for part in text.split(","))
        self.assertGreater(len(selectors), 50)
        for selector in selectors:
            self.assertTrue(selector.startswith(':root[data-layout="crate"]'), selector)

    def test_the_wall_is_five_then_four_then_three_columns_with_a_two_by_two_hero(self):
        self.assertIn("--crate-cols: 3;", self.crate)
        self.assertIn("@media (min-width: 1060px) { :root[data-layout=\"crate\"] { --crate-cols: 4; } }", self.crate)
        self.assertIn("@media (min-width: 1280px) { :root[data-layout=\"crate\"] { --crate-cols: 5; } }", self.crate)
        self.assertIn(".ranked-list > .ranked-row:first-child { grid-column: span 2; grid-row: span 2; }", self.crate)
        self.assertIn("repeat(var(--crate-cols), minmax(0, 1fr))", self.crate)

    def test_status_is_a_stamp_that_keeps_its_word_and_the_active_label_is_tilted_and_filled(self):
        self.assertIn(".status-badge {", self.crate)
        self.assertNotIn("font-size: 0", self.crate.split(".status-badge {")[1].split("}")[0])
        self.assertIn("transform: rotate(-6deg);", self.crate)
        active = self.crate.split("nav button.active {")[1].split("}")[0]
        self.assertIn("background: var(--accent);", active)
        self.assertIn("transform: rotate(-2deg);", active)

    def test_the_drawer_moves_only_the_dialog_box_and_stops_animating_under_reduced_motion(self):
        drawer = self.crate.split("Album window: a right-hand drawer")[1]
        self.assertIn("place-items: stretch end;", drawer)
        self.assertIn(".album-modal {", drawer)
        self.assertIn("animation: crate-drawer-in", drawer)
        reduced = self.layouts.split("==== Zine Spread")[0].split("@media (prefers-reduced-motion: reduce) {")[-1]
        self.assertIn('[data-layout="crate"] .album-modal { animation: none; }', reduced)
        self.assertNotIn("display: none", drawer.split(".album-modal-layout")[0])  # nothing in the dialog is hidden

    def test_get_moves_to_the_drawer_foot_and_not_for_me_runs_the_rows_own_dismiss_control(self):
        index = (ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<div id="albumModalFoot" class="album-modal-foot" hidden>', index)
        self.assertIn('id="albumModalActions" class="action-group"', index)
        placed = self.app.split("function placeAlbumModalActions() {")[1].split("\n}\n")[0]
        self.assertIn("document.documentElement.dataset.layout === 'crate' && albumDrawerQuery.matches", placed)
        self.assertIn("foot.prepend(group)", placed)  # the same element moves, so Get keeps its state and handlers
        self.assertIn("art.append(group)", placed)
        skip = self.app.split("$('albumModalSkip').addEventListener('click', () => {")[1].split("});")[0]
        self.assertIn("querySelector('.dismiss-album')", skip)
        self.assertIn("dismiss.click();", skip)
        self.assertLess(skip.index("closeAlbumModal();"), skip.index("dismiss.click();"))
        self.assertIn("skip.toggleAttribute('data-available', Boolean(card.querySelector('.dismiss-album')));", self.app)
        self.assertIn(":root[data-layout=\"crate\"] .album-modal-skip:not([data-available]) { display: none; }", self.crate)
        self.assertNotIn(".album-modal-foot", (STATIC / "app.css").read_text(encoding="utf-8"))

    def test_the_hover_card_exists_only_for_hover_capable_devices(self):
        card = self.crate.split("The hover card")[1].split("*/")[1]
        self.assertTrue(card.lstrip().startswith(':root[data-layout="crate"] .ranked-row .row-meta { display: none; }'))
        self.assertIn("@media (hover: hover) {", card)

    def test_the_shelf_arrows_are_hidden_by_default_and_hide_themselves_when_the_strip_fits(self):
        self.assertIn("arrows.hidden = true;", self.app)
        self.assertIn("arrows.toggleAttribute('data-fits', track.scrollWidth <= track.clientWidth + 1)", self.app)
        self.assertIn(':root[data-layout="crate"] .shelf-arrows[data-fits] { display: none; }', self.crate)
        self.assertNotIn(".shelf-arrows", (STATIC / "app.css").read_text(encoding="utf-8"))

    def test_each_palette_defines_the_full_token_set_and_every_text_pair_meets_aa(self):
        for theme in CRATE_THEMES:
            block = self._block(theme)
            for token in ("ink-rail", "ink", "surface", "surface-raised", "surface-hover", "edge", "text", "text-muted", "text-subtle",
                          "accent", "accent-text", "focus", "accent-hover", "accent-dim", "on-accent", "chart-red", "ok", "caution",
                          "crate-gold", "crate-on-gold"):
                self.assertIn(f"--{token}:", block, f"{theme} {token}")
            light = theme != "cratenight"
            self.assertEqual("--slider-fade: #141211" in block, light, theme)
            self.assertIn("color-scheme: light;" if light else "color-scheme: dark;", block)
            surface, raised, ground = (self._token(block, n) for n in ("surface", "surface-raised", "ink"))
            for text_token in ("text", "text-muted", "text-subtle", "accent-text"):
                for bg in (surface, raised):
                    self.assertGreaterEqual(_contrast(self._token(block, text_token), bg), 4.5, f"{theme} {text_token} on {bg}")
            accent, on = self._token(block, "accent"), self._token(block, "on-accent")
            self.assertGreaterEqual(_contrast(on, accent), 4.5, f"{theme} stamp text on the accent")
            self.assertGreaterEqual(_contrast(self._token(block, "crate-on-gold"), self._token(block, "crate-gold")), 4.5, f"{theme} Queued stamp")
            self.assertGreaterEqual(_contrast(self._token(block, "text"), self._token(block, "surface-hover")), 4.5, f"{theme} text on a hovered tile")
            self.assertGreaterEqual(_contrast(self._token(block, "text"), ground), 4.5, f"{theme} header text on the band")
            self.assertGreaterEqual(_contrast(self._token(block, "focus"), ground), 3.0, f"{theme} focus on the page")
            self.assertGreaterEqual(_contrast(self._token(block, "focus"), surface), 3.0, f"{theme} focus on a tile")
            self.assertEqual(self._token(block, "ink-rail"), ground, f"{theme} header band is the page ground")


if __name__ == "__main__":
    unittest.main()
