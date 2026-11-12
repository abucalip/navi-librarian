package app.discair.player

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test

/** Checks when the controller offers the queue to Navidrome. The saver itself is tested in NavidromeQueueSaverTest. */
@OptIn(ExperimentalCoroutinesApi::class)
class PlayerQueueSyncTest {
    private fun song(i: Int) = QueueItem("s$i", "T$i", "A", "Al", durationSec = 200)
    private fun songs(n: Int) = (1..n).map { song(it) }

    private class Rig(val c: PlayerController, val port: FakePort, val saves: MutableList<RemotePlayQueue>)

    private fun TestScope.rig(): Rig {
        val port = FakePort()
        val saves = mutableListOf<RemotePlayQueue>()
        val remote = PlayQueueSync(RemotePlayQueueApi { saves += it; true }, backgroundScope)
        val scrobbler = ScrobbleCoordinator(RecordingApi(), backgroundScope, { "p" })
        val c = PlayerController(port, MemoryStorage(), scrobbler, backgroundScope, clock = { 0L }, remote = remote)
        return Rig(c, port, saves)
    }

    @Test fun startingAnAlbumOffersTheQueueFromTheStartingSong() = runTest {
        val r = rig()
        r.c.playItems(songs(3), 1)
        runCurrent()
        assertEquals(RemotePlayQueue(listOf("s2", "s3"), "s2", 0), r.saves.last())
    }

    @Test fun pausingOffersTheQueueWithTheCurrentPosition() = runTest {
        val r = rig()
        r.c.playItems(songs(2), 0)
        runCurrent()
        val before = r.saves.size
        r.port.positionMs = 73_000
        r.c.pause()
        runCurrent()
        assertEquals(before + 1, r.saves.size)
        assertEquals(RemotePlayQueue(listOf("s1", "s2"), "s1", 73_000), r.saves.last())
    }

    @Test fun aStationIsNeverOffered() = runTest {
        val r = rig()
        r.c.playItems(listOf(QueueItem("radio:1", "FM", "Station", "")), 0)
        runCurrent()
        assertEquals(0, r.saves.size)
    }

    @Test fun whilePlayingTheQueueIsOfferedEvery30Ticks() = runTest {
        val r = rig()
        r.c.playItems(songs(2), 0) // starts playing, which starts the ticker
        runCurrent()
        val after = r.saves.size
        advanceTimeBy(29_500)     // 29 ticks: no periodic save yet
        runCurrent()
        assertEquals(after, r.saves.size)
        advanceTimeBy(1_000)      // tick 30
        runCurrent()
        assertEquals(after + 1, r.saves.size)
    }
}
