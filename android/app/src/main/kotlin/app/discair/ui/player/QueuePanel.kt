package app.discair.ui.player

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.player.PlayerController
import app.discair.player.PlayerUiState
import app.discair.ui.common.Target
import app.discair.ui.common.RowDivider

/** The queue: tap a row to play it; the menu has Move up, Move down and Remove (no drag-only reordering). */
@Composable
fun QueuePanel(state: PlayerUiState, controller: PlayerController, modifier: Modifier = Modifier) {
    val items = state.queue.items
    Column(modifier.fillMaxWidth()) {
        Text(
            "Queue · ${items.size} ${if (items.size == 1) "song" else "songs"}",
            style = MaterialTheme.typography.titleMedium,
            modifier = Modifier.padding(vertical = 8.dp).semantics { heading() },
        )
        if (state.status != null) {
            Text(state.status, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.primary, modifier = Modifier.padding(bottom = 8.dp))
        }
        LazyColumn(Modifier.fillMaxWidth().weight(1f)) {
            itemsIndexed(items, key = { index, item -> "$index-${item.songId}" }) { index, item ->
                val current = index == state.queue.index
                val unavailable = item.songId in state.queue.unavailable
                var menu by remember { mutableStateOf(false) }
                Row(
                    Modifier.fillMaxWidth().heightIn(min = 56.dp)
                        .clickable(onClickLabel = "Play this song", role = Role.Button) { if (!unavailable) controller.skipTo(index) },
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    app.discair.ui.common.Cover(item.coverUrl.ifBlank { null }, Modifier.padding(end = 12.dp).size(40.dp))
                    Column(Modifier.weight(1f).padding(vertical = 8.dp)) {
                        // The state is written out, never colour alone.
                        val tag = when { unavailable -> "Unavailable"; current && state.isPlaying -> "Now playing"; current -> "Paused here"; else -> null }
                        if (tag != null) Text(tag, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
                        Text(item.title, style = MaterialTheme.typography.bodyMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        Text(item.artist, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    }
                    Column {
                        IconButton(onClick = { menu = true }, Modifier.size(Target)) {
                            Icon(Icons.Default.MoreVert, contentDescription = "Actions for ${item.title}")
                        }
                        DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                            DropdownMenuItem(text = { Text("Move up") }, enabled = index > 0, onClick = { menu = false; controller.move(index, index - 1) })
                            DropdownMenuItem(text = { Text("Move down") }, enabled = index < items.lastIndex, onClick = { menu = false; controller.move(index, index + 1) })
                            DropdownMenuItem(text = { Text("Remove from queue") }, onClick = { menu = false; controller.remove(index) })
                        }
                    }
                }
                RowDivider()
            }
        }
    }
}
