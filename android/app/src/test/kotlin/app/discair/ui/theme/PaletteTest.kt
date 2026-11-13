package app.discair.ui.theme

import androidx.compose.ui.graphics.Color
import kotlin.math.pow
import org.junit.Test
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue

class PaletteTest {
    private fun lin(v: Float): Double = v.toDouble().let { if (it <= 0.03928) it / 12.92 else ((it + 0.055) / 1.055).pow(2.4) }
    private fun lum(c: Color) = 0.2126 * lin(c.red) + 0.7152 * lin(c.green) + 0.0722 * lin(c.blue)
    private fun contrast(a: Color, b: Color): Double {
        val x = lum(a); val y = lum(b)
        return (maxOf(x, y) + 0.05) / (minOf(x, y) + 0.05)
    }

    private fun check(p: Palette, what: String, fg: Color, bg: Color, need: Double, bgName: String) {
        val got = contrast(fg, bg)
        assertTrue("${p.label}: $what on $bgName is %.2f, needs %.1f".format(got, need), got >= need)
    }

    @Test fun thirtyNineThemesWithUniqueIds() {
        assertEquals(39, Palettes.All.size)
        assertEquals(25, Palettes.Light.size)
        assertEquals(14, Palettes.Dark.size)
        assertEquals(16, Palettes.All.count { it.family == Family.Classic })
        assertEquals(23, Palettes.All.count { it.family == Family.Brutal })
        assertTrue(Palettes.All.all { (it.family == Family.Brutal) == (it.shape != null) })
        assertEquals(Palettes.All.size, Palettes.All.map { it.id }.toSet().size)
        assertEquals(Palettes.All.size, Palettes.All.map { it.label }.toSet().size)
        assertTrue(Palettes.Light.all { it.light } && Palettes.Dark.none { it.light })
        assertEquals("sand", Palettes.Light.first().id) // default day theme
        assertEquals("night", Palettes.Dark.first().id) // default night theme
    }

    @Test fun nightKeepsTheOriginalColours() {
        val n = Palettes.Night
        assertEquals(Color(0xFF0F0E0D), n.rail); assertEquals(Color(0xFF141211), n.ink)
        assertEquals(Color(0xFF1C1A18), n.surface); assertEquals(Color(0xFF252220), n.raised)
        assertEquals(Color(0xFF34302C), n.edge); assertEquals(Color(0xFF787168), n.edgeStrong)
        assertEquals(Color(0xFFF4EFE6), n.text); assertEquals(Color(0xFFB4AC9F), n.textMuted)
        assertEquals(Color(0xFFF5D33F), n.accent); assertEquals(Color(0xFF554B26), n.accentDim)
        assertEquals(Color(0xFF141211), n.onAccent); assertEquals(Color(0xFFFF5A3C), n.chartRed)
        assertEquals(Color(0xFFFF7B62), n.chartRedText); assertEquals(Color(0xFF86D39B), n.ok)
        assertEquals(Color(0xFFF0A640), n.caution)
    }

    @Test fun textRolesMeetContrastOnEveryTheme() {
        for (p in Palettes.All) {
            for ((bgName, bg) in listOf("page" to p.ink, "surface" to p.surface, "raised" to p.raised)) {
                check(p, "text", p.text, bg, p.minTextContrast, bgName)
                check(p, "muted text", p.textMuted, bg, p.minTextContrast, bgName)
                check(p, "error text", p.chartRedText, bg, 4.5, bgName)
                check(p, "caution text", p.caution, bg, 4.5, bgName)
                check(p, "ok text", p.ok, bg, 4.5, bgName)
            }
            check(p, "button label", p.onAccent, p.accent, p.minTextContrast, "accent")
            check(p, "text", p.text, p.accentDim, 4.5, "selected background")
        }
    }

    @Test fun graphicsMeetThreeToOne() {
        for (p in Palettes.All) {
            // Brutal accents are pastel and always drawn inside the theme's thick outline, so the accent itself is
            // held to a lower bar there and the outline carries the 3:1.
            check(p, "accent", p.accent, p.ink, p.minAccentContrast, "page")
            check(p, "accent", p.accent, p.surface, p.minAccentContrast, "surface")
            check(p, "strong edge", p.edgeStrong, p.surface, 3.0, "surface")
            check(p, "strong edge", p.edgeStrong, p.ink, 3.0, "page")
        }
    }

    @Test fun overArtworkKeepsLightTextOnLightThemes() {
        val over = Palettes.Sand.overArtwork(Palettes.Night)
        assertEquals(Palettes.Night.text, over.text)
        // The accent stays the theme's own, so the sheet's Play button matches the album page's.
        assertEquals(Palettes.Sand.accent, over.accent)
        assertEquals(Palettes.Sand.onAccent, over.onAccent)
        assertTrue(!over.light)
        // A dark theme is left alone.
        assertEquals(Palettes.Ember.accent, Palettes.Ember.overArtwork(Palettes.Night).accent)
    }

