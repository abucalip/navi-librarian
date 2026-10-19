"""Regression contracts for the browser-side Get and acquisition Dismiss flows.

These tests intentionally avoid a browser and never call a real acquisition API.
The separate cleanup tests exercise the production filesystem safety boundary.
"""
import re
import unittest
from pathlib import Path


APP_JS = Path(__file__).resolve().parents[1] / "static" / "app.js"


def function_source(source, signature, next_signature):
    start = source.index(signature)
    end = source.index(next_signature, start)
    return source[start:end]


class AcquisitionUIRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = APP_JS.read_text(encoding="utf-8")

    def test_get_stays_on_current_page_and_posts_once_per_click(self):
        get_button = function_source(
            self.source,
            "function createGetButton(",
            "function setGetButtonState(",
        )
        request = function_source(
            self.source,
            "async function searchAlbum(",
            "function reportAcquisitionOutcome(",
        )

        self.assertIn("button.addEventListener('click', () => searchAlbum(artist, album, metadata, button))", get_button)
        self.assertIn("if (button && button.disabled && !button.classList.contains('is-failed')) return;", request)
        self.assertEqual(request.count("sendJSON('/api/acquire', 'POST'"), 1)
        self.assertNotRegex(request, r"\b(?:showPage|location\.(?:assign|href)|history\.pushState)\s*\(")

    def test_get_has_pending_requested_and_retryable_failure_transitions(self):
        states = function_source(
            self.source,
            "function setGetButtonState(",
            "async function searchAlbum(",
        )
        request = function_source(
            self.source,
            "async function searchAlbum(",
            "function reportAcquisitionOutcome(",
        )

        self.assertIn("button.disabled = true;", states)
        self.assertIn("button.classList.add('is-pending');", states)
        self.assertIn("button.classList.add('requested');", states)
        self.assertIn("button.disabled = false;", states)
        self.assertIn("button.classList.add('is-failed');", states)
        # The word is no longer written to the button's text node: the transient states are carried
        # by the icon slot, and only the idle state keeps a label. The icon slots themselves are
        # pinned by AsyncGetButtonTests, so this is a move of the assertion, not a weakening.
        self.assertIn("setGetButtonLabel(button, 'get');", states)
        self.assertLess(request.index("setGetButtonState(button, 'pending'"), request.index("await sendJSON('/api/acquire'"))
        self.assertIn("data.ok === false", request)
        self.assertIn("setGetButtonState(button, 'failed'", request)
        self.assertIn("setGetButtonState(button, 'requested'", request)
        self.assertIn("catch (error)", request)
        self.assertIn("reportAcquisitionOutcome(error.message, 'error')", request)

    def test_every_non_dismissed_acquisition_card_has_dismiss_and_only_removes_on_success(self):
        render = function_source(
            self.source,
            "function renderAcquisitions(",
            "const ACTIVE_DOWNLOAD_STATUSES",
        )

        self.assertIn("if (job.status !== 'dismissed')", render)
        self.assertIn("dismiss.textContent = 'Dismiss';", render)
        self.assertIn("await sendJSON('/api/acquisitions/dismiss', 'POST'", render)
        # Phase 5 (status rows): the record is a row, so the removal targets `row`. Only the element name
        # changed; the success-only removal and its ordering are asserted exactly as before.
        self.assertIn("row.remove();", render)
        self.assertIn("dismiss.disabled = false;", render)
        self.assertIn("status.textContent = error.message;", render)
        self.assertLess(render.index("await sendJSON('/api/acquisitions/dismiss'"), render.index("row.remove();"))
        self.assertLess(render.index("catch (error)", render.index("await sendJSON('/api/acquisitions/dismiss'")), render.index("dismiss.disabled = false;", render.index("await sendJSON('/api/acquisitions/dismiss'")))

    def test_dismiss_is_not_limited_to_a_single_acquisition_status(self):
        render = function_source(
            self.source,
            "function renderAcquisitions(",
            "const ACTIVE_DOWNLOAD_STATUSES",
        )
        dismiss_block = render[render.index("const dismiss = document.createElement('button');"):render.index("actions.append(dismiss);")]

        self.assertNotRegex(dismiss_block, r"job\.status\s*(?:===|!==|==|!=)")
        self.assertIn("if (job.status !== 'dismissed')", render)


