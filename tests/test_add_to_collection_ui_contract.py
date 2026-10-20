"""Source contracts for the Add to your collection ranked rows (Redesign Phase 3, item 4).

Add to your collection (Classics) reuses the Discover music ranked row through options
(DESIGN_SYSTEM.md sections 8, 9.2, 9.4, 9.6). The server orders candidates by an exploration
score with random jitter, and Load albums rotates them on the client, so rows carry a muted
position and no red rank numeral, and the status line names the basis. Get stays prominent and
Not for me / Dismiss artist keep routing to the server feedback endpoint. These tests read the
template, script and stylesheet as source. They never open a browser, so they do not replace the
manual checklist, and server-side behaviour stays with the backend tests.
"""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "app" / "templates" / "index.html"
APP_JS = ROOT / "static" / "app.js"
APP_CSS = ROOT / "static" / "app.css"


class AddToCollectionRowContractTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = APP_CSS.read_text(encoding="utf-8")

    def _function_body(self, signature, end_marker):
        start = self.js.index(signature)
        return self.js[start:self.js.index(end_marker, start)]

    def test_results_use_the_ranked_list_container(self):
        self.assertIn('id="classicsCards" class="ranked-list"', self.html)
        self.assertNotIn('id="classicsCards" class="cards"', self.html)

    def test_load_refresh_and_status_line_are_unchanged(self):
        self.assertIn('data-load-discovery="classics">Load albums</button>', self.html)
        self.assertIn('data-refresh-discovery="classics">Refresh</button>', self.html)
        self.assertIn('id="classicsStatus" class="status-line" aria-live="polite"', self.html)
        self.assertIn("classics: ['classicsCards','classicsStatus']", self.js)

    def test_endpoint_pool_size_and_rotation_are_unchanged(self):
        self.assertIn("requestJSON(`/api/discovery/${name}?count=${poolCount}&nonce=${Date.now()}`)", self.js)
        self.assertIn("const poolCount = name === 'artist_deep_dive' ? 150 : name === 'classics' ? 100 : 30;", self.js)
        self.assertIn("if ((name === 'classics' || name === 'artist_deep_dive') && options.rotate) {", self.js)
        self.assertIn("if (count >= 3) return false;", self.js)

    def test_classics_rows_reuse_the_shared_builder_without_a_fork(self):
        body = self._function_body("function buildClassicsRow(", "// Lazy artist bio for a ranked row.")
        self.assertIn("return buildRecommendationRow(item, index + 1, {", body)
        self.assertIn("indexed: true,", body)
        self.assertNotIn("createElement('article')", body)
        self.assertNotIn("innerHTML", body)

    def test_classics_items_render_as_rows_not_editorial_cards(self):
        loop_start = self.js.index("for (const [index, item] of items.entries()) {")
        loop_head = self.js[loop_start:loop_start + 600]
        self.assertIn("if (name === 'classics') {\n        target.append(buildClassicsRow(item, index));", loop_head)
        generic_card = self.js.index("const artist = item.artist || item.album_artist || 'Unknown artist';", loop_start)
        self.assertLess(loop_start + loop_head.index("if (name === 'classics')"), generic_card)

    def test_rows_show_a_muted_position_and_no_red_rank_numeral(self):
        builder = self._function_body("function buildRecommendationRow(", "const monthAbbreviations")
        self.assertIn("numeral.className = options.indexed ? 'rank-numeral is-index' : 'rank-numeral';", builder)
        start = self.css.index(".rank-numeral.is-index {")
        self.assertIn("color: var(--text-muted);", self.css[start:start + 80])

    def test_dismiss_and_dismiss_artist_route_to_the_classics_list(self):
        body = self._function_body("function buildClassicsRow(", "// Lazy artist bio for a ranked row.")
        self.assertIn("sendFeedback('dismiss', artist, album, metadata, 'classics', row)", body)
        self.assertIn("sendFeedback('dismiss_artist', artist, album, metadata, 'classics', row)", body)

    def test_status_line_names_the_real_basis_and_never_claims_a_score_order(self):
        self.assertIn("name === 'classics' && items.length", self.js)
        self.assertIn("' · Picked for exploration, not ranked by score'", self.js)
        self.assertNotIn("Ranked by discovery score'", self._function_body(
            "async function loadDiscovery(", "async function sendFeedback("))

    def test_meta_lines_come_from_the_api_and_are_text_only(self):
        body = self._function_body("function buildClassicsRow(", "// Lazy artist bio for a ranked row.")
        self.assertIn("item.anchor_artist", body)
        self.assertIn("item.lastfm_playcount", body)
        self.assertNotIn("discovery_score", body)
        self.assertNotIn("innerHTML", body)

    def test_artist_bio_keeps_the_card_connection_rule(self):
        body = self._function_body("function buildClassicsRow(", "// Lazy artist bio for a ranked row.")
        self.assertIn("const hasBio = /Genre tags connect this artist to your established musical interests/i.test(item.reason || '');", body)
        self.assertIn("artistBio: hasBio,", body)
        self.assertIn("hasBio ? '' : item.reason", body)

    def test_loading_shows_skeleton_rows_and_failure_clears_them(self):
        self.assertIn("target.replaceChildren(...(rankedRowList ? skeletonRows(6) : []));", self.js)
        self.assertIn("if (rankedRowList) target.replaceChildren();\n    discoveryStatus(name, error.message);", self.js)

    def test_empty_state_copy_is_unchanged(self):
        self.assertIn("classics: 'No albums to add yet.", self.js)

    def test_row_title_clamp_comes_from_the_shared_row(self):
        self.assertIn(".ranked-row h3 {", self.css)
        self.assertNotIn("#classicsCards .card h3", self.css)


if __name__ == "__main__":
    unittest.main()
