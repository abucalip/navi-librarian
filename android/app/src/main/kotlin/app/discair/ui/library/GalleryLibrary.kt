package app.discair.ui.library

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import app.discair.data.AlbumSort
import app.discair.data.ArtistSort
import app.discair.ui.LocalBottomClearance
import app.discair.ui.Opener
import app.discair.ui.common.Cover
import app.discair.ui.common.ErrorBlock
import app.discair.ui.common.GalleryButton
import app.discair.ui.common.GalleryButtonKind
import app.discair.ui.common.GalleryCaption
import app.discair.ui.common.GalleryEyebrow
import app.discair.ui.common.GalleryIcons
import app.discair.ui.common.GalleryListsRules
import app.discair.ui.common.GalleryMenuButton
import app.discair.ui.common.GalleryMuted
import app.discair.ui.common.GalleryPageHead
import app.discair.ui.common.GalleryPagesRules
import app.discair.ui.common.GalleryPrint
import app.discair.ui.common.GalleryRow
import app.discair.ui.common.GalleryRules
import app.discair.ui.common.GalleryTabs
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.plural
import app.discair.ui.common.sharedCover
import app.discair.ui.player.LocalPlayActions
import app.discair.ui.theme.LocalPalette

/*
 * Gallery's Library (Layout.Gallery). Spec: docs/GALLERY_THEME.md section 10; mockup: docs/design/gallery/pages/library-search.html, frames 1 and 2.
 * The count as the catalogue line, "Library" as the large title, tabs Artists / Albums, the order line with Sort, then artists as rows with photo prints or
 * albums as two columns of captioned prints. The data, the paging, the sort and every tap are the page every theme has (LibraryScreen).
 */

private val Gutter = GalleryRules.GUTTER.dp

@Composable
internal fun GalleryLibrary(state: LibraryState, model: LibraryViewModel, open: Opener, list: LazyListState) {
    Column(Modifier.fillMaxSize().statusBarsPadding()) {
        val tabs = listOf(LibraryTab.Artists, LibraryTab.Albums)
        val noun = if (state.tab == LibraryTab.Artists) "artists" else "albums"
        GalleryPageHead("Library", Modifier.padding(top = 10.dp).semantics { heading() }, eyebrow = GalleryListsRules.countEyebrow(noun, state.total))
        GalleryTabs(listOf("Artists", "Albums"), tabs.indexOf(state.tab), { model.selectTab(tabs[it]) }, Modifier.padding(top = 12.dp))
        SortLine(state, model, noun)
        val count = if (state.tab == LibraryTab.Artists) state.artists.size else state.albums.size
        Box(Modifier.weight(1f)) {
            when {
                state.failure != null && count == 0 -> ErrorBlock(state.failure, model::retry)
                state.indexState == "building" && count == 0 -> Note("Your library is still being indexed. Try again in a moment.")
                state.indexState == "unavailable" -> Note("The library index is unavailable.")
                !state.loading && count == 0 -> Note(if (state.query.isBlank()) "Your library is empty." else "Nothing in your library matches “${state.query}”.")
                state.tab == LibraryTab.Albums -> AlbumGrid(state, model, open)
                else -> ArtistRows(state, model, open, list)
            }
        }
    }
}

@Composable
private fun Note(text: String) {
    Box(Modifier.fillMaxSize().padding(Gutter)) { GalleryMuted(text) }
}

/** "By name" at the left (DM Mono capitals, muted), a Sort text button with its icon at the right. The menu is the Standard page's. */
@Composable
private fun SortLine(state: LibraryState, model: LibraryViewModel, noun: String) {
    var open by remember { mutableStateOf(false) }
    val label = if (state.tab == LibraryTab.Artists) state.artistSort.label else state.albumSort.label
    Row(Modifier.fillMaxWidth().padding(start = Gutter, end = 10.dp, top = 6.dp), verticalAlignment = Alignment.CenterVertically) {
        GalleryEyebrow(GalleryListsRules.sortLine(label, directionLabel(state)), Modifier.weight(1f).semantics { liveRegion = LiveRegionMode.Polite })
        Box {
            GalleryButton("Sort", { open = true }, kind = GalleryButtonKind.Text, icon = GalleryIcons.Sort, small = true, modifier = Modifier.semantics { contentDescription = "Sort $noun, now $label" })
            DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
                if (state.tab == LibraryTab.Artists) ArtistSort.entries.forEach { sort ->
                    DropdownMenuItem(text = { Text(sort.label) }, onClick = { open = false; model.sortArtists(sort) })
                } else AlbumSort.entries.forEach { sort ->
                    DropdownMenuItem(text = { Text(sort.label) }, onClick = { open = false; model.sortAlbums(sort) })
                }
                DropdownMenuItem(text = { Text("Reverse: " + directionLabel(state)) }, onClick = { open = false; model.flipDirection() })
            }
        }
    }
}

