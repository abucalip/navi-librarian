package app.discair.ui.common

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.drawOutline
import androidx.compose.ui.graphics.drawscope.translate
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.sp
import app.discair.ui.theme.Layout
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.Palette

/**
 * Soft Brut's "Cover Stack" layout (docs/ANDROID_ART_THEMES_PROPOSAL.md section 3). Its one recipe is a 1.5dp ink outline with a 3dp
 * ink shadow to the lower right on a surface fill; the numbers come from the palette's [Palette.shape], so nothing here is fixed in code.
 */
object CoverStackRules {
    /** The outline, shadow and radius (dp) a Cover Stack control is drawn with; falls back to the proposal's values. */
    fun outline(p: Palette): Float = p.shape?.outline ?: 1.5f
    fun shadow(p: Palette): Float = p.shape?.shadow ?: 3f
    fun radius(p: Palette): Float = p.shape?.radius ?: 10f

    /** The navigation bar's corner radius is 4 more than a card's (mockup: 14 on 10). */
    fun barRadius(p: Palette): Float = radius(p) + 4f

    /** The destinations of the bar, in order: all four, with Discover in the bar (NavRules.discoverInBar). */
    val cells: List<String> = listOf("Home", "Discover", "Library", "Search")
}

/** The Cover Stack recipe's hard shadow in [p]'s shadow colour, offset by the palette's shadow width. */
fun Modifier.coverStackShadow(shape: Shape, p: Palette, offsetDp: Float? = null): Modifier {
    val off = offsetDp ?: CoverStackRules.shadow(p)
    if (off == 0f) return this
    return drawBehind {
        val outline = shape.createOutline(size, layoutDirection, this)
        translate(off.dp.toPx(), off.dp.toPx()) { drawOutline(outline, p.shadowColor) }
    }
}

/** Surface fill, ink outline and hard shadow: the recipe every Cover Stack card, bar and button shares. */
fun Modifier.coverStackFrame(shape: Shape, p: Palette, fill: Color = p.surface): Modifier =
    coverStackShadow(shape, p).clip(shape).background(fill).border(CoverStackRules.outline(p).dp, p.edgeStrong, shape)

/**
 * The Cover Stack navigation: one outlined bar, radius 14, four icon-only cells of 50dp. The current cell is filled with the accent
 * and outlined. Floats 12dp from the sides and bottom. Mockup: soft-brut/home, the bar under the mini player.
 */
@Composable
fun CoverStackNavBar(
    palette: Palette, homeSelected: Boolean, discoverSelected: Boolean, librarySelected: Boolean,
    onHome: () -> Unit, onDiscover: () -> Unit, onLibrary: () -> Unit, onSearch: () -> Unit, modifier: Modifier = Modifier,
    homeIcon: @Composable (Color) -> Unit, discoverIcon: @Composable (Color) -> Unit,
    libraryIcon: @Composable (Color) -> Unit, searchIcon: @Composable (Color) -> Unit,
) {
    val bar = RoundedCornerShape(CoverStackRules.barRadius(palette).dp)
    Box(modifier.fillMaxWidth().navigationBarsPadding().padding(start = 12.dp, end = 15.dp, bottom = 15.dp), contentAlignment = Alignment.BottomCenter) {
        Row(
            Modifier.fillMaxWidth().coverStackFrame(bar, palette).padding(5.dp),
            horizontalArrangement = Arrangement.spacedBy(4.dp), verticalAlignment = Alignment.CenterVertically,
        ) {
            Cell(palette, "Home", homeSelected, onHome) { homeIcon(it) }
            Cell(palette, "Discover", discoverSelected, onDiscover) { discoverIcon(it) }
            Cell(palette, "Library", librarySelected, onLibrary) { libraryIcon(it) }
            Cell(palette, "Search", false, onSearch) { searchIcon(it) }
        }
    }
}

@Composable
private fun RowScope.Cell(palette: Palette, label: String, selected: Boolean, onClick: () -> Unit, icon: @Composable (Color) -> Unit) {
    val shape = RoundedCornerShape(9.dp)
    val ol = CoverStackRules.outline(palette).dp
    Column(
        Modifier.weight(1f).height(50.dp).clip(shape)
            .background(if (selected) palette.accent else Color.Transparent)
            .border(ol, if (selected) palette.edgeStrong else Color.Transparent, shape)
            .clickable(role = Role.Button, onClick = onClick)
            .semantics { contentDescription = label; this.selected = selected },
        horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center,
    ) {
        // Icons only; the label stays as the cell's content description.
        Box(Modifier.size(24.dp), contentAlignment = Alignment.Center) { icon(palette.text) }
    }
}

/** True while the owner's theme is Soft Brut's Cover Stack. Every Cover Stack branch in a shared control is guarded by this, so no other theme changes. */
@Composable
@androidx.compose.runtime.ReadOnlyComposable
fun isCoverStack(): Boolean = LocalPalette.current.layout == Layout.CoverStack

/** The dashed 1.5dp divider of Cover Stack lists (the palette's grid colour). */
@Composable
fun CoverStackDivider(modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    val ol = CoverStackRules.outline(p)
    Box(modifier.fillMaxWidth().height(ol.dp).drawBehind {
        drawLine(p.chartGrid, Offset(0f, size.height / 2), Offset(size.width, size.height / 2), strokeWidth = ol.dp.toPx(), pathEffect = PathEffect.dashPathEffect(floatArrayOf(4.dp.toPx(), 3.dp.toPx())))
    })
}

/**
 * Cover Stack tabs: one joined, outlined group with a hard shadow, the selected segment filled with the accent and a rule between segments.
 * 40dp high, label Inter 700 13. Up to four tabs share the width; more scroll. Mockup: soft-brut/components.
 */
@Composable
fun CoverStackTabs(labels: List<String>, selectedIndex: Int, onSelect: (Int) -> Unit, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(CoverStackRules.radius(p).dp)
    val ol = CoverStackRules.outline(p).dp
    val fits = labels.size <= 4
    Row(
        modifier.coverStackFrame(shape, p).then(if (fits) Modifier else Modifier.horizontalScroll(rememberScrollState())).height(40.dp),
    ) {
        labels.forEachIndexed { i, label ->
            val on = i == selectedIndex
            Box(
                (if (fits) Modifier.weight(1f) else Modifier.widthIn(min = 72.dp)).fillMaxHeight()
                    .background(if (on) p.accent else p.surface)
                    .clickable(role = Role.Tab, onClick = { onSelect(i) })
                    .semantics { selected = on },
                contentAlignment = Alignment.Center,
            ) {
                Text(label, style = MaterialTheme.typography.labelLarge.copy(fontSize = 13.sp, fontWeight = FontWeight.Bold), color = if (on) p.onAccent else p.text, maxLines = 1, modifier = Modifier.padding(horizontal = 12.dp))
            }
            if (i < labels.lastIndex) Box(Modifier.width(ol).fillMaxHeight().background(p.edgeStrong))
        }
    }
}
