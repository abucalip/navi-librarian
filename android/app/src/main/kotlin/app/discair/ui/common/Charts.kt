package app.discair.ui.common

import androidx.compose.animation.core.Animatable
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.clipRect
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.CustomAccessibilityAction
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.customActions
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.TextMeasurer
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.MotionRole
import app.discair.ui.theme.MotionRules
import app.discair.ui.theme.MotionTokens
import app.discair.ui.theme.Palette
import app.discair.ui.theme.currentMotionFamily
import app.discair.ui.theme.rememberReducedMotion
import app.discair.ui.theme.toTween
import kotlin.math.abs

/*
 * The chart kit (docs/redesign.md 4.4, 7.2 and 7.3, step A4), drawn on Compose Canvas: line, columns, paired bars, dumbbell,
 * ranked bars and the acquisition tracker. Every chart takes a [ChartState]; a chart that is not Ready shows its own sentence
 * and never a zero or a blank. The marks follow the theme's family through [ChartRules.style]. What is measured and decided
 * lives in ChartMath.kt.
 */

private val AxisWidth = 48.dp
private val TimeAxisHeight = 24.dp
private val SelectionHeader = 28.dp

@Composable
private fun chartStyle(): ChartStyle {
    val p = LocalPalette.current
    return ChartRules.style(p.family, p.layout, p.light)
}

/** Marks grow from the baseline over `emphasis`, or are fully grown at once when the phone reduces motion. Restarts when [key] changes. */
@Composable
private fun rememberDrawIn(key: Any?): Float {
    val reduced = rememberReducedMotion()
    val family = currentMotionFamily()
    val progress = remember(key) { Animatable(if (reduced) 1f else 0f) }
    LaunchedEffect(key, reduced) {
        if (reduced) progress.snapTo(1f)
        else progress.animateTo(1f, MotionRules.timing(MotionTokens.EMPHASIS_MS, MotionRole.Arrive, family, false).toTween())
    }
    return progress.value
}

/**
 * The frame every chart shares: the title in the heading style, the subtitle (unit, source, exact period), then the plot or the
 * sentence for its state. [summary] is the label a screen reader gets for the whole chart.
 */
@Composable
fun ChartFrame(
    title: String,
    subtitle: String,
    state: ChartState,
    plotHeight: Dp,
    modifier: Modifier = Modifier,
    legend: @Composable (() -> Unit)? = null,
    content: @Composable () -> Unit,
) {
    val p = LocalPalette.current
    Column(modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(title, style = MaterialTheme.typography.titleMedium, color = p.text)
        Text(subtitle, style = MaterialTheme.typography.bodySmall, color = p.textMuted)
        Box(Modifier.padding(top = 8.dp).fillMaxWidth().height(maxOf(plotHeight, ChartRules.MIN_PLOT_HEIGHT_DP.dp))) {
            when (state) {
                ChartState.Ready -> content()
                ChartState.Loading -> Box(
                    Modifier.fillMaxSize().clip(RoundedCornerShape(8.dp)).background(p.chartGhost)
                        .semantics { contentDescription = "$title is loading" },
                )
                is ChartState.Insufficient -> StateSentence(state.sentence, ghostLine = true)
                is ChartState.Unavailable -> StateSentence(state.sentence, ghostLine = false)
                is ChartState.Stale -> Column {
                    Text(
                        "▲ ${state.sentence}", style = MaterialTheme.typography.bodySmall, color = p.caution,
                        modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(8.dp)).background(p.cautionDim).padding(8.dp),
                    )
                    Box(Modifier.alpha(0.5f).weight(1f)) { content() }
                }
            }
        }
        legend?.invoke()
    }
}

@Composable
private fun StateSentence(sentence: String, ghostLine: Boolean) {
    val p = LocalPalette.current
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        if (ghostLine) {
            Canvas(Modifier.fillMaxSize()) {
                val y = size.height * 0.55f
                drawLine(
                    p.chartGhost, Offset(0f, y), Offset(size.width, y), strokeWidth = 2.dp.toPx(),
                    cap = StrokeCap.Round, pathEffect = PathEffect.dashPathEffect(floatArrayOf(2.dp.toPx(), 8.dp.toPx())),
                )
            }
        }
        Text(
            sentence, style = MaterialTheme.typography.bodyMedium, color = p.text,
            modifier = Modifier.padding(horizontal = 16.dp).background(p.surface.copy(alpha = 0.85f)).padding(8.dp),
        )
    }
}

