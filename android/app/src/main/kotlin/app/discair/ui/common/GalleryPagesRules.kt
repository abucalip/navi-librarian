package app.discair.ui.common

/**
 * The words on Gallery's Album, Artist and Genre pages (docs/GALLERY_THEME.md section 10, mockup gallery/pages/album-artist-genre).
 * Pure, so the tests can pin them. The catalogue lines are set in DM Mono capitals by the screens; these return plain text.
 */
object GalleryPagesRules {
    const val ALBUM_PRINT_DP = 228
    const val ARTIST_PRINT_DP = 200
    const val CAPTION_PRINT_DP = 151
    const val SIMILAR_PRINT_DP = 104
    const val ROW_PRINT_DP = 48
    const val PHOTO_PRINT_DP = 52
    const val SONGS_SHOWN = 5
    const val ALBUMS_SHOWN = 6
    const val MISSING_SHOWN = 10

    const val NOT_OWNED = "Not in your library. Get it and its songs are listed here."

    /** "1991 · 6 songs · 43 min · FLAC": year, song count, length and quality, each only when known. */
    fun albumEyebrow(year: Int?, songs: Int, seconds: Int, quality: String?): String =
        listOfNotNull(
            year?.toString(),
            if (songs > 0) (if (songs == 1) "1 song" else "$songs songs") else null,
            length(seconds),
            quality?.trim()?.ifEmpty { null },
        ).joinToString(" · ")

    /** "43 min", "1 h 19 min", "2 h"; null when the length is unknown. */
    fun length(seconds: Int): String? {
        val minutes = (seconds + 30) / 60
        return when {
            seconds <= 0 -> null
            minutes >= 60 -> "${minutes / 60} h" + if (minutes % 60 > 0) " ${minutes % 60} min" else ""
            else -> "${maxOf(minutes, 1)} min"
        }
    }

    /** "3:07" for a song's length. */
    fun clock(seconds: Int): String = "%d:%02d".format(seconds / 60, seconds % 60)

    /** "1981 to 1991", a single year when they agree, null with none. */
    fun yearSpan(years: List<Int?>): String? {
        val known = years.filterNotNull()
        if (known.isEmpty()) return null
        val first = known.min()
        val last = known.max()
        return if (first == last) "$first" else "$first to $last"
    }

    /** "5 albums in your library · 1981 to 1991", or "Not in your library". */
    fun artistEyebrow(inLibrary: Boolean, albumCount: Int, years: List<Int?>): String =
        if (!inLibrary) "Not in your library"
        else listOfNotNull(plural(albumCount, "album") + " in your library", yearSpan(years)).joinToString(" · ")

    /** "86 albums · 41 artists in your library". */
    fun genreEyebrow(albums: Int, artists: Int): String = plural(albums, "album") + " · " + plural(artists, "artist") + " in your library"

    /** "Floating Points, 2021": the maker and the year under a caption. */
    fun maker(artist: String, year: Int?): String = listOfNotNull(artist.ifBlank { null }, year?.toString()).joinToString(", ")

    /** The sub line of a missing album: the year and how often it is played. */
    fun missingSub(year: Int?, popularity: Long): String =
        listOfNotNull(year?.toString(), if (popularity > 0) abbreviate(popularity) + " listens" else null).joinToString(" · ")

    /** The album page's tabs, in order: Songs (when the page lists songs), Info, Reviews and Booklet (only with booklet pages). */
    fun albumTabs(hasSongs: Boolean, hasBooklet: Boolean): List<String> =
        listOfNotNull(if (hasSongs) "Songs" else null, "Info", "Reviews", if (hasBooklet) "Booklet" else null)

    /** The tab shown before the reader picks one: Songs when listed; else Reviews once an album with no description has finished loading; else Info. */
    fun defaultTab(tabs: List<String>, finished: Boolean, noDescription: Boolean): Int = when {
        "Songs" in tabs -> tabs.indexOf("Songs")
        finished && noDescription -> tabs.indexOf("Reviews")
        else -> tabs.indexOf("Info")
    }

    /** What the note under the actions says: nothing when every song is in the library, else which are missing. */
    fun note(owned: Boolean, missingSongs: Int): String? = when {
        !owned -> NOT_OWNED
        missingSongs > 0 -> plural(missingSongs, "song") + (if (missingSongs == 1) " is" else " are") + " not in your library."
        else -> null
    }
}
