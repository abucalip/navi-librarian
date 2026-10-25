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
        # A searchbox has no listbox behind it here, so no combobox ARIA may be claimed.
        search_input = self.html[self.html.index('<input id="globalSearchInput"'):]
        search_input = search_input[:search_input.index(">")]
        self.assertNotIn("aria-expanded", search_input)
        self.assertNotIn("aria-controls", search_input)
        self.assertNotIn("aria-autocomplete", search_input)
        self.assertIn('<div id="globalSearchResults" class="search-results" role="region"', self.html)
        self.assertIn('id="globalSearchStatus" class="status-line" aria-live="polite"', self.html)

    def test_copy_does_not_promise_albums_or_songs_that_do_not_open(self):
        self.assertIn('placeholder="Search your library"', self.html)
        self.assertNotIn("albums and songs", self.html)
        self.assertIn("Select an artist to see their albums.", self.html)

    def test_header_tagline_rules_do_not_reach_the_search_dropdown_paragraphs(self):
        # The dropdown's status and group headings are paragraphs inside the header, so the
        # tagline rules must not match them (they would right-align and hide them on phones).
        self.assertNotIn("\nheader p {", self.css)
        self.assertNotIn(" header p {", self.css)
        self.assertIn(".header-tools > p { margin: 0;", self.css)
        self.assertIn(".header-tools > p { display: none; }", self.css)

    def test_only_buttons_show_the_result_hover_state(self):
        self.assertIn("button.search-item-content:hover", self.css)
        self.assertNotIn(" .search-item-content:hover", self.css.replace("button.search-item-content:hover", ""))

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

    def test_results_stream_into_their_groups_with_a_running_count(self):
        self.assertIn("searchGroupList(item.type).append(buildSearchItem(item));", self.new_js)
        self.assertIn("'Searching… ' + pluralize(shown, 'match', 'matches') + ' so far'", self.new_js)
        self.assertIn("setSearchStatusLive(false);", self.new_js)
        self.assertIn("setSearchStatusLive(true);", self.new_js)
        self.assertIn("if (!SEARCH_GROUPS.some(([type]) => type === item.type)) return;", self.new_js)

    def test_previous_results_are_cleared_only_when_the_new_stream_responds(self):
        capabilities_block = self.new_js[self.new_js.index("source.addEventListener('capabilities'"):]
        capabilities_block = capabilities_block[:capabilities_block.index("});")]
        self.assertIn("groupsEl.replaceChildren();", capabilities_block)
        start_block = self.new_js[self.new_js.index("function startGlobalSearch("):self.new_js.index("source.addEventListener('capabilities'")]
        self.assertNotIn("replaceChildren", start_block)

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

    def test_escape_is_handled_on_the_form_so_it_works_from_results_too(self):
        self.assertIn("$('globalSearch').addEventListener('keydown'", self.new_js)
        self.assertIn("if (event.key === 'Escape' && !$('globalSearchResults').hidden) {", self.new_js)
        self.assertNotIn("$('globalSearchInput').addEventListener('keydown'", self.new_js)

    def test_focus_leaving_the_form_closes_it_but_a_null_target_does_not(self):
        # Safari does not focus buttons on click; a null relatedTarget must not close the panel first.
        self.assertIn("$('globalSearch').addEventListener('focusout'", self.new_js)
        self.assertIn("if (next && !$('globalSearch').contains(next)) closeGlobalSearch();", self.new_js)

    def test_outside_click_closes_the_results_panel(self):
        self.assertIn("if (!$('globalSearch').contains(event.target)) closeGlobalSearch();", self.new_js)

    def test_group_headings_are_paragraphs_so_the_heading_order_has_no_gap(self):
        self.assertIn("addTextElement(section, 'p', 'search-group-heading', SEARCH_GROUPS[rank][1]);", self.new_js)
        self.assertNotIn("'h3', 'search-group-heading'", self.new_js)

    def test_a_failed_append_retries_the_append_not_a_reset(self):
        self.assertIn("showLibraryListMore(true, 'Try again', reset);", self.new_js)
        self.assertIn("loadLibrary({reset: libraryView.retry})", self.new_js)

    def test_styles_hide_panels_that_use_the_hidden_attribute_and_stack_search_on_phones(self):
        self.assertIn(".search-results[hidden], #libraryDetailView[hidden], #libraryListView[hidden], #libraryMore[hidden] { display: none; }", self.css)
        self.assertIn("header .global-search { order: 3; flex: 1 0 100%; margin-left: 0; }", self.css)
        self.assertIn("main { margin: 136px 14px 0;", self.css)


if __name__ == "__main__":
    unittest.main()
