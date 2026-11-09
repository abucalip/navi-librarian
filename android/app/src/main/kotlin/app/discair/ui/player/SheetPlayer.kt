package app.discair.ui.player

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.wrapContentHeight
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import app.discair.lyrics.LyricsUiState
import app.discair.player.PlayerController
import app.discair.player.PlayerUiState
import app.discair.player.QueueItem
import app.discair.player.qualityLabel
import app.discair.ui.common.Cover
import app.discair.ui.common.SheetStackRules
import app.discair.ui.common.Target
import app.discair.ui.common.VerticalVolumeSlider
import app.discair.ui.theme.LocalFontPair
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.brutalShadow
import app.discair.ui.theme.themeShape

/** Height of the queue and lyrics panels that open under the transport. */
private val PanelHeight = 380.dp

/** The panel that is open under the transport: none, the lyrics (1) or the queue (2). */
const val SHEET_VIEW_PLAYER = 0
const val SHEET_VIEW_LYRICS = 1
const val SHEET_VIEW_QUEUE = 2

/**
 * Sheet Stack only: Now Playing as a bottom sheet (the sheet's own grab handle) with a large cover and a vertical volume slider
 * beside it, the title, a seek bar, a joined four-button transport (previous, play or pause, next, queue) and a lyrics strip.
 * Opening the queue or tapping the strip shows that panel under them. It replaces the Standard layout's flip card; every control
 * does what its Standard twin does, and the lyrics are the same view and the same lookups (the strip is the Lyrics view, so it
 * loads while the sheet is open).
 */
