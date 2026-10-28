"""Regression contracts for keyboard access to the scroll tracks, focus containment in the
album dialog, and transient acquisition feedback.

Like the other ``*_ui_contract`` modules these read the shipped static assets and assert on
their source. They never start a browser, a server, or an acquisition request, so they
protect the client contract rather than proving rendered behaviour. The rendered checks are
recorded separately in the PR's manual test report.
"""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "static" / "app.js"
APP_CSS = ROOT / "static" / "app.css"
INDEX_HTML = ROOT / "app" / "templates" / "index.html"
VENDOR_DIR = ROOT / "static" / "vendor" / "notyf"


def function_source(source, signature, next_signature):
    start = source.index(signature)
    end = source.index(next_signature, start)
    return source[start:end]


class ScrollTrackKeyboardTests(unittest.TestCase):
    """The scroll tracks had no container-level keyboard affordance or accessible name."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = APP_CSS.read_text(encoding="utf-8")

    def test_scroll_tracks_become_named_tab_stops(self):
        helper = function_source(
            self.js, "function makeScrollTrackFocusable(", "async function loadDashboardPicks("
        )
        self.assertIn("track.setAttribute('tabindex', '0')", helper)
        self.assertIn("track.setAttribute('role', 'group')", helper)
        self.assertIn("track.setAttribute('aria-label', label)", helper)

    def test_arrow_keys_and_home_end_scroll_the_track(self):
        helper = function_source(
            self.js, "function makeScrollTrackFocusable(", "async function loadDashboardPicks("
        )
        for key in ("'ArrowRight'", "'ArrowLeft'", "'Home'", "'End'"):
            self.assertIn("event.key === " + key, helper)
        # preventDefault only runs for a handled key, so Tab and Escape still work.
        self.assertIn("else return;", helper)
        self.assertIn("event.preventDefault();", helper)
        # Modified arrows belong to the browser and the OS, not to the carousel.
        self.assertIn("if (event.altKey || event.ctrlKey || event.metaKey) return;", helper)

    def test_scroll_helper_is_wired_to_the_dashboard_strip_and_genre_rows(self):
        # The dashboard picks are a static strip (DESIGN_SYSTEM.md 8, D1), so the strip gets the
        # same tab stop and arrow handling as the genre rows. It is attached once at startup, not
        # inside loadDashboardPicks, so each shuffle does not stack another keydown listener.
        dashboard = function_source(
            self.js, "async function loadDashboardPicks(", "$('shuffleDashboard').addEventListener"
        )
        self.assertNotIn("makeScrollTrackFocusable(", dashboard)
        self.assertIn("makeScrollTrackFocusable($('dashboardCarousel'));", self.js)
        self.assertIn(
            "makeScrollTrackFocusable(track, genreRowLabel(genre, rowLabels) + ' albums');", self.js
        )

    def test_scroll_motion_is_suppressed_under_reduced_motion(self):
        self.assertIn(
            "window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'",
            self.js,
        )
        # The pre-existing arrow buttons share the same motion-aware helper.
        self.assertIn(
            "arrow.addEventListener('click', () => scrollTrackBy(track, direction * trackScrollStep(track)));",
            self.js,
        )

    def test_focus_ring_is_drawn_on_the_scroll_container(self):
        self.assertIn(
            ".genre-row-track:focus-visible "
            "{ outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 4px; }",
            self.css,
        )


class DashboardTileStripTests(unittest.TestCase):
    """The dashboard picks are a static, unranked strip of tiles (DESIGN_SYSTEM.md 8, 9.2, 15 D1).

    The coverflow ring these tests used to pin is retired. Its contract tests are removed rather
    than kept, because they asserted code that no longer exists; the behavioural rules that still
    apply (one named open control per tile, Get kept as its own control, the server-confirmed
    Get state, reduced motion) are asserted here against the strip instead.
    """

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = APP_CSS.read_text(encoding="utf-8")
        cls.index = INDEX_HTML.read_text(encoding="utf-8")

    def test_the_ring_and_its_3d_transforms_are_gone(self):
        for name in ("buildDashboardRing", "ringSyncLayout", "ring-scene", "ring-stage", "ring-card", "is-ring"):
            self.assertNotIn(name, self.js)
            self.assertNotIn(name, self.css)
        for name in ("rotateY", "translateZ", "preserve-3d", "perspective:"):
            self.assertNotIn(name, self.css)
        self.assertNotIn("RING_", self.js)

    def test_tiles_are_unranked(self):
        tile = function_source(self.js, "function buildDashboardTile(item) {", "async function loadDashboardPicks(")
        # Random order means no numeral; the rank column belongs to ordered lists only.
        for name in ("rank-numeral", "padStart", "is-index"):
            self.assertNotIn(name, tile)

    def test_each_tile_has_one_named_open_control_and_a_separate_get(self):
        tile = function_source(self.js, "function buildDashboardTile(item) {", "async function loadDashboardPicks(")
        self.assertIn("open.className = 'dashboard-tile-open';", tile)
        self.assertIn("open.setAttribute('aria-label', 'View details for ' + album + ' by ' + artist);", tile)
        self.assertIn("open.addEventListener('click', () => openAlbumModal(tile, open));", tile)
        # Get is appended to the artwork, never to the open button, so no control is nested.
        self.assertIn("tile.querySelector('.card-art').append(createGetButton(artist, album, item));", tile)
        self.assertNotIn("open.append(", tile)
        # The open control precedes the artwork in the DOM, so it is the first focus stop.
        self.assertLess(tile.index("tile.append(open);"), tile.index("attachArtwork(tile, artist, album);"))

    def test_the_tile_article_is_data_only_and_not_a_focus_stop(self):
        interactive = function_source(
            self.js, "function makeAlbumCardInteractive(", "function ensureAlbumYearBadge("
        )
        self.assertIn("if (interactive) {", interactive)
        self.assertIn("card.setAttribute('tabindex', '0');", interactive)
        self.assertIn("makeAlbumCardInteractive(tile, artist, album, item, true, false);", self.js)

    def test_closing_the_dialog_returns_focus_to_the_tile_button(self):
        open_modal = function_source(self.js, "async function openAlbumModal(", "  $('albumModalTitle').replaceChildren();")
        self.assertIn("async function openAlbumModal(card, returnFocus = card) {", open_modal)
        self.assertIn("albumModalReturnFocus = returnFocus;", open_modal)

    def test_metadata_text_is_not_hidden_because_the_album_and_artist_names_are_links(self):
        # The album and artist names on a tile open their library pages, so the metadata block must stay
        # in the accessibility tree: focusable links inside an aria-hidden block are an ARIA violation.
        # The links sit above the tile's full-size open control so they can be clicked.
        tile = function_source(self.js, "function buildDashboardTile(item) {", "async function loadDashboardPicks(")
        self.assertNotIn("meta.setAttribute('aria-hidden', 'true');", tile)
        self.assertIn("linkAlbumName(title, artist, album, item);", tile)
        self.assertIn("linkArtistName(addTextElement(meta, 'p', 'card-artist', ''), artist);", tile)
        self.assertIn(".dashboard-tile-meta .inline-link { position: relative; z-index: 3; }", self.css)

    def test_get_keeps_the_server_confirmed_state_machine(self):
        search = function_source(self.js, "async function searchAlbum(", "// Route acquisition feedback")
        self.assertIn("setGetButtonState(button, 'pending', artist, album);", search)
        # 'requested' is set only after the server answers, and an ok:false answer is a failure.
        self.assertLess(search.index("if (data && data.ok === false)"), search.index("setGetButtonState(button, 'requested', artist, album);"))
        self.assertIn("setGetButtonState(button, 'failed', artist, album);", search)

    def test_shuffle_cannot_race_two_responses_into_the_strip(self):
        load = function_source(self.js, "async function loadDashboardPicks(", "$('shuffleDashboard').addEventListener")
        self.assertIn("shuffle.disabled = true;", load)
        self.assertIn("shuffle.disabled = false;", load)
        self.assertIn("status.textContent = error.message;", load)
        self.assertIn("'No suggestions yet. Open a discovery page and refresh its list first.'", load)

    def test_strip_is_a_focusable_named_scroller_with_a_visible_focus_ring(self):
        self.assertIn('aria-label="Random album recommendations"', self.index)
        self.assertIn('role="group"', self.index)
        self.assertIn(".dashboard-carousel:focus-visible { outline: 2px solid var(--accent);", self.css)
        self.assertIn(".dashboard-carousel > .card { flex: 0 0 218px; width: 218px;", self.css)
        # The gesture is named in copy a user can read.
        self.assertIn("Scroll the row, or focus it and use", self.index)

    def test_tile_open_control_has_a_visible_focus_ring_inside_the_clipped_tile(self):
        self.assertIn(".dashboard-tile.card > .dashboard-tile-open:focus-visible { outline: 2px solid var(--accent); outline-offset: -4px; }", self.css)
        # The generic card margins would inset the open control; the overlay must still cover the tile.
        self.assertIn(".dashboard-tile.card > .dashboard-tile-open { position: absolute; inset: 0;", self.css)


class AlbumModalFocusTests(unittest.TestCase):
    """The dialog declared aria-modal but did not contain Tab or restore focus."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.index = INDEX_HTML.read_text(encoding="utf-8")

    def test_tab_is_trapped_while_the_dialog_is_open(self):
        handler = function_source(
            self.js, "document.addEventListener('keydown', event => {", "$('albumModalClose')"
        )
        self.assertIn("const albumModalOpen = !$('albumModalBackdrop').hidden;", handler)
        self.assertIn("if (event.key === 'Tab' && albumModalOpen) trapAlbumModalFocus(event);", handler)
        # Escape keeps working, and the dialog still opens from a card.
        self.assertIn("if (event.key === 'Escape' && albumModalOpen) closeAlbumModal();", handler)

    def test_trap_wraps_both_ends_and_recovers_focus_from_outside(self):
        trap = function_source(
            self.js, "function trapAlbumModalFocus(", "function closeAlbumModal() {"
        )
        self.assertIn("const first = focusable[0];", trap)
        self.assertIn("const last = focusable[focusable.length - 1];", trap)
        self.assertIn("if (event.shiftKey && active === first) {", trap)
        self.assertIn("} else if (!event.shiftKey && active === last) {", trap)
        # Platform links are rebuilt while open, so focus can land outside the control list.
        self.assertIn("if (!focusable.includes(active)) {", trap)
        self.assertIn("(event.shiftKey ? last : first).focus();", trap)

    def test_focusable_scan_survives_a_fixed_position_backdrop(self):
        scan = function_source(
            self.js, "function albumModalFocusable(", "function trapAlbumModalFocus("
        )
        # offsetParent is always null inside a position:fixed backdrop, so it cannot be used.
        self.assertIn("element.getClientRects().length > 0", scan)
        self.assertNotIn(".offsetParent", scan)
        self.assertIn("modal.querySelectorAll(ALBUM_MODAL_FOCUSABLE)", scan)
        self.assertIn('''[tabindex]:not([tabindex="-1"])''', self.js)

    def test_focus_returns_to_the_originating_card(self):
        # Updated narrowly with the dashboard tile change: a tile's article is not focusable, so
        # the opener is passed in explicitly (the tile's open button). The behaviour is unchanged:
        # focus goes back to whatever opened the dialog.
        self.assertIn("albumModalReturnFocus = returnFocus;", self.js)
        self.assertIn("async function openAlbumModal(card, returnFocus = card) {", self.js)
        close = function_source(
            self.js, "function closeAlbumModal() {", "async function openAlbumModal("
        )
        self.assertIn("if (returnTo && returnTo.isConnected) returnTo.focus();", close)
        # A lane can re-render while the dialog is open, detaching the originating card.
        self.assertIn("albumModalReturnFocus = null;", close)


