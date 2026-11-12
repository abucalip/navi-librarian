package app.discair.ui

import app.discair.ui.player.CoverStackPlayerRules
import org.junit.Assert.assertEquals
import org.junit.Test

class CoverStackPlayerRulesTest {
    @Test fun titlesFollowTheMockup() {
        assertEquals("Now playing", CoverStackPlayerRules.frameTitle(CoverStackPlayerRules.VIEW_PLAYER))
        assertEquals("Queue", CoverStackPlayerRules.frameTitle(CoverStackPlayerRules.VIEW_QUEUE))
        assertEquals("Lyrics", CoverStackPlayerRules.frameTitle(CoverStackPlayerRules.VIEW_LYRICS))
    }

    @Test fun theLeftButtonClosesOnThePlayerAndReturnsFromTheOtherViews() {
        assertEquals("Close now playing", CoverStackPlayerRules.backLabel(0))
        assertEquals("Back to now playing", CoverStackPlayerRules.backLabel(1))
        assertEquals("Back to now playing", CoverStackPlayerRules.backLabel(2))
    }

    @Test fun nextUpIsAfterThePlayingSongAndEarlierIsBefore() {
        assertEquals(listOf(3, 4, 5), CoverStackPlayerRules.nextUp(6, 2))
        assertEquals(listOf(0, 1), CoverStackPlayerRules.earlier(6, 2))
        assertEquals(emptyList<Int>(), CoverStackPlayerRules.nextUp(6, 5))
        assertEquals(emptyList<Int>(), CoverStackPlayerRules.earlier(6, 0))
        assertEquals(emptyList<Int>(), CoverStackPlayerRules.nextUp(0, 0))
        assertEquals(emptyList<Int>(), CoverStackPlayerRules.earlier(0, 3))
    }

    @Test fun everySongIsInExactlyOneGroup() {
        val size = 7
        for (i in 0 until size) {
            val all = CoverStackPlayerRules.earlier(size, i) + i + CoverStackPlayerRules.nextUp(size, i)
            assertEquals((0 until size).toList(), all)
        }
    }

    @Test fun labelsCountSongs() {
        assertEquals("Next up · 5 songs", CoverStackPlayerRules.nextUpLabel(5))
        assertEquals("Next up · 1 song", CoverStackPlayerRules.nextUpLabel(1))
        assertEquals("Next up · 0 songs", CoverStackPlayerRules.nextUpLabel(0))
    }
}
