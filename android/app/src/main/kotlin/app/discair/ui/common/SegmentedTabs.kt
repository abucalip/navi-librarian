package app.discair.ui.common

import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.ScrollState
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.layout.positionInParent
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.ui.theme.Ink

private val TrackShape = RoundedCornerShape(9.dp)
private val ThumbShape = RoundedCornerShape(7.dp)
private val Thumb = Color(0xFF3A3632)

/**
 * The segmented tab control (Uiverse, zanina-yassine) in the app's palette: a rounded dark track with a
 * raised thumb that slides under the selected label. The tabs are as wide as their words, so more fit on a
 * screen; when they still do not all fit the track scrolls, and follows the selection. The selected label is
 * white and full strength, the others are white at 60%; the selected tab is also announced as selected.
 */
@Composable
fun SegmentedTabs(
    labels: List<String>,
    selectedIndex: Int,
    onSelect: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val scroll: ScrollState = rememberScrollState()
    val density = LocalDensity.current
    // Each tab's left edge and width inside the track, in dp, as laid out.
    val lefts = remember(labels) { mutableStateMapOf<Int, Float>() }
    val widths = remember(labels) { mutableStateMapOf<Int, Float>() }
    val thumbX by animateDpAsState(with(density) { (lefts[selectedIndex] ?: 0f).toDp() }, tween(200), label = "thumbX")
    val thumbW by animateDpAsState(with(density) { (widths[selectedIndex] ?: 0f).toDp() }, tween(200), label = "thumbW")
    LaunchedEffect(selectedIndex, widths[selectedIndex]) {
        val left = lefts[selectedIndex] ?: return@LaunchedEffect
        val width = widths[selectedIndex] ?: return@LaunchedEffect
        scroll.animateScrollTo((left - (scroll.viewportSize - width) / 2f).toInt().coerceAtLeast(0))
    }
    Box(
        modifier.clip(TrackShape).background(Ink.Raised).border(BorderStroke(0.5.dp, Ink.Edge), TrackShape),
    ) {
        Box(Modifier.horizontalScroll(scroll).padding(2.dp)) {
            if (widths[selectedIndex] != null) Box(
                Modifier.offset(x = thumbX).width(thumbW).height(Target - 4.dp)
                    .shadow(3.dp, ThumbShape).clip(ThumbShape).background(Thumb)
                    .border(BorderStroke(0.5.dp, Ink.EdgeStrong.copy(alpha = 0.5f)), ThumbShape),
            )
            Row {
                labels.forEachIndexed { index, label ->
                    val on = index == selectedIndex
                    Box(
                        Modifier
                            .onGloballyPositioned {
                                lefts[index] = it.positionInParent().x
                                widths[index] = it.size.width.toFloat()
                            }
                            .height(Target - 4.dp)
                            .clip(ThumbShape)
                            .clickable(
                                MutableInteractionSource(), indication = null, role = Role.Tab,
                                onClick = { onSelect(index) },
                            )
                            .semantics { selected = on }
                            .padding(horizontal = 12.dp),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(
                            label, color = Color.White, fontSize = 12.sp,
                            fontWeight = if (on) FontWeight.SemiBold else FontWeight.Normal,
                            maxLines = 1, modifier = Modifier.alpha(if (on) 1f else 0.6f),
                        )
                    }
                }
            }
        }
    }
}
