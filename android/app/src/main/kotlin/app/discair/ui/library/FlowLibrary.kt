package app.discair.ui.library

import app.discair.ui.common.FlowIcons
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.DropdownMenuItem
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
import app.discair.ui.common.DropdownMenu
import app.discair.ui.common.ErrorBlock
import app.discair.ui.common.FlowChevron
import app.discair.ui.common.FlowDivider
import app.discair.ui.common.FlowPagesRules
import app.discair.ui.common.FlowSmallButton
import app.discair.ui.common.FlowTabs
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.OutlinedButton
import app.discair.ui.common.Target
import app.discair.ui.common.plural
import app.discair.ui.common.sharedCover
import app.discair.ui.player.LocalPlayActions
import app.discair.ui.player.RowMoreMenu
import app.discair.ui.theme.LocalPalette

/*
 * Flow's Library. Mockup: flow/library-search, frames 1 and 2 (flow.css `.li`, `.cap`).
 * LibraryScreen reaches this behind isFlow(); the data, paging, sort and taps are the Standard page's. The shell's bar carries the large title.
 */

/** Artists | Albums control, the count line with a Sort capsule, then artist rows or a two-column cover grid. */
@Composable
internal fun FlowLibrary(state: LibraryState, model: LibraryViewModel, open: Opener, list: LazyListState) {
    Column(Modifier.fillMaxSize()) {
        val tabs = listOf(LibraryTab.Artists, LibraryTab.Albums)
        FlowTabs(listOf("Artists", "Albums"), tabs.indexOf(state.tab), { model.selectTab(tabs[it]) }, Modifier.padding(start = 16.dp, top = 4.dp, end = 16.dp).fillMaxWidth())
        FlowSortRow(state, model)
        val count = if (state.tab == LibraryTab.Artists) state.artists.size else state.albums.size
        Box(Modifier.weight(1f)) {
            when {
                state.failure != null && count == 0 -> ErrorBlock(state.failure, model::retry)
                state.indexState == "building" && count == 0 -> Note("Your library is still being indexed. Try again in a moment.")
                state.indexState == "unavailable" -> Note("The library index is unavailable.")
                !state.loading && count == 0 -> Note(if (state.query.isBlank()) "Your library is empty." else "Nothing in your library matches “${state.query}”.")
                state.tab == LibraryTab.Albums -> FlowAlbumGrid(state, model, open)
                else -> FlowArtistRows(state, model, open, list)
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

/** "312 artists · by name" at the left, a Sort capsule at the right (accent label on `raised`). The menu is the Standard page's. */
@Composable
private fun FlowSortRow(state: LibraryState, model: LibraryViewModel) {
    val p = LocalPalette.current
    var open by remember { mutableStateOf(false) }
    val noun = if (state.tab == LibraryTab.Artists) "artists" else "albums"
    Row(Modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp, top = 8.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(
            app.discair.ui.downloads.LibraryText.countLine(noun, state.total, directionLabel(state)),
            color = p.textMuted, style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.weight(1f).semantics { liveRegion = LiveRegionMode.Polite },
        )
        Box {
            FlowSmallButton("Sort", FlowIcons.Sort, false, "Sort $noun, now ${if (state.tab == LibraryTab.Artists) state.artistSort.label else state.albumSort.label}") { open = true }
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

/** Artists as rows: a round photo 48, the name in Inter 600 15, the album count in words, a grey chevron and a hairline (`.li`). */
@Composable
private fun FlowArtistRows(state: LibraryState, model: LibraryViewModel, open: Opener, list: LazyListState) {
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
                    Cover(artist.artworkUrl?.let { repo.absolute(it) }, Modifier.size(FlowPagesRules.ROW_COVER.dp).clip(CircleShape), circle = true)
                    Column(Modifier.weight(1f)) {
                        Text(artist.name, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 15.sp, lineHeight = 20.sp))
                        Text(plural(artist.albumCount, "album"), color = p.textMuted, style = MaterialTheme.typography.bodySmall.copy(fontSize = 13.sp, lineHeight = 18.sp))
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
                    FlowChevron(Modifier.padding(end = 12.dp))
                }
                FlowDivider(Modifier.padding(horizontal = 16.dp))
            }
        }
        if (state.loading) item { Text("Loading…", Modifier.padding(16.dp), color = p.textMuted) }
        if (state.failure != null) item {
            Column(Modifier.padding(16.dp)) {
                Text(state.failure.message, color = p.chartRedText)
                OutlinedButton(onClick = model::loadMore, Modifier.heightIn(min = Target)) { Text("Try again") }
            }
        }
    }
}

/** Albums as two covers to a row, 14dp apart: a cover of radius 8 with no outline, the title in Inter 600 14, artist and year muted (`.g2 .cap`). */
@Composable
private fun FlowAlbumGrid(state: LibraryState, model: LibraryViewModel, open: Opener) {
    val p = LocalPalette.current
    val repo = LocalRepository.current
    val grid = rememberLazyGridState()
    LaunchedEffect(grid, state.nextCursor) {
        snapshotFlow { grid.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0 }
            .collect { last -> if (last >= grid.layoutInfo.totalItemsCount - 6) model.loadMore() }
    }
    val gap = FlowPagesRules.GRID_GAP.dp
    LazyVerticalGrid(
        columns = GridCells.Fixed(2), state = grid, modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 12.dp, bottom = LocalBottomClearance.current),
        horizontalArrangement = Arrangement.spacedBy(gap), verticalArrangement = Arrangement.spacedBy(gap),
    ) {
        items(state.albums.size, key = { state.albums[it].id }) { i ->
            val album = state.albums[i]
            Column(
                Modifier.animateItem().clip(RoundedCornerShape(8.dp)).clickable(role = Role.Button) { open.album(album.key, album.artist, album.name, album.id, album.year) },
            ) {
                Cover(album.artworkUrl?.let { repo.absolute(it) }, Modifier.fillMaxWidth().aspectRatio(1f).clip(RoundedCornerShape(8.dp)).sharedCover(album.key))
                Text(album.name, Modifier.padding(top = 8.dp), color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.SemiBold, fontSize = 14.sp))
                Text(
                    listOfNotNull(album.artist, album.year?.toString()).joinToString(" · "),
                    color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall.copy(fontSize = 13.sp, lineHeight = 18.sp),
                )
            }
        }
    }
}
