package app.discair.ui.common

import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import app.discair.ui.player.PlayerIcons
import app.discair.ui.theme.Layout
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.Palette

/**
 * Flow's layout (docs/ANDROID_ART_THEMES_PROPOSAL.md section 4): no outlines and no hard shadows. Soft depth in three levels, continuous
 * corners, translucent bars, capsule buttons and grouped lists. The numbers are the tokens of design/android-art-themes/flow.css.
 */
object FlowRules {
    const val RADIUS_CARD = 16f
    const val RADIUS_COVER = 14f
    const val RADIUS_COVER_SMALL = 8f
    const val RADIUS_NAV = 30f
    const val RADIUS_MINI = 18f

    /** A list row is at least this high (dp). */
    const val ROW_MIN = 64f

    /** The bars' fill is white at this alpha. Blur behind them is a later refinement (proposal D3). */
    const val BAR_ALPHA = 0.86f

    /** The shadow elevation (dp) of a depth level: 1 cards and grouped lists, 2 the bars and snackbar, 3 the cover in front. */
    fun elevation(level: Int): Float = when (level) { 1 -> 4f; 2 -> 8f; else -> 16f }

    /** The destinations of the bar, in order: all four, with Discover in the bar (NavRules.discoverInBar). */
    val cells: List<String> = listOf("Home", "Discover", "Library", "Search")

    /** The fill of the navigation bar and the mini player. */
    fun barFill(p: Palette): Color = p.surface.copy(alpha = BAR_ALPHA)
}

/** True while the owner's theme is Flow. Every Flow branch in a shared control is guarded by this, so no other theme changes. */
@Composable
@androidx.compose.runtime.ReadOnlyComposable
fun isFlow(): Boolean = LocalPalette.current.layout == Layout.Flow

/** Flow's soft depth: a shadow of the text colour at the given level (1 to 3). */
fun Modifier.flowDepth(level: Int, shape: Shape, p: Palette): Modifier {
    val e = FlowRules.elevation(level).dp
    return shadow(e, shape, clip = false, ambientColor = p.text.copy(alpha = 0.12f), spotColor = p.text.copy(alpha = if (level == 3) 0.5f else 0.3f))
}

/** A floating bar: translucent white, a 0.5dp hairline and level 2 depth. */
fun Modifier.flowBar(shape: Shape, p: Palette): Modifier =
    flowDepth(2, shape, p).clip(shape).background(FlowRules.barFill(p)).border(0.5.dp, Color.Black.copy(alpha = 0.08f), shape)

/** The Flow card: white, radius 16, level 1 depth. */
fun Modifier.flowCard(p: Palette, shape: Shape = RoundedCornerShape(FlowRules.RADIUS_CARD.dp)): Modifier =
    flowDepth(1, shape, p).clip(shape).background(p.surface)

/**
 * The Flow navigation: a floating capsule (radius 30) with four cells of 50dp, icon over label. The current cell is accent-coloured on a
 * `raised` pill; the others are muted. Floats 12dp from the sides and bottom. Mockup: flow/components, flow/home.
 */
