package app.discair.ui.player

import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.player.PlayerController
import app.discair.player.PlayerUiState
import app.discair.ui.common.CoverStackRules
import app.discair.ui.common.Cover
import app.discair.ui.common.Target
import app.discair.ui.common.coverStackFrame
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.LocalThemePalette

/**
 * Cover Stack only: the mini player above the navigation bar while a song is queued. A 56dp outlined card with a 40dp outlined cover,
 * the title, the artist (or the reason it is not playing) and play or pause. Tapping the text opens Now Playing (mockup: soft-brut/home).
 */
@Composable
fun CoverStackMiniPlayer(state: PlayerUiState, controller: PlayerController, onOpen: () -> Unit, modifier: Modifier = Modifier) {
    val item = state.current ?: return
    val p = LocalThemePalette.current ?: LocalPalette.current
    val ol = CoverStackRules.outline(p).dp
    Row(
        modifier.fillMaxWidth().padding(start = 12.dp, end = 15.dp).coverStackFrame(RoundedCornerShape(CoverStackRules.radius(p).dp), p)
            .height(56.dp).padding(start = 7.dp, end = 4.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Box(Modifier.size(40.dp).clip(RoundedCornerShape(6.dp)).border(ol, p.edgeStrong, RoundedCornerShape(6.dp))) {
            Cover(item.coverUrl.ifBlank { null }, Modifier.fillMaxSize(), rect = true)
        }
        Column(
            Modifier.weight(1f).height(Target).clickable(onClickLabel = "Open now playing", role = Role.Button, onClick = onOpen),
            verticalArrangement = Arrangement.Center,
        ) {
            Text(
                item.title, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold), maxLines = 1, overflow = TextOverflow.Ellipsis,
                modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
            )
            Text(playerSubtitle(state), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
        Box(
            Modifier.size(Target).clickable(role = Role.Button, onClick = controller::playPause)
                .semantics { contentDescription = if (state.isPlaying) "Pause" else "Play" },
            contentAlignment = Alignment.Center,
        ) { Icon(if (state.isPlaying) PlayerIcons.Pause else PlayerIcons.Play, contentDescription = null, modifier = Modifier.size(24.dp)) }
    }
}
