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
}
