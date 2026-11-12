package app.discair.ui.common

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.verticalDrag
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.RowScope
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.ProgressBarRangeInfo
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.progressBarRangeInfo
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.setProgress
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import app.discair.lyrics.LyricsUiState
import app.discair.lyrics.lyricsFailureText
import app.discair.ui.theme.Layout
import app.discair.ui.theme.Palette
import app.discair.ui.theme.brutalShadow
import app.discair.ui.theme.themeShape

/** Pure rules for the Sheet Stack layout (docs/BRUT_LAYOUTS_PLAN.md section 7), apart from the drawing so they are unit-tested. */
object SheetStackRules {
    /** The request words of Home's list: Fetching, Queued, Done; any other status keeps the app's own label (never a bare colour). */
    fun requestWord(status: String, label: String): String = when (status.lowercase()) {
        "queued", "requested", "queued_unconfirmed" -> "Queued"
        "imported" -> "Done"
        "searching", "downloading", "download_complete_waiting_for_folder", "importing", "monitoring", "recovery_started",
        "source_switching", "skip_requested", "retry_requested" -> "Fetching"
        else -> label
    }

    /** Dismissed requests are not listed; the rest keep the server's order (newest first), at most [limit]. */
    const val HOME_REQUESTS = 4

    /** 1 at the top of the track, 0 at the bottom: [y] is the touch position, [height] the slider's height, [inset] its end padding. */
    fun volumeFromTouch(y: Float, height: Float, inset: Float): Float {
        val span = (height - 2 * inset).coerceAtLeast(1f)
        return (1f - (y - inset) / span).coerceIn(0f, 1f)
    }

    /** Spoken value of the volume slider, for example "70 percent". */
    fun volumeDescription(volume: Float): String = "${(volume.coerceIn(0f, 1f) * 100).toInt()} percent"

    /** The queue button and the lyrics strip each open their own panel under the player; pressing the open one closes it again. */
    fun toggleView(current: Int, target: Int): Int = if (current == target) 0 else target

    /** The words in the lyrics strip: the line being sung, or the same "no lyrics" states the Lyrics view shows. */
    fun lyricsStripText(state: LyricsUiState, currentLine: Int): String = when (state) {
        LyricsUiState.Idle, is LyricsUiState.Loading -> "Loading lyrics…"
        is LyricsUiState.None -> "No lyrics for this song."
        is LyricsUiState.Unsupported -> "Your Navidrome doesn't provide lyrics."
        is LyricsUiState.Failed -> lyricsFailureText(state.problem)
        is LyricsUiState.Ready -> {
            val line = state.lyrics.lines.getOrNull(currentLine)?.text?.trim().orEmpty()
            if (state.lyrics.timed && line.isNotEmpty()) line else "Lyrics · tap to read"
        }
    }
}

/**
 * The Sheet Stack's navigation: one joined group in a hard-shadowed frame, in the owner's chosen theme; the current page is filled with
 * the accent. It holds Home, Search and Library, then the Player cell (the group has no mini player, so the player lives here). Discover
 * is in the top bar, not in the group. [player] draws the Player cell's content (the live meter).
 */
@Composable
fun SheetNavGroup(
    palette: Palette, homeSelected: Boolean, librarySelected: Boolean, playerLabel: String,
    onHome: () -> Unit, onSearch: () -> Unit, onLibrary: () -> Unit, onPlayer: () -> Unit,
    modifier: Modifier = Modifier,
    homeIcon: @Composable (Color) -> Unit, searchIcon: @Composable (Color) -> Unit,
    libraryIcon: @Composable (Color) -> Unit, player: @Composable (Color) -> Unit,
) {
    val shape = themeShape(14.dp)
    val seam = (palette.shape?.outline ?: 2).dp
    Box(modifier.fillMaxWidth().navigationBarsPadding().padding(start = 16.dp, end = 24.dp, bottom = 16.dp, top = 8.dp)) {
        Row(
            Modifier.fillMaxWidth().height(56.dp).brutalShadow(shape).clip(shape).background(palette.surface)
                .border(seam, palette.edgeStrong, shape),
        ) {
            SheetSegment(palette, "Home", homeSelected, onHome, seam, last = false) { homeIcon(it) }
            SheetSegment(palette, "Search", false, onSearch, seam, last = false) { searchIcon(it) }
            SheetSegment(palette, "Library", librarySelected, onLibrary, seam, last = false) { libraryIcon(it) }
            SheetSegment(palette, playerLabel, false, onPlayer, seam, last = true, word = null) { player(it) }
        }
    }
}

