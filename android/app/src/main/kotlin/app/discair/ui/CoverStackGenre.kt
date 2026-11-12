package app.discair.ui

import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.model.GenrePage
import app.discair.ui.common.ArtistPhoto
import app.discair.ui.common.CoverStackCover
import app.discair.ui.common.CoverStackDivider
import app.discair.ui.common.CoverStackRules
import app.discair.ui.common.CoverStackTabs
import app.discair.ui.common.CoverStackTitle
import app.discair.ui.common.CoverStackTopBar
import app.discair.ui.common.Loaded
import app.discair.ui.common.LoadView
import app.discair.ui.common.plural
import app.discair.ui.theme.LocalPalette

/**
 * Soft Brut's Genre page (mockup soft-brut/album-artist-genre, frame 3): the genre as a large title with its counts, an Albums | Artists
 * group, then albums as a two-column grid of outlined covers or artists as rows with round photos. Which items are in the library is said in words.
 * The data and the taps are the Standard page's; only the arrangement is new.
 */
@Composable
internal fun CoverStackGenre(route: GenreRoute, loaded: Loaded<GenrePage>, open: Opener) {
    val p = LocalPalette.current
    var tab by rememberSaveable { mutableIntStateOf(0) }
    Column(Modifier.fillMaxSize()) {
        CoverStackTopBar(open.back, emptyList(), title = route.name)
        LoadView(loaded) { page ->
            val artists = page.sections.artists.items
            val albums = page.sections.albums.items
            LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 32.dp + LocalBottomClearance.current)) {
                item {
                    Column(Modifier.padding(horizontal = 16.dp, vertical = 8.dp)) {
                        CoverStackTitle(route.name)
                        Text(
                            plural(albums.size, "album") + " · " + plural(artists.size, "artist"),
                            color = p.textMuted, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(top = 2.dp),
                        )
                    }
                }
                if (artists.isEmpty() && albums.isEmpty()) item {
                    Text("Nothing found for this genre.", Modifier.padding(16.dp), color = p.textMuted)
                } else {
                    item { CoverStackTabs(listOf("Albums", "Artists"), tab, { tab = it }, Modifier.padding(start = 16.dp, end = 19.dp, top = 8.dp, bottom = 14.dp).fillMaxWidth()) }
                    if (tab == 0) {
                        if (albums.isEmpty()) item { Text("No albums for this genre.", Modifier.padding(16.dp), color = p.textMuted) }
                        items(albums.chunked(2)) { pair ->
                            Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp).padding(bottom = 14.dp), horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                                pair.forEach { a ->
                                    Column(
                                        Modifier.weight(1f).clip(androidx.compose.foundation.shape.RoundedCornerShape(8.dp))
                                            .clickable(role = Role.Button) { open.album(a.key, a.artist, a.name, a.id, a.year) },
                                        verticalArrangement = Arrangement.spacedBy(2.dp),
                                    ) {
                                        CoverStackCover(a.artist, a.name, null, Modifier.fillMaxWidth(), radius = CoverStackRules.radius(p).toInt())
                                        Text(a.name, Modifier.padding(top = 6.dp), color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold, fontSize = 14.sp))
                                        Text(
                                            listOfNotNull(a.artist.ifBlank { null }, a.year?.toString()).joinToString(" · ").ifEmpty { " " },
                                            color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall,
                                        )
                                        if (a.owned) Text("In your library", color = p.ok, style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.SemiBold))
                                    }
                                }
                                if (pair.size == 1) Box(Modifier.weight(1f))
                            }
                        }
                    } else {
                        if (artists.isEmpty()) item { Text("No artists for this genre.", Modifier.padding(16.dp), color = p.textMuted) }
                        items(artists, key = { it.key.ifEmpty { it.name } }) { a ->
                            Column {
                                Row(
                                    Modifier.fillMaxWidth().heightIn(min = 64.dp).clickable(role = Role.Button) { open.artist(a.name, a.key, a.id, null) }.padding(horizontal = 16.dp, vertical = 8.dp),
                                    horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
                                ) {
                                    ArtistPhoto(a.name, null, Modifier.size(48.dp).clip(CircleShape).border(CoverStackRules.outline(p).dp, p.edgeStrong, CircleShape), circle = true)
                                    Column(Modifier.weight(1f)) {
                                        Text(a.name, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 14.sp))
                                        Text(if (a.owned) "In your library" else "Not in your library", color = if (a.owned) p.ok else p.textMuted, style = MaterialTheme.typography.bodySmall)
                                    }
                                }
                                CoverStackDivider(Modifier.padding(horizontal = 16.dp))
                            }
                        }
                    }
                }
            }
        }
    }
}
