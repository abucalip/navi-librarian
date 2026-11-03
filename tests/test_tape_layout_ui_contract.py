"""Tape Deck layout (D-023, docs/BRUT_LAYOUTS_PLAN.md, phase P1): the layout hook, its three palettes and the scoping of its rules."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
TEMPLATES = ROOT / "app" / "templates"
TAPE_THEMES = ["tapelime", "tapecobalt", "tapetangerine"]


def _lum(hex_color):
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a, b):
    x, y = _lum(a), _lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


class TapeLayoutTests(unittest.TestCase):
    def setUp(self):
        self.script = (STATIC / "appearance.js").read_text(encoding="utf-8")
        self.themes = (STATIC / "themes.css").read_text(encoding="utf-8")
        self.layouts = (STATIC / "layouts.css").read_text(encoding="utf-8")

    def _block(self, theme):
        return self.themes.split(f':root[data-theme="{theme}"]')[1].split("\n}")[0]

    def _token(self, block, name):
        return re.search(rf"--{name}: (#[0-9a-fA-F]{{6}})", block).group(1)

    def test_the_three_tape_themes_declare_the_tape_layout_and_the_script_sets_the_attribute(self):
        entries = self.script.split("var THEMES = [")[1].split("];")[0]
        for theme in TAPE_THEMES:
            line = next(l for l in entries.splitlines() if f"id: '{theme}'" in l)
            self.assertIn("layout: 'tape'", line, theme)
            self.assertIn("brut: true", line, theme)
            self.assertIn("dark: false", line, theme)
        for line in entries.splitlines():
            if not any(f"id: '{t}'" in line for t in TAPE_THEMES) and "layout: 'ledger'" not in line and "layout: 'crate'" not in line and "layout: 'zine'" not in line:
                self.assertNotIn("layout:", line)  # every earlier theme keeps today's pages
        self.assertIn("root.setAttribute('data-layout', theme.layout)", self.script)
        self.assertIn("root.removeAttribute('data-layout')", self.script)

    def test_the_main_page_loads_the_layout_sheet_after_the_themes_and_the_login_page_does_not_need_it(self):
        index = (TEMPLATES / "index.html").read_text(encoding="utf-8")
        self.assertLess(index.index('href="/static/themes.css"'), index.index('href="/static/layouts.css"'))
        self.assertNotIn("layouts.css", (TEMPLATES / "login.html").read_text(encoding="utf-8"))

    def test_every_rule_in_the_layout_sheet_is_scoped_to_a_layout(self):
        css = re.sub(r"/\*.*?\*/", "", self.layouts, flags=re.S)
        selectors = []
        for chunk in re.findall(r"([^{}]+)\{", css):
            text = chunk.strip()
            if text.startswith("@") or re.fullmatch(r"(\d+%|from|to)(\s*,\s*(\d+%|from|to))*", text):
                continue
            selectors.extend(part.strip() for part in text.split(","))
        self.assertGreater(len(selectors), 30)
        for selector in selectors:
            self.assertTrue(selector.startswith((':root[data-layout="tape"]', ':root[data-layout="ledger"]', ':root[data-layout="crate"]', ':root[data-layout="zine"]')), selector)

    def test_the_layout_applies_only_above_900px_so_the_phone_and_icon_rail_shells_are_untouched(self):
        self.assertIn("@media (min-width: 901px) {", self.layouts)
        body = self.layouts.split("@media (min-width: 901px) {")[1]
        # the only rule outside the gate is the meter's keyframes and the reduced-motion switch
        outside = body.split("\n}\n", 1)[1]
        self.assertIn("@keyframes tape-meter", outside)
        self.assertNotIn("nav", outside.replace("tape-meter", ""))

    def test_the_tab_strip_has_one_rule_between_groups_and_the_search_fields_are_rectangles(self):
        self.assertIn(':root[data-layout="tape"] .nav-group > button:last-of-type { border-right: 0; }', self.layouts)
        rule = self.layouts.split("Search fields are plain rectangles")[1].split("}")[0]
        for selector in (".search-field,", ".search-field::before,", '.global-search input[type="search"],'):
            self.assertIn(selector, rule)
        self.assertIn("border-radius: 0;", rule)

    def test_a_row_never_clips_its_text_and_the_small_shelf_cover_hides_the_hover_bio(self):
        row = self.layouts.split("A row never clips its text")[1].split("*/")[1]
        self.assertIn('.ranked-row .row-main { height: auto; min-height: var(--row-art); overflow: visible;', row)
        self.assertIn('.ranked-row .artist-bio { -webkit-line-clamp: 1;', row)
        self.assertIn('.ranked-row.is-bio-open .artist-bio { display: block; -webkit-line-clamp: none;', row)
        hidden = self.layouts.split("The hover bio and its about button")[1].split("}")[0]
        self.assertIn(".shelf-card .card-art > .artist-bio", hidden)
        self.assertIn(".shelf-card .card-art > .about-toggle", hidden)
        self.assertIn("display: none", hidden)

    def test_the_small_shelf_cover_shows_no_placeholder_text(self):
        self.assertIn(':root[data-layout="tape"] .shelf-card .card-art-placeholder { padding: 0; font-size: 0; }', self.layouts)
        self.assertIn(':root[data-layout="tape"] .shelf-card .card-art-placeholder::before { content: none; }', self.layouts)

    def test_the_downloading_meter_is_decorative_and_stops_under_reduced_motion(self):
        self.assertIn('.acq-row[data-status="downloading"] .acq-status::after', self.layouts)
        self.assertIn('content: ""', self.layouts)
        reduced = self.layouts.split("@media (prefers-reduced-motion: reduce) {")[1]
        self.assertIn("animation: none", reduced)

    def test_each_palette_defines_the_full_token_set_with_a_visible_focus_and_readable_text(self):
        for theme in TAPE_THEMES:
            block = self._block(theme)
            for token in ("ink-rail", "ink", "surface", "surface-raised", "surface-hover", "edge", "text", "text-muted", "text-subtle",
                          "accent", "accent-text", "focus", "accent-hover", "accent-dim", "on-accent", "chart-red", "ok", "caution"):
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
            self.assertEqual(self._token(block, "ink-rail"), surface, f"{theme} header and tab strip share the surface colour")

    def test_the_cobalt_accent_was_darkened_from_the_mockup_so_white_text_passes(self):
        # The mockup used #4f7cff (white on it is 3.9:1). #3d68f0 keeps the hue and passes.
        block = self._block("tapecobalt")
        self.assertEqual(self._token(block, "accent"), "#3d68f0")
        self.assertGreaterEqual(_contrast("#ffffff", "#3d68f0"), 4.5)

    def test_the_deck_is_hidden_by_default_built_from_the_loaded_list_and_its_meter_is_decorative_and_stops_under_reduced_motion(self):
        index = (TEMPLATES / "index.html").read_text(encoding="utf-8")
        app = (STATIC / "app.js").read_text(encoding="utf-8")
        self.assertIn('<aside id="tapeDashDeck" class="tape-deck" aria-label="Acquisition deck" hidden></aside>', index)
        self.assertIn('id="tapeAcqDeck" class="tape-deck tape-deck-large" role="region" aria-label="Acquisition deck" hidden>', index)
        build = app.split("function buildTapeDeck(box, job, percent, counts) {")[1].split("\n}\n")[0]
        self.assertIn("meter.setAttribute('aria-hidden', 'true');", build)
        self.assertNotIn("fetch(", build)
        update = app.split("function updateTapeDecks(jobs) {")[1].split("\n}\n")[0]
        self.assertNotIn("requestJSON", update)
        self.assertIn("if (box.dataset.sig === signature) continue;", update)  # rebuilt only when what it shows changes
        self.assertIn("updateTapeDecks(jobs);", app.split("function updateActiveDownloadBadge(data) {")[1].split("\n}\n")[0])
        reduced = self.layouts.split("@media (prefers-reduced-motion: reduce) {")[1]
        self.assertIn(':root[data-layout="tape"] .tape-meter > i { animation: none;', reduced)
        for selector in (".tape-deck {", ".tape-meter {"):
            self.assertIn(':root[data-layout="tape"] ' + selector, self.layouts)
            self.assertNotIn(selector, (STATIC / "app.css").read_text(encoding="utf-8"))

    def test_the_dashboard_has_a_deck_column_beside_the_shelves(self):
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr)) minmax(260px, 300px);", self.layouts)
        self.assertIn(':root[data-layout="tape"] #tapeDashDeck { grid-column: 3; grid-row: 3 / span 2; }', self.layouts)

    def test_the_search_shortcut_hint_is_shown_by_every_layout(self):
        for layout in ("tape", "ledger", "crate"):
            self.assertIn(f':root[data-layout="{layout}"] .search-shortcut {{ display: block;', self.layouts)


if __name__ == "__main__":
    unittest.main()
