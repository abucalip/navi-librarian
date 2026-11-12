package app.discair.ui.home

import app.discair.data.AlbumSort
import app.discair.data.LibraryRepository
import app.discair.model.AcquisitionJob
import app.discair.model.InsightCard
import app.discair.model.InsightsResponse
import app.discair.model.TasteProfiles
import app.discair.ui.common.ChartPoint
import app.discair.ui.common.ChartRules
import app.discair.ui.common.ChartState
import app.discair.ui.common.ShiftRow
import java.time.Duration
import java.time.Instant
import java.time.LocalDate
import java.time.YearMonth
import java.time.ZoneOffset
import java.time.format.DateTimeParseException
import java.time.format.TextStyle
import java.util.Locale
import kotlin.math.abs

/*
 * The pure half of the Android dashboard (docs/redesign.md 8.1, step A6): every figure and state the modules draw, computed
 * from existing models only. Missing is never zero: a figure that cannot be known is null and its module says so in words.
 */

/** What one pass over the library list (newest first) found: the server's total and the added dates it read. */
data class LibraryRead(
    /** The server's album count; null when the list carried none. */
    val total: Int?,
    /** Added dates read, newest first. A null is an album the server gave no date for. */
    val added: List<Instant?>,
    /** True when the read reached an album older than the window or the last page, so every album in the window was seen. */
    val complete: Boolean,
)

/** The hero: the album count, albums added in the last 30 days, and in the 30 before. */
data class HeroFigures(val count: Int, val added30: Int, val addedBefore30: Int)

/** One row of Arrivals. [stage] is the tracker's current step (4 = in library). */
data class ArrivalRow(val job: AcquisitionJob, val stage: Int, val failed: Boolean, val detail: String)

/** The Waiting stat: today's picks, and how many arrivals came in. */
data class WaitingFigures(val picks: Int, val arrived: Int)

object DashboardRules {
    const val GROWTH_MONTHS = 12
    const val ARRIVALS_SHOWN = 2
    const val TASTE_SHIFTS_SHOWN = 3

    /** The read covers a year, plus the 30 days before the oldest month's start, so every month has its count. */
    const val READ_DAYS = 400L
    const val MAX_PAGES = 20

    /** The two-pane layout starts here (docs/redesign.md 7.1). */
    const val TWO_PANE_MIN_DP = 840

    fun parseAdded(added: String?): Instant? {
        if (added.isNullOrBlank()) return null
        return try { Instant.parse(added) } catch (e: DateTimeParseException) { null }
    }

    /** Reads the library list sorted by date added, newest first, until it passes [READ_DAYS], runs out or hits [MAX_PAGES]. */
    fun read(repo: LibraryRepository, now: Instant = Instant.now()): LibraryRead {
        val limit = now.minus(Duration.ofDays(READ_DAYS))
        val out = mutableListOf<Instant?>()
        var total: Int? = null
        var cursor: String? = null
        repeat(MAX_PAGES) {
            val page = repo.albums("", AlbumSort.Added, true, cursor)
            if (total == null) total = page.total
            for (item in page.items) {
                val at = parseAdded(item.added)
                if (at != null && at.isBefore(limit)) return LibraryRead(total, out, complete = true)
                out += at
            }
            cursor = page.nextCursor ?: return LibraryRead(total, out, complete = true)
        }
        return LibraryRead(total, out, complete = false)
    }

    /** The hero, or null when the server gave no total or the read stopped before covering 60 days. */
    fun hero(read: LibraryRead, now: Instant): HeroFigures? {
        val total = read.total ?: return null
        val cut30 = now.minus(Duration.ofDays(30))
        val cut60 = now.minus(Duration.ofDays(60))
        val dates = read.added.filterNotNull()
        // A read cut short before day 60 cannot say what was added in the 30 days before.
        if (!read.complete && (dates.lastOrNull()?.isAfter(cut60) != false)) return null
        val recent = dates.count { !it.isBefore(cut30) }
        val before = dates.count { !it.isBefore(cut60) && it.isBefore(cut30) }
        return HeroFigures(total, recent, before)
    }

