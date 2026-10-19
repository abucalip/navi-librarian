"""Phase 6 item 2 contract: sign-in and first-run setup use the Chart Rundown tokens.

DESIGN_SYSTEM.md sections 4, 5, 6, 7, 9.1, 9.7, 11 and 12; REDESIGN_ROADMAP.md Phase 6.
These are source-contract checks. Rendered behaviour was checked in the browser (see
docs/UI_BACKLOG_EXECUTION.md section 21), not by these tests.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
TEMPLATE = ROOT / "app" / "templates" / "login.html"

REQUIRED_TOKENS = [
    "--ink", "--surface", "--surface-raised", "--edge", "--edge-strong", "--text", "--text-muted",
    "--text-subtle", "--accent", "--on-accent", "--chart-red", "--chart-red-text",
    "--display", "--body",
]


def css_outside_root(css):
    return re.sub(r":root\s*\{.*?\}", "", css, count=1, flags=re.S)


class LoginTemplateTests(unittest.TestCase):
    def setUp(self):
        self.html = TEMPLATE.read_text(encoding="utf-8")

    def test_page_has_a_named_main_landmark_and_one_heading(self):
        self.assertIn('<main id="main"', self.html)
        self.assertEqual(len(re.findall(r"<h1[\s>]", self.html)), 1)

    def test_every_input_has_a_visible_label_and_the_confirmation_hint_is_linked(self):
        for field in ("username", "password", "confirmation"):
            self.assertRegex(self.html, rf'<label for="{field}">', field)
            self.assertRegex(self.html, rf'<input id="{field}"', field)
        self.assertIn('aria-describedby="passwordHint"', self.html)
        self.assertIn('id="passwordHint"', self.html)

    def test_error_region_is_a_live_alert_and_the_form_keeps_its_ids_and_endpoints_in_script(self):
        self.assertRegex(self.html, r'<p id="message"[^>]*role="alert"')
        for ident in ('id="authForm"', 'id="submitButton"', 'id="confirmationWrap"', 'name="confirmation"'):
            self.assertIn(ident, self.html)

    def test_no_inline_style_script_or_third_party_asset(self):
        self.assertNotIn("<style", self.html)
        self.assertNotIn("<script>", self.html)
        self.assertNotIn(' style="', self.html)
        self.assertNotIn("fonts.googleapis.com", self.html)
        self.assertNotIn("fonts.gstatic.com", self.html)
        self.assertIn('<script src="/static/login.js" defer></script>', self.html)

    def test_no_credential_or_configuration_value_is_rendered_into_markup(self):
        for secret_like in ("value=", "sandbox", "secret", "token"):
            self.assertNotIn(secret_like, self.html.lower(), secret_like)


class LoginStylesheetTests(unittest.TestCase):
    def setUp(self):
        self.css = (STATIC / "login.css").read_text(encoding="utf-8")
        self.rules = css_outside_root(self.css)

    def test_tokens_are_defined_on_root_with_the_chart_rundown_values(self):
        for token in REQUIRED_TOKENS:
            self.assertIn(f"{token}:", self.css, token)
        self.assertIn("--chart-red: #ff5a3c", self.css)
        self.assertIn("--ink: #141211", self.css)
        self.assertIn("--accent: #f5d33f", self.css)

    def test_rules_use_tokens_not_literal_colours(self):
        self.assertIsNone(re.search(r"#[0-9a-fA-F]{3,6}\b", self.rules))
        self.assertNotIn("rgba(", self.rules)

    def test_no_shadow_gradient_or_glow_on_the_panel(self):
        self.assertNotIn("box-shadow", self.rules)
        self.assertNotIn("gradient", self.rules)
        self.assertNotIn("filter:", self.rules)

    def test_primary_action_and_inputs_meet_the_44px_target_floor(self):
        self.assertRegex(self.rules, r"button\s*\{[^}]*min-height: 44px")
        self.assertRegex(self.rules, r"input\s*\{[^}]*min-height: 44px")

    def test_focus_is_visible_on_inputs_and_the_button(self):
        self.assertRegex(self.rules, r"button:focus-visible, input:focus-visible \{[^}]*outline: 2px solid var\(--accent\)")

    def test_error_is_carried_by_a_glyph_and_text_not_colour_alone(self):
        self.assertIn(".glyph", self.rules)
        self.assertRegex(self.rules, r"\.message \{[^}]*color: var\(--chart-red-text\)")

    def test_reduced_motion_removes_the_button_transition(self):
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.css)
        self.assertRegex(self.css, r"prefers-reduced-motion: reduce\) \{\s*button \{ transition: none \}")

    def test_display_face_is_limited_to_the_page_heading(self):
        for match in re.finditer(r"([^{}]+)\{([^}]*)\}", self.rules):
            if "var(--display)" in match.group(2):
                self.assertIn("h1", match.group(1), match.group(1))

    def test_no_font_weight_outside_the_shipped_faces(self):
        self.assertNotIn("font: 800", self.rules)
        self.assertNotIn("font-weight: 800", self.rules)

    def test_labels_and_hints_use_the_ui_face_not_mono(self):
        self.assertNotIn("var(--mono)", self.rules)


class LoginScriptTests(unittest.TestCase):
    def setUp(self):
        self.js = (STATIC / "login.js").read_text(encoding="utf-8")

    def test_endpoints_and_setup_confirmation_field_are_unchanged(self):
        self.assertIn("'/api/auth/status'", self.js)
        self.assertIn("'/api/auth/setup'", self.js)
        self.assertIn("'/api/auth/login'", self.js)
        self.assertIn("body.password_confirmation=confirmationInput.value", self.js)

    def test_redirect_happens_only_after_the_server_accepts(self):
        self.assertRegex(self.js, r"if\(!r\.ok\)throw.*\n?.*window\.location\.replace\('/'\)")
        self.assertLess(self.js.index("if(!r.ok)"), self.js.index("window.location.replace('/')"))

    def test_server_text_is_never_inserted_as_markup(self):
        self.assertNotIn("innerHTML", self.js)
        self.assertNotIn("insertAdjacentHTML", self.js)
        self.assertNotIn("outerHTML", self.js)

    def test_error_glyph_is_decorative_and_the_text_is_real(self):
        self.assertIn("setAttribute('aria-hidden','true')", self.js)
        self.assertIn("createTextNode(text)", self.js)

    def test_submit_is_disabled_and_announced_busy_while_pending(self):
        self.assertIn("button.disabled=true", self.js)
        self.assertIn("setAttribute('aria-busy','true')", self.js)
        self.assertIn("removeAttribute('aria-busy')", self.js)

    def test_auth_status_failure_is_reported_with_a_glyph(self):
        self.assertIn("classList.add('is-error')", self.js)


if __name__ == "__main__":
    unittest.main()
