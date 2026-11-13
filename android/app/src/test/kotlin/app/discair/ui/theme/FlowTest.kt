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

    @Test fun flowIsALightClassicFlowLayoutTheme() {
        assertEquals("flow", p.id); assertEquals("Flow \u00b7 Warm white", p.label)
        assertEquals(Layout.Flow, p.layout); assertEquals("Flow", p.layout.label)
        assertEquals(Family.Classic, p.family); assertNull(p.shape); assertFalse(p.brutal)
        assertTrue(p.light && p in Palettes.Light)
        assertEquals(setOf("flow", "flow_forest", "flow_raspberry", "flow_violet"), Palettes.All.filter { it.layout == Layout.Flow }.map { it.id }.toSet())
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

    @Test fun depthLevelsAndGroupedRowsKeepTheMockupNumbers() {
        assertEquals(4f, FlowRules.elevation(1), 0f); assertEquals(8f, FlowRules.elevation(2), 0f); assertEquals(16f, FlowRules.elevation(3), 0f)
        assertEquals(16f, FlowRules.RADIUS_CARD, 0f)
        assertEquals(64f, FlowRules.ROW_MIN, 0f)
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

    // Step P3 of docs/palettes.md: the three new day palettes (sections 4.2 and 4.4).
    private val day = listOf(Palettes.FlowForest, Palettes.FlowRaspberry, Palettes.FlowViolet)

    @Test fun newDayPalettesAreListedAfterFlowAndKeepTheThemeShape() {
        assertEquals(listOf("flow", "flow_forest", "flow_raspberry", "flow_violet"), Palettes.Light.map { it.id }.filter { it.startsWith("flow") })
        assertEquals(listOf("Flow · Forest", "Flow · Raspberry", "Flow · Violet"), day.map { it.label })
        for (d in day) {
            assertTrue(d.light && d in Palettes.Light && d !in Palettes.Dark)
            assertEquals(Layout.Flow, d.layout); assertEquals(Family.Classic, d.family); assertNull(d.shape); assertEquals("flow", d.suggestedFontId)
            assertEquals(d.id, AppearanceRules.sanitizeDay(d.id))
            assertEquals(Palettes.Night.id, AppearanceRules.sanitizeNight(d.id))
            assertEquals(p.ok, d.ok); assertEquals(p.okDim, d.okDim); assertEquals(p.caution, d.caution); assertEquals(p.cautionDim, d.cautionDim)
            assertEquals(p.chartRedText, d.chartRedText); assertEquals(p.dangerDim, d.dangerDim); assertEquals(p.info, d.info); assertEquals(p.infoDim, d.infoDim)
        }
    }

    @Test fun newDayPalettesMatchTheSpecTable() {
        // id -> page, surface, raised, edge, strong edge, text, muted, accent, accentDim, onAccent, chart2, chart3
        val spec = mapOf(
            "flow_forest" to listOf("F8F9F4", "FFFFFF", "E9EDE2", "DBE0D2", "7D8672", "12150F", "596051", "1B7340", "D9EEDF", "FFFFFF", "87907C", "D0D6C6"),
            "flow_raspberry" to listOf("FCF8F8", "FFFFFF", "F1E8E9", "E5DADB", "8E7F82", "171113", "6A5C5F", "BE2260", "FADCE6", "FFFFFF", "96878A", "DCCFD1"),
            "flow_violet" to listOf("F9F8FC", "FFFFFF", "ECEAF3", "DEDBE8", "827D93", "13111A", "5F5A6E", "6A3BD2", "E7DEFA", "FFFFFF", "8A859B", "D3CFE0"),
        )
        for (d in day) {
            val got = listOf(d.ink, d.surface, d.raised, d.edge, d.edgeStrong, d.text, d.textMuted, d.accent, d.accentDim, d.onAccent, d.chart2, d.chart3).map(::hex)
            assertEquals(d.id, spec[d.id], got)
            assertEquals(d.ink, d.rail); assertEquals(d.accent, d.chart1); assertEquals(d.raised, d.chartGhost); assertEquals(d.edge, d.chartGrid); assertEquals(d.edgeStrong, d.chartBase)
            assertEquals(4.5, d.minTextContrast, 0.0)
        }
    }

    @Test fun everyNewDayPaletteMeetsTheContrastFloors() {
        for (d in day) {
            for ((name, bg) in listOf("page" to d.ink, "surface" to d.surface, "raised" to d.raised)) {
                assertTrue("${d.id} text on $name", ratio(d.text, bg) >= 4.5)
                assertTrue("${d.id} muted on $name", ratio(d.textMuted, bg) >= 4.5)
                assertTrue("${d.id} error on $name", ratio(d.chartRedText, bg) >= 4.5)
            }
            assertTrue("${d.id} accent on the page", ratio(d.accent, d.ink) >= 4.5)
            assertTrue("${d.id} accent on the surface", ratio(d.accent, d.surface) >= 4.5)
            assertTrue("${d.id} label on the accent", ratio(d.onAccent, d.accent) >= 4.5)
            assertTrue("${d.id} text on the accent tint", ratio(d.text, d.accentDim) >= 4.5)
            assertTrue("${d.id} ok", ratio(d.ok, d.okDim) >= 4.5); assertTrue("${d.id} caution", ratio(d.caution, d.cautionDim) >= 4.5)
            assertTrue("${d.id} danger", ratio(d.chartRedText, d.dangerDim) >= 4.5); assertTrue("${d.id} info", ratio(d.info, d.infoDim) >= 4.5)
            assertTrue("${d.id} the strong edge holds against the page", ratio(d.edgeStrong, d.ink) >= 3.0)
            assertEquals(d.accent, d.accentText)
        }
    }

    @Test fun switchAndChevronFollowThePaletteAndTheCurrentFlowIsUnchanged() {
        assertEquals("D9D5CB", hex(FlowRules.switchOff(p))); assertEquals("B5B0A5", hex(FlowRules.chevron(p)))
        assertEquals(listOf("D0D6C6", "DCCFD1", "D3CFE0"), day.map { hex(FlowRules.switchOff(it)) })
        assertEquals(listOf("AEB5A3", "BBADB0", "B2AEC2"), day.map { hex(FlowRules.chevron(it)) })
    }
}
