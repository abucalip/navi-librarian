package app.discair.ui.common

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
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import app.discair.ui.theme.Palette

/**
 * Pure rules for the Cassette Deck layout (docs/BRUT_LAYOUTS_PLAN.md section 7), apart from the drawing so they are unit-tested.
 */
object TapeDeckRules {
    /** The meter moves only while a song is really playing: not paused, not buffering, and not when the phone reduces motion. */
    fun meterMoves(playing: Boolean, buffering: Boolean, reducedMotion: Boolean): Boolean = playing && !buffering && !reducedMotion

    /** Heights (share of the meter's height) the bars rest at, tallest in the middle; the count is the number of bars. */
    fun restingBars(count: Int): List<Float> {
        val base = listOf(0.45f, 0.8f, 0.6f, 1f, 0.55f)
        return List(count) { base[it % base.size] }
    }

    /** "Track 2 of 8"; blank when there is no queue to place the song in. */
    fun trackLabel(index: Int, total: Int): String = if (total <= 0 || index < 0 || index >= total) "" else "Track ${index + 1} of $total"

    /** The mini player belongs to the Cassette Deck only, and only while a song is queued; every other layout has none. */
    fun miniPlayerShown(layout: app.discair.ui.theme.Layout, hasSong: Boolean): Boolean = layout == app.discair.ui.theme.Layout.TapeDeck && hasSong

    /** Settings sits in the Cassette Deck's navigation bar (the mini player took the player's place), so Home's page buttons drop it. */
    fun homeShowsSettingsButton(layout: app.discair.ui.theme.Layout): Boolean = layout != app.discair.ui.theme.Layout.TapeDeck

    /** The Cassette Deck's bar also has a Library cell, so Home's page buttons drop Library there too (Discover is what is left). */
    fun homeShowsLibraryButton(layout: app.discair.ui.theme.Layout): Boolean = layout != app.discair.ui.theme.Layout.TapeDeck

    /** Where the ruler marks of the Cassette Deck's seek bar sit, as fractions of the track: [count] equal steps, the two ends excluded. */
    fun seekTicks(count: Int): List<Float> = if (count < 2) emptyList() else List(count - 1) { (it + 1f) / count }

    /** The lyrics button on Now Playing: the view is lyrics (1) or the queue under the player (0). A stale queue-face view (2) also becomes lyrics. */
    fun toggleLyrics(view: Int): Int = if (view == 1) 0 else 1

    /** How many rows the Home list shows before "See all": the ruled list is not lazy, so it stays short. */
    const val HOME_ROWS = 8
}

/**
 * A row of square bars that rise and fall while [moving] and stand still otherwise. Decorative: it carries no description,
 * the row beside it says what is playing. [bars] is 3 in lists and 5 on Now Playing.
 */
@Composable
fun TapeMeter(bars: Int, moving: Boolean, color: Color, modifier: Modifier = Modifier, size: Dp = 16.dp) {
    val resting = TapeDeckRules.restingBars(bars)
    val periods = intArrayOf(520, 380, 610, 450, 560)
    val heights = FloatArray(bars) { resting[it] }
    if (moving) {
        val transition = rememberInfiniteTransition(label = "tapeMeter")
        for (i in heights.indices) {
            val h by transition.animateFloat(
                initialValue = 0.25f, targetValue = 1f,
                animationSpec = infiniteRepeatable(tween(periods[i % periods.size], easing = LinearEasing), RepeatMode.Reverse),
                label = "bar$i",
            )
            heights[i] = h
        }
    }
    Canvas(modifier.size(size)) {
        val gap = size.toPx() / (bars * 3f)
        val bar = (this.size.width - gap * (bars - 1)) / bars
        heights.forEachIndexed { i, share ->
            val h = this.size.height * share
            drawRect(color, Offset(i * (bar + gap), this.size.height - h), Size(bar, h))
        }
    }
}

/**
 * The ruled navigation bar of the Cassette Deck: Search, Home, Library and Settings (four cells) in a full-width bar split by rules; the current page is
 * filled with the accent. The player has no cell here: the mini player above the bar opens Now Playing. [palette] is the owner's
 * chosen theme: the bar sits on the page, not on the dark artwork tint the island takes.
 */
@Composable
fun TapeNavBar(
    palette: Palette,
    homeSelected: Boolean,
    librarySelected: Boolean,
    settingsSelected: Boolean,
    onSearch: () -> Unit,
    onHome: () -> Unit,
    onLibrary: () -> Unit,
    onSettings: () -> Unit,
    modifier: Modifier = Modifier,
    searchIcon: @Composable (Color) -> Unit,
    homeIcon: @Composable (Color) -> Unit,
    libraryIcon: @Composable (Color) -> Unit,
    settingsIcon: @Composable (Color) -> Unit,
) {
    val rule = (palette.shape?.outline ?: 2).dp
    Row(
        modifier.fillMaxWidth().background(palette.surface).drawBehind {
            drawRect(palette.edgeStrong, Offset.Zero, Size(size.width, rule.toPx()))
        }.navigationBarsPadding().height(56.dp + rule),
        horizontalArrangement = Arrangement.spacedBy(0.dp),
    ) {
        TapeNavCell(palette, "Search", false, onSearch, Modifier.weight(1f), rule, last = false) { searchIcon(it) }
        TapeNavCell(palette, "Home", homeSelected, onHome, Modifier.weight(1f), rule, last = false) { homeIcon(it) }
        TapeNavCell(palette, "Library", librarySelected, onLibrary, Modifier.weight(1f), rule, last = false) { libraryIcon(it) }
        TapeNavCell(palette, "Settings", settingsSelected, onSettings, Modifier.weight(1f), rule, last = true) { settingsIcon(it) }
    }
}

@Composable
private fun androidx.compose.foundation.layout.RowScope.TapeNavCell(
    palette: Palette, label: String, selected: Boolean, onClick: () -> Unit, modifier: Modifier, rule: Dp, last: Boolean,
    content: @Composable (Color) -> Unit,
) {
    val fill = if (selected) palette.accent else palette.surface
    val ink = if (selected) palette.onAccent else palette.text
    Box(
        modifier.fillMaxHeight().padding0Top(rule).background(fill)
            .let { if (last) it else it.drawBehind { drawRect(palette.edgeStrong, Offset(size.width - rule.toPx(), 0f), Size(rule.toPx(), size.height)) } }
            .clickable(role = Role.Button, onClick = onClick)
            .semantics { contentDescription = label; this.selected = selected },
        contentAlignment = Alignment.Center,
    ) { content(ink) }
}

/** Leaves [top] clear above the cell, where the bar's top rule is drawn. */
private fun Modifier.padding0Top(top: Dp): Modifier = this.then(Modifier.padding(top = top))
