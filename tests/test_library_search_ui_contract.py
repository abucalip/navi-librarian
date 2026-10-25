"""Source-contract regressions for the top-bar search and the library page (SEARCH_CONTRACT P1 UI).

Behavior was exercised in a DOM harness outside the repository. These tests keep the
structure, the textContent-only rendering and the stream lifecycle from being removed.
"""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "app" / "templates" / "index.html"
APP_JS = ROOT / "static" / "app.js"
APP_CSS = ROOT / "static" / "app.css"


class LibrarySearchUIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = APP_CSS.read_text(encoding="utf-8")
        cls.new_js = cls.js[cls.js.index("// ---- Library and global search (SEARCH_CONTRACT P1)"):]

    def test_top_bar_search_is_a_labelled_search_landmark_with_a_results_region(self):
        self.assertIn('<form id="globalSearch" class="global-search" role="search"', self.html)
        self.assertIn('<label for="globalSearchInput" class="sr-only">Search your library</label>', self.html)
        self.assertIn('aria-controls="globalSearchResults" aria-expanded="false"', self.html)
        self.assertIn('<div id="globalSearchResults" class="search-results" role="region"', self.html)
        self.assertIn('id="globalSearchStatus" class="status-line" aria-live="polite"', self.html)

    def test_library_is_reachable_from_the_header_menu_and_has_labelled_controls(self):
        self.assertIn('<button type="button" data-page="library">Library</button>', self.html)
        self.assertIn('<section id="library" class="page hidden" aria-labelledby="libraryHeading">', self.html)
        self.assertIn('<label for="libraryFilter">Filter artists</label>', self.html)
        self.assertIn('<label for="librarySort">Sort by</label>', self.html)
        self.assertIn('<h3 id="artistDetailHeading" tabindex="-1"></h3>', self.html)

    def test_router_marks_library_current_and_loads_it_on_each_visit(self):
        self.assertIn("name === 'saved' || name === 'library'", self.js)
        self.assertIn("if (name === 'library') loadLibrary({reset: true});", self.js)

    def test_search_uses_the_sse_endpoint_and_closes_the_stream_on_done_and_error(self):
        self.assertIn("new EventSource('/api/search?'", self.new_js)
        self.assertIn("source.addEventListener('done'", self.new_js)
        self.assertIn("source.addEventListener('error'", self.new_js)
        self.assertIn("const message = event.data", self.new_js)
        self.assertIn("const isCurrent = () => seq === globalSearchSeq;", self.new_js)
        self.assertIn("const finish = () => {", self.new_js)

    def test_new_script_never_writes_html_from_data(self):
        self.assertNotIn("innerHTML", self.new_js)
        self.assertNotIn("insertAdjacentHTML", self.new_js)
        self.assertNotIn("outerHTML", self.new_js)

    def test_artist_view_is_addressed_by_key_and_navidrome_id(self):
        self.assertIn("'/api/artists/' + encodeURIComponent(key) + '?' + params", self.new_js)
        self.assertIn("const params = new URLSearchParams({id});", self.new_js)

    def test_index_states_are_never_shown_as_an_empty_library(self):
        self.assertIn("if (data.index_state === 'building' || data.index_state === 'unavailable') {", self.new_js)
        self.assertIn("'Your library is still being indexed. Try again in a moment.'", self.new_js)
        self.assertIn("'Your library could not be indexed right now.'", self.new_js)

    def test_escape_and_outside_click_close_the_results_panel(self):
        self.assertIn("if (event.key === 'Escape') {", self.new_js)
        self.assertIn("if (!$('globalSearch').contains(event.target)) closeGlobalSearch();", self.new_js)

    def test_styles_hide_panels_that_use_the_hidden_attribute_and_stack_search_on_phones(self):
        self.assertIn(".search-results[hidden], #libraryDetailView[hidden], #libraryListView[hidden], #libraryMore[hidden] { display: none; }", self.css)
        self.assertIn("header .global-search { order: 3; flex: 1 0 100%; margin-left: 0; }", self.css)
        self.assertIn("main { margin: 136px 14px 0;", self.css)


if __name__ == "__main__":
    unittest.main()
