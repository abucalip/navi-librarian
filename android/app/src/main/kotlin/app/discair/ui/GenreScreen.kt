package app.discair.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.ui.common.BackBar
import app.discair.ui.common.Heading
import app.discair.ui.common.LoadView
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.OwnedMark
import app.discair.ui.common.plural
import app.discair.ui.common.rememberLoad

@Composable
fun GenreScreen(route: GenreRoute, open: Opener) {
    val repo = LocalRepository.current
    val loaded = rememberLoad(route) { repo.genrePage(route.tag) }
    Column(Modifier.fillMaxSize()) {
        BackBar(open.back)
        LoadView(loaded) { page ->
            val artists = page.sections.artists.items
            val albums = page.sections.albums.items
            LazyColumn(Modifier.fillMaxSize(), contentPadding = androidx.compose.foundation.layout.PaddingValues(bottom = 32.dp)) {
                item {
                    Text(
                        route.name, style = MaterialTheme.typography.headlineLarge,
                        modifier = Modifier.padding(horizontal = 16.dp).semantics { heading() },
                    )
                    Text(
                        plural(artists.size + albums.size, "item"),
                        style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
                    )
                }
                if (artists.isNotEmpty()) {
                    item { Heading("Artists", Modifier.padding(horizontal = 16.dp)) }
                    items(artists.size) { i ->
                        val a = artists[i]
                        Row(
                            Modifier.fillMaxWidth().heightIn(min = 52.dp)
                                .clickable { open.artist(a.name, a.key, a.id, null) }.padding(horizontal = 16.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(a.name, style = MaterialTheme.typography.bodyLarge, maxLines = 1, overflow = TextOverflow.Ellipsis,
                                textDecoration = androidx.compose.ui.text.style.TextDecoration.Underline, modifier = Modifier.weight(1f))
                            OwnedMark(a.owned)
                        }
                    }
                }
                if (albums.isNotEmpty()) {
                    item { Heading("Albums", Modifier.padding(horizontal = 16.dp)) }
                    items(albums.size) { i ->
                        val a = albums[i]
                        Row(
                            Modifier.fillMaxWidth().heightIn(min = 56.dp)
                                .clickable { open.album(a.key, a.artist, a.name, a.id, a.year) }.padding(horizontal = 16.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(Modifier.weight(1f)) {
                                Text(a.name, style = MaterialTheme.typography.bodyLarge, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                Text(
                                    listOfNotNull(a.artist.ifBlank { null }, a.year?.toString()).joinToString(" · "),
                                    style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                            OwnedMark(a.owned)
                        }
                    }
                }
                if (artists.isEmpty() && albums.isEmpty()) item {
                    Text("Nothing found for this genre.", Modifier.padding(16.dp), color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}
