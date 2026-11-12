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
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.layout.width
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import kotlinx.coroutines.flow.first
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MoreVert
import app.discair.ui.common.DropdownMenu
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
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.OutlinedButton
import app.discair.ui.common.Target
import androidx.compose.runtime.produceState
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import app.discair.ui.common.RowDivider
import app.discair.model.ArtworkImage
import app.discair.model.ArtworkSize
import app.discair.model.trackImages
import app.discair.ui.common.LocalImageLoader
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.semantics.clearAndSetSemantics
import coil3.compose.AsyncImage

/**
 * The Track images of the playing album (idea 6): each a card with its type and edition as the caption (plain text). Nothing is drawn
 * for an empty list. The picture is read by its label, so the caption is hidden from screen readers to avoid saying it twice.
 */
@Composable
fun TrackImageCards(tracks: List<ArtworkImage>, modifier: Modifier = Modifier) {
    if (tracks.isEmpty()) return
    val repo = LocalRepository.current
    Column(modifier.fillMaxWidth()) {
        tracks.forEach { image ->
            val url = remember(image) { repo.artworkImageUrl(image, ArtworkSize.Display) } ?: return@forEach
            Column(Modifier.fillMaxWidth().padding(bottom = 8.dp)) {
                AsyncImage(
                    model = url, contentDescription = image.label(), imageLoader = LocalImageLoader.current,
                    contentScale = ContentScale.Fit,
                    modifier = Modifier.fillMaxWidth().heightIn(max = 180.dp),
                )
                Text(
                    image.label(), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 2, overflow = TextOverflow.Ellipsis, modifier = Modifier.padding(top = 4.dp).clearAndSetSemantics {},
                )
            }
        }
    }
}

/** The queue: tap a row to play it; the menu has Move up, Move down and Remove (no drag-only reordering). */
@Composable
fun QueuePanel(state: PlayerUiState, controller: PlayerController, modifier: Modifier = Modifier) {
    val items = state.queue.items
    val repo = LocalRepository.current
    val play = LocalPlayActions.current
    // Sounds-like shows only when the server says it has sonic similarity; read live, false when unknown.
    val sonic by produceState(false, repo) { value = withContext(Dispatchers.IO) { repo.sonicAvailable() } }
    val queuedIds = items.mapTo(HashSet()) { it.songId }
    var pathTo by remember { mutableStateOf<app.discair.player.QueueItem?>(null) }
    pathTo?.let { target -> state.current?.let { SonicPathSheet(it, target) { pathTo = null } } }
    Column(modifier.fillMaxWidth()) {
        Text(
            "Queue · ${items.size} ${if (items.size == 1) "song" else "songs"}",
            style = MaterialTheme.typography.titleMedium,
            modifier = Modifier.padding(vertical = 8.dp).semantics { heading() },
        )
        if (state.status != null) {
            Text(state.status, style = MaterialTheme.typography.bodySmall, color = app.discair.ui.theme.Ink.AccentText, modifier = Modifier.padding(bottom = 8.dp))
        }
        val playing = state.current
        if (sonic && playing != null) {
            OutlinedButton(
                onClick = { play.soundsLike(playing.songId, queuedIds) },
                Modifier.heightIn(min = Target).padding(bottom = 8.dp),
            ) { Text("Add songs that sound like this") }
        }
        // The playing album's Track images (docs/artwork.md, idea 6): a card each, shown only when the album has some.
        TrackImageCards(trackImages(rememberAlbumArtIndex(playing)), Modifier.padding(bottom = 8.dp))
        val list = rememberLazyListState()
        // Opening the queue brings the playing song into view when it is not already on screen.
        LaunchedEffect(Unit) {
            if (items.isEmpty()) return@LaunchedEffect
            val shown = snapshotFlow { list.layoutInfo.visibleItemsInfo }.first { it.isNotEmpty() }
            if (shown.none { it.index == state.queue.index }) list.scrollToItem(state.queue.index.coerceIn(0, items.lastIndex))
        }
        LazyColumn(Modifier.fillMaxWidth().weight(1f), state = list) {
            itemsIndexed(items, key = { index, item -> "$index-${item.songId}" }) { index, item ->
                val current = index == state.queue.index
                val unavailable = item.songId in state.queue.unavailable
                var menu by remember { mutableStateOf(false) }
                Row(
                    Modifier.fillMaxWidth().heightIn(min = 56.dp)
                        .clickable(onClickLabel = "Play this song", role = Role.Button) { if (!unavailable) controller.skipTo(index) },
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    // The song's place in the queue.
                    Text(
                        "${index + 1}", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
                        textAlign = TextAlign.End, maxLines = 1, modifier = Modifier.width(32.dp).padding(end = 8.dp),
                    )
                    app.discair.ui.common.Cover(item.coverUrl.ifBlank { null }, Modifier.padding(end = 16.dp).size(40.dp))
                    Column(Modifier.weight(1f).padding(vertical = 8.dp)) {
                        // The state is a moving icon beside the title (still when paused, spoken as words) or the word Unavailable; never colour alone.
                        if (unavailable) Text("Unavailable", style = MaterialTheme.typography.labelSmall, color = app.discair.ui.theme.Ink.AccentText)
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                item.title, style = MaterialTheme.typography.bodyMedium,
                                fontWeight = if (current) FontWeight.Bold else FontWeight.Normal, maxLines = 1, overflow = TextOverflow.Ellipsis,
                                modifier = Modifier.weight(1f, fill = false),
                            )
                            if (current && !unavailable) NowPlayingIndicator(state.isPlaying, Modifier.padding(start = 8.dp))
                        }
                        Text(item.artist, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    }
                    Column {
                        IconButton(onClick = { menu = true }, Modifier.size(Target)) {
                            Icon(Icons.Default.MoreVert, contentDescription = "Actions for ${item.title}")
                        }
                        DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                            DropdownMenuItem(text = { Text("Move up") }, enabled = index > 0, onClick = { menu = false; controller.move(index, index - 1) })
                            DropdownMenuItem(text = { Text("Move down") }, enabled = index < items.lastIndex, onClick = { menu = false; controller.move(index, index + 1) })
                            if (sonic) DropdownMenuItem(text = { Text("Add songs that sound like this") }, onClick = { menu = false; play.soundsLike(item.songId, queuedIds) })
                            if (sonic && state.current != null && !current) DropdownMenuItem(text = { Text("Sonic path from playing song to this one") }, onClick = { menu = false; pathTo = item })
                            DropdownMenuItem(text = { Text("Remove from queue") }, onClick = { menu = false; controller.remove(index) })
                        }
                    }
                }
                RowDivider()
            }
        }
    }
}
