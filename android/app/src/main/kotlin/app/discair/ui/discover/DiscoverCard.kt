package app.discair.ui.discover

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.sp
import app.discair.R
import app.discair.model.GetState
import app.discair.ui.common.LocalAcquisitions
import app.discair.ui.common.Target
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.model.DiscoveryEntry
import app.discair.ui.Opener
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.ArtistBio
import app.discair.ui.common.OwnedMark
import app.discair.ui.common.SaveState
import app.discair.ui.common.aspectSquare
import app.discair.ui.common.rememberAlbumYear
import app.discair.ui.common.routeKey
import app.discair.ui.theme.Ink

private const val BIO_LINES = 3

private val TitleMax = 20.sp
private val TitleMin = 14.sp

/**
 * An album title on one line in the display face. A long title shrinks a step at a time down to [TitleMin],
 * the smallest size that still reads well; if it is still too wide it is cut with an ellipsis. Every card
 * keeps the same title height, so the grid stays even without holding back a second line.
 */
@Composable
private fun FitTitle(text: String, modifier: Modifier = Modifier) {
    val base = MaterialTheme.typography.titleLarge
    val measurer = rememberTextMeasurer()
    BoxWithConstraints(modifier) {
        val size = remember(text, constraints.maxWidth, base) {
            var s = TitleMax.value
            while (s > TitleMin.value && measurer.measure(
                    text, base.copy(fontSize = s.sp, lineHeight = (s * 1.05f).sp), maxLines = 1, softWrap = false,
                ).size.width > constraints.maxWidth
            ) s -= 1f
            s
        }
        Text(
            text, style = base.copy(fontSize = size.sp, lineHeight = (TitleMax.value * 1.05f).sp),
            maxLines = 1, softWrap = false, overflow = TextOverflow.Ellipsis,
        )
    }
}

/** The three-dot menu over the cover's top-left corner: Download, Save, and the two ways to say no. */
@Composable
private fun CardMenu(entry: DiscoveryEntry, saveState: SaveState, onSave: () -> Unit, onDismiss: (Boolean) -> Unit, modifier: Modifier) {
    val item = entry.item
    val artist = item.artistName
    val hub = LocalAcquisitions.current
    val get = hub.getState(artist, item.album)
    var open by remember { mutableStateOf(false) }
    Box(modifier) {
        IconButton(onClick = { open = true }, Modifier.size(Target)) {
            // A dark round backing keeps the dots readable on any cover; the old soft halo vanished on white and yellow ones.
            Box(Modifier.size(34.dp).background(Color.Black.copy(alpha = 0.55f), CircleShape), contentAlignment = Alignment.Center) {
                Icon(Icons.Default.MoreVert, contentDescription = "Options for ${item.album}", tint = Color.White)
            }
        }
        DropdownMenu(open, onDismissRequest = { open = false }) {
            val downloadable = !item.acquired && (get is GetState.Idle || get is GetState.Failed)
            DropdownMenuItem(
                text = { Text(if (item.acquired) "In your library" else if (get is GetState.Requested) "Requested" else "Download") },
                leadingIcon = { Icon(painterResource(R.drawable.ic_get_cloud), contentDescription = null) },
                enabled = downloadable,
                onClick = { open = false; hub.getAlbum(artist, item.album, entry.raw) },
            )
            DropdownMenuItem(
                text = { Text(if (saveState == SaveState.Saved) "Saved" else "Save") },
                leadingIcon = {
                    if (saveState == SaveState.Saved) Icon(Icons.Default.Favorite, contentDescription = null, tint = Ink.Accent)
                    else Icon(Icons.Default.FavoriteBorder, contentDescription = null)
                },
                enabled = saveState != SaveState.Pending,
                onClick = { open = false; onSave() },
            )
            DropdownMenuItem(
                text = { Text("Not this album") },
                leadingIcon = { Icon(Icons.Default.Delete, contentDescription = null) },
                onClick = { open = false; onDismiss(false) },
            )
            DropdownMenuItem(
                text = { Text("Not this artist") },
                leadingIcon = { Icon(Icons.Default.Delete, contentDescription = null) },
                onClick = { open = false; onDismiss(true) },
            )
        }
    }
}

/**
 * The Discover album card, two to a row: the cover with a three-dot menu (Download, Save, Not this album, Not this artist) in its corner, then the
 * title, the artist, the year (accent) with the listener count (grey), and the artist's bio. The server's
 * "reason" line is not shown. Order and content come from the server; the card only draws.
 */
@Composable
fun DiscoverCard(
    entry: DiscoveryEntry,
    open: Opener,
    saveState: SaveState,
    onSave: () -> Unit,
    onDismiss: (artistToo: Boolean) -> Unit,
    modifier: Modifier = Modifier,
) {
    val item = entry.item
    val artist = item.artistName
    val listeners = (item.albumListeners ?: item.listeners)?.takeIf { it > 0 }
    val openAlbum = { open.album(routeKey(artist, item.album), artist, item.album, null, item.year) }
    Column(modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(MaterialTheme.colorScheme.surface)) {
        Box {
            AlbumCover(
                artist, item.album, null,
                Modifier.fillMaxWidth().aspectSquare().clickable(role = Role.Button, onClick = openAlbum),
                rect = true,
            )
            CardMenu(entry, saveState, onSave, onDismiss, Modifier.align(Alignment.TopEnd))
            if (item.acquired) Box(Modifier.align(Alignment.BottomStart).padding(8.dp)) { OwnedMark(true) }
        }
        Column(Modifier.padding(start = 12.dp, end = 12.dp, top = 8.dp, bottom = 12.dp)) {
            FitTitle(item.album, Modifier.fillMaxWidth().clickable(role = Role.Button, onClick = openAlbum))
            Text(
                artist, style = MaterialTheme.typography.bodyMedium, color = Ink.Text,
                maxLines = 1, overflow = TextOverflow.Ellipsis,
                modifier = Modifier.clickable(role = Role.Button) { open.artist(artist, null, null, null) },
            )
            val year = rememberAlbumYear(artist, item.album, item.year)
            val line = buildAnnotatedString {
                year?.let { withStyle(SpanStyle(color = Ink.Accent)) { append("$it") } }
                if (year != null && listeners != null) append("  ")
                listeners?.let { withStyle(SpanStyle(color = Ink.TextMuted)) { append("%,d listeners".format(it)) } }
            }
            // Always one line tall, so every card is the same height whether or not a year or count is known yet.
            Text(line.ifEmpty { AnnotatedString(" ") }, style = MaterialTheme.typography.labelMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
            ArtistBio(artist, reserveLines = BIO_LINES, expandable = false)
        }
    }
}
