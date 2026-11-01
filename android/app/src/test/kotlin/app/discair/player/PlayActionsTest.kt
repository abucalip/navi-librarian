package app.discair.player

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

private class FakeSource(val albums: Map<String, List<SongRef>> = emptyMap(), val artists: Map<String, List<String>> = emptyMap()) : SongSource {
    val requests = mutableListOf<String>()
    var failure: SongSourceException? = null
    override fun albumSongs(albumId: String): List<SongRef> {
        requests += "album:$albumId"; failure?.let { throw it }; return albums[albumId] ?: emptyList()
    }
    override fun artistAlbumIds(artistId: String): List<String> {
        requests += "artist:$artistId"; failure?.let { throw it }; return artists[artistId] ?: emptyList()
    }
}

@OptIn(ExperimentalCoroutinesApi::class)
class PlayActionsTest {
    private fun ref(id: String, title: String, track: Int, album: String = "al1") = SongRef(id, title, "Ar", "Al", album, track, null, 200)
    private val album1 = listOf(ref("a1", "One", 1), ref("a2", "Two", 2), ref("a3", "Three", 3))
    private val album2 = listOf(ref("b1", "Four", 1, "al2"), ref("b2", "Five", 2, "al2"))

    private class Rig(val actions: PlayActions, val controller: PlayerController, val port: FakePort, val source: FakeSource, val messages: MutableList<String>)

    private fun TestScope.rig(source: FakeSource): Rig {
        val port = FakePort()
        val scrobbler = ScrobbleCoordinator(RecordingApi(), backgroundScope)
        val controller = PlayerController(port, MemoryStorage(), scrobbler, backgroundScope)
        val actions = PlayActions(source, controller, this, StandardTestDispatcher(testScheduler), { "https://lib/api/owned/artwork/$it" })
        val messages = mutableListOf<String>()
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { actions.messages.collect { messages += it } }
        return Rig(actions, controller, port, source, messages)
    }

    @Test fun playAlbumQueuesTheWholeAlbumFromTheStart() = runTest {
        val r = rig(FakeSource(mapOf("al1" to album1)))
        r.actions.playAlbum("al1"); advanceUntilIdle()
        val q = r.controller.state.value.queue
        assertEquals(listOf("a1", "a2", "a3"), q.items.map { it.songId }); assertEquals(0, q.index)
        assertEquals("https://lib/api/owned/artwork/al1", q.items[0].coverUrl)
        assertTrue(r.port.log.contains("shuffle false"))
    }

    @Test fun playFromATrackStartsThereWithTheRestAfterIt() = runTest {
        val r = rig(FakeSource(mapOf("al1" to album1)))
        r.actions.playAlbum("al1", startTitle = "Two", startNumber = 2); advanceUntilIdle()
        assertEquals(1, r.controller.state.value.queue.index); assertEquals(3, r.controller.state.value.queue.items.size)
    }

    @Test fun aTrackNotInTheLibraryIsReportedAndNothingChanges() = runTest {
        val r = rig(FakeSource(mapOf("al1" to album1)))
        r.actions.playAlbum("al1", startTitle = "Missing", startNumber = 9); advanceUntilIdle()
        assertFalse(r.controller.state.value.visible)
        assertEquals(listOf("Couldn't find \"Missing\" in your library."), r.messages)
    }

    @Test fun shufflePlayTurnsShuffleOn() = runTest {
        val r = rig(FakeSource(mapOf("al1" to album1)))
        r.actions.playAlbum("al1", shuffle = true); advanceUntilIdle()
        assertTrue(r.port.log.contains("shuffle true")); assertTrue(r.controller.state.value.queue.shuffle)
    }

    @Test fun playNextAndAddToQueueUseTheAlbumAndSayWhatHappened() = runTest {
        val r = rig(FakeSource(mapOf("al1" to album1, "al2" to album2)))
        r.actions.playAlbum("al1"); advanceUntilIdle()
        r.actions.queueAlbum("al2", next = true); advanceUntilIdle()
        assertEquals(listOf("a1", "b1", "b2", "a2", "a3"), r.controller.state.value.queue.items.map { it.songId })
        r.actions.queueAlbum("al2", next = false); advanceUntilIdle()
        assertEquals(7, r.controller.state.value.queue.items.size)
        assertEquals(listOf("2 songs will play next.", "Added 2 songs to the queue."), r.messages)
    }

    @Test fun playArtistGathersEveryAlbumInOrder() = runTest {
        val r = rig(FakeSource(mapOf("al1" to album1, "al2" to album2), mapOf("ar1" to listOf("al1", "al2"))))
        r.actions.playArtist("ar1", shuffle = false); advanceUntilIdle()
        assertEquals(5, r.controller.state.value.queue.items.size); assertEquals(0, r.controller.state.value.queue.index)
        assertEquals("Loading songs…", r.messages.first())
    }

    @Test fun anArtistWithNoSongsSaysSo() = runTest {
        val r = rig(FakeSource())
        r.actions.playArtist("ar1", shuffle = true); advanceUntilIdle()
        assertFalse(r.controller.state.value.visible)
        assertTrue(r.messages.last().contains("No songs found"))
    }

    @Test fun failuresAreSpokenAndLeavePlaybackAlone() = runTest {
        val source = FakeSource(mapOf("al1" to album1))
        val r = rig(source)
        r.actions.playAlbum("al1"); advanceUntilIdle()
        source.failure = SongSourceException(SongSourceProblem.Unreachable, "Can't reach Navidrome. Is Tailscale connected?")
        r.actions.playAlbum("al2"); advanceUntilIdle()
        assertEquals("Can't reach Navidrome. Is Tailscale connected?", r.messages.last())
        assertEquals(3, r.controller.state.value.queue.items.size) // the earlier queue is untouched
    }

    @Test fun aSecondTapWhileLoadingIsIgnored() = runTest {
        val source = FakeSource(mapOf("al1" to album1))
        val r = rig(source)
        r.actions.playAlbum("al1"); r.actions.playAlbum("al1"); advanceUntilIdle()
        assertEquals(1, source.requests.size)
        assertEquals("Still loading songs.", r.messages.single())
    }

    @Test fun aSearchSongPlaysAtOnceWithNoRequest() = runTest {
        val source = FakeSource()
        val r = rig(source)
        val item = QueueItem("s1", "Song", "Ar", "Al", "al1", "al1", durationSec = 100)
        r.actions.playSong(item)
        assertEquals(listOf("s1"), r.controller.state.value.queue.items.map { it.songId }); assertTrue(source.requests.isEmpty())
        r.actions.queueSong(item.copy(songId = "s2", title = "Two"), next = false)
        assertEquals(2, r.controller.state.value.queue.items.size)
        assertEquals("Added \"Two\" to the queue.", r.messages.last())
    }

    @Test fun badSongIdsAreIgnored() = runTest {
        val r = rig(FakeSource())
        r.actions.playSong(QueueItem("bad/id", "x", "y", "z")); r.actions.queueSong(QueueItem("", "x", "y", "z"), next = true)
        assertFalse(r.controller.state.value.visible)
    }
}
