package app.discair.model

import app.discair.net.ConnectionException
import app.discair.net.ConnectionFailure
import app.discair.net.classifyException
import app.discair.data.CacheMiss

/**
 * What the album Paths sheet lists: the four graph kinds plus Neighbours by ear. The sheet works on [AlbumStep]s so the
 * list and pane do not care which route a step came from.
 */
enum class AlbumTab(val label: String, val graph: AlbumPathKind?) {
    StudioCrew("Studio crew", AlbumPathKind.StudioCrew),
    GuestList("Guest list", AlbumPathKind.GuestList),
    CoversAndSources("Covers and sources", AlbumPathKind.CoversAndSources),
    SameYearSameScene("Same year, same scene", AlbumPathKind.SameYearSameScene),
    SameRoom("Same room", AlbumPathKind.SameRoom),
    ListenThroughGaps("Listen-through gaps", AlbumPathKind.ListenThroughGaps),
    NeighboursByEar("Neighbours by ear", null),
}

/** The tabs a sheet offers: Neighbours by ear only when the server reports sonic similarity. */
fun albumTabs(sonicAvailable: Boolean): List<AlbumTab> = AlbumTab.entries.filter { it.graph != null || sonicAvailable }

/**
 * One reason on an album step, as the server sent it. [credits] are the stored credits behind it, the one on the start
 * first; the Trail link reads the role of a studio credit from them.
 */
data class AlbumStepReason(
    val code: String, val text: String, val via: PathRef?, val anchor: PathRef?,
    val credits: List<PathCreditFact> = emptyList(),
)

/** One owned album a path reaches. [detail] is the second line of its list row. */
data class AlbumStep(
    val album: String, val artist: String, val year: Int?, val albumId: String?,
    val detail: String, val reasons: List<AlbumStepReason>, val matchCount: Int = 0,
    /** Listen-through gaps: the server's play label ("Not played"); null elsewhere. */
    val play: String? = null,
)

/** The steps of one tab and the honest notes under them (what was cut, what was skipped). */
data class AlbumAnswer(
    val steps: List<AlbumStep>, val notes: List<String>, val seeds: Int = 0,
    /** Said instead of the generic empty line when the server's own figures explain why nothing is listed. */
    val empty: String? = null,
)

/** What the play history of a Listen-through gaps answer means for the list, in words. Never reads a count as taste. */
internal fun historyNotes(history: PathHistory?): List<String> {
    history ?: return emptyList()
    fun albums(n: Int) = "$n ${if (n == 1) "album" else "albums"}"
    return when (history.state) {
        "thin" -> listOf("Your play history is too short to tell which albums you have not played, so every album these credits reach is listed, played or not.")
        "unavailable" -> listOf("Your play history could not be read, so every album these credits reach is listed, played or not.")
        else -> buildList {
            if (history.filteredOut > 0) add("${albums(history.filteredOut)} reached by these credits left out because you have played ${if (history.filteredOut == 1) "it" else "them"} more than ${history.littlePlaysBelow - 1} ${if (history.littlePlaysBelow - 1 == 1) "time" else "times"}.")
            if (history.unknown > 0) add("${albums(history.unknown)} left out because ${if (history.unknown == 1) "it has" else "they have"} no play record.")
        }
    }
}

internal fun truncationNote(reason: String): String {
    val words = when (reason) {
        "rows" -> "row limit"
        "time" -> "time limit"
        "stops" -> "stop limit"
        else -> "limit"
    }
    return "The server stopped this path early ($words), so later steps may be missing."
}

/** Steps of a graph kind. A step without a reason cannot be explained and is already left out by the parser. */
fun PathsResponse.toAlbumAnswer(): AlbumAnswer {
    val steps = stops.map { stop ->
        val by = stop.albumArtist ?: stop.displayContext.orEmpty()
        val via = stop.reasons.firstOrNull()?.via?.name
        AlbumStep(
            album = stop.name, artist = by, year = null, albumId = null,
            detail = listOfNotNull(by.ifBlank { null }, stop.play ?: via).joinToString(" · ").ifBlank { stop.reason },
            reasons = stop.reasons.map { AlbumStepReason(it.code, it.text, it.via, it.anchor, it.credits) },
            play = stop.play,
        )
    }
    val notes = buildList {
        addAll(historyNotes(history))
        capped.forEach { add("${it.more} more ${if (it.more == 1) "album" else "albums"} with ${it.via} ${if (it.more == 1) "is" else "are"} not shown.") }
        truncated?.let { add(truncationNote(it)) }
    }
    val empty = history?.takeIf { it.state == "ok" && steps.isEmpty() && it.filteredOut > 0 }?.let {
        "Every album these credits reach is one you have already played more than ${it.littlePlaysBelow - 1} ${if (it.littlePlaysBelow - 1 == 1) "time" else "times"}, so there is no gap to list."
    }
    return AlbumAnswer(steps, notes, empty = empty)
}

