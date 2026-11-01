package app.discair.player

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** A fake player that counts what is open, to prove release happens on every path. */
private class FakePlayerHandles {
    var open = 0
    fun acquire() { open++ }
    fun release() { open-- }
}

class ReleaseGuardTest {
    @Test fun releaseRunsOnceEvenWhenCalledRepeatedly() {
        val handles = FakePlayerHandles().apply { acquire(); acquire() }
        val guard = ReleaseGuard { handles.release(); handles.release() }
        guard.release(); guard.release(); guard.release()
        assertEquals(0, handles.open); assertTrue(guard.isReleased)
    }

    @Test fun nothingIsReleasedBeforeTheFirstCall() {
        val handles = FakePlayerHandles().apply { acquire() }
        val guard = ReleaseGuard { handles.release() }
        assertFalse(guard.isReleased); assertEquals(1, handles.open)
    }
}
