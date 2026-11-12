package app.discair.ui.player

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.RectangleShape
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.player.PlayerController
import app.discair.player.PlayerUiState
import app.discair.player.QueueItem
import app.discair.player.RepeatMode
import app.discair.player.qualityLabel
import app.discair.ui.common.BrutalIconButton
import app.discair.ui.common.Cover
import app.discair.ui.common.TapeDeckRules
import app.discair.ui.common.TapeMeter
import app.discair.ui.common.Target
import app.discair.ui.theme.rememberReducedMotion
import app.discair.ui.theme.LocalFontPair
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.brutalShadow

/** Height of the playlist and lyrics panel under the player card; the panels scroll inside it. */
private val PanelHeight = 380.dp

/**
 * Cassette Deck only: Now Playing as one player card with the queue shown as a playlist under it, in place of the Standard
 * layout's flip card (queue and lyrics on its faces). The cover is a 68dp square with a hard shadow beside "Track n of m", the title
 * and a five-bar meter; then a seek bar, a square transport and the extras. The lyrics button swaps the playlist for the lyrics
 * (the same lyrics view and the same fetching as the Standard layout's lyrics face). Every control does what its Standard twin does.
 */
@Composable
fun TapePlayer(
    state: PlayerUiState, controller: PlayerController, showLyrics: Boolean, onToggleLyrics: () -> Unit,
    onSignIn: () -> Unit, onEqualizer: () -> Unit, onCrossfade: () -> Unit,
    onOpenArtist: (QueueItem) -> Unit, onOpenAlbum: (QueueItem) -> Unit,
    onCoverColor: (Color) -> Unit, line: LineUi, lyricsPanel: @Composable () -> Unit, disc: app.discair.model.ArtworkImage? = null,
) {
    val item = state.current ?: return
    val p = LocalPalette.current
    val rule = (p.shape?.outline ?: 2).dp
    val mono = LocalFontPair.current.mono
    val reduced = rememberReducedMotion()
    var dragging by remember { mutableStateOf<Float?>(null) }
    val duration = state.durationMs
    val fraction = dragging ?: if (duration > 0) (state.positionMs.toFloat() / duration).coerceIn(0f, 1f) else 0f
    val shown = if (dragging != null) (fraction * duration).toLong() else state.positionMs
    val timeStyle = MaterialTheme.typography.labelSmall.copy(fontFamily = mono)
    val muted = MaterialTheme.colorScheme.onSurfaceVariant

    Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(bottom = 24.dp)) {
        // The player card: a framed box with a hard shadow.
        Column(
            Modifier.padding(end = 8.dp, bottom = 8.dp).fillMaxWidth().brutalShadow(RectangleShape)
                .background(p.surface).border(rule, p.edgeStrong).padding(16.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(68.dp).brutalShadow(RectangleShape).border(rule, p.edgeStrong)) {
                    Cover(playerArtworkUrl(item.coverUrl), Modifier.fillMaxSize(), rect = true, onColor = onCoverColor)
                }
                Column(Modifier.weight(1f).padding(start = 16.dp)) {
                    val label = TapeDeckRules.trackLabel(state.queue.index, state.queue.items.size)
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        if (label.isNotEmpty()) Text(label, style = timeStyle, color = muted, modifier = Modifier.weight(1f, fill = false))
                        Spacer(Modifier.size(8.dp))
                        TapeMeter(5, TapeDeckRules.meterMoves(state.isPlaying, state.buffering, reduced), p.text, size = 18.dp)
                    }
                    Text(
                        item.title, style = MaterialTheme.typography.titleMedium, maxLines = 2, overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite; heading() },
                    )
                    // The artist and the album each open their own page, as on the Standard Now Playing.
                    if (item.artist.isNotBlank()) Text(
                        item.artist, style = MaterialTheme.typography.bodyMedium, color = muted, maxLines = 1, overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.heightIn(min = Target).clickable(onClickLabel = "Open artist", role = Role.Button) { onOpenArtist(item) }
                            .wrapContentHeight(Alignment.CenterVertically),
                    )
                }
                // The disc label (docs/artwork.md, idea 3): it turns while the song plays and stands still otherwise.
                if (disc != null) DiscImage(disc, 56.dp, state.isPlaying, Modifier.padding(start = 8.dp))
            }
            if (item.album.isNotBlank()) Text(
                listOfNotNull(item.album, item.year?.toString()).joinToString(" · "), style = MaterialTheme.typography.bodySmall, color = muted,
                maxLines = 1, overflow = TextOverflow.Ellipsis,
                modifier = Modifier.fillMaxWidth().heightIn(min = Target).clickable(onClickLabel = "Open album", role = Role.Button) { onOpenAlbum(item) }
                    .wrapContentHeight(Alignment.CenterVertically),
            )
            // The line (synced lyric or a fact) in a ruled row with its two switches.
            Row(
                Modifier.fillMaxWidth().padding(vertical = 4.dp).border(rule, p.edgeStrong).padding(start = 12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                PlayerLineText(line.line, Modifier.weight(1f), TextAlign.Start)
                LineSwitches(line)
            }
            // Status in words: loading, buffering, lost connection, unavailable, queue full.
            if (state.status != null || state.buffering) {
                Text(
                    playerSubtitle(state), style = MaterialTheme.typography.bodyMedium, color = app.discair.ui.theme.Ink.AccentText,
                    modifier = Modifier.fillMaxWidth().semantics { liveRegion = LiveRegionMode.Polite },
                )
            }
            if (state.signInRequired) TextButton(onClick = { controller.dismissSignIn(); onSignIn() }, Modifier.heightIn(min = Target)) { Text("Sign in again") }
            if (state.waitingForNetwork) TextButton(onClick = controller::retryNow, Modifier.heightIn(min = Target)) { Text("Retry now") }

            qualityLabel(item)?.let {
                Text(it, style = timeStyle, color = muted, maxLines = 1, modifier = Modifier.padding(top = 4.dp).border(1.dp, p.edgeStrong).padding(horizontal = 8.dp, vertical = 1.dp))
            }
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
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
            // The square transport, with the lyrics button at its end.
            Row(Modifier.fillMaxWidth().padding(top = 4.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                val shuffle = state.queue.shuffle
                BrutalIconButton(
                    onClick = { controller.setShuffle(!shuffle) }, selected = shuffle,
                    modifier = Modifier.size(48.dp).semantics { stateDescription = if (shuffle) "On" else "Off" },
                ) { Icon(PlayerIcons.Shuffle, contentDescription = "Shuffle") }
                BrutalIconButton(onClick = controller::previous, modifier = Modifier.size(48.dp)) { Icon(PlayerIcons.Previous, contentDescription = "Previous song") }
                BrutalIconButton(onClick = controller::playPause, primary = true, modifier = Modifier.size(56.dp)) {
                    Icon(if (state.isPlaying) PlayerIcons.Pause else PlayerIcons.Play, contentDescription = if (state.isPlaying) "Pause" else "Play", modifier = Modifier.size(32.dp))
                }
                BrutalIconButton(onClick = controller::next, enabled = state.queue.items.size > 1, modifier = Modifier.size(48.dp)) { Icon(PlayerIcons.Next, contentDescription = "Next song") }
                val repeat = state.queue.repeat
                BrutalIconButton(
                    onClick = controller::cycleRepeat, selected = repeat != RepeatMode.Off,
                    modifier = Modifier.size(48.dp).semantics { stateDescription = when (repeat) { RepeatMode.Off -> "Off"; RepeatMode.All -> "Repeat all"; RepeatMode.One -> "Repeat one" } },
                ) { Icon(if (repeat == RepeatMode.One) PlayerIcons.RepeatOne else PlayerIcons.Repeat, contentDescription = "Repeat") }
                BrutalIconButton(
                    onClick = onToggleLyrics, selected = showLyrics,
                    modifier = Modifier.size(48.dp).semantics { stateDescription = if (showLyrics) "Showing lyrics" else "Showing the queue" },
                ) { Icon(PlayerIcons.Quote, contentDescription = if (showLyrics) "Hide lyrics, show the queue" else "Show lyrics") }
            }
        }
        Spacer(Modifier.height(16.dp))
        // The playlist (or the lyrics) under the card, in its own ruled box.
        Box(
            Modifier.padding(end = 8.dp, bottom = 8.dp).fillMaxWidth().height(PanelHeight).brutalShadow(RectangleShape)
                .background(p.surface).border(rule, p.edgeStrong).padding(horizontal = 16.dp),
        ) {
            if (showLyrics) lyricsPanel() else QueuePanel(state, controller, Modifier.fillMaxSize())
        }
        Spacer(Modifier.height(16.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
            EqualizerLink(onEqualizer)
            Spacer(Modifier.size(16.dp))
            CrossfadeLink(onCrossfade)
        }
    }
}
