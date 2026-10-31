package app.discair.ui.common

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.ui.theme.Ink

private val ButtonEdge = Color(0xFF2C2C2C)
private val ButtonEdgeActive = Color(0xFF666666)
private val ButtonFill = Color(0xFF1A1A1A)
private val ButtonFillActive = Color(0xFF292929)

/**
 * The "boton-elegante" pill (Uiverse, iZOXVL) for the Discover categories: a dark pill with a bold white
 * label, a lighter border and fill while pressed, and a soft radial glow that grows from the middle.
 * A phone has no hover, so pressed stands in for it. The selected category keeps the lighter fill and
 * takes the accent border, so it is told apart by more than colour: it is also announced as selected.
 */
@Composable
fun ElegantButton(text: String, selected: Boolean, onClick: () -> Unit, modifier: Modifier = Modifier) {
    val source = remember { MutableInteractionSource() }
    val pressed by source.collectIsPressedAsState()
    val active = pressed || selected
    val border by animateColorAsState(
        when {
            selected -> Ink.Accent
            pressed -> ButtonEdgeActive
            else -> ButtonEdge
        },
        tween(400), label = "edge",
    )
    val fill by animateColorAsState(if (active) ButtonFillActive else ButtonFill, tween(400), label = "fill")
    val glow by animateFloatAsState(if (pressed) 1f else 0f, tween(500), label = "glow")
    val shape = RoundedCornerShape(30.dp)
    Box(
        modifier.heightIn(min = Target)
            .clip(shape)
            .background(fill)
            .border(BorderStroke(2.dp, border), shape)
            .drawBehind {
                if (glow > 0f) {
                    // The web grows a 70% radial gradient to 4x; here it grows to the pill's own length.
                    val radius = size.width * 0.5f * glow
                    drawCircle(
                        Brush.radialGradient(
                            0f to Color.White.copy(alpha = 0.25f), 0.7f to Color.Transparent,
                            center = Offset(size.width / 2, size.height / 2), radius = radius.coerceAtLeast(1f),
                        ),
                        radius = radius.coerceAtLeast(1f),
                    )
                }
            }
            .clickable(source, indication = null, role = Role.Button, onClick = onClick)
            .semantics { this.selected = selected }
            .padding(horizontal = 18.dp, vertical = 10.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(text, color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Bold, maxLines = 1)
    }
}