@Composable
fun FlowNavBar(
    palette: Palette, homeSelected: Boolean, discoverSelected: Boolean, librarySelected: Boolean,
    onHome: () -> Unit, onDiscover: () -> Unit, onLibrary: () -> Unit, onSearch: () -> Unit, modifier: Modifier = Modifier,
    homeIcon: @Composable (Color) -> Unit, discoverIcon: @Composable (Color) -> Unit,
    libraryIcon: @Composable (Color) -> Unit, searchIcon: @Composable (Color) -> Unit,
) {
    val bar = RoundedCornerShape(FlowRules.RADIUS_NAV.dp)
    Box(modifier.fillMaxWidth().navigationBarsPadding().padding(start = 12.dp, end = 12.dp, bottom = 12.dp), contentAlignment = Alignment.BottomCenter) {
        Row(
            Modifier.fillMaxWidth().flowBar(bar, palette).padding(5.dp),
            horizontalArrangement = Arrangement.spacedBy(2.dp), verticalAlignment = Alignment.CenterVertically,
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
    val shape = RoundedCornerShape(25.dp)
    // Muted text holds 4.6:1 on `raised` and 5.2:1 on the bar; the accent as text holds on the page and the surface but not on `raised`
    // (proposal section 4), so the selected cell keeps the accent on its icon and the text colour on its label.
    val tint = if (selected) palette.accent else palette.textMuted
    Column(
        Modifier.weight(1f).height(50.dp).clip(shape).background(if (selected) palette.raised else Color.Transparent)
            .clickable(role = Role.Button, onClick = onClick)
            .semantics { contentDescription = label; this.selected = selected },
        horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center,
    ) {
        Box(Modifier.size(24.dp), contentAlignment = Alignment.Center) { icon(tint) }
        Text(
            label, style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold, fontSize = 10.5.sp),
            color = if (selected) palette.text else palette.textMuted, maxLines = 1, modifier = Modifier.clearAndSetSemantics { },
        )
    }
}

/** Flow's list rule: a 0.5dp hairline in the `edge` colour. */
@Composable
fun FlowDivider(modifier: Modifier = Modifier) {
    Box(modifier.fillMaxWidth().height(0.5.dp).background(LocalPalette.current.edge))
}

/**
 * Flow's segmented control: a `raised` track of radius 11 with the selected segment a white pill of radius 9 and a small shadow.
 * 36dp high, label Inter 600 13. Up to four tabs share the width; more scroll. Mockup: flow/components.
 */
@Composable
fun FlowTabs(labels: List<String>, selectedIndex: Int, onSelect: (Int) -> Unit, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    val track = RoundedCornerShape(11.dp)
    val pill = RoundedCornerShape(9.dp)
    val fits = labels.size <= 4
    Row(
        modifier.clip(track).background(p.raised).padding(2.dp).then(
            if (fits) Modifier else Modifier.horizontalScroll(rememberScrollState()),
        ).height(36.dp),
    ) {
        labels.forEachIndexed { i, label ->
            val on = i == selectedIndex
            Box(
                (if (fits) Modifier.weight(1f) else Modifier.padding(horizontal = 2.dp)).fillMaxHeight()
                    .then(if (on) Modifier.shadow(2.dp, pill, clip = false, ambientColor = Color.Black.copy(alpha = 0.1f), spotColor = Color.Black.copy(alpha = 0.25f)).clip(pill).background(p.surface) else Modifier.clip(pill))
                    .clickable(role = Role.Tab, onClick = { onSelect(i) })
                    .semantics { selected = on },
                contentAlignment = Alignment.Center,
            ) {
                Text(label, style = MaterialTheme.typography.labelLarge.copy(fontSize = 13.sp, fontWeight = FontWeight.SemiBold), color = p.text, maxLines = 1, modifier = Modifier.padding(horizontal = 14.dp))
            }
        }
    }
}

/** Flow's switch: 52 by 32, a grey track (green when on) and a 28dp white knob with a soft shadow. */
@Composable
fun FlowSwitch(checked: Boolean, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    val knobX by animateDpAsState(if (checked) 20.dp else 0.dp, tween(200), label = "flowKnob")
    Box(modifier.size(width = 52.dp, height = 32.dp).clip(RoundedCornerShape(16.dp)).background(if (checked) p.ok else FLOW_SWITCH_OFF)) {
        Box(
            Modifier.padding(2.dp).align(Alignment.CenterStart).offset(x = knobX).size(28.dp)
                .shadow(3.dp, CircleShape, clip = false, ambientColor = Color.Black.copy(alpha = 0.15f), spotColor = Color.Black.copy(alpha = 0.3f))
                .background(Color.White, CircleShape),
        )
    }
}

/** The switch track when off (flow.css `.sw`). */
private val FLOW_SWITCH_OFF = Color(0xFFD9D5CB)

/**
 * Flow's grouped list (flow.css `.list.card`): one white card of radius 16 at level 1 depth, rows 12dp in from its edge, a 0.5dp hairline
 * between rows (none after the last). Margins are 16dp at the sides, as the mockups draw it. Rows are [FlowListRow]s.
 */
@Composable
fun FlowGroup(modifier: Modifier = Modifier, content: @Composable androidx.compose.foundation.layout.ColumnScope.() -> Unit) {
    val p = LocalPalette.current
    Column(
        modifier.padding(horizontal = 16.dp).fillMaxWidth().flowCard(p).padding(horizontal = 12.dp),
        content = content,
    )
}

/**
 * One row of a group (flow.css `.li`): at least 64dp, a [leading] visual (a 32dp [FlowIconTile], a cover or a photo), the title in Inter 600 15,
 * its state in words under it in muted text, then a grey chevron or [trailing]. [divider] draws the hairline above the row (every row but the first).
 */
@Composable
fun FlowListRow(
    title: String, modifier: Modifier = Modifier, state: String = "", onClick: (() -> Unit)? = null, divider: Boolean = false,
    leading: (@Composable () -> Unit)? = null, trailing: (@Composable () -> Unit)? = null,
) {
    val p = LocalPalette.current
    Column(modifier) {
        if (divider) FlowDivider()
        Row(
            Modifier.fillMaxWidth().heightIn(min = FlowRules.ROW_MIN.dp)
                .then(if (onClick != null) Modifier.clickable(role = Role.Button, onClick = onClick) else Modifier)
                .semantics(mergeDescendants = true) { contentDescription = if (state.isEmpty()) title else "$title, $state" }
                .padding(vertical = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
        ) {
            leading?.invoke()
            Column(Modifier.weight(1f)) {
                Text(title, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 15.sp, lineHeight = 20.sp))
                if (state.isNotEmpty()) Text(state, color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall.copy(fontSize = 12.sp, lineHeight = 18.sp))
            }
            if (trailing != null) trailing() else Icon(PlayerIcons.Right, contentDescription = null, tint = FLOW_CHEVRON, modifier = Modifier.size(16.dp))
        }
    }
}

/** The 32dp tile in front of a grouped row: radius 8, `raised`, an 18dp glyph in the text colour (flow.css `.ic`). */
@Composable
fun FlowIconTile(icon: ImageVector, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    Box(modifier.size(32.dp).clip(RoundedCornerShape(8.dp)).background(p.raised), contentAlignment = Alignment.Center) {
        Icon(icon, contentDescription = null, tint = p.text, modifier = Modifier.size(18.dp))
    }
}

/**
 * Flow's round icon button: a `raised` circle of 36dp in a top bar (the touch target stays 48dp) or 44dp elsewhere; [size] is that visible diameter
 * (flow.css `.ib`, `.btn.sq`). The glyph is the text colour, or the accent when [accent] (the bars' own buttons).
 */
@Composable
fun FlowCircleButton(icon: ImageVector, label: String, onClick: () -> Unit, modifier: Modifier = Modifier, size: Int = 36, accent: Boolean = false) {
    val p = LocalPalette.current
    Box(
        modifier.size(maxOf(size, 48).dp).clip(CircleShape).clickable(role = Role.Button, onClick = onClick).semantics { contentDescription = label },
        contentAlignment = Alignment.Center,
    ) {
        Box(Modifier.size(size.dp).clip(CircleShape).background(p.raised), contentAlignment = Alignment.Center) {
            Icon(icon, contentDescription = null, tint = if (accent) p.accent else p.text, modifier = Modifier.size(20.dp))
        }
    }
}

/** Flow's tag: Inter 600 11 in capitals, radius 6, a tinted fill. The label is the text colour on the accent tint (4.2:1 for the accent itself, D7). */
@Composable
fun FlowTag(text: String, modifier: Modifier = Modifier, tint: Color = LocalPalette.current.raised, labelColor: Color = LocalPalette.current.textMuted) {
    Text(
        text.uppercase(), color = labelColor, maxLines = 1,
        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold, fontSize = 11.sp, lineHeight = 16.sp, letterSpacing = 0.03.em),
        modifier = modifier.clip(RoundedCornerShape(6.dp)).background(tint).padding(horizontal = 7.dp, vertical = 2.dp),
    )
}

/** The chevron colour (flow.css `.chev`). */
private val FLOW_CHEVRON = Color(0xFFB5B0A5)
