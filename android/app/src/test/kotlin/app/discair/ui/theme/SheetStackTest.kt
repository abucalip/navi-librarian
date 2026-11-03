package app.discair.ui.theme

import androidx.compose.ui.graphics.Color
import app.discair.lyrics.LyricLine
import app.discair.lyrics.Lyrics
import app.discair.lyrics.LyricsProblem
import app.discair.lyrics.LyricsUiState
import app.discair.ui.common.SheetStackRules
import kotlin.math.pow
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Round 2, Sheet Stack (docs/BRUT_LAYOUTS_PLAN.md, D-023): the three palettes and the pure composition rules. */
class SheetStackTest {
    private fun lin(v: Float): Double = v.toDouble().let { if (it <= 0.03928) it / 12.92 else ((it + 0.055) / 1.055).pow(2.4) }
    private fun lum(c: Color) = 0.2126 * lin(c.red) + 0.7152 * lin(c.green) + 0.0722 * lin(c.blue)
    private fun contrast(a: Color, b: Color): Double = (maxOf(lum(a), lum(b)) + 0.05) / (minOf(lum(a), lum(b)) + 0.05)

    private val sheet = listOf(Palettes.SheetViolet, Palettes.SheetAcid, Palettes.SheetDaylight)

    @Test fun onlyTheThreeSheetThemesAskForTheSheetStack() {
        assertEquals(listOf("sheetviolet", "sheetacid", "sheetdaylight"), sheet.map { it.id })
        assertTrue(sheet.all { it.layout == Layout.SheetStack && it.brutal })
        assertEquals(setOf("Sheet · Violet-orange", "Sheet · Acid Night", "Sheet · Daylight"), sheet.map { it.label }.toSet())
        assertTrue(Palettes.All.filter { it !in sheet }.none { it.layout == Layout.SheetStack })
    }

    @Test fun twoAreNightThemesAndOneIsADayTheme() {
        assertEquals(listOf(false, false, true), sheet.map { it.light })
        assertTrue(Palettes.SheetDaylight in Palettes.Light)
        assertTrue(Palettes.SheetViolet in Palettes.Dark && Palettes.SheetAcid in Palettes.Dark)
        assertEquals("sheetviolet", AppearanceRules.sanitizeNight("sheetviolet"))
        assertEquals("sheetdaylight", AppearanceRules.sanitizeDay("sheetdaylight"))
        assertEquals(Palettes.Night.id, AppearanceRules.sanitizeNight("sheetdaylight"))
    }

    @Test fun layoutSurvivesTheOverlay() {
        for (p in sheet) assertEquals(Layout.SheetStack, p.overArtwork(Palettes.Night).layout)
    }

    @Test fun everyTextPairMeetsAAAndTheEdgeAndAccentAreVisible() {
        for (p in sheet) {
            for ((name, bg) in listOf("page" to p.ink, "surface" to p.surface, "raised" to p.raised)) {
                assertTrue("${p.label} text on $name", contrast(p.text, bg) >= 4.5)
                assertTrue("${p.label} muted text on $name", contrast(p.textMuted, bg) >= 4.5)
                assertTrue("${p.label} error text on $name", contrast(p.chartRedText, bg) >= 4.5)
            }
            assertTrue("${p.label} label on the accent", contrast(p.onAccent, p.accent) >= 4.5)
            assertTrue("${p.label} text on the soft accent", contrast(p.text, p.accentDim) >= 4.5)
            assertTrue("${p.label} label on the second tone", contrast(p.onAccent, p.accent2) >= 4.5)
            assertTrue("${p.label} edge", contrast(p.edgeStrong, p.surface) >= 3.0)
            assertTrue("${p.label} accent", contrast(p.accent, p.surface) >= p.minAccentContrast)
        }
    }

