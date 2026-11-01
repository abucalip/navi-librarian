package app.discair.player.crossfade

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class CrossfadeTextTest {
    @Test fun lengthIsInWholeSecondsWithTheRightPlural() {
        assertEquals("1 second", CrossfadeText.length(1))
        assertEquals("5 seconds", CrossfadeText.length(5))
        assertEquals("12 seconds", CrossfadeText.length(12))
    }

    @Test fun anOutOfRangeLengthIsShownAsTheClampedValue() {
        assertEquals("1 second", CrossfadeText.length(0))
        assertEquals("1 second", CrossfadeText.length(-7))
        assertEquals("12 seconds", CrossfadeText.length(10_000))
    }

    @Test fun talkBackReadsTheLabelAndTheValue() {
        assertEquals("Crossfade length, 5 seconds", CrossfadeText.lengthSpoken(5))
        assertEquals("Crossfade length, 1 second", CrossfadeText.lengthSpoken(1))
    }

    @Test fun theSettingsRowSaysOffOrTheLength() {
        assertEquals("Off", CrossfadeText.summary(CrossfadeSettings(enabled = false, seconds = 8)))
        assertEquals("8 seconds", CrossfadeText.summary(CrossfadeSettings(enabled = true, seconds = 8)))
    }

    @Test fun theNowPlayingLinkAppearsOnlyWhileCrossfadeIsOn() {
        assertNull(CrossfadeText.nowPlayingLink(CrossfadeSettings(enabled = false)))
        assertEquals("Crossfade: 5 s", CrossfadeText.nowPlayingLink(CrossfadeSettings(enabled = true, seconds = 5)))
        assertEquals("Crossfade: 12 s", CrossfadeText.nowPlayingLink(CrossfadeSettings(enabled = true, seconds = 99)))
    }

    @Test fun everyStateHasWordsAndMentionsWhatItDoesNotDo() {
        assertTrue(CrossfadeText.switchHelp(true).startsWith("On."))
        assertTrue(CrossfadeText.switchHelp(true).contains("Skipping a song yourself is not faded"))
        assertTrue(CrossfadeText.switchHelp(false).startsWith("Off."))
        assertTrue(CrossfadeText.keepAlbumsHelp(true).startsWith("On."))
        assertTrue(CrossfadeText.keepAlbumsHelp(false).startsWith("Off."))
    }

    @Test fun theQualityLineAppearsOnlyBelowOriginal() {
        assertNull(CrossfadeText.qualityLine(null))
        assertTrue(CrossfadeText.qualityLine(128)!!.contains("below Original"))
        assertTrue(CrossfadeText.qualityLine(320)!!.isNotBlank())
    }

    @Test fun minusAndPlusStopAtTheEnds() {
        assertEquals(6, CrossfadeText.nudge(5, +1))
        assertEquals(4, CrossfadeText.nudge(5, -1))
        assertEquals(1, CrossfadeText.nudge(1, -1))
        assertEquals(12, CrossfadeText.nudge(12, +1))
        assertFalse(CrossfadeText.canLower(1)); assertTrue(CrossfadeText.canLower(2))
        assertFalse(CrossfadeText.canRaise(12)); assertTrue(CrossfadeText.canRaise(11))
    }

    @Test fun theSliderGivesWholeSecondsInRange() {
        assertEquals(5, CrossfadeText.fromSlider(5.2f))
        assertEquals(6, CrossfadeText.fromSlider(5.6f))
        assertEquals(1, CrossfadeText.fromSlider(-3f))
        assertEquals(12, CrossfadeText.fromSlider(99f))
        assertEquals(5, CrossfadeText.fromSlider(Float.NaN))
    }
}
