package app.discair.ui.common

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.layout.positionInParent
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.ui.theme.Ink

/**
 * Editor-style tabs (Uiverse, Vosoone): a flat strip with a hairline under it; the selected tab takes the page
 * colour, white text and a 2dp accent line along its bottom edge. A press stands in for hover. The accent is the
 * app's yellow where the original uses blue.
 */
@Composable
fun EditorTabs(labels: List<String>, selectedIndex: Int, onSelect: (Int) -> Unit, modifier: Modifier = Modifier) {
    val scroll = rememberScrollState()
    val lefts = remember(labels) { mutableStateMapOf<Int, Float>() }
    val widths = remember(labels) { mutableStateMapOf<Int, Float>() }
    // The strip follows the selection, so swiping to a tab that is off screen brings it into view.
    LaunchedEffect(selectedIndex, widths[selectedIndex]) {
        val left = lefts[selectedIndex] ?: return@LaunchedEffect
        val width = widths[selectedIndex] ?: return@LaunchedEffect
        scroll.animateScrollTo((left - (scroll.viewportSize - width) / 2f).toInt().coerceAtLeast(0))
    }
    Box(
        modifier.fillMaxWidth().background(Ink.Raised).drawBehind {
            drawLine(Ink.Edge, Offset(0f, size.height - 0.5f), Offset(size.width, size.height - 0.5f), 1.dp.toPx())
        },
    ) {
        Row(Modifier.horizontalScroll(scroll)) {
            labels.forEachIndexed { index, label ->
                val on = index == selectedIndex
                val source = remember { MutableInteractionSource() }
                val pressed by source.collectIsPressedAsState()
                Box(
                    Modifier.height(Target)
                        .onGloballyPositioned { lefts[index] = it.positionInParent().x; widths[index] = it.size.width.toFloat() }
                        .background(if (on) Ink.Ink else if (pressed) Ink.Surface else Color.Transparent)
                        .drawBehind {
                            if (on) drawLine(Ink.Accent, Offset(0f, size.height - 1.dp.toPx()), Offset(size.width, size.height - 1.dp.toPx()), 2.dp.toPx())
                        }
                        .clickable(source, indication = null, role = Role.Tab) { onSelect(index) }
                        .semantics { selected = on }
                        .padding(horizontal = 18.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(label, color = if (on || pressed) Color.White else Color.White.copy(alpha = 0.7f), fontSize = 13.sp, maxLines = 1)
                }
            }
        }
    }
}
