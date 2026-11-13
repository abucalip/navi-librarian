package app.discair.ui.theme

import app.discair.ui.NavRules
import app.discair.ui.common.CoverStackRules
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Step S1 of docs/ANDROID_ART_THEMES_PROPOSAL.md: the Soft Brut palette, its layout, its shell rules and its contrast. */
class SoftBrutTest {
    private val p = Palettes.SoftBrut
    private fun ratio(a: androidx.compose.ui.graphics.Color, b: androidx.compose.ui.graphics.Color) = Contrast.ratio(a, b)

    @Test fun softBrutIsALightBrutalCoverStackTheme() {
        assertEquals("softbrut", p.id); assertEquals("Soft Brut · Lavender", p.label)
        assertEquals(Layout.CoverStack, p.layout); assertEquals("Cover Stack", p.layout.label)
        assertEquals(Family.Brutal, p.family)
        assertTrue(p.light && p in Palettes.Light)
        assertEquals(setOf("softbrut", "softbrut_mint", "softbrut_peach", "softbrut_sky", "softbrut_lemon"), Palettes.All.filter { it.layout == Layout.CoverStack }.map { it.id }.toSet())
        assertEquals(Layout.CoverStack, p.overArtwork(Palettes.Night).layout)
        assertEquals("softbrut", AppearanceRules.sanitizeDay("softbrut"))
        assertEquals(Palettes.Night.id, AppearanceRules.sanitizeNight("softbrut"))
    }

    @Test fun theShapeIsTheSpecifiedOneAndHoldsAFraction() {
        val s = p.shape!!
        assertEquals(Triple(10f, 1.5f, 3f), Triple(s.radius, s.outline, s.shadow))
        assertEquals(p.edgeStrong, p.shadowColor)
    }

    @Test fun tokensMatchTheSpecTable() {
        fun hex(c: androidx.compose.ui.graphics.Color) = "%02X%02X%02X".format((c.red * 255).toInt(), (c.green * 255).toInt(), (c.blue * 255).toInt())
        assertEquals("FBF7EE", hex(p.ink)); assertEquals("FFFFFF", hex(p.surface)); assertEquals("F1EBDD", hex(p.raised))
        assertEquals("1C1B22", hex(p.edge)); assertEquals("5E5A6B", hex(p.textMuted)); assertEquals("C4B5FD", hex(p.accent))
        assertEquals("ECE6FF", hex(p.accentDim)); assertEquals("BFD9FF", hex(p.accent2)); assertEquals("A6E9CB", hex(p.accent3))
        assertEquals("FFD84D", hex(p.accent4)); assertEquals(1.7, p.minAccentContrast, 0.0); assertEquals(4.5, p.minTextContrast, 0.0)
    }

    @Test fun everyTextPairMeetsTheirFloor() {
        for ((name, bg) in listOf("page" to p.ink, "surface" to p.surface, "raised" to p.raised)) {
            assertTrue("text on $name", ratio(p.text, bg) >= 4.5)
            assertTrue("muted on $name", ratio(p.textMuted, bg) >= 4.5)
            assertTrue("error on $name", ratio(p.chartRedText, bg) >= 4.5)
        }
        assertTrue("label on the accent", ratio(p.onAccent, p.accent) >= 4.5)
        assertTrue("text on the sky tile", ratio(p.text, p.accent2) >= 4.5)
        assertTrue("text on the mint tag", ratio(p.text, p.accent3) >= 4.5)
        assertTrue("text on the yellow tag", ratio(p.text, p.accent4) >= 4.5)
        assertTrue("ok on its tint", ratio(p.ok, p.okDim) >= 4.5)
        assertTrue("caution on its tint", ratio(p.caution, p.cautionDim) >= 4.5)
        assertTrue("danger on its tint", ratio(p.chartRedText, p.dangerDim) >= 4.5)
        assertTrue("info on its tint", ratio(p.info, p.infoDim) >= 4.5)
        assertTrue("the accent holds against the page", ratio(p.accent, p.ink) >= p.minAccentContrast)
        // The accent is never text: the text colour is used (accentText).
        assertEquals(p.text, p.accentText)
    }

