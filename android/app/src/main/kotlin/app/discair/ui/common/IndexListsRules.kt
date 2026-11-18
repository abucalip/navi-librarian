package app.discair.ui.common

import app.discair.model.DiscoveryList
import app.discair.model.SearchResult

/**
 * The words and numbers of Index's Discover, Library and Search (docs/INDEX_THEME.md step I4; mockups docs/design/index/pages/discover.html and
 * library-search.html). Pure, so the tests can pin them; the screens only draw what these return.
 */
object IndexListsRules {
    /** A Discover entry's cover, 96dp (index.css: grid 26 / 96 / 1fr). */
    const val ENTRY_COVER_DP = 96

    /** The reason under a Discover entry may run this many lines: it is why the entry is there. */
    const val REASON_LINES = 3

    /** `/api/dashboard/genres` answers at most this many genres unless asked for more; the app asks with the default. */
    const val GENRES_LIMIT = 60

    /** "01", "12": a place in a list, from a 0-based index. */
    fun number(index: Int): String = "%02d".format(index + 1)

    /** The tab names over Discover, in [DiscoveryList] order, so a sideways swipe moves the same way as the tabs. Short words, as the mockup's. */
    fun tabLabel(list: DiscoveryList): String = when (list) {
        DiscoveryList.Daily -> "Daily picks"
        DiscoveryList.DeepDive -> "Deep dives"
        DiscoveryList.NewReleases -> "New releases"
        DiscoveryList.Classics -> "Collection"
        DiscoveryList.Personal -> "Personal"
        DiscoveryList.Saved -> "Saved"
        DiscoveryList.Insights -> "Insights"
    }

    val tabs: List<String> get() = DiscoveryList.entries.map(::tabLabel)

    /** The count beside "Discover": every entry the list shows. Null (no superscript) for Insights, while loading, or when the list is empty. */
    fun headCount(list: DiscoveryList, entryCounts: List<Int>?): String? =
        if (list == DiscoveryList.Insights || entryCounts == null) null else entryCounts.sum().takeIf { it > 0 }?.toString()

    /** "Cocteau Twins · 1990": the maker and the year, either left out when unknown. */
    fun maker(artist: String, year: Int?): String = listOfNotNull(artist.ifBlank { null }, year?.toString()).joinToString(" · ")

    /** What a screen reader hears on an entry's X: the menu holds both ways to say no and the More / Less like this items. */
    fun dismissMenuDescription(album: String): String = "Not this album, not this artist, or more options for $album"

    /** "Artists 312", "Albums 1284": a library tab with its count once known; the name alone while it is not. */
    fun libraryTab(label: String, count: Int?): String = if (count == null) label else "$label $count"

    /** The genre tab's count: the list's length while it is shorter than the server's limit; null (no number) when the list may be cut off. */
    fun genreCount(size: Int, limit: Int = GENRES_LIMIT): Int? = size.takeIf { it < limit }

    /** "Sort · Date added ↓": the order line, the arrow pointing the way the list runs (down for newest or most first, Z to A). */
    fun sortLine(label: String, descending: Boolean): String = "Sort · $label " + if (descending) "↓" else "↑"

    /** "5 albums · 212 plays": an artist row's meta line; plays are left out when the server does not send them (an older server). */
    fun artistMeta(albums: Int, plays: Int?): String =
        listOfNotNull(if (albums == 1) "1 album" else "$albums albums", plays?.let { if (it == 1) "1 play" else "$it plays" }).joinToString(" · ")

    /** "1 album", "14 albums": a genre row's meta line. */
    fun albumCount(n: Int): String = if (n == 1) "1 album" else "$n albums"

    /**
     * The index letter of a name: its first letter or digit, in capitals with any accent dropped ("Ä" files under "A"); "#" for a digit or a name with
     * neither. A letter outside A to Z (another script) is kept as it is.
     */
    fun letter(name: String): String {
        val c = name.trim().firstOrNull { it.isLetterOrDigit() } ?: return "#"
        if (!c.isLetter()) return "#"
        val plain = java.text.Normalizer.normalize(c.toString(), java.text.Normalizer.Form.NFD).firstOrNull() ?: c
        return plain.uppercaseChar().toString()
    }

