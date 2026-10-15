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
        self.assertIn("button.classList.add('requested');", states)
        self.assertIn("button.textContent = 'requested';", states)
        self.assertIn("button.disabled = false;", states)
        self.assertIn("button.classList.add('is-failed');", states)
        self.assertIn("button.textContent = 'retry';", states)
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


if __name__ == "__main__":
    unittest.main()
