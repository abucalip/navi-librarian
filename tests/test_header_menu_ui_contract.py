"""Source-contract regressions for the header gear menu that holds Settings and Log out.

These read the shipped template, stylesheet and script as source and never open a browser,
so they do not replace the manual browser checklist in docs/LOCAL_UI_TESTING.md. They guard
the points most likely to regress silently: the Settings page opening empty if the menu
bypasses initializePage, Log out losing its endpoint or redirect, the skip link losing its
place as the first tab stop, and the Safari focusout rule.
"""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "app" / "templates" / "index.html"
APP_JS = ROOT / "static" / "app.js"
APP_CSS = ROOT / "static" / "app.css"


def _function_body(source, signature):
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for position in range(brace, len(source)):
        char = source[position]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace:position + 1]
    raise AssertionError(f"unterminated body for {signature}")


class HeaderMenuMarkupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        nav_start = cls.html.index('<nav aria-label="Main">')
        nav_end = cls.html.index("</nav>", nav_start)
        cls.rail = cls.html[nav_start:nav_end]
        header_start = cls.html.index("<header>")
        header_end = cls.html.index("</header>", header_start)
        cls.header = cls.html[header_start:header_end]

    def test_rail_no_longer_contains_settings_or_logout(self):
        self.assertNotIn('data-page="settings"', self.rail)
        self.assertNotIn('id="logoutButton"', self.rail)

    def test_header_menu_contains_settings_and_logout_in_order(self):
        panel = self.header[self.header.index('id="appMenu"'):]
        self.assertLess(panel.index('data-page="settings"'), panel.index('id="logoutButton"'))

    def test_logout_button_id_is_unique(self):
        self.assertEqual(self.html.count('id="logoutButton"'), 1)

    def test_toggle_is_a_named_disclosure_controlling_the_panel(self):
        toggle = re.search(r'<button id="appMenuButton"[^>]*>', self.header).group(0)
        self.assertIn('aria-expanded="false"', toggle)
        self.assertIn('aria-controls="appMenu"', toggle)
        self.assertIn('aria-label="Settings and account"', toggle)
        self.assertNotIn("aria-haspopup", toggle)
        self.assertIn('id="appMenu"', self.header)

    def test_toggle_glyph_is_hidden_from_assistive_tech(self):
        svg = re.search(r"<svg[^>]*>", self.header).group(0)
        self.assertIn('aria-hidden="true"', svg)
        self.assertIn('focusable="false"', svg)

    def test_panel_is_hidden_in_shipped_markup(self):
        self.assertRegex(self.header, r'<div id="appMenu" class="header-menu-panel" hidden>')

    def test_skip_link_precedes_header_so_it_stays_first_tab_stop(self):
        self.assertLess(self.html.index('class="skip-link"'), self.html.index("<header>"))

    def test_element_ids_stay_unique(self):
        ids = re.findall(r'\bid="([^"]+)"', self.html)
        duplicates = {value for value in ids if ids.count(value) > 1}
        self.assertEqual(duplicates, set())


class HeaderMenuScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")

    def test_shared_navigation_runs_initialize_and_stop_stream(self):
        body = _function_body(self.js, "function navigateTo(name)")
        self.assertIn("showPage(name)", body)
        self.assertIn("initializePage(name)", body)
        self.assertIn("stopAcquisitionStream()", body)

    def test_rail_and_menu_share_the_click_binding(self):
        self.assertIn("nav button[data-page], .header-menu button[data-page]", self.js)
        self.assertIn("navigateTo(button.dataset.page)", self.js)

    def test_show_page_and_aria_sync_cover_the_menu_selector(self):
        self.assertIn("'appMenuButton').classList.toggle('is-current'", self.js)
        sync_body = _function_body(self.js, "function syncNavAria()")
        self.assertIn(".header-menu button[data-page]", sync_body)

    def test_logout_keeps_endpoint_and_redirect_and_guards_duplicates(self):
        self.assertIn("/api/auth/logout", self.js)
        self.assertIn("window.location.replace('/login')", self.js)
        self.assertIn("button.disabled = true", self.js)
        self.assertIn("aria-busy", self.js)

    def test_escape_closes_menu_only_after_album_modal_check(self):
        modal_check = self.js.index("if (event.key === 'Escape' && albumModalOpen) closeAlbumModal();")
        menu_check = self.js.index("else if (event.key === 'Escape' && !appMenu.hidden)")
        self.assertLess(modal_check, menu_check)
        self.assertIn("focusToggle: true", self.js[menu_check:menu_check + 120])

    def test_focusout_requires_a_real_element_outside_the_container(self):
        self.assertIn("'focusout'", self.js)
        self.assertIn("if (next && !appMenuContainer.contains(next))", self.js)

    def test_arrow_home_end_navigation_is_wired(self):
        for key in ("ArrowDown", "ArrowUp", "Home", "End"):
            self.assertIn(f"'{key}'", self.js)


class HeaderMenuStyleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = APP_CSS.read_text(encoding="utf-8")

    def test_menu_shadow_is_a_named_token(self):
        self.assertIn("--shadow-menu: 0 8px 24px rgba(0,0,0,.45);", self.css)
        self.assertIn("box-shadow: var(--shadow-menu)", self.css)

    def test_current_settings_state_is_defined(self):
        self.assertIn('.header-menu-panel button[aria-current="page"]', self.css)
        self.assertIn(".header-menu-toggle.is-current", self.css)

    def test_item_focus_ring_is_inset(self):
        self.assertRegex(self.css, r"\.header-menu-panel button:focus-visible \{[^}]*outline-offset: -2px")

    def test_reduced_motion_disables_panel_animation(self):
        self.assertRegex(
            self.css,
            r"@media \(prefers-reduced-motion: reduce\) \{ \.header-menu-panel:not\(\[hidden\]\) \{ animation: none; \} \}",
        )

    def test_toggle_meets_touch_target_floor(self):
        self.assertRegex(self.css, r"\.header-menu-toggle \{[^}]*width: 44px;[^}]*height: 44px;")


if __name__ == "__main__":
    unittest.main()
