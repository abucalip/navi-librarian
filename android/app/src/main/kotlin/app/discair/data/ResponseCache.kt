package app.discair.data

import java.io.File
import java.security.MessageDigest

/** A saved answer and when it was saved (epoch milliseconds). */
data class Cached(val body: String, val savedAtMillis: Long)

/**
 * Last good answer of each read-only Librarian route, kept so the app can show something when the
 * phone has no connection (Phase 5). Never used for launches, feedback, search or acquisition status:
 * those must reflect the server now.
 */
interface ResponseCache {
    fun get(key: String): Cached?
    fun put(key: String, body: String)
    fun hasContent(): Boolean
    fun clear()
}

/**
 * One file per key under [dir], named by the key's hash; the first line is the save time. The total
 * is kept under [maxBytes] by deleting the oldest files, so the cache cannot grow without bound.
 *
 * The folder is listed once, on the first write; after that the sizes and their order are kept in memory. A write used to
 * list and sort the whole folder (a date read per comparison) while every read waited on the same lock: with thousands of
 * small picture lookups saved, each request on the phone paid that scan, and pages and pictures queued behind it.
 * Reads take no lock: a file is replaced by a rename, so a read sees the old answer or the new one, never half of one.
 */
class FileResponseCache(
    private val dir: File,
    private val maxBytes: Long = 20L * 1024 * 1024,
    private val now: () -> Long = System::currentTimeMillis,
) : ResponseCache {
    private fun file(key: String) = File(dir, MessageDigest.getInstance("SHA-256").digest(key.toByteArray()).joinToString("") { "%02x".format(it) })

    /** File name to size, oldest write first; null until the first write lists the folder. */
    private var index: LinkedHashMap<String, Long>? = null
    private var total = 0L

    private fun index(): LinkedHashMap<String, Long> = index ?: LinkedHashMap<String, Long>().also { map ->
        val files = dir.listFiles().orEmpty().filter { it.isFile }
        files.filter { it.name.endsWith(".tmp") }.forEach { it.delete() } // a write cut short
        files.filterNot { it.name.endsWith(".tmp") }
            .map { Triple(it.name, it.lastModified(), it.length()) }
            .sortedBy { it.second }
            .forEach { (name, _, size) -> map[name] = size; total += size }
        index = map
    }

    override fun get(key: String): Cached? = try {
        val f = file(key)
        if (!f.isFile) null else {
            val text = f.readText()
            val split = text.indexOf('\n')
            val saved = text.substring(0, split).toLong()
            Cached(text.substring(split + 1), saved)
        }
    } catch (e: Exception) {
        null // a damaged entry is the same as no entry
    }

    @Synchronized
    override fun put(key: String, body: String) {
        try {
            dir.mkdirs()
            val f = file(key)
            val tmp = File(dir, f.name + ".tmp")
            val map = index()
            tmp.writeText("${now()}\n$body")
            if (!tmp.renameTo(f)) { f.delete(); tmp.renameTo(f) }
            map.remove(f.name)?.let { total -= it }
            val size = f.length()
            map[f.name] = size // now the newest
            total += size
            trim(map)
        } catch (e: Exception) {
            // Caching is a convenience; a full disk must not break a read that succeeded.
        }
    }

    @Synchronized
    override fun hasContent() = index?.isNotEmpty() ?: (dir.listFiles()?.any { it.isFile && !it.name.endsWith(".tmp") } == true)

    @Synchronized
    override fun clear() {
        dir.listFiles()?.forEach { it.delete() }
        index = LinkedHashMap()
        total = 0
    }

    /** Deletes the oldest files until the total fits, from the in-memory order; the folder is not listed again. */
    private fun trim(map: LinkedHashMap<String, Long>) {
        val names = map.keys.iterator()
        while (total > maxBytes && map.size > 1 && names.hasNext()) {
            val oldest = names.next()
            total -= map[oldest] ?: 0
            names.remove()
            File(dir, oldest).delete()
        }
    }
}

/** Does nothing; used where no cache is wanted (tests, and a signed-out app). */
object NoCache : ResponseCache {
    override fun get(key: String): Cached? = null
    override fun put(key: String, body: String) = Unit
    override fun hasContent() = false
    override fun clear() = Unit
}