    /**
     * The letter rail for a list sorted A to Z by name, from the rows' sort keys (the server's `key`, articles and accents already dropped, so the rows run
     * in letter order): each letter with the index of its first row. A letter at or below the last one on the rail is left off, so the rail never runs
     * backwards.
     */
    fun letters(names: List<String>): List<Pair<String, Int>> {
        val out = ArrayList<Pair<String, Int>>()
        names.forEachIndexed { i, n ->
            val l = letter(n)
            if (out.isEmpty() || railOrder(l) > railOrder(out.last().first)) out += l to i
        }
        return out
    }

    /** "#" sorts first, then A to Z, then any other letter by its code. */
    private fun railOrder(l: String): Int = if (l == "#") 0 else (l.firstOrNull()?.code ?: 0) + 1

    /** The rail's letter under a finger at [y] on a rail [height] tall with [count] letters, clamped to the ends. */
    fun letterAt(y: Float, height: Float, count: Int): Int =
        if (count <= 0 || height <= 0f) 0 else (y / height * count).toInt().coerceIn(0, count - 1)

    /** Search's three groups, in the mockup's order: artists, then what is in the library, then what is not ("Not in your library last"). */
    enum class SearchGroup(private val one: String, private val many: String) {
        Artist("Artist", "Artists"), InLibrary("In your library", "In your library"), NotInLibrary("Not in your library", "Not in your library");

        fun title(count: Int): String = if (count == 1) one else many
    }

    /** The groups with their rows, empty groups left out. Rows keep the server's order (nothing is re-ranked); a result streamed twice shows once. */
    fun searchGroups(results: List<SearchResult>): List<Pair<SearchGroup, List<SearchResult>>> {
        val unique = results.distinctBy { searchKey(it) }
        return listOf(
            SearchGroup.Artist to unique.filter { it.type == "artist" },
            SearchGroup.InLibrary to unique.filter { it.type != "artist" && it.owned },
            SearchGroup.NotInLibrary to unique.filter { it.type != "artist" && !it.owned },
        ).filter { it.second.isNotEmpty() }
    }

    /** A search row's key: its kind, its id (else its name) and whether it is owned, so one row never appears twice in a list. */
    fun searchKey(r: SearchResult): String = "${r.type}:${r.id.ifEmpty { r.name }}:${r.owned}"

    /** "3:51" from seconds; null when unknown. */
    fun duration(seconds: Int?): String? = seconds?.takeIf { it > 0 }?.let { "%d:%02d".format(it / 60, it % 60) }

    /**
     * The mono line under a search result: an artist "3 albums · Psychedelic", an album "Album · 2020", a song "Song · Mordechai · 3:51", a genre "Genre".
     * Unknown parts are left out.
     */
    fun searchMeta(r: SearchResult): String = when (r.type) {
        "artist" -> listOfNotNull(r.albumCount?.let(::albumCount), r.genre?.takeIf { it.isNotBlank() }).joinToString(" · ")
        "album" -> listOfNotNull("Album", r.artist?.takeIf { it.isNotBlank() && !r.owned }, r.year?.toString()).joinToString(" · ")
        "song" -> listOfNotNull("Song", r.album?.takeIf { it.isNotBlank() }, duration(r.duration)).joinToString(" · ")
        "genre" -> "Genre"
        else -> ""
    }

    /** The meta word beside Insights' Taste head: the window in words ("Last 90 days", "Past year", "All time"); [windowLabel] is `TasteCard.windowLabel`. */
    fun tasteMeta(windowLabel: String): String =
        if (windowLabel.firstOrNull()?.isDigit() == true) "Last $windowLabel" else windowLabel.replaceFirstChar { it.uppercase() }
}
