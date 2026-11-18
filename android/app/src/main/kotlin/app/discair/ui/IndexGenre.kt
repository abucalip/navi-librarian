package app.discair.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.model.GenrePage
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.ArtistPhoto
import app.discair.ui.common.IndexLabel
import app.discair.ui.common.IndexMuted
import app.discair.ui.common.IndexPageBar
import app.discair.ui.common.IndexPageHead
import app.discair.ui.common.IndexPagesRules
import app.discair.ui.common.IndexRow
import app.discair.ui.common.IndexRules
import app.discair.ui.common.IndexSectionHead
import app.discair.ui.common.IndexType
import app.discair.ui.common.LoadView
import app.discair.ui.common.Loaded
import app.discair.ui.common.indexArrive
import app.discair.ui.common.sharedCover
import app.discair.ui.theme.LocalPalette

private const val ARTISTS_SHOWN = 5
private const val ALBUMS_SHOWN = 12

/*
 * Index's Genre page (Layout.Index). Spec: docs/plans/INDEX_THEME.md step I3; mockup: docs/design/index/pages/album-artist-genre.html, frame 4.
 * The genre as a Display head with its album count, numbered artist rows with their library state, and the albums in a two-column grid. The page has no
 * play action on any theme, so the mockup's Shuffle genre and Discover more are not drawn (listed in the I3 PR).
 */
@Composable
internal fun IndexGenre(route: GenreRoute, loaded: Loaded<GenrePage>, open: Opener) {
    val p = LocalPalette.current
    val gutter = IndexRules.GUTTER.dp
    var allArtists by rememberSaveable(route.tag) { mutableStateOf(false) }
    var allAlbums by rememberSaveable(route.tag) { mutableStateOf(false) }
    Column(Modifier.fillMaxSize()) {
        IndexPageBar("Genre", open.back)
        LoadView(loaded) { page ->
            val artists = page.sections.artists.items
            val albums = page.sections.albums.items
            LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 32.dp + LocalBottomClearance.current)) {
                item { IndexPageHead(route.name, Modifier.indexArrive(0).semantics { heading() }, count = IndexPagesRules.genreCount(albums.size)) }
                if (artists.isEmpty() && albums.isEmpty()) item { IndexMuted("Nothing found for this genre.", Modifier.padding(gutter)) }
                if (artists.isNotEmpty()) {
                    val more = artists.size > ARTISTS_SHOWN && !allArtists
                    item { IndexSectionHead("Artists", meta = artists.size.toString(), link = if (more) "All" else null, onLink = { allArtists = true }, rule = false) }
                    val shown = if (allArtists) artists else artists.take(ARTISTS_SHOWN)
                    shown.forEachIndexed { i, a ->
                        item(key = "artist:${a.key.ifEmpty { a.name }}") {
                            IndexRow(
                                a.name, Modifier.indexArrive(1 + i).padding(horizontal = gutter), meta = if (a.owned) "In library" else "Not in library",
                                number = IndexPagesRules.number(i), onClick = { open.artist(a.name, a.key, a.id, null) },
                                lead = { ArtistPhoto(a.name, null, Modifier.size(48.dp), rect = true) },
                            )
                        }
                    }
                }
                if (albums.isNotEmpty()) {
                    val more = albums.size > ALBUMS_SHOWN && !allAlbums
                    item { IndexSectionHead("Albums", meta = albums.size.toString(), link = if (more) "All" else null, onLink = { allAlbums = true }, rule = artists.isNotEmpty()) }
                    val shown = if (allAlbums) albums else albums.take(ALBUMS_SHOWN)
                    shown.chunked(2).forEachIndexed { row, pair ->
                        item {
                            Row(Modifier.fillMaxWidth().padding(start = gutter, end = gutter, top = if (row == 0) 8.dp else 16.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                pair.forEach { a ->
                                    val said = listOfNotNull(a.name, a.artist.ifBlank { null }, a.year?.toString(), if (a.owned) "in your library" else null).joinToString(", ")
                                    Column(
                                        Modifier.weight(1f).clickable(role = Role.Button) { open.album(a.key, a.artist, a.name, a.id, a.year) }.semantics(mergeDescendants = true) { contentDescription = said },
                                        verticalArrangement = Arrangement.spacedBy(4.dp),
                                    ) {
                                        AlbumCover(a.artist, a.name, null, Modifier.fillMaxWidth().aspectRatio(1f).sharedCover(a.key), rect = true)
                                        Text(a.name, style = IndexType.rowTitle().copy(fontSize = 14.sp, fontWeight = FontWeight.SemiBold), color = p.text, maxLines = 2, overflow = TextOverflow.Ellipsis)
                                        IndexLabel(listOfNotNull(a.artist.ifBlank { null }, a.year?.toString()).joinToString(" · "))
                                        if (a.owned) IndexLabel("In library", color = p.ok)
                                    }
                                }
                                if (pair.size == 1) Box(Modifier.weight(1f))
                            }
                        }
                    }
                }
            }
        }
    }
}
