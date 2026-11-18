package app.discair.ui.home

import app.discair.ui.common.IndexDatum

/**
 * The pure rules behind Index's Home (docs/plans/INDEX_THEME.md section 9, mockup index/pages/home): the head's count, the catalogue numbers ("01"), which albums
 * the strip shows, the lead's data list, the play counts and the insight's numeral. No Compose here, so each rule has a unit test. The radio words
 * (plates, last heard, "Heard on") are [GalleryHomeRules], shared because they are the same words.
 */
object IndexHomeRules {
    /** The strip under the lead shows this many albums (02 to 05). */
    const val STRIP_SHOWN = 4

    /** The Played section shows this many rows. */
    const val PLAYED_SHOWN = 3

    /** The Artists and Radio sections show this many in their four columns. */
    const val COLUMNS = 4

    /** The genre line shows this many names, drawn at random each time Home opens (as on every theme). */
    const val GENRES_SHOWN = 5

    /** The head's count (the superscript beside "Picks"): the number of albums in the source, or "—" while it is not known. */
    fun count(n: Int?): String = n?.toString() ?: "—"

    /** A catalogue number: "01", "12", "105" (two digits at least). [index] is 0-based. */
    fun number(index: Int): String = "%02d".format(index + 1)

    /**
     * The albums the strip shows: the first [STRIP_SHOWN] places after leaving out the lead's, in list order. A long press makes a strip album the lead, so
     * the strip keeps the remaining albums and each keeps its own catalogue number ([number] of its place in the list).
     */
    fun strip(count: Int, lead: Int): List<Int> = (0 until count).filter { it != lead }.take(STRIP_SHOWN)

    /** The lead's place after the list changed (an album was dismissed): inside the list, 0 when it is empty. */
    fun leadAt(lead: Int, count: Int): Int = if (count <= 0) 0 else lead.coerceIn(0, count - 1)

    /** The lead's data list. A line whose data is unknown is left out, never filled in; Owned is always said, and "No" is the accent word. */
    fun dataRows(artist: String, year: Int?, genre: String?, owned: Boolean): List<IndexDatum> = buildList {
        if (artist.isNotBlank()) add(IndexDatum("Artist", artist))
        if (year != null) add(IndexDatum("Year", year.toString()))
        if (!genre.isNullOrBlank()) add(IndexDatum("Genre", genre))
        add(if (owned) IndexDatum("Owned", "Yes") else IndexDatum("Owned", "No", accent = true))
    }

    /** "14 plays" for a row in Played; null when the server could not read the listens (the count is then hidden, not shown as 0). */
    fun plays(n: Int?): String? = n?.let { "$it " + if (it == 1) "play" else "plays" }

    /** The meta line of a Played row: "Talk Talk · 1991". */
    fun meta(artist: String, year: Int?): String = listOfNotNull(artist.ifBlank { null }, year?.toString()).joinToString(" · ")

    /** The first number in an insight's title that is not a year ("Blue Lines turns 35" gives "35"); null when it has none, and the block then has no numeral. */
    fun insightNumeral(title: String): String? =
        Regex("""(?<![\d.,])\d{1,3}(?![\d.,])""").find(title)?.value

    /** The tracker's lit segments for an arrival's [stage] (0 found, 1 downloading, 2 importing, 4 in library): the step it is on counts, so a download shows two of four. */
    fun trackerReached(stage: Int): Int = if (stage >= 4) 4 else (stage + 1).coerceIn(1, 3)

    /** What Played says when nothing has been played yet (frame 4). */
    const val NOTHING_PLAYED = "Play a few albums. What you play most is indexed here."

    /** What the lead says when the source has no albums. */
    fun empty(tab: FlowHomeRules.Tab): String = FlowHomeRules.empty(tab)

    /** The library line (mono, the only stats on Home): the parts that are known. */
    fun libraryLine(albums: Int?, artists: Int?, newThisMonth: Int?): String {
        val parts = ArrayList<String>()
        if (albums != null) parts += DashboardRules.formatCount(albums) + (if (albums == 1) " album" else " albums")
        if (artists != null) parts += DashboardRules.formatCount(artists) + (if (artists == 1) " artist" else " artists")
        if (newThisMonth != null) parts += "$newThisMonth new this month"
        return if (parts.isEmpty()) "Library stats" else parts.joinToString(" · ")
    }
}