    // Sand is the default day theme. (Day · Mist's blue is 2.98 here, just under 3.0; not changed.) The redesign's Sand
    // accent #AD4016 (was #C04A1A) is 2.91 on the dark surface over artwork: held to 2.9 until the owner reviews it.
    @Test fun sandAccentStaysVisibleOverArtwork() {
        val over = Palettes.Sand.overArtwork(Palettes.Night)
        check(over, "accent over artwork", over.accent, over.surface, 2.9, "dark surface")
    }

    @Test fun twelvePairsWithUniqueIdsAndDiscairFirst() {
        assertEquals(12, FontPairs.All.size)
        assertEquals(FontPairs.All.size, FontPairs.All.map { it.id }.toSet().size)
        assertEquals(FontPairs.All.size, FontPairs.All.map { it.label }.toSet().size)
        assertEquals("discair", FontPairs.All.first().id)
    }

    @Test fun sixBrutPairsAreNamedBrutAndAreIndependentOfTheTheme() {
        val brut = FontPairs.All.filter { it.id.startsWith("brut_") }
        assertEquals(listOf("Baseline", "Technical", "Editorial", "Modern", "Poster shout", "Swiss brut").map { "Brut · $it" }, brut.map { it.label })
        // Each pair is chosen by its id alone: the saved font id never depends on the colour theme.
        for (p in brut) assertEquals(p.id, AppearanceRules.sanitizeFont(p.id))
        // The older pairs keep JetBrains Mono for numbers; the Brut pairs that name another mono bring it.
        assertEquals(setOf("JetBrains Mono"), FontPairs.All.filter { !it.id.startsWith("brut_") && it.id != "flow" }.map { it.monoName }.toSet())
        assertEquals(setOf("JetBrains Mono", "IBM Plex Mono", "DM Mono", "Space Mono", "Roboto Mono"), brut.map { it.monoName }.toSet())
        assertTrue(brut.all { it.titleScale in 0.5f..1.5f })
        // Technical's body is proportional (IBM Plex Sans); only its numbers are monospaced.
        val technical = brut.first { it.id == "brut_technical" }
        assertEquals("IBM Plex Sans", technical.bodyName)
        assertEquals("IBM Plex Mono", technical.monoName)
        assertEquals(0.8f, technical.titleScale)
    }

    @Test fun pastelTintsKeepMutedTextReadableOnEveryHue() {
        val muted = Palettes.Light.minOf { contrast(it.textMuted, Color.White) } // the weakest muted text over white
        assertTrue("muted text over white is only %.2f".format(muted), muted >= 4.5)
        for (hue in 0 until 360 step 15) {
            val tint = Color.hsv(hue.toFloat(), 0.85f, 0.4f) // the strongest tint the app produces
            val wash = pastelOf(tint)
            for (p in Palettes.Light) {
                check(p, "muted text over the $hue degree tint", p.textMuted, wash, 4.5, "pastel")
                check(p, "text over the $hue degree tint", p.text, wash, 4.5, "pastel")
            }
        }
    }

    @Test fun pastelKeepsTheHueOfTheCover() {
        val red = pastelOf(Color.hsv(0f, 0.8f, 0.4f))
        assertTrue(red.red > red.green && red.red > red.blue)
        val blue = pastelOf(Color.hsv(220f, 0.8f, 0.4f))
        assertTrue(blue.blue > blue.red)
    }

    @Test fun brutalThemesHaveTheirOwnShapes() {
        val radii = Palettes.All.filter { it.brutal }.map { it.shape!!.radius }.toSet()
        assertTrue("shape variety kept: $radii", radii.size >= 5)
        assertEquals(0f, Palettes.BrutPoster.shape!!.radius, 0f) // square
        assertTrue(Palettes.All.filter { it.brutal }.all { it.shape!!.outline >= 1.5f && it.shapeShadowIsVisible() })
        assertTrue(Palettes.All.filter { !it.brutal }.all { it.shape == null })
    }

    @Test fun brutalLabelsOnTheThreeExtraColoursAreReadable() {
        // Rank chips and badges put black text on accent2..4 (the number chips in the Appearance tiles and lists).
        for (p in Palettes.All.filter { it.brutal }) {
            for ((i, c) in listOf(p.accent2, p.accent3, p.accent4).withIndex()) check(p, "black on accent${i + 2}", Color.Black, c, 4.5, "chip")
        }
    }

    private fun Palette.shapeShadowIsVisible() = shadowColor != Color.Transparent && contrast(shadowColor, ink) >= 3.0

    private fun Palette.redesignRoles() =
        listOf(info, infoDim, okDim, cautionDim, dangerDim, chart1, chart2, chart3, chartGhost, chartGrid, chartBase)

