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

    def test_lens_rows_are_a_list_of_list_items(self):
        # Position in the list is announced through the list semantics, so the rank is not lost.
        self.assertIn('id="lensListsCards" class="ranked-list" role="list"', self.html)
        self.assertIn("row.setAttribute('role', 'listitem');", self.js)

    def test_lens_buttons_use_title_case(self):
        self.assertIn('aria-pressed="true">Repeated Tracks</button>', self.html)
        self.assertIn('aria-pressed="false">Deep Cuts</button>', self.html)
        self.assertIn('aria-pressed="false">Obsessions</button>', self.html)

    def test_one_lens_button_per_stored_lens_with_pressed_state(self):
        for lens in ("repeated_tracks", "deep_cuts", "obsessions"):
            self.assertIn(f'data-lens="{lens}"', self.html)
        self.assertIn('role="group" aria-label="Lens"', self.html)
        self.assertIn('data-lens="repeated_tracks" aria-pressed="true"', self.html)
        # The server lens names must match the list the page offers.
        self.assertIn("LENS_LIST_ORDER = (REPEATED_TRACKS, DEEP_CUTS, OBSESSIONS)", (
            ROOT / "discovery" / "lens_lists.py").read_text(encoding="utf-8"))

    def test_daily_lists_is_on_the_phone_bar_and_new_releases_moved_to_more(self):
        # Daily lists is a daily-use list, so it takes a bar slot; New releases moves to More.
        self.assertIn('<button data-page="lensLists" title="Daily picks">', self.html)
        self.assertIn('<button class="nav-overflow" data-page="newReleases"', self.html)
        self.assertIn('<button type="button" data-page="newReleases" title="New releases">', self.html)
        self.assertNotIn('data-page="lensLists" title="Daily picks">Daily picks</button>', self.html)
        self.assertIn("const NAV_MORE_PAGES = ['newReleases', 'classics', 'artistDeepDive'];", self.js)

    def test_icon_sprite_is_well_formed_xml(self):
        # A string search cannot catch a malformed sprite: one bad attribute stops the whole file
        # from parsing, so every icon breaks. Parse it.
        import xml.etree.ElementTree as ET
        root = ET.fromstring(self.icons)
        ids = [node.get("id") for node in root.iter() if node.tag.endswith("symbol")]
        self.assertIn("list-music", ids)
        self.assertIn("library", ids)

    def test_the_album_modal_image_is_not_in_the_markup_without_a_source(self):
        # The detector's broken-image rule: no <img> may ship without a src.
        import re
        self.assertIsNone(re.search(r"<img(?![^>]*\bsrc=)[^>]*>", self.html))
        self.assertIn("const albumArtworkImage = document.createElement('img');", self.js)

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

    def test_lens_rows_offer_save_and_route_its_errors_to_the_lens_status(self):
        self.assertIn("lens_lists: ['lensListsCards','lensListsStatus'],", self.js)

    def test_ranked_rows_have_no_hover_stripe(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        self.assertNotIn(".ranked-row::before", css)
        self.assertNotIn(".ranked-row:hover::before", css)

    def test_rows_reuse_the_shared_discover_row_and_add_only_seed_and_listeners(self):
        start = self.js.index("function buildLensRow(")
        body = self.js[start:self.js.index("async function loadLensList(", start)]
        self.assertIn("const row = buildRecommendationRow(item, item.rank, {", body)
        self.assertIn("'Seed tag: ' + item.seed_tag", body)
        self.assertIn("' listeners'", body)
        self.assertIn("listName: 'lens_lists',", body)

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
        self.assertIn("'Daily picks are turned off in Settings.'", body)
        self.assertNotIn("engine2_lens_lists_enabled", body)


if __name__ == "__main__":
    unittest.main()
