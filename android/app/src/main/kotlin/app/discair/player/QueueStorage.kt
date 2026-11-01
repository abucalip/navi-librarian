package app.discair.player

import java.io.File
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

private const val VERSION = 1

@Serializable
private data class StoredQueue(
    val v: Int = VERSION,
    val items: List<QueueItem> = emptyList(),
    val index: Int = 0,
    val positionMs: Long = 0,
    val shuffle: Boolean = false,
    val repeat: String = "Off",
    val volume: Float = 1f,
)

/** Turns a queue into versioned JSON and back. Bad, old or hostile data yields an empty queue, never a crash. */
object QueueCodec {
    private val json = Json { ignoreUnknownKeys = true; isLenient = false }

    fun encode(state: QueueState): String = json.encodeToString(
        StoredQueue(
            items = state.items, index = state.index, positionMs = state.positionMs,
            shuffle = state.shuffle, repeat = state.repeat.name, volume = state.volume,
        ),
    )

    fun decode(text: String?): QueueState {
        if (text.isNullOrBlank()) return QueueState()
        val stored = try {
            json.decodeFromString<StoredQueue>(text)
        } catch (e: Exception) {
            return QueueState()
        }
        if (stored.v != VERSION) return QueueState()
        val items = stored.items.filter { isValidSongId(it.songId) }.take(MAX_QUEUE)
        val volume = if (stored.volume.isNaN()) 1f else stored.volume.coerceIn(0f, 1f)
        val repeat = RepeatMode.entries.firstOrNull { it.name == stored.repeat } ?: RepeatMode.Off
        val base = QueueState(
            items = items,
            index = if (items.isEmpty()) 0 else stored.index.coerceIn(0, items.size - 1),
            positionMs = stored.positionMs.coerceAtLeast(0),
            shuffle = false,
            repeat = repeat,
            volume = volume,
        )
        // The shuffled order is not stored; rebuild it from the current song.
        return if (stored.shuffle) base.withShuffle(true) else base
    }
}

/** Where the queue lives. The file is private to the app and written atomically. */
interface QueueStorage {
    fun read(): String?
    fun write(text: String)
    fun clear()
}

class FileQueueStorage(private val file: File) : QueueStorage {
    override fun read(): String? = try {
        if (file.isFile) file.readText() else null
    } catch (e: Exception) {
        null
    }

    override fun write(text: String) {
        val temp = File(file.parentFile, file.name + ".tmp")
        temp.writeText(text)
        if (!temp.renameTo(file)) {
            file.delete()
            temp.renameTo(file)
        }
    }

    override fun clear() {
        file.delete()
    }
}
