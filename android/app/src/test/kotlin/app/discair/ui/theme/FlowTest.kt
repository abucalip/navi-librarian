package app.discair.ui.theme

import app.discair.ui.NavRules
import app.discair.ui.common.FlowRules
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Step F1 of docs/ANDROID_ART_THEMES_PROPOSAL.md: the Flow palette, its layout, its font pair, its shell rules and its contrast. */
class FlowTest {
    private val p = Palettes.Flow
    private fun ratio(a: androidx.compose.ui.graphics.Color, b: androidx.compose.ui.graphics.Color) = Contrast.ratio(a, b)
    private fun hex(c: androidx.compose.ui.graphics.Color) = "%02X%02X%02X".format((c.red * 255).toInt(), (c.green * 255).toInt(), (c.blue * 255).toInt())

    @Test fun flowIsTheOnlyFlowLayoutAndALightClassicTheme() {
        assertEquals("flow", p.id); assertEquals("Flow \u00b7 Warm white", p.label)
        assertEquals(Layout.Flow, p.layout); assertEquals("Flow", p.layout.label)
        assertEquals(Family.Classic, p.family); assertNull(p.shape); assertFalse(p.brutal)
        assertTrue(p.light && p in Palettes.Light)
        assertEquals(listOf(p), Palettes.All.filter { it.layout == Layout.Flow })
        assertEquals(Layout.Flow, p.overArtwork(Palettes.Night).layout)
        assertEquals("flow", AppearanceRules.sanitizeDay("flow"))
        assertEquals(Palettes.Night.id, AppearanceRules.sanitizeNight("flow"))
    }

    @Test fun tokensMatchTheSpecTable() {
        assertEquals("FBFAF7", hex(p.ink)); assertEquals("FBFAF7", hex(p.rail)); assertEquals("FFFFFF", hex(p.surface))
        assertEquals("EFECE5", hex(p.raised)); assertEquals("E2DFD6", hex(p.edge)); assertEquals("8E887B", hex(p.edgeStrong))
        assertEquals("15130F", hex(p.text)); assertEquals("645F55", hex(p.textMuted))
        assertEquals("C2410C", hex(p.accent)); assertEquals("FBE4D5", hex(p.accentDim)); assertEquals("FFFFFF", hex(p.onAccent))
        assertEquals("1B7339", hex(p.ok)); assertEquals("DCEEDF", hex(p.okDim)); assertEquals("8A5300", hex(p.caution)); assertEquals("F8E8CC", hex(p.cautionDim))
        assertEquals("C0271A", hex(p.chartRedText)); assertEquals("F9DCD8", hex(p.dangerDim)); assertEquals("1F5FBF", hex(p.info)); assertEquals("DCE7F8", hex(p.infoDim))
        assertEquals("C2410C", hex(p.chart1)); assertEquals("8F897D", hex(p.chart2)); assertEquals("D9D4C8", hex(p.chart3))
        assertEquals(p.raised, p.chartGhost); assertEquals(p.edge, p.chartGrid); assertEquals(p.edgeStrong, p.chartBase)
        assertEquals(4.5, p.minTextContrast, 0.0)
    }

    @Test fun everyTextPairMeetsItsFloor() {
        for ((name, bg) in listOf("page" to p.ink, "surface" to p.surface, "raised" to p.raised)) {
            assertTrue("text on $name", ratio(p.text, bg) >= 4.5)
            assertTrue("muted on $name", ratio(p.textMuted, bg) >= 4.5)
            assertTrue("error on $name", ratio(p.chartRedText, bg) >= 4.5)
        }
        // The accent is text on the page and the surface, not on `raised` (proposal section 4): the fill-only rule there is the text colour.
        assertTrue("accent on the page", ratio(p.accent, p.ink) >= 4.5)
        assertTrue("accent on the surface", ratio(p.accent, p.surface) >= 4.5)
        assertTrue("label on the accent", ratio(p.onAccent, p.accent) >= 4.5)
        assertTrue("ok on its tint", ratio(p.ok, p.okDim) >= 4.5)
        assertTrue("caution on its tint", ratio(p.caution, p.cautionDim) >= 4.5)
        assertTrue("danger on its tint", ratio(p.chartRedText, p.dangerDim) >= 4.5)
        assertTrue("info on its tint", ratio(p.info, p.infoDim) >= 4.5)
        // The accent on its own tint is 4.23:1, under the floor for 11sp tag text: an accent tag takes the text colour for its label (the tint carries the accent).
        assertTrue("text on the accent tint", ratio(p.text, p.accentDim) >= 4.5)
        assertTrue("the strong edge holds against the page", ratio(p.edgeStrong, p.ink) >= 3.0)
        assertEquals(p.accent, p.accentText)
    }

    @Test fun theNavigationCarriesFourDestinationsAndNoPlayerCell() {
        assertEquals(NavRules.destinations, FlowRules.cells)
        assertTrue(NavRules.discoverInBar(Layout.Flow))
        assertTrue(!NavRules.discoverInTopBar(Layout.Flow, rail = false))
        assertTrue(!NavRules.playerButtonShown(Layout.Flow))
        for (l in Layout.values().filter { it != Layout.CoverStack && it != Layout.TapeDeck && it != Layout.Flow }) {
            assertTrue(!NavRules.discoverInBar(l)); assertTrue(NavRules.playerButtonShown(l))
        }
    }

    @Test fun depthLevelsGrowAndTheBarIsTranslucent() {
        assertTrue(FlowRules.elevation(1) < FlowRules.elevation(2) && FlowRules.elevation(2) < FlowRules.elevation(3))
        assertEquals(0.86f, FlowRules.BAR_ALPHA, 0f)
        assertEquals(0.86f, FlowRules.barFill(p).alpha, 0.01f)
        assertEquals(30f, FlowRules.RADIUS_NAV, 0f); assertEquals(18f, FlowRules.RADIUS_MINI, 0f)
    }

    @Test fun motionTakesTheStandardFamily() {
        assertEquals(MotionFamily.Standard, MotionRules.familyFor(Layout.Flow))
    }

    @Test fun theFontPairIsInterAndSuggestedNeverForced() {
        val f = FontPairs.Flow
        assertEquals("flow", f.id); assertEquals("Inter", f.titleName); assertEquals("Inter", f.bodyName); assertEquals("Inter", f.monoName)
        assertEquals(-0.03, f.titleTracking.value.toDouble(), 0.0001)
        assertEquals("flow", p.suggestedFontId)
        assertEquals("flow", AppearanceRules.suggestedFont(p, FontPairs.Discair.id)?.id)
        assertNull(AppearanceRules.suggestedFont(p, "flow"))
        assertEquals(FontPairs.Discair.id, AppearanceRules.sanitizeFont(FontPairs.Discair.id))
        assertEquals("flow", AppearanceRules.sanitizeFont("flow"))
    }
}
