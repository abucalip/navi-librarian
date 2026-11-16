package app.discair.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import app.discair.model.GenrePage
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.ArtistPhoto
import app.discair.ui.common.GalleryCaption
import app.discair.ui.common.GalleryMuted
import app.discair.ui.common.GalleryPageBar
import app.discair.ui.common.GalleryPageHead
import app.discair.ui.common.GalleryPagesRules
import app.discair.ui.common.GalleryPrint
import app.discair.ui.common.GalleryRow
import app.discair.ui.common.GalleryRules
import app.discair.ui.common.GalleryState
import app.discair.ui.common.GalleryTabs
import app.discair.ui.common.LoadView
import app.discair.ui.common.Loaded
import app.discair.ui.theme.LocalPalette

/*
 * Gallery's Genre page (Layout.Gallery). Spec: docs/GALLERY_THEME.md section 10; mockup: docs/design/gallery/pages/album-artist-genre.html, frame 4.
 * The catalogue line with the counts, the genre's name as the large title, tabs Albums / Artists, then albums as two columns of captioned prints or artists as rows
 * with photo prints. Which items are in the library is said in words. The data and the taps are the page every theme has; only the arrangement is new.
 */
@Composable
internal fun GalleryGenre(route: GenreRoute, loaded: Loaded<GenrePage>, open: Opener) {
    val p = LocalPalette.current
    var tab by rememberSaveable { mutableIntStateOf(0) }
    val gutter = GalleryRules.GUTTER.dp
    Column(Modifier.fillMaxSize()) {
        GalleryPageBar("Genre", open.back)
        LoadView(loaded) { page ->
            val artists = page.sections.artists.items
            val albums = page.sections.albums.items
            LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 32.dp + LocalBottomClearance.current)) {
                item {
                    GalleryPageHead(route.name, Modifier.semantics { heading() }, eyebrow = GalleryPagesRules.genreEyebrow(albums.size, artists.size))
                }
                if (artists.isEmpty() && albums.isEmpty()) item { GalleryMuted("Nothing found for this genre.", Modifier.padding(gutter)) }
                else {
                    item { GalleryTabs(listOf("Albums", "Artists"), tab, { tab = it }, Modifier.padding(top = 16.dp)) }
                    if (tab == 0) {
                        if (albums.isEmpty()) item { GalleryMuted("No albums for this genre.", Modifier.padding(gutter)) }
                        else {
                            item { Box(Modifier.padding(top = 20.dp)) }
                            items(albums.chunked(2)) { pair ->
                                Row(Modifier.fillMaxWidth().padding(horizontal = gutter).padding(bottom = 20.dp), horizontalArrangement = Arrangement.spacedBy(18.dp)) {
                                    pair.forEach { a ->
                                        GalleryCaption(
                                            a.name, GalleryPagesRules.maker(a.artist, a.year), Modifier.weight(1f), state = if (a.owned) "In library" else null,
                                            onClick = { open.album(a.key, a.artist, a.name, a.id, a.year) },
                                        ) { AlbumCover(a.artist, a.name, null, Modifier.fillMaxWidth().aspectRatio(1f), rect = true) }
                                    }
                                    if (pair.size == 1) Box(Modifier.weight(1f))
                                }
                            }
                        }
                    } else {
                        if (artists.isEmpty()) item { GalleryMuted("No artists for this genre.", Modifier.padding(gutter)) }
                        items(artists, key = { it.key.ifEmpty { it.name } }) { a ->
                            GalleryRow(
                                a.name, Modifier.padding(horizontal = gutter), minHeight = 72.dp, onClick = { open.artist(a.name, a.key, a.id, null) },
                                lead = { GalleryPrint(GalleryPagesRules.PHOTO_PRINT_DP.dp) { ArtistPhoto(a.name, null, Modifier.fillMaxWidth().aspectRatio(1f), rect = true) } },
                                trail = { GalleryState(if (a.owned) "In library" else "Not in library", color = if (a.owned) p.ok else p.textMuted) },
                            )
                        }
                    }
                }
            }
        }
    }
}
