package app.discair.ui.common

import app.discair.model.ActiveYears
import app.discair.model.PathYears
import app.discair.model.SharedAlbum

/**
 * The pure rules behind Index's Album, Artist, Genre and Paths (docs/INDEX_THEME.md step I3; mockups index/pages/album-artist-genre and paths): the catalogue
 * lines, the data lists, the album's big numeral, the numbers and letters of steps and reasons. No Compose here, so each rule has a unit test. A fact the
 * server did not send is left out, never filled in.
 */
object IndexPagesRules {
    /** The album page's cover, the unowned album's cover, the artist photo (width and height) and the genre grid's columns. */
    const val ALBUM_COVER_DP = 200
    const val MISSING_COVER_DP = 150
    const val ARTIST_PHOTO_W_DP = 150
    const val ARTIST_PHOTO_H_DP = 180

    /** Top songs and albums shown before ALL →; similar albums shown in the four-column strip. */
    const val SONGS_SHOWN = 5
    const val ALBUMS_SHOWN = 8
    const val COLUMNS = 4

    /** A library position as four digits at least: 418 is "0418". */
    fun pad4(n: Int): String = "%04d".format(n)

    /** A catalogue number: "01", "12" (two digits at least). [index] is 0-based. */
    fun number(index: Int): String = "%02d".format(index + 1)

    /** A reason's letter: A, B, C… [index] is 0-based; past Z it keeps counting with two letters (AA). */
    fun letter(index: Int): String = if (index < 26) ('A' + index).toString() else letter(index / 26 - 1) + letter(index % 26)

    /** The album page's bar: "Album 0418 / 1284" when the server placed it, "Album" when it did not, "Not in your library" for an album the library lacks. */
    fun albumCatalogue(owned: Boolean, position: Int?, total: Int?): String = when {
        !owned -> "Not in your library"
        position != null && total != null && position in 1..total -> "Album ${pad4(position)} / $total"
        else -> "Album"
    }

    /** "44:12"; an hour or more reads "1:19:04"; null for no length. */
    fun length(seconds: Int): String? {
        if (seconds <= 0) return null
        val h = seconds / 3600
        val m = (seconds % 3600) / 60
        val s = seconds % 60
        return if (h > 0) "%d:%02d:%02d".format(h, m, s) else "%d:%02d".format(m, s)
    }

    /** A track's time: "4:10". */
    fun clock(seconds: Int): String = "%d:%02d".format(seconds / 60, seconds % 60)

    /** The album's numeral beside the cover: the playing song's place ("05", "/ 10", "Playing"), or, when nothing of this album plays, the song count ("10", "Songs"). */
    data class Numeral(val big: String, val small: String?, val word: String, val accent: Boolean)

    /** [playing] is the 0-based place of the playing song in the list, or null. Null for an album with no songs listed. */
    fun albumNumeral(playing: Int?, songs: Int): Numeral? = when {
        songs <= 0 -> null
        playing != null && playing in 0 until songs -> Numeral(number(playing), "/ $songs", "Playing", accent = true)
        else -> Numeral("%02d".format(songs), null, if (songs == 1) "Song" else "Songs", accent = false)
    }

    /** The owned album's data list: Artist, Year, Length, Format (index.css `.dl`), then Genre. A line whose data is unknown is left out. */
    fun albumRows(artist: String, year: Int?, seconds: Int, quality: String?, genre: String?): List<IndexDatum> = buildList {
        if (artist.isNotBlank()) add(IndexDatum("Artist", artist))
        if (year != null) add(IndexDatum("Year", year.toString()))
        length(seconds)?.let { add(IndexDatum("Length", it)) }
        if (!quality.isNullOrBlank()) add(IndexDatum("Format", quality))
        if (!genre.isNullOrBlank()) add(IndexDatum("Genre", genre))
    }

    /** The unowned album's key/value grid: Artist, Year, Genre, Songs. Unknown cells are left out. */
    fun missingAlbumGrid(artist: String, year: Int?, genre: String?, songs: Int): List<IndexDatum> = buildList {
        if (artist.isNotBlank()) add(IndexDatum("Artist", artist))
        if (year != null) add(IndexDatum("Year", year.toString()))
        if (!genre.isNullOrBlank()) add(IndexDatum("Genre", genre))
        if (songs > 0) add(IndexDatum("Songs", songs.toString()))
    }

