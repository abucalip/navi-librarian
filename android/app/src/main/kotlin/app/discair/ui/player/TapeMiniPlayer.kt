package app.discair.ui.player

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.RectangleShape
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.player.PlayerController
import app.discair.player.PlayerUiState
import app.discair.ui.common.BrutalIconButton
import app.discair.ui.common.Cover
import app.discair.ui.common.TapeDeckRules
import app.discair.ui.common.TapeMeter
import app.discair.ui.common.Target
import app.discair.ui.theme.rememberReducedMotion
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.LocalThemePalette

/**
 * Cassette Deck only: the mini player that sits on the ruled navigation bar while a song is queued (the Standard layout has none).
 * Cover, title and artist, a three-bar meter, play or pause and next, and a seek strip along the bottom edge. Tapping the text opens
 * Now Playing; the strip is decorative (Now Playing has the seek bar) and the meter stops when playback is not really running.
 */
@Composable
fun TapeMiniPlayer(state: PlayerUiState, controller: PlayerController, onOpen: () -> Unit, modifier: Modifier = Modifier) {
    val item = state.current ?: return
    val p = LocalThemePalette.current ?: LocalPalette.current
    val rule = (p.shape?.outline ?: 2f).dp
    val reduced = rememberReducedMotion()
    val fraction = if (state.durationMs > 0) (state.positionMs.toFloat() / state.durationMs).coerceIn(0f, 1f) else 0f
    Column(modifier.fillMaxWidth().background(p.surface)) {
        Box(Modifier.fillMaxWidth().height(rule).background(p.edgeStrong))
        Row(
            Modifier.fillMaxWidth().height(64.dp).padding(start = 8.dp, end = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Box(Modifier.size(48.dp).border(rule, p.edgeStrong)) { Cover(item.coverUrl.ifBlank { null }, Modifier.fillMaxSize(), rect = true) }
            Column(
                Modifier.weight(1f).height(Target).clickable(onClickLabel = "Open now playing", role = Role.Button, onClick = onOpen),
                verticalArrangement = Arrangement.Center,
            ) {
                Text(
                    item.title, style = MaterialTheme.typography.bodyMedium, maxLines = 1, overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite }, // spoken once when the track changes
                )
                Text(
                    playerSubtitle(state), style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis,
                )
            }
            TapeMeter(3, TapeDeckRules.meterMoves(state.isPlaying, state.buffering, reduced), p.text, size = 16.dp)
            BrutalIconButton(
                onClick = controller::playPause, primary = true,
                modifier = Modifier.size(44.dp).semantics { contentDescription = if (state.isPlaying) "Pause" else "Play" },
            ) { Icon(if (state.isPlaying) PlayerIcons.Pause else PlayerIcons.Play, contentDescription = null, modifier = Modifier.size(24.dp)) }
            BrutalIconButton(
                onClick = controller::next, enabled = state.queue.items.size > 1,
                modifier = Modifier.size(44.dp).semantics { contentDescription = "Next song" },
            ) { Icon(PlayerIcons.Next, contentDescription = null, modifier = Modifier.size(24.dp)) }
        }
        // The seek strip along the bottom edge: decorative, like the Standard mini player's thin bar.
        Box(Modifier.fillMaxWidth().height(6.dp).background(p.raised).clearAndSetSemantics { }) {
            Box(Modifier.fillMaxHeight().fillMaxWidth(fraction).background(p.accent))
        }
    }
}