/** Legend, only when two series exist: under the plot, leading-aligned, in the mono face. */
@Composable
fun ChartLegend(first: String, second: String, firstColor: Color, secondColor: Color) {
    val p = LocalPalette.current
    Row(Modifier.padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.CenterVertically) {
        for ((name, color) in listOf(first to firstColor, second to secondColor)) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.width(12.dp).height(4.dp).clip(RoundedCornerShape(2.dp)).background(color))
                Text(name, style = MaterialTheme.typography.labelSmall, color = p.textMuted)
            }
        }
    }
}

// ----- shared drawing ---------------------------------------------------------------------------------------------

private fun DrawScope.axisLabel(measurer: TextMeasurer, text: String, style: TextStyle, color: Color, x: Float, centerY: Float, alignEnd: Boolean = false) {
    val layout = measurer.measure(text, style)
    val left = if (alignEnd) x - layout.size.width else x
    drawText(layout, color, Offset(left, centerY - layout.size.height / 2f))
}

private fun DrawScope.gridlines(
    p: Palette, measurer: TextMeasurer, labelStyle: TextStyle, ticks: List<Double>, lo: Double, hi: Double,
    plotWidth: Float, plotHeight: Float, format: (Double) -> String,
) {
    for (t in ticks) {
        val y = ChartRules.scaleY(t, lo, hi, 0f, plotHeight)
        val base = t == lo && lo == 0.0
        drawLine(if (base) p.chartBase else p.chartGrid, Offset(0f, y), Offset(plotWidth, y), strokeWidth = 1.dp.toPx())
        axisLabel(measurer, format(t), labelStyle, p.textMuted, plotWidth + 8.dp.toPx(), y)
    }
}

/** Selection by touch: tap or drag along the plot picks the nearest point. Horizontal only, so the page still scrolls up and down. */
private fun Modifier.selectByTouch(count: Int, onSelect: (Int) -> Unit): Modifier = this
    .pointerInput(count) { detectTapGestures { onSelect(ChartRules.nearestIndex(it.x, size.width.toFloat(), count)) } }
    .pointerInput(count) {
        detectHorizontalDragGestures(
            onDragStart = { onSelect(ChartRules.nearestIndex(it.x, size.width.toFloat(), count)) },
            onHorizontalDrag = { change, _ ->
                change.consume()
                onSelect(ChartRules.nearestIndex(change.position.x, size.width.toFloat(), count))
            },
        )
    }

/** What TalkBack reads: the summary, the selected value as state, and "Previous value" and "Next value" actions to step through. */
private fun Modifier.chartSemantics(summary: String, selected: String?, count: Int, index: Int, onSelect: (Int) -> Unit): Modifier =
    this.semantics {
        contentDescription = summary
        if (selected != null) stateDescription = selected
        if (count > 1) customActions = listOf(
            CustomAccessibilityAction("Next value") { onSelect((index + 1).coerceAtMost(count - 1)); true },
            CustomAccessibilityAction("Previous value") { onSelect((index - 1).coerceAtLeast(0)); true },
        )
    }

// ----- line -------------------------------------------------------------------------------------------------------

/**
 * A line over time. The value axis has labels only, on the trailing side; gridlines are horizontal, at most four. The time axis
 * shows [timeLabelCount] labels, the first leading-aligned and the last trailing-aligned. Touch and drag select a value, which is
 * written above the plot. [previous], when given, is the period before, drawn as a dashed line in the comparison colour.
 */
