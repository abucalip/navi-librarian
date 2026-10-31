"""Source-contract regressions for the album page's Info and Reviews tabs."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "app.css").read_text(encoding="utf-8")


class AlbumTabsUIContractTests(unittest.TestCase):
    def test_tabs_follow_the_tabs_pattern_with_info_selected_first(self):
        self.assertIn('role="tablist" aria-label="About this album"', HTML)
        self.assertIn('id="albumTabInfo" class="album-tab active" role="tab" aria-selected="true" aria-controls="albumInfoPanel"', HTML)
        self.assertIn('id="albumTabReviews" class="album-tab" role="tab" aria-selected="false" aria-controls="albumReviewsPanel" tabindex="-1"', HTML)
        self.assertIn('id="albumInfoPanel" class="album-tab-panel" role="tabpanel" aria-labelledby="albumTabInfo"', HTML)
        self.assertIn('id="albumReviewsPanel" class="album-tab-panel" role="tabpanel" aria-labelledby="albumTabReviews" hidden', HTML)

    def test_info_keeps_the_description_and_names_its_source_and_licence(self):
        for element in ('id="albumDescription"', 'id="albumDescriptionToggle"', 'id="albumDescriptionLink"',
                        'id="albumDescriptionLicense"', 'id="albumInfoNote"'):
            self.assertIn(element, HTML)
        self.assertIn("link.textContent = description.source || 'Apple Music';", JS)
        self.assertIn("description.license ? ' \\u00b7 ' + description.license : ''", JS)

    def test_the_keyboard_moves_between_tabs_like_the_settings_tabs(self):
        for key in ("'ArrowRight'", "'ArrowLeft'", "'Home'", "'End'"):
            self.assertIn(f"event.key === {key}", JS[JS.index("albumTabButtons.forEach(button => {"):])
        self.assertIn("tab.setAttribute('tabindex', active ? '0' : '-1');", JS[JS.index("function selectAlbumTab"):])

    def test_reviews_load_when_the_tab_opens_not_with_the_album(self):
        select = JS[JS.index("function selectAlbumTab"):JS.index("function moveAlbumTab")]
        self.assertIn("if (name === 'reviews' && albumTabState.reviews === 'idle') loadAlbumReviews();", select)
        self.assertIn("requestJSON('/api/album-reviews?' + params)", JS)
        self.assertNotIn("album-reviews", JS[JS.index("function applyAlbumSection"):JS.index("function applyAlbumSection") + 6000])

    def test_a_new_album_resets_the_tabs_and_a_stale_answer_is_ignored(self):
        self.assertIn("  resetAlbumTabs();\n  setAlbumDescription(null);", JS)
        self.assertEqual(JS.count("if (seq !== albumTabState.reviewSeq) return;"), 2)

    def test_an_album_without_a_description_opens_on_reviews_unless_the_reader_chose(self):
        self.assertIn("if (description && !albumTabState.chosen) selectAlbumTab('reviews', {byReader: false});", JS)

    def test_each_review_is_a_quote_over_a_link_to_the_full_review(self):
        build = JS[JS.index("function buildAlbumReview"):JS.index("async function loadAlbumReviews")]
        self.assertIn("addTextElement(quote, 'p', '', '\\u201c' + review.quote + '\\u201d');", build)
        self.assertIn("link.textContent = 'Read the full review at ' + review.source;", build)
        self.assertIn("link.rel = 'noopener noreferrer';", build)
        self.assertNotIn("innerHTML", build)

    def test_a_partial_answer_is_asked_again_only_by_the_button(self):
        load = JS[JS.index("async function loadAlbumReviews"):JS.index("// The description's first paragraph")]
        # Only a failed request leaves the tab ready to ask again; a partial answer is kept as shown.
        self.assertEqual(load.count("albumTabState.reviews = 'idle';"), 1)
        self.assertIn("albumTabState.reviews = 'loaded';", load)
        self.assertIn("'No reviews found. Some sources did not answer.'", load)
        self.assertIn("$('albumReviewsRetry').addEventListener('click', loadAlbumReviews);", JS)

    def test_the_status_note_and_retry_button_follow_the_reviews(self):
        panel = HTML[HTML.index('id="albumReviewsPanel"'):]
        self.assertLess(panel.index('id="albumReviews"'), panel.index('id="albumReviewsNote"'))
        self.assertLess(panel.index('id="albumReviewsNote"'), panel.index('id="albumReviewsRetry"'))

    def test_the_tabs_keep_one_centred_width_in_every_state(self):
        # .album-head centres its children, which would shrink the block to its content: a short state such as
        # "No reviews found" must not narrow or shift the tabs.
        self.assertIn(".album-about { width: min(60ch, 100%);", CSS)
        self.assertIn(".album-tabs { display: flex; justify-content: center;", CSS)
        self.assertIn(".album-about .section-note { text-align: center; }", CSS)
        self.assertIn("#albumReviewsRetry { display: block; margin: var(--space-2) auto 0; }", CSS)

    def test_tab_styles_cover_the_active_tab_and_hidden_panels(self):
        for rule in (".album-tabs .album-tab.active {", ".album-tab-panel[hidden] { display: none; }",
                     ".album-review blockquote {", ".album-review-link {"):
            self.assertIn(rule, CSS)


if __name__ == "__main__":
    unittest.main()
