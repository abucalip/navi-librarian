package app.discair.lyrics

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class LyricsTimelineTest {
    private fun timed(vararg starts: Long) = Lyrics(true, starts.map { LyricLine(it, "l$it") })
    private val three = LyricsTimeline(timed(1000, 2000, 3000))

    @Test fun beforeTheFirstLineNoneIsCurrent() {
        assertEquals(LyricsTimeline.NONE, three.lineAt(0)); assertEquals(LyricsTimeline.NONE, three.lineAt(999))
    }

    @Test fun exactBoundariesBelongToTheLineThatStarts() {
        assertEquals(0, three.lineAt(1000)); assertEquals(0, three.lineAt(1999))
        assertEquals(1, three.lineAt(2000)); assertEquals(2, three.lineAt(3000))
    }

    @Test fun afterTheLastLineTheLastStaysCurrent() = assertEquals(2, three.lineAt(10_000_000))

    @Test fun seekBackwardAndForwardGiveTheRightLine() {
        assertEquals(2, three.lineAt(3500)); assertEquals(0, three.lineAt(1200)); assertEquals(1, three.lineAt(2999))
    }

    @Test fun firstLineAtZeroIsCurrentFromTheStart() = assertEquals(0, LyricsTimeline(timed(0, 500)).lineAt(0))

    @Test fun duplicateStartsPickTheLastOfThem() = assertEquals(2, LyricsTimeline(timed(0, 500, 500, 900)).lineAt(600))

    @Test fun emptyOnelinePlainAndMissingCases() {
        assertEquals(LyricsTimeline.NONE, LyricsTimeline(Lyrics(true, emptyList())).lineAt(5))
        assertEquals(0, LyricsTimeline(timed(100)).lineAt(100)); assertEquals(LyricsTimeline.NONE, LyricsTimeline(timed(100)).lineAt(99))
        val plain = LyricsTimeline(Lyrics(false, listOf(LyricLine(null, "a"), LyricLine(null, "b"))))
        assertEquals(LyricsTimeline.NONE, plain.lineAt(5000)); assertFalse(plain.isTimed)
        assertEquals(LyricsTimeline.NONE, LyricsTimeline(null).lineAt(5000))
    }

    @Test fun offsetAlreadyInTheStartsMovesTheMarker() {
        // The data layer adds an offset of -300 to starts of 1000 and 2000.
        val l = found("""{"synced":true,"offset":-300,"line":[{"start":1000,"value":"a"},{"start":2000,"value":"b"}]}""")
        val t = LyricsTimeline(l)
        assertEquals(0, t.lineAt(700)); assertEquals(LyricsTimeline.NONE, t.lineAt(699)); assertEquals(1, t.lineAt(1700))
    }

    private fun found(entry: String) = (LyricsParse.answer(
        """{"subsonic-response":{"status":"ok","lyricsList":{"structuredLyrics":[$entry]}}}""", "en") as LyricsAnswer.Found).lyrics

    // --- the follower -----------------------------------------------------------------------

    private class Clock(var now: Long = 0)

    @Test fun checkRunsOnlyWhenVisibleAndPlayingWithATimedTimeline() = runTest {
        val clock = Clock()
        val f = LyricsFollower(this, { clock.now })
        f.setTimeline(three)
        assertFalse(f.isChecking)
        f.setVisible(true); assertFalse(f.isChecking)       // not playing
        f.setPlaying(true); assertTrue(f.isChecking)
        f.setVisible(false); assertFalse(f.isChecking)      // hidden stops it
        f.setVisible(true); assertTrue(f.isChecking)
        f.setPlaying(false); assertFalse(f.isChecking)      // pause stops it
        f.setPlaying(true); f.setTimeline(LyricsTimeline(Lyrics(false, emptyList()))); assertFalse(f.isChecking) // plain
        f.setTimeline(three); f.setVisible(false) // leave nothing running
    }

    @Test fun markerFollowsThePlayerEveryTickAndStopsAtTheTickRate() = runTest {
        val clock = Clock()
        var reads = 0
        val f = LyricsFollower(this, { reads++; clock.now })
        f.setTimeline(three); f.setVisible(true); f.setPlaying(true)
        runCurrent2()
        assertEquals(LyricsTimeline.NONE, f.line.value)
        clock.now = 1100; advanceTimeBy(250); runCurrent2(); assertEquals(0, f.line.value)
        clock.now = 2500; advanceTimeBy(250); runCurrent2(); assertEquals(1, f.line.value)
        // About four checks a second, not more.
        val before = reads; advanceTimeBy(1000); runCurrent2()
        assertTrue("reads=${reads - before}", reads - before in 3..5)
        f.setVisible(false)
    }

    @Test fun pauseFreezesTheMarkerAndNoMoreReadsHappen() = runTest {
        val clock = Clock(1500)
        var reads = 0
        val f = LyricsFollower(this, { reads++; clock.now })
        f.setTimeline(three); f.setVisible(true); f.setPlaying(true); runCurrent2()
        assertEquals(0, f.line.value)
        f.setPlaying(false)
        val frozen = reads; clock.now = 5000; advanceTimeBy(5_000); runCurrent2()
        assertEquals(frozen, reads); assertEquals(0, f.line.value)
    }

    @Test fun hiddenViewDoesNoWork() = runTest {
        var reads = 0
        val f = LyricsFollower(this, { reads++; 0 })
        f.setTimeline(three); f.setPlaying(true)
        advanceTimeBy(10_000); runCurrent2()
        assertEquals(1, reads) // only the one refresh from setTimeline
        assertFalse(f.isChecking)
    }

    @Test fun refreshShowsASeekAtOnceEvenWhilePaused() = runTest {
        val clock = Clock(0)
        val f = LyricsFollower(this, { clock.now })
        f.setTimeline(three); f.setVisible(true)
        clock.now = 3200; f.refresh(); assertEquals(2, f.line.value)
        clock.now = 1100; f.refresh(); assertEquals(0, f.line.value)
    }

    @Test fun showingTheViewAgainCatchesUpAtOnce() = runTest {
        val clock = Clock(0)
        val f = LyricsFollower(this, { clock.now })
        f.setTimeline(three); f.setPlaying(true)
        clock.now = 2100; f.setVisible(true)
        assertEquals(1, f.line.value); f.setVisible(false)
    }

    @Test fun aNewSongsTimelineReplacesTheMarker() = runTest {
        val clock = Clock(2100)
        val f = LyricsFollower(this, { clock.now })
        f.setTimeline(three); assertEquals(1, f.line.value)
        f.setTimeline(null); assertEquals(LyricsTimeline.NONE, f.line.value); assertFalse(f.isChecking)
    }

    private fun TestScope.runCurrent2() = testScheduler.runCurrent()
}