    /** "12 added in the last 30 days · 7 in the 30 before". */
    fun heroSentence(h: HeroFigures): String = "${h.added30} added in the last 30 days · ${h.addedBefore30} in the 30 before"

    /** The arrow word beside the sentence, so colour never carries the change alone. */
    fun heroTrend(h: HeroFigures): String = when {
        h.added30 > h.addedBefore30 -> "Up"
        h.added30 < h.addedBefore30 -> "Down"
        else -> "Level"
    }

    /**
     * Albums in the library at the end of each of the last [months] months (the last point is now), counted back from the
     * server's total by the added dates. Null when the read did not reach far enough back, or the total is unknown.
     */
    fun growth(read: LibraryRead, now: Instant, months: Int = GROWTH_MONTHS): List<ChartPoint>? {
        val total = read.total ?: return null
        if (!read.complete) return null
        val dates = read.added.filterNotNull()
        val current = YearMonth.from(now.atZone(ZoneOffset.UTC))
        return (months - 1 downTo 0).map { back ->
            val month = current.minusMonths(back.toLong())
            val end: Instant = if (back == 0) now else month.plusMonths(1).atDay(1).atStartOfDay(ZoneOffset.UTC).toInstant()
            val addedAfter = dates.count { it.isAfter(end) }
            val value = (total - addedAfter).coerceAtLeast(0).toDouble()
            ChartPoint(month.month.getDisplayName(TextStyle.SHORT, Locale.ENGLISH), value)
        }
    }

    fun growthSubtitle(points: List<ChartPoint>, now: Instant): String {
        val first = points.firstOrNull() ?: return "Albums over the last 12 months"
        val from = YearMonth.from(now.atZone(ZoneOffset.UTC)).minusMonths((points.size - 1).toLong())
        return "Albums at the end of each month, ${first.label} ${from.year} to now"
    }

    fun growthState(points: List<ChartPoint>?, loading: Boolean): ChartState = when {
        loading -> ChartState.Loading
        points == null -> ChartState.Unavailable("The library list could not be read back far enough to chart the year.")
        points.map { it.value }.distinct().size < 2 && points.all { it.value == 0.0 } ->
            ChartState.Insufficient("Nothing in the library yet to chart.")
        else -> ChartState.Ready
    }

    // ----- arrivals -----------------------------------------------------------------------------------------------

    /** The tracker's current step for a status: 0 Found, 1 Downloading, 2 Importing, 4 in library. */
    fun stageOf(job: AcquisitionJob): Int = when (job.status.lowercase()) {
        "imported" -> 4
        "importing" -> 2
        "downloading", "download_complete_waiting_for_folder" -> 1
        else -> 0
    }

    /** Failed means a record the server will not continue by itself: it offers Try again. */
    fun isFailed(job: AcquisitionJob): Boolean = job.info.tone == app.discair.model.Tone.Error

    /** Up to [ARRIVALS_SHOWN] rows: active downloads first, then albums that arrived. Songs and dismissed records are left out. */
    fun arrivals(jobs: List<AcquisitionJob>?): List<ArrivalRow> {
        val albums = jobs.orEmpty().filter { !it.isSong }
        val live = albums.filter { it.isActive || isFailed(it) }
        val arrived = albums.filter { it.isImported }
        return (live + arrived).take(ARRIVALS_SHOWN).map { job ->
            ArrivalRow(job, stageOf(job), isFailed(job), arrivalDetail(job))
        }
    }

    fun arrivalDetail(job: AcquisitionJob): String {
        val status = job.info.label
        return when {
            job.isImported -> "${job.artistName} · Arrived"
            isFailed(job) -> "${job.artistName} · $status" + (job.error?.let { ": $it" } ?: "")
            else -> "${job.artistName} · $status"
        }
    }

