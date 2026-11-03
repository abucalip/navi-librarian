"""Phase 1 contract: fonts and icons are self-hosted, licensed, and within the weight budget.

DESIGN_SYSTEM.md sections 5, 10 and 12; REDESIGN_ROADMAP.md Phase 1.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
FONTS = STATIC / "fonts"
TEMPLATES = ROOT / "app" / "templates"
FONT_BUDGET_BYTES = 180 * 1024
# The Brut font pairs (Settings > Appearance) live in their own stylesheet. A browser fetches a face only when
# the chosen pair uses it, so the default page still downloads only the faces above; this is the ceiling for
# the whole optional set (owner-approved 2026-11-02, about 470 KB at the time of writing).
BRUT_FONT_BUDGET_BYTES = 520 * 1024
ICON_NAMES = [
    # list-music: the Daily lists nav item (Engine 2, Phase 4 slice 4), added with its rail entry.
    "layout-dashboard", "compass", "calendar-plus", "user-round", "list-music", "library", "mic-vocal",
    "download", "settings", "log-out", "search", "chevron-left", "chevron-right", "x", "trash-2",
    "bookmark", "bookmark-check",
    # rotate-cw: shuffle, refresh and try again; skip-forward: use next source (acquisitions group).
    "rotate-cw", "skip-forward",
    # Button groups: save, plug-zap (test connection), sparkles (generate), list-plus (load), plus (load more), chevrons up/down.
    "save", "plug-zap", "sparkles", "list-plus", "plus", "chevron-up", "chevron-down",
    # Library display types: list and grid.
    "list", "layout-grid",
]


class SelfHostedFontTests(unittest.TestCase):
    def test_no_stylesheet_or_template_loads_a_third_party_font(self):
        for path in [STATIC / "app.css", STATIC / "login.css", STATIC / "themes.css", STATIC / "appearance.js",
                     STATIC / "fonts" / "fonts.css", STATIC / "fonts" / "brut-fonts.css",
                     TEMPLATES / "index.html", TEMPLATES / "login.html"]:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("fonts.googleapis.com", text, path.name)
            self.assertNotIn("fonts.gstatic.com", text, path.name)

    def test_both_pages_link_the_self_hosted_stylesheet_and_preload_only_the_display_faces(self):
        for name in ("index.html", "login.html"):
            text = (TEMPLATES / name).read_text(encoding="utf-8")
            self.assertIn('href="/static/fonts/fonts.css"', text, name)
            preloads = re.findall(r'<link rel="preload"[^>]*href="([^"]+)"', text)
            self.assertEqual(preloads, ["/static/fonts/peace-sans-latin-400-normal.woff2", "/static/fonts/big-shoulders-display-700.woff2"], name)
            self.assertIn("crossorigin", text.split("/static/fonts/big-shoulders-display-700.woff2")[1].split(">")[0], name)

    def test_every_face_declared_is_shipped_with_swap_and_the_total_is_within_budget(self):
        css = (FONTS / "fonts.css").read_text(encoding="utf-8")
        urls = re.findall(r'url\("([^"]+\.woff2)"\)', css)
        self.assertEqual(len(urls), 8)
        self.assertEqual(css.count("font-display: swap"), 8)
        total = 0
        for url in urls:
            path = FONTS / url
            self.assertTrue(path.is_file(), url)
            total += path.stat().st_size
        self.assertLessEqual(total, FONT_BUDGET_BYTES)

    def test_brut_font_faces_are_shipped_with_swap_within_their_own_budget_and_not_preloaded(self):
        css = (FONTS / "brut-fonts.css").read_text(encoding="utf-8")
        urls = re.findall(r'url\("([^"]+\.woff2)"\)', css)
        self.assertEqual(len(urls), 24)
        self.assertEqual(css.count("font-display: swap"), 24)
        self.assertEqual(len(set(urls)), 24)
        total = 0
        for url in urls:
            path = FONTS / url
            self.assertTrue(path.is_file(), url)
            total += path.stat().st_size
        self.assertLessEqual(total, BRUT_FONT_BUDGET_BYTES)
        for name in ("index.html", "login.html"):
            text = (TEMPLATES / name).read_text(encoding="utf-8")
            self.assertIn('href="/static/fonts/brut-fonts.css"', text, name)
            self.assertNotIn("brut", " ".join(re.findall(r'<link rel="preload"[^>]*href="([^"]+)"', text)), name)

    def test_each_brut_font_family_ships_its_ofl_licence(self):
        for family in ("space-grotesk", "public-sans", "rubik-mono-one", "ibm-plex-mono", "bebas-neue", "outfit", "dm-mono",
                       "inter", "inter-tight", "anton", "barlow", "space-mono", "roboto-mono", "ibm-plex-sans"):
            licence = (FONTS / f"LICENSE-{family}.txt").read_text(encoding="utf-8")
            self.assertIn("SIL OPEN FONT LICENSE VERSION 1.1", licence.upper(), family)

    def test_each_font_family_ships_its_ofl_licence(self):
        for family in ("big-shoulders-display", "peace-sans", "open-sans", "jetbrains-mono"):
            licence = (FONTS / f"LICENSE-{family}.txt").read_text(encoding="utf-8")
            self.assertIn("SIL OPEN FONT LICENSE VERSION 1.1", licence.upper(), family)


class IconSpriteTests(unittest.TestCase):
    def test_sprite_contains_the_initial_lucide_set_and_nothing_else(self):
        sprite = (STATIC / "icons.svg").read_text(encoding="utf-8")
        ids = re.findall(r'<symbol id="([^"]+)"', sprite)
        self.assertEqual(ids, ICON_NAMES)
        self.assertIn('stroke="currentColor"', sprite)
        self.assertNotIn("<script", sprite)

    def test_lucide_licence_is_vendored_beside_the_sprite(self):
        licence = (STATIC / "vendor" / "lucide" / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("ISC License", licence)


if __name__ == "__main__":
    unittest.main()


class ThemeAndFontChoiceTests(unittest.TestCase):
    """Settings > Appearance: eighteen themes and seven font pairs, applied before first paint from localStorage."""

    THEME_IDS = ["ink", "vinyl", "nocturne", "parchment", "gallery", "sleeve", "cassette", "mintdesk", "nightshift", "tapelime", "tapecobalt", "tapetangerine", "ledgerslate", "ledgerplum", "ledgermono", "cratekraft", "cratemint", "cratenight"]
    FONT_IDS = ["discair", "baseline", "technical", "editorial", "modern", "shout", "swiss"]

    def test_every_theme_and_font_in_the_script_has_a_stylesheet_block_except_the_defaults(self):
        script = (STATIC / "appearance.js").read_text(encoding="utf-8")
        css = (STATIC / "themes.css").read_text(encoding="utf-8")
        themes = script.split("var THEMES = [")[1].split("];")[0]
        fonts = script.split("var FONTS = [")[1].split("];")[0]
        self.assertEqual(re.findall(r"id: '(\w+)'", themes), self.THEME_IDS)
        self.assertEqual(re.findall(r"id: '(\w+)'", fonts), self.FONT_IDS)
        for theme in self.THEME_IDS[1:]:  # ink is the :root of app.css
            self.assertIn(f':root[data-theme="{theme}"]', css, theme)
        for font in self.FONT_IDS[1:]:  # the Discair pair is the :root of app.css
            self.assertIn(f':root[data-font="{font}"]', css, font)

    def test_neobrut_themes_are_the_ones_the_script_marks_as_brut(self):
        script = (STATIC / "appearance.js").read_text(encoding="utf-8")
        css = (STATIC / "themes.css").read_text(encoding="utf-8")
        themes = script.split("var THEMES = [")[1].split("];")[0]
        brut = [m.group(1) for m in re.finditer(r"id: '(\w+)'[^}]*brut: true", themes)]
        self.assertEqual(brut, ["cassette", "mintdesk", "nightshift", "tapelime", "tapecobalt", "tapetangerine", "ledgerslate", "ledgerplum", "ledgermono", "cratekraft", "cratemint", "cratenight"])
        for theme in self.THEME_IDS[1:]:
            block = css.split(f':root[data-theme="{theme}"]')[1].split("}")[0]
            self.assertEqual("--brut-sh:" in block, theme in brut, theme)

    def test_both_pages_apply_the_saved_choice_before_the_stylesheets_and_the_wordmark_dots_follow_the_accent(self):
        for name in ("index.html", "login.html"):
            text = (TEMPLATES / name).read_text(encoding="utf-8")
            self.assertLess(text.index('src="/static/appearance.js"'), text.index('rel="stylesheet"'), name)
            self.assertIn('<script src="/static/appearance.js"></script>', text, name)
            self.assertIn('href="/static/themes.css"', text, name)
            self.assertIn('<path class="wordmark-dots"', text, name)
            self.assertNotIn("#f5d33f", text, name)
        for sheet in ("app.css", "login.css"):
            self.assertIn(".wordmark .wordmark-dots { fill: var(--accent); }", (STATIC / sheet).read_text(encoding="utf-8"), sheet)

    def test_accent_as_text_uses_its_own_token_so_pale_neobrut_accents_stay_readable(self):
        css = (STATIC / "app.css").read_text(encoding="utf-8")
        self.assertNotRegex(css, r"(?<![-\w])color: var\(--accent\)")
        self.assertIn("--accent-text: var(--accent)", css)
        themes = (STATIC / "themes.css").read_text(encoding="utf-8")
        self.assertEqual(themes.count("--accent-text:"), len(self.THEME_IDS) - 1)

    def test_settings_appearance_is_exactly_two_pill_rows_font_then_theme(self):
        html = (TEMPLATES / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-settings-tab="appearance"', html)
        panel = html.split('<div id="settingsAppearance"')[1].split("</section>")[0]
        self.assertEqual(panel.count('class="appearance-row"'), 2)
        for control in ("appearanceFont", "appearanceTheme"):
            self.assertIn(f'<div id="{control}" class="appearance-pills" role="radiogroup"', panel, control)
        self.assertLess(panel.index('id="appearanceFont"'), panel.index('id="appearanceTheme"'))
        # nothing else: no heading, no sentence, no status line, no Day or Night rows
        for gone in ("<h3>", "<p ", "appearanceDay", "appearanceNight", "appearanceStatus", "kept on this device only"):
            self.assertNotIn(gone, panel, gone)
        js = (STATIC / "app.js").read_text(encoding="utf-8")
        self.assertIn("appearance: 'settingsAppearance'", js)
        self.assertIn("initAppearanceSettings();", js)
        self.assertIn('type="radio"', js)
        for gone in ("appearance-swatch", "is-group-start", "data-font=", "A.SYSTEM", "appearanceDay"):
            self.assertNotIn(gone, js, gone)

    def test_only_real_buttons_get_a_neobrut_shadow_not_links_inputs_or_circles(self):
        css = (STATIC / "themes.css").read_text(encoding="utf-8")
        rule = next(line for line in css.splitlines() if line.startswith(":root[data-brut] button:not("))
        for link_like in (".inline-link", ".library-link", ".genre-text-link", ".library-artist", ".dashboard-tile-open",
                          ".bio-toggle", ".show-all-button", ".album-review-link", ".owned-album-card", ".album-row-open"):
            self.assertIn(link_like, rule, link_like)
        self.assertNotIn(":where(button, select, input)", css)
        self.assertNotIn("select, input", css)

    def test_text_over_a_fixed_dark_scrim_keeps_light_colours_on_every_theme(self):
        css = (STATIC / "app.css").read_text(encoding="utf-8")
        block = css.split(".artist-stage, .artist-back, .card-art > .artist-bio, .about-toggle {")[1].split("}")[0]
        self.assertIn("--text: #f4efe6", block)
        self.assertIn("--accent-text: #f5d33f", block)

    # ---- Review fixes (impeccable critique, 2026-11-02) ----
    @staticmethod
    def _lum(hex_color):
        channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

    def _contrast(self, a, b):
        x, y = self._lum(a), self._lum(b)
        return (max(x, y) + 0.05) / (min(x, y) + 0.05)

    def _theme_blocks(self):
        css = (STATIC / "themes.css").read_text(encoding="utf-8")
        return {m.group(1): m.group(2) for m in re.finditer(r':root\[data-theme="(\w+)"\] \{(.*?)\n\}', css, re.S)}

    def _token(self, block, name):
        return re.search(rf"--{name}: (#[0-9a-fA-F]{{6}})", block).group(1)

    def test_keyboard_focus_ring_uses_a_visible_focus_token_on_every_theme(self):
        for sheet in ("app.css", "login.css"):
            text = (STATIC / sheet).read_text(encoding="utf-8")
            self.assertNotIn("outline: 2px solid var(--accent)", text, sheet)
            self.assertIn("--focus: var(--accent)", text, sheet)
        for theme, block in self._theme_blocks().items():
            focus = self._token(block, "focus")
            surface = self._token(block, "surface")
            self.assertGreaterEqual(self._contrast(focus, surface), 3.0, f"{theme} focus on surface")
            self.assertGreaterEqual(self._contrast(focus, self._token(block, "ink")), 3.0, f"{theme} focus on page")

    def test_the_muted_text_level_is_always_stronger_than_the_subtle_one_and_both_stay_readable(self):
        for theme, block in self._theme_blocks().items():
            for ground in ("surface", "surface-raised"):
                bg = self._token(block, ground)
                muted, subtle = self._token(block, "text-muted"), self._token(block, "text-subtle")
                self.assertGreaterEqual(self._contrast(subtle, bg), 4.5, f"{theme} subtle on {ground}")
                self.assertGreaterEqual(self._contrast(muted, bg), self._contrast(subtle, bg), f"{theme} muted weaker than subtle on {ground}")

    def test_vinyl_and_sleeve_working_accents_are_not_the_signature_red(self):
        blocks = self._theme_blocks()
        for theme in ("vinyl", "sleeve"):
            accent, red = self._token(blocks[theme], "accent"), self._token(blocks[theme], "chart-red")
            self.assertNotEqual(accent, red, theme)
            # a hue test: the accent must not be a red (red channel dominant over both others by a wide margin)
            r, g, b = (int(accent[i:i + 2], 16) for i in (1, 3, 5))
            self.assertFalse(r > g + 60 and r > b + 60, f"{theme} accent {accent} reads as red")

    def test_names_keep_their_case_pairs_that_capitalise_titles_use_the_body_face_for_names(self):
        css = (STATIC / "app.css").read_text(encoding="utf-8")
        for selector in (".card h3", ".acq-row h3", ".ranked-row h3", ".album-row-name", ".owned-album-name", "#artistDetailHeading", "#albumHeading", ".album-modal-copy h2"):
            start = css.index(selector + " {")
            rule = css[start:css.index("}", start)]
            self.assertIn("var(--name-face)", rule, selector)
            self.assertIn("text-transform: none", rule, selector)
            self.assertNotIn("--title-case", rule, selector)
        themes = (STATIC / "themes.css").read_text(encoding="utf-8")
        for font in ("technical", "editorial", "shout"):
            block = themes.split(f':root[data-font="{font}"]')[1].split("}")[0]
            self.assertIn("--title-case: uppercase", block, font)
            self.assertIn("--name-face: var(--body)", block, font)
        for font in ("baseline", "modern", "swiss"):
            block = themes.split(f':root[data-font="{font}"]')[1].split("}")[0]
            self.assertNotIn("--name-face", block, font)

    def test_technical_has_a_proportional_body_and_a_larger_title_scale(self):
        themes = (STATIC / "themes.css").read_text(encoding="utf-8")
        block = themes.split(':root[data-font="technical"]')[1].split("}")[0]
        self.assertIn('--body: "IBM Plex Sans"', block)
        self.assertIn('--mono: "IBM Plex Mono"', block)
        self.assertIn("--title-scale: 0.8", block)

    def test_the_neobrut_hover_nudge_is_limited_to_devices_that_can_hover(self):
        css = (STATIC / "themes.css").read_text(encoding="utf-8")
        gate = css.index("@media (hover: hover) {")
        # every hover rule that moves something (a transform) sits inside the gate; a colour-only hover may stay outside
        for match in re.finditer(r"translate\(var\(--brut-lift\)", css):
            self.assertGreater(match.start(), gate)

    def test_neobrut_covers_the_artist_hero_search_field_and_caps_the_row_rules(self):
        css = (STATIC / "themes.css").read_text(encoding="utf-8")
        self.assertIn(":root[data-brut] .artist-stage {", css)
        self.assertIn(':root[data-brut] .global-search input[type="search"]', css)
        self.assertIn("border-bottom-width: min(var(--bw), 2px)", css)
        self.assertIn(":root[data-brut] .nav-indicator { display: none; }", css)

    def test_the_browser_bar_follows_the_theme_and_the_labels_match_the_owners_screenshot(self):
        script = (STATIC / "appearance.js").read_text(encoding="utf-8")
        blocks = self._theme_blocks()
        themes = script.split("var THEMES = [")[1].split("];")[0]
        bars = dict(re.findall(r"id: '(\w+)'.*?bar: '(#[0-9a-fA-F]{6})'", themes))
        self.assertEqual(bars["ink"], "#0f0e0d")
        for theme, block in blocks.items():
            self.assertEqual(bars[theme], self._token(block, "ink-rail"), theme)
        self.assertIn("label: 'Ink'", script)
        self.assertIn("label: 'Discair (current)'", script)
        for gone in ("system", "'day'", "'night'", "sw:"):
            self.assertNotIn(gone, script, gone)
        self.assertIn("meta[name=\"theme-color\"]", script)
        for name in ("index.html", "login.html"):
            self.assertIn('<meta name="theme-color"', (TEMPLATES / name).read_text(encoding="utf-8"), name)

    def test_pills_are_plain_text_no_colour_dots_and_no_per_font_typefaces(self):
        css = (STATIC / "app.css").read_text(encoding="utf-8")
        for gone in ("appearance-swatch", "is-group-start", '.appearance-pill[data-font='):
            self.assertNotIn(gone, css, gone)
        self.assertIn("border: max(var(--bw), 2px) solid var(--text)", css)
        self.assertIn(".appearance-pill input:checked + span { color: var(--ink); background: var(--text); }", css)
        self.assertNotIn("appearance-pill", (STATIC / "themes.css").read_text(encoding="utf-8"))

    # ---- Neobrut component layer (neobrut.md) ----
    def test_neobrut_component_layer_covers_every_component_the_page_has(self):
        css = (STATIC / "themes.css").read_text(encoding="utf-8")
        layer = css.split("Neobrut component layer")[1].split("/* ---- Brut font pairs")[0]
        for selector in (
            'input:not([type="search"], [type="radio"], [type="checkbox"], [type="range"]), select, textarea',  # input field
            ".search-field {",                                          # search field (input group)
            ".action-group {",                                          # button group
            ".get-album:not(.action-group .get-album)",                 # button (the Get control)
            'button[aria-pressed="true"]',                              # toggle
            ".header-menu-panel, :root[data-brut] .nav-more-panel",     # dropdown menu
            ".genre-tag, .card-category, .nav-count",                   # tags
            ".album-modal-backdrop",                                    # dialog scrim
            ".dashboard-dot::before",                                   # carousel dots
            ".acq-progress {",                                          # progress bar
            'input[type="range"]::-webkit-slider-thumb',                # slider
            ".skeleton-art",                                            # skeleton
            ".notyf__toast, :root[data-brut] .undo-snackbar",           # toast
            ".radio-switch {",                                          # switch
            ".settings-tabs, .album-tabs",                              # tabs
        ):
            self.assertIn(selector, layer, selector)

    def test_neobrut_buttons_press_down_into_their_shadow_and_inputs_get_a_shadow_sm(self):
        css = (STATIC / "themes.css").read_text(encoding="utf-8")
        self.assertIn("button:not(", css)
        self.assertRegex(css, r":active \{ transform: translate\(calc\(var\(--brut-sh\) \* \.6\), calc\(var\(--brut-sh\) \* \.6\)\); box-shadow: none; \}")
        field = css.split('input:not([type="search"], [type="radio"], [type="checkbox"], [type="range"]), select, textarea) {')[1].split("}")[0]
        self.assertIn("box-shadow: calc(var(--brut-sh) * .5)", field)
        self.assertIn("var(--bw) solid var(--edge)", field)

    def test_neobrut_tabs_are_a_bordered_list_with_the_active_tab_filled_not_an_underline(self):
        css = (STATIC / "themes.css").read_text(encoding="utf-8")
        active = css.split(".album-tabs .album-tab).active {")[1].split("}")[0]
        self.assertIn("background: var(--accent)", active)
        self.assertIn("color: var(--on-accent)", active)
        self.assertNotIn("border-bottom-width", css.split("Neobrut component layer")[0].split(".settings-tab.active")[-1][:200])

    def test_the_undo_action_is_a_real_neobrut_button_not_a_link_like_one(self):
        css = (STATIC / "themes.css").read_text(encoding="utf-8")
        rule = next(line for line in css.splitlines() if line.startswith(":root[data-brut] button:not("))
        self.assertNotIn(".undo-snackbar button", rule)
        self.assertIn(":root[data-brut] .undo-snackbar button {", css)

    # ---- Carousel text and genre tiles (owner review, 2026-11-03) ----
    def test_carousel_text_stays_light_on_the_dark_cover_tint_on_every_theme(self):
        css = (STATIC / "app.css").read_text(encoding="utf-8")
        self.assertIn("var(--slider-fade, var(--ink))", css)
        block = css.split('.dashboard-slider.has-tint > .card[data-slot="1"] > .dashboard-tile-meta, .dashboard-slider.has-tint .dashboard-slider-count {')[1].split("}")[0]
        self.assertIn("--text: #f4efe6", block)
        self.assertIn("--text-muted: #d4cdc0", block)
        self.assertIn("--accent-text: #f5d33f", block)
        # light themes fade the tint to Ink's dark; dark themes already end dark and need nothing
        light = {"parchment", "gallery", "sleeve", "cassette", "mintdesk", "tapelime", "tapecobalt", "tapetangerine", "ledgerslate", "ledgerplum", "ledgermono", "cratekraft", "cratemint"}
        for theme, themed in self._theme_blocks().items():
            self.assertEqual("--slider-fade: #141211" in themed, theme in light, theme)

    def test_neobrut_genre_tiles_are_filled_outlined_and_shadowed(self):
        css = (STATIC / "themes.css").read_text(encoding="utf-8")
        rule = next(line for line in css.splitlines() if line.startswith(":root[data-brut] .genre-tile {"))
        self.assertIn("hsl(var(--genre-hue)", rule)
        self.assertIn("color: #000", rule)
        self.assertIn("var(--bw) solid var(--edge)", rule)
        self.assertIn("box-shadow:", rule)
        self.assertIn(":root[data-brut] .dashboard-slider {", css)

    # ---- Review fixes (owner review, 2026-11-03) ----
    def test_a_long_carousel_title_runs_over_the_first_thumbnail_and_the_bio_keeps_its_column(self):
        css = (STATIC / "app.css").read_text(encoding="utf-8")
        wide = css.split("@media (min-width: 621px) {\n  .dashboard-slider > .card[data-slot=\"1\"] { z-index: 2; pointer-events: none; }")[1].split("\n}\n")[0]
        self.assertIn("pointer-events: auto", wide)
        self.assertIn(".dashboard-tile-meta { padding-bottom: 76px; }", wide)
        self.assertIn("margin-right: calc(-1 * min(var(--thumbs), 1) * (var(--thumb-w) + var(--thumb-gap)))", wide)
        self.assertIn("max-height: calc(3 * var(--title-leading) * 1em)", wide)

    def test_icons_follow_a_stroke_variable_and_a_neobrut_theme_thickens_them_and_blackens_button_icons(self):
        sprite = (STATIC / "icons.svg").read_text(encoding="utf-8")
        self.assertNotIn('stroke-width="1.75"', sprite)
        self.assertIn("stroke-width: var(--icon-stroke, 1.75)", sprite)
        css = (STATIC / "themes.css").read_text(encoding="utf-8")
        self.assertIn(":root[data-brut] { --icon-stroke: 2.3; }", css)
        icons = next(line for line in css.splitlines() if line.startswith(":root[data-brut] :is(.action-group > button, .icon-square-button"))
        self.assertIn("color: var(--text);", icons)

    def test_the_artist_back_button_the_quality_tag_and_the_tabs_get_the_neobrut_treatment(self):
        css = (STATIC / "themes.css").read_text(encoding="utf-8")
        rule = next(line for line in css.splitlines() if line.startswith(":root[data-brut] button:not("))
        self.assertNotIn(".artist-back", rule)
        for needle in (":root[data-brut] .artist-back {", ":root[data-brut] .album-quality {", ":root[data-brut] .album-tabs { margin-left: auto; margin-right: auto; }",
                       ":root[data-brut] .library-control select"):
            self.assertIn(needle, css, needle)
        self.assertIn("background: var(--surface)", next(l for l in css.splitlines() if l.startswith(":root[data-brut] .album-quality {")))

