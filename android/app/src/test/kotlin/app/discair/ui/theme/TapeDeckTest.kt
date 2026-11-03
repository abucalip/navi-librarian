package app.discair.ui.theme

import androidx.compose.ui.graphics.Color
import app.discair.ui.common.TapeDeckRules
import kotlin.math.pow
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Round 2, Cassette Deck (docs/BRUT_LAYOUTS_PLAN.md, D-023): the layout field, the three palettes and the pure composition rules. */
class TapeDeckTest {
    private fun lin(v: Float): Double = v.toDouble().let { if (it <= 0.03928) it / 12.92 else ((it + 0.055) / 1.055).pow(2.4) }
    private fun lum(c: Color) = 0.2126 * lin(c.red) + 0.7152 * lin(c.green) + 0.0722 * lin(c.blue)
    private fun contrast(a: Color, b: Color): Double = (maxOf(lum(a), lum(b)) + 0.05) / (minOf(lum(a), lum(b)) + 0.05)

    private val tape = listOf(Palettes.TapeLime, Palettes.TapeCobalt, Palettes.TapeTangerine)

    @Test fun onlyTheThreeTapeThemesAskForTheCassetteDeckAndEveryOtherThemeKeepsStandard() {
        assertEquals(listOf("tapelime", "tapecobalt", "tapetangerine"), tape.map { it.id })
        assertTrue(tape.all { it.layout == Layout.TapeDeck && it.light && it.brutal })
        assertTrue(Palettes.All.filter { it !in tape }.none { it.layout == Layout.TapeDeck })
        assertTrue(Palettes.All.filter { it.layout == Layout.Standard }.size >= 20) // the twenty earlier themes keep Standard
        assertEquals(setOf("Tape · Lime", "Tape · Cobalt", "Tape · Tangerine"), tape.map { it.label }.toSet())
    }

    @Test fun theTapeThemesAreInTheDayList() {
        assertTrue(tape.all { it in Palettes.Light })
        assertEquals("sand", AppearanceRules.sanitizeDay("sand"))
        for (p in tape) {
            assertEquals(p.id, AppearanceRules.sanitizeDay(p.id))
            assertEquals(p.id, AppearanceRules.sanitizeChoice(p.id))
            assertEquals(Palettes.Night.id, AppearanceRules.sanitizeNight(p.id)) // a light theme is never a night theme
        }
    }

    @Test fun layoutSurvivesTheDarkOverlayThePlayerSheetUses() {
        for (p in tape) assertEquals(Layout.TapeDeck, p.overArtwork(Palettes.Night).layout)
        assertEquals(Layout.Standard, Palettes.Sand.overArtwork(Palettes.Night).layout)
    }

    @Test fun everyTextPairInTheTapePalettesMeetsAA() {
        for (p in tape) {
            for ((name, bg) in listOf("page" to p.ink, "surface" to p.surface, "raised" to p.raised)) {
                assertTrue("${p.label} text on $name", contrast(p.text, bg) >= 4.5)
                assertTrue("${p.label} muted text on $name", contrast(p.textMuted, bg) >= 4.5)
                assertTrue("${p.label} error text on $name", contrast(p.chartRedText, bg) >= 4.5)
            }
            assertTrue("${p.label} label on the accent", contrast(p.onAccent, p.accent) >= 4.5)
            assertTrue("${p.label} text on the playing row", contrast(p.text, p.accentDim) >= 4.5)
            assertTrue("${p.label} strong edge", contrast(p.edgeStrong, p.surface) >= 3.0)
            assertTrue("${p.label} accent against its minimum", contrast(p.accent, p.surface) >= p.minAccentContrast)
        }
    }

    @Test fun theCobaltAccentIsTheDarkenedWebValueSoWhiteTextPasses() {
        assertEquals(Color(0xFF3D68F0), Palettes.TapeCobalt.accent)
        assertTrue(contrast(Color.White, Palettes.TapeCobalt.accent) >= 4.5)
    }

    @Test fun theMeterMovesOnlyWhilePlayingAndNeitherBufferingNorReducedMotion() {
        assertTrue(TapeDeckRules.meterMoves(playing = true, buffering = false, reducedMotion = false))
        assertFalse(TapeDeckRules.meterMoves(playing = false, buffering = false, reducedMotion = false)) // paused
        assertFalse(TapeDeckRules.meterMoves(playing = true, buffering = true, reducedMotion = false)) // buffering
        assertFalse(TapeDeckRules.meterMoves(playing = true, buffering = false, reducedMotion = true)) // the phone reduces motion
    }

    @Test fun restingBarsAreOneHeightPerBarAndNeverFlat() {
        for (n in listOf(3, 4, 5)) {
            val bars = TapeDeckRules.restingBars(n)
            assertEquals(n, bars.size)
            assertTrue(bars.all { it in 0.3f..1f })
            assertTrue(bars.toSet().size > 1)
        }
    }

    @Test fun theTrackLabelNamesThePlaceInTheQueueOrIsBlank() {
        assertEquals("Track 2 of 8", TapeDeckRules.trackLabel(1, 8))
        assertEquals("Track 1 of 1", TapeDeckRules.trackLabel(0, 1))
        assertEquals("", TapeDeckRules.trackLabel(0, 0))
        assertEquals("", TapeDeckRules.trackLabel(8, 8))
        assertEquals("", TapeDeckRules.trackLabel(-1, 3))
    }

    @Test fun theMiniPlayerExistsOnlyOnTheCassetteDeckAndOnlyWhileASongIsQueued() {
        assertTrue(TapeDeckRules.miniPlayerShown(Layout.TapeDeck, hasSong = true))
        assertFalse(TapeDeckRules.miniPlayerShown(Layout.TapeDeck, hasSong = false))
        for (layout in Layout.values().filter { it != Layout.TapeDeck }) assertFalse(TapeDeckRules.miniPlayerShown(layout, hasSong = true))
    }

    @Test fun settingsMovesToTheCassetteDeckBarAndLeavesHomeWithTwoPageButtons() {
        assertFalse(TapeDeckRules.homeShowsSettingsButton(Layout.TapeDeck))
        for (layout in Layout.values().filter { it != Layout.TapeDeck }) assertTrue(TapeDeckRules.homeShowsSettingsButton(layout))
    }

    @Test fun theLyricsButtonSwapsTheQueueAndTheLyrics() {
        assertEquals(1, TapeDeckRules.toggleLyrics(0)) // queue -> lyrics
        assertEquals(0, TapeDeckRules.toggleLyrics(1)) // lyrics -> queue
        assertEquals(1, TapeDeckRules.toggleLyrics(2)) // a queue face left over from another theme counts as the queue
        assertEquals(0, TapeDeckRules.toggleLyrics(TapeDeckRules.toggleLyrics(0)))
    }

    @Test fun everyLayoutHasAUniqueLabel() {
        assertEquals(Layout.values().size, Layout.values().map { it.label }.toSet().size)
    }
}