    fun waiting(pickCount: Int?, jobs: List<AcquisitionJob>?): WaitingFigures? {
        if (pickCount == null) return null
        return WaitingFigures(pickCount, jobs.orEmpty().count { !it.isSong && it.isImported })
    }

    // ----- taste --------------------------------------------------------------------------------------------------

    /** The headline window's biggest listed shifts as dumbbell rows, in points of share; only what the server listed. */
    fun tasteRows(profiles: TasteProfiles?, shown: Int = TASTE_SHIFTS_SHOWN): List<ShiftRow> {
        val window = profiles?.headline?.window ?: return emptyList()
        return profiles.shifts(window).take(shown).map { ShiftRow(it.value, it.fromShare * 100.0, it.toShare * 100.0) }
    }

    // ----- insight ------------------------------------------------------------------------------------------------

    /**
     * One card from an enabled lens that has cards, rotating by [dayNumber] (days since the epoch): the day picks the lens, then the
     * card within it. [hidden] cards (dismissed) are skipped. Null when no lens has a card.
     */
    fun insightOfTheDay(response: InsightsResponse?, hidden: Set<String>, dayNumber: Long): InsightCard? {
        if (response == null) return null
        val lenses = response.orderedKinds.mapNotNull { kind ->
            val lens = response.lenses[kind]?.takeIf { it.enabled } ?: return@mapNotNull null
            val cards = lens.cards.filter { it.id !in hidden }
            if (cards.isEmpty()) null else cards
        }
        if (lenses.isEmpty()) return null
        val lens = lenses[Math.floorMod(dayNumber, lenses.size.toLong()).toInt()]
        return lens[Math.floorMod(dayNumber / lenses.size, lens.size.toLong()).toInt()]
    }

    // ----- server and banner --------------------------------------------------------------------------------------

    /** The Server row's sentence: all quiet, or the one thing that needs attention. */
    fun serverLine(problem: String?): String = if (problem.isNullOrBlank()) "Server: all quiet" else "Server: needs attention"

    /** The warning banner under the top bar: shown for a failing service, with its words; null when nothing is wrong. */
    fun banner(problem: String?): String? = problem?.takeIf { it.isNotBlank() }

    // ----- stat cards ---------------------------------------------------------------------------------------------

    /** What a stat card says when its figure is not served yet. Never a zero. */
    const val NOT_AVAILABLE = "Not available yet"

    fun changeWords(delta: Int, unit: String): String = when {
        delta > 0 -> "▲ $delta more $unit"
        delta < 0 -> "▼ ${abs(delta)} fewer $unit"
        else -> "No change"
    }

    fun dayNumber(date: LocalDate): Long = date.toEpochDay()

    fun formatCount(n: Int): String = ChartRules.formatCount(n.toDouble())
}

/** The modules of 8.1 in the order they appear. Phone is one column; at 840 dp the primary pane is two thirds, the secondary one third. */
enum class DashModule {
    Hero, Stats, Pick, Arrivals, Taste, Insight, Numbers, Shelves, Genres, Radio, Server;

    companion object {
        val phone = listOf(Hero, Stats, Pick, Arrivals, Taste, Insight, Numbers, Shelves, Genres, Radio, Server)
        val primary = listOf(Hero, Pick, Arrivals, Numbers, Shelves, Genres, Radio, Server)
        val secondary = listOf(Stats, Taste, Insight)
    }
}

/** Everything the modules draw, gathered once so the screen function only lays them out. */
data class DashboardData(
    val hero: HeroFigures?,
    val heroLoading: Boolean,
    val waiting: WaitingFigures?,
    val arrivals: List<ArrivalRow>,
    val picks: List<app.discair.model.Pick>,
    val picksState: app.discair.ui.common.Load<List<app.discair.model.Pick>>,
    val retryPicks: () -> Unit,
    val tasteProfiles: TasteProfiles?,
    val tasteLoaded: Boolean,
    val tasteFailed: Boolean,
    val insight: InsightCard?,
    val libraryRead: LibraryRead?,
    val libraryLoading: Boolean,
    val now: Instant,
    val problem: String?,
)
