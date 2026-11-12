package app.discair.player

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.launch

/** Most songs sent to Navidrome in one save: the current song and the ones after it. Keeps the request URL short. */
const val REMOTE_QUEUE_MAX = 100

/** The play queue as Navidrome's `savePlayQueue` takes it: song ids from the current one on, that song, and the position in ms. */
data class RemotePlayQueue(val songIds: List<String>, val currentId: String, val positionMs: Long)

/** Saves one queue. Returns true when Navidrome accepted it. Must never throw. */
fun interface RemotePlayQueueApi {
    suspend fun save(queue: RemotePlayQueue): Boolean
}

/**
 * Builds the queue to save from the player state. Null when there is nothing to save: an empty queue, a radio
 * station as the current item (its address is never sent), or a current id that is not a song id.
 * Radio items end the list, so a station is never sent in the middle of it.
 */
fun remotePlayQueueOf(queue: QueueState, positionMs: Long): RemotePlayQueue? {
    val current = queue.current ?: return null
    if (current.isRadio || !isValidSongId(current.songId)) return null
    val ids = queue.items.drop(queue.index)
        .takeWhile { !it.isRadio }
        .map { it.songId }
        .filter { isValidSongId(it) }
        .take(REMOTE_QUEUE_MAX)
    return RemotePlayQueue(songIds = ids, currentId = current.songId, positionMs = positionMs.coerceAtLeast(0))
}

/**
 * Sends saved queues in order without blocking playback. Only the newest pending queue is kept: if a save is
 * still running when a newer one arrives, the older one is dropped, so Navidrome never ends with stale data.
 */
class PlayQueueSync(private val api: RemotePlayQueueApi, scope: CoroutineScope) {
    private val latest = Channel<RemotePlayQueue>(Channel.CONFLATED)

    init {
        scope.launch {
            for (queue in latest) {
                try { api.save(queue) } catch (e: Exception) { /* best effort: the next change saves again */ }
            }
        }
    }

    fun offer(queue: RemotePlayQueue) { latest.trySend(queue) }
}
