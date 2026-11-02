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

    @Test fun twelveThemesWithUniqueIds() {
        assertEquals(12, Palettes.All.size)
        assertEquals(5, Palettes.Light.size)
        assertEquals(7, Palettes.Dark.size)
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
            check(p, "accent", p.accent, p.ink, 3.0, "page")
            check(p, "accent", p.accent, p.surface, 3.0, "surface")
            check(p, "strong edge", p.edgeStrong, p.surface, 3.0, "surface")
        }
    }

    @Test fun overArtworkKeepsLightTextOnLightThemes() {
        val over = Palettes.Sand.overArtwork(Palettes.Night)
        assertEquals(Palettes.Night.text, over.text)
        assertEquals(Palettes.Night.accent, over.accent)
        assertTrue(!over.light)
        // A dark theme is left alone.
        assertEquals(Palettes.Ember.accent, Palettes.Ember.overArtwork(Palettes.Night).accent)
    }

    @Test fun fivePairsWithUniqueIdsAndDiscairFirst() {
        assertEquals(5, FontPairs.All.size)
        assertEquals(FontPairs.All.size, FontPairs.All.map { it.id }.toSet().size)
        assertEquals("discair", FontPairs.All.first().id)
    }
}