@Composable
fun SheetPlayer(
    state: PlayerUiState, controller: PlayerController, view: Int, onView: (Int) -> Unit,
    lyricsState: LyricsUiState, currentLine: Int,
    onSignIn: () -> Unit, onEqualizer: () -> Unit, onCrossfade: () -> Unit,
    onOpenArtist: (QueueItem) -> Unit, onOpenAlbum: (QueueItem) -> Unit,
    onCoverColor: (Color) -> Unit, line: LineUi, lyricsPanel: @Composable () -> Unit,
) {
    val item = state.current ?: return
    val p = LocalPalette.current
    val rule = (p.shape?.outline ?: 2).dp
    val shape = themeShape(14.dp)
    val mono = LocalFontPair.current.mono
    var dragging by remember { mutableStateOf<Float?>(null) }
    val duration = state.durationMs
    val fraction = dragging ?: if (duration > 0) (state.positionMs.toFloat() / duration).coerceIn(0f, 1f) else 0f
    val shown = if (dragging != null) (fraction * duration).toLong() else state.positionMs
    val timeStyle = MaterialTheme.typography.labelSmall.copy(fontFamily = mono)
    val muted = MaterialTheme.colorScheme.onSurfaceVariant

    Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(bottom = 24.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        // The cover and the volume slider, side by side; the slider is as tall as the cover.
        BoxWithConstraints(Modifier.fillMaxWidth()) {
            val cover: Dp = minOf(maxWidth - 72.dp, 380.dp)
            Row(Modifier.fillMaxWidth().height(cover), horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(cover).brutalShadow(shape).clip(shape).border(rule, p.edgeStrong, shape)) {
                    Cover(playerArtworkUrl(item.coverUrl), Modifier.fillMaxSize(), rect = true, onColor = onCoverColor)
                }
                Spacer(Modifier.width(16.dp))
                VerticalVolumeSlider(state.queue.volume, controller::setVolume, p, Modifier.fillMaxHeight())
            }
        }
        Spacer(Modifier.height(16.dp))
        Text(
            item.title, style = MaterialTheme.typography.titleLarge, textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth().semantics { liveRegion = LiveRegionMode.Polite; heading() },
        )
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
            val link = MaterialTheme.typography.bodyMedium
            if (item.artist.isNotBlank()) Text(
                item.artist, style = link, color = muted, maxLines = 1, overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f, fill = false).heightIn(min = Target).clickable(onClickLabel = "Open artist", role = Role.Button) { onOpenArtist(item) }
                    .wrapContentHeight(Alignment.CenterVertically),
            )
            if (item.artist.isNotBlank() && item.album.isNotBlank()) Text(" · ", style = link, color = muted)
            if (item.album.isNotBlank()) Text(
                item.album, style = link, color = muted, maxLines = 1, overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f, fill = false).heightIn(min = Target).clickable(onClickLabel = "Open album", role = Role.Button) { onOpenAlbum(item) }
                    .wrapContentHeight(Alignment.CenterVertically),
            )
        }
        // Status in words: loading, buffering, lost connection, unavailable, queue full.
        if (state.status != null || state.buffering) {
            Text(
                playerSubtitle(state), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.primary, textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth().padding(top = 4.dp).semantics { liveRegion = LiveRegionMode.Polite },
            )
        }
        if (state.signInRequired) TextButton(onClick = { controller.dismissSignIn(); onSignIn() }, Modifier.heightIn(min = Target)) { Text("Sign in again") }
        if (state.waitingForNetwork) TextButton(onClick = controller::retryNow, Modifier.heightIn(min = Target)) { Text("Retry now") }
        qualityLabel(item)?.let {
            Text(it, style = timeStyle, color = muted, maxLines = 1, modifier = Modifier.padding(top = 4.dp).border(1.dp, p.edgeStrong, themeShape(4.dp)).padding(horizontal = 8.dp, vertical = 1.dp))
        }
        Row(Modifier.fillMaxWidth().padding(top = 4.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(formatTime(shown), style = timeStyle, color = muted, modifier = Modifier.padding(end = 8.dp))
            SeekBar(
                fraction = fraction, enabled = duration > 0,
                onChange = { dragging = it },
                onFinish = { dragging?.let { controller.seekTo((it * duration).toLong()) }; dragging = null },
                modifier = Modifier.weight(1f).semantics {
                    contentDescription = "Seek"
                    stateDescription = seekDescription(shown, duration)
                },
                peaks = line.peaks,
            )
            Text(if (duration > 0) formatTime(duration) else "--:--", style = timeStyle, color = muted, modifier = Modifier.padding(start = 8.dp))
        }
        // The joined transport: four segments in one frame.
        Spacer(Modifier.height(8.dp))
        Row(
            Modifier.padding(end = 4.dp, bottom = 4.dp).fillMaxWidth().height(56.dp).brutalShadow(shape).clip(shape).background(p.surface).border(rule, p.edgeStrong, shape),
        ) {
            TransportSegment("Previous song", false, true, controller::previous) { Icon(PlayerIcons.Previous, contentDescription = null, tint = it) }
            Seam()
            TransportSegment(if (state.isPlaying) "Pause" else "Play", true, true, controller::playPause) {
                Icon(if (state.isPlaying) PlayerIcons.Pause else PlayerIcons.Play, contentDescription = null, tint = it, modifier = Modifier.size(32.dp))
            }
            Seam()
            TransportSegment("Next song", false, state.queue.items.size > 1, controller::next) { Icon(PlayerIcons.Next, contentDescription = null, tint = it) }
            Seam()
            TransportSegment("Queue", view == SHEET_VIEW_QUEUE, true, { onView(SheetStackRules.toggleView(view, SHEET_VIEW_QUEUE)) }, selectedState = view == SHEET_VIEW_QUEUE) {
                Icon(PlayerIcons.List, contentDescription = null, tint = it)
            }
        }
        // The lyrics strip: the line being sung, or the same "no lyrics" words as the Lyrics view. Tapping opens the lyrics under it.
        Spacer(Modifier.height(16.dp))
        Row(
            Modifier.padding(end = 4.dp, bottom = 4.dp).fillMaxWidth().heightIn(min = 56.dp).brutalShadow(shape).clip(shape)
                .background(if (view == SHEET_VIEW_LYRICS) p.accentDim else p.surface).border(rule, p.edgeStrong, shape)
                .clickable(onClickLabel = if (view == SHEET_VIEW_LYRICS) "Hide lyrics" else "Show lyrics", role = Role.Button) { onView(SheetStackRules.toggleView(view, SHEET_VIEW_LYRICS)) }
                .padding(horizontal = 16.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(PlayerIcons.Quote, contentDescription = null, modifier = Modifier.size(20.dp))
            // The line when there is one (lyric, or a fact with its small label); otherwise the strip's own words (loading, none, tap to read).
            val l = line.line
            Column(Modifier.weight(1f).padding(start = 16.dp).semantics { stateDescription = if (view == SHEET_VIEW_LYRICS) "Lyrics open" else "Lyrics closed" }) {
                if (l is app.discair.player.PlayerLine.Fact) Text("Fact", style = MaterialTheme.typography.labelSmall.copy(fontFamily = mono), color = muted)
                if (l is app.discair.player.PlayerLine.Empty) Text(SheetStackRules.lyricsStripText(lyricsState, currentLine), style = MaterialTheme.typography.bodyMedium, maxLines = 2, overflow = TextOverflow.Ellipsis)
                else PlayerLineText(l, Modifier, TextAlign.Start)
            }
            LineSwitches(line)
        }
        if (view == SHEET_VIEW_QUEUE || view == SHEET_VIEW_LYRICS) {
            Spacer(Modifier.height(16.dp))
            Box(
                Modifier.padding(end = 4.dp, bottom = 4.dp).fillMaxWidth().height(PanelHeight).brutalShadow(shape).clip(shape)
                    .background(p.surface).border(rule, p.edgeStrong, shape).padding(horizontal = 16.dp),
            ) {
                if (view == SHEET_VIEW_QUEUE) QueuePanel(state, controller, Modifier.fillMaxSize()) else lyricsPanel()
            }
        }
        Spacer(Modifier.height(16.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
            EqualizerLink(onEqualizer)
            Spacer(Modifier.size(16.dp))
            CrossfadeLink(onCrossfade)
        }
    }
}

@Composable
private fun RowScope.TransportSegment(
    label: String, filled: Boolean, enabled: Boolean, onClick: () -> Unit, selectedState: Boolean? = null, content: @Composable (Color) -> Unit,
) {
    val p = LocalPalette.current
    val fill = if (!enabled) p.raised else if (filled) p.accent else p.surface
    val ink = if (!enabled) p.textMuted else if (filled) p.onAccent else p.text
    Box(
        Modifier.weight(if (label == "Play" || label == "Pause") 1.4f else 1f).fillMaxHeight().background(fill)
            .clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .semantics { contentDescription = label; if (selectedState != null) selected = selectedState },
        contentAlignment = Alignment.Center,
    ) { content(ink) }
}

@Composable
private fun Seam() {
    val p = LocalPalette.current
    Box(Modifier.width((p.shape?.outline ?: 2).dp).fillMaxHeight().background(p.edgeStrong))
}
