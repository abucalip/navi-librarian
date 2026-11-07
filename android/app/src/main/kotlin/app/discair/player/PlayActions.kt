package app.discair.player

import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private fun norm(text: String) = text.lowercase().filter { it.isLetterOrDigit() }

/**
 * Finds a page track among the album's songs: the same title first, then the same track number.
 * Numbers count within a disc, so when the page knows the [disc] a title shared by two discs
 * ("Intro") and a number are read on that disc only.
 */
fun matchSong(songs: List<SongRef>, title: String, number: Int?, disc: Int? = null): SongRef? {
    fun onDisc(song: SongRef) = disc == null || (song.disc ?: 1) == disc
    val titled = if (norm(title).isEmpty()) emptyList() else songs.filter { norm(it.title) == norm(title) }
    return titled.firstOrNull { onDisc(it) && (number == null || it.track == number) }
        ?: titled.firstOrNull { onDisc(it) }
        ?: titled.firstOrNull()
        ?: number?.let { n -> songs.firstOrNull { it.track == n && onDisc(it) } }
}

/**
 * What the Play, Shuffle, Play next and Add to queue buttons do. Only songs that Navidrome lists for the
 * owner's own albums can be played; recommendation and Get cards never reach here. Failures become a
 * message in words and playback is left as it was.
 */
