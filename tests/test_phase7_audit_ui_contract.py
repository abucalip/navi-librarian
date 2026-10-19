"""Contracts for the Phase 7 audit fixes (docs/UI_BACKLOG_EXECUTION.md section 24).

Each test pins one fix the audit measured on the rendered pages: 44px targets on the
controls that measured 19 to 43px, the acquisition row not being a button around its own
buttons, and the album modal not showing a broken-image glyph. They read the stylesheet and
script as text, as the other *_ui_contract.py files do.
"""
import unittest
from pathlib import Path


STATIC = Path(__file__).resolve().parents[1] / "static"


class Phase7AuditContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = (STATIC / "app.css").read_text(encoding="utf-8")
        cls.js = (STATIC / "app.js").read_text(encoding="utf-8")

    def test_settings_inputs_meet_the_44px_floor(self):
        self.assertIn(".settings-tab-panel input { display: block; box-sizing: border-box; width: 100%; min-height: 44px;", self.css)
        self.assertNotIn("min-height: 40px; margin-top: 6px;", self.css)

    def test_request_controls_and_discovery_filters_meet_the_44px_floor(self):
        self.assertIn(".controls button, .controls select, .discovery-controls input, .discovery-controls select { min-height: 44px; }", self.css)

    def test_diagnostics_disclosure_meets_the_44px_floor(self):
        self.assertIn("summary { min-height: 44px; display: list-item;", self.css)

    def test_skip_link_meets_the_44px_floor(self):
        self.assertIn(".skip-link { min-height: 44px; }", self.css)

    def test_status_line_uses_the_smallest_type_token(self):
        self.assertIn(".dashboard-picks-status { min-height: 18px; color: var(--text-muted); font-size: var(--text-xs); }", self.css)

    def test_album_articles_are_not_buttons_around_their_own_controls(self):
        self.assertNotIn("card.setAttribute('role', 'button');", self.js)
        # Focus and Enter still open the modal from the focused article.
        self.assertIn(".acq-row[data-album-title]", self.js)
        self.assertIn("event.target.matches('.card[data-album-title], .ranked-row[data-album-title], .acq-row[data-album-title]')", self.js)

    def test_album_modal_artwork_is_hidden_until_a_source_resolves(self):
        self.assertIn("artwork.hidden = true;", self.js)
        self.assertIn("artwork.hidden = false;\n      artwork.src = artworkUrl;", self.js)
        self.assertIn("$('albumModalArtwork').addEventListener('error'", self.js)


if __name__ == "__main__":
    unittest.main()
