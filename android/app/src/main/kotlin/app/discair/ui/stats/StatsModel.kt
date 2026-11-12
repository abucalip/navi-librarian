package app.discair.ui.stats

import app.discair.data.AlbumSort
import app.discair.data.LibraryRepository
import app.discair.model.TasteProfiles
import app.discair.ui.common.ChartPoint
import app.discair.ui.common.ChartState
import app.discair.ui.common.PairedRow
import app.discair.ui.common.RankedItem
import app.discair.ui.home.DashboardRules
import java.time.Instant
import java.time.LocalDate
import java.time.YearMonth
import java.time.ZoneOffset
import java.time.format.TextStyle
import java.util.Locale

/*
 * The pure half of the Library stats screen (docs/redesign.md 8.2, step A7): the series and shares each chart draws, computed from
 * the library list and the taste body only. Missing is never zero: a figure that cannot be known is null and its chart says so.
 */

enum class StatsRange(val label: String) { ThreeMonths("3M"), OneYear("1Y"), FiveYears("5Y"), All("All") }

/** What the library list says about one album; the year can be missing, and so can the added date. */
data class AlbumStamp(val added: Instant?, val year: Int?)

/** One pass over the whole library list: the server's total and every album read. [complete] is true when the last page was reached. */
data class StatsRead(val total: Int?, val albums: List<AlbumStamp>, val complete: Boolean)

/** The collection line: points oldest first, the first period's start in words, and the total now. */
data class CollectionSeries(val points: List<ChartPoint>, val from: String, val total: Int)

data class DecadeShares(val rows: List<PairedRow>, val hasListens: Boolean)

object StatsRules {
    /** Pages read at most; a longer library says "not available" instead of charting part of it. */
    const val MAX_PAGES = 120
    const val ALL_MAX_BUCKETS = 60

    /** Contexts of the time-of-day lens in the order of a day, the order the chart draws. */
    val timeOfDayOrder = listOf("night", "morning", "afternoon", "evening")

    /** The shelf-life chart needs a last-played date per album; the phone has none. */
    const val SHELF_LIFE_UNAVAILABLE = "Not available yet. The phone has no last-played date for your albums."

    fun read(repo: LibraryRepository): StatsRead {
        val out = mutableListOf<AlbumStamp>()
        var total: Int? = null
        var cursor: String? = null
        repeat(MAX_PAGES) {
            val page = repo.albums("", AlbumSort.Added, true, cursor)
            if (total == null) total = page.total
            page.items.mapTo(out) { AlbumStamp(DashboardRules.parseAdded(it.added), it.year?.takeIf { y -> y > 0 }) }
            cursor = page.nextCursor ?: return StatsRead(total, out, complete = true)
        }
        return StatsRead(total, out, complete = false)
    }

    // ----- collection over time ------------------------------------------------------------------------------------

    private fun month(m: YearMonth, long: Boolean): String {
        val name = m.month.getDisplayName(TextStyle.SHORT, Locale.ENGLISH)
        return if (long) "$name ’${(m.year % 100).toString().padStart(2, '0')}" else name
    }

    private fun atEndOf(m: YearMonth, now: Instant): Instant =
        if (m == YearMonth.from(now.atZone(ZoneOffset.UTC))) now else m.plusMonths(1).atDay(1).atStartOfDay(ZoneOffset.UTC).toInstant()

    /** Albums in the library at the end of each bucket, counted back from the server's total by the added dates. */
    fun collection(read: StatsRead, range: StatsRange, now: Instant): CollectionSeries? {
        val total = read.total ?: return null
        if (!read.complete) return null
        val dates = read.albums.mapNotNull { it.added }
        if (dates.isEmpty()) return null
        fun owned(end: Instant) = (total - dates.count { it.isAfter(end) }).coerceAtLeast(0).toDouble()
        val current = YearMonth.from(now.atZone(ZoneOffset.UTC))

        if (range == StatsRange.ThreeMonths) {
            val ends = (12 downTo 0).map { now.minusSeconds(7L * 86_400 * it) }
            val points = ends.map { e ->
                val d = e.atZone(ZoneOffset.UTC).toLocalDate()
                ChartPoint("${d.dayOfMonth} ${d.month.getDisplayName(TextStyle.SHORT, Locale.ENGLISH)}", owned(e))
            }
            val first = ends.first().atZone(ZoneOffset.UTC).toLocalDate()
            return CollectionSeries(points, dateWords(first), total)
        }
        val (count, step) = when (range) {
            StatsRange.OneYear -> 12 to 1
            StatsRange.FiveYears -> 60 to 1
            else -> {
                val oldest = YearMonth.from(dates.min().atZone(ZoneOffset.UTC))
                val months = (oldest.until(current, java.time.temporal.ChronoUnit.MONTHS).toInt() + 1).coerceAtLeast(2)
                if (months > ALL_MAX_BUCKETS) Math.ceil(months / 3.0).toInt() to 3 else months to 1
            }
        }
        val months = (count - 1 downTo 0).map { current.minusMonths((it * step).toLong()) }
        val long = months.size > 12
        val points = months.map { ChartPoint(month(it, long), owned(atEndOf(it, now))) }
        return CollectionSeries(points, "${months.first().month.getDisplayName(TextStyle.SHORT, Locale.ENGLISH)} ${months.first().year}", total)
    }

