package app.discair.data

/** Thrown in cache-only mode when a read has no saved copy; the caller then waits for the server. */
class CacheMiss : RuntimeException("No saved copy.")

/**
 * Lets a screen read from the saved copies alone for an instant first paint, then read again from the
 * server to bring it up to date. The flag belongs to the calling thread, so a read that hops threads
 * must carry it over with [only].
 */
object ReadMode {
    private val cacheOnly = ThreadLocal<Boolean>()

    val isCacheOnly: Boolean get() = cacheOnly.get() == true

    fun <T> only(enabled: Boolean, block: () -> T): T {
        val before = cacheOnly.get()
        cacheOnly.set(enabled)
        try {
            return block()
        } finally {
            if (before == null) cacheOnly.remove() else cacheOnly.set(before)
        }
    }
}