    @Test fun theNavigationCarriesFourDestinationsAndNoPlayerCell() {
        assertEquals(listOf("Home", "Discover", "Library", "Search"), CoverStackRules.cells)
        assertEquals(NavRules.destinations, CoverStackRules.cells)
        assertTrue(NavRules.discoverInBar(Layout.CoverStack))
        assertTrue(!NavRules.discoverInTopBar(Layout.CoverStack, rail = false))
        assertTrue(!NavRules.playerButtonShown(Layout.CoverStack))
        // No other layout changes.
        for (l in Layout.values().filter { it != Layout.CoverStack && it != Layout.TapeDeck && it != Layout.Flow }) {
            assertTrue(!NavRules.discoverInBar(l)); assertTrue(NavRules.playerButtonShown(l))
        }
    }

    @Test fun theBarIsFourMoreRoundThanACard() {
        assertEquals(10f, CoverStackRules.radius(p), 0f); assertEquals(14f, CoverStackRules.barRadius(p), 0f)
        assertEquals(1.5f, CoverStackRules.outline(p), 0f); assertEquals(3f, CoverStackRules.shadow(p), 0f)
    }

    @Test fun motionTakesTheStandardFamily() {
        assertEquals(MotionFamily.Standard, MotionRules.familyFor(Layout.CoverStack))
    }

    @Test fun theFontPairIsSuggestedNeverForced() {
        assertEquals("brut_modern", p.suggestedFontId)
        assertEquals("brut_modern", AppearanceRules.suggestedFont(p, FontPairs.Discair.id)?.id)
        assertNull(AppearanceRules.suggestedFont(p, "brut_modern")) // already in use: nothing to say
        assertNull(AppearanceRules.suggestedFont(Palettes.Sand, FontPairs.Discair.id)) // other themes say nothing
        assertEquals(FontPairs.Discair.id, AppearanceRules.sanitizeFont(FontPairs.Discair.id)) // choosing the theme changes no stored font
    }

    // Step P1 of docs/palettes.md: the four new day palettes (section 4.1).
    private val day = listOf(Palettes.SoftBrutMint, Palettes.SoftBrutPeach, Palettes.SoftBrutSky, Palettes.SoftBrutLemon)
    private fun hex(c: androidx.compose.ui.graphics.Color) = "%02X%02X%02X".format((c.red * 255).toInt(), (c.green * 255).toInt(), (c.blue * 255).toInt())

    @Test fun newDayPalettesAreListedAfterSoftBrutAndKeepTheThemeShape() {
        assertEquals(listOf("softbrut", "softbrut_mint", "softbrut_peach", "softbrut_sky", "softbrut_lemon"), Palettes.Light.map { it.id }.filter { it.startsWith("softbrut") })
        assertEquals(listOf("Soft Brut · Mint", "Soft Brut · Peach", "Soft Brut · Sky", "Soft Brut · Lemon"), day.map { it.label })
        for (d in day) {
            assertTrue(d.light && d in Palettes.Light && d !in Palettes.Dark)
            assertEquals(Layout.CoverStack, d.layout); assertEquals(Family.Brutal, d.family); assertEquals("brut_modern", d.suggestedFontId)
            assertEquals(Triple(10f, 1.5f, 3f), Triple(d.shape!!.radius, d.shape!!.outline, d.shape!!.shadow))
            assertEquals(d.edgeStrong, d.shadowColor); assertEquals(d.edge, d.edgeStrong); assertEquals(d.text, d.onAccent)
            assertEquals(d.id, AppearanceRules.sanitizeDay(d.id))
            assertEquals(Palettes.Night.id, AppearanceRules.sanitizeNight(d.id))
        }
    }

