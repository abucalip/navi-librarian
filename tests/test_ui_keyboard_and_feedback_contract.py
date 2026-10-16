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

    def test_scroll_helper_is_wired_to_the_genre_rows_only(self):
        # The dashboard list is a ring now, not a scroller, so it must not take the scroll
        # helper's tab stop; its keyboard contract is the ring's own (see DashboardRingTests).
        dashboard = function_source(
            self.js, "async function loadDashboardPicks(", "$('shuffleDashboard')"
        )
        self.assertNotIn("makeScrollTrackFocusable(target)", dashboard)
        self.assertIn("buildDashboardRing(target);", dashboard)
        self.assertIn(
            "makeScrollTrackFocusable(track, genreRowLabel(genre) + ' albums');", self.js
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
            "{ outline: 2px solid var(--yellow); outline-offset: 2px; border-radius: 4px; }",
            self.css,
        )


class DashboardRingTests(unittest.TestCase):
    """The dashboard list is a coverflow ring, steered rather than merely animated."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = APP_CSS.read_text(encoding="utf-8")
        cls.index = INDEX_HTML.read_text(encoding="utf-8")

    def _ring(self, signature, next_signature):
        return function_source(self.js, signature, next_signature)

    def test_ring_is_opt_in_so_the_flat_list_survives_a_failure(self):
        build = self._ring("function buildDashboardRing(scene) {", "async function loadDashboardPicks(")
        # The class is added only once the stage exists; without it the existing flat flex
        # row is still what renders.
        self.assertIn("scene.classList.add('is-ring');", build)
        self.assertIn(".dashboard-carousel > .card { flex: 0 0 218px;", self.css)
        self.assertIn(".dashboard-carousel.is-ring { display: block;", self.css)

    def test_ring_needs_at_least_three_albums(self):
        build = self._ring("function buildDashboardRing(scene) {", "async function loadDashboardPicks(")
        self.assertIn("if (cards.length < 3) return;", build)

    def test_geometry_radius_spaces_neighbours_edge_to_edge(self):
        build = self._ring("function buildDashboardRing(scene) {", "async function loadDashboardPicks(")
        self.assertIn("Math.tan(Math.PI / RING.count)", build)
        for name in ("--ring-step", "--ring-radius", "--ring-card-width"):
            self.assertIn(name, build)

    def test_ambient_rotation_yields_to_reading_acting_and_being_unseen(self):
        ambient = self._ring("function ringAmbientVelocity() {", "function ringSettled()")
        self.assertIn("if (document.hidden || !RING.onscreen || RING.dragging) return 0;", ambient)
        self.assertIn("if (RING.pointerOver || RING.focusWithin) return 0;", ambient)
        self.assertIn("if (RING_REDUCED_MOTION.matches) return 0;", ambient)
        self.assertIn("return RING_BASE_VELOCITY;", ambient)

    def test_loop_stops_when_settled_instead_of_spinning_forever(self):
        start = self._ring("function ringStart() {", "// Exactly one card is legible")
        self.assertIn("if (!RING.raf && RING.stage && !ringSettled())", start)
        frame = self._ring("function ringFrame() {", "function ringStart() {")
        # The boost is driven to exactly zero, so ringSettled() can actually become true.
        self.assertIn("Math.abs(RING.boost) < 0.02 ? 0 : RING.boost * RING_BOOST_DECAY", frame)
        self.assertIn("if (!ringSettled()) ringStart();", frame)

    def test_reduced_motion_removes_the_ambient_loop_but_keeps_steering(self):
        # A reduced-motion path that also disabled the keys would leave one album reachable
        # and the other nine stranded.
        self.assertIn("if (RING_REDUCED_MOTION.matches) return 0;", self.js)
        keys = self._ring("function ringKeyDown(event) {", "// Zoom the ring out until it fits")
        self.assertIn("'ArrowRight'", keys)
        self.assertIn("'ArrowLeft'", keys)
        self.assertNotIn("RING_REDUCED_MOTION", keys)

    def test_drag_and_keys_accelerate_and_then_ease_out(self):
        move = self._ring("function ringPointerMove(event) {", "function ringPointerUp() {")
        self.assertIn("RING.boost + degrees * 0.3", move)
        self.assertIn("RING_BOOST_MAX", move)
        # The reference component's stated limitation is that rotation snaps on release.
        self.assertIn("RING.boost * RING_BOOST_DECAY", self.js)

    def test_only_the_front_card_is_operable(self):
        apply_front = self._ring("function ringApplyFront(index) {", "function ringPointerDown(event)")
        self.assertIn("card.classList.toggle('is-front', isFront);", apply_front)
        self.assertIn("card.tabIndex = isFront ? 0 : -1;", apply_front)
        self.assertIn("else card.setAttribute('aria-hidden', 'true');", apply_front)
        self.assertIn("if (RING.inert) card.inert = !isFront;", apply_front)

    def test_a_drag_does_not_open_the_album_dialog(self):
        down = self._ring("function ringPointerDown(event) {", "function ringPointerMove(event) {")
        move = self._ring("function ringPointerMove(event) {", "function ringPointerUp() {")
        self.assertIn("RING.suppressClick = false;", down)
        self.assertIn("if (RING.dragDistance > 6) RING.suppressClick = true;", move)
        self.assertIn("if (!RING.suppressClick) return;", self.js)

    def test_clipping_stays_outside_the_3d_context(self):
        # overflow on the element that establishes preserve-3d flattens its children.
        self.assertIn("transform-style: preserve-3d;", self.css)
        self.assertIn(".dashboard-carousel.is-ring { display: block; padding: 16px 0 0; overflow: hidden;", self.css)
        self.assertIn(".ring-scene { perspective: 2000px; }", self.css)

    def test_ring_joins_the_existing_token_and_control_vocabulary(self):
        self.assertIn(".dashboard-carousel.is-ring .ring-card:focus-visible { outline: 2px solid var(--yellow);", self.css)
        # Depth is an offset plus a soft blur, not a halo.
        self.assertIn("box-shadow: 0 22px 48px rgba(0,0,0,.52);", self.css)
        self.assertIn('aria-label="Random album recommendations"', self.index)
        self.assertIn('role="group"', self.index)
        # The gesture is named in copy a user can read.
        self.assertIn("Drag the ring, or focus it and use", self.index)


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
        self.assertIn("albumModalReturnFocus = card;", self.js)
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
