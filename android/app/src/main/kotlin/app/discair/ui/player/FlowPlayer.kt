package app.discair.ui.player

import app.discair.ui.common.FlowIcons
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
import app.discair.ui.common.Cover
import app.discair.ui.common.FlowRules
import app.discair.ui.common.Target
import app.discair.ui.common.flowBar
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.LocalThemePalette

/**
 * Flow only: the mini player above the navigation capsule while a song is queued. A 56dp translucent capsule (radius 18, level 2 depth) with a
 * 40dp cover, the title, the artist (or the reason it is not playing) and play or pause. Tapping the text opens Now Playing (mockup: flow/home).
 */
@Composable
fun FlowMiniPlayer(state: PlayerUiState, controller: PlayerController, onOpen: () -> Unit, modifier: Modifier = Modifier) {
    val item = state.current ?: return
    val p = LocalThemePalette.current ?: LocalPalette.current
    Row(
        modifier.fillMaxWidth().padding(horizontal = 12.dp).flowBar(RoundedCornerShape(FlowRules.RADIUS_MINI.dp), p)
            .height(56.dp).padding(start = 8.dp, end = 6.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Box(Modifier.size(40.dp).clip(RoundedCornerShape(9.dp))) {
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
        ) { Icon(if (state.isPlaying) FlowIcons.Pause else FlowIcons.Play, contentDescription = null, modifier = Modifier.size(24.dp)) }
    }
}
