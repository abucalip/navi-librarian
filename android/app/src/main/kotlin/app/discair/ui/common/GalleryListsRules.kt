package app.discair.ui.common

import java.time.LocalDate
import java.time.format.TextStyle
import java.util.Locale

/**
 * The words on Gallery's Discover, Library and Search pages (docs/GALLERY_THEME.md section 10, mockups gallery/pages/discover and library-search).
 * Pure, so the tests can pin them. The catalogue lines are set in DM Mono capitals by the screens; these return plain text.
 */
object GalleryListsRules {
    const val ENTRY_PRINT_DP = 104
    const val INSIGHT_PRINT_DP = 96
    const val BARS_SHOWN = 4

    /** "Monday 16 November": the catalogue line over Discover's title. */
    fun dateLine(day: LocalDate, locale: Locale = Locale.getDefault()): String =
        day.dayOfWeek.getDisplayName(TextStyle.FULL, locale) + " " + day.dayOfMonth + " " + day.month.getDisplayName(TextStyle.FULL, locale)

    /** "No. 01 · Post-rock": the place in the list, then the genre when the entry has one. */
    fun entryEyebrow(index: Int, genre: String?): String = "No. %02d".format(index + 1) + (genre?.trim()?.takeIf { it.isNotEmpty() }?.let { " · $it" } ?: "")

    /** The genre an entry is filed under: its first tag, else the row label of a deep dive. */
    fun entryGenre(genres: List<String>, rowLabel: String?): String? = genres.firstOrNull { it.isNotBlank() } ?: rowLabel?.takeIf { it.isNotBlank() }

    /** "Your taste · last 90 days", "Your taste · past year", "Your taste · all time". [windowLabel] is `TasteCard.windowLabel`. */
    fun tasteHeading(windowLabel: String): String =
        "Your taste · " + if (windowLabel.firstOrNull()?.isDigit() == true) "last $windowLabel" else windowLabel.lowercase()

    /** "1,240 listens of 48,912". */
    fun listensLine(window: Int, allTime: Int): String = "%,d listens of %,d".format(window, allTime)

    /** "312 artists", "1 album": the count over Library's title; empty while the total is unknown. */
    fun countEyebrow(noun: String, total: Int?): String =
        if (total == null) "" else "%,d %s".format(total, if (total == 1) noun.removeSuffix("s") else noun)

    /** The order line left of Sort: "By name" for A to Z by name, the direction alone for dates ("Newest first"), else "By album count · Most first". */
    fun sortLine(label: String, direction: String): String = when {
        label == "Name" && direction == "A to Z" -> "By name"
        direction == "Newest first" || direction == "Oldest first" -> direction
        else -> "By ${label.lowercase()} · $direction"
    }

    /** The grey line under a search result: artists "5 albums in your library", albums "Artist, year", songs "Artist · Album". */
    fun searchDetail(type: String, owned: Boolean, artist: String?, album: String?, year: Int?, albumCount: Int?, genre: String?): String = when (type) {
        "artist" -> listOfNotNull(
            albumCount?.let { (if (it == 1) "1 album" else "$it albums") + if (owned) " in your library" else "" },
            genre?.takeIf { it.isNotBlank() },
        ).joinToString(" · ")
        "album" -> GalleryPagesRules.maker(artist.orEmpty(), year)
        "song" -> listOfNotNull(artist?.takeIf { it.isNotBlank() }, album?.takeIf { it.isNotBlank() }).joinToString(" · ")
        else -> ""
    }
}