/** Artists as rows: a 52dp photo print, the name (Manrope 600 15, upright: a person's name), the album count in words, the play menu and a chevron. */
@Composable
private fun ArtistRows(state: LibraryState, model: LibraryViewModel, open: Opener, list: LazyListState) {
    val p = LocalPalette.current
    val repo = LocalRepository.current
    val play = LocalPlayActions.current
    LaunchedEffect(list, state.nextCursor) {
        snapshotFlow { list.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0 }
            .collect { last -> if (last >= list.layoutInfo.totalItemsCount - 6) model.loadMore() }
    }
    LazyColumn(Modifier.fillMaxSize(), state = list, contentPadding = PaddingValues(top = 4.dp, bottom = LocalBottomClearance.current)) {
        items(state.artists, key = { it.id }) { artist ->
            GalleryRow(
                artist.name, Modifier.animateItem().padding(horizontal = Gutter), sub = plural(artist.albumCount, "album"),
                onClick = { open.artist(artist.name, artist.key, artist.id, null) },
                lead = {
                    GalleryPrint(GalleryPagesRules.PHOTO_PRINT_DP.dp, Modifier.width(GalleryPagesRules.PHOTO_PRINT_DP.dp)) {
                        Cover(artist.artworkUrl?.let { repo.absolute(it) }, Modifier.fillMaxWidth().aspectRatio(1f), rect = true)
                    }
                },
                trail = {
                    // Play and the ways to queue stay one tap away (the mockup shows only the chevron).
                    GalleryMenuButton(
                        "More ways to play ${artist.name}",
                        listOf(
                            "Play" to { play.playArtist(artist.id, shuffle = false) },
                            "Shuffle" to { play.playArtist(artist.id, shuffle = true) },
                            "Play next" to { play.queueArtist(artist.id, next = true) },
                            "Add to queue" to { play.queueArtist(artist.id, next = false) },
                        ),
                    )
                    Icon(GalleryIcons.Chevron, null, tint = p.control, modifier = Modifier.size(GalleryRules.ICON_INLINE.dp))
                },
            )
        }
        if (state.loading) item { GalleryMuted("Loading…", Modifier.padding(Gutter)) }
        if (state.failure != null) item {
            Column(Modifier.padding(Gutter), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(state.failure.message, color = p.chartRedText)
                GalleryButton("Try again", model::loadMore, kind = GalleryButtonKind.Outlined, small = true)
            }
        }
    }
}

/** Albums as two captioned prints to a row, 18dp apart and 20dp between rows (gallery.css `.g2`): the work in italic, "Artist, year" under it. */
@Composable
private fun AlbumGrid(state: LibraryState, model: LibraryViewModel, open: Opener) {
    val repo = LocalRepository.current
    val grid = rememberLazyGridState()
    LaunchedEffect(grid, state.nextCursor) {
        snapshotFlow { grid.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0 }
            .collect { last -> if (last >= grid.layoutInfo.totalItemsCount - 6) model.loadMore() }
    }
    LazyVerticalGrid(
        columns = GridCells.Fixed(2), state = grid, modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(start = Gutter, end = Gutter, top = 14.dp, bottom = 24.dp + LocalBottomClearance.current),
        horizontalArrangement = Arrangement.spacedBy(18.dp), verticalArrangement = Arrangement.spacedBy(20.dp),
    ) {
        items(state.albums.size, key = { state.albums[it].id }) { i ->
            val album = state.albums[i]
            GalleryCaption(
                album.name, GalleryPagesRules.maker(album.artist, album.year), Modifier.animateItem(),
                onClick = { open.album(album.key, album.artist, album.name, album.id, album.year) },
            ) { Cover(album.artworkUrl?.let { repo.absolute(it) }, Modifier.fillMaxWidth().aspectRatio(1f).sharedCover(album.key), rect = true) }
        }
    }
}