class PlayActions(
    private val source: SongSource,
    private val controller: PlayerController,
    private val scope: CoroutineScope,
    private val io: CoroutineDispatcher,
    /** Absolute address of an owned album's cover on Librarian. */
    private val coverUrl: (albumId: String) -> String,
    private val random: kotlin.random.Random = kotlin.random.Random,
    /** Where "Download to device" saves songs; null in tests that don't need it. */
    private val offline: OfflineSongs? = null,
    /** Asks the server for songs that sound like one song (`/api/sonic/similar`); null when the app has no Librarian. */
    private val sonic: ((songId: String, count: Int) -> app.discair.model.SonicResponse)? = null,
    /** Asks the server for the sonic path between two songs (`/api/sonic/path`); null when the app has no Librarian. */
    private val sonicPath: ((startId: String, endId: String, count: Int) -> app.discair.model.SonicResponse)? = null,
) {
    private val _messages = MutableSharedFlow<String>(extraBufferCapacity = 4, onBufferOverflow = BufferOverflow.DROP_OLDEST)
    val messages: SharedFlow<String> = _messages.asSharedFlow()
    private var job: Job? = null

    private fun item(s: SongRef) = QueueItem(
        songId = s.id, title = s.title, artist = s.artist, album = s.album, albumId = s.albumId,
        coverId = s.albumId, coverUrl = coverUrl(s.albumId), durationSec = s.durationSec,
        year = s.year, bitRateKbps = s.bitRateKbps, suffix = s.suffix, bitDepth = s.bitDepth, samplingRateHz = s.samplingRateHz,
    )

    private fun launch(block: suspend () -> Unit) {
        if (job?.isActive == true) { _messages.tryEmit("Still loading songs."); return }
        job = scope.launch {
            try { block() } catch (e: SongSourceException) { _messages.tryEmit(e.message.orEmpty()) }
            catch (e: kotlinx.coroutines.CancellationException) { throw e }
            catch (e: Exception) { _messages.tryEmit("Couldn't load the songs.") }
        }
    }

    private suspend fun album(albumId: String): List<QueueItem> =
        withContext(io) { source.albumSongs(albumId) }.map(::item)

    /** Play album, or play from a track (by title or number) with the rest of the album after it. */
    fun playAlbum(albumId: String, startTitle: String? = null, startNumber: Int? = null, shuffle: Boolean = false, startDisc: Int? = null) = launch {
        val songs = withContext(io) { source.albumSongs(albumId) }
        if (songs.isEmpty()) { _messages.tryEmit("No songs found for that album in your library."); return@launch }
        var start = 0
        if (startTitle != null) {
            val match = matchSong(songs, startTitle, startNumber, startDisc)
            if (match == null) { _messages.tryEmit("Couldn't find \"$startTitle\" in your library."); return@launch }
            start = songs.indexOf(match)
        } else if (shuffle) start = random.nextInt(songs.size)
        controller.playItems(songs.map(::item), start)
        controller.setShuffle(shuffle)
    }

    fun queueAlbum(albumId: String, next: Boolean) = launch {
        val items = album(albumId)
        if (items.isEmpty()) { _messages.tryEmit("No songs found for that album in your library."); return@launch }
        if (next) controller.playNext(items) else controller.enqueue(items)
        _messages.tryEmit(if (next) "${items.size} songs will play next." else "Added ${items.size} songs to the queue.")
    }

    /** Every owned album of the artist, up to the queue cap, in Navidrome's order. */
    private suspend fun artistItems(artistId: String): List<QueueItem> {
        val all = mutableListOf<QueueItem>()
        for (albumId in withContext(io) { source.artistAlbumIds(artistId) }) {
            if (all.size >= MAX_QUEUE) break
            all += album(albumId)
        }
        return all
    }

    /** One track of an album, added after the current song or at the end. */
    fun queueTrack(albumId: String, title: String, number: Int?, next: Boolean, disc: Int? = null) = launch {
        val songs = withContext(io) { source.albumSongs(albumId) }
        val match = matchSong(songs, title, number, disc)
        if (match == null) { _messages.tryEmit("Couldn't find \"$title\" in your library."); return@launch }
        queueSong(item(match), next)
    }

    /** Saves one track of an album on the device so it plays without a connection. */
    fun downloadTrack(albumId: String, title: String, number: Int?, disc: Int? = null) {
        val store = offline ?: return
        // Its own coroutine: a long download must not block Play, Add to queue and the like.
        scope.launch {
            try {
                val songs = withContext(io) { source.albumSongs(albumId) }
                val match = matchSong(songs, title, number, disc)
                if (match == null) { _messages.tryEmit("Couldn't find \"$title\" in your library."); return@launch }
                if (store.isSaved(match.id)) { _messages.tryEmit("\"${match.title}\" is already on this device."); return@launch }
                _messages.tryEmit("Saving \"${match.title}\" to this device…")
                store.download(match)
                _messages.tryEmit("\"${match.title}\" is on this device. It plays without a connection.")
            } catch (e: SongSourceException) { _messages.tryEmit(e.message.orEmpty()) }
            catch (e: OfflineException) { _messages.tryEmit(e.message.orEmpty()) }
            catch (e: kotlinx.coroutines.CancellationException) { throw e }
            catch (e: Exception) { _messages.tryEmit("Couldn't save the song.") }
        }
    }

    /**
     * Adds songs that sound like [seedId] after what is queued, in the server's order (the score is not used).
     * Songs already queued and the seed itself are skipped; a song the server has no analysis for says so.
     */
    fun soundsLike(seedId: String, queuedIds: Set<String>) {
        val ask = sonic ?: return
        if (job?.isActive == true) { _messages.tryEmit("Still loading songs."); return }
        job = scope.launch {
            try {
                val response = withContext(io) { ask(seedId, SONIC_BATCH) }
                val exclude = queuedIds + seedId
                val seen = mutableSetOf<String>()
                val items = response.tracks.filter { it.songId !in exclude && seen.add(it.songId) }.map {
                    QueueItem(
                        songId = it.songId, title = it.title, artist = it.artist, album = it.album, albumId = it.albumId,
                        coverId = it.albumId, coverUrl = if (it.albumId.isBlank()) "" else coverUrl(it.albumId),
                        durationSec = it.durationSec, year = it.year,
                    )
                }
                if (items.isEmpty()) {
                    _messages.tryEmit(if (response.status == "empty") "No sound matches for this song yet." else "Nothing new sounds like this song.")
                    return@launch
                }
                controller.enqueue(items)
                _messages.tryEmit("Added ${items.size} songs that sound like this one.")
            } catch (e: kotlinx.coroutines.CancellationException) { throw e }
            catch (e: Exception) { _messages.tryEmit(app.discair.model.sonicFailure(e).message) }
        }
    }

    /** A sonic path as queue items, start song first; [SonicResponse.status] `empty` means no analysis data. Throws on failure. */
    suspend fun sonicPathItems(startId: String, endId: String): List<QueueItem> {
        val ask = sonicPath ?: return emptyList()
        return withContext(io) { ask(startId, endId, PATH_STEPS) }.tracks.map {
            QueueItem(
                songId = it.songId, title = it.title, artist = it.artist, album = it.album, albumId = it.albumId,
                coverId = it.albumId, coverUrl = if (it.albumId.isBlank()) "" else coverUrl(it.albumId),
                durationSec = it.durationSec, year = it.year,
            )
        }
    }

    /** Adds the path's steps (not the start song, which is already playing) after the queue, or plays the whole path now. */
    fun useSonicPath(steps: List<QueueItem>, playNow: Boolean) {
        scope.launch {
            if (playNow) controller.playItems(steps) else controller.enqueue(steps.drop(1))
            _messages.tryEmit(if (playNow) "Playing a sonic path of ${steps.size} songs." else "Added ${steps.size - 1} songs along the sonic path.")
        }
    }

    fun queueArtist(artistId: String, next: Boolean) = launch {
        _messages.tryEmit("Loading songs…")
        val items = artistItems(artistId)
        if (items.isEmpty()) { _messages.tryEmit("No songs found for that artist in your library."); return@launch }
        if (next) controller.playNext(items) else controller.enqueue(items)
        _messages.tryEmit(if (next) "${items.size} songs will play next." else "Added ${items.size} songs to the queue.")
    }

    fun playArtist(artistId: String, shuffle: Boolean) = launch {
        _messages.tryEmit("Loading songs…")
        val all = artistItems(artistId)
        if (all.isEmpty()) { _messages.tryEmit("No songs found for that artist in your library."); return@launch }
        controller.playItems(all, if (shuffle) random.nextInt(minOf(all.size, MAX_QUEUE)) else 0)
        controller.setShuffle(shuffle)
        if (all.size > MAX_QUEUE) _messages.tryEmit("Queue is full at $MAX_QUEUE songs.")
    }

    /** One song from search: the result already carries its year and file details, so no request is needed. */
    fun playSong(item: QueueItem) {
        if (!isValidSongId(item.songId)) return
        scope.launch { controller.playItems(listOf(item)); controller.setShuffle(false) }
    }

    fun queueSong(item: QueueItem, next: Boolean) {
        if (!isValidSongId(item.songId)) return
        scope.launch {
            if (next) controller.playNext(listOf(item)) else controller.enqueue(listOf(item))
            _messages.tryEmit(if (next) "\"${item.title}\" will play next." else "Added \"${item.title}\" to the queue.")
        }
    }

    private companion object {
        /** Songs asked of the server for one Sounds-like batch (the server already caps the seed's own artist at 2). */
        const val SONIC_BATCH = 20
        /** Steps asked for one path, start and end included. */
        const val PATH_STEPS = 10
    }
}