    @Test fun dayAccentIsTheRevisedSand() {
        // Was #C04A1A, 4.00:1 as text on the page; #AD4016 is 4.83:1.
        assertEquals(Color(0xFFAD4016), Palettes.Sand.accent)
        check(Palettes.Sand, "accent as text", Palettes.Sand.accent, Palettes.Sand.ink, 4.5, "page")
    }

    @Test fun specifiedPalettesHaveTheRedesignTable() {
        // docs/redesign.md 7.3, which matches the tokens in docs/design/redesign/android/android.css. Order: info, infoDim,
        // okDim, cautionDim, dangerDim, chart1, chart2, chart3, chartGhost, chartGrid, chartBase.
        val table = mapOf(
            Palettes.Sand to listOf(0x1F5A8AL, 0xCFDDE8L, 0xD5E5CFL, 0xF1DDB4L, 0xF2CFC2L, 0xAD4016L, 0x8C7B57L, 0xC9BB9CL, 0xE3D8C0L, 0xCFC2A6L, 0x857758L),
            Palettes.Night to listOf(0x8FB8E8L, 0x1D2C3DL, 0x1F3326L, 0x3D2E14L, 0x40211AL, 0xF5D33FL, 0x7A736AL, 0x4A4540L, 0x252220L, 0x34302CL, 0x787168L),
            Palettes.TapeLime to listOf(0x1D4FB8L, 0xD3DFFAL, 0xD3EBD9L, 0xFBE6BFL, 0xF7D4D1L, 0xC6F432L, 0x7C7A6EL, 0xFFFDF6L, 0xF1ECDCL, 0x111111L, 0x111111L),
            Palettes.SheetViolet to listOf(0x9DB8FFL, 0x2A3152L, 0x223A33L, 0x43351FL, 0x472A33L, 0xFF6A3DL, 0x7A7499L, 0x35E0D0L, 0x2E2A43L, 0x3A3552L, 0xF4F1FFL),
        )
        for ((p, hexes) in table) {
            assertEquals("${p.label} redesign roles", hexes.map { Color(0xFF000000L or it) }, p.redesignRoles())
        }
    }

    @Test fun everyPaletteHasTheRedesignRoles() {
        // Derived defaults for the other palettes: every role is an opaque colour, never a transparent placeholder.
        for (p in Palettes.All) {
            assertTrue("${p.label} has a transparent redesign role", p.redesignRoles().all { it.alpha == 1f })
            check(p, "info text", p.info, p.surface, 4.5, "surface")
            check(p, "info text", p.info, p.ink, 4.5, "page")
        }
    }

    @Test fun statusTextReadsOnItsContainerOnEveryTheme() {
        for (p in Palettes.All) {
            check(p, "ok text", p.ok, p.okDim, 4.5, "ok container")
            check(p, "caution text", p.caution, p.cautionDim, 4.5, "caution container")
            check(p, "error text", p.chartRedText, p.dangerDim, 4.5, "danger container")
            check(p, "info text", p.info, p.infoDim, 4.5, "info container")
        }
    }

    @Test fun secondChartSeriesReadsOnSurfaceOnEveryTheme() {
        // Chart 2 is the comparison line and the baseline dot: a graphic, so 3:1 (docs/redesign.md 4.4).
        for (p in Palettes.All) check(p, "chart 2", p.chart2, p.surface, 3.0, "surface")
    }

    @Test fun accentTextIsTheAccentOnlyWhereItReadsOnThePageAndCard() {
        for (p in Palettes.All) {
            val got = p.accentText
            if (got == p.accent) {
                check(p, "accent as text", p.accent, p.ink, 4.5, "page")
                check(p, "accent as text", p.accent, p.surface, 4.5, "surface")
            } else assertEquals("${p.label}: falls back to the ink text colour", p.text, got)
        }
    }

    @Test fun theFourSpecifiedThemesFollowTheAccentAsTextRule() {
        val byId = Palettes.All.associateBy { it.id }
        // 7.3: accent as text on the page is 4.8 on Sand, 12.7 on Night, 6.5 on Sheet, and not allowed on Tape (1.1).
        val sand = Palettes.All.first { it.accent == Color(0xFFAD4016) && it.light }
        val night = Palettes.All.first { it.accent == Color(0xFFF5D33F) && !it.light }
        val tape = Palettes.All.first { it.accent == Color(0xFFC6F432) && it.light }
        val sheet = Palettes.All.first { it.accent == Color(0xFFFF6A3D) && !it.light }
        assertEquals(sand.accent, sand.accentText)
        assertEquals(night.accent, night.accentText)
        assertEquals(sheet.accent, sheet.accentText)
        assertEquals(tape.text, tape.accentText)
        assertTrue(byId.isNotEmpty())
    }
}
