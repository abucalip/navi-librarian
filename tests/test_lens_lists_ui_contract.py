"""Source contracts for the Daily lists page (Engine 2, Phase 4, slice 4).

The page shows the stored lens lists from /api/discovery/<lens> and reuses the shared Discover
row. These tests read the template and script as source. They never open a browser, so they do
not replace the manual checklist in docs/LOCAL_UI_TESTING.md.
"""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "app" / "templates" / "index.html"
APP_JS = ROOT / "static" / "app.js"
ICONS_SVG = ROOT / "static" / "icons.svg"


class LensListsUiContractTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.icons = ICONS_SVG.read_text(encoding="utf-8")

    def test_page_and_its_status_and_list_containers_exist(self):
        self.assertIn('<section id="lensLists" class="page hidden" aria-labelledby="lensListsHeading">', self.html)
        self.assertIn('id="lensListsStatus" class="status-line" aria-live="polite"', self.html)
        self.assertIn('id="lensListsCards" class="ranked-list"', self.html)

    def test_one_lens_button_per_stored_lens_with_pressed_state(self):
        for lens in ("repeated_tracks", "deep_cuts", "obsessions"):
            self.assertIn(f'data-lens="{lens}"', self.html)
        self.assertIn('role="group" aria-label="Lens"', self.html)
        self.assertIn('data-lens="repeated_tracks" aria-pressed="true"', self.html)
        # The server lens names must match the list the page offers.
        self.assertIn("LENS_LIST_ORDER = (REPEATED_TRACKS, DEEP_CUTS, OBSESSIONS)", (
            ROOT / "discovery" / "lens_lists.py").read_text(encoding="utf-8"))

    def test_nav_entry_is_reachable_on_desktop_and_in_the_phone_more_panel(self):
        self.assertIn('class="nav-overflow" data-page="lensLists"', self.html)
        self.assertIn('<button type="button" data-page="lensLists" title="Daily lists">', self.html)
        self.assertIn("const NAV_MORE_PAGES = ['lensLists', 'classics', 'artistDeepDive'];", self.js)

    def test_phone_bar_keeps_its_five_in_bar_destinations(self):
        in_bar = self.html[self.html.index('<nav'):self.html.index('id="navMoreButton"')]
        self.assertNotIn('data-page="lensLists"', in_bar.split('class="nav-overflow"')[0])

    def test_nav_icon_is_defined_in_the_sprite(self):
        self.assertIn('href="/static/icons.svg#list-music"', self.html)
        self.assertIn('<symbol id="list-music"', self.icons)

    def test_page_loads_the_selected_lens_on_first_visit(self):
        self.assertIn("else if (name === 'lensLists') loadLensList(activeLens);", self.js)

    def test_requests_use_the_lens_endpoint_and_a_fresh_nonce(self):
        start = self.js.index("async function loadLensList(")
        body = self.js[start:self.js.index("document.querySelectorAll('[data-lens]')", start)]
        self.assertIn("requestJSON(`/api/discovery/${name}?count=10&nonce=${Date.now()}`)", body)

    def test_stale_responses_cannot_overwrite_the_current_lens(self):
        start = self.js.index("async function loadLensList(")
        body = self.js[start:self.js.index("document.querySelectorAll('[data-lens]')", start)]
        self.assertGreaterEqual(body.count("if (requestId !== lensRequestId) return;"), 2)

    def test_disabled_and_empty_responses_are_status_text_not_errors(self):
        start = self.js.index("async function loadLensList(")
        body = self.js[start:self.js.index("document.querySelectorAll('[data-lens]')", start)]
        self.assertIn("data.message || label + ' has no albums today.'", body)
        self.assertIn("setStatusState(status, items.length ? 'progress' : 'empty');", body)

    def test_rows_reuse_the_shared_discover_row_and_add_only_seed_and_listeners(self):
        start = self.js.index("function buildLensRow(")
        body = self.js[start:self.js.index("async function loadLensList(", start)]
        self.assertIn("return buildRecommendationRow(item, item.rank, {", body)
        self.assertIn("'Seed tag: ' + item.seed_tag", body)
        self.assertIn("' listeners'", body)
        # Lens lists have no save list, so the row must not be given one.
        self.assertNotIn("listName", body)

    def test_lens_text_is_never_written_as_html(self):
        start = self.js.index("const LENS_LISTS = {")
        body = self.js[start:self.js.index("document.querySelectorAll('[data-lens]')", start)]
        self.assertNotIn("innerHTML", body)
        self.assertNotIn("insertAdjacentHTML", body)

    def test_dismissing_a_lens_row_reloads_the_lens_not_a_discover_view(self):
        start = self.js.index("async function commitDismiss(")
        body = self.js[start:self.js.index("function undoDismiss(", start)]
        self.assertIn("if (entry.listName === 'lens_lists') await loadLensList(activeLens);", body)
        self.assertIn("if (entry.listName === 'lens_lists') {", body)

    def test_the_selected_lens_has_a_visible_mark_besides_aria_pressed(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        self.assertIn('.controls button[aria-pressed="true"] { color: var(--text); box-shadow: inset 0 -3px var(--accent); }', css)

    def test_disabled_state_is_neutral_copy_without_the_config_key(self):
        start = self.js.index("async function loadLensList(")
        body = self.js[start:self.js.index("document.querySelectorAll('[data-lens]')", start)]
        self.assertIn("'Daily lists are turned off in Settings.'", body)
        self.assertNotIn("engine2_lens_lists_enabled", body)


if __name__ == "__main__":
    unittest.main()
