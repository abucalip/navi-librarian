package app.discair.ui.library

import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.data.AlbumSort
import app.discair.data.ArtistSort
import app.discair.ui.LocalBottomClearance
import app.discair.ui.Opener
import app.discair.ui.common.Cover
import app.discair.ui.common.CoverStackDivider
import app.discair.ui.common.CoverStackRules
import app.discair.ui.common.CoverStackTabs
import app.discair.ui.common.CoverStackTitle
import app.discair.ui.common.DropdownMenu
import app.discair.ui.common.ErrorBlock
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.OutlinedButton
import app.discair.ui.common.Target
import app.discair.ui.common.plural
import app.discair.ui.common.sharedCover
import app.discair.ui.discover.SmallButton
import app.discair.ui.player.LocalPlayActions
import app.discair.ui.player.PlayerIcons
import app.discair.ui.player.RowMoreMenu
import app.discair.ui.theme.Ink
import app.discair.ui.theme.LocalPalette

/*
 * Soft Brut's (Layout.CoverStack) Library. Mockup: soft-brut/library-search, frames 1 and 2.
 * LibraryScreen reaches this behind isCoverStack(); no other theme changes. The data, paging, sort and taps are the Standard page's.
 */

/** Title, Artists | Albums group, the count line with Sort, then artist rows or a two-column cover grid. */
@Composable
internal fun CoverStackLibrary(state: LibraryState, model: LibraryViewModel, open: Opener, list: LazyListState) {
    val p = LocalPalette.current
    Column(Modifier.fillMaxSize()) {
        CoverStackTitle("Library", Modifier.padding(start = 16.dp, top = 16.dp, end = 16.dp), maxLines = 1)
        val tabs = listOf(LibraryTab.Artists, LibraryTab.Albums)
        CoverStackTabs(
            listOf("Artists", "Albums"), tabs.indexOf(state.tab), { model.selectTab(tabs[it]) },
            Modifier.padding(start = 16.dp, top = 12.dp, end = 19.dp, bottom = 4.dp).fillMaxWidth(),
        )
        CoverStackSortRow(state, model)
        val count = if (state.tab == LibraryTab.Artists) state.artists.size else state.albums.size
        Box(Modifier.weight(1f)) {
            when {
                state.failure != null && count == 0 -> ErrorBlock(state.failure, model::retry)
                state.indexState == "building" && count == 0 -> Note("Your library is still being indexed. Try again in a moment.")
                state.indexState == "unavailable" -> Note("The library index is unavailable.")
                !state.loading && count == 0 -> Note(if (state.query.isBlank()) "Your library is empty." else "Nothing in your library matches “${state.query}”.")
                state.tab == LibraryTab.Albums -> CoverStackAlbumGrid(state, model, open)
                else -> CoverStackArtistRows(state, model, open, list)
            }
        }
    }
}

@Composable
private fun Note(text: String) {
    Box(Modifier.fillMaxSize().padding(24.dp), contentAlignment = Alignment.Center) {
        Text(text, style = MaterialTheme.typography.bodyLarge, color = LocalPalette.current.textMuted)
    }
}

