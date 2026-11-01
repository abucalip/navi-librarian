package app.discair.player

import kotlin.random.Random
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class PlayQueueTest {
    private val rnd = Random(7)
    private fun song(i: Int) = QueueItem("s$i", "T$i", "A", "Al", durationSec = 200)
    private fun songs(n: Int) = (1..n).map(::song)
    private fun queue(n: Int, start: Int = 0) = QueueState().replace(songs(n), start, rnd).state

    @Test fun playAlbumReplacesAndStartsAtTheStart() {
        val q = queue(3).enqueue(songs(2), rnd).state.replace(songs(4), 0, rnd).state
        assertEquals(4, q.items.size); assertEquals(0, q.index); assertEquals("s1", q.current?.songId)
    }

    @Test fun enqueueAppendsAndPlayNextInsertsAfterCurrent() {
        val q = queue(3, 1)
        assertEquals(listOf("s1", "s2", "s3", "x"), q.enqueue(listOf(song(0).copy(songId = "x")), rnd).state.items.map { it.songId })
        assertEquals(listOf("s1", "s2", "x", "s3"), q.playNext(listOf(song(0).copy(songId = "x")), rnd).state.items.map { it.songId })
    }

    @Test fun capAt500IsReported() {
        val full = QueueState().replace(songs(600), 0, rnd)
        assertTrue(full.capped); assertEquals(MAX_QUEUE, full.state.items.size)
        val more = full.state.enqueue(songs(3), rnd)
        assertTrue(more.capped); assertEquals(MAX_QUEUE, more.state.items.size)
        assertFalse(queue(3).enqueue(songs(1), rnd).capped)
    }

    @Test fun nextAndPreviousWalkTheQueue() {
        val q = queue(3)
        assertEquals(1, q.nextIndex()); assertNull(q.previousIndex())
        assertNull(q.skipTo(2).nextIndex()); assertEquals(1, q.skipTo(2).previousIndex())
    }

    @Test fun repeatAllWraps() {
        val q = queue(3).withRepeat(RepeatMode.All)
        assertEquals(0, q.skipTo(2).nextIndex()); assertEquals(2, q.previousIndex())
    }

    @Test fun repeatOneLoopsOnlyWhenTheTrackEnds() {
        val q = queue(3, 1).withRepeat(RepeatMode.One)
        assertEquals(1, q.afterTrackEnded()); assertEquals(2, q.nextIndex())
    }

    @Test fun endOfQueueStopsWhenRepeatIsOff() {
        assertNull(queue(2, 1).afterTrackEnded())
        assertEquals(0, queue(1).withRepeat(RepeatMode.All).nextIndex())
        assertNull(QueueState().nextIndex())
    }

    @Test fun unavailableSongsAreSkipped() {
        val q = queue(4).markUnavailable("s2").markUnavailable("s3")
        assertEquals(3, q.nextIndex())
        assertNull(queue(3).markUnavailable("s2").markUnavailable("s3").nextIndex())
        // repeat-one does not loop on an unavailable song
        assertNull(queue(1).markUnavailable("s1").withRepeat(RepeatMode.One).afterTrackEnded())
    }

    @Test fun shuffleStartsAtCurrentVisitsEachOnceAndTurnsOffCleanly() {
        val q = queue(6, 2).withShuffle(true, rnd)
        assertEquals(2, q.shuffleOrder.first())
        assertEquals((0..5).toList(), q.shuffleOrder.sorted())
        var cur = q; val seen = mutableListOf(cur.index)
        while (true) { cur = cur.skipTo(cur.nextIndex() ?: break); seen += cur.index }
        assertEquals((0..5).toList(), seen.sorted())
        val off = q.withShuffle(false, rnd)
        assertTrue(off.shuffleOrder.isEmpty()); assertEquals(3, off.nextIndex())
        assertEquals(listOf("s1","s2","s3","s4","s5","s6"), off.items.map { it.songId })
    }

    @Test fun removeKeepsTheCurrentSong() {
        assertEquals("s3", queue(4, 2).remove(0, rnd).current?.songId)
        assertEquals("s3", queue(4, 2).remove(3, rnd).current?.songId)
        assertEquals("s4", queue(4, 2).remove(2, rnd).current?.songId)
        assertTrue(queue(1).remove(0, rnd).isEmpty)
        assertEquals(queue(2), queue(2).remove(9, rnd))
    }

    @Test fun moveKeepsTheCurrentSong() {
        assertEquals("s2", queue(4, 1).move(3, 0, rnd).current?.songId)
        assertEquals("s2", queue(4, 1).move(0, 3, rnd).current?.songId)
        assertEquals("s2", queue(4, 1).move(1, 3, rnd).current?.songId)
        assertEquals(listOf("s2", "s3", "s4", "s1"), queue(4).move(0, 3, rnd).items.map { it.songId })
    }

    @Test fun clearKeepsPreferencesButNotSongs() {
        val q = queue(3).withShuffle(true, rnd).withRepeat(RepeatMode.All).withVolume(0.4f).clear()
        assertTrue(q.isEmpty); assertEquals(RepeatMode.All, q.repeat); assertEquals(0.4f, q.volume, 0f)
    }

    @Test fun volumeIsClamped() {
        assertEquals(1f, queue(1).withVolume(5f).volume, 0f)
        assertEquals(0f, queue(1).withVolume(-1f).volume, 0f)
    }
}
