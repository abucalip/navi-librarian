package app.discair.player

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class PlayerControllerTest {
    private fun song(i: Int, dur: Int = 200) = QueueItem("s$i", "T$i", "A", "Al", durationSec = dur)
    private fun songs(n: Int) = (1..n).map { song(it) }

    private class Rig(val c: PlayerController, val port: FakePort, val storage: MemoryStorage, val api: RecordingApi)

    private fun TestScope.rig(saved: String? = null): Rig {
        val port = FakePort(); val storage = MemoryStorage(saved); val api = RecordingApi()
        val scrobbler = ScrobbleCoordinator(api, backgroundScope, { "p" + System.nanoTime() })
        return Rig(PlayerController(port, storage, scrobbler, backgroundScope, clock = { 42_000L }), port, storage, api)
    }

    @Test fun playItemsReplacesTheQueueStartsPlayingAndSaves() = runTest {
        val r = rig()
        r.c.playItems(songs(3), 1)
        val s = r.c.state.value
        assertTrue(s.visible); assertEquals(1, s.queue.index); assertTrue(s.isPlaying)
        assertEquals("T2 by A", s.announcement)
        assertEquals("set 3 @1 play=true", r.port.log.first())
        assertEquals(3, QueueCodec.decode(r.storage.text).items.size)
    }

    @Test fun restoreIsPausedAndStartsNoPlay() = runTest {
        val saved = QueueCodec.encode(QueueState().replace(songs(3), 2).state.withPosition(51_000))
        val r = rig(saved)
        r.c.restore()
        runCurrent()
        assertTrue(r.port.log.contains("set 3 @2 play=false"))
        assertFalse(r.c.state.value.isPlaying); assertEquals(51_000, r.c.state.value.positionMs)
        assertTrue(r.api.calls.isEmpty()) // no now-playing until the user presses play
    }

    @Test fun nowPlayingIsSentWhenPlaybackStartsWithThePlayStartTime() = runTest {
        val r = rig()
        r.c.playItems(songs(2)); runCurrent()
        assertEquals(listOf(Triple("s1", false, 42_000L)), r.api.calls)
    }

    @Test fun pausingAndResumingDoesNotStartANewPlay() = runTest {
        val r = rig()
        r.c.playItems(songs(2)); r.c.playPause(); r.c.playPause(); runCurrent()
        assertEquals(1, r.api.calls.size)
    }

    @Test fun repeatOneLoopIsANewPlay() = runTest {
        val r = rig()
        r.c.playItems(songs(1)); runCurrent()
        r.port.listener!!.onItemChanged(0, repeated = true); runCurrent()
        assertEquals(2, r.api.calls.size)
    }

    @Test fun aScrobbleIsSentAfterHalfTheTrackIsPlayed() = runTest {
        val r = rig(); r.port.durationMs = 120_000
        r.c.playItems(listOf(song(1, 120)))
        for (i in 1..70) { r.port.positionMs = i * 1000L; advanceTimeBy(1_000) }
        runCurrent()
        assertEquals(1, r.api.calls.count { it.second })
    }

    @Test fun seekingForwardDoesNotCreditTime() = runTest {
        val r = rig()
        r.c.playItems(listOf(song(1, 120)))
        r.port.positionMs = 1000; advanceTimeBy(1_000)
        r.c.seekTo(100_000); r.port.positionMs = 100_000
        advanceTimeBy(1_000); r.port.positionMs = 101_000; advanceTimeBy(1_000); runCurrent()
        assertEquals(0, r.api.calls.count { it.second })
        assertTrue(r.port.log.contains("seek 100000"))
    }

    @Test fun enqueueAppendsAndPlayNextInsertsAfterCurrent() = runTest {
        val r = rig(); r.c.playItems(songs(3), 1)
        r.c.enqueue(listOf(song(9))); r.c.playNext(listOf(song(8)))
        assertTrue(r.port.log.contains("add [s9] @3"))
        assertTrue(r.port.log.contains("add [s8] @2"))
        assertEquals(listOf("s1", "s2", "s8", "s3", "s9"), r.c.state.value.queue.items.map { it.songId })
    }

    @Test fun enqueueOnAnEmptyQueueLoadsItPaused() = runTest {
        val r = rig(); r.c.enqueue(songs(2))
        assertEquals("set 2 @0 play=false", r.port.log.single())
        assertFalse(r.c.state.value.isPlaying)
    }

    @Test fun theCapIsReportedInWords() = runTest {
        val r = rig(); r.c.playItems((1..MAX_QUEUE).map(::song))
        r.c.enqueue(listOf(song(9999)))
        assertEquals("Queue is full at 500 songs.", r.c.state.value.status)
        assertEquals(MAX_QUEUE, r.c.state.value.queue.items.size)
    }

    @Test fun removeAndMoveAreMirroredAndSaved() = runTest {
        val r = rig(); r.c.playItems(songs(4), 0)
        r.c.move(0, 3); r.c.remove(1)
        assertTrue(r.port.log.contains("move 0->3")); assertTrue(r.port.log.contains("remove 1"))
        assertEquals(3, QueueCodec.decode(r.storage.text).items.size)
    }

    @Test fun removingTheLastSongClearsEverything() = runTest {
        val r = rig(); r.c.playItems(songs(1)); r.c.remove(0)
        assertFalse(r.c.state.value.visible); assertNull(r.storage.text); assertTrue(r.port.log.contains("clear"))
    }

    @Test fun clearStopsAudioAndDeletesTheSavedQueue() = runTest {
        val r = rig(); r.c.playItems(songs(2)); r.c.clear()
        assertFalse(r.c.state.value.visible); assertFalse(r.c.state.value.isPlaying); assertNull(r.storage.text)
    }

    @Test fun unavailableSongIsMarkedAndSkippedWithWords() = runTest {
        val r = rig(); r.c.playItems(songs(3))
        r.port.listener!!.onError(PlaybackFailure.Unavailable(), 0)
        val s = r.c.state.value
        assertTrue("s1" in s.queue.unavailable); assertTrue(s.status!!.contains("not available. Skipped"))
        assertTrue(r.port.log.contains("skipPastFailure"))
    }

    @Test fun unavailableLastSongStopsWithoutSkipping() = runTest {
        val r = rig(); r.port.hasNext = false; r.c.playItems(songs(1))
        r.port.listener!!.onError(PlaybackFailure.Unavailable(), 0)
        assertFalse(r.c.state.value.isPlaying); assertFalse(r.c.state.value.status!!.contains("Skipped"))
    }

    @Test fun signInAgainPausesOnceAndDoesNotLoop() = runTest {
        val r = rig(); r.c.playItems(songs(3))
        r.port.listener!!.onError(PlaybackFailure.SignInAgain(), 0)
        assertTrue(r.c.state.value.signInRequired); assertFalse(r.c.state.value.isPlaying)
        assertEquals(0, r.port.log.count { it == "skipPastFailure" || it == "retry" })
    }

    @Test fun networkFailureWaitsThenResumesOnceWhenTheConnectionReturns() = runTest {
        val r = rig(); r.c.playItems(songs(2))
        r.port.listener!!.onError(PlaybackFailure.Network(), 0)
        assertTrue(r.c.state.value.waitingForNetwork)
        assertEquals(0, r.port.log.count { it == "retry" })
        r.c.networkAvailable(); r.c.networkAvailable()
        assertEquals(1, r.port.log.count { it == "retry" })
    }

    @Test fun unsupportedFormatRetriesOnceWithMp3ThenGivesUp() = runTest {
        val r = rig(); r.c.playItems(songs(2))
        r.port.listener!!.onError(PlaybackFailure.UnsupportedFormat(), 0)
        assertEquals(1, r.port.log.count { it.startsWith("mp3") })
        r.port.listener!!.onError(PlaybackFailure.UnsupportedFormat(), 0)
        assertEquals(1, r.port.log.count { it.startsWith("mp3") })
        assertTrue("s1" in r.c.state.value.queue.unavailable)
    }

    @Test fun trackChangesAreAnnouncedOnceNotOnEveryTick() = runTest {
        val r = rig(); r.c.playItems(songs(2))
        advanceTimeBy(10_000); runCurrent()
        assertEquals("T1 by A", r.c.state.value.announcement)
        r.port.listener!!.onItemChanged(1, false)
        assertEquals("T2 by A", r.c.state.value.announcement)
    }

    @Test fun shuffleRepeatAndVolumeAreMirroredAndSaved() = runTest {
        val r = rig(); r.c.playItems(songs(3))
        r.c.setShuffle(true); r.c.cycleRepeat(); r.c.cycleRepeat(); r.c.cycleRepeat(); r.c.setVolume(2f)
        assertTrue(r.port.log.containsAll(listOf("shuffle true", "repeat All", "repeat One", "repeat Off", "volume 1.0")))
        assertTrue(QueueCodec.decode(r.storage.text).shuffle)
    }

    @Test fun scrobblingToggleStopsEverything() = runTest {
        val r = rig(); r.c.setScrobbling(false); r.c.playItems(songs(2)); runCurrent()
        assertTrue(r.api.calls.isEmpty())
    }

    @Test fun signOutLeavesNothingOnDisk() = runTest {
        val r = rig(); r.c.playItems(songs(2)); r.c.signOut()
        assertNull(r.storage.text); assertFalse(r.c.state.value.visible)
    }
}