@Composable
fun LineChart(
    title: String,
    subtitle: String,
    points: List<ChartPoint>,
    modifier: Modifier = Modifier,
    state: ChartState = ChartState.Ready,
    previous: List<Double>? = null,
    timeLabelCount: Int = 5,
    plotHeight: Dp = ChartRules.MIN_PLOT_HEIGHT_DP.dp,
) {
    val p = LocalPalette.current
    val style = chartStyle()
    val measurer = rememberTextMeasurer()
    val labelStyle = MaterialTheme.typography.labelSmall
    var selected by remember(points) { mutableIntStateOf(-1) }
    val grow = rememberDrawIn(points)
    val summary = ChartRules.lineSummary(title, points)
    val selectedPoint = points.getOrNull(selected)

    ChartFrame(title, subtitle, state, plotHeight + SelectionHeader + TimeAxisHeight, modifier) {
        Column(Modifier.fillMaxSize()) {
            Box(Modifier.height(SelectionHeader), contentAlignment = Alignment.CenterStart) {
                Text(
                    selectedPoint?.let(ChartRules::selectedText) ?: "Touch and drag the chart to read a date.",
                    style = MaterialTheme.typography.labelMedium, color = if (selectedPoint != null) p.text else p.textMuted,
                )
            }
            val values = points.map { it.value } + (previous ?: emptyList())
            val rawLo = values.minOrNull() ?: 0.0
            val rawHi = values.maxOrNull() ?: 1.0
            val ticks = ChartRules.niceTicks(rawLo, rawHi)
            val lo = ticks.first()
            val hi = ticks.last()
            Canvas(
                Modifier.fillMaxSize()
                    .selectByTouch(points.size) { selected = it }
                    .chartSemantics(summary, selectedPoint?.let(ChartRules::selectedText), points.size, selected) { selected = it },
            ) {
                val axisPx = AxisWidth.toPx()
                val plotW = size.width - axisPx
                val plotH = size.height - TimeAxisHeight.toPx()
                gridlines(p, measurer, labelStyle, ticks, lo, hi, plotW, plotH, ChartRules::formatCount)
                // Time axis: first label leading, last trailing, the rest centred under their point.
                val n = points.size
                val labelCount = minOf(timeLabelCount, n)
                for (k in 0 until labelCount) {
                    val i = if (labelCount == 1) 0 else Math.round(k * (n - 1) / (labelCount - 1).toFloat())
                    val x = ChartRules.pointX(i, n, plotW)
                    val layout = measurer.measure(points[i].label, labelStyle)
                    val left = when (k) {
                        0 -> 0f
                        labelCount - 1 -> plotW - layout.size.width
                        else -> x - layout.size.width / 2f
                    }
                    drawText(layout, p.textMuted, Offset(left, plotH + 6.dp.toPx()))
                }
                fun path(vals: List<Double>, closeToBase: Boolean): Path = Path().apply {
                    vals.forEachIndexed { i, v ->
                        val x = ChartRules.pointX(i, vals.size, plotW)
                        val y = ChartRules.scaleY(v, lo, hi, 0f, plotH)
                        when {
                            i == 0 -> { if (closeToBase) { moveTo(x, plotH); lineTo(x, y) } else moveTo(x, y) }
                            style.steppedLine -> { lineTo(x, ChartRules.scaleY(vals[i - 1], lo, hi, 0f, plotH)); lineTo(x, y) }
                            else -> lineTo(x, y)
                        }
                    }
                    if (closeToBase) { lineTo(ChartRules.pointX(vals.size - 1, vals.size, plotW), plotH); close() }
                }
                clipRect(left = 0f, top = 0f, right = plotW * grow, bottom = plotH + 2.dp.toPx()) {
                    if (previous != null && previous.size > 1) {
                        drawPath(
                            path(previous, false), p.chart2,
                            style = Stroke(1.5.dp.toPx(), pathEffect = PathEffect.dashPathEffect(floatArrayOf(6.dp.toPx(), 4.dp.toPx()))),
                        )
                    }
                    if (points.size > 1) {
                        if (style.area) drawPath(path(points.map { it.value }, true), p.chart1.copy(alpha = if (p.layout == app.discair.ui.theme.Layout.TapeDeck) 0.35f else ChartRules.AREA_ALPHA))
                        drawPath(
                            path(points.map { it.value }, false), p.chart1,
                            style = Stroke(style.lineWidthDp.dp.toPx(), cap = StrokeCap.Round, join = if (style.steppedLine) StrokeJoin.Miter else StrokeJoin.Round),
                        )
                    }
                }
                if (selected in points.indices) {
                    val x = ChartRules.pointX(selected, n, plotW)
                    val y = ChartRules.scaleY(points[selected].value, lo, hi, 0f, plotH)
                    drawLine(p.text, Offset(x, 0f), Offset(x, plotH), strokeWidth = 1.dp.toPx())
                    drawCircle(p.surface, 6.5f.dp.toPx(), Offset(x, y))
                    drawCircle(p.chart1, 5.dp.toPx(), Offset(x, y))
                }
            }
        }
    }
}

// ----- columns ----------------------------------------------------------------------------------------------------