    @Test fun newDayPalettesMatchTheSpecTable() {
        // id -> page, raised, outline/text, muted, accent, accentDim, accent2, accent3, accent4, soft edge, chart2, floor
        val spec = mapOf(
            "softbrut_mint" to listOf("F5F8F0", "E6EDDD", "17211C", "55625A", "9BE3C0", "DDF5EA", "FFD9A8", "C9BBFF", "FFD84D", "CFD8C6", "7F8C84"),
            "softbrut_peach" to listOf("FFF6EE", "F7E6D6", "261A15", "6B564C", "FFB59A", "FFE6DB", "BFE3FF", "B9E8C2", "FFD84D", "E2CFBF", "94827A"),
            "softbrut_sky" to listOf("F3F7FB", "E1EAF3", "141C2B", "556073", "A9CCFF", "E0ECFF", "FFC9DE", "A6E9CB", "FFE066", "C9D4E0", "808B9C"),
            "softbrut_lemon" to listOf("FBF8E9", "F0EBCF", "1F1D12", "615C45", "FFDF5C", "FFF4BF", "C9BBFF", "A6E9CB", "FFB59A", "D9D3B3", "8C876E"),
        )
        val floors = mapOf("softbrut_mint" to 1.3, "softbrut_peach" to 1.5, "softbrut_sky" to 1.5, "softbrut_lemon" to 1.2)
        for (d in day) {
            val got = listOf(d.ink, d.raised, d.text, d.textMuted, d.accent, d.accentDim, d.accent2, d.accent3, d.accent4, d.chartGrid, d.chart2).map(::hex)
            assertEquals(d.id, spec[d.id], got)
            assertEquals("FFFFFF", hex(d.surface)); assertEquals(d.ink, d.rail); assertEquals(d.accent, d.chart1)
            assertEquals(d.surface, d.chart3); assertEquals(d.raised, d.chartGhost); assertEquals(floors[d.id]!!, d.minAccentContrast, 0.0)
        }
    }

    @Test fun newDayPalettesShareTheCurrentStatusColours() {
        for (d in day) {
            assertEquals(p.ok, d.ok); assertEquals(p.okDim, d.okDim); assertEquals(p.caution, d.caution); assertEquals(p.cautionDim, d.cautionDim)
            assertEquals(p.chartRed, d.chartRed); assertEquals(p.chartRedText, d.chartRedText); assertEquals(p.dangerDim, d.dangerDim)
            assertEquals(p.info, d.info); assertEquals(p.infoDim, d.infoDim)
        }
    }

    @Test fun everyNewDayPaletteMeetsTheContrastFloors() {
        for (d in day) {
            for ((name, bg) in listOf("page" to d.ink, "surface" to d.surface, "raised" to d.raised)) {
                assertTrue("${d.id} text on $name", ratio(d.text, bg) >= 4.5)
                assertTrue("${d.id} muted on $name", ratio(d.textMuted, bg) >= 4.5)
                assertTrue("${d.id} error on $name", ratio(d.chartRedText, bg) >= 4.5)
            }
            for ((name, fill) in listOf("accent" to d.accent, "accent2" to d.accent2, "accent3" to d.accent3, "accent4" to d.accent4, "accentDim" to d.accentDim))
                assertTrue("${d.id} onAccent on $name", ratio(d.onAccent, fill) >= 4.5)
            assertTrue("${d.id} ok", ratio(d.ok, d.okDim) >= 4.5); assertTrue("${d.id} caution", ratio(d.caution, d.cautionDim) >= 4.5)
            assertTrue("${d.id} danger", ratio(d.chartRedText, d.dangerDim) >= 4.5); assertTrue("${d.id} info", ratio(d.info, d.infoDim) >= 4.5)
            assertTrue("${d.id} accent holds against the page", ratio(d.accent, d.ink) >= d.minAccentContrast)
            assertEquals(d.text, d.accentText)
        }
    }
}
