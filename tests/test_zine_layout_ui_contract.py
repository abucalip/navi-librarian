"""Zine Spread layout (D-024, docs/BRUT_ROUND3_PLAN.md, phase P1): its palette, the scoping of its rules and its hidden-by-default hooks."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"


def _lum(hex_color):
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a, b):
    x, y = _lum(a), _lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


class ZineLayoutTests(unittest.TestCase):
    def setUp(self):
        self.script = (STATIC / "appearance.js").read_text(encoding="utf-8")
        self.themes = (STATIC / "themes.css").read_text(encoding="utf-8")
        self.layouts = (STATIC / "layouts.css").read_text(encoding="utf-8")
        self.app = (STATIC / "app.js").read_text(encoding="utf-8")
        self.html = (ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")
        self.zine = self.layouts.split('==== Zine Spread ("zine")')[1].split("*/", 1)[1]
        self.block = self.themes.split(':root[data-theme="zine"]')[1].split("\n}")[0]

    def _token(self, name):
        return re.search(rf"--{name}: (#[0-9a-fA-F]{{6}})", self.block).group(1)

    def test_the_catalogue_entry_declares_the_layout(self):
        line = next(l for l in self.script.splitlines() if "id: 'zine'" in l)
        for field in ("label: 'Zine \\u00b7 Yellow'", "group: 'Zine Spread'", "dark: false", "brut: true", "layout: 'zine'", "bar: '#ffde59'"):
            self.assertIn(field, line)

    def test_every_zine_selector_is_scoped_and_the_layout_applies_only_above_900px(self):
        css = re.sub(r"/\*.*?\*/", "", self.zine, flags=re.S)
        self.assertTrue(css.lstrip().startswith("@media (min-width: 901px) {"))
        selectors = []
        for chunk in re.findall(r"([^{}]+)\{", css):
            text = chunk.strip()
            if text.startswith("@") or re.fullmatch(r"(\d+%|from|to)(\s*,\s*(\d+%|from|to))*", text):
                continue
            selectors.extend(part.strip() for part in text.split(","))
        self.assertGreater(len(selectors), 20)
        for selector in selectors:
            self.assertTrue(selector.startswith(':root[data-layout="zine"]'), selector)

    def test_the_palette_has_the_full_token_set(self):
        for name in ("ink-rail", "ink", "surface", "surface-raised", "surface-hover", "edge", "text", "text-muted", "accent", "accent-text",
                     "focus", "on-accent", "bw", "brut-sh", "brut-shadow-color", "brut-nav-bg", "brut-nav-text", "zine-pink", "zine-teal"):
            self.assertRegex(self.block, rf"--{name}:", name)
        self.assertEqual(self._token("accent"), "#ffde59")

    def test_text_contrast_meets_wcag_aa(self):
        t = self._token
        pairs = [("text", "ink"), ("text", "surface"), ("text-muted", "ink"), ("text-muted", "surface"), ("text-muted", "ink-rail"),
                 ("text", "ink-rail"), ("accent-text", "surface"), ("accent-text", "ink"), ("on-accent", "accent"),
                 ("zine-on-colour", "zine-pink"), ("zine-on-colour", "zine-teal"), ("brut-nav-text", "brut-nav-bg"),
                 ("text", "surface-raised"), ("text-muted", "surface-raised")]
        for fg, bg in pairs:
            fg_hex = t(fg) if fg != "zine-on-colour" else self._token("zine-on-colour")
            self.assertGreaterEqual(_contrast(fg_hex, t(bg)), 4.5, f"{fg} on {bg}")
        self.assertGreaterEqual(_contrast(t("focus"), t("ink")), 3, "focus ring on ground")
        self.assertGreaterEqual(_contrast(t("focus"), t("surface")), 3, "focus ring on surface")

    def test_the_ticker_is_hidden_and_aria_hidden_by_default_and_shown_only_by_the_layout(self):
        self.assertRegex(self.html, r'<p id="zineTicker" class="zine-ticker" aria-hidden="true" hidden>')
        self.assertNotIn(".zine-ticker", self.layouts.split('==== Zine Spread ("zine")')[0])
        self.assertIn('document.documentElement.dataset.layout !== \'zine\'', self.app)
        self.assertIn("updateZineTicker(jobs);", self.app)

    def test_the_ticker_states_are_words_and_make_no_new_request(self):
        fn = self.app.split("function updateZineTicker(jobs) {")[1].split("\n}\n")[0]
        self.assertIn("acquisitionStatusInfo(job.status).label", fn)
        self.assertNotIn("fetch(", fn)

    def test_the_letter_strip_is_hidden_by_default_acts_only_on_loaded_rows_and_never_fetches(self):
        self.assertIn('<div id="zineLetters" class="zine-letters" role="group" aria-label="Jump to a letter" hidden></div>', self.html)
        fn = self.app.split("function updateZineLetters() {")[1].split("\n}\n")[0]
        self.assertIn("document.documentElement.dataset.layout !== 'zine'", fn)
        self.assertIn("button.disabled = true;", fn)
        self.assertIn("No loaded entry starts with", fn)
        self.assertNotIn("fetch(", fn)
        self.assertNotIn("requestJSON", fn)

    def test_the_lead_story_and_shelves_keep_dom_order_and_are_css_only(self):
        self.assertIn('#dashboard > .panel:not(.dashboard-shelf) { grid-column: 1 / -1; }', self.zine)
        self.assertIn("column-count: 2", self.zine)
        self.assertNotIn("order:", re.sub(r"/\*.*?\*/", "", self.zine, flags=re.S).replace("border:", "").replace("-order", ""))

    def test_reduced_motion_disables_any_zine_animation(self):
        css = re.sub(r"/\*.*?\*/", "", self.zine, flags=re.S)
        if "animation:" in css or "transition:" in css:
            self.assertIn("prefers-reduced-motion: reduce", css)


if __name__ == "__main__":
    unittest.main()