private fun DrawScope.mark(
    p: Palette, style: ChartStyle, color: Color, left: Float, top: Float, width: Float, height: Float,
) {
    if (height <= 0f) return
    val radius = CornerRadius(style.barRadiusDp.dp.toPx())
    if (style.marks == MarkShape.Rounded) {
        // Rounded 3 dp tops only: a rounded rectangle taller than the radius, with its foot squared off.
        drawRoundRect(color, Offset(left, top), Size(width, height), radius)
        if (height > radius.y) drawRect(color, Offset(left, top + height - radius.y), Size(width, radius.y))
    } else {
        drawRect(color, Offset(left, top), Size(width, height))
        drawRect(p.edgeStrong, Offset(left, top), Size(width, height), style = Stroke(2.dp.toPx()))
    }
}

/**
 * Columns from a zero baseline. The tallest column is the accent and the rest are context. Values are written above the
 * columns and the labels sit beneath them in the mono face. Tape draws each column as stacked meter segments.
 */
@Composable
fun ColumnChart(
    title: String,
    subtitle: String,
    items: List<ChartPoint>,
    modifier: Modifier = Modifier,
    state: ChartState = ChartState.Ready,
    highlight: Int = ChartRules.highlightIndex(items.map { it.value }),
    plotHeight: Dp = 184.dp,
) {
    val p = LocalPalette.current
    val style = chartStyle()
    val measurer = rememberTextMeasurer()
    val labelStyle = MaterialTheme.typography.labelSmall
    val grow = rememberDrawIn(items)
    val summary = ChartRules.barsSummary(title, items)
    var selected by remember(items) { mutableIntStateOf(-1) }
    val top = ChartRules.columnTop(items.map { it.value })
    ChartFrame(title, subtitle, state, plotHeight + TimeAxisHeight, modifier) {
        Canvas(
            Modifier.fillMaxSize()
                .selectByTouch(items.size) { selected = it }
                .chartSemantics(summary, items.getOrNull(selected)?.let(ChartRules::selectedText), items.size, selected) { selected = it },
        ) {
            val labelH = TimeAxisHeight.toPx()
            val valueH = 20.dp.toPx()
            val plotH = size.height - labelH
            val usable = plotH - valueH
            val slots = ChartRules.slots(items.size, size.width)
            drawLine(p.chartBase, Offset(0f, plotH), Offset(size.width, plotH), strokeWidth = 1.dp.toPx())
            items.forEachIndexed { i, item ->
                val slot = slots[i]
                val fraction = ChartRules.barFraction(item.value, top) * ChartRules.staggeredProgress(grow, i, items.size)
                val h = usable * fraction
                val color = if (i == highlight) p.chart1 else p.chart3
                if (style.meterColumns) {
                    val seg = ChartRules.METER_SEGMENT_DP.dp.toPx()
                    val count = ChartRules.meterSegments(fraction, usable, seg)
                    for (s in 0 until count) mark(p, style, color, slot.left, plotH - (s + 1) * seg + 1.dp.toPx(), slot.width, seg - 2.dp.toPx())
                } else mark(p, style, color, slot.left, plotH - h, slot.width, h)
                val cx = slot.left + slot.width / 2f
                val value = measurer.measure(item.display, labelStyle)
                drawText(value, if (i == highlight || i == selected) p.text else p.textMuted, Offset(cx - value.size.width / 2f, plotH - h - value.size.height - 4.dp.toPx()))
                val label = measurer.measure(item.label, labelStyle)
                drawText(label, if (i == selected) p.text else p.textMuted, Offset(cx - label.size.width / 2f, plotH + 6.dp.toPx()))
            }
        }
    }
}

// ----- paired bars ------------------------------------------------------------------------------------------------

/**
 * Two shares per row on one scale: what you own against what you play. The second bar is the accent, the first the context
 * colour; [selected] row is drawn in full accent with its label in text colour. Values are written at the end of each row.
 */
