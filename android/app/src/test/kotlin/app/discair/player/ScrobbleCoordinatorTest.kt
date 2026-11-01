package app.discair.player

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.currentTime
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

private data class Call(val songId: String, val submission: Boolean, val timeMs: Long, val atMs: Long)

private class FakeApi(var script: (Call) -> SendOutcome = { SendOutcome.Accepted }, private val now: () -> Long) : ScrobbleApi {
    val calls = mutableListOf<Call>()
    var throwNext = false
    override suspend fun send(songId: String, submission: Boolean, timeMs: Long): SendOutcome {
        val call = Call(songId, submission, timeMs, now())
        calls += call
        if (throwNext) { throwNext = false; throw IllegalStateException("boom") }
        return script(call)
    }
    val scrobbles get() = calls.filter { it.submission }
    val nowPlaying get() = calls.filter { !it.submission }
}

@OptIn(ExperimentalCoroutinesApi::class)
class ScrobbleCoordinatorTest {
    private var ids = 0
    private fun TestScope.setup(enabled: Boolean = true, script: (Call) -> SendOutcome = { SendOutcome.Accepted }): Pair<ScrobbleCoordinator, FakeApi> {
        val api = FakeApi(script) { currentTime }
        return ScrobbleCoordinator(api, this, { "play${ids++}" }, enabled = enabled) to api
    }

    /** Plays media seconds [from, to] at one-second ticks. */
    private fun ScrobbleCoordinator.run(from: Int, to: Int) {
        onTick(from * 1000L, true)
        for (s in from + 1..to) onTick(s * 1000L, true)
    }

    @Test fun nowPlayingThenOneScrobbleAtHalf() = runTest {
        val (c, api) = setup()
        c.startPlay("song1", 200, 5_000)
        c.onPlaying(); c.onPlaying(); runCurrent()
        assertEquals(1, api.nowPlaying.size)
        c.run(0, 90); runCurrent()
        assertEquals(0, api.scrobbles.size)
        c.run(90, 200); runCurrent()
        assertEquals(1, api.scrobbles.size)
        assertEquals(Call("song1", true, 5_000, 0), api.scrobbles[0])
    }

    @Test fun aTrackThatNeverPlaysSendsNothing() = runTest {
        val (c, api) = setup()
        c.startPlay("song1", 200, 0); runCurrent()
        assertTrue(api.calls.isEmpty())
    }

    @Test fun shortTrackSendsNowPlayingOnly() = runTest {
        val (c, api) = setup()
        c.startPlay("short", 20, 0); c.onPlaying(); c.run(0, 20); runCurrent()
        assertEquals(1, api.nowPlaying.size); assertEquals(0, api.scrobbles.size)
    }

    @Test fun skipAtTenSecondsDoesNotScrobble() = runTest {
        val (c, api) = setup()
        c.startPlay("a", 200, 0); c.onPlaying(); c.run(0, 10)
        c.startPlay("b", 200, 10_000); c.onPlaying(); runCurrent()
        assertEquals(0, api.scrobbles.size); assertEquals(2, api.nowPlaying.size)
    }

    @Test fun repeatOneAndReplayEachCountAsANewPlay() = runTest {
        val (c, api) = setup()
        repeat(3) { n ->
            c.startPlay("loop", 60, 1_000L * n); c.onPlaying(); c.run(0, 40); runCurrent()
        }
        assertEquals(3, api.scrobbles.size)
        assertEquals(listOf(0L, 1000L, 2000L), api.scrobbles.map { it.timeMs })
        assertEquals(3, api.nowPlaying.size)
    }

    @Test fun seekingToTheMiddleDoesNotScrobble() = runTest {
        val (c, api) = setup()
        c.startPlay("a", 200, 0); c.onPlaying(); c.run(0, 5)
        c.onSeek(150_000); c.run(150, 190); runCurrent()
        assertEquals(0, api.scrobbles.size)
    }

    @Test fun reloadStartsFreshWithNoCarriedPlayedTime() = runTest {
        val (c1, api) = setup()
        c1.startPlay("a", 200, 0); c1.onPlaying(); c1.run(0, 90)
        val (c2, api2) = setup()
        c2.startPlay("a", 200, 99_000); c2.onPlaying(); c2.run(0, 20); runCurrent()
        assertEquals(0, api2.scrobbles.size)
        c2.run(20, 100); runCurrent()
        assertEquals(1, api2.scrobbles.size)
    }

    // --- retries ---

    @Test fun notSentIsRetriedThreeTimesWithBackoffAndTheOriginalTime() = runTest {
        val (c, api) = setup(script = { if (it.submission) SendOutcome.NotSent else SendOutcome.Accepted })
        c.startPlay("a", 200, 7_000); c.onPlaying(); c.run(0, 100); runCurrent()
        assertEquals(1, api.scrobbles.size)
        advanceTimeBy(2_000); runCurrent(); assertEquals(2, api.scrobbles.size)
        advanceTimeBy(10_000); runCurrent(); assertEquals(3, api.scrobbles.size)
        advanceTimeBy(30_000); runCurrent(); assertEquals(4, api.scrobbles.size)
        advanceTimeBy(600_000); advanceUntilIdle()
        assertEquals(4, api.scrobbles.size) // one send and at most three retries
        assertEquals(listOf(7_000L), api.scrobbles.map { it.timeMs }.distinct())
        assertEquals(listOf(0L, 2_000L, 12_000L, 42_000L), api.scrobbles.map { it.atMs })
    }

