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

    @Test fun softBrutIsTheOnlyCoverStackAndALightBrutalTheme() {
        assertEquals("softbrut", p.id); assertEquals("Soft Brut · Lavender", p.label)
        assertEquals(Layout.CoverStack, p.layout); assertEquals("Cover Stack", p.layout.label)
        assertEquals(Family.Brutal, p.family)
        assertTrue(p.light && p in Palettes.Light)
        assertEquals(listOf(p), Palettes.All.filter { it.layout == Layout.CoverStack })
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
        for (l in Layout.values().filter { it != Layout.CoverStack && it != Layout.TapeDeck }) {
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
}
