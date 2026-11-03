"""Pipeline Board layout (D-024, docs/BRUT_ROUND3_PLAN.md, phase P2): its palette, the scoping of its rules, its hidden-by-default board and the rules of its drop."""

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


class PipelineLayoutTests(unittest.TestCase):
    def setUp(self):
        self.script = (STATIC / "appearance.js").read_text(encoding="utf-8")
        self.themes = (STATIC / "themes.css").read_text(encoding="utf-8")
        self.layouts = (STATIC / "layouts.css").read_text(encoding="utf-8")
        self.app = (STATIC / "app.js").read_text(encoding="utf-8")
        self.pipe_js = (STATIC / "layout-pipeline.js").read_text(encoding="utf-8")
        self.html = (ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")
        self.pipe = self.layouts.split('==== Pipeline Board ("pipeline")')[1].split("*/", 1)[1]
        self.block = self.themes.split(':root[data-theme="pipeline"]')[1].split("\n}")[0]

    def _token(self, name):
        return re.search(rf"--{name}: (#[0-9a-fA-F]{{6}})", self.block).group(1)

    def test_the_catalogue_entry_declares_the_layout(self):
        line = next(l for l in self.script.splitlines() if "id: 'pipeline'" in l)
        for field in ("label: 'Pipeline \\u00b7 Orange'", "group: 'Pipeline Board'", "dark: false", "brut: true", "layout: 'pipeline'", "bar: '#ff7a1a'"):
            self.assertIn(field, line)

    def test_every_pipeline_selector_is_scoped_and_applies_only_above_900px(self):
        css = re.sub(r"/\*.*?\*/", "", self.pipe, flags=re.S)
        self.assertTrue(css.lstrip().startswith("@media (min-width: 901px) {"))
        selectors = []
        for chunk in re.findall(r"([^{}]+)\{", css):
            text = chunk.strip()
            if text.startswith("@") or re.fullmatch(r"(\d+%|from|to)(\s*,\s*(\d+%|from|to))*", text):
                continue
            selectors.extend(part.strip() for part in text.split(","))
        self.assertGreater(len(selectors), 20)
        for selector in selectors:
            self.assertTrue(selector.startswith(':root[data-layout="pipeline"]'), selector)

    def test_the_palette_has_the_full_token_set(self):
        for name in ("ink-rail", "ink", "surface", "surface-raised", "surface-hover", "edge", "text", "text-muted", "accent", "accent-text",
                     "focus", "on-accent", "pipe-orange", "pipe-lime", "pipe-yellow", "pipe-violet", "pipe-red", "pipe-teal", "pipe-green"):
            self.assertRegex(self.block, rf"--{name}:", name)
        self.assertEqual(self._token("accent"), "#c6f432")

    def test_text_contrast_meets_wcag_aa(self):
        ground = self._token("ink")
        surface = self._token("surface")
        ink = self._token("text")
        muted = self._token("text-muted")
        self.assertGreaterEqual(_contrast(ink, ground), 4.5)
        self.assertGreaterEqual(_contrast(ink, surface), 4.5)
        self.assertGreaterEqual(_contrast(muted, ground), 4.5)
        self.assertGreaterEqual(_contrast(muted, surface), 4.5)
        self.assertGreaterEqual(_contrast(ink, self._token("accent")), 4.5)
        self.assertGreaterEqual(_contrast(ink, self._token("pipe-yellow")), 4.5)
        self.assertGreaterEqual(_contrast(ink, self._token("pipe-lime")), 4.5)
        self.assertGreaterEqual(_contrast(self._token("surface"), self._token("edge")), 4.5)

    def test_the_board_is_hidden_by_default_and_filled_only_by_its_script(self):
        self.assertIn('<section id="pipelineBoard" class="pipeline-board" aria-labelledby="pipelineHeading" hidden>', self.html)
        self.assertIn('id="pipelineToast" class="pipeline-toast" role="status"', self.html)
        self.assertIn('/static/layout-pipeline.js', self.html)
        self.assertLess(self.html.index('/static/app.js'), self.html.index('/static/layout-pipeline.js'))
        self.assertIn("function renderPipelineBoard", self.pipe_js)
        self.assertIn("if (!pipelineActive()) {\n    board.hidden = true;", self.pipe_js)
        self.assertIn("pipelineOn() && !isMobileLayout()", self.pipe_js)

    def test_the_default_dashboard_panels_are_hidden_only_in_this_layout(self):
        self.assertIn(':root[data-layout="pipeline"] #dashboard > :not(#pipelineBoard) { display: none !important; }', self.pipe)

    def test_app_js_calls_the_hook_on_the_dashboard_and_on_acquisition_changes(self):
        self.assertIn("zineHook('renderPipelineBoard');", self.app)
        self.assertIn("zineHook('renderPipelineBoard', jobs);", self.app)
        self.assertIn("if (name === 'Recent') zineHook('renderPipelineBoard');", self.app)

    def test_a_drop_runs_the_existing_get_and_save_controls_and_never_a_second_request(self):
        self.assertIn("card.querySelector('.get-album')", self.pipe_js)
        self.assertIn("get.click();", self.pipe_js)
        self.assertIn("card.querySelector('.save-album')", self.pipe_js)
        self.assertNotIn("fetch('/api/acquire'", self.pipe_js)
        self.assertNotIn("sendJSON('/api/acquire'", self.pipe_js)
        self.assertNotIn("/api/acquire", self.pipe_js)

    def test_only_queued_and_saved_accept_a_drop(self):
        self.assertIn("const PIPELINE_DROP = new Set(['queued', 'saved']);", self.pipe_js)
        self.assertNotIn("dismiss-album'", self.pipe_js.split("function pipelineAct")[1].split("function pipelineMoveMenu")[0])

    def test_every_drag_has_a_button_alternative(self):
        self.assertIn("button.className = 'pipeline-move';", self.pipe_js)
        self.assertIn("button.textContent = 'Move to…';", self.pipe_js)

    def test_the_board_takes_its_cards_from_the_app_builders(self):
        for builder in ("buildShelfCard(", "buildSavedCard(", "acquisitionStatusInfo(", "pipelineLoadSaved("):
            self.assertIn(builder, self.pipe_js)
        self.assertIn("/api/discovery/for_me", self.pipe_js)
        self.assertNotIn("/api/library/", self.pipe_js)

    def test_reduced_motion_removes_movement(self):
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.pipe)
        self.assertIn("transform: none !important;", self.pipe)


if __name__ == "__main__":
    unittest.main()
