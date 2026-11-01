package app.discair.ui.player

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.player.PlayerController
import app.discair.player.PlayerUiState
import app.discair.ui.common.Cover
import app.discair.ui.common.Target
import app.discair.ui.theme.Ink

/** Words under the title: the reason first (loading, lost connection, unavailable), the artist otherwise. */
fun playerSubtitle(state: PlayerUiState): String {
    val item = state.current ?: return ""
    return when {
        state.status != null -> state.status
        state.buffering && state.isPlaying.not() && state.positionMs == 0L -> "Loading…"
        state.buffering -> "Buffering…"
        else -> item.artist
    }
}

/** The bar above the bottom navigation: cover, title, play or pause, next. Tapping the text opens Now Playing. */
@Composable
fun MiniPlayer(state: PlayerUiState, controller: PlayerController, onOpen: () -> Unit, modifier: Modifier = Modifier) {
    val item = state.current ?: return
    Surface(modifier.fillMaxWidth(), color = Ink.Raised, tonalElevation = 3.dp) {
        Column {
            if (state.durationMs > 0) {
                LinearProgressIndicator(
                    progress = { (state.positionMs.toFloat() / state.durationMs).coerceIn(0f, 1f) },
                    modifier = Modifier.fillMaxWidth().height(2.dp).clearAndSetSemantics { }, // decorative; Now Playing has the seek bar
                    color = MaterialTheme.colorScheme.primary,
                    trackColor = Ink.Edge,
                )
            }
            Row(
                Modifier.fillMaxWidth().height(64.dp).padding(start = 8.dp, end = 4.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Cover(item.coverUrl.ifBlank { null }, Modifier.size(48.dp))
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
                IconButton(onClick = controller::playPause, modifier = Modifier.size(Target)) {
                    Icon(
                        if (state.isPlaying) PlayerIcons.Pause else PlayerIcons.Play,
                        contentDescription = if (state.isPlaying) "Pause" else "Play",
                    )
                }
                IconButton(onClick = controller::next, modifier = Modifier.size(Target), enabled = state.queue.items.size > 1) {
                    Icon(PlayerIcons.Next, contentDescription = "Next song")
                }
            }
        }
    }
}