@Composable
private fun RowScope.SheetSegment(
    palette: Palette, label: String, selected: Boolean, onClick: () -> Unit, seam: Dp, last: Boolean,
    word: String? = label, content: @Composable (Color) -> Unit,
) {
    val fill = if (selected) palette.accent else palette.surface
    val ink = if (selected) palette.onAccent else palette.text
    Column(
        Modifier.weight(1f).fillMaxHeight().background(fill).clickable(role = Role.Button, onClick = onClick)
            .semantics { contentDescription = label; this.selected = selected },
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Box(Modifier.size(22.dp), contentAlignment = Alignment.Center) { content(ink) }
        if (word != null) Text(word, style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold), color = ink, maxLines = 1, modifier = Modifier.clearAndSetSemantics { })
    }
    if (!last) Box(Modifier.width(seam).fillMaxHeight().background(palette.edgeStrong))
}

/**
 * A vertical volume slider: an outlined track filled from the bottom, with a square thumb. Dragging or tapping sets the player's
 * volume; assistive tech gets the value and can adjust it (progress actions). The touch area is 48dp wide.
 */
@Composable
fun VerticalVolumeSlider(volume: Float, onChange: (Float) -> Unit, palette: Palette, modifier: Modifier = Modifier) {
    val v = volume.coerceIn(0f, 1f)
    val outline = (palette.shape?.outline ?: 2).dp
    Canvas(
        modifier.width(48.dp)
            .semantics {
                contentDescription = "Volume"
                stateDescription = SheetStackRules.volumeDescription(v)
                progressBarRangeInfo = ProgressBarRangeInfo(v, 0f..1f, 19)
                setProgress { target -> onChange(target.coerceIn(0f, 1f)); true }
            }
            .pointerInput(Unit) {
                val inset = 14.dp.toPx()
                awaitEachGesture {
                    val down = awaitFirstDown()
                    down.consume()
                    onChange(SheetStackRules.volumeFromTouch(down.position.y, size.height.toFloat(), inset))
                    verticalDrag(down.id) { change -> change.consume(); onChange(SheetStackRules.volumeFromTouch(change.position.y, size.height.toFloat(), inset)) }
                }
            },
    ) {
        val inset = 14.dp.toPx()
        val trackW = 14.dp.toPx()
        val left = (size.width - trackW) / 2
        val top = inset
        val trackH = size.height - 2 * inset
        val corner = CornerRadius(minOf(palette.shape?.radius ?: 0, 4).dp.toPx())
        drawRoundRect(palette.surface, Offset(left, top), Size(trackW, trackH), corner)
        val fillH = trackH * v
        drawRoundRect(palette.accent, Offset(left, top + trackH - fillH), Size(trackW, fillH), corner)
        drawRoundRect(palette.edgeStrong, Offset(left, top), Size(trackW, trackH), corner, style = androidx.compose.ui.graphics.drawscope.Stroke(outline.toPx()))
        val t = 22.dp.toPx()
        val ty = top + trackH - fillH - t / 2
        drawRoundRect(palette.shadowColor, Offset(left + trackW / 2 - t / 2 + 2.dp.toPx(), ty + 2.dp.toPx()), Size(t, t), corner)
        drawRoundRect(palette.surface, Offset(left + trackW / 2 - t / 2, ty), Size(t, t), corner)
        drawRoundRect(palette.edgeStrong, Offset(left + trackW / 2 - t / 2, ty), Size(t, t), corner, style = androidx.compose.ui.graphics.drawscope.Stroke(outline.toPx()))
    }
}