    @Test fun requestsAreAlwaysAWordFetchingQueuedOrDone() {
        assertEquals("Queued", SheetStackRules.requestWord("queued", "Queued"))
        assertEquals("Queued", SheetStackRules.requestWord("requested", "Requested"))
        assertEquals("Done", SheetStackRules.requestWord("imported", "Imported"))
        for (s in listOf("searching", "downloading", "importing", "monitoring", "source_switching")) assertEquals("Fetching", SheetStackRules.requestWord(s, "x"))
        assertEquals("Download failed", SheetStackRules.requestWord("download_failed", "Download failed")) // anything else keeps its own words
        assertEquals("Unknown status", SheetStackRules.requestWord("whatever", "Unknown status"))
    }

    @Test fun libraryMovesIntoTheNavigationGroupOnlyOnTheSheetStack() {
        assertFalse(SheetStackRules.homeShowsLibraryButton(Layout.SheetStack))
        for (l in Layout.values().filter { it != Layout.SheetStack && it != Layout.TapeDeck }) assertTrue(SheetStackRules.homeShowsLibraryButton(l)) // the Cassette Deck bar has a Library cell too
    }

    @Test fun theVolumeSliderMapsATouchToZeroToOneFromTheBottom() {
        assertEquals(1f, SheetStackRules.volumeFromTouch(0f, 400f, 14f), 0.001f) // above the track: full
        assertEquals(1f, SheetStackRules.volumeFromTouch(14f, 400f, 14f), 0.001f)
        assertEquals(0.5f, SheetStackRules.volumeFromTouch(200f, 400f, 14f), 0.001f)
        assertEquals(0f, SheetStackRules.volumeFromTouch(386f, 400f, 14f), 0.001f)
        assertEquals(0f, SheetStackRules.volumeFromTouch(999f, 400f, 14f), 0.001f)
        assertEquals("70 percent", SheetStackRules.volumeDescription(0.7f))
        assertEquals("0 percent", SheetStackRules.volumeDescription(-1f))
        assertEquals("100 percent", SheetStackRules.volumeDescription(2f))
    }

    @Test fun pressingTheOpenPanelClosesIt() {
        assertEquals(2, SheetStackRules.toggleView(0, 2))
        assertEquals(0, SheetStackRules.toggleView(2, 2))
        assertEquals(1, SheetStackRules.toggleView(2, 1)) // the strip while the queue is open switches to the lyrics
        assertEquals(0, SheetStackRules.toggleView(1, 1))
    }

    @Test fun theLyricsStripShowsTheLineOrTheSameNoLyricsWordsAsTheLyricsView() {
        val timed = Lyrics(true, listOf(LyricLine(0, "First"), LyricLine(1000, "Second"), LyricLine(2000, "  ")))
        val ready = LyricsUiState.Ready("s", timed)
        assertEquals("Second", SheetStackRules.lyricsStripText(ready, 1))
        assertEquals("Lyrics · tap to read", SheetStackRules.lyricsStripText(ready, -1)) // before the first line
        assertEquals("Lyrics · tap to read", SheetStackRules.lyricsStripText(ready, 2)) // a blank line
        assertEquals("Lyrics · tap to read", SheetStackRules.lyricsStripText(LyricsUiState.Ready("s", Lyrics(false, listOf(LyricLine(null, "Plain")))), 0))
        assertEquals("Loading lyrics…", SheetStackRules.lyricsStripText(LyricsUiState.Idle, -1))
        assertEquals("Loading lyrics…", SheetStackRules.lyricsStripText(LyricsUiState.Loading("s"), -1))
        assertEquals("No lyrics for this song.", SheetStackRules.lyricsStripText(LyricsUiState.None("s"), -1))
        assertEquals("Your Navidrome doesn't provide lyrics.", SheetStackRules.lyricsStripText(LyricsUiState.Unsupported("s"), -1))
        assertTrue(SheetStackRules.lyricsStripText(LyricsUiState.Failed("s", LyricsProblem.Unreachable), -1).startsWith("Can't reach Navidrome"))
    }
}
