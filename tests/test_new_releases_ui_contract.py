"""Source contracts for the New releases ranked rows (Redesign Phase 3, item 2).

New releases reuses the Discover music ranked row with a release-date column in place of the
rank numeral (DESIGN_SYSTEM.md sections 8, 9.4, 9.6). These tests read the templates, script and
stylesheet as source. They never open a browser, so they do not replace the manual checklist.
"""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "app" / "templates" / "index.html"
APP_JS = ROOT / "static" / "app.js"
APP_CSS = ROOT / "static" / "app.css"


class NewReleasesRowContractTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = APP_CSS.read_text(encoding="utf-8")

    def test_results_use_the_ranked_list_container(self):
        self.assertIn('id="newReleasesCards" class="ranked-list"', self.html)
        self.assertNotIn('id="newReleasesCards" class="cards"', self.html)

    def test_load_and_refresh_controls_and_status_line_are_unchanged(self):
        self.assertRegex(self.html, r'<button data-load-discovery="new_releases"[^>]*title="Load new releases" aria-label="Load new releases">')
        self.assertRegex(self.html, r'<button data-refresh-discovery="new_releases"[^>]*title="Refresh in background" aria-label="Refresh in background">')
        self.assertIn('id="newReleasesStatus" class="status-line" aria-live="polite"', self.html)

    def test_new_releases_rows_come_from_the_shared_recommendation_row(self):
        # One ranked-row builder: the release list passes options to it instead of forking it.
        self.assertIn("return buildRecommendationRow(item, null, {", self.js)
        self.assertIn("releaseDate: true,", self.js)
        self.assertIn("if (name === 'new_releases') {\n        target.append(buildNewReleaseRow(item));", self.js)

    def test_release_rows_show_a_date_column_and_no_rank_numeral(self):
        start = self.js.index("function buildRecommendationRow(")
        builder = self.js[start:self.js.index("$('recommendationSearch').addEventListener", start)]
        self.assertIn("if (options.releaseDate) {\n    row.append(releaseDateColumn(item, row));", builder)
        # The numeral is built only on the Discover branch, so release rows never get one.
        self.assertIn("} else {\n    const numeral = document.createElement('span');", builder)
        self.assertIn("row.className = options.releaseDate ? 'ranked-row is-dated' : 'ranked-row';", builder)

    def test_release_year_badge_is_skipped_because_the_date_shows_the_year(self):
        start = self.js.index("function buildRecommendationRow(")
        builder = self.js[start:self.js.index("$('recommendationSearch').addEventListener", start)]
        self.assertIn("if (!options.releaseDate) {\n    const year = firstReleaseYear(", builder)

    def test_date_is_only_shown_when_the_api_returns_one(self):
        # The parser accepts only the API's own shapes and returns null otherwise: nothing invented.
        self.assertIn(
            r"/^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$/", self.js,
            "first_release_date must match YYYY, YYYY-MM or YYYY-MM-DD only",
        )
        start = self.js.index("function releaseDateParts(")
        parser = self.js[start:self.js.index("function releaseDateColumn(", start)]
        self.assertIn("if (!match) return null;", parser)
        self.assertIn("if (parts.day) addTextElement(column, 'span', 'row-date-day', parts.day);", self.js)
        self.assertIn("parts.year);", self.js)
        self.assertNotIn("innerHTML", parser)

    def test_release_date_is_added_to_the_accessible_name(self):
        start = self.js.index("function releaseDateColumn(")
        body = self.js[start:self.js.index("function buildNewReleaseRow(", start)]
        self.assertIn("row.setAttribute('aria-label', `${row.getAttribute('aria-label')}, released ${parts.label}`);", body)

    def test_sort_basis_is_named_in_the_status_line(self):
        self.assertIn("' · Sorted by release date, newest first'", self.js)
        self.assertIn("name === 'new_releases' && items.length", self.js)

    def test_new_releases_dismiss_uses_the_server_feedback_endpoint(self):
        start = self.js.index("function buildNewReleaseRow(")
        body = self.js[start:self.js.index("// Discover music metadata lines", start)]
        self.assertIn("sendFeedback('dismiss', artist, album, metadata, 'new_releases', row)", body)
        self.assertNotIn("dismiss_artist", body)

    def test_get_and_modal_handling_for_release_rows_are_the_shared_ones(self):
        start = self.js.index("function buildRecommendationRow(")
        builder = self.js[start:self.js.index("$('recommendationSearch').addEventListener", start)]
        self.assertIn("makeAlbumCardInteractive(row, artist, album, item);", builder)
        self.assertIn("createActionGroup(artist, album, item, {", builder)
        self.assertNotIn("Dismiss artist", builder)
        self.assertNotIn("innerHTML", builder, "rows must be built with text APIs only")

    def test_loading_shows_skeleton_rows_and_clears_them_before_rendering(self):
        # Personal Discoveries shares the skeleton path (its own contract is in
        # test_personal_discoveries_ui_contract.py), so the check is on the shared flag.
        # Narrow update (Phase 3 item 4): Add to your collection is a ranked list too.
        self.assertIn("const rankedRowList = name === 'new_releases' || name === 'personal' || name === 'classics';", self.js)
        self.assertIn("target.replaceChildren(...(rankedRowList ? skeletonRows(6) : []));", self.js)
        self.assertIn("if (rankedRowList) target.replaceChildren();", self.js)

    def test_failure_clears_skeleton_rows_and_shows_the_error_message(self):
        start = self.js.index("async function loadDiscovery(")
        body = self.js[start:self.js.index("async function sendFeedback(", start)]
        self.assertIn("if (rankedRowList) target.replaceChildren();\n    discoveryStatus(name, error.message);", body)

    def test_release_date_column_is_plain_text_not_the_red_numeral(self):
        start = self.css.index(".row-date {")
        block = self.css[start:self.css.index("}", self.css.index(".row-date-year", start))]
        self.assertNotIn("chart-red", block)
        self.assertIn(".row-date-day { font: 600 var(--text-md)/1.2 var(--display); color: var(--text);", block)

    def test_phone_layout_gives_the_date_column_room(self):
        self.assertIn(".ranked-row.is-dated { grid-template-columns: 56px var(--row-art) minmax(0, 1fr); }", self.css)
        self.assertIn(".ranked-row .row-date { grid-column: 1; grid-row: 1; }", self.css)


if __name__ == "__main__":
    unittest.main()
