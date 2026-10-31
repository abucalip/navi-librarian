package app.discair.ui.common

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.ui.Opener
import app.discair.ui.theme.Display
import app.discair.ui.theme.Ink
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** What the Save control shows. Only [Saved] means the server confirmed. */
enum class SaveState { Idle, Pending, Saved, Failed }

/** What a row's leading column shows: the position in the list, or the release date. */
sealed interface RowLead {
    data class Rank(val n: Int) : RowLead
    data class Date(val day: String, val year: String) : RowLead
    data object None : RowLead
}

/** Everything a row needs; the screens build it, the row never decides anything. */
data class RowModel(
    val artist: String,
    val album: String,
    val year: Int?,
    val lead: RowLead,
    val meta: List<String>,
    val bio: Boolean,
    /** The row exactly as the server sent it; Get sends it back as `metadata`, as the web does. */
    val metadata: kotlinx.serialization.json.JsonObject = kotlinx.serialization.json.JsonObject(emptyMap()),
    /** The server says the album is already in the library: show the check instead of Get. */
    val owned: Boolean = false,
)

/**
 * The shared ranked album row (contract 6.5, web PRs #533 and #554): lead column, artwork, title,
 * artist, meta lines, artist bio that expands on tap, and the Get, Save and Not-for-me controls.
 * Rows keep the order the server sent; the row only draws.
 */
@Composable
fun RankedRow(
    model: RowModel,
    open: Opener,
    saveState: SaveState,
    onSave: () -> Unit,
    onDismiss: (artistToo: Boolean) -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(modifier.fillMaxWidth().padding(start = 16.dp, end = 4.dp, top = 8.dp, bottom = 8.dp)) {
        Box(Modifier.width(if (model.lead is RowLead.Date) 48.dp else 36.dp).padding(top = 4.dp).clearAndSetSemantics {}) {
            when (val lead = model.lead) {
                is RowLead.Rank -> Text(
                    "%02d".format(lead.n), style = MaterialTheme.typography.titleLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                is RowLead.Date -> Column {
                    if (lead.day.isNotEmpty()) Text(lead.day, style = MaterialTheme.typography.labelMedium)
                    Text(lead.year, style = MaterialTheme.typography.labelSmall, color = Ink.Accent)
                }
                RowLead.None -> Unit
            }
        }
        AlbumCover(
            model.artist, model.album, null,
            Modifier.size(72.dp).clickable {
                open.album(routeKey(model.artist, model.album), model.artist, model.album, null, model.year)
            },
        )
        Column(Modifier.weight(1f).padding(start = 12.dp)) {
            Text(
                model.album, style = MaterialTheme.typography.titleLarge.copy(fontFamily = Display),
                maxLines = 2, overflow = TextOverflow.Ellipsis,
                modifier = Modifier.clickable {
                    open.album(routeKey(model.artist, model.album), model.artist, model.album, null, model.year)
                },
            )
            Text(
                model.artist, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.primary,
                maxLines = 1, overflow = TextOverflow.Ellipsis,
                modifier = Modifier.heightIn(min = Target).clickable { open.artist(model.artist, null, null, null) }
                    .padding(vertical = 12.dp),
            )
            model.meta.forEach {
                Text(
                    it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 2, overflow = TextOverflow.Ellipsis,
                )
            }
            if (model.bio) ArtistBio(model.artist)
        }
        Column {
            if (model.owned) Box(Modifier.size(Target), contentAlignment = Alignment.Center) { OwnedMark(true) }
            else GetAlbumButton(model.artist, model.album, model.metadata)
            SaveButton(model.album, saveState, onSave)
            DismissMenu(model.album, model.artist, onDismiss)
        }
    }
}

/** The artist biography, three lines until tapped. Fetched when the row first appears. */
@Composable
private fun ArtistBio(artist: String) {
    val repo = LocalRepository.current
    val bio by produceState<String?>(null, artist) { value = withContext(Dispatchers.IO) { repo.artistBio(artist) } }
    var expanded by remember(artist) { mutableStateOf(false) }
    bio?.let {
        Text(
            it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = if (expanded) Int.MAX_VALUE else 3, overflow = TextOverflow.Ellipsis,
            modifier = Modifier.padding(top = 2.dp).clickable { expanded = !expanded }.semantics {
                stateDescription = if (expanded) "Expanded" else "Collapsed"
            },
        )
    }
}

/** Save is a bookmark. The four states differ by icon and spoken state, not by colour alone. */
@Composable
fun SaveButton(album: String, state: SaveState, onClick: () -> Unit) {
    IconButton(
        onClick = { if (state != SaveState.Pending) onClick() },
        Modifier.size(Target).semantics {
            contentDescription = "Save $album"
            stateDescription = when (state) {
                SaveState.Idle -> "Not saved"
                SaveState.Pending -> "Saving"
                SaveState.Saved -> "Saved. Select to undo"
                SaveState.Failed -> "Could not save. Select to try again"
            }
        },
    ) {
        when (state) {
            SaveState.Idle -> Icon(Icons.Default.FavoriteBorder, contentDescription = null)
            SaveState.Pending -> CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
            SaveState.Saved -> Icon(Icons.Default.Favorite, contentDescription = null, tint = Ink.Accent)
            SaveState.Failed -> Icon(Icons.Default.Warning, contentDescription = null, tint = Ink.ChartRedText)
        }
    }
}

/** "Not for me": the choice between the album and the whole artist is a menu, so neither is gesture-only. */
@Composable
private fun DismissMenu(album: String, artist: String, onDismiss: (Boolean) -> Unit) {
    var open by remember { mutableStateOf(false) }
    Box {
        IconButton(onClick = { open = true }, Modifier.size(Target)) {
            Icon(Icons.Default.MoreVert, contentDescription = "Not for me: $album")
        }
        DropdownMenu(open, onDismissRequest = { open = false }) {
            DropdownMenuItem(text = { Text("Not this album") }, onClick = { open = false; onDismiss(false) })
            DropdownMenuItem(text = { Text("Never suggest $artist") }, onClick = { open = false; onDismiss(true) })
        }
    }
}
