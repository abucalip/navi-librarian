package app.discair.ui

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawOutline
import androidx.compose.ui.graphics.drawscope.translate
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import app.discair.ui.theme.Ink

/** Heights (share of the icon's height) the bars rest at when nothing moves them. */
private val RestingBars = floatArrayOf(0.45f, 0.85f, 0.6f, 0.75f)

/** Seconds-ish periods (ms) per bar, so the four never move in step. */
private val BarPeriods = intArrayOf(520, 380, 610, 450)

/** Extra room the last item on a page needs so it can scroll clear of the floating island. */
val LocalBottomClearance = androidx.compose.runtime.compositionLocalOf { 0.dp }

/**
 * The bottom navigation, drawn in the owner's theme.
 *
 * - Cassette Deck: a ruled bar with Home, Discover, Library and Search; the mini player sits above it.
 * - Flow: a floating capsule with Home, Discover, Library and Search; the mini player sits above it.
 * - Cover Stack: one outlined bar with Home, Discover, Library and Search; the mini player sits above it.
 * - Sticker Wall: a pill with Search, Home, Library and the player.
 * - Sheet Stack: a joined group with Home, Search, Library and the player.
 * - Standard: a floating island with Search, Home, Library and the player (no mini player here).
 *
 * Discover is not in the island, the pill or the group: it is in the top bar. The player cell is the live meter and opens
 * Now Playing. The island takes the dark tint of the current song's artwork; the other layouts use the owner's palette.
 */
