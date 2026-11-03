package app.discair.ui.player

import androidx.compose.animation.core.animateDpAsState
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.drag
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.disabled
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import app.discair.ui.theme.Ink

private val Thumb = 4.dp
private val ThumbActive = 12.dp

/**
 * A thin progress bar with a small yellow dot. The dot grows while it is touched or dragged and
 * shrinks back afterwards. The touch area stays 48dp tall so the bar is still easy to hit.
 */
@Composable
fun SeekBar(fraction: Float, enabled: Boolean, onChange: (Float) -> Unit, onFinish: () -> Unit, modifier: Modifier = Modifier) {
    var active by remember { mutableStateOf(false) }
    val radius by animateDpAsState(if (active) ThumbActive else Thumb, label = "seekThumb")
    val pad = ThumbActive
    val palette = app.discair.ui.theme.LocalPalette.current
    val trackColor = Ink.Edge
    val fill = Ink.Accent
    val dot = if (enabled) Ink.Accent else Ink.EdgeStrong
    Canvas(
        modifier.fillMaxWidth().height(48.dp)
            .semantics { if (!enabled) disabled() }
            .pointerInput(enabled) {
                if (!enabled) return@pointerInput
                val inset = pad.toPx()
                fun at(x: Float) = ((x - inset) / (size.width - 2 * inset).coerceAtLeast(1f)).coerceIn(0f, 1f)
                awaitEachGesture {
                    val down = awaitFirstDown()
                    down.consume()
                    active = true
                    onChange(at(down.position.x))
                    drag(down.id) { change -> change.consume(); onChange(at(change.position.x)) }
                    active = false
                    onFinish()
                }
            },
    ) {
        val inset = pad.toPx()
        val y = size.height / 2
        if (palette.layout == app.discair.ui.theme.Layout.TapeDeck) {
            // Cassette Deck: a ruled track with a mark every tenth, the played part filled with the accent, and a tall bar as the thumb.
            val outline = (palette.shape?.outline ?: 2).dp.toPx()
            val h = 18.dp.toPx()
            val left = inset
            val width = size.width - 2 * inset
            val x = left + width * fraction.coerceIn(0f, 1f)
            val top = y - h / 2
            drawRect(palette.surface, Offset(left, top), androidx.compose.ui.geometry.Size(width, h))
            drawRect(palette.accent, Offset(left, top), androidx.compose.ui.geometry.Size((x - left).coerceAtLeast(0f), h))
            for (tick in app.discair.ui.common.TapeDeckRules.seekTicks(10)) {
                val tx = left + width * tick
                drawLine(palette.edgeStrong, Offset(tx, top + h * 0.55f), Offset(tx, top + h), strokeWidth = (outline / 2).coerceAtLeast(1f))
            }
            drawRect(palette.edgeStrong, Offset(left, top), androidx.compose.ui.geometry.Size(width, h), style = androidx.compose.ui.graphics.drawscope.Stroke(outline))
            val tw = (if (active) 8.dp else 6.dp).toPx()
            val th = 30.dp.toPx()
            drawRect(palette.edgeStrong, Offset(x - tw / 2, y - th / 2), androidx.compose.ui.geometry.Size(tw, th))
            return@Canvas
        }
        if (palette.brutal) {
            // Neobrut: an outlined track (thin, like the reference) with the accent for the played part, and a square
            // outlined thumb with a hard shadow that grows a little while it is held.
            val outline = (palette.shape?.outline ?: 2).dp.toPx()
            val h = 14.dp.toPx()
            val corner = androidx.compose.ui.geometry.CornerRadius(minOf(palette.shape?.radius ?: 0, 3).dp.toPx())
            val left = inset
            val width = size.width - 2 * inset
            val x = left + width * fraction.coerceIn(0f, 1f)
            drawRoundRect(palette.surface, Offset(left, y - h / 2), androidx.compose.ui.geometry.Size(width, h), corner)
            drawRoundRect(palette.accent, Offset(left, y - h / 2), androidx.compose.ui.geometry.Size((x - left).coerceAtLeast(0f), h), corner)
            drawRoundRect(palette.edgeStrong, Offset(left, y - h / 2), androidx.compose.ui.geometry.Size(width, h), corner, style = androidx.compose.ui.graphics.drawscope.Stroke(outline))
            val t = (if (active) 26.dp else 22.dp).toPx()
            val sh = ((palette.shape?.shadow ?: 0) * 0.5f).dp.toPx()
            val tl = Offset(x - t / 2, y - t / 2)
            drawRoundRect(palette.shadowColor, Offset(tl.x + sh, tl.y + sh), androidx.compose.ui.geometry.Size(t, t), corner)
            drawRoundRect(if (enabled) palette.surface else palette.raised, tl, androidx.compose.ui.geometry.Size(t, t), corner)
            drawRoundRect(palette.edgeStrong, tl, androidx.compose.ui.geometry.Size(t, t), corner, style = androidx.compose.ui.graphics.drawscope.Stroke(outline))
            return@Canvas
        }
        val track = 2.dp.toPx()
        val x = inset + (size.width - 2 * inset) * fraction.coerceIn(0f, 1f)
        drawLine(trackColor, Offset(inset, y), Offset(size.width - inset, y), strokeWidth = track, cap = StrokeCap.Round)
        drawLine(fill, Offset(inset, y), Offset(x, y), strokeWidth = track, cap = StrokeCap.Round)
        drawCircle(dot, radius.toPx(), Offset(x, y))
    }
}
