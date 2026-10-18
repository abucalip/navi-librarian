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
        self.assertIn("card.remove();", render)
        self.assertIn("dismiss.disabled = false;", render)
        self.assertIn("status.textContent = error.message;", render)
        self.assertLess(render.index("await sendJSON('/api/acquisitions/dismiss'"), render.index("card.remove();"))
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
        self.assertIn("stroke-dashoffset: 1;", self.css)

    def test_working_state_travels_an_accent_arc(self):
        self.assertIn(
            "stroke: var(--accent); stroke-dasharray: 15.8 56.46; "
            "animation: get-arc-travel 1.15s linear infinite;",
            self.css,
        )
        self.assertIn("@keyframes get-arc-travel", self.css)

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
            ".get-album.requested .get-album-tick { animation: none; stroke-dashoffset: 0; }",
            self.css,
        )


if __name__ == "__main__":
    unittest.main()
