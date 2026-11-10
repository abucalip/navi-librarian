package app.discair.player

import app.discair.model.RadioDownload
import app.discair.model.RadioGetResult
import app.discair.model.RadioNow
import app.discair.model.RadioNowState
import app.discair.model.RadioStation
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class RadioPlaybackTest {
    private val station = RadioStation("11", "Rock FM", true, "https://relay.example/radio/stream/tok", null, "/api/radio/stations/11/logo", false, emptyList(), null)
    private fun now(play: Long?, song: String = "Artist - Song") = RadioNow(RadioNowState.Ok, song, "Artist", "Song", play, false, null)

    private class Rig(val radio: RadioPlayback, val c: PlayerController, val port: FakePort, val storage: MemoryStorage, val api: RecordingApi, val asked: MutableList<String>, val gets: MutableList<Long>)

    private fun TestScope.rig(answers: () -> RadioNow, get: (Long) -> RadioGetResult = { RadioGetResult(true, "Looking for it.") }): Rig {
        val port = FakePort(); val storage = MemoryStorage(); val api = RecordingApi()
        val c = PlayerController(port, storage, ScrobbleCoordinator(api, backgroundScope), backgroundScope, clock = { 1L })
        val asked = mutableListOf<String>(); val gets = mutableListOf<Long>()
        val radio = RadioPlayback(
            c, backgroundScope, StandardTestDispatcher(testScheduler),
            nowFor = { asked += it; answers() }, getPlay = { gets += it; get(it) },
            absolute = { if (it.startsWith("http")) it else "https://lib.example$it" },
            artwork = { byteArrayOf(1) }, pollMs = 5_000,
        )
        return Rig(radio, c, port, storage, api, asked, gets)
    }

    @Test fun playingAStationQueuesALiveItemWithoutSavingOrScrobbling() = runTest {
        val r = rig({ now(null) })
        r.radio.play(station); runCurrent()
        val item = r.c.state.value.current!!
        assertTrue(item.isRadio); assertEquals("Rock FM", item.title); assertEquals("https://relay.example/radio/stream/tok", item.liveUrl)
        assertTrue(item.coverUrl.contains("/logo?size=512"))
        assertTrue(r.c.state.value.isPlaying)
        assertEquals(null, r.storage.text) // the relay token is never saved
        assertTrue(r.api.calls.isEmpty()) // Navidrome never hears about a radio song
        assertEquals(0L, r.c.state.value.durationMs)
    }

    @Test fun seekingALiveStreamDoesNothing() = runTest {
        val r = rig({ now(null) })
        r.radio.play(station); runCurrent()
        r.c.seekTo(30_000)
        assertFalse(r.port.log.any { it.startsWith("seek") })
    }

    @Test fun liveSongShowsUnderTheStationAndUpdatesInPlace() = runTest {
        val r = rig({ now(null) })
        r.radio.play(station); runCurrent()
        assertEquals("Artist - Song", r.c.state.value.current!!.artist)
        assertTrue(r.port.log.contains("update 0 Artist - Song art=true"))
        assertEquals(RadioDownload.Waiting, r.radio.state.value.download)
    }

    @Test fun downloadEnablesOnlyOncePlayIdArrivesAndSendsOneRequest() = runTest {
        var current = now(null)
        val r = rig({ current })
        r.radio.play(station); runCurrent()
        assertFalse(r.radio.state.value.download.enabled)
        current = now(9); advanceTimeBy(5_001); runCurrent()
        assertEquals(RadioDownload.Ready, r.radio.state.value.download)
        r.radio.download(9); r.radio.download(9); runCurrent()
        assertEquals(listOf(9L), r.gets)
        assertEquals(RadioDownload.Done, r.radio.state.value.download)
        assertEquals("Looking for it.", r.radio.state.value.message)
    }

    @Test fun refusedDownloadKeepsTheServersWordsAndOffersTryAgain() = runTest {
        val r = rig({ now(4) }, get = { RadioGetResult(false, "Could not find which album this song is on.") })
        r.radio.play(station); runCurrent()
        r.radio.download(4); runCurrent()
        assertEquals(RadioDownload.Failed, r.radio.state.value.download)
        assertEquals("Could not find which album this song is on.", r.radio.state.value.message)
        r.radio.download(4); runCurrent()
        assertEquals(listOf(4L, 4L), r.gets) // a retry is allowed after a refusal
    }

    @Test fun noQuestionToTheServerWhilePausedOrForAStationThatIsNotRelayed() = runTest {
        val r = rig({ now(null) })
        r.radio.play(station); runCurrent()
        r.c.playPause(); runCurrent()
        val before = r.asked.size
        advanceTimeBy(20_000); runCurrent()
        assertEquals(before, r.asked.size)
        val plain = rig({ now(null) })
        plain.radio.play(station.copy(proxied = false)); runCurrent(); advanceTimeBy(20_000); runCurrent()
        assertTrue(plain.asked.isEmpty())
        assertEquals(RadioNowState.NotProxied, plain.radio.state.value.now!!.state)
    }

    @Test fun pollingStopsWhenASongReplacesTheStation() = runTest {
        val r = rig({ now(null) })
        r.radio.play(station); runCurrent()
        r.c.playItems(listOf(QueueItem("s1", "T", "A", "Al"))); runCurrent()
        advanceTimeBy(5_001); runCurrent()
        val n = r.asked.size
        advanceTimeBy(30_000); runCurrent()
        assertEquals(n, r.asked.size)
        assertFalse(r.radio.state.value.active)
    }

    @Test fun liveUrlIsNotWrittenIntoASavedQueue() {
        val saved = QueueCodec.encode(QueueState().replace(listOf(QueueItem("radio:1", "R", "", "Radio", liveUrl = "https://x/y")), 0).state)
        assertFalse(saved.contains("https://x/y"))
    }

    // ---- Slice 6: reconnect

    private fun TestScope.reconnectRig(foreground: () -> Boolean = { true }): Rig {
        val port = FakePort(); val storage = MemoryStorage(); val api = RecordingApi()
        val c = PlayerController(port, storage, ScrobbleCoordinator(api, backgroundScope), backgroundScope, clock = { 1L })
        val radio = RadioPlayback(
            c, backgroundScope, StandardTestDispatcher(testScheduler),
            nowFor = { now(null) }, getPlay = { RadioGetResult(true, "") },
            absolute = { if (it.startsWith("http")) it else "https://lib.example$it" },
            pollMs = 5_000, backoffMs = listOf(2_000L, 4_000L), stallMs = 10_000, watchTickMs = 1_000, inForeground = foreground,
        )
        return Rig(radio, c, port, storage, RecordingApi(), mutableListOf(), mutableListOf())
    }

    private fun Rig.drop() { port.isPlaying = false; c.onIsPlaying(false); c.onError(PlaybackFailure.Network(), 0) }
    private fun Rig.retries() = port.log.count { it == "retry" }

    @Test fun droppedStreamRetriesWithBackoffThenSaysUnreachable() = runTest {
        val r = reconnectRig()
        r.radio.play(station); runCurrent()
        r.drop(); runCurrent()
        assertTrue(r.c.state.value.waitingForNetwork)
        advanceTimeBy(2_100); runCurrent()
        assertEquals(1, r.retries()); assertEquals(1, r.radio.state.value.reconnectAttempt)
        r.drop(); advanceTimeBy(4_100); runCurrent()
        assertEquals(2, r.retries())
        r.drop(); advanceTimeBy(1_100); runCurrent()
        assertTrue(r.radio.state.value.unreachable)
        advanceTimeBy(60_000); runCurrent()
        assertEquals(2, r.retries()) // bounded: no loop after the last try
        assertEquals("Station unreachable.", r.c.state.value.status)
    }

    @Test fun soundReturningClearsTheCountAndTheUnreachableState() = runTest {
        val r = reconnectRig()
        r.radio.play(station); runCurrent()
        r.drop(); advanceTimeBy(2_100); runCurrent()
        r.port.isPlaying = true; r.c.onIsPlaying(true); advanceTimeBy(1_100); runCurrent()
        assertEquals(0, r.radio.state.value.reconnectAttempt); assertFalse(r.radio.state.value.unreachable)
        r.drop(); advanceTimeBy(2_100); runCurrent()
        assertEquals(2, r.retries()) // the count started again from the first wait
    }

    @Test fun retryActionRestartsTheTriesAtOnce() = runTest {
        val r = reconnectRig()
        r.radio.play(station); runCurrent()
        r.drop(); advanceTimeBy(2_100); r.drop(); advanceTimeBy(4_100); r.drop(); advanceTimeBy(1_100); runCurrent()
        assertTrue(r.radio.state.value.unreachable)
        r.radio.retry(); runCurrent()
        assertFalse(r.radio.state.value.unreachable)
        assertEquals(3, r.retries())
    }

    @Test fun noRetryWhileTheAppIsInTheBackground() = runTest {
        var shown = false
        val r = reconnectRig { shown }
        r.radio.play(station); runCurrent()
        r.drop(); advanceTimeBy(30_000); runCurrent()
        assertEquals(0, r.retries())
        shown = true; advanceTimeBy(2_100); runCurrent()
        assertEquals(1, r.retries()) // back on screen: the tries begin
    }

    @Test fun aPauseEndsTheWaitSoNothingRetriesAfterwards() = runTest {
        val r = reconnectRig()
        r.radio.play(station); runCurrent()
        r.drop(); runCurrent()
        r.c.pause(); advanceTimeBy(30_000); runCurrent()
        assertEquals(0, r.retries())
        assertFalse(r.c.state.value.waitingForNetwork)
    }

    @Test fun aStreamThatStaysBufferingCountsAsDropped() = runTest {
        val r = reconnectRig()
        r.radio.play(station); runCurrent()
        r.port.isPlaying = false; r.c.onIsPlaying(false); r.c.onBuffering(true)
        advanceTimeBy(9_000); runCurrent(); assertEquals(0, r.retries())
        advanceTimeBy(4_000); runCurrent()
        assertEquals(1, r.retries())
    }

    @Test fun aServerErrorOnAStationReadsAsUnreachableNotAsASkippedSong() = runTest {
        val r = reconnectRig()
        r.radio.play(station); runCurrent()
        r.c.onError(PlaybackFailure.Server("The server answered 502."), 0)
        assertTrue(r.c.state.value.waitingForNetwork)
        assertEquals("Station unreachable.", r.c.state.value.status)
        assertFalse(r.port.log.contains("skipPastFailure"))
    }
}
