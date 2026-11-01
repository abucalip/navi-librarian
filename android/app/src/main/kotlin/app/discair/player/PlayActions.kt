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
import kotlinx.coroutines.withTimeoutOrNull

private fun norm(text: String) = text.lowercase().filter { it.isLetterOrDigit() }

/** Finds a page track among the album's songs: the same title first, then the same track number. */
fun matchSong(songs: List<SongRef>, title: String, number: Int?): SongRef? =
    songs.firstOrNull { norm(it.title) == norm(title) && norm(title).isNotEmpty() }
        ?: number?.let { n -> songs.firstOrNull { it.track == n } }

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
    fun playAlbum(albumId: String, startTitle: String? = null, startNumber: Int? = null, shuffle: Boolean = false) = launch {
        val songs = withContext(io) { source.albumSongs(albumId) }
        if (songs.isEmpty()) { _messages.tryEmit("No songs found for that album in your library."); return@launch }
        var start = 0
        if (startTitle != null) {
            val match = matchSong(songs, startTitle, startNumber)
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
    fun queueTrack(albumId: String, title: String, number: Int?, next: Boolean) = launch {
        val songs = withContext(io) { source.albumSongs(albumId) }
        val match = matchSong(songs, title, number)
        if (match == null) { _messages.tryEmit("Couldn't find \"$title\" in your library."); return@launch }
        queueSong(item(match), next)
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

    /** One song from search, already known: no request is needed. */
    /**
     * Search results carry no year or file details (Librarian's index drops them), so ask Navidrome for
     * this one song first. Any failure or a slow answer just plays the song as it came.
     */
    private suspend fun detailed(item: QueueItem): QueueItem {
        if (item.suffix.isNotEmpty() && item.year != null) return item
        val found = try {
            withTimeoutOrNull(DETAIL_WAIT_MS) { withContext(io) { source.song(item.songId) } }
        } catch (e: kotlinx.coroutines.CancellationException) { throw e } catch (e: Exception) { null } ?: return item
        return item.copy(
            year = item.year ?: found.year, bitRateKbps = item.bitRateKbps ?: found.bitRateKbps,
            suffix = item.suffix.ifEmpty { found.suffix }, bitDepth = item.bitDepth ?: found.bitDepth,
            samplingRateHz = item.samplingRateHz ?: found.samplingRateHz,
        )
    }

    fun playSong(item: QueueItem) {
        if (!isValidSongId(item.songId)) return
        scope.launch { controller.playItems(listOf(detailed(item))); controller.setShuffle(false) }
    }

    fun queueSong(item: QueueItem, next: Boolean) {
        if (!isValidSongId(item.songId)) return
        scope.launch {
            val full = detailed(item)
            if (next) controller.playNext(listOf(full)) else controller.enqueue(listOf(full))
            _messages.tryEmit(if (next) "\"${item.title}\" will play next." else "Added \"${item.title}\" to the queue.")
        }
    }

    private companion object { const val DETAIL_WAIT_MS = 2_000L }
}
