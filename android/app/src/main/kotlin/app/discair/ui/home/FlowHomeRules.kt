package app.discair.ui.home

import app.discair.model.Pick
import app.discair.model.ShelfAlbum

/**
 * The pure rules behind Flow's Home (docs/ANDROID_ART_THEMES_PROPOSAL.md section 6.2, mockup flow/home): the segmented control, the cover
 * carousel, the lines under the cover and the grouped list. No Compose here, so each rule has a unit test.
 */
object FlowHomeRules {
    /** What the carousel shows. Picks is `picks(10)`, New is `shelf(Newest)`, Played is `shelf(Recent)`. */
    enum class Tab(val label: String) { Picks("Picks"), New("New"), Played("Played") }

    val labels: List<String> = Tab.entries.map { it.label }

    /** The remembered tab by its name; a missing or unknown value is Picks. */
    fun tabOf(saved: String?): Tab = Tab.entries.firstOrNull { it.name == saved } ?: Tab.Picks

    /** Carousel sizes (mockup `.flow .c`, `.flow .s`): the centred cover, its neighbours, their opacity, how far they are cut by the screen edge. */
    const val CENTER_DP = 220
    const val SIDE_DP = 160
    const val SIDE_ALPHA = 0.75f
    const val SIDE_OVERHANG_DP = 70
    const val CAROUSEL_HEIGHT_DP = 236

    /** One cover in the carousel and what the lines and buttons under it need. [albumId] is the library album when the album is owned. */
    data class Item(val artist: String, val title: String, val year: Int?, val genre: String?, val albumId: String?, val artworkUrl: String?)

    fun items(pick: Pick) = Item(pick.artist, pick.album, pick.year, pick.genres.firstOrNull(), null, null)

    fun items(album: ShelfAlbum) = Item(album.artist, album.name, album.year, null, album.id.ifBlank { null }, album.artworkUrl)

    /** The neighbours drawn beside the centred cover: the previous and the next, wrapping; never the centred cover itself, never the same one twice. */
    fun neighbours(index: Int, count: Int): Pair<Int?, Int?> {
        if (count <= 1) return null to null
        val next = (index + 1) % count
        val prev = Math.floorMod(index - 1, count)
        return (if (prev == next) null else prev) to next
    }

    /** The cover shown after moving [delta] places (1 = swipe left, -1 = swipe right), wrapping around the list. */
    fun step(index: Int, count: Int, delta: Int): Int = if (count <= 0) 0 else Math.floorMod(index + delta, count)

    /** A pick that was dismissed leaves the list; keep the index inside it. */
    fun clamp(index: Int, count: Int): Int = if (count <= 0) 0 else index.coerceIn(0, count - 1)

    /** A horizontal drag this long (dp), or longer, changes the cover. */
    const val SWIPE_DP = 48

    /** The swipe's direction: dragging left (negative) shows the next cover, right the previous; null when too short. */
    fun swipeDelta(dragDp: Float): Int? = when {
        dragDp <= -SWIPE_DP -> 1
        dragDp >= SWIPE_DP -> -1
        else -> null
    }

    /** "Bark Psychosis · 1994 · Post-rock": the parts that exist, in that order. */
    fun line(item: Item): String =
        listOfNotNull(item.artist.ifBlank { null }, item.year?.toString(), item.genre?.takeIf { it.isNotBlank() }).joinToString(" · ")

    /** Picks get Get album, Save and the menu; New and Played play what is owned. */
    fun hasGet(tab: Tab) = tab == Tab.Picks

    /** What a tab says when it has nothing to show. */
    fun empty(tab: Tab): String = when (tab) {
        Tab.Picks -> "Nothing recommended right now."
        Tab.New -> "Nothing was added lately."
        Tab.Played -> "Nothing played yet."
    }

    /** The Library row's state line: "1,284 albums · 12 new this month"; a figure that is not known is left out, never zero. */
    fun libraryLine(hero: HeroFigures?): String =
        if (hero == null) "Stats" else "${DashboardRules.formatCount(hero.count)} albums · ${hero.added30} new this month"

    /** The Radio row's state line, the same words every theme's Radio entry uses. */
    fun radioLine(plays: List<app.discair.model.RadioPlay>?): String = CoverStackHomeRules.radioLine(plays)

    /** An arrival's state in words with the percent while downloading: "Downloading · 64%". */
    fun arrivalLine(row: ArrivalRow): String = CoverStackHomeRules.arrivalLine(row)

    /** The caption of the Artists block when there is no listening yet. */
    const val ARTISTS_LOADING = "Loading…"
}