class AcquisitionFeedbackTests(unittest.TestCase):
    """Toasts are additive, purely visual, and never announce a message twice."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = APP_CSS.read_text(encoding="utf-8")
        cls.index = INDEX_HTML.read_text(encoding="utf-8")

    def test_message_is_announced_through_exactly_one_live_region(self):
        report = function_source(
            self.js, "function reportAcquisitionOutcome(", "async function loadNavidromeSettings("
        )
        self.assertIn(
            "const target = page && (page.querySelector('.status-line') || page.querySelector('.muted[aria-live]'));",
            report,
        )
        self.assertIn("const liveRegion = target || $('appStatusAnnouncer');", report)
        self.assertEqual(report.count("liveRegion.textContent = message;"), 1)
        # The old early return dropped feedback entirely on views with no status line.
        self.assertNotIn("if (!target) return;", report)

    def test_toast_is_visual_only_so_notyf_does_not_speak_second(self):
        self.assertIn(
            "acquisitionToasts.view.container.setAttribute('aria-hidden', 'true');", self.js
        )
        self.assertIn(
            "acquisitionToasts.view.a11yContainer.setAttribute('aria-live', 'off');", self.js
        )

    def test_toast_surface_uses_design_tokens_not_notyf_defaults(self):
        setup = function_source(
            self.js, "const acquisitionToasts = typeof Notyf === 'function'", "function reportAcquisitionOutcome("
        )
        self.assertIn("backgroundColor: 'var(--surface-raised)'", setup)
        # Notyf's stock teal/red fills would bypass the token palette.
        self.assertNotIn("#3dc763", setup)
        self.assertNotIn("#ed3d3d", setup)
        # Only the surface colour and duration are overridden; class names and icons survive.
        self.assertNotIn("className:", setup)

    def test_toast_motion_is_reduced_without_skipping_removal(self):
        self.assertIn("animation-duration: .01ms !important;", self.css)
        # Notyf drops a toast on animationend, so animation: none would strand it on screen.
        self.assertNotIn(".notyf__toast { animation: none", self.css)

    def test_every_acquisition_outcome_call_site_is_unchanged(self):
        request = function_source(
            self.js, "async function searchAlbum(", "function reportAcquisitionOutcome("
        )
        self.assertIn("reportAcquisitionOutcome(data && data.message, 'success')", request)
        self.assertIn("reportAcquisitionOutcome(error.message, 'error')", request)


class VendoredAssetTests(unittest.TestCase):
    """The toast library ships inside the repository; nothing is fetched at runtime."""

    @classmethod
    def setUpClass(cls):
        cls.index = INDEX_HTML.read_text(encoding="utf-8")

    def test_required_vendor_files_are_present(self):
        for name in ("notyf.min.js", "notyf.min.css", "LICENSE", "README.md"):
            self.assertTrue((VENDOR_DIR / name).is_file(), name + " is missing")

    def test_vendored_files_carry_no_remote_reference(self):
        for name in ("notyf.min.js", "notyf.min.css"):
            text = (VENDOR_DIR / name).read_text(encoding="utf-8")
            self.assertNotIn("http://", text)
            self.assertNotIn("https://", text)
            self.assertNotIn("url(", (VENDOR_DIR / name).read_text(encoding="utf-8"))

    def test_vendor_provenance_records_the_pinned_version(self):
        readme = (VENDOR_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("3.10.0", readme)
        self.assertIn("MIT", (VENDOR_DIR / "LICENSE").read_text(encoding="utf-8"))

    def test_template_loads_vendored_assets_before_the_application(self):
        self.assertNotIn("cdn.jsdelivr", self.index)
        self.assertNotIn("unpkg", self.index)
        self.assertLess(
            self.index.index("/static/vendor/notyf/notyf.min.css"),
            self.index.index("/static/app.css"),
        )
        self.assertLess(
            self.index.index("/static/vendor/notyf/notyf.min.js"),
            self.index.index("/static/app.js"),
        )

    def test_shared_announcer_exists_and_is_a_live_region(self):
        self.assertIn('id="appStatusAnnouncer"', self.index)
        self.assertIn('role="status"', self.index)
        self.assertIn('aria-live="polite"', self.index)
        self.assertIn('class="sr-only"', self.index)


if __name__ == "__main__":
    unittest.main()
