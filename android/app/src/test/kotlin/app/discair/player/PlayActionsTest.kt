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
import org.junit.Assert.assertNull
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

    @Test fun aSearchSongPlaysWithTheDetailsItCameWith() = runTest {
        val source = FakeSource()
        val r = rig(source)
        val item = QueueItem("s1", "Song", "Ar", "Al", "al1", "al1", durationSec = 100, year = 1999, bitRateKbps = 320, suffix = "mp3")
        r.actions.playSong(item); advanceUntilIdle()
        val played = r.controller.state.value.queue.items.single()
        assertEquals(1999, played.year); assertEquals("320Kbps", qualityLabel(played))
        assertTrue(source.requests.isEmpty()) // no request to Navidrome for one search song
        r.actions.queueSong(item.copy(songId = "s2", title = "Two"), next = false); advanceUntilIdle()
        assertEquals(2, r.controller.state.value.queue.items.size)
        assertEquals("Added \"Two\" to the queue.", r.messages.last())
    }

    @Test fun badSongIdsAreIgnored() = runTest {
        val r = rig(FakeSource())
        r.actions.playSong(QueueItem("bad/id", "x", "y", "z")); r.actions.queueSong(QueueItem("", "x", "y", "z"), next = true)
        assertFalse(r.controller.state.value.visible)
    }

    @Test fun aSingleTrackCanBeQueuedNextOrAtTheEnd() = runTest {
        val r = rig(FakeSource(mapOf("al1" to album1)))
        r.actions.playSong(QueueItem("x1", "Other", "Ar", "Al", "al9")); advanceUntilIdle()
        r.actions.queueTrack("al1", "Two", 2, next = true); advanceUntilIdle()
        r.actions.queueTrack("al1", "Three", 3, next = false); advanceUntilIdle()
        assertEquals(listOf("x1", "a2", "a3"), r.controller.state.value.queue.items.map { it.songId })
        assertEquals("Added \"Three\" to the queue.", r.messages.last())
    }

    @Test fun aMissingTrackIsReportedWhenQueueing() = runTest {
        val r = rig(FakeSource(mapOf("al1" to album1)))
        r.actions.queueTrack("al1", "Nope", 9, next = false); advanceUntilIdle()
        assertFalse(r.controller.state.value.visible)
        assertEquals("Couldn't find \"Nope\" in your library.", r.messages.last())
    }

    @Test fun anArtistCanBeQueuedNextOrAtTheEnd() = runTest {
        val r = rig(FakeSource(mapOf("al1" to album1, "al2" to album2), mapOf("ar1" to listOf("al1", "al2"))))
        r.actions.playAlbum("al1"); advanceUntilIdle()
        r.actions.queueArtist("ar1", next = true); advanceUntilIdle()
        assertEquals(listOf("a1", "a1", "a2", "a3", "b1", "b2", "a2", "a3"), r.controller.state.value.queue.items.map { it.songId })
        r.actions.queueArtist("ar1", next = false); advanceUntilIdle()
        assertEquals(13, r.controller.state.value.queue.items.size)
        assertTrue(r.messages.contains("Added 5 songs to the queue."))
    }

    private fun sonicRig(scope: TestScope, answer: (String, Int) -> app.discair.model.SonicResponse): Rig {
        val port = FakePort()
        val controller = PlayerController(port, MemoryStorage(), ScrobbleCoordinator(RecordingApi(), scope.backgroundScope), scope.backgroundScope)
        val actions = PlayActions(FakeSource(emptyMap()), controller, scope, StandardTestDispatcher(scope.testScheduler),
            { "https://lib/api/owned/artwork/$it" }, sonic = answer)
        val messages = mutableListOf<String>()
        scope.backgroundScope.launch(UnconfinedTestDispatcher(scope.testScheduler)) { actions.messages.collect { messages += it } }
        return Rig(actions, controller, port, FakeSource(emptyMap()), messages)
    }

    private fun sonicTracks(vararg ids: String) =
        app.discair.model.SonicResponse("ok", ids.map { app.discair.model.SonicTrack(it, "T$it", "Art", "Alb", "alb$it", 200, 2001, 0.9) })

    @Test fun soundsLikeQueuesMatchesInServerOrderSkippingTheSeedAndQueuedSongs() = runTest {
        val r = sonicRig(this) { id, count -> assertEquals("seed", id); assertEquals(20, count); sonicTracks("n2", "seed", "q1", "n1", "n2") }
        r.actions.soundsLike("seed", setOf("q1")); advanceUntilIdle()
        assertEquals(listOf("n2", "n1"), r.controller.state.value.queue.items.map { it.songId })
        assertEquals("https://lib/api/owned/artwork/albn2", r.controller.state.value.queue.items[0].coverUrl)
        assertEquals(listOf("Added 2 songs that sound like this one."), r.messages)
    }

    @Test fun soundsLikeSaysSoWhenTheSongHasNoAnalysisData() = runTest {
        val r = sonicRig(this) { _, _ -> app.discair.model.SonicResponse("empty", emptyList()) }
        r.actions.soundsLike("seed", emptySet()); advanceUntilIdle()
        assertTrue(r.controller.state.value.queue.isEmpty)
        assertEquals(listOf("No sound matches for this song yet."), r.messages)
    }

    @Test fun soundsLikeReportsAServerFailureInWordsAndLeavesTheQueueAlone() = runTest {
        val r = sonicRig(this) { _, _ -> throw app.discair.net.ConnectionException(app.discair.net.ConnectionFailure.Server(502, "x")) }
        r.actions.soundsLike("seed", emptySet()); advanceUntilIdle()
        assertTrue(r.controller.state.value.queue.isEmpty)
        assertEquals(listOf("Sound matching isn't available right now. Try again later."), r.messages)
    }
}
