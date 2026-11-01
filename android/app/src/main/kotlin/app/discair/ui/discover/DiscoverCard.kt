package app.discair.ui.discover

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.CircleShape
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
import app.discair.ui.common.DismissMenu
import app.discair.ui.common.GetAlbumButton
import app.discair.ui.common.OwnedMark
import app.discair.ui.common.SaveButton
import app.discair.ui.common.SaveState
import app.discair.ui.common.aspectSquare
import app.discair.ui.common.rememberAlbumYear
import app.discair.ui.common.routeKey
import app.discair.ui.theme.Ink

private const val BIO_LINES = 3

/** The round dark backing that keeps a control readable over any cover. */
@Composable
private fun OnCover(modifier: Modifier, content: @Composable () -> Unit) {
    Box(modifier.padding(4.dp).clip(CircleShape).background(Color.Black.copy(alpha = 0.55f))) { content() }
}

/**
 * The Discover album card, two to a row: the cover with Get, Save and Not-for-me laid over it, then the
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
            if (item.acquired) OnCover(Modifier.align(Alignment.BottomStart)) {
                Box(Modifier.padding(12.dp)) { OwnedMark(true) }
            } else OnCover(Modifier.align(Alignment.BottomStart)) { GetAlbumButton(artist, item.album, entry.raw) }
            OnCover(Modifier.align(Alignment.BottomEnd)) { SaveButton(item.album, saveState, onSave) }
            OnCover(Modifier.align(Alignment.TopEnd)) { DismissMenu(item.album, artist, onDismiss) }
        }
        Column(Modifier.padding(start = 12.dp, end = 12.dp, top = 8.dp, bottom = 12.dp)) {
            Text(
                item.album, style = MaterialTheme.typography.titleMedium,
                minLines = 2, maxLines = 2, overflow = TextOverflow.Ellipsis,
                modifier = Modifier.clickable(role = Role.Button, onClick = openAlbum),
            )
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
