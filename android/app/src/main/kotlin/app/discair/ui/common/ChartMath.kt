package app.discair.ui.common

import app.discair.ui.theme.Family
import app.discair.ui.theme.Layout
import java.util.Locale
import kotlin.math.abs
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.log10
import kotlin.math.pow

/*
 * The pure half of the chart kit (docs/redesign.md 4.4 and 7.2, step A4): scales, slots, selection, per-family style,
 * states and the summary sentences TalkBack reads. Nothing here touches Compose, so it is unit-tested without a device.
 * Charts.kt draws what these functions decide.
 */

/** One plotted value with the words that name it ("Nov", "1990s") and its text form ("1,171", "38%"). */
data class ChartPoint(val label: String, val value: Double, val display: String = ChartRules.formatCount(value))

/** A row of two shares on one scale: albums owned and listens, both in percent. */
data class PairedRow(val label: String, val first: Double, val second: Double)

/** A before and after on one axis (a taste shift): the dumbbell's two ends. */
data class ShiftRow(val label: String, val from: Double, val to: Double)

/** A ranked bar: [value] sets the length, [display] is the text written beside it. */
data class RankedItem(val label: String, val value: Double, val display: String = ChartRules.formatCount(value))

/** What a chart shows instead of its plot (4.4: loading, not enough data, not available, stale). Each state has its own sentence. */
sealed interface ChartState {
    data object Ready : ChartState
    data object Loading : ChartState
    data class Insufficient(val sentence: String) : ChartState
    data class Unavailable(val sentence: String) : ChartState

    /** The last good chart stays at 50% under a warning that gives its date. */
    data class Stale(val sentence: String) : ChartState
}

/** How marks are drawn: soft (Classic), outlined with square ends (Brutal), or stepped meter segments (Tape). */
enum class MarkShape { Rounded, Outlined }

/** The per-family drawing rules of 7.3 ("Bars and columns", "Lines", "Tracker"). */
data class ChartStyle(
    val marks: MarkShape,
    val lineWidthDp: Float,
    /** A line chart fills under the line. */
    val area: Boolean,
    /** Tape draws lines as steps, not curves. */
    val steppedLine: Boolean,
    /** Tape draws columns as stacked meter segments. */
    val meterColumns: Boolean,
    /** Corner radius of a bar's far end, in dp. */
    val barRadiusDp: Float,
    /** The tracker's segment corner radius, in dp. */
    val segmentRadiusDp: Float,
)

object ChartRules {
    const val MAX_GRIDLINES = 4
    const val MIN_PLOT_HEIGHT_DP = 152
    const val METER_SEGMENT_DP = 8f
    const val STAGE_COUNT = 4

    /** Day and Night: rounded 3 dp tops, a 2 dp accent line (Day fills under it at 8%, Night does not). Tape and Sheet follow 7.3. */
    fun style(family: Family, layout: Layout, light: Boolean): ChartStyle = when {
        layout == Layout.TapeDeck -> ChartStyle(
            MarkShape.Outlined, 2f, area = true, steppedLine = true, meterColumns = true, barRadiusDp = 0f, segmentRadiusDp = 0f,
        )
        layout == Layout.SheetStack -> ChartStyle(
            MarkShape.Outlined, 3f, area = false, steppedLine = false, meterColumns = false, barRadiusDp = 0f, segmentRadiusDp = 0f,
        )
        family == Family.Brutal -> ChartStyle(
            MarkShape.Outlined, 2f, area = false, steppedLine = false, meterColumns = false, barRadiusDp = 0f, segmentRadiusDp = 0f,
        )
        else -> ChartStyle(
            MarkShape.Rounded, 2f, area = light, steppedLine = false, meterColumns = false, barRadiusDp = 3f, segmentRadiusDp = 2f,
        )
    }

    /** The area under a Day line is the accent at this share. */
    const val AREA_ALPHA = 0.08f

