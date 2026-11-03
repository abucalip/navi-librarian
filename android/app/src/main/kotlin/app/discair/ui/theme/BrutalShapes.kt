package app.discair.ui.theme

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Shapes
import androidx.compose.runtime.Composable
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.graphics.RectangleShape
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.drawscope.translate
import androidx.compose.ui.graphics.drawOutline
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/*
 * Shape rules shared by the components. A Classic theme returns each component's own default, so it looks as
 * it always did. A Brutal theme (Palette.shape) supplies a corner radius, an outline width and a hard shadow.
 */

/** The corner radius to use: the Brutal theme's own, else [default]. */
@Composable @ReadOnlyComposable
fun themeShape(default: Dp): Shape {
    val r = LocalPalette.current.shape?.radius ?: return RoundedCornerShape(default)
    return if (r == 0) RectangleShape else RoundedCornerShape(r.dp)
}

/** A fully round shape (switch track, chips); square on a theme whose radius is 0. */
@Composable @ReadOnlyComposable
fun pillShape(): Shape = if (LocalPalette.current.shape?.radius == 0) RectangleShape else RoundedCornerShape(50)

/** The outline to draw: a Brutal theme's thick outline in its strong edge colour, else [classic]. */
@Composable @ReadOnlyComposable
fun themeBorder(classic: BorderStroke): BorderStroke {
    val p = LocalPalette.current
    val s = p.shape ?: return classic
    return BorderStroke(s.outline.dp, p.edgeStrong)
}

/** The hard offset shadow of a Brutal theme, drawn behind the component; nothing on a Classic theme. */
@Composable
fun Modifier.brutalShadow(shape: Shape, scale: Float = 1f): Modifier {
    val p = LocalPalette.current
    val s = p.shape ?: return this
    if (s.shadow == 0) return this
    val color = p.shadowColor
    val offset = (s.shadow * scale).dp
    return drawBehind {
        val outline = shape.createOutline(size, layoutDirection, this)
        translate(offset.toPx(), offset.toPx()) { drawOutline(outline, color) }
    }
}

/** Material's own components (buttons, menus, dialogs, fields) follow a Brutal theme's radius. */
fun shapesFor(p: Palette): Shapes {
    val r = p.shape?.radius ?: return Shapes()
    val s = RoundedCornerShape(r.dp)
    return Shapes(extraSmall = s, small = s, medium = s, large = s, extraLarge = s)
}

/** The outline of a Brutal theme's components: its outline width in the strong edge colour. */
@Composable @ReadOnlyComposable
fun brutalOutline(): BorderStroke {
    val p = LocalPalette.current
    return BorderStroke((p.shape?.outline ?: 1).dp, p.edgeStrong)
}