/** Steps of Neighbours by ear. The count of matched tracks is the only measure shown; `similarity` is never read. */
fun SonicAlbumNeighbours.toAlbumAnswer(): AlbumAnswer {
    val of = seeds.size
    val steps = stops.map { s ->
        val tracks = if (of > 0) "${s.matchCount} of $of tracks" else "${s.matchCount} ${if (s.matchCount == 1) "track" else "tracks"}"
        AlbumStep(
            album = s.album, artist = s.artist, year = s.year, albumId = s.albumId,
            detail = listOf(s.artist.ifBlank { null }, tracks).filterNotNull().joinToString(" · "),
            reasons = listOfNotNull(s.reasonText?.let { AlbumStepReason("sonic_neighbour", it, null, null) }),
            matchCount = s.matchCount,
        )
    }
    val notes = buildList {
        if (skipped.isNotEmpty()) add("${skipped.size} ${if (skipped.size == 1) "track has" else "tracks have"} no sound analysis and ${if (skipped.size == 1) "was" else "were"} skipped.")
        truncated?.let { add(truncationNote(it)) }
    }
    return AlbumAnswer(steps, notes, seeds = of)
}

/** One line under the chips, per tab. [seeds] is how many of the album's tracks Neighbours by ear used, once known. */
fun albumTabDescription(tab: AlbumTab, album: String, seeds: Int = 0): String = when (tab) {
    AlbumTab.StudioCrew -> "Albums in your library that share a producer, engineer or mixer credit with $album."
    AlbumTab.GuestList -> "Albums in your library where the guests credited on $album also appear."
    AlbumTab.CoversAndSources -> "Other albums in your library with a recording of a song on $album, and the works they come from."
    AlbumTab.SameYearSameScene -> "Albums in your library from the same years as $album, linked by a label, an area or a shared artist."
    AlbumTab.SameRoom -> "Albums in your library with a recording made in the same studio or at the same event as a recording on $album."
    AlbumTab.ListenThroughGaps -> "Albums in your library that share a credit with $album and that you have played little or never."
    AlbumTab.NeighboursByEar -> if (seeds > 0) "Albums in your library that sound like $album, found from $seeds of its tracks." else "Albums in your library that sound like $album."
}

fun albumPathsEmpty(tab: AlbumTab, album: String) =
    "No ${tab.label.lowercase()} path from $album yet. A path appears only when every step has evidence."

/** The honest reason an album path could not be read, in the album's words. */
fun albumPathsFailure(error: Throwable): ConnectionFailure {
    if (error is CacheMiss) return ConnectionFailure.Server(0, "Paths need the server. They are not saved on this phone.")
    val failure = (error as? ConnectionException)?.failure
    if (failure is ConnectionFailure.Server) {
        return when (failure.code) {
            400 -> ConnectionFailure.Server(400, "The server can't build this path for the album.")
            404 -> ConnectionFailure.Server(404, "This album isn't in the server's knowledge store yet.")
            422 -> ConnectionFailure.Server(422, "The server rejected the request.")
            501 -> ConnectionFailure.Server(501, "The server can't build this path yet.")
            502 -> ConnectionFailure.Server(502, "The server couldn't read its knowledge store. Try again later.")
            else -> failure
        }
    }
    return classifyException(error, networkAvailable = true)
}

/** "Within 2 years" from a Same year, same scene sentence ("...within 2 years of each other"); null when the server worded it otherwise. */
internal fun yearGap(text: String): String? =
    Regex("""within (\d+) years?""").find(text)?.groupValues?.get(1)?.toIntOrNull()?.let { "Within $it ${if (it == 1) "year" else "years"}" }

/** The small label above a reason's card, from its code. */
internal fun reasonEyebrow(code: String): String = when (code) {
    "crew_on" -> "Production credit"
    "guest_on" -> "Guest credit"
    "same_work" -> "Same work"
    "derived_work" -> "Related work"
    "same_period_label" -> "Same label"
    "same_period_credit" -> "Shared artist"
    "same_period_area" -> "Same area"
    "recorded_at" -> "Recorded at"
    "sonic_neighbour" -> "Sounds alike"
    else -> "Why it's here"
}
