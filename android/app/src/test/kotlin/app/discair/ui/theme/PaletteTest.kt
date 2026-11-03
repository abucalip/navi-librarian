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

    @Test fun twentySixThemesWithUniqueIds() {
        assertEquals(26, Palettes.All.size)
        assertEquals(15, Palettes.Light.size)
        assertEquals(11, Palettes.Dark.size)
        assertEquals(12, Palettes.All.count { it.family == Family.Classic })
        assertEquals(14, Palettes.All.count { it.family == Family.Brutal })
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

    // Sand is the default day theme. (Day · Mist's blue is 2.98 here, just under 3.0; not changed.)
    @Test fun sandAccentStaysVisibleOverArtwork() {
        val over = Palettes.Sand.overArtwork(Palettes.Night)
        check(over, "accent over artwork", over.accent, over.surface, 3.0, "dark surface")
    }

    @Test fun elevenPairsWithUniqueIdsAndDiscairFirst() {
        assertEquals(11, FontPairs.All.size)
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
        assertEquals(setOf("JetBrains Mono"), FontPairs.All.filter { !it.id.startsWith("brut_") }.map { it.monoName }.toSet())
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
        assertEquals(0, Palettes.BrutPoster.shape!!.radius) // square
        assertTrue(Palettes.All.filter { it.brutal }.all { it.shape!!.outline >= 2 && it.shapeShadowIsVisible() })
        assertTrue(Palettes.All.filter { !it.brutal }.all { it.shape == null })
    }

    @Test fun brutalLabelsOnTheThreeExtraColoursAreReadable() {
        // Rank chips and badges put black text on accent2..4 (the number chips in the Appearance tiles and lists).
        for (p in Palettes.All.filter { it.brutal }) {
            for ((i, c) in listOf(p.accent2, p.accent3, p.accent4).withIndex()) check(p, "black on accent${i + 2}", Color.Black, c, 4.5, "chip")
        }
    }

    private fun Palette.shapeShadowIsVisible() = shadowColor != Color.Transparent && contrast(shadowColor, ink) >= 3.0
}