@Composable
fun NavIsland(
    tint: Color?,
    homeSelected: Boolean,
    playing: Boolean,
    playerLabel: String,
    onSearch: () -> Unit,
    onHome: () -> Unit,
    onPlayer: () -> Unit,
    modifier: Modifier = Modifier,
    /** Cassette Deck only: Discover has a cell in its ruled bar. */
    discoverSelected: Boolean = false,
    onDiscover: () -> Unit = {},
    /** Every layout but the Cassette Deck: Library has a cell here. */
    onLibrary: () -> Unit = {},
    librarySelected: Boolean = false,
) {
    // Cassette Deck: a full-width ruled bar in the owner's theme (the island's tint and pill are the Standard composition).
    val deckTheme = app.discair.ui.theme.LocalThemePalette.current ?: app.discair.ui.theme.LocalPalette.current
    if (deckTheme.layout == app.discair.ui.theme.Layout.TapeDeck) {
        app.discair.ui.common.TapeNavBar(
            deckTheme, homeSelected, discoverSelected, librarySelected, onHome, onDiscover, onLibrary, onSearch, modifier,
            homeIcon = { Icon(Icons.Default.Home, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
            discoverIcon = { Icon(Icons.Default.Star, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
            libraryIcon = { Icon(Icons.AutoMirrored.Filled.List, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
            searchIcon = { Icon(Icons.Default.Search, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
        )
        return
    }
    // Cover Stack (Soft Brut): one outlined bar with Home, Discover, Library and Search; the mini player sits above it.
    if (deckTheme.layout == app.discair.ui.theme.Layout.CoverStack) {
        app.discair.ui.common.CoverStackNavBar(
            deckTheme, homeSelected, discoverSelected, librarySelected, onHome, onDiscover, onLibrary, onSearch, modifier,
            homeIcon = { Icon(app.discair.ui.common.ArtIcons.Home, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
            discoverIcon = { Icon(app.discair.ui.common.ArtIcons.Disc, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
            libraryIcon = { Icon(app.discair.ui.common.ArtIcons.Lib, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
            searchIcon = { Icon(app.discair.ui.common.ArtIcons.Search, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
        )
        return
    }
    // Flow: a floating translucent capsule with Home, Discover, Library and Search; the mini player sits above it.
    if (deckTheme.layout == app.discair.ui.theme.Layout.Flow) {
        app.discair.ui.common.FlowNavBar(
            deckTheme, homeSelected, discoverSelected, librarySelected, onHome, onDiscover, onLibrary, onSearch, modifier,
            homeIcon = { Icon(app.discair.ui.common.ArtIcons.Home, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
            discoverIcon = { Icon(app.discair.ui.common.ArtIcons.Disc, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
            libraryIcon = { Icon(app.discair.ui.common.ArtIcons.Lib, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
            searchIcon = { Icon(app.discair.ui.common.ArtIcons.Search, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
        )
        return
    }
    // Sticker Wall: a floating pill (Search, Home, Library, Player) in the owner's theme.
    if (deckTheme.layout == app.discair.ui.theme.Layout.StickerWall) {
        val reduced = app.discair.ui.theme.rememberReducedMotion()
        app.discair.ui.common.StickerPill(
            deckTheme, homeSelected, librarySelected, playerLabel, onSearch, onHome, onLibrary, onPlayer, modifier,
            searchIcon = { Icon(Icons.Default.Search, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
            homeIcon = { Icon(Icons.Default.Home, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
            libraryIcon = { Icon(Icons.AutoMirrored.Filled.List, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
            player = { app.discair.ui.common.TapeMeter(4, app.discair.ui.common.TapeDeckRules.meterMoves(playing, false, reduced), it, size = 22.dp) },
        )
        return
    }
    // Sheet Stack: one joined group (Home, Search, Library, Player) in the owner's theme.
    if (deckTheme.layout == app.discair.ui.theme.Layout.SheetStack) {
        val reduced = app.discair.ui.theme.rememberReducedMotion()
        app.discair.ui.common.SheetNavGroup(
            deckTheme, homeSelected, librarySelected, playerLabel, onHome, onSearch, onLibrary, onPlayer, modifier,
            homeIcon = { Icon(Icons.Default.Home, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
            searchIcon = { Icon(Icons.Default.Search, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
            libraryIcon = { Icon(Icons.AutoMirrored.Filled.List, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
            player = { app.discair.ui.common.TapeMeter(4, app.discair.ui.common.TapeDeckRules.meterMoves(playing, false, reduced), it, size = 22.dp) },
        )
        return
    }
    // Standard: the floating island, 64 dp high with 16 dp margins, its cells 48 dp; the current cell is filled with the accent.
    Box(modifier.fillMaxWidth().navigationBarsPadding().padding(start = 16.dp, end = 16.dp, bottom = 16.dp), contentAlignment = Alignment.BottomCenter) {
        val card = RoundedCornerShape(32.dp)
        val fill by animateColorAsState(tint ?: Ink.Raised, animationSpec = tween(500), label = "islandTint")
        // Neobrut: the outline and hard shadow of the theme the owner chose (the island itself may sit on the dark artwork palette).
        val chosen = app.discair.ui.theme.LocalThemePalette.current ?: app.discair.ui.theme.LocalPalette.current
        val frame = if (chosen.brutal) {
            val outline = (chosen.shape?.outline ?: 2f).dp
            Modifier.brutalShadowOf(card, chosen).background(fill, card).border(outline, chosen.edgeStrong, card)
        } else Modifier.shadow(10.dp, card).background(fill, card).border(1.dp, Color.White.copy(alpha = 0.12f), card)
        Row(
            frame.padding(horizontal = 8.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            IslandCell(onClick = onSearch, label = "Search", icon = Icons.Default.Search)
            IslandCell(onClick = onHome, label = "Home", icon = Icons.Default.Home, selected = homeSelected)
            IslandCell(onClick = onLibrary, label = "Library", icon = Icons.AutoMirrored.Filled.List, selected = librarySelected)
            IslandPlayer(onClick = onPlayer, label = playerLabel) { PlayBars(playing, Ink.Text) }
        }
    }
}

/** A labelled island cell: the icon over its word, 48 dp high. The current page fills the cell with the accent and inks it dark. */
@Composable
private fun IslandCell(onClick: () -> Unit, label: String, icon: androidx.compose.ui.graphics.vector.ImageVector, selected: Boolean = false) {
    val ink = if (selected) Ink.OnAccent else Ink.Text
    Column(
        Modifier.height(48.dp).widthIn(min = 56.dp).clip(RoundedCornerShape(24.dp))
            .background(if (selected) Ink.Accent else Color.Transparent)
            .clickable(role = Role.Button, onClick = onClick)
            .semantics { contentDescription = label; this.selected = selected }
            .padding(horizontal = 6.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Icon(icon, contentDescription = null, tint = ink, modifier = Modifier.size(20.dp))
        Text(label, style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold), color = ink, maxLines = 1, modifier = Modifier.clearAndSetSemantics { })
    }
}

/** The player cell: a round 48 dp button holding the live bars; it opens Now Playing. */
@Composable
private fun IslandPlayer(onClick: () -> Unit, label: String, content: @Composable () -> Unit) {
    Box(
        Modifier.size(48.dp).clip(CircleShape)
            .clickable(role = Role.Button, onClick = onClick)
            .semantics { contentDescription = label },
        contentAlignment = Alignment.Center,
    ) { content() }
}

/** Four rounded bars. They bounce while music plays and stand still otherwise (paused, or nothing queued). */
@Composable
private fun PlayBars(playing: Boolean, color: Color) {
    val heights = FloatArray(RestingBars.size) { RestingBars[it] }
    if (playing) {
        val transition = rememberInfiniteTransition(label = "playBars")
        for (i in heights.indices) {
            val h by transition.animateFloat(
                initialValue = 0.25f, targetValue = 1f,
                animationSpec = infiniteRepeatable(tween(BarPeriods[i], easing = LinearEasing), RepeatMode.Reverse),
                label = "bar$i",
            )
            heights[i] = h
        }
    }
    Canvas(Modifier.size(22.dp)) {
        val bar = 3.5.dp.toPx()
        val gap = (size.width - bar * heights.size) / (heights.size - 1)
        heights.forEachIndexed { i, share ->
            val h = size.height * share
            drawRoundRect(
                color, topLeft = Offset(i * (bar + gap), size.height - h), size = Size(bar, h), cornerRadius = CornerRadius(bar / 2),
            )
        }
    }
}

/** A hard shadow in a given palette's shadow colour (the island needs the chosen theme's, not the over-artwork copy's edge). */
private fun Modifier.brutalShadowOf(shape: androidx.compose.ui.graphics.Shape, p: app.discair.ui.theme.Palette): Modifier {
    val s = p.shape ?: return this
    if (s.shadow == 0f) return this
    return drawBehind {
        val outline = shape.createOutline(size, layoutDirection, this)
        translate(s.shadow.dp.toPx(), s.shadow.dp.toPx()) { drawOutline(outline, p.shadowColor) }
    }
}
