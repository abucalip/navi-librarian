package app.discair.player

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class SleepTimerTest {
    private fun TestScope.timer(expired: MutableList<Long>) = SleepTimer(backgroundScope, onExpire = { expired += testScheduler.currentTime }, clock = { testScheduler.currentTime })

    @Test fun firesOnceAfterTheChosenTimeAndClears() = runTest {
        val expired = mutableListOf<Long>()
        val t = timer(expired)
        t.start(15); runCurrent()
        assertEquals(15 * 60_000L, t.remainingMs.value)
        advanceTimeBy(15 * 60_000L - 1_000); runCurrent()
        assertEquals(0, expired.size)
        advanceTimeBy(2_000); runCurrent()
        assertEquals(1, expired.size); assertNull(t.remainingMs.value)
        advanceTimeBy(60_000); runCurrent()
        assertEquals(1, expired.size)
    }

    @Test fun cancelStopsItAndStartingAgainRestarts() = runTest {
        val expired = mutableListOf<Long>()
        val t = timer(expired)
        t.start(15); advanceTimeBy(60_000); t.cancel(); advanceTimeBy(20 * 60_000L); runCurrent()
        assertEquals(0, expired.size); assertNull(t.remainingMs.value)
        t.start(15); advanceTimeBy(10 * 60_000L); t.start(30); advanceTimeBy(20 * 60_000L); runCurrent()
        assertEquals(0, expired.size) // the first 15 would have fired by now
        advanceTimeBy(11 * 60_000L); runCurrent()
        assertEquals(1, expired.size)
    }

    @Test fun wordsRoundUpAndSayOff() {
        assertEquals("Sleep timer: off", sleepTimerText(null))
        assertEquals("Sleep timer: stops in 15 min", sleepTimerText(15 * 60_000L))
        assertEquals("Sleep timer: stops in 1 min", sleepTimerText(1_000))
        assertEquals("Sleep timer: stops in 12 min", sleepTimerText(11 * 60_000L + 1))
    }
}