@Composable
fun PairedBars(
    title: String,
    subtitle: String,
    rows: List<PairedRow>,
    firstName: String,
    secondName: String,
    modifier: Modifier = Modifier,
    state: ChartState = ChartState.Ready,
    selected: Int = rows.indices.maxByOrNull { abs(rows[it].first - rows[it].second) } ?: -1,
) {
    val p = LocalPalette.current
    val style = chartStyle()
    val grow = rememberDrawIn(rows)
    val top = maxOf(rows.maxOfOrNull { maxOf(it.first, it.second) } ?: 0.0, 1.0)
    ChartFrame(
        title, subtitle, state, (rows.size * 40).dp, modifier,
        legend = { ChartLegend(firstName, secondName, p.chart3, p.chart1) },
    ) {
        Column(
            Modifier.fillMaxSize().semantics { contentDescription = ChartRules.pairedSummary(title, rows, firstName, secondName) },
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            rows.forEachIndexed { i, row ->
                Row(Modifier.fillMaxWidth().height(32.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        row.label, style = MaterialTheme.typography.labelMedium, color = if (i == selected) p.text else p.textMuted,
                        modifier = Modifier.width(56.dp),
                    )
                    Canvas(Modifier.weight(1f).fillMaxSize()) {
                        val barH = 8.dp.toPx()
                        val f1 = ChartRules.barFraction(row.first, top) * ChartRules.staggeredProgress(grow, i, rows.size)
                        val f2 = ChartRules.barFraction(row.second, top) * ChartRules.staggeredProgress(grow, i, rows.size)
                        val y1 = size.height / 2f - barH - 1.dp.toPx()
                        val y2 = size.height / 2f + 1.dp.toPx()
                        val second = if (i == selected) p.chart1 else p.chart1.copy(alpha = 0.55f)
                        drawBar(p, style, p.chart3, y1, size.width * f1, barH)
                        drawBar(p, style, second, y2, size.width * f2, barH)
                    }
                    Column(Modifier.width(48.dp).padding(start = 8.dp), horizontalAlignment = Alignment.End) {
                        val weight = if (i == selected) p.text else p.textMuted
                        Text(ChartRules.formatPercent(row.first), style = MaterialTheme.typography.labelSmall, color = p.textMuted)
                        Text(ChartRules.formatPercent(row.second), style = MaterialTheme.typography.labelSmall, color = weight)
                    }
                }
            }
        }
    }
}

private fun DrawScope.drawBar(p: Palette, style: ChartStyle, color: Color, y: Float, width: Float, height: Float) {
    if (width <= 0f) return
    if (style.marks == MarkShape.Rounded) drawRoundRect(color, Offset(0f, y), Size(width, height), CornerRadius(height / 2f))
    else {
        drawRect(color, Offset(0f, y), Size(width, height))
        drawRect(p.edgeStrong, Offset(0f, y), Size(width, height), style = Stroke(2.dp.toPx()))
    }
}

// ----- dumbbell ---------------------------------------------------------------------------------------------------

/**
 * Before and after for each listed shift, on one 0 to 100 scale: a hollow dot for lately's baseline, a filled one for now. A
 * share that rose is the accent, one that fell is ink, and each carries an arrow word, so colour never carries it alone.
 */
@Composable
fun Dumbbell(
    title: String,
    subtitle: String,
    rows: List<ShiftRow>,
    modifier: Modifier = Modifier,
    state: ChartState = ChartState.Ready,
) {
    val p = LocalPalette.current
    val grow = rememberDrawIn(rows)
    ChartFrame(title, subtitle, state, (rows.size * 48).dp, modifier) {
        Column(
            Modifier.fillMaxSize().semantics { contentDescription = ChartRules.shiftSummary(title, rows) },
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            rows.forEach { row ->
                val rose = ChartRules.rose(row)
                val color = if (rose) p.chart1 else p.text
                Column(Modifier.fillMaxWidth().height(40.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(row.label, style = MaterialTheme.typography.bodyMedium, color = p.text)
                        Text(
                            "${if (rose) "↑" else "↓"} ${ChartRules.formatPercent(row.from)} → ${ChartRules.formatPercent(row.to)}",
                            style = MaterialTheme.typography.labelMedium, color = color,
                        )
                    }
                    Canvas(Modifier.fillMaxWidth().height(16.dp)) {
                        val r = 5.dp.toPx()
                        val w = size.width - 2 * r
                        val x1 = r + w * (row.from / 100.0).coerceIn(0.0, 1.0).toFloat()
                        val x2 = r + w * (row.to / 100.0).coerceIn(0.0, 1.0).toFloat()
                        val xNow = x1 + (x2 - x1) * grow
                        val cy = size.height / 2f
                        drawLine(p.chartGhost, Offset(r, cy), Offset(size.width - r, cy), strokeWidth = 2.dp.toPx(), cap = StrokeCap.Round)
                        drawLine(color, Offset(x1, cy), Offset(xNow, cy), strokeWidth = 2.dp.toPx(), cap = StrokeCap.Round)
                        drawCircle(p.chart2, r, Offset(x1, cy), style = Stroke(2.dp.toPx()))
                        drawCircle(color, r, Offset(xNow, cy))
                    }
                }
            }
        }
    }
}

