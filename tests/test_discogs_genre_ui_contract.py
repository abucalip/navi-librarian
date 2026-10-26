"""Source-contract regressions for the Discogs settings tab and the genre view (SEARCH_CONTRACT P4 UI).

These read the shipped template, stylesheet and script as source and never open a browser.
Browser checks in docs/LOCAL_UI_TESTING.md still apply.
"""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "app.css").read_text(encoding="utf-8")


class DiscogsSettingsUITests(unittest.TestCase):
    def test_tab_and_panel_follow_the_tabs_pattern(self):
        self.assertIn('id="tabDiscogs" class="settings-tab" role="tab" aria-selected="false" aria-controls="settingsDiscogs" data-settings-tab="discogs"', HTML)
        self.assertIn('id="settingsDiscogs" class="settings-tab-panel" role="tabpanel" aria-labelledby="tabDiscogs" hidden', HTML)
        self.assertIn("discogs: 'settingsDiscogs'", JS)

    def test_token_field_is_a_password_input_and_never_filled_from_the_server(self):
        field = HTML[HTML.index('<input id="discogsToken"'):]
        field = field[:field.index(">")]
        self.assertIn('type="password"', field)
        self.assertIn('autocomplete="new-password"', field)
        self.assertNotIn("value=", field)
        load = JS[JS.index("async function loadDiscogsSettings"):JS.index("// An empty token clears")]
        self.assertIn("$('discogsToken').value = '';", load)
        self.assertNotIn(".token", load)

    def test_status_is_a_polite_live_region_and_attribution_is_shown(self):
        self.assertIn('id="discogsStatus" class="status-line" aria-live="polite"', HTML)
        self.assertIn("Data provided by Discogs", HTML)

    def test_save_never_sends_an_empty_token_and_remove_sends_one_on_purpose(self):
        self.assertIn("saveDiscogsToken(token);", JS)
        self.assertIn("$('removeDiscogs').addEventListener('click', () => saveDiscogsToken(''));", JS)
        self.assertRegex(JS, r"if \(!token\) \{\s*\$\('discogsStatus'\)")

    def test_test_button_uses_the_shared_helper_and_reads_the_error_field(self):
        self.assertIn("testServiceConnection('/api/settings/discogs/test', 'discogsStatus')", JS)
        self.assertIn("data.message || data.error ||", JS)

    def test_discogs_settings_load_with_the_other_settings(self):
        self.assertIn("loadDiscogsSettings(); }", JS)


class GenreViewUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.genre_js = JS[JS.index("// ---- Genre view (SEARCH_CONTRACT P4) ----"):JS.index("// ---- Wiring ----")]

    def test_markup_has_a_labelled_view_with_a_focusable_heading_and_live_status(self):
        self.assertIn('<div id="libraryGenreView" hidden>', HTML)
        self.assertIn('<h3 id="genreHeading" tabindex="-1"></h3>', HTML)
        self.assertIn('id="genreStatus" class="status-line" aria-live="polite"', HTML)
        self.assertIn('<ul id="genreArtists" class="library-album-list" aria-labelledby="genreArtistsHeading">', HTML)
        self.assertIn('<ul id="genreAlbums" class="library-album-list" aria-labelledby="genreAlbumsHeading">', HTML)

    def test_genre_button_sits_in_the_artist_view_and_starts_hidden(self):
        self.assertIn('id="artistGenre" class="genre-link" hidden', HTML)
        self.assertIn("$('artistGenre').addEventListener('click', () => {", JS)
        self.assertIn("libraryView.genreReturn = 'artist';", JS)
        self.assertIn("openGenre($('artistGenre').dataset.genre);", JS)

    def test_data_is_written_with_text_only(self):
        self.assertNotIn("innerHTML", self.genre_js)
        self.assertNotIn("insertAdjacentHTML", self.genre_js)

    def test_stale_responses_are_dropped_and_the_tag_is_encoded(self):
        self.assertIn("if (seq !== view.genreSeq) return;", self.genre_js)
        self.assertIn("'/api/genres/' + encodeURIComponent(tag)", self.genre_js)

    def test_attribution_is_shown_from_the_server_field_on_each_item(self):
        self.assertIn("if (item.attribution) addTextElement(row, 'span', 'library-album-detail', item.attribution);", self.genre_js)

    def test_owned_artists_open_their_artist_view_and_others_are_text_only(self):
        self.assertIn("if (item.owned && type === 'artists') {", self.genre_js)
        self.assertIn("openArtistDetail(item.id, item.key, button, null, libraryView.genreTag);", self.genre_js)

    def test_incomplete_and_empty_states_are_distinct(self):
        self.assertIn("Some sources did not answer, so this list may be incomplete", self.genre_js)
        self.assertIn("'Nothing found for this genre.'", self.genre_js)
        self.assertIn("'This genre could not be loaded. Try again.'", self.genre_js)

    def test_back_returns_focus_to_the_genre_button_or_the_artist_heading(self):
        self.assertIn("libraryView.genreReturn = 'artist';", JS)
        self.assertIn("if (!button.hidden) button.focus();", self.genre_js)
        self.assertIn("$('genreBack').addEventListener('click', closeGenre);", JS)

    def test_an_artist_opened_from_a_genre_returns_to_that_genre(self):
        self.assertIn("openArtistDetail(item.id, item.key, button, null, libraryView.genreTag);", self.genre_js)
        self.assertIn("view.fromGenre = fromGenre;", JS)
        close = JS[JS.index("function closeArtistDetail()"):JS.index("// ---- Genre view")]
        self.assertIn("if (libraryView.fromGenre) {", close)
        self.assertIn("openGenre(tag);", close)
        # The list view stays hidden on that path, so focus is never sent to a hidden return button.
        self.assertLess(close.index("openGenre(tag);"), close.index("libraryListView"))
        self.assertLess(close.index("return;"), close.index("libraryListView"))

    def test_other_ways_of_opening_an_artist_clear_the_genre_return(self):
        self.assertIn("async function openArtistDetail(id, key, returnFocus, artworkUrl, fromGenre = '') {", JS)

    def test_search_lists_genres_and_a_genre_result_opens_the_genre_view(self):
        self.assertIn("['genre', 'Genres']];", JS)
        self.assertIn("genre: 'Genre'}", JS)
        self.assertIn("openGenreFromSearch(item)", JS)
        opener = JS[JS.index("function openGenreFromSearch"):JS.index("// ---- Library list ----")]
        self.assertIn("navigateTo('library');", opener)
        self.assertIn("openGenre(item.tag);", opener)
        self.assertNotIn("innerHTML", opener)

    def test_back_from_search_genre_returns_to_library_list(self):
        opener = JS[JS.index("function openGenreFromSearch"):JS.index("// ---- Library list ----")]
        self.assertIn("libraryView.genreReturn = 'list';", opener)
        close = JS[JS.index("function closeGenre()"):JS.index("// ---- Wiring ----")]
        self.assertIn("if (libraryView.genreReturn === 'artist')", close)
        self.assertIn("$('libraryListView').hidden = false;", close)
        self.assertIn("$('libraryIntro').hidden = false;", close)
        self.assertIn("$('libraryHeading').focus();", close)

    def test_touch_targets_meet_the_44px_floor(self):
        self.assertRegex(CSS, r"\.genre-link, \.genre-item-link \{ min-height: 44px; \}")


if __name__ == "__main__":
    unittest.main()
