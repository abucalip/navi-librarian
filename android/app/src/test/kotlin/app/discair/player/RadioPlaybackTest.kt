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
        assertTrue(item.coverUrl.endsWith("/logo?size=512"))
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
}