    /**
     * Gridline values for [min]..[max], at most [maxCount] of them, on 1, 2 or 5 times a power of ten. Bars and columns pass
     * min 0 and get a first tick at 0; a line may pass a min above zero. The last tick is never below [max].
     */
    fun niceTicks(min: Double, max: Double, maxCount: Int = MAX_GRIDLINES): List<Double> {
        if (maxCount < 2) return listOf(min)
        if (!(max > min)) return listOf(min)
        val rawStep = (max - min) / (maxCount - 1)
        val magnitude = 10.0.pow(floor(log10(rawStep)))
        val step = listOf(1.0, 2.0, 5.0, 10.0).map { it * magnitude }.first { it >= rawStep - 1e-9 }
        val start = floor(min / step) * step
        val end = ceil(max / step) * step
        val out = ArrayList<Double>()
        var v = start
        while (v <= end + step * 1e-6) {
            out += (v / step).let { Math.round(it) * step }
            v += step
        }
        return out
    }

    /** Where [value] sits on screen: [top] for [hi], [top] + [height] for [lo]. A flat domain draws mid-height. */
    fun scaleY(value: Double, lo: Double, hi: Double, top: Float, height: Float): Float {
        if (!(hi > lo)) return top + height / 2f
        val t = ((value - lo) / (hi - lo)).coerceIn(0.0, 1.0)
        return (top + height * (1.0 - t)).toFloat()
    }

    /** x for the [index]th of [count] points across [width], first at 0 and last at [width]. One point sits in the middle. */
    fun pointX(index: Int, count: Int, width: Float): Float =
        if (count <= 1) width / 2f else width * index / (count - 1)

    /** The point nearest to a touch at [x] across [width]; clamped, so a drag past the edge reads the first or last value. */
    fun nearestIndex(x: Float, width: Float, count: Int): Int {
        if (count <= 0) return -1
        if (count == 1 || width <= 0f) return 0
        return Math.round((x / width).coerceIn(0f, 1f) * (count - 1))
    }

    /** One slot of a column or bar chart: its left edge and the width of its mark. */
    data class Slot(val left: Float, val width: Float)

    /** [count] equal slots across [width]; the mark fills [fill] of its slot and is centred in it. */
    fun slots(count: Int, width: Float, fill: Float = 0.62f): List<Slot> {
        if (count <= 0 || width <= 0f) return emptyList()
        val slot = width / count
        val mark = slot * fill
        return List(count) { Slot(it * slot + (slot - mark) / 2f, mark) }
    }

    /** Bars and columns start at zero (4.4): the height of a mark for [value] against the top of the scale [hi], as 0..1. */
    fun barFraction(value: Double, hi: Double): Float = if (hi > 0.0) (value / hi).coerceIn(0.0, 1.0).toFloat() else 0f

    /** The top of a column chart's scale: the largest value, never below 1 so an all-zero chart still has a scale. */
    fun columnTop(values: List<Double>): Double = maxOf(values.maxOrNull() ?: 0.0, 1.0)

    /** The number of whole meter segments a column of [heightPx] holds, for Tape's stacked meter columns. */
    fun meterSegments(fraction: Float, plotHeightPx: Float, segmentPx: Float): Int =
        if (segmentPx <= 0f) 0 else floor(fraction * plotHeightPx / segmentPx).toInt()

    /** Index of the highest value, the one the accent marks in a column chart; the first on a tie; -1 when empty. */
    fun highlightIndex(values: List<Double>): Int {
        if (values.isEmpty()) return -1
        var best = 0
        for (i in 1 until values.size) if (values[i] > values[best]) best = i
        return best
    }

    /** The grown share of a mark at [progress] 0..1 with its own [index] delay: marks grow from the baseline, 30 ms apart. */
    fun staggeredProgress(progress: Float, index: Int, count: Int, staggerShare: Float = 0.25f): Float {
        if (count <= 1) return progress.coerceIn(0f, 1f)
        val delay = staggerShare * index / (count - 1)
        return ((progress - delay) / (1f - staggerShare)).coerceIn(0f, 1f)
    }