/** "312 artists · by name" at the left, an outlined Sort button at the right (mockup `.pad.row`). The menu is the Standard page's. */
@Composable
private fun CoverStackSortRow(state: LibraryState, model: LibraryViewModel) {
    val p = LocalPalette.current
    var open by remember { mutableStateOf(false) }
    val noun = if (state.tab == LibraryTab.Artists) "artists" else "albums"
    Row(Modifier.fillMaxWidth().padding(start = 16.dp, end = 12.dp, top = 4.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(
            app.discair.ui.downloads.LibraryText.countLine(noun, state.total, directionLabel(state)),
            color = p.textMuted, style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.weight(1f).semantics { liveRegion = LiveRegionMode.Polite },
        )
        Box {
            SmallButton("Sort", null, false, "Sort ${noun}, now ${if (state.tab == LibraryTab.Artists) state.artistSort.label else state.albumSort.label}", Modifier.width(84.dp)) { open = true }
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

/** Artists as rows: a round outlined photo, name, album count in words, a chevron, a dashed rule (mockup `.li`). */
@Composable
private fun CoverStackArtistRows(state: LibraryState, model: LibraryViewModel, open: Opener, list: LazyListState) {
    val p = LocalPalette.current
    val repo = LocalRepository.current
    val play = LocalPlayActions.current
    LaunchedEffect(list, state.nextCursor) {
        snapshotFlow { list.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0 }
            .collect { last -> if (last >= list.layoutInfo.totalItemsCount - 6) model.loadMore() }
    }
    LazyColumn(Modifier.fillMaxSize(), state = list, contentPadding = PaddingValues(top = 8.dp, bottom = LocalBottomClearance.current)) {
        items(state.artists, key = { it.id }) { artist ->
            Column(Modifier.animateItem()) {
                Row(
                    Modifier.fillMaxWidth().heightIn(min = 64.dp).clickable(role = Role.Button) { open.artist(artist.name, artist.key, artist.id, null) }
                        .padding(start = 16.dp, end = 4.dp, top = 8.dp, bottom = 8.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
                ) {
                    Cover(
                        artist.artworkUrl?.let { repo.absolute(it) },
                        Modifier.size(48.dp).clip(CircleShape).border(CoverStackRules.outline(p).dp, p.edgeStrong, CircleShape), circle = true,
                    )
                    Column(Modifier.weight(1f)) {
                        Text(artist.name, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 14.sp))
                        Text(plural(artist.albumCount, "album"), color = p.textMuted, style = MaterialTheme.typography.bodySmall)
                    }
                    // Play and the ways to queue stay one tap away, in the menu (the mockup shows only the chevron).
                    RowMoreMenu(
                        artist.name,
                        listOf(
                            "Play" to { play.playArtist(artist.id, shuffle = false) },
                            "Shuffle" to { play.playArtist(artist.id, shuffle = true) },
                            "Play next" to { play.queueArtist(artist.id, next = true) },
                            "Add to queue" to { play.queueArtist(artist.id, next = false) },
                        ),
                    )
                    Icon(PlayerIcons.Right, contentDescription = null, tint = p.text, modifier = Modifier.padding(end = 12.dp))
                }
                CoverStackDivider(Modifier.padding(horizontal = 16.dp))
            }
        }
        footer(state, model)
    }
}

private fun androidx.compose.foundation.lazy.LazyListScope.footer(state: LibraryState, model: LibraryViewModel) {
    if (state.loading) item { Text("Loading…", Modifier.padding(16.dp), color = Ink.Ink.copy(alpha = 0.7f)) }
    if (state.failure != null) item {
        Column(Modifier.padding(16.dp)) {
            Text(state.failure.message, color = Ink.ChartRedText)
            OutlinedButton(onClick = model::loadMore, Modifier.heightIn(min = Target)) { Text("Try again") }
        }
    }
}

/** Albums as two covers to a row: outlined cover, bold title, artist and year (mockup `.g2 .cap`). */
@Composable
private fun CoverStackAlbumGrid(state: LibraryState, model: LibraryViewModel, open: Opener) {
    val p = LocalPalette.current
    val repo = LocalRepository.current
    val grid = rememberLazyGridState()
    LaunchedEffect(grid, state.nextCursor) {
        snapshotFlow { grid.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0 }
            .collect { last -> if (last >= grid.layoutInfo.totalItemsCount - 6) model.loadMore() }
    }
    val shape = RoundedCornerShape(CoverStackRules.radius(p).dp)
    LazyVerticalGrid(
        columns = GridCells.Fixed(2), state = grid, modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 12.dp, bottom = LocalBottomClearance.current),
        horizontalArrangement = Arrangement.spacedBy(14.dp), verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        items(state.albums.size, key = { state.albums[it].id }) { i ->
            val album = state.albums[i]
            Column(
                Modifier.animateItem().clip(RoundedCornerShape(8.dp)).clickable(role = Role.Button) { open.album(album.key, album.artist, album.name, album.id, album.year) },
            ) {
                Cover(
                    album.artworkUrl?.let { repo.absolute(it) },
                    Modifier.fillMaxWidth().aspectRatio1().clip(shape).border(CoverStackRules.outline(p).dp, p.edgeStrong, shape).sharedCover(album.key),
                )
                Text(album.name, Modifier.padding(top = 8.dp), color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold, fontSize = 14.sp))
                Text(
                    listOfNotNull(album.artist, album.year?.toString()).joinToString(" · "),
                    color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall,
                )
            }
        }
    }
}

private fun Modifier.aspectRatio1(): Modifier = this.then(Modifier.aspectRatio(1f))
