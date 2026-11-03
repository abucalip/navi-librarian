"""Zine Spread layout (D-024, docs/BRUT_ROUND3_PLAN.md, phase P1): its palette, the scoping of its rules and its hidden-by-default hooks."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"


def _lum(hex_color):
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a, b):
    x, y = _lum(a), _lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


class ZineLayoutTests(unittest.TestCase):
    def setUp(self):
        self.script = (STATIC / "appearance.js").read_text(encoding="utf-8")
        self.themes = (STATIC / "themes.css").read_text(encoding="utf-8")
        self.layouts = (STATIC / "layouts.css").read_text(encoding="utf-8")
        self.app = (STATIC / "app.js").read_text(encoding="utf-8")
        self.zine_js = (STATIC / "layout-zine.js").read_text(encoding="utf-8")
        self.html = (ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")
        self.zine = self.layouts.split('==== Zine Spread ("zine")')[1].split("*/", 1)[1].split("==== Pipeline Board")[0]
        self.block = self.themes.split(':root[data-theme="zine"]')[1].split("\n}")[0]

    def _token(self, name):
        return re.search(rf"--{name}: (#[0-9a-fA-F]{{6}})", self.block).group(1)

    def test_the_catalogue_entry_declares_the_layout(self):
        line = next(l for l in self.script.splitlines() if "id: 'zine'" in l)
        for field in ("label: 'Zine \\u00b7 Yellow'", "group: 'Zine Spread'", "dark: false", "brut: true", "layout: 'zine'", "bar: '#ffde59'"):
            self.assertIn(field, line)

    def test_every_zine_selector_is_scoped_and_the_layout_applies_only_above_900px(self):
        css = re.sub(r"/\*.*?\*/", "", self.zine, flags=re.S)
        self.assertTrue(css.lstrip().startswith("@media (min-width: 901px) {"))
        selectors = []
        for chunk in re.findall(r"([^{}]+)\{", css):
            text = chunk.strip()
            if text.startswith("@") or re.fullmatch(r"(\d+%|from|to)(\s*,\s*(\d+%|from|to))*", text):
                continue
            selectors.extend(part.strip() for part in text.split(","))
        self.assertGreater(len(selectors), 20)
        for selector in selectors:
            self.assertTrue(selector.startswith(':root[data-layout="zine"]'), selector)

    def test_the_palette_has_the_full_token_set(self):
        for name in ("ink-rail", "ink", "surface", "surface-raised", "surface-hover", "edge", "text", "text-muted", "accent", "accent-text",
                     "focus", "on-accent", "bw", "brut-sh", "brut-shadow-color", "brut-nav-bg", "brut-nav-text", "zine-pink", "zine-teal", "zine-cover"):
            self.assertRegex(self.block, rf"--{name}:", name)
        self.assertEqual(self._token("accent"), "#ffde59")

    def test_text_contrast_meets_wcag_aa(self):
        t = self._token
        pairs = [("text", "ink"), ("text", "surface"), ("text-muted", "ink"), ("text-muted", "surface"), ("text-muted", "ink-rail"),
                 ("text", "ink-rail"), ("accent-text", "surface"), ("accent-text", "ink"), ("on-accent", "accent"),
                 ("zine-on-colour", "zine-pink"), ("zine-on-colour", "zine-teal"), ("brut-nav-text", "brut-nav-bg"), ("accent", "zine-cover"),
                 ("text", "surface-raised"), ("text-muted", "surface-raised")]
        for fg, bg in pairs:
            fg_hex = t(fg) if fg != "zine-on-colour" else self._token("zine-on-colour")
            self.assertGreaterEqual(_contrast(fg_hex, t(bg)), 4.5, f"{fg} on {bg}")
        self.assertGreaterEqual(_contrast(t("focus"), t("ink")), 3, "focus ring on ground")
        self.assertGreaterEqual(_contrast(t("focus"), t("surface")), 3, "focus ring on surface")

    # ---- hooks: hidden by default, filled only by static/layout-zine.js, in the template once ----
    def test_every_hook_is_hidden_by_default(self):
        for hook in ('id="zineMast" class="zine-mast" aria-hidden="true" hidden', 'id="zineTicker" class="zine-ticker" aria-hidden="true" hidden',
                     'id="zineFront" class="zine-front" hidden', 'id="zineLetters" class="zine-letters" role="group" aria-label="Jump to a letter" hidden',
                     'id="zineAlbumBy" class="zine-album-by" hidden', 'id="zineGetMissing" class="zine-get-missing" hidden', 'id="zinePull" class="zine-pull" hidden',
                     'id="zineCoverLines" class="zine-cover-lines" aria-hidden="true" hidden', 'id="zineIssuesSection" class="zine-issues"'):
            self.assertIn(hook, self.html)
        before = self.layouts.split('==== Zine Spread ("zine")')[0]
        self.assertNotIn(".zine-", before)

    def test_the_script_loads_after_app_js_and_app_js_reaches_it_only_through_the_hook(self):
        self.assertLess(self.html.index('/static/app.js'), self.html.index('/static/layout-zine.js'))
        self.assertIn("function zineHook(name, ...args)", self.app)
        for name in ("updateZineTicker", "renderZineFront", "updateZineMast", "renderZineArtist", "renderZineAlbum", "focusZineLead"):
            self.assertIn(f"zineHook('{name}'", self.app)
        self.assertNotRegex(self.app, r"(?<!zineHook\(')(?<!function )\b(updateZine\w+|renderZine\w+)\(")

    def test_every_function_returns_unless_the_layout_is_active(self):
        for fn in ("updateZineMast", "renderZineArtist", "renderZineAlbum", "updateZineLetters"):
            body = self.zine_js.split(f"function {fn}(")[1].split("\n}\n")[0]
            self.assertIn("zineOn()", body, fn)
        self.assertIn("zineFrontActive()", self.zine_js.split("function renderZineFront() {")[1].split("\n}\n")[0])

    # ---- mast and ticker ----
    def test_the_mast_names_the_page_like_the_mockup(self):
        mast = self.zine_js.split("function updateZineMast() {")[1].split("\n}\n")[0]
        for text in ("The Discair Daily", "The Index", "The Wire", "'Vol. '", "imported this week", "/ to filter", "Review"):
            self.assertIn(text, mast)

    def test_the_ticker_is_black_with_words_and_glyphs_and_makes_no_request(self):
        fn = self.zine_js.split("function updateZineTicker(jobs) {")[1].split("\n}\n")[0]
        for text in ("downloading", "imported", "failed", "(retry)", "new releases this week"):
            self.assertIn(text, fn)
        self.assertNotIn("fetch(", fn)
        self.assertIn("color: var(--accent); background: var(--edge)", self.zine)

    # ---- dashboard ----
    def test_the_front_page_is_built_from_the_default_builders(self):
        for hook in ('id="zineLead"', 'id="zineNew"', 'id="zineClassifieds"', "New this week", "Classifieds", 'id="zineGetAll"', 'id="zineIndexChips"', "J / K next story"):
            self.assertIn(hook, self.html)
        fn = self.zine_js.split("function renderZineFront() {")[1].split("\n}\n")[0]
        self.assertIn("buildDashboardTile(", fn)
        self.assertIn("buildShelfCard(", fn)
        self.assertNotIn("fetch(", fn)
        self.assertIn("zineHook('renderZineFront')", self.app.split("function renderDashboardPicks() {")[1].split("\n}\n")[0])

    def test_the_lead_story_headline_names_what_the_library_holds(self):
        fn = self.zine_js.split("function zineApplyLead(")[1].split("\n}\n")[0]
        self.assertIn("'you own '", fn)
        self.assertIn("Not this one.", fn)
        self.assertIn("missing from your shelf", fn)
        self.assertIn("Start here.", fn)
        facts = self.zine_js.split("async function zineShelfFacts(")[1].split("\n}\n")[0]
        self.assertIn("/api/library/albums", facts)
        self.assertNotIn("/api/acquire", self.zine_js)

    def test_the_lead_blurb_places_the_pick_on_the_shelf_says_why_and_names_the_target_quality(self):
        position = self.zine_js.split("function zinePosition(")[1].split("\n}\n")[0]
        for text in ("sits between the two you have", "comes after", "comes before", "is your way into"):
            self.assertIn(text, position)
        why = self.zine_js.split("function zineWhy(")[1].split("\n}\n")[0]
        for text in ("Ranked first today", "from your plays of", "Last.fm neighbours of", "shelfItems.Frequent"):
            self.assertIn(text, why)
        fn = self.zine_js.split("function zineApplyLead(")[1].split("\n}\n")[0]
        self.assertIn("' Target quality: '", fn)
        self.assertIn("quality_priority", self.zine_js.split("function zineTargetQuality()")[1].split("\n}\n")[0])

    def test_the_album_description_leads_and_the_artist_bio_is_the_fallback(self):
        self.assertIn("/api/album-description", self.zine_js)
        fn = self.zine_js.split("function zineApplyLead(")[1].split("\n}\n")[0]
        self.assertIn("paragraphs.length", fn)
        self.assertIn("tile.classList.add('has-desc')", fn)
        self.assertIn(".zine-lead-tile.has-desc .artist-bio { display: none; }", self.zine)
        self.assertIn(".zine-lead-tile .artist-bio { display: block;", self.zine)

    def test_j_and_k_step_the_lead_story_on_the_dashboard_and_lines_in_the_library(self):
        block = self.zine_js.split("document.addEventListener('keydown'")[1].split("/* ----------------------------------------------------------------")[0]
        for guard in ("event.ctrlKey", "event.metaKey", "event.altKey", "INPUT|TEXTAREA|SELECT", "albumModalBackdrop", "zineStep(", "'/'"):
            self.assertIn(guard, block)
        step = self.zine_js.split("function zineStep(delta) {")[1].split("\n}\n")[0]
        self.assertIn("'Story '", step)

    def test_the_front_page_actions_carry_text_labels_including_not_for_me(self):
        self.assertIn("'dismiss-album-label', 'Not for me'", self.zine_js)
        for label in ("get-album-label", "save-album-label", "dismiss-album-label"):
            self.assertIn(f".zine-lead-tile .action-group .{label}", self.zine)

    def test_dismissing_a_front_page_pick_uses_the_feedback_path_and_can_be_undone(self):
        fn = self.app.split("function dismissDashboardPick(tile, artist, album, item) {")[1].split("\n}\n")[0]
        self.assertIn("tile.parentNode !== slider", fn)
        self.assertIn("sendFeedback('dismiss', artist, album, item, 'dashboard_picks', tile", fn)
        self.assertIn("dashboardPickItems.splice(spot, 0, item)", fn)

    def test_get_all_clicks_the_real_get_buttons(self):
        fn = self.zine_js.split("function zineGetAll() {")[1].split("\n}\n")[0]
        self.assertIn("#zineClassifieds .get-album:not(:disabled)", fn)
        self.assertIn("button.click()", fn)

    def test_the_default_recommended_panel_and_new_releases_shelf_are_hidden_only_by_this_layout(self):
        self.assertIn('#dashboard > .panel:has(#dashboardCarousel)', self.zine)
        self.assertIn('shelfNewReleasesHeading', self.zine)

    def test_the_index_foot_opens_the_library_at_a_range_of_letters(self):
        self.assertIn("['ABCD', 'EFGH', 'IJKL', 'MNOP', 'QRST', 'UVWXYZ']", self.zine_js)
        fn = self.zine_js.split("function zineOpenIndex(range) {")[1].split("\n}\n")[0]
        self.assertIn("navigateTo('library')", fn)
        self.assertIn("libraryView.sort = 'name'", fn)

    # ---- library ----
    def test_the_letter_margin_is_vertical_acts_only_on_loaded_rows_and_never_fetches(self):
        self.assertIn('<div class="zine-index">', self.html)
        fn = self.zine_js.split("function updateZineLetters() {")[1].split("\n}\n")[0]
        self.assertIn("button.disabled = true;", fn)
        self.assertIn("No loaded entry starts with", fn)
        self.assertIn("zine-letter-head", fn)
        self.assertNotIn("fetch(", fn)
        self.assertNotIn("requestJSON", fn)
        self.assertIn("flex-direction: column", self.zine.split(".zine-letters {")[1].split("}")[0])
        self.assertIn('[aria-current="true"]', self.zine)

    # ---- album ----
    def test_the_album_article_has_a_byline_pull_quote_and_missing_track_coupons(self):
        fn = self.zine_js.split("function renderZineAlbum() {")[1].split("\n}\n")[0]
        for text in ("owned ", "' tracks'", "One is a coupon.", "Every song is on your shelf.", "Get missing track"):
            self.assertIn(text, fn)
        self.assertIn("content: \"GET \\2702\"", self.zine)
        self.assertIn(".album-head { display: contents; }", self.zine)
        self.assertIn(".album-hero-art-wrap { float: left;", self.zine)
        self.assertIn("columns: 2; column-gap: 16px", self.zine.split(".track-list {")[1].split("}")[0])
        self.assertIn("albumPage.tracks = section.items;", self.app)

    # ---- artist ----
    def test_the_artist_cover_has_cover_lines_and_back_issues_built_from_the_page_data(self):
        fn = self.zine_js.split("function renderZineArtist(ctx) {")[1].split("\n}\n")[0]
        for text in ("Inside: ", "issues on your shelf", "Also: ", "ctx.ownedAlbums", "ctx.missing", "ctx.similar"):
            self.assertIn(text, fn)
        card = self.zine_js.split("function zineIssueCard(item) {")[1].split("\n}\n")[0]
        self.assertIn("buildAlbumState(item)", card)
        self.assertIn("Missing \u00b7 Get", card)
        self.assertIn("--zine-cover", self.zine)
        self.assertIn("white-space: nowrap", self.zine.split("#artistDetailHeading {")[1].split("}")[0])
        for hook in ("ctx.ownedAlbums = ", "ctx.similar = ", "ctx.albumCount = "):
            self.assertIn(hook, self.app)

    # ---- acquisitions ----
    def test_acquisition_dispatches_have_verbs_a_hatched_press_bar_and_keep_their_controls(self):
        css = self.zine.split("Acquisitions: THE WIRE")[1]
        for verb in ('" arrives"', '" waits its turn"', '" stalls"'):
            self.assertIn(verb, css)
        self.assertIn("repeating-linear-gradient(90deg", css)
        self.assertNotIn(".acq-actions { display: none", css)

    def test_reduced_motion_disables_any_zine_animation(self):
        css = re.sub(r"/\*.*?\*/", "", self.zine, flags=re.S)
        if "animation:" in css or "transition:" in css:
            self.assertIn("prefers-reduced-motion: reduce", css)


if __name__ == "__main__":
    unittest.main()