    /** Which end of a dumbbell is bigger decides its arrow: a share that rose is accent, one that fell is ink (never red and green). */
    fun rose(row: ShiftRow): Boolean = row.to > row.from

    // ----- tracker ------------------------------------------------------------------------------------------------

    enum class Stage { Done, Current, Pending, Failed }

    /**
     * The four-segment acquisition tracker (section 3): Found, Downloading, Importing, In library. [current] is the index of the
     * step in progress; 4 or more means all four are done. A failed record marks its current step failed and the rest pending.
     */
    fun stages(current: Int, failed: Boolean, count: Int = STAGE_COUNT): List<Stage> = List(count) { i ->
        when {
            i < current -> Stage.Done
            i == current && failed -> Stage.Failed
            i == current -> Stage.Current
            else -> Stage.Pending
        }
    }

    // ----- text ---------------------------------------------------------------------------------------------------

    /** 1171 -> "1,171". Whole numbers only; a fractional value keeps one decimal. */
    fun formatCount(value: Double): String =
        if (abs(value - Math.rint(value)) < 1e-9) String.format(Locale.US, "%,d", Math.round(value)) else String.format(Locale.US, "%,.1f", value)

    /** 38.0 -> "38%". Shares are whole percentages (section 3). */
    fun formatPercent(value: Double): String = "${Math.round(value)}%"

    /** The sentence a line chart reads to TalkBack: what it is, how many points, the range, the first and last value. */
    fun lineSummary(title: String, points: List<ChartPoint>): String {
        if (points.isEmpty()) return "$title. No data."
        val lo = points.minBy { it.value }
        val hi = points.maxBy { it.value }
        val first = points.first()
        val last = points.last()
        return "$title. ${points.size} points. From ${first.display} at ${first.label} to ${last.display} at ${last.label}. " +
            "Lowest ${lo.display} at ${lo.label}, highest ${hi.display} at ${hi.label}."
    }

    /** The sentence for columns and ranked bars: how many, the largest and the smallest. Each value is also reachable one by one. */
    fun barsSummary(title: String, items: List<ChartPoint>): String {
        if (items.isEmpty()) return "$title. No data."
        val hi = items.maxBy { it.value }
        val lo = items.minBy { it.value }
        return "$title. ${items.size} bars. Largest ${hi.label}, ${hi.display}. Smallest ${lo.label}, ${lo.display}."
    }

    fun pairedSummary(title: String, rows: List<PairedRow>, firstName: String, secondName: String): String {
        if (rows.isEmpty()) return "$title. No data."
        val widest = rows.maxBy { abs(it.first - it.second) }
        return "$title. ${rows.size} rows of $firstName against $secondName. Largest gap: ${widest.label}, " +
            "${formatPercent(widest.first)} against ${formatPercent(widest.second)}."
    }

    fun shiftSummary(title: String, rows: List<ShiftRow>): String {
        if (rows.isEmpty()) return "$title. No shifts."
        return "$title. " + rows.joinToString(" ") {
            "${it.label} ${if (rose(it)) "rose" else "fell"} from ${formatPercent(it.from)} to ${formatPercent(it.to)}."
        }
    }

    /** The label of a tracker segment for a screen reader: "Downloading, current". */
    fun stageLabel(name: String, stage: Stage): String = when (stage) {
        Stage.Done -> "$name, done"
        Stage.Current -> "$name, in progress"
        Stage.Pending -> "$name, waiting"
        Stage.Failed -> "$name, failed"
    }

    /** The selected value written above the plot while a finger is down (a tooltip would sit under it). */
    fun selectedText(point: ChartPoint): String = "${point.display} · ${point.label}"
}
