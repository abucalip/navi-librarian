package app.discair.player

import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class PlayQueueSyncTest {
    private fun song(i: Int) = QueueItem("s$i", "T$i", "A", "Al", durationSec = 200)
    private fun queue(n: Int, index: Int) = QueueState(items = (1..n).map { song(it) }, index = index)

    @Test fun snapshotStartsAtTheCurrentSongWithItsPosition() {
        val r = remotePlayQueueOf(queue(3, 1), positionMs = 42_000)!!
        assertEquals(listOf("s2", "s3"), r.songIds)
        assertEquals("s2", r.currentId)
        assertEquals(42_000L, r.positionMs)
    }

    @Test fun nothingIsSavedForAnEmptyQueueOrARadioStationAsCurrent() {
        assertNull(remotePlayQueueOf(QueueState(), 0))
        val station = QueueItem("radio:9", "FM", "Station", "")
        assertNull(remotePlayQueueOf(QueueState(items = listOf(station)), 0))
    }

    @Test fun aStationInTheMiddleEndsTheListAndIsNeverSent() {
        val station = QueueItem("radio:9", "FM", "Station", "")
        val q = QueueState(items = listOf(song(1), song(2), station, song(3)), index = 0)
        assertEquals(listOf("s1", "s2"), remotePlayQueueOf(q, 0)!!.songIds)
    }

    @Test fun anInvalidSongIdIsNotSent() {
        val bad = QueueItem("bad:id", "X", "A", "Al")
        assertNull(remotePlayQueueOf(QueueState(items = listOf(bad)), 0))
    }

    @Test fun theListIsCappedAtTheRemoteMaximum() {
        val r = remotePlayQueueOf(queue(REMOTE_QUEUE_MAX + 50, 0), 0)!!
        assertEquals(REMOTE_QUEUE_MAX, r.songIds.size)
        assertEquals("s1", r.songIds.first())
    }

    @Test fun onlyTheNewestPendingQueueIsSentWhileASaveIsRunning() = runTest {
        val sent = mutableListOf<String>()
        val gate = CompletableDeferred<Unit>()
        var first = true
        val api = RemotePlayQueueApi { q ->
            if (first) { first = false; gate.await() }
            sent += q.currentId
            true
        }
        val sync = PlayQueueSync(api, backgroundScope)
        fun q(id: String) = RemotePlayQueue(listOf(id), id, 0)

        sync.offer(q("a")); runCurrent()          // the first save starts and waits on the gate
        sync.offer(q("b")); sync.offer(q("c"))    // both arrive while it waits; only "c" should remain
        gate.complete(Unit); runCurrent()

        assertEquals(listOf("a", "c"), sent)
    }
}
