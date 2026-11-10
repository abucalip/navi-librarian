package app.discair.model

import java.time.LocalDate

/**
 * The liner note of the day (docs/artwork.md, idea 12): one picture of an album on Home, cropped by a fixed centre rule, with the
 * album revealed on tap. Chosen by day and by type only; taste and play data play no part in the picture. Mirrors the macOS rules in
 * `macos/Sources/DiscairLibrarian/LinerNote.swift`.
 */

/** A stable number for a day or a key (FNV-1a, positive). `hashCode` is not used: its value is not promised across releases. */
fun linerNoteSeed(key: String): Long {
    var hash = -3750763034362895579L // 0xcbf29ce484222325
    for (byte in key.toByteArray(Charsets.UTF_8)) {
        hash = hash xor (byte.toLong() and 0xff)
        hash *= 0x100000001b3L
    }
    return hash and Long.MAX_VALUE
}

/** The local calendar day as `yyyy-MM-dd`, the key the note is chosen for. */
fun linerNoteDay(date: LocalDate): String = date.toString()

/**
 * The release groups to try for a day, in order: the valid, unique ids sorted, rotated by the day's number. The order does not depend
 * on the order the list arrived in (the dashboard shuffles its picks). At most a handful of ids, so no bound is needed here.
 */
fun linerNoteOrder(groups: List<String>, day: String): List<String> {
    val ids = groups.mapNotNull { g -> g.trim().takeIf { MBID.matches(it) }?.lowercase() }.distinct().sorted()
    if (ids.isEmpty()) return emptyList()
    val start = (linerNoteSeed(day) % ids.size).toInt()
    return ids.subList(start, ids.size) + ids.subList(0, start)
}

/**
 * The picture for the day's note: a booklet page, a session or band photo (the artist collage rule) or a label (Medium). Never a PDF,
 * never a Front, Back or other cover. Null when the album has none.
 */
fun linerNotePicture(index: ArtworkIndex?, day: String): ArtworkImage? {
    index ?: return null
    val pool = (
        index.bookletImages().filter { !it.isPdf } +
            index.images.filter { it.qualifiesForCollage() } +
            listOfNotNull(index.slotImage("Medium"))
        ).filter { !it.isPdf }.distinctBy { it.imageId }
    if (pool.isEmpty()) return null
    return pool[(linerNoteSeed(day) % pool.size).toInt()]
}

/** What the owner saw for today's note, so it stays the same all day (the Home picks reshuffle on each load). */
data class LinerNoteChoice(val day: String, val rgid: String, val title: String, val artist: String)
