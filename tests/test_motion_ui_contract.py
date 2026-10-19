"""Contracts for the Phase 7 motion table (docs/DESIGN_SYSTEM.md section 11).

Only transform and opacity animate; no transition is declared on `all`; durations come from the
motion tokens; and reduced motion leaves each animated state at its end state. These tests read
the stylesheets and script as text, as the other *_ui_contract.py files do.
"""
import re
import unittest
from pathlib import Path


STATIC = Path(__file__).resolve().parents[1] / "static"
ALLOWED_PROPERTIES = {"transform", "opacity"}
# Looping motions have no token in DESIGN_SYSTEM.md section 11; their existing periods are kept.
LOOP_DURATIONS = {"1.15s", "1.4s"}


def declared_transition_properties(css):
    names = set()
    for value in re.findall(r"(?<![-\w])transition:\s*([^;}]+)", css):
        for part in value.split(","):
            token = part.strip().split(" ")[0]
            if token and token not in {"var(--dur)", "var(--dur-fast)", "var(--dur-slow)"}:
                names.add(token)
    return names


def keyframe_bodies(css):
    return re.findall(r"@keyframes [\w-]+ \{((?:[^{}]|\{[^{}]*\})*)\}", css)


class MotionTableContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_css = (STATIC / "app.css").read_text(encoding="utf-8")
        cls.login_css = (STATIC / "login.css").read_text(encoding="utf-8")
        cls.js = (STATIC / "app.js").read_text(encoding="utf-8")

    def test_no_transition_is_declared_on_all(self):
        self.assertNotIn("transition: all", self.app_css)
        self.assertNotIn("transition: all", self.login_css)

    def test_transitions_only_animate_transform_or_opacity(self):
        for css in (self.app_css, self.login_css):
            names = declared_transition_properties(css)
            self.assertLessEqual(names, ALLOWED_PROPERTIES | {"none"}, names)

    def test_keyframes_only_animate_transform_or_opacity(self):
        for body in keyframe_bodies(self.app_css):
            properties = set(re.findall(r"([a-z-]+):", body))
            self.assertLessEqual(properties, ALLOWED_PROPERTIES, body)

    def test_no_dash_offset_or_size_animation_remains(self):
        self.assertNotIn("stroke-dashoffset", self.app_css)
        self.assertNotIn("get-tick-draw", self.app_css)
        self.assertNotRegex(self.app_css, r"animation:[^;]*\b(width|height|top|left)\b")

    def test_durations_are_tokens_except_the_two_looping_periods(self):
        literal = re.findall(r"(?:transition|animation):[^;}]*?(\d*\.?\d+m?s)\b", self.app_css)
        unexpected = {value for value in literal if value not in LOOP_DURATIONS and value not in {"0s", ".01ms"}}
        # 120ms, 180ms and 260ms are the tokens themselves; they only appear inside the :root block.
        self.assertEqual(unexpected, set(), unexpected)

    def test_menu_fade_is_opacity_only(self):
        self.assertIn("@keyframes header-menu-in { from { opacity: 0; } to { opacity: 1; } }", self.app_css)
        self.assertIn("animation: header-menu-in var(--dur) var(--ease-out);", self.app_css)

    def test_card_hover_has_no_lift(self):
        self.assertNotRegex(self.app_css, r"\.card:hover \{[^}]*translateY")

    def test_reduced_motion_ends_every_animation_at_its_end_state(self):
        reduced = self.app_css[self.app_css.index("/* The async Get button"):self.app_css.index("/* Ranked rows")]
        self.assertIn(".get-album.is-pending .get-album-arc { animation: none; }", reduced)
        self.assertIn(".get-album.requested .get-album-tick { animation: none; opacity: 1; transform: none; }", reduced)
        self.assertIn(".header-menu-panel:not([hidden]) { animation: none; }", self.app_css)
        self.assertIn(".acq-row.is-skeleton { animation: none; }", self.app_css)
        self.assertIn(".ranked-row.is-skeleton { animation: none; }", self.app_css)
        self.assertIn(".album-modal-backdrop, .album-modal { animation: none; }", self.app_css)

    def test_sort_reorder_is_flip_on_transform_and_respects_reduced_motion(self):
        reorder = self.js[self.js.index("function reorderRecommendations(render) {"):self.js.index("// Describes the order the rows are shown in.")]
        self.assertIn("matchMedia('(prefers-reduced-motion: reduce)')", reorder)
        self.assertIn("row.animate(", reorder)
        self.assertIn("transform: `translateY(${distance}px)`", reorder)
        self.assertIn("'--dur-slow'", reorder)
        self.assertIn("'--ease-out'", reorder)
        # Only the sort control reorders with motion; search and filters re-render without it.
        self.assertIn("$('recommendationSort').addEventListener('change', () => reorderRecommendations(applyRecommendationFilters));", self.js)
        self.assertEqual(self.js.count("reorderRecommendations("), 2)


if __name__ == "__main__":
    unittest.main()
