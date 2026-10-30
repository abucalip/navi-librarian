"""Source contracts for the Personal Discoveries ranked rows (Redesign Phase 3, item 3).

Personal Discoveries reuses the Discover music ranked row through options (DESIGN_SYSTEM.md
sections 8, 9.4, 9.6). The server returns these items in its selection order, not in
discovery_score order, so rows carry a muted position and no red rank numeral. These tests read
the template, script and stylesheet as source. They never open a browser, so they do not replace
the manual checklist, and server-side behaviour stays with the backend tests.
"""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "app" / "templates" / "index.html"
APP_JS = ROOT / "static" / "app.js"
APP_CSS = ROOT / "static" / "app.css"


class PersonalDiscoveriesRowContractTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = APP_CSS.read_text(encoding="utf-8")

    def _function_body(self, signature, end_marker):
        start = self.js.index(signature)
        return self.js[start:self.js.index(end_marker, start)]

    def test_results_use_the_ranked_list_container(self):
        self.assertIn('id="personalCards" class="ranked-list"', self.html)
        self.assertNotIn('id="personalCards" class="cards"', self.html)

    def test_load_refresh_and_status_line_are_unchanged(self):
        self.assertRegex(self.html, r'<button data-load-discovery="personal"[^>]*title="Load discoveries" aria-label="Load discoveries">')
        self.assertRegex(self.html, r'<button data-refresh-discovery="personal"[^>]*title="Refresh" aria-label="Refresh">')
        self.assertIn('id="personalStatus" class="status-line" aria-live="polite"', self.html)

    def test_endpoints_and_feedback_route_are_unchanged(self):
        self.assertIn("requestJSON(`/api/discovery/${name}?count=${poolCount}&nonce=${Date.now()}`)", self.js)
        self.assertIn("await sendJSON('/api/discovery/feedback', 'POST',", self.js)

    def test_personal_rows_reuse_the_shared_builder_without_a_fork(self):
        body = self._function_body("function buildPersonalRow(", "// Discover music metadata lines.")
        self.assertIn("return buildRecommendationRow(item, index + 1, {", body)
        self.assertIn("indexed: true,", body)
        self.assertNotIn("createElement('article')", body)
        self.assertNotIn("innerHTML", body)

    def test_personal_items_render_as_rows_not_editorial_cards(self):
        loop_start = self.js.index("for (const [index, item] of items.entries()) {")
        loop_head = self.js[loop_start:loop_start + 400]
        self.assertIn("if (name === 'personal') {\n        target.append(buildPersonalRow(item, index));", loop_head)
        # The personal branch must come before the generic card code, or the old card would still run.
        generic_card = self.js.index("const artist = item.artist || item.album_artist || 'Unknown artist';", loop_start)
        self.assertLess(loop_start + loop_head.index("if (name === 'personal')"), generic_card)

    def test_rows_show_a_muted_position_and_no_red_rank_numeral(self):
        builder = self._function_body("function buildRecommendationRow(", "$('recommendationSearch').addEventListener")
        self.assertIn("numeral.className = options.indexed ? 'rank-numeral is-index' : 'rank-numeral';", builder)
        start = self.css.index(".rank-numeral.is-index {")
        self.assertIn("color: var(--text-muted);", self.css[start:start + 80])
        self.assertNotIn("chart-red", self.css[start:start + 80])

    def test_dismiss_and_dismiss_artist_route_to_the_personal_list(self):
        body = self._function_body("function buildPersonalRow(", "// Discover music metadata lines.")
        self.assertIn("sendFeedback('dismiss', artist, album, metadata, 'personal', row)", body)
        self.assertNotIn("dismiss_artist", body)

    def test_status_line_names_the_real_sort_basis(self):
        self.assertIn("name === 'personal' && items.length", self.js)
        self.assertIn("' · Engine order, not ranked by discovery score'", self.js)
        # A numeral would need the basis to be a score order; the basis label must never claim one.
        self.assertNotIn("Ranked by discovery score'", self._function_body(
            "async function loadDiscovery(", "async function sendFeedback("))

    def test_meta_lines_come_from_the_api_and_are_text_only(self):
        body = self._function_body("function buildPersonalRow(", "// Discover music metadata lines.")
        self.assertIn("item.discovery_category", body)
        self.assertIn("item.reason", body)
        # The listen count moved to the title line (addAlbumListens in buildRecommendationRow).
        self.assertNotIn("lastfm_playcount", body)
        self.assertNotIn("discovery_score", body, "the score is not shown as a rank or a metadata line here")

    def test_loading_shows_skeleton_rows_and_failure_clears_them(self):
        # Narrow update (Phase 3 item 4): Add to your collection is a ranked list too.
        self.assertIn("const rankedRowList = name === 'new_releases' || name === 'personal' || name === 'classics';", self.js)
        self.assertIn("target.replaceChildren(...(rankedRowList ? skeletonRows(6) : []));", self.js)
        self.assertIn("if (rankedRowList) target.replaceChildren();\n    discoveryStatus(name, error.message);", self.js)

    def test_empty_state_copy_names_the_precondition(self):
        self.assertIn("personal: 'No personal discoveries yet.", self.js)
        self.assertIn("need Last.fm or ListenBrainz configured in Settings", self.js)

    def test_every_personal_row_shows_the_artist_bio(self):
        body = self._function_body("function buildPersonalRow(", "function attachArtistBio(")
        self.assertIn("artistBio: true,", body)

    def test_artist_bio_uses_the_existing_endpoint_cache_and_text_api(self):
        body = self._function_body("function attachArtistBio(", "// Discover music metadata lines.")
        self.assertIn("cachedBioRequest(bioKey, artist)", body)
        self.assertIn("bio.textContent = result.bio;", body)
        self.assertIn("if (artistBioObserver) artistBioObserver.observe(row);", body)
        self.assertNotIn("innerHTML", body)

    def test_artist_bio_is_only_attached_to_rows_that_ask_for_it(self):
        builder = self._function_body("function buildRecommendationRow(", "$('recommendationSearch').addEventListener")
        self.assertIn("if (options.artistBio) attachArtistBio(row, main, artist);", builder)
        self.assertIn(".ranked-row .artist-bio", self.css)


if __name__ == "__main__":
    unittest.main()
