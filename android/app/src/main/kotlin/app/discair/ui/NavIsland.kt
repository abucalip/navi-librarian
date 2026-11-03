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
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.graphics.drawOutline
import androidx.compose.ui.graphics.drawscope.translate
import androidx.compose.ui.draw.drawBehind
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import app.discair.ui.theme.Ink

/** Heights (share of the icon's height) the bars rest at when nothing moves them. */
private val RestingBars = floatArrayOf(0.45f, 0.85f, 0.6f, 0.75f)

/** Seconds-ish periods (ms) per bar, so the four never move in step. */
private val BarPeriods = intArrayOf(520, 380, 610, 450)

/** Extra room the last item on a page needs so it can scroll clear of the floating island. */
val LocalBottomClearance = androidx.compose.runtime.compositionLocalOf { 0.dp }

/**
 * The floating navigation island: Search on the left, Home (the dashboard) in the middle and the
 * play bars on the right, which open the player. No bar sits behind it, so pages scroll underneath.
 * It takes the dark tint of the artwork of the current song, playing or paused; the active page
 * is marked by a yellow ring.
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
    /** Cassette Deck only: Settings takes the player's cell in its ruled bar (the mini player opens Now Playing). */
    onSettings: () -> Unit = {},
    settingsSelected: Boolean = false,
    /** Sheet Stack only: Library takes a segment of its joined group. */
    onLibrary: () -> Unit = {},
    librarySelected: Boolean = false,
) {
    // Cassette Deck: a full-width ruled bar in the owner's theme (the island's tint and pill are the Standard composition).
    val deckTheme = app.discair.ui.theme.LocalThemePalette.current ?: app.discair.ui.theme.LocalPalette.current
    if (deckTheme.layout == app.discair.ui.theme.Layout.TapeDeck) {
        app.discair.ui.common.TapeNavBar(
            deckTheme, homeSelected, settingsSelected, onSearch, onHome, onSettings, modifier,
            searchIcon = { Icon(Icons.Default.Search, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
            homeIcon = { Icon(Icons.Default.Home, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
            settingsIcon = { Icon(app.discair.ui.player.PlayerIcons.Tune, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
        )
        return
    }
    // Sticker Wall: a floating pill (Search, Home, Player) in the owner's theme.
    if (deckTheme.layout == app.discair.ui.theme.Layout.StickerWall) {
        val reduced = app.discair.ui.common.rememberReducedMotion()
        app.discair.ui.common.StickerPill(
            deckTheme, homeSelected, playerLabel, onSearch, onHome, onPlayer, modifier,
            searchIcon = { Icon(Icons.Default.Search, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
            homeIcon = { Icon(Icons.Default.Home, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
            player = { app.discair.ui.common.TapeMeter(4, app.discair.ui.common.TapeDeckRules.meterMoves(playing, false, reduced), it, size = 22.dp) },
        )
        return
    }
    // Sheet Stack: one joined four-segment group (Home, Search, Library, Player) in the owner's theme.
    if (deckTheme.layout == app.discair.ui.theme.Layout.SheetStack) {
        val reduced = app.discair.ui.common.rememberReducedMotion()
        app.discair.ui.common.SheetNavGroup(
            deckTheme, homeSelected, librarySelected, playerLabel, onHome, onSearch, onLibrary, onPlayer, modifier,
            homeIcon = { Icon(Icons.Default.Home, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
            searchIcon = { Icon(Icons.Default.Search, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
            libraryIcon = { Icon(Icons.AutoMirrored.Filled.List, contentDescription = null, tint = it, modifier = Modifier.size(24.dp)) },
            player = { app.discair.ui.common.TapeMeter(4, app.discair.ui.common.TapeDeckRules.meterMoves(playing, false, reduced), it, size = 22.dp) },
        )
        return
    }
    Box(modifier.fillMaxWidth().navigationBarsPadding().padding(bottom = 12.dp), contentAlignment = Alignment.BottomCenter) {
        val card = RoundedCornerShape(50.dp)
        val fill by animateColorAsState(tint ?: Ink.Raised, animationSpec = tween(500), label = "islandTint")
        // Neobrut: the outline and hard shadow of the theme the owner chose (the island itself may sit on the dark artwork palette).
        val chosen = app.discair.ui.theme.LocalThemePalette.current ?: app.discair.ui.theme.LocalPalette.current
        val frame = if (chosen.brutal) {
            val outline = (chosen.shape?.outline ?: 2).dp
            Modifier.brutalShadowOf(card, chosen).background(fill, card).border(outline, chosen.edgeStrong, card)
        } else Modifier.shadow(10.dp, card).background(fill, card).border(1.dp, Color.White.copy(alpha = 0.12f), card)
        Row(
            frame.padding(horizontal = 14.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            IslandButton(onClick = onSearch, label = "Search") {
                Icon(Icons.Default.Search, contentDescription = null, tint = Ink.Text, modifier = Modifier.size(24.dp))
            }
            IslandButton(onClick = onHome, label = "Home", selected = homeSelected) {
                Icon(Icons.Default.Home, contentDescription = null, tint = Ink.Text, modifier = Modifier.size(24.dp))
            }
            IslandButton(onClick = onPlayer, label = playerLabel) { PlayBars(playing, Ink.Text) }
        }
    }
}

@Composable
private fun IslandButton(onClick: () -> Unit, label: String, selected: Boolean = false, content: @Composable () -> Unit) {
    Box(
        Modifier.size(48.dp).clip(CircleShape).then(if (selected) Modifier.border(2.dp, Ink.Accent, CircleShape) else Modifier)
            .clickable(role = Role.Button, onClick = onClick)
            .semantics { contentDescription = label; this.selected = selected },
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
    if (s.shadow == 0) return this
    return drawBehind {
        val outline = shape.createOutline(size, layoutDirection, this)
        translate(s.shadow.dp.toPx(), s.shadow.dp.toPx()) { drawOutline(outline, p.shadowColor) }
    }
}
