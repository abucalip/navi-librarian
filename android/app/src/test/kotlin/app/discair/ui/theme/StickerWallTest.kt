package app.discair.ui.theme

import androidx.compose.ui.graphics.Color
import app.discair.ui.common.Sticker
import app.discair.ui.common.StickerWallRules
import app.discair.ui.common.StickerWallRules.EqBar
import kotlin.math.pow
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Round 2, Sticker Wall (docs/BRUT_LAYOUTS_PLAN.md, D-023): the one palette and the pure composition rules. */
class StickerWallTest {
    private fun lin(v: Float): Double = v.toDouble().let { if (it <= 0.03928) it / 12.92 else ((it + 0.055) / 1.055).pow(2.4) }
    private fun lum(c: Color) = 0.2126 * lin(c.red) + 0.7152 * lin(c.green) + 0.0722 * lin(c.blue)
    private fun contrast(a: Color, b: Color): Double = (maxOf(lum(a), lum(b)) + 0.05) / (minOf(lum(a), lum(b)) + 0.05)

    @Test fun onlyPeachTealAsksForTheStickerWallAndItIsALightBrutalTheme() {
        val p = Palettes.StickerPeach
        assertEquals("stickerpeach", p.id); assertEquals("Sticker · Peach-teal", p.label)
        assertEquals(Layout.StickerWall, p.layout)
        assertTrue(p.light && p.brutal && p in Palettes.Light)
        assertEquals(listOf(p), Palettes.All.filter { it.layout == Layout.StickerWall })
        assertEquals(Layout.StickerWall, p.overArtwork(Palettes.Night).layout)
        assertEquals("stickerpeach", AppearanceRules.sanitizeDay("stickerpeach"))
        assertEquals(Palettes.Night.id, AppearanceRules.sanitizeNight("stickerpeach"))
    }

    @Test fun everyTextPairMeetsAAAndTheStickerAndAccentColoursCarryTheirLabels() {
        val p = Palettes.StickerPeach
        for ((name, bg) in listOf("page" to p.ink, "surface" to p.surface, "raised" to p.raised)) {
            assertTrue("text on $name", contrast(p.text, bg) >= 4.5)
            assertTrue("muted text on $name", contrast(p.textMuted, bg) >= 4.5)
            assertTrue("error text on $name", contrast(p.chartRedText, bg) >= 4.5)
        }
        assertTrue("label on the accent", contrast(p.onAccent, p.accent) >= 4.5)
        assertTrue("text on the soft accent", contrast(p.text, p.accentDim) >= 4.5)
        // The New and Missing stickers use the yellow and the pink tone under dark text.
        assertTrue("New sticker", contrast(p.text, p.accent4) >= 4.5)
        assertTrue("Missing sticker", contrast(p.text, p.accent3) >= 4.5)
        assertTrue("edge", contrast(p.edgeStrong, p.surface) >= 3.0)
    }

    @Test fun tiltsAreSmallStaticAndAlternate() {
        val tilts = (0..7).map { StickerWallRules.tiltFor(it) }
        assertTrue(tilts.all { kotlin.math.abs(it) <= 2f })
        assertTrue(tilts.toSet().size > 1)
        assertEquals(StickerWallRules.tiltFor(0), StickerWallRules.tiltFor(4))
        assertEquals(StickerWallRules.tiltFor(3), StickerWallRules.tiltFor(-1)) // negative indexes wrap, never throw
    }

    @Test fun aTileIsSpokenWithItsStickerWord() {
        assertEquals("Blue Train, by John Coltrane, Missing", StickerWallRules.tileDescription("Blue Train", "John Coltrane", Sticker.Missing))
        assertEquals("Kind of Blue, by Miles Davis, New", StickerWallRules.tileDescription("Kind of Blue", "Miles Davis", Sticker.New))
        assertEquals("Unknown album, by unknown artist, New", StickerWallRules.tileDescription("", " ", Sticker.New))
        assertEquals(listOf("New", "Missing"), Sticker.values().map { it.word })
    }

    @Test fun aTitleStacksIntoWholeWordsInAtMostThreeLines() {
        assertEquals(listOf("Freddie", "Freeloader"), StickerWallRules.stackTitle("Freddie Freeloader"))
        for (title in listOf("So What", "A Love Supreme Part One Acknowledgement", "Everything In Its Right Place", "One", "")) {
            val lines = StickerWallRules.stackTitle(title)
            assertTrue(lines.size <= 3)
            assertEquals(title.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }, lines.flatMap { it.split(" ") }) // no word cut, none reordered, none lost
        }
        assertEquals(emptyList<String>(), StickerWallRules.stackTitle("   "))
        assertEquals(listOf("One"), StickerWallRules.stackTitle("One"))
        assertEquals(3, StickerWallRules.stackTitle("A Love Supreme Part One Acknowledgement").size)
    }

    @Test fun theThreeBarsAverageTheirBandsAndFillFromHalfWhenFlat() {
        val flat = List(10) { 0.0 }
        for (bar in EqBar.values()) {
            assertEquals(0.0, StickerWallRules.barGainDb(flat, bar), 0.0001)
            assertEquals(0.5f, StickerWallRules.barFraction(0.0, 12.0), 0.0001f)
        }
        val bands = listOf(6.0, 6.0, 6.0, 0.0, 0.0, 0.0, 0.0, -12.0, -12.0, -12.0)
        assertEquals(6.0, StickerWallRules.barGainDb(bands, EqBar.Bass), 0.0001)
        assertEquals(0.0, StickerWallRules.barGainDb(bands, EqBar.Mid), 0.0001)
        assertEquals(-12.0, StickerWallRules.barGainDb(bands, EqBar.Treble), 0.0001)
        assertEquals(0.75f, StickerWallRules.barFraction(6.0, 12.0), 0.0001f)
        assertEquals(0f, StickerWallRules.barFraction(-12.0, 12.0), 0.0001f)
        assertEquals(1f, StickerWallRules.barFraction(99.0, 12.0), 0.0001f)
        assertEquals(0.0, StickerWallRules.barGainDb(listOf(1.0), EqBar.Treble), 0.0001) // a short list counts missing bands as flat
    }

    @Test fun theBarsAreSpokenInWords() {
        assertEquals("Bass plus 2.5 decibels", StickerWallRules.barSpoken(EqBar.Bass, 2.5))
        assertEquals("Mid flat", StickerWallRules.barSpoken(EqBar.Mid, 0.02))
        assertEquals("Treble minus 3 decibels", StickerWallRules.barSpoken(EqBar.Treble, -3.0))
    }
}