    fun dateWords(d: LocalDate): String =
        "${d.dayOfMonth} ${d.month.getDisplayName(TextStyle.FULL, Locale.ENGLISH)} ${d.year}"

    fun collectionSubtitle(series: CollectionSeries) = "Albums in your library · ${series.from} to today"

    fun collectionState(series: CollectionSeries?, read: StatsRead?, loading: Boolean): ChartState = when {
        loading -> ChartState.Loading
        read == null || series == null -> when {
            read != null && read.total == null -> ChartState.Unavailable("The server did not say how many albums you have.")
            read != null && !read.complete -> ChartState.Unavailable("The library list is too long to read back in full, so the history is not charted.")
            read != null && read.albums.none { it.added != null } -> ChartState.Insufficient("No album has an added date yet.")
            else -> ChartState.Unavailable("The library list could not be read.")
        }
        else -> ChartState.Ready
    }

    // ----- own and play, by decade ---------------------------------------------------------------------------------

    fun decadeLabel(year: Int) = "${year / 10 * 10}s"

    /**
     * Share of albums by decade against the share of recent listens. The listen side is drawn only when the server's recent window
     * is sound for the era dimension; otherwise only the albums are shown, which [DecadeShares.hasListens] says.
     */
    fun decades(read: StatsRead?, taste: TasteProfiles?): DecadeShares? {
        val years = read?.albums?.mapNotNull { it.year }.orEmpty()
        if (years.isEmpty()) return null
        val owned = years.groupingBy { decadeLabel(it) }.eachCount()
        val window = taste?.window("recent")?.takeIf { !it.lowSample && !it.isLowSample("era") }
        val listens = window?.entries("era").orEmpty().takeIf { it.isNotEmpty() }?.associate { it.value to it.share }
        val labels = (owned.keys + listens?.keys.orEmpty()).sorted()
        return DecadeShares(
            labels.map { PairedRow(it, 100.0 * (owned[it] ?: 0) / years.size, 100.0 * (listens?.get(it) ?: 0.0)) },
            hasListens = listens != null,
        )
    }

    fun decadesSubtitle(shares: DecadeShares, recentDays: Int) =
        if (shares.hasListens) "Share of albums against share of listens, $recentDays days" else "Share of the albums you own · listens need more history"

    fun ownedRanked(shares: DecadeShares): List<RankedItem> =
        shares.rows.map { RankedItem(it.label, it.first, "${Math.round(it.first)}%") }

    // ----- when you listen -----------------------------------------------------------------------------------------

    /** Share of listens in each part of the day, in day order; null when the server has not served the context lens. */
    fun timeOfDay(counts: Map<String, Int>?): List<ChartPoint>? {
        if (counts == null) return null
        val total = timeOfDayOrder.sumOf { counts[it] ?: 0 }
        if (total <= 0) return emptyList()
        return timeOfDayOrder.map { name ->
            val share = 100.0 * (counts[name] ?: 0) / total
            ChartPoint(name.replaceFirstChar { it.uppercase() }, share, "${Math.round(share)}%")
        }
    }

    fun timeOfDayState(points: List<ChartPoint>?, loading: Boolean): ChartState = when {
        loading -> ChartState.Loading
        points == null -> ChartState.Unavailable("Not available yet. It arrives with the next taste refresh.")
        points.isEmpty() -> ChartState.Insufficient("No listens by time of day yet.")
        else -> ChartState.Ready
    }

    fun timeOfDaySubtitle(zone: String) = "Share of listens by time of day, $zone · all time"
}
