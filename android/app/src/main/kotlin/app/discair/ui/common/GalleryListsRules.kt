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

    // Discover's one switch and grid of tiles (Flow's design in Gallery's type; docs/Discover_page.md 4.1 to 4.5).
    const val SWITCH_DP = 52
    const val DASH_DP = 8
    const val DASH_CURRENT_DP = 20
    const val GRID_GAP_X_DP = 18
    const val GRID_GAP_Y_DP = 30
    const val TILE_PRINT_DP = 150
    const val GET_ON_PRINT_DP = 34

    /** The reason under a tile may run this many lines: it is why the tile is there. */
    const val REASON_LINES = 4

    /** The line under a tile: the reason for the pick, else "In your library" for an owned album, else nothing. */
    fun tileReason(reason: String, owned: Boolean): String? = reason.trim().ifEmpty { if (owned) "In your library" else null }

    /**
     * Why a tile is on the list, from everything the server sends, first match wins: the pick's own reason ([pick], `because` or `similar_to`), the
     * server's `reason` sentence (Deep dives, New releases, Personal), the lens and its seed tag (the Daily picks lenses), the artist's albums in the
     * library (Collection), then "In your library" for an owned album. Null when nothing says why.
     */
    fun tileReason(pick: String, serverReason: String, lens: String?, seedTag: String?, libraryAlbums: Int?, owned: Boolean): String? {
        pick.trim().takeIf { it.isNotEmpty() }?.let { return it }
        serverReason.trim().takeIf { it.isNotEmpty() }?.let { return it }
        lensReason(lens, seedTag)?.let { return it }
        if (libraryAlbums != null && libraryAlbums > 0) return "A well-known album; you have " + (if (libraryAlbums == 1) "1 album" else "$libraryAlbums albums") + " by this artist"
        return if (owned) "In your library" else null
    }

    /** The lens and its seed tag in words: "From the acid house you keep repeating". Null without a seed tag. */
    fun lensReason(lens: String?, seedTag: String?): String? {
        val tag = seedTag?.trim()?.takeIf { it.isNotEmpty() } ?: return null
        return when (lens) {
            "repeated_tracks" -> "From the $tag you keep repeating"
            "obsessions" -> "From your $tag obsession"
            "deep_cuts" -> "A lesser-known record from the $tag you play"
            "current_tastes" -> "Close to the $tag you play lately"
            else -> "Through the $tag you play"
        }
    }

    /** "1 ALBUM", "10 ALBUMS": a grid section's count (the screen sets it in capitals). */
    fun countLine(count: Int): String = if (count == 1) "1 album" else "$count albums"

    /** What a screen reader hears on a tile's bookmark. */
    fun saveDescription(album: String, saved: Boolean, failed: Boolean): String = when {
        saved -> "Remove $album from saved"
        failed -> "Could not save $album. Try again"
        else -> "Save $album"
    }

    /** The state a screen reader hears on Get. */
    fun getState(get: app.discair.model.GetState): String = when (get) {
        app.discair.model.GetState.Idle -> "Not requested"
        app.discair.model.GetState.Pending -> "Requesting"
        is app.discair.model.GetState.Requested -> "Requested. Follow it under Downloads"
        is app.discair.model.GetState.Failed -> "Could not request. Select to try again"
    }

    /** The catalogue line on an Insights card: the lens's name; an anniversary card names one ("Anniversary"). */
    fun lensLine(lens: String, anniversary: Boolean): String = when {
        !anniversary -> lens
        lens.endsWith("ies") -> lens.removeSuffix("ies") + "y"
        else -> lens.removeSuffix("s")
    }

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
