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
        self.assertIn('<label for="globalSearchInput" class="sr-only">Search your library or discover new music</label>', self.html)
        # A searchbox has no listbox behind it here, so no combobox ARIA may be claimed.
        search_input = self.html[self.html.index('<input id="globalSearchInput"'):]
        search_input = search_input[:search_input.index(">")]
        self.assertNotIn("aria-expanded", search_input)
        self.assertNotIn("aria-controls", search_input)
        self.assertNotIn("aria-autocomplete", search_input)
        self.assertIn('<div id="globalSearchResults" class="search-results" role="region"', self.html)
        self.assertIn('id="globalSearchStatus" class="status-line" aria-live="polite"', self.html)

    def test_copy_does_not_promise_albums_or_songs_that_do_not_open(self):
        self.assertIn('placeholder="Search your library or discover new music"', self.html)
        self.assertNotIn("albums and songs", self.html)
        self.assertIn("Select an artist to see their bio, albums and similar artists.", self.html)

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
        self.assertIn('<h2 id="artistDetailHeading" tabindex="-1"></h2>', self.html)

    def test_router_marks_library_current_and_loads_it_on_each_visit(self):
        self.assertIn("name === 'saved' || name === 'library'", self.js)
        self.assertIn("if (name === 'library') { libraryReset(); loadLibrary({reset: true}); }", self.js)
        self.assertRegex(self.html, r'<button data-page="library"[^>]*>.*?</button>\s*<button data-page="acquisitions"')

    def test_search_uses_the_sse_endpoint_and_closes_the_stream_on_done_and_error(self):
        self.assertIn("new EventSource('/api/search?'", self.new_js)
        self.assertIn("source.addEventListener('done'", self.new_js)
        self.assertIn("source.addEventListener('error'", self.new_js)
        self.assertIn("const message = event.data", self.new_js)
        self.assertIn("const isCurrent = () => seq === globalSearchSeq;", self.new_js)
        self.assertIn("const finish = () => {", self.new_js)

    def test_artist_results_show_their_genre_after_the_name_when_there_is_one(self):
        self.assertIn("return item.type === 'artist' && item.genre ? item.name + ' (' + item.genre + ')' : item.name;", self.new_js)
        self.assertIn("addTextElement(text, 'span', 'search-item-name', searchItemName(item));", self.new_js)

    def test_results_stream_into_their_groups_with_a_running_count(self):
        self.assertIn("searchGroupList(item.type).append(buildSearchItem(item));", self.new_js)
        self.assertIn("'Searching… ' + pluralize(shown + external, 'match', 'matches') + ' so far'", self.new_js)
        self.assertIn("setSearchStatusLive(false);", self.new_js)
        self.assertIn("setSearchStatusLive(true);", self.new_js)
        self.assertIn("if (!SEARCH_GROUPS.some(([type]) => type === item.type)) return;", self.new_js)

    def test_previous_results_are_cleared_only_when_the_new_stream_responds(self):
        capabilities_block = self.new_js[self.new_js.index("source.addEventListener('capabilities'"):]
        capabilities_block = capabilities_block[:capabilities_block.index("});")]
        self.assertIn("groupsEl.replaceChildren();", capabilities_block)
        start_block = self.new_js[self.new_js.index("function startGlobalSearch("):self.new_js.index("source.addEventListener('capabilities'")]
        self.assertNotIn("replaceChildren", start_block)

    def test_results_not_in_the_library_have_their_own_group_and_are_not_counted_as_owned(self):
        self.assertIn('<section id="globalSearchExternal" class="search-group"', self.html)
        self.assertIn('<p id="globalSearchExternalHeading" class="search-group-heading">Not in your library</p>', self.html)
        self.assertIn("if (item.owned) {", self.new_js)
        self.assertIn("pluralize(external, 'match', 'matches') + ' not in your library'", self.new_js)
        self.assertNotIn("in your library' + ' not", self.new_js)

    def test_search_panel_shows_two_sections_and_no_provider_names_or_status(self):
        # Direction from the owner: while typing, the panel shows only "In your library" and
        # "Not in your library". Provider names, provider status and popularity never appear.
        self.assertNotIn("globalSearchSources", self.html)
        self.assertNotIn("source.addEventListener('source'", self.new_js)
        self.assertNotIn("renderSourceStatus", self.new_js)
        self.assertNotIn("Some sources did not finish", self.new_js)
        for provider in ("MusicBrainz", "Last.fm", "ListenBrainz", "Discogs"):
            self.assertNotIn(provider, self.new_js[self.new_js.index("function searchItemName"):self.new_js.index("// ---- Library list ----")])

    def test_artists_albums_and_genres_open_their_page_owned_or_not_and_songs_do_not(self):
        self.assertIn("if (item.type === 'artist') return artistTarget(item);", self.new_js)
        self.assertIn("if (item.type === 'album') return albumTarget(item);", self.new_js)
        self.assertIn("const content = target ? document.createElement('button') : document.createElement('div');", self.new_js)

    def test_a_song_opens_the_album_that_holds_it(self):
        self.assertIn("if (item.type === 'song' && item.album) {", self.new_js)
        self.assertIn("id: item.album_id,", self.new_js)

    def test_only_an_owned_item_sends_a_navidrome_id(self):
        self.assertIn("id: owned ? item.id || null : null,", self.new_js)

    def test_new_script_never_writes_html_from_data(self):
        self.assertNotIn("innerHTML", self.new_js)
        self.assertNotIn("insertAdjacentHTML", self.new_js)
        self.assertNotIn("outerHTML", self.new_js)

    def test_artist_view_is_addressed_by_key_and_streams_its_sections(self):
        self.assertIn("new EventSource('/api/artists/' + encodeURIComponent(target.key) + '?' + params)", self.new_js)
        self.assertIn("if (target.id) params.set('id', target.id);", self.new_js)
        self.assertIn("if (target.mbid) params.set('mbid', target.mbid);", self.new_js)

    def test_artist_view_shows_bio_tags_top_songs_owned_missing_and_similar_artists(self):
        for element in ('id="artistBio"', 'id="artistTags"', 'id="artistTopSongs"', 'id="artistOwnedAlbums"',
                        'id="artistMissingAlbums"', 'id="artistSimilar"'):
            self.assertIn(element, self.html)
        for name in ("section.section === 'bio'", "section.section === 'tags'", "section.section === 'top_songs'",
                     "section.section === 'owned_albums'", "section.section === 'missing_albums'", "section.section === 'similar'"):
            self.assertIn(name, self.new_js)

    def test_albums_are_owned_check_or_get_button(self):
        self.assertIn("if (item.owned) return buildOwnedCheck();", self.new_js)
        self.assertIn("return createGetButton(item.artist, item.name, {", self.new_js)
        self.assertIn("setAttribute('aria-label', 'In your library')", self.new_js)
        self.assertIn("color: var(--ok)", self.css)

    def test_owned_and_missing_albums_have_their_own_sections_and_no_toggle(self):
        self.assertNotIn("artistOwnedOnly", self.html)
        self.assertNotIn("ownedOnly", self.new_js)
        self.assertIn("art.append(buildOwnedCheck());", self.new_js)
        self.assertIn("buildAlbumRow({...item, showListens: true})", self.new_js)
        self.assertIn('<section id="artistOwnedSection" aria-labelledby="artistOwnedHeading" hidden>', self.html)

    def test_similar_albums_name_their_artist_in_grey_beside_the_album(self):
        self.assertIn("if (item.showArtist && item.artist) addTextElement(title, 'span', 'album-row-artist', item.artist);", self.new_js)
        self.assertIn("buildAlbumRow({...item, showArtist: true})", self.new_js)
        self.assertRegex(self.css, r"\.album-row-artist \{[^}]*color: var\(--text-muted\)")

    def test_album_page_has_the_panel_sized_get_button_and_the_service_links(self):
        self.assertIn(".album-hero-action .get-album { position: absolute; right: var(--space-3); bottom: var(--space-3); width: 40px; height: 40px;", self.css)
        self.assertIn('<div id="albumPlatformLinks" class="album-platform-links"', self.html)
        for service in ("'Apple Music'", "'Deezer'", "'MusicBrainz'", "'Qobuz'"):
            self.assertIn(service, self.js[self.js.index("function setAlbumPagePlatformLinks"):self.js.index("function fillPlatformLinks")])

    def test_similar_artists_without_a_library_cover_load_a_photo(self):
        self.assertIn("button.append(buildArtistPhoto(item, 300));", self.new_js)
        self.assertIn("'/api/artist-image?' + new URLSearchParams({name: item.name})", self.new_js)

    def test_names_and_tags_on_cards_and_rows_open_library_pages(self):
        self.assertIn("function foldKey(name) {", self.new_js)
        self.assertIn("event.stopPropagation();", self.new_js)
        self.assertIn("openLibraryTarget(target);", self.new_js)
        for call in ("linkAlbumName(title, artist, album || 'Untitled album', item);",
                     "linkArtistName(addTextElement(main, 'p', 'row-artist', ''), artist || 'Unknown artist');",
                     "linkGenres(genreLine, genres);",
                     "linkAlbumName($('albumModalTitle'), artist, album, metadata);",
                     "linkArtistName($('albumModalArtist'), artist);"):
            self.assertIn(call, self.js)
        self.assertIn("button.inline-link {", self.css)

    def test_artist_page_albums_show_their_listen_count_beside_the_name(self):
        self.assertIn("item => buildAlbumRow({...item, showListens: true})", self.new_js)
        self.assertIn("compactCount(item.popularity) + ' listens'", self.new_js)
        self.assertIn(".album-row-listens, .album-row-artist {", self.css)

    def test_artist_albums_without_a_year_get_one_from_the_batch_lookup(self):
        self.assertIn("async function fillMissingYears(ctx) {", self.new_js)
        self.assertIn("sendJSON('/api/album-years', 'POST'", self.new_js)

    def test_album_page_shows_apple_music_notes_with_read_more(self):
        for element in ('id="albumDescription"', 'id="albumDescriptionToggle"', 'id="albumDescriptionLink"'):
            self.assertIn(element, self.html)
        self.assertIn("section.section === 'description'", self.new_js)
        self.assertIn("for (const paragraph of paragraphs) addTextElement(text, 'p', '', paragraph);", self.new_js)
        self.assertIn(".album-description-text.is-collapsed p:not(:first-child) { display: none; }", self.css)
        self.assertIn(".album-head { display: grid; justify-items: center;", self.css)
        self.assertIn("-webkit-line-clamp: 3; overflow: hidden; }\n@media (max-width: 620px) { .album-description-text.is-collapsed p:first-child { -webkit-line-clamp: 6; } }", self.css)

    def test_an_empty_album_status_draws_no_marker(self):
        self.assertIn("setStatus(status, '', 'idle');", self.new_js)
        self.assertIn("#albumStatus:empty { display: none; }", self.css)

    def test_album_view_has_tracklist_and_two_similar_rows(self):
        for element in ('id="albumTracks"', 'id="albumSimilarArtists"', 'id="albumSimilarAlbums"', 'id="albumAction"'):
            self.assertIn(element, self.html)
        self.assertIn("new EventSource('/api/albums/'", self.new_js)

    def test_artist_view_leads_with_artwork_and_steps_the_intro_aside(self):
        self.assertIn('<p id="libraryIntro">', self.html)
        self.assertIn('<div class="artist-hero">', self.html)
        self.assertIn("$('libraryIntro').hidden = name !== 'list';", self.new_js)
        self.assertIn("buildArtwork(sizedArtwork(target.artworkUrl, ARTIST_HERO_PHOTO_SIZE), 'artist-hero-art')", self.new_js)
        self.assertIn("$('libraryHeading').hidden = name === 'artist' || name === 'album';", self.new_js)
        self.assertIn("'/api/artist-image?'", self.new_js)
        self.assertIn("#artistDetailHeading { margin: 0; font: 700 clamp(2.75rem, 8vw, 6.5rem)/.92 var(--display);", self.css)

    def test_artist_page_has_an_icon_only_back_button_and_no_library_heading(self):
        self.assertIn('<button type="button" id="libraryBack" class="artist-back" aria-label="Back" title="Back">', self.html)
        self.assertNotIn(">Back</button>\n      <div class=\"artist-hero\">", self.html)
        self.assertIn("$('libraryHeading').hidden = name === 'artist' || name === 'album';", self.new_js)

    def test_artist_page_top_songs_show_rank_title_listens_and_an_owned_check_without_play_buttons(self):
        self.assertIn("function buildTopSongRow(item) {", self.new_js)
        self.assertIn("row.append(item.owned ? buildOwnedCheck()", self.new_js)
        self.assertIn("const TOP_SONGS_SHOWN = 5;", self.new_js)
        self.assertIn("document.querySelector('.artist-hero').classList.add('no-songs');", self.new_js)
        self.assertNotIn("play", self.new_js[self.new_js.index("function buildTopSongRow"):self.new_js.index("function paintTopSongs")].lower())

    def test_owned_album_cards_drop_a_year_suffix_from_the_name(self):
        self.assertIn("const ALBUM_YEAR_SUFFIX = /\\s*[(\\[]\\s*(?:19|20)\\d{2}\\s*[)\\]]\\s*$/;", self.new_js)
        self.assertIn("displayAlbumName(item.name)", self.new_js)
        self.assertIn("heading.textContent = displayAlbumName(target.name) || 'Loading album…';", self.new_js)
        self.assertIn("$('albumHeading').textContent = displayAlbumName(album.name);", self.new_js)

    def test_artist_page_shows_at_most_three_genre_tags(self):
        self.assertIn("const ARTIST_TAGS_SHOWN = 3;", self.new_js)
        self.assertIn("}, ARTIST_TAGS_SHOWN);", self.new_js)

    def test_album_page_is_one_centered_column_in_the_owner_s_order(self):
        album = self.html[self.html.index('<div id="libraryAlbumView" hidden>'):self.html.index('<div id="libraryGenreView"')]
        order = ['id="albumAction"', 'id="albumHeading"', 'id="albumArtist"', 'id="albumGenre"', 'id="albumYear"',
                 'id="albumDescription"', 'id="albumTracks"', 'id="albumPlatformLinks"', 'id="albumSimilarAlbums"',
                 'id="albumSimilarArtists"']
        positions = [album.index(part) for part in order]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('<button type="button" id="albumBack" class="album-back" aria-label="Back" title="Back">', album)
        self.assertIn('<ol id="albumSimilarAlbums" class="album-row-list ranked-album-list"></ol>', album)
        self.assertIn(".album-page { position: relative; max-width: 880px; margin: 0 auto;", self.css)

    def test_album_tracks_show_number_title_length_and_an_owned_check(self):
        self.assertIn("function buildTrackRow(track, index) {", self.new_js)
        self.assertIn("row.append(track.owned ? buildOwnedCheck()", self.new_js)
        self.assertIn("createTrackGetButton({", self.new_js)
        self.assertIn("fillRows($('albumTracks'), section.items, buildTrackRow);", self.new_js)
        self.assertIn("function albumSummary(tracks) {", self.new_js)

    def test_album_genre_is_a_text_link_before_the_year(self):
        self.assertIn("section.section === 'genre'", self.new_js)
        self.assertIn("buildLibraryLink(genre, {type: 'genre', tag: genre}, 'genre-text-link')", self.new_js)
        self.assertIn('#albumGenre:not(:empty) + #albumYear:not(:empty)::before', self.css)

    def test_album_description_read_more_appears_only_when_there_is_more(self):
        self.assertIn("function fitAlbumDescription() {", self.new_js)
        self.assertIn("const long = text.childElementCount > 1 || first.scrollHeight > first.clientHeight + 1;", self.new_js)
        self.assertNotIn("ALBUM_DESCRIPTION_CLAMP_LENGTH", self.new_js)

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
        self.assertIn("loadLibrary({reset: libraryView.resetOnRetry})", self.new_js)

    def test_styles_hide_panels_that_use_the_hidden_attribute_and_stack_search_on_phones(self):
        self.assertIn(".search-results[hidden], #libraryDetailView[hidden], #libraryListView[hidden], #libraryAlbumView[hidden], #libraryGenreView[hidden], #libraryMore[hidden] { display: none; }", self.css)
        self.assertIn("header .global-search { order: 3; flex: 1 0 100%; margin-left: 0; }", self.css)
        self.assertIn("main { margin: 136px 14px 0;", self.css)


if __name__ == "__main__":
    unittest.main()
