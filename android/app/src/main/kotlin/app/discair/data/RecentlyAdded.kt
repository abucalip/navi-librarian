package app.discair.data

import app.discair.model.LibraryAlbum
import java.time.Duration
import java.time.Instant
import java.time.format.DateTimeParseException

/** The Recently added albums section covers this many days. */
const val RECENT_DAYS = 30L

/** True when [added] (an ISO-8601 instant from the library index) falls within [days] before [now]. */
fun addedWithin(added: String?, now: Instant, days: Long = RECENT_DAYS): Boolean {
    if (added.isNullOrBlank()) return false
    val at = try { Instant.parse(added) } catch (e: DateTimeParseException) { return false }
    return !at.isBefore(now.minus(Duration.ofDays(days)))
}

/**
 * Albums added to the library in the last [days] days, newest first. Reads the library list sorted by
 * date added, newest first, and stops at the first album that is too old, at the last page, or after
 * [maxPages] pages.
 */
fun LibraryRepository.recentlyAdded(now: Instant = Instant.now(), days: Long = RECENT_DAYS, maxPages: Int = 8): List<LibraryAlbum> {
    val found = mutableListOf<LibraryAlbum>()
    var cursor: String? = null
    repeat(maxPages) {
        val page = albums("", AlbumSort.Added, true, cursor)
        for (album in page.items) {
            if (!addedWithin(album.added, now, days)) return found
            found += album
        }
        cursor = page.nextCursor ?: return found
    }
    return found
}
