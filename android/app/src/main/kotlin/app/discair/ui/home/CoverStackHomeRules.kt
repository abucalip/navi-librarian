package app.discair.ui.home

import app.discair.model.RadioPlay
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/**
 * The pure rules behind Soft Brut's Home (docs/ANDROID_ART_THEMES_PROPOSAL.md section 6.1, mockup soft-brut/home): the pile of
 * sleeves, the radio line, the arrival line and the stat strip. No Compose here, so each rule has a unit test.
 */
object CoverStackHomeRules {
    /** Sleeves drawn behind the front one. */
    const val BEHIND = 2

    /** The two back sleeves are turned 2.5 and 5 degrees (mockup `.b1`, `.b2`). */
    val behindTilt = listOf(2.5f, 5f)

    /** Back sleeves shown, in front-to-back order: the next picks after [index], wrapping, never the front pick itself. */
    fun behind(index: Int, count: Int): List<Int> {
        if (count <= 1) return emptyList()
        return (1..minOf(BEHIND, count - 1)).map { (index + it) % count }
    }

    /** The pick shown after moving [delta] places (1 = swipe left, -1 = swipe right), wrapping around the list. */
    fun step(index: Int, count: Int, delta: Int): Int = if (count <= 0) 0 else Math.floorMod(index + delta, count)

    /** A pick that was dismissed leaves the list; keep the index inside it. */
    fun clamp(index: Int, count: Int): Int = if (count <= 0) 0 else index.coerceIn(0, count - 1)

    /** "1 / 7". */
    fun counter(index: Int, count: Int): String = "${index + 1} / $count"

    /** A horizontal drag this long (dp), or longer, changes the pick. */
    const val SWIPE_DP = 48

    /** The swipe's direction: dragging left (negative) shows the next pick, right the previous; null when too short. */
    fun swipeDelta(dragDp: Float): Int? = when {
        dragDp <= -SWIPE_DP -> 1
        dragDp >= SWIPE_DP -> -1
        else -> null
    }

    /** "Artist · 1994 · Post-rock": the parts that exist, in that order. */
    fun pickLine(artist: String, year: Int?, genre: String?): String =
        listOfNotNull(artist.ifBlank { null }, year?.toString(), genre?.takeIf { it.isNotBlank() }).joinToString(" · ")

    /** The Radio tile's second line: "Last heard: FIP, 08:42" or, with nothing heard yet, the page's own name. */
    fun radioLine(plays: List<RadioPlay>?, zone: ZoneId = ZoneId.systemDefault()): String {
        val last = plays?.firstOrNull() ?: return "Stations"
        val time = last.heardAt?.let { DateTimeFormatter.ofPattern("HH:mm").format(Instant.ofEpochMilli((it * 1000).toLong()).atZone(zone)) }
        val station = last.stationName.ifBlank { null }
        return when {
            station != null && time != null -> "Last heard: $station, $time"
            station != null -> "Last heard: $station"
            time != null -> "Last heard at $time"
            else -> "Stations"
        }
    }

    /** An arrival's detail with the download percent when the server gave one: "Slowdive · Downloading · 64%". */
    fun arrivalLine(row: ArrivalRow): String {
        val pct = row.job.progress?.percent
        return if (pct != null && !row.failed && row.stage < 4) "${row.detail} · ${Math.round(pct)}%" else row.detail
    }

    /** How full the arrival's bar is, 0..1: the server's percent while downloading, else the tracker step. */
    fun arrivalFill(row: ArrivalRow): Float {
        if (row.stage >= 4) return 1f
        val pct = row.job.progress?.percent
        if (row.stage == 1 && pct != null) return (pct / 100.0).toFloat().coerceIn(0.04f, 1f)
        return when (row.stage) { 2 -> 0.9f; else -> 0.04f }
    }

    /** The stat strip's cells: albums, added in the last 30 days, and the link to Library stats. A figure that is not known is left out, never zero. */
    fun statStrip(hero: HeroFigures?): List<String> =
        listOfNotNull(
            hero?.let { "${DashboardRules.formatCount(it.count)} albums" },
            hero?.let { "${it.added30} new this month" },
            "Stats →",
        )

    /** The wording of the two-line states under the pile. */
    const val NO_PICKS = "Nothing recommended right now."
    const val LOADING = "Loading"
}