    /** "5 of 9"; null unless both are known and the total is not zero. */
    fun ownedOf(owned: Int?, total: Int?): String? = if (owned != null && total != null && total > 0) "$owned of $total" else null

    /** Active years: "1967 – 2007", "Since 1967" while active, "From 1967" when ended with no end year; null when no begin year is stored. */
    fun activeYears(years: ActiveYears?): String? {
        val begin = years?.begin ?: return null
        val end = years.end
        return when {
            end != null && end != begin -> "$begin – $end"
            end != null -> "$begin"
            years.ended -> "From $begin"
            else -> "Since $begin"
        }
    }

    /** "1,284" for a count. */
    fun count(n: Int): String = "%,d".format(n)

    /**
     * The artist's data list: Genre, Owned ("5 of 9", else the owned album count alone), Plays (only for an artist in the library, so 0 is said), Active.
     * A line whose data is unknown is left out.
     */
    fun artistRows(genre: String?, ownedCount: Int?, albumCount: Int?, libraryAlbums: Int, inLibrary: Boolean, plays: Int?, years: ActiveYears?): List<IndexDatum> = buildList {
        if (!genre.isNullOrBlank()) add(IndexDatum("Genre", genre))
        val owned = ownedOf(ownedCount, albumCount) ?: if (inLibrary && libraryAlbums > 0) libraryAlbums.toString() else null
        add(if (owned != null) IndexDatum("Owned", owned) else IndexDatum("Owned", "None", accent = true))
        if (inLibrary && plays != null) add(IndexDatum("Plays", count(plays)))
        activeYears(years)?.let { add(IndexDatum("Active", it)) }
    }

    /** The Albums section's meta word: "4 to get"; null when the library has them all. */
    fun toGet(missing: Int): String? = if (missing > 0) "$missing to get" else null

    /** "Spiritual jazz 38": the genre's count beside its head (albums listed). Null when none. */
    fun genreCount(albums: Int): String? = if (albums > 0) albums.toString() else null

    // ---------------------------------------------------------------- Paths

    /** The Paths sheet header's line: "7 kinds · 4 steps" once the chosen kind has answered, "7 kinds" until then. */
    fun pathsLine(kinds: Int, steps: Int?): String =
        listOfNotNull(if (kinds == 1) "1 kind" else "$kinds kinds", steps?.let { if (it == 1) "1 step" else "$it steps" }).joinToString(" · ")

    /** An opened step's bar line: "Studio crew · step 01 / 04". */
    fun stepLine(kind: String, index: Int, count: Int): String = "$kind · step ${number(index)} / ${"%02d".format(count)}"

    /** The opened album step's eyebrow: "1969 · in library", "Not in library" with no year. */
    fun stepEyebrow(year: Int?, owned: Boolean): String = listOfNotNull(year?.toString(), if (owned) "In library" else "Not in library").joinToString(" · ")

    /** Years together: "1968 – 1971", one year alone when they are the same. */
    fun withYears(years: PathYears?): String? = years?.let { if (it.from == it.to) "${it.from}" else "${it.from} – ${it.to}" }

    /** "Owned 2 of 4" for a sideman stop's shared albums; null when the server did not send them or sent none. */
    fun sharedOwned(albums: List<SharedAlbum>?): String? = albums?.takeIf { it.isNotEmpty() }?.let { "${it.count(SharedAlbum::owned)} of ${it.size}" }

    /** A lettered reason's word: "Played together" for a sideman credit, the album paths' own words for theirs, else the kind's name. */
    fun reasonWord(code: String, kindLabel: String): String = when (code) {
        "sideman_on" -> "Played together"
        else -> app.discair.model.reasonEyebrow(code).takeIf { it != "Why it's here" } ?: kindLabel
    }

    /** A reason as a sentence: the server's sideman wording is a fragment that follows the stop's name ("led Karma, …"), so the name goes before it; a full stop ends it. */
    fun reasonSentence(name: String, text: String): String {
        val t = text.trim()
        if (t.isEmpty()) return t
        val whole = if (t.first().isLowerCase() && name.isNotBlank()) "$name $t" else t
        return if (whole.last() in ".!?") whole else "$whole."
    }
}
