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
 */
class FileResponseCache(
    private val dir: File,
    private val maxBytes: Long = 20L * 1024 * 1024,
    private val now: () -> Long = System::currentTimeMillis,
) : ResponseCache {
    private fun file(key: String) = File(dir, MessageDigest.getInstance("SHA-256").digest(key.toByteArray()).joinToString("") { "%02x".format(it) })

    @Synchronized
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
            tmp.writeText("${now()}\n$body")
            if (!tmp.renameTo(f)) { f.delete(); tmp.renameTo(f) }
            trim()
        } catch (e: Exception) {
            // Caching is a convenience; a full disk must not break a read that succeeded.
        }
    }

    @Synchronized
    override fun hasContent() = dir.listFiles()?.any { it.isFile && !it.name.endsWith(".tmp") } == true

    @Synchronized
    override fun clear() {
        dir.listFiles()?.forEach { it.delete() }
    }

    private fun trim() {
        val files = dir.listFiles()?.filter { it.isFile }?.sortedBy { it.lastModified() }.orEmpty().toMutableList()
        var total = files.sumOf { it.length() }
        while (total > maxBytes && files.size > 1) {
            val oldest = files.removeAt(0)
            total -= oldest.length()
            oldest.delete()
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