    @Test fun retrySucceedingStopsRetrying() = runTest {
        var n = 0
        val (c, api) = setup(script = { if (it.submission && n++ < 1) SendOutcome.NotSent else SendOutcome.Accepted })
        c.startPlay("a", 200, 0); c.onPlaying(); c.run(0, 100); runCurrent()
        advanceTimeBy(60_000); advanceUntilIdle()
        assertEquals(2, api.scrobbles.size)
    }

    @Test fun aLostResponseAfterSendIsNeverRetriedSoItCannotDuplicate() = runTest {
        // Navidrome recorded the play, but the answer was lost: the outcome is ambiguous.
        val (c, api) = setup(script = { if (it.submission) SendOutcome.Ambiguous else SendOutcome.Accepted })
        c.startPlay("a", 200, 0); c.onPlaying(); c.run(0, 100); c.run(100, 200)
        advanceTimeBy(600_000); advanceUntilIdle()
        assertEquals(1, api.scrobbles.size)
    }

    @Test fun nowPlayingIsNeverRetried() = runTest {
        val (c, api) = setup(script = { SendOutcome.NotSent })
        c.startPlay("a", 200, 0); c.onPlaying(); runCurrent()
        advanceTimeBy(600_000); advanceUntilIdle()
        assertEquals(1, api.nowPlaying.size)
    }

    @Test fun anExceptionFromTheClientIsSwallowedAndNotRetried() = runTest {
        val (c, api) = setup()
        api.throwNext = true
        c.startPlay("a", 200, 0); c.onPlaying(); c.run(0, 100); runCurrent()
        advanceTimeBy(600_000); advanceUntilIdle()
        assertEquals(1, api.scrobbles.size)
    }

    @Test fun thePlayIsSentOncePerPlayEvenIfTheThresholdIsCrossedAgain() = runTest {
        val (c, api) = setup()
        c.startPlay("a", 200, 0); c.onPlaying(); c.run(0, 100); c.onSeek(0); c.run(0, 150); runCurrent()
        assertEquals(1, api.scrobbles.size)
    }

    // --- Settings toggle ---

    @Test fun disabledSendsNothingAtAll() = runTest {
        val (c, api) = setup(enabled = false)
        c.startPlay("a", 200, 0); c.onPlaying(); c.run(0, 200); runCurrent()
        assertTrue(api.calls.isEmpty())
    }

    @Test fun turningOffMidTrackCancelsPendingRetriesAndSendsNothingMore() = runTest {
        val (c, api) = setup(script = { if (it.submission) SendOutcome.NotSent else SendOutcome.Accepted })
        c.startPlay("a", 200, 0); c.onPlaying(); c.run(0, 100); runCurrent()
        assertEquals(1, api.scrobbles.size)
        c.setEnabled(false)
        advanceTimeBy(600_000); advanceUntilIdle()
        assertEquals(1, api.scrobbles.size)
        c.run(100, 200); runCurrent()
        assertEquals(1, api.scrobbles.size)
    }

    @Test fun turningOffBeforeTheThresholdSendsNothingForThatPlay() = runTest {
        val (c, api) = setup()
        c.startPlay("a", 200, 0); c.onPlaying(); c.run(0, 90)
        c.setEnabled(false); c.run(90, 200); runCurrent()
        assertEquals(0, api.scrobbles.size); assertEquals(1, api.nowPlaying.size)
    }

    @Test fun turningOnMidTrackCountsFromThenWithNoBackfillAndNoNowPlaying() = runTest {
        val (c, api) = setup(enabled = false)
        c.startPlay("a", 200, 0); c.onPlaying(); c.run(0, 90)
        c.setEnabled(true)
        c.onPlaying(); c.run(90, 150); runCurrent()
        assertEquals(0, api.scrobbles.size) // only 60 s counted since enabling
        assertEquals(0, api.nowPlaying.size)
        c.run(150, 200); runCurrent()
        assertEquals(1, api.scrobbles.size)
    }

    @Test fun newSongAfterReEnablingScrobblesNormally() = runTest {
        val (c, api) = setup()
        c.setEnabled(false); c.setEnabled(true)
        c.startPlay("a", 200, 0); c.onPlaying(); c.run(0, 100); runCurrent()
        assertEquals(1, api.nowPlaying.size); assertEquals(1, api.scrobbles.size)
    }

    @Test fun endPlayStopsCounting() = runTest {
        val (c, api) = setup()
        c.startPlay("a", 200, 0); c.onPlaying(); c.run(0, 50); c.endPlay(); c.run(50, 200); runCurrent()
        assertEquals(0, api.scrobbles.size)
    }
}