class AcquisitionStatusRowTests(unittest.TestCase):
    """Phase 5: acquisition jobs render as status rows (DESIGN_SYSTEM.md 9.5, 9.6, 11)."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = (APP_JS.parent / "app.css").read_text(encoding="utf-8")
        cls.html = (APP_JS.parent.parent / "app" / "templates" / "index.html").read_text(encoding="utf-8")

    def test_every_status_in_the_server_vocabulary_has_a_glyph_and_a_label(self):
        table = function_source(self.js, "const ACQUISITION_STATUS_TABLE = {", "function acquisitionStatusInfo(")
        for status in ("searching", "requested", "queued", "downloading", "download_complete_waiting_for_folder",
                       "importing", "imported", "dismissed", "queue_uncertain", "recovery_started", "monitoring",
                       "no_matches", "queue_failed", "settings_required", "slskd_error"):
            self.assertRegex(table, rf"\n\s+{status}: \{{glyph: '[^']+', label: '[^']+', tone: '[a-z]+'\}}")

    def test_an_unknown_status_still_renders_a_glyph_and_a_label(self):
        info = function_source(self.js, "function acquisitionStatusInfo(", "// Skeleton rows are shown only")
        self.assertIn("hasOwnProperty.call(ACQUISITION_STATUS_TABLE, key)", info)
        self.assertIn("glyph: '•'", info)
        self.assertIn("'unknown status'", info)

    def test_status_is_never_carried_by_colour_alone(self):
        render = function_source(self.js, "function renderAcquisitions(", "const ACTIVE_DOWNLOAD_STATUSES")
        self.assertIn("glyph.setAttribute('aria-hidden', 'true');", render)
        self.assertIn("statusLabel.textContent = info.label;", render)
        self.assertIn("statusLine.append(glyph, statusLabel);", render)

    def test_progress_is_a_progressbar_scaled_with_transform_only(self):
        render = function_source(self.js, "function renderAcquisitions(", "const ACTIVE_DOWNLOAD_STATUSES")
        self.assertIn("meter.setAttribute('role', 'progressbar');", render)
        self.assertIn("meter.setAttribute('aria-valuenow', String(Math.round(percent)));", render)
        self.assertIn("fill.style.setProperty('--progress', String(percent / 100));", render)
        self.assertNotIn("progress-ring", self.js)
        self.assertNotIn("conic-gradient", self.css.split("/* Acquisition status rows")[1].split("/* Ranked rows")[0])
        self.assertIn("transform: scaleX(var(--progress, 0));", self.css)
        fill = self.css[self.css.index(".acq-progress-fill {"):self.css.index("}", self.css.index(".acq-progress-fill {"))]
        self.assertIn("transition: transform", fill)
        self.assertNotRegex(fill, r"\b(?:width|height|left)\s*:")

    def test_progress_without_a_percentage_says_so(self):
        render = function_source(self.js, "function renderAcquisitions(", "const ACTIVE_DOWNLOAD_STATUSES")
        self.assertIn("meter.setAttribute('aria-valuetext', 'Progress unavailable');", render)

    def test_the_list_is_not_a_card_grid_and_numerals_are_not_used(self):
        self.assertIn('id="acquisitionCards" class="acq-list"', self.html)
        render = function_source(self.js, "function renderAcquisitions(", "const ACTIVE_DOWNLOAD_STATUSES")
        self.assertNotIn("rank-numeral", render)
        self.assertIn("row.dataset.status = String(job.status || 'unknown');", render)

    def test_status_rows_open_the_album_dialog_and_still_use_the_shared_click_handler(self):
        self.assertIn(".acq-row[data-album-title]", self.js)
        render = function_source(self.js, "function renderAcquisitions(", "const ACTIVE_DOWNLOAD_STATUSES")
        self.assertIn("makeAlbumCardInteractive(row, artist, album, details, true);", render)

    def test_loading_shows_placeholder_rows_only_while_the_list_is_empty(self):
        skeleton = function_source(self.js, "function showAcquisitionSkeleton()", "function renderAcquisitions(")
        self.assertIn("if (target.children.length) return;", skeleton)
        self.assertIn("row.setAttribute('aria-hidden', 'true');", skeleton)
        load = function_source(self.js, "async function loadAcquisitions()", "refreshActiveDownloadBadge();")
        self.assertIn("showAcquisitionSkeleton();", load)
        self.assertIn("querySelector('.is-skeleton')) $('acquisitionCards').replaceChildren();", load)

    def test_placeholder_rows_pulse_only_and_reduced_motion_stops_them(self):
        self.assertIn(".acq-row.is-skeleton { cursor: default; animation: skeleton-pulse 1.4s ease-in-out infinite; }", self.css)
        reduced = self.css[self.css.index("@media (prefers-reduced-motion: reduce) {\n  .acq-progress-fill"):]
        self.assertIn(".acq-row.is-skeleton { animation: none; }", reduced)

    def test_the_live_stream_and_reconnect_path_are_unchanged(self):
        stream = function_source(self.js, "let acquisitionStream = null;", "function stopAcquisitionStream()")
        self.assertIn("new EventSource('/api/acquisitions/stream')", stream)
        self.assertIn("Reconnecting to live download updates…", stream)


class AsyncGetButtonTests(unittest.TestCase):
    """The Get button's async state machine, drawn in an icon slot rather than written as a word.

    The button is a 44-58px circle in three slots, so "requested" cannot be its visible label;
    the transient states are drawn, and the accessible name carries them for assistive tech.
    """

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = (APP_JS.parent / "app.css").read_text(encoding="utf-8")

    def test_the_button_carries_an_icon_slot_and_a_label_element(self):
        build = function_source(self.js, "const GET_BUTTON_ICON =", "function decorateGetButton(button) {")
        for glyph in ('class="get-album-glyph"', 'class="get-album-arc"', 'class="get-album-tick"',
                      'class="get-album-arrow"', 'class="get-album-arrow-head"'):
            self.assertIn(glyph, build)
        # Decorative, so it stays out of the accessible tree.
        self.assertIn('aria-hidden="true"', build)
        self.assertIn('focusable="false"', build)
        decorate = function_source(self.js, "function decorateGetButton(button) {", "function setGetButtonLabel(")
        self.assertIn("label.className = 'get-album-label';", decorate)
        # The existing word moves into the label element, so the idle face is unchanged.
        self.assertIn("label.textContent = (button.textContent || '').trim() || 'get';", decorate)

    def test_only_the_tick_is_normalised_with_pathLength(self):
        # The arc's dash pattern is written in real user units, so a pathLength on it would rescale
        # the dash and change the arc length the component specifies as 15.8 / 56.6.
        build = function_source(self.js, "const GET_BUTTON_ICON =", "function decorateGetButton(button) {")
        arc = build[build.index("get-album-arc"):build.index("get-album-tick")]
        self.assertNotIn("pathLength", arc)
        tick = build[build.index("get-album-tick"):build.index("get-album-arrow")]
        self.assertIn('pathLength="1"', tick)
        self.assertIn("stroke-dasharray: 15.8 56.46;", self.css)
        # Phase 7 motion pass (DESIGN_SYSTEM.md 11): the tick enters with transform and opacity, not a
        # dash offset, so the dash-draw keyframes are gone.
        self.assertNotIn("stroke-dashoffset", self.css)
        self.assertIn("animation: get-tick-in var(--dur) var(--ease-out) both;", self.css)

    def test_working_state_travels_an_accent_arc(self):
        self.assertIn(
            "stroke: var(--accent); stroke-dasharray: 15.8 56.46; transform-box: view-box; "
            "transform-origin: 22px 22px; animation: get-arc-travel 1.15s linear infinite;",
            self.css,
        )
        self.assertIn("@keyframes get-arc-travel { to { transform: rotate(360deg); } }", self.css)

    def test_requested_state_is_an_accent_fill_with_a_drawn_tick(self):
        requested = function_source(self.css, ".get-album.requested {", "/* Failed:")
        self.assertIn("background: var(--accent);", requested)
        self.assertIn("color: var(--on-accent);", requested)
        # The red fill this replaced is gone: attention colour is not the confirmed state, and it
        # also carried the dark glow the design detector flags.
        self.assertNotIn("--red", requested)
        self.assertIn(".get-album.requested .get-album-tick {", self.css)

    def test_requested_state_is_held_and_never_reverts_to_idle(self):
        # The reference component returns to idle after DONE ms. Doing that here would let a second
        # click request the same album twice, so only a server answer changes the state.
        request = function_source(self.js, "async function searchAlbum(", "function reportAcquisitionOutcome(")
        self.assertIn("setGetButtonState(button, 'requested', artist, album);", request)
        self.assertNotIn("setTimeout", request)
        self.assertNotIn("'idle'", request)

    def test_failure_state_draws_a_retry_arrow_and_stays_usable(self):
        self.assertIn(
            ".get-album.is-failed .get-album-arrow, .get-album.is-failed .get-album-arrow-head "
            "{ opacity: 1; }",
            self.css,
        )
        states = function_source(
            self.js, "function setGetButtonState(button, state, artist, album) {", "const acquisitionToasts"
        )
        failed = states[states.index("state === 'failed'"):states.index("} else {")]
        self.assertIn("button.disabled = false;", failed)

    def test_only_the_idle_state_keeps_a_word(self):
        states = function_source(
            self.js, "function setGetButtonState(button, state, artist, album) {", "const acquisitionToasts"
        )
        self.assertEqual(states.count("setGetButtonLabel(button, '');"), 3)
        self.assertIn("setGetButtonLabel(button, 'get');", states)

    def test_the_accessible_name_carries_every_state(self):
        # With no visible word in the transient states, the name is the accessible channel. Without
        # this an icon-only face would be an unlabelled button.
        states = function_source(
            self.js, "function setGetButtonState(button, state, artist, album) {", "const acquisitionToasts"
        )
        self.assertIn("'Requesting '", states)
        self.assertIn("'Acquisition requested'", states)
        self.assertIn("'Request failed. Try again'", states)
        self.assertIn("button.setAttribute('aria-label', button.title);", states)
        self.assertIn("button.setAttribute('aria-busy', 'true');", states)

    def test_reduced_motion_keeps_the_state_without_the_motion(self):
        self.assertIn(".get-album.is-pending .get-album-arc { animation: none; }", self.css)
        self.assertIn(
            ".get-album.requested .get-album-tick { animation: none; opacity: 1; transform: none; }",
            self.css,
        )


if __name__ == "__main__":
    unittest.main()
