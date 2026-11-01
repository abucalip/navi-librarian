package app.discair.lyrics

import java.io.File
import java.security.MessageDigest
import kotlinx.serialization.Serializable
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

/** A saved answer. [lyrics] is null for a cached "none". */
class CachedLyrics(val lyrics: Lyrics?, val savedAtMillis: Long, private val now: Long) {
    /** A found entry is refreshed in the background at most once a day (contract 8). */
    val needsRefresh: Boolean get() = now - savedAtMillis >= DAY_MS
    override fun toString() = "CachedLyrics(found=${lyrics != null})"
}

const val DAY_MS = 24L * 60 * 60 * 1000

/**
 * One small file per song under [dir] (contract 8). The file name is a hash of the server address, the user
 * and the song id, so a different server or user never finds it. At most [maxEntries] files or [maxBytes]
 * bytes: the oldest are removed first. "None" answers are kept 24 hours. [scope] is read on every call so a
 * changed login takes effect at once.
 */
class LyricsCache(
    private val dir: File,
    private val scope: () -> String,
    private val maxEntries: Int = 300,
    private val maxBytes: Long = 5L * 1024 * 1024,
    private val now: () -> Long = System::currentTimeMillis,
) {
    @Serializable
    private class Entry(val savedAt: Long, val lyrics: Lyrics?)

    private val json = Json { ignoreUnknownKeys = true }

    private fun file(songId: String) = File(dir, sha256("${scope()}\n$songId"))

    private fun sha256(text: String) = MessageDigest.getInstance("SHA-256").digest(text.toByteArray()).joinToString("") { "%02x".format(it) }

    @Synchronized
    fun get(songId: String): CachedLyrics? {
        val f = file(songId)
        return try {
            if (!f.isFile) return null
            val entry = json.decodeFromString<Entry>(f.readText())
            if (entry.lyrics == null && now() - entry.savedAt >= DAY_MS) { f.delete(); return null }
            CachedLyrics(entry.lyrics, entry.savedAt, now())
        } catch (e: Exception) {
            f.delete() // a damaged entry is the same as no entry
            null
        }
    }

    /** Saves a found answer, or a "none" when [lyrics] is null. */
    @Synchronized
    fun put(songId: String, lyrics: Lyrics?) {
        try {
            dir.mkdirs()
            val f = file(songId)
            val tmp = File(dir, f.name + ".tmp")
            tmp.writeText(json.encodeToString(Entry(now(), lyrics)))
            if (!tmp.renameTo(f)) { f.delete(); tmp.renameTo(f) }
            f.setLastModified(now())
            trim()
        } catch (e: Exception) {
            // Caching is a convenience; a full disk must not break a lookup that succeeded.
        }
    }

    /** Called at sign-out (contract 3.4). */
    @Synchronized
    fun clear() {
        dir.listFiles()?.forEach { it.delete() }
    }

    private fun trim() {
        val files = dir.listFiles()?.filter { it.isFile && !it.name.endsWith(".tmp") }?.sortedBy { it.lastModified() }.orEmpty().toMutableList()
        var total = files.sumOf { it.length() }
        while ((files.size > maxEntries || total > maxBytes) && files.size > 1) {
            val oldest = files.removeAt(0)
            total -= oldest.length()
            oldest.delete()
        }
    }
}