// ----- ranked bars ------------------------------------------------------------------------------------------------

/** Sorted horizontal bars, 10 dp on a ghost track, the top one in the accent. For parts of a whole with more than three parts. */
@Composable
fun RankedBars(
    title: String,
    subtitle: String,
    items: List<RankedItem>,
    modifier: Modifier = Modifier,
    state: ChartState = ChartState.Ready,
) {
    val p = LocalPalette.current
    val style = chartStyle()
    val grow = rememberDrawIn(items)
    val sorted = items.sortedByDescending { it.value }
    val top = maxOf(sorted.firstOrNull()?.value ?: 0.0, 1.0)
    ChartFrame(title, subtitle, state, (sorted.size * 40).dp, modifier) {
        Column(
            Modifier.fillMaxSize().semantics {
                contentDescription = ChartRules.barsSummary(title, sorted.map { ChartPoint(it.label, it.value, it.display) })
            },
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            sorted.forEachIndexed { i, item ->
                Column(Modifier.fillMaxWidth()) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(item.label, style = MaterialTheme.typography.bodyMedium, color = p.text)
                        Text(item.display, style = MaterialTheme.typography.labelMedium, color = p.textMuted)
                    }
                    Canvas(Modifier.fillMaxWidth().height(14.dp).padding(top = 4.dp)) {
                        val h = 10.dp.toPx()
                        val radius = if (style.marks == MarkShape.Rounded) CornerRadius(h / 2f) else CornerRadius(0f)
                        drawRoundRect(p.chartGhost, Offset.Zero, Size(size.width, h), radius)
                        val w = size.width * ChartRules.barFraction(item.value, top) * ChartRules.staggeredProgress(grow, i, sorted.size)
                        drawBar(p, style, if (i == 0) p.chart1 else p.chart3, 0f, w, h)
                    }
                }
            }
        }
    }
}

// ----- tracker ----------------------------------------------------------------------------------------------------

/**
 * The acquisition tracker (section 3): four segments named Found, Downloading, Importing, In library. Done segments are text
 * colour, the current one is the accent filled to [progress], a failed one is danger. State is also written in words for a
 * screen reader; the caller puts the server's reason beside it for a failure.
 */
@Composable
fun StageTracker(
    current: Int,
    modifier: Modifier = Modifier,
    failed: Boolean = false,
    progress: Float = 0f,
    names: List<String> = listOf("Found", "Downloading", "Importing", "In library"),
) {
    val p = LocalPalette.current
    val style = chartStyle()
    val stages = ChartRules.stages(current, failed, names.size)
    val shape = RoundedCornerShape(style.segmentRadiusDp.dp)
    Column(
        modifier.fillMaxWidth().semantics {
            contentDescription = names.indices.joinToString(". ") { ChartRules.stageLabel(names[it], stages[it]) }
        },
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            stages.forEach { stage ->
                val outlined = style.marks == MarkShape.Outlined
                Box(
                    Modifier.weight(1f).height(if (outlined) 8.dp else 4.dp)
                        .clip(shape).background(p.chartGhost)
                        .then(if (outlined) Modifier.border(2.dp, p.edgeStrong, shape) else Modifier),
                ) {
                    val fill = when (stage) {
                        ChartRules.Stage.Done -> 1f to p.text
                        ChartRules.Stage.Current -> progress.coerceIn(0.08f, 1f) to p.chart1
                        ChartRules.Stage.Failed -> 1f to p.chartRedText
                        ChartRules.Stage.Pending -> 0f to p.chartGhost
                    }
                    Box(Modifier.fillMaxSize().fillFraction(fill.first).background(fill.second))
                }
            }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            names.forEachIndexed { i, name ->
                Text(
                    name, modifier = Modifier.weight(1f), style = MaterialTheme.typography.labelSmall,
                    color = when (stages[i]) {
                        ChartRules.Stage.Failed -> p.chartRedText
                        ChartRules.Stage.Pending -> p.textMuted
                        else -> p.text
                    },
                )
            }
        }
    }
}

private fun Modifier.fillFraction(f: Float): Modifier = this.then(Modifier.fillMaxWidth(f.coerceIn(0f, 1f)))
