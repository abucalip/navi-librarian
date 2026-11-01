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
    fun playArtist(artistId: String, shuffle: Boolean) = launch {
        _messages.tryEmit("Loading songs…")
        val all = mutableListOf<QueueItem>()
        for (albumId in withContext(io) { source.artistAlbumIds(artistId) }) {
            if (all.size >= MAX_QUEUE) break
            all += album(albumId)
        }
        if (all.isEmpty()) { _messages.tryEmit("No songs found for that artist in your library."); return@launch }
        controller.playItems(all, if (shuffle) random.nextInt(minOf(all.size, MAX_QUEUE)) else 0)
        controller.setShuffle(shuffle)
        if (all.size > MAX_QUEUE) _messages.tryEmit("Queue is full at $MAX_QUEUE songs.")
    }

    /** One song from search, already known: no request is needed. */
    fun playSong(item: QueueItem) { if (isValidSongId(item.songId)) { controller.playItems(listOf(item)); controller.setShuffle(false) } }

    fun queueSong(item: QueueItem, next: Boolean) {
        if (!isValidSongId(item.songId)) return
        if (next) controller.playNext(listOf(item)) else controller.enqueue(listOf(item))
        _messages.tryEmit(if (next) "\"${item.title}\" will play next." else "Added \"${item.title}\" to the queue.")
    }
}
