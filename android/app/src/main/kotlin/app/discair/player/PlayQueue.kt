package app.discair.player

import kotlin.random.Random
import kotlinx.serialization.Serializable

const val MAX_QUEUE = 500

enum class RepeatMode { Off, All, One }

@Serializable
data class QueueItem(
    val songId: String,
    val title: String,
    val artist: String,
    val album: String,
    val albumId: String = "",
    val coverId: String = "",
    /** Absolute address of the cover on Librarian (loaded with the app's session); empty when unknown. */
    val coverUrl: String = "",
    val durationSec: Int = 0,
)

/** Result of an add: the new state and whether the 500-song cap cut the request short. */
data class AddResult(val state: QueueState, val capped: Boolean)

/**
 * The play queue as an immutable value. `items` is the display order. With shuffle on, `shuffleOrder`
 * is a permutation of item indices that starts at the current song; turning shuffle off goes back to
 * the display order. Structural changes (add, remove, move) rebuild the shuffled order from the
 * current song, which forgets which songs were already heard in that shuffle.
 */
data class QueueState(
    val items: List<QueueItem> = emptyList(),
    val index: Int = 0,
    val positionMs: Long = 0,
    val shuffle: Boolean = false,
    val repeat: RepeatMode = RepeatMode.Off,
    val volume: Float = 1f,
    val shuffleOrder: List<Int> = emptyList(),
    val unavailable: Set<String> = emptySet(),
) {
    val current: QueueItem? get() = items.getOrNull(index)
    val isEmpty: Boolean get() = items.isEmpty()

    /** Replaces the queue (play album, play song) and starts at [startIndex]. */
    fun replace(newItems: List<QueueItem>, startIndex: Int = 0, random: Random = Random): AddResult {
        val capped = newItems.size > MAX_QUEUE
        val kept = newItems.take(MAX_QUEUE)
        val start = if (kept.isEmpty()) 0 else startIndex.coerceIn(0, kept.size - 1)
        val next = copy(items = kept, index = start, positionMs = 0, unavailable = emptySet())
        return AddResult(next.reshuffled(random), capped)
    }

    /** "Add to queue": append at the end. */
    fun enqueue(add: List<QueueItem>, random: Random = Random): AddResult {
        val room = MAX_QUEUE - items.size
        val taken = add.take(room.coerceAtLeast(0))
        if (taken.isEmpty()) return AddResult(this, add.isNotEmpty())
        val next = copy(items = items + taken)
        return AddResult(next.reshuffled(random), taken.size < add.size)
    }

    /** "Play next": insert right after the current song. */
    fun playNext(add: List<QueueItem>, random: Random = Random): AddResult {
        val room = MAX_QUEUE - items.size
        val taken = add.take(room.coerceAtLeast(0))
        if (taken.isEmpty()) return AddResult(this, add.isNotEmpty())
        val at = if (items.isEmpty()) 0 else (index + 1).coerceAtMost(items.size)
        val next = copy(items = items.toMutableList().apply { addAll(at, taken) })
        return AddResult(next.reshuffled(random), taken.size < add.size)
    }

    fun remove(position: Int, random: Random = Random): QueueState {
        if (position !in items.indices) return this
        val newItems = items.toMutableList().apply { removeAt(position) }
        val newIndex = when {
            newItems.isEmpty() -> 0
            position < index -> index - 1
            else -> index.coerceAtMost(newItems.size - 1)
        }
        val resetPosition = if (position == index) 0L else positionMs
        return copy(items = newItems, index = newIndex, positionMs = resetPosition).reshuffled(random)
    }

    fun move(from: Int, to: Int, random: Random = Random): QueueState {
        if (from !in items.indices || to !in items.indices || from == to) return this
        val newItems = items.toMutableList().apply { add(to, removeAt(from)) }
        val newIndex = when {
            index == from -> to
            from < index && to >= index -> index - 1
            from > index && to <= index -> index + 1
            else -> index
        }
        return copy(items = newItems, index = newIndex).reshuffled(random)
    }

    fun clear() = QueueState(volume = volume, shuffle = shuffle, repeat = repeat)

    fun withShuffle(on: Boolean, random: Random = Random) = copy(shuffle = on).reshuffled(random)
    fun withRepeat(mode: RepeatMode) = copy(repeat = mode)
    fun withVolume(v: Float) = copy(volume = v.coerceIn(0f, 1f))
    fun withPosition(ms: Long) = copy(positionMs = ms.coerceAtLeast(0))

    /** Marks a song unavailable (it will be skipped). */
    fun markUnavailable(songId: String) = copy(unavailable = unavailable + songId)

    private fun playable(i: Int) = items[i].songId !in unavailable

    private fun order(): List<Int> = if (shuffle && shuffleOrder.size == items.size) shuffleOrder else items.indices.toList()

    /** The index after the current one for the next button, skipping unavailable songs. */
    fun nextIndex(): Int? {
        if (items.isEmpty()) return null
        val order = order()
        val at = order.indexOf(index)
        for (step in 1..order.size) {
            val pos = at + step
            if (pos >= order.size && repeat != RepeatMode.All) return null
            val candidate = order[pos % order.size]
            if (candidate == index && order.size > 1) continue
            if (playable(candidate)) return candidate
        }
        return null
    }

    fun previousIndex(): Int? {
        if (items.isEmpty()) return null
        val order = order()
        val at = order.indexOf(index)
        for (step in 1..order.size) {
            val pos = at - step
            if (pos < 0 && repeat != RepeatMode.All) return null
            val candidate = order[(pos + order.size) % order.size]
            if (playable(candidate)) return candidate
        }
        return null
    }

    /** What plays when the current song ends by itself: the same song for repeat-one. */
    fun afterTrackEnded(): Int? = if (repeat == RepeatMode.One && current?.let { it.songId !in unavailable } == true) index else nextIndex()

    fun skipTo(newIndex: Int): QueueState =
        if (newIndex in items.indices) copy(index = newIndex, positionMs = 0) else this

    private fun reshuffled(random: Random): QueueState {
        if (!shuffle || items.isEmpty()) return copy(shuffleOrder = emptyList())
        val others = items.indices.filter { it != index }.shuffled(random)
        return copy(shuffleOrder = listOf(index) + others)
    }
}
