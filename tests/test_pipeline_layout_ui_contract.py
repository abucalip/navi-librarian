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

    def layouts_css_text(self):
        return self.layouts

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

    def test_the_toast_follows_the_real_get_state_after_a_drop(self):
        self.assertIn("function pipelineFollowGet(get, album, target)", self.pipe_js)
        self.assertIn("pipelineFollowGet(get, album, 'pipelineToast');", self.pipe_js)
        self.assertIn("pipelineFollowGet(get, album, 'pipelineArtistStatus');", self.pipe_js)
        self.assertIn("get.classList.contains('is-failed')", self.pipe_js)

    def test_only_queued_and_saved_accept_a_drop(self):
        self.assertIn("const PIPELINE_DROP = new Set(['queued', 'saved']);", self.pipe_js)
        self.assertNotIn("dismiss-album'", self.pipe_js.split("function pipelineAct")[1].split("function pipelineMoveMenu")[0])

    def test_no_move_to_button_on_the_tiles(self):
        # The owner removed Move to from the tiles. The album page is the visible path to Get, Save and Not for me.
        self.assertNotIn("'Move to…'", self.pipe_js)
        self.assertNotIn("card.append(pipelineMoveMenu(card))", self.pipe_js)
        self.assertIn("group.classList.add('pipeline-hidden-controls');", self.pipe_js)
        self.assertIn(".pipeline-tile .pipeline-hidden-controls { display: none; }", self.app + self.layouts_css_text())

    def test_the_board_takes_its_cards_from_the_app_builders(self):
        # Tiles carry the app's own action group (Get, Save, Not for me) and its artwork builder.
        for builder in ("createActionGroup(", "buildAlbumArtwork(", "acquisitionStatusInfo(", "pipelineLoadSaved(", "setSaveButtonState("):
            self.assertIn(builder, self.pipe_js)
        self.assertIn("/api/discovery/for_me", self.pipe_js)
        self.assertNotIn("/api/library/", self.pipe_js)
        self.assertIn("sendFeedback('dismiss', artist, name, metadata", self.pipe_js)

    def test_no_card_builder_shelf_cards_remain_on_the_board(self):
        self.assertNotIn("buildShelfCard(shelf", self.pipe_js)
        self.assertNotIn("buildSavedCard(entry)", self.pipe_js)

    def test_the_part_one_count_bug_is_gone(self):
        # Part one read an undeclared `count` in pipelineColumnElement, which threw as soon as the board drew.
        self.assertNotIn("String(count)", self.pipe_js)
        self.assertIn("badge.textContent = '0';", self.pipe_js)

    def test_p2b_uses_only_the_existing_read_endpoints(self):
        # No new endpoint or field: every /api path the layout script names must already be read by the app.
        paths = set(re.findall(r"'(/api/[^'?]+)", self.pipe_js))
        self.assertEqual(paths, {"/api/discovery/for_me", "/api/dashboard/genres", "/api/genres/"}, paths)
        for path in paths:
            self.assertIn(path, self.app + self.pipe_js, path)
        self.assertNotIn("/api/acquire", self.pipe_js)
        self.assertNotIn("/api/acquisitions/dismiss", self.pipe_js)

    def test_p2b_hooks_are_called_from_app_js_and_are_no_ops_in_other_layouts(self):
        for hook in ("renderPipelineLanes", "renderPipelineAlbum", "renderPipelineArtist"):
            self.assertIn("zineHook('%s'" % hook, self.app, hook)
            self.assertIn("function %s(" % hook, self.pipe_js, hook)
            self.assertIn(hook, self.app)
        self.assertGreaterEqual(self.app.count("zineHook('renderPipelineAlbum');"), 4)
        self.assertIn("zineHook('renderPipelineLanes');", self.app.split("function libraryShow(name)")[1].split("function closeLibraryStreams")[0])
        for fn in ("renderPipelineLanes", "renderPipelineAlbum", "renderPipelineArtist", "renderPipelineAcquisitions"):
            body = self.pipe_js.split("function %s(" % fn)[1].split("\nfunction ")[0]
            self.assertTrue("pipelineWide()" in body or "pipelineActive()" in body or "pipelineWide" in body, fn)

    def test_p2b_containers_are_hidden_by_default(self):
        for markup in (
            '<section id="pipelineLanes" class="pipeline-lanes" aria-labelledby="pipelineLanesHeading" hidden>',
            '<div id="pipelineStages" class="pipeline-stages" hidden></div>',
            '<div id="pipelineArtistQueue" class="pipeline-drop" role="group" aria-label="Queued" hidden>',
            '<div id="pipelineAcq" class="pipeline-acq" aria-labelledby="pipelineAcqHeading" hidden>',
            'id="pipelineAcqStatus" class="pipeline-toast" role="status"',
            'id="pipelineAcqCols"',
        ):
            self.assertIn(markup, self.html, markup)

    def test_the_default_library_and_acquisition_lists_are_hidden_only_in_this_layout(self):
        self.assertIn(':root[data-layout="pipeline"] #libraryBrowse > .library-toolbar', self.pipe)
        self.assertIn(':root[data-layout="pipeline"] #libraryBrowse > .zine-index', self.pipe)
        self.assertIn(':root[data-layout="pipeline"] #acquisitionCards { display: none; }', self.pipe)

    def test_acquisition_retry_and_dismiss_are_proxies_for_the_real_rows(self):
        acq = self.pipe_js.split("function pipelineProxyButton")[1].split("function pipelineAcqCard")[0]
        self.assertIn("pipelineRealRow(acquisitionRowKey(job))", acq)
        self.assertIn("control.click();", acq)
        self.assertNotIn("sendJSON(", acq)
        self.assertNotIn("fetch(", acq)
        self.assertIn("pipelineProxyButton('Retry', 'retry-acquisition', job)", self.pipe_js)
        self.assertIn("pipelineProxyButton('Dismiss', 'dismiss-album', job)", self.pipe_js)

    def test_failed_requests_are_not_in_the_dashboard_downloading_column(self):
        column = self.pipe_js.split("function pipelineJobColumn")[1].split("function renderPipelineBoard")[0]
        self.assertIn("if (acquisitionStatusInfo(job.status).tone === 'error') return null;", column)
        self.assertNotIn("tone === 'error') return 'downloading'", column)

    def test_stage_tracker_states_are_words_and_a_position(self):
        self.assertIn("const PIPELINE_STAGE_WORDS = {done: 'Done', current: 'Now', todo: 'To do'};", self.pipe_js)
        self.assertIn("const PIPELINE_STAGES = ['Recommended', 'Saved', 'Queued', 'Downloaded', 'In library'];", self.pipe_js)
        self.assertIn("'Step ' + (index + 1) + ' of ' + PIPELINE_STAGES.length", self.pipe_js)
        self.assertIn("item.setAttribute('aria-current', 'step')", self.pipe_js)

    def test_stage_buttons_run_the_real_save_and_get_controls(self):
        self.assertIn("createSaveButton(artist, name, metadata, 'pipeline_album')", self.pipe_js)
        self.assertIn("get.addEventListener('click', () => getControl.click());", self.pipe_js)
        self.assertIn("$('albumAction').querySelector('.get-album')", self.pipe_js)

    def test_artist_drop_runs_the_dropped_rows_own_get(self):
        drop = self.pipe_js.split("function pipelineWireArtistStrip")[1].split("/* ----")[0]
        self.assertIn("pipelineDragged.querySelector('.get-album')", drop)
        self.assertIn("get.click();", drop)
        self.assertNotIn("sendJSON", drop)
        self.assertIn("'Missing (drag to Queued)'", self.pipe_js)

    def test_genre_lanes_load_when_first_seen_and_reuse_the_genre_endpoint(self):
        lane = self.pipe_js.split("async function pipelineLoadLane")[1].split("/* ----")[0]
        self.assertIn("pipelineLaneObserver.unobserve(entry.target);", self.pipe_js)
        self.assertIn("requestJSON('/api/genres/' + encodeURIComponent(lane.dataset.tag))", lane)
        self.assertIn("pipelineTile({...item, owned: Boolean(item.owned)}, {listName: 'library_lane', genre: lane.dataset.name})", lane)
        # A failed lane is not re-observed: that would retry in a loop while it stays on screen.
        self.assertNotIn("observe(lane)", lane.split("catch")[1])

    def test_library_filters_are_genre_and_year_and_quality_is_disabled(self):
        self.assertIn('id="pipelineFilterGenre"', self.html)
        self.assertIn('id="pipelineFilterYear"', self.html)
        self.assertIn('id="pipelineFilterQuality" disabled', self.html)
        self.assertIn("$(id).addEventListener('change', pipelineApplyLaneFilters)", self.pipe_js)
        self.assertIn("tile.hidden = Boolean(year) && tile.dataset.year !== year;", self.pipe_js)

    def test_p2b_new_rules_are_scoped_and_keep_hidden_elements_hidden(self):
        for selector in (".pipeline-lanes[hidden]", ".pipeline-stages[hidden]", ".pipeline-drop[hidden]", "#pipelineAcq[hidden]"):
            self.assertIn(':root[data-layout="pipeline"] ' + selector, self.pipe, selector)

    def test_p2b_focus_is_visible_on_every_new_control(self):
        self.assertIn(":focus-visible", self.pipe)
        self.assertIn("outline: 3px solid var(--focus)", self.pipe)

    def test_reduced_motion_removes_movement(self):
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.pipe)
        self.assertIn("transform: none !important;", self.pipe)


if __name__ == "__main__":
    unittest.main()
