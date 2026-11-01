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
        val track = 2.dp.toPx()
        val x = inset + (size.width - 2 * inset) * fraction.coerceIn(0f, 1f)
        drawLine(Ink.Edge, Offset(inset, y), Offset(size.width - inset, y), strokeWidth = track, cap = StrokeCap.Round)
        drawLine(Ink.Accent, Offset(inset, y), Offset(x, y), strokeWidth = track, cap = StrokeCap.Round)
        drawCircle(if (enabled) Ink.Accent else Ink.EdgeStrong, radius.toPx(), Offset(x, y))
    }
}
