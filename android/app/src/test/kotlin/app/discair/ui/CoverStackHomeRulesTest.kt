package app.discair.ui

import app.discair.model.RadioPlay
import app.discair.ui.home.CoverStackHomeRules
import app.discair.ui.home.HeroFigures
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.ZoneId

class CoverStackHomeRulesTest {
    private fun play(station: String, at: Double?) = RadioPlay(1, station, "A", "T", null, false, false, at)

    @Test fun behindIsTheNextTwoPicksWrapping() {
        assertEquals(listOf(1, 2), CoverStackHomeRules.behind(0, 7))
        assertEquals(listOf(0, 1), CoverStackHomeRules.behind(6, 7))
    }

    @Test fun smallListsDrawFewerSleevesAndNeverTheFrontOne() {
        assertTrue(CoverStackHomeRules.behind(0, 1).isEmpty())
        assertEquals(listOf(1), CoverStackHomeRules.behind(0, 2))
        assertEquals(listOf(0), CoverStackHomeRules.behind(1, 2))
        assertTrue(CoverStackHomeRules.behind(0, 0).isEmpty())
    }

    @Test fun stepWraps() {
        assertEquals(1, CoverStackHomeRules.step(0, 7, 1))
        assertEquals(6, CoverStackHomeRules.step(0, 7, -1))
        assertEquals(0, CoverStackHomeRules.step(6, 7, 1))
        assertEquals(0, CoverStackHomeRules.step(3, 0, 1))
    }

    @Test fun clampKeepsTheIndexInsideAShrunkenList() {
        assertEquals(2, CoverStackHomeRules.clamp(5, 3))
        assertEquals(0, CoverStackHomeRules.clamp(2, 0))
    }

    @Test fun counterIsOneBased() = assertEquals("1 / 7", CoverStackHomeRules.counter(0, 7))

    @Test fun swipeNeedsADeliberateDrag() {
        assertEquals(1, CoverStackHomeRules.swipeDelta(-60f))
        assertEquals(-1, CoverStackHomeRules.swipeDelta(48f))
        assertNull(CoverStackHomeRules.swipeDelta(-20f))
    }

    @Test fun pickLineSkipsWhatIsMissing() {
        assertEquals("Bark Psychosis · 1994 · Post-rock", CoverStackHomeRules.pickLine("Bark Psychosis", 1994, "Post-rock"))
        assertEquals("Bark Psychosis", CoverStackHomeRules.pickLine("Bark Psychosis", null, " "))
    }

    @Test fun radioLineNamesStationAndTime() {
        val utc = ZoneId.of("UTC")
        assertEquals("Last heard: FIP, 08:42", CoverStackHomeRules.radioLine(listOf(play("FIP", 8 * 3600 + 42 * 60.0)), utc))
        assertEquals("Last heard: FIP", CoverStackHomeRules.radioLine(listOf(play("FIP", null)), utc))
        assertEquals("Stations", CoverStackHomeRules.radioLine(emptyList(), utc))
        assertEquals("Stations", CoverStackHomeRules.radioLine(null, utc))
    }

    @Test fun statStripLeavesOutUnknownFiguresInsteadOfZero() {
        assertEquals(listOf("1,284 albums", "12 new this month", "Stats →"), CoverStackHomeRules.statStrip(HeroFigures(1284, 12, 7)))
        assertEquals(listOf("Stats →"), CoverStackHomeRules.statStrip(null))
    }
}
