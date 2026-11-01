package app.discair.player

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ScrobbleTrackerTest {
    private fun tracker(serverSec: Int, playerSec: Int? = null) =
        ScrobbleTracker(Play("p1", "s1", 1_000), serverSec).also { t -> playerSec?.let(t::onPlayerDuration) }

    /** Plays [seconds] of media from [from] in one-second ticks; returns the tick count at which it became due, or null. */
    private fun ScrobbleTracker.play(from: Int, seconds: Int): Int? {
        onTick(from * 1000L, true)
        for (i in 1..seconds) if (onTick((from + i) * 1000L, true)) return i
        return null
    }

    @Test fun thresholdIsHalfTheTrackOrFourMinutes() {
        assertEquals(100_000L, ScrobbleRules.thresholdMs(200))
        assertEquals(240_000L, ScrobbleRules.thresholdMs(480))
        assertEquals(240_000L, ScrobbleRules.thresholdMs(900))
        assertEquals(15_000L, ScrobbleRules.thresholdMs(30))
        assertEquals(240_000L, ScrobbleRules.thresholdMs(null))
    }

    @Test fun scrobblesOnceAtHalf() {
        val t = tracker(200)
        assertEquals(100, t.play(0, 150))
        assertFalse(t.onTick(120_000, true)); assertFalse(t.onTick(121_000, true))
    }

    @Test fun longTracksUseFourMinutes() = assertEquals(240, tracker(900).play(0, 400))

    @Test fun tracksUnder30SecondsNeverScrobble() {
        assertNull(tracker(29).play(0, 29))
        assertEquals(15, tracker(30).play(0, 30))
    }

    @Test fun missingServerDurationUsesThePlayers() {
        assertEquals(60, tracker(0, 120).play(0, 200))
        assertEquals(60, tracker(-5, 120).play(0, 200))
    }

    @Test fun noDurationAtAllFallsBackToFourMinutes() {
        assertEquals(240, tracker(0).play(0, 300))
        assertEquals(240, tracker(0, 0).play(0, 300))
    }

    @Test fun durationArrivingLaterIsUsedFromThen() {
        val t = tracker(0)
        assertNull(t.play(0, 70))
        t.onPlayerDuration(120)
        assertTrue(t.onTick(71_000, true)) // 71 s played, threshold now 60 s
    }

    @Test fun durationRuleDetails() {
        assertEquals(250, ScrobbleRules.effectiveDurationSec(200, 250))   // 20 % apart: larger
        assertEquals(200, ScrobbleRules.effectiveDurationSec(200, 210))   // within 10 %: server
        assertEquals(250, ScrobbleRules.effectiveDurationSec(250, 200))
        assertEquals(200, ScrobbleRules.effectiveDurationSec(200, null))
        assertEquals(90, ScrobbleRules.effectiveDurationSec(0, 90))
        assertNull(ScrobbleRules.effectiveDurationSec(0, null))
        assertNull(ScrobbleRules.effectiveDurationSec(-1, -1))
    }

    @Test fun seekingForwardPastTheThresholdDoesNotScrobble() {
        val t = tracker(200)
        t.play(0, 10)
        t.onSeek(10_000)
        assertFalse(t.onTick(150_000, true)) // jump of 140 s: no credit
        assertEquals(10_000L, t.playedMs)
    }

    @Test fun seekingBackwardDoesNotSubtract() {
        val t = tracker(200)
        t.play(0, 40)
        t.onSeek(5_000)
        assertFalse(t.onTick(6_000, true))
        assertEquals(41_000L, t.playedMs)
    }

    @Test fun aJumpWithoutASeekCallbackIsStillNotCredited() {
        val t = tracker(200)
        t.onTick(0, true); t.onTick(1_000, true)
        t.onTick(100_000, true) // a seek the player did not announce
        assertEquals(1_000L, t.playedMs)
    }

    @Test fun pausedTimeAddsNothing() {
        val t = tracker(200)
        t.play(0, 10)
        for (i in 0..300) t.onTick(10_000, false) // paused for a long time
        t.onTick(10_000, true); t.onTick(11_000, true)
        assertEquals(11_000L, t.playedMs)
    }

    @Test fun bufferingAddsNothingAndDoesNotCreditTheGap() {
        val t = tracker(200)
        t.play(0, 10)
        t.onStall()
        t.onTick(10_000, true)   // resumes: first tick only sets the start
        t.onTick(11_000, true)
        assertEquals(11_000L, t.playedMs)
    }

    @Test fun playbackSpeedDoesNotChangeMediaTime() {
        val t = tracker(200)
        // 2x speed: one second of wall time advances two seconds of media; ticks of 2 s are credited as media time
        t.onTick(0, true)
        for (i in 1..50) t.onTick(i * 2_000L, true)
        assertEquals(100_000L, t.playedMs)
        assertEquals(true, t.playedMs >= ScrobbleRules.thresholdMs(200))
    }

    @Test fun nowPlayingIsSentOnceOnly() {
        val t = tracker(200)
        assertTrue(t.onPlaying()); assertFalse(t.onPlaying()); assertFalse(t.onPlaying())
    }

    @Test fun nowPlayingAlreadySentStaysSent() {
        assertFalse(ScrobbleTracker(Play("p", "s", 0), 200, nowPlayingAlreadySent = true).onPlaying())
    }
}
