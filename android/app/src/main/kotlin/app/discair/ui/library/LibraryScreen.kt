package app.discair.ui.library

import androidx.compose.foundation.clickable
import androidx.compose.ui.semantics.Role
import app.discair.ui.common.PageHeading
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.draw.clip
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SegmentedButton
import app.discair.ui.common.OutlinedIconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.Icons
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.grid.items as gridItems
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.text.KeyboardOptions
import app.discair.ui.common.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import app.discair.ui.common.FilterChip
import androidx.compose.material3.MaterialTheme
import app.discair.ui.common.OutlinedButton
import app.discair.ui.common.OutlinedTextField
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
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import app.discair.data.AlbumSort
import app.discair.data.ArtistSort
import app.discair.ui.Opener
import app.discair.ui.common.ActionGroup
import app.discair.ui.common.ActionGroupButton
import app.discair.ui.common.GroupDivider
import app.discair.ui.common.GroupIcon
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import app.discair.ui.common.Cover
import app.discair.ui.common.ErrorBlock
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.Target
import app.discair.ui.common.plural
import app.discair.ui.theme.Ink
import androidx.compose.runtime.collectAsState

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LibraryScreen(open: Opener) {
    val repo = LocalRepository.current
    val model: LibraryViewModel = viewModel(factory = LibraryViewModelFactory(repo))
    val state by model.state.collectAsState()
    val list = rememberLazyListState()
    // Albums are two to a row, as drawn; artists stay a list (docs/redesign.md 8.2).
    val grid = state.tab == LibraryTab.Albums
    val cell = 160f

    Column(Modifier.fillMaxSize()) {
        PageHeading("Library", Modifier.padding(start = 16.dp, top = 16.dp, end = 16.dp), large = true)
        val tabs = listOf(LibraryTab.Artists, LibraryTab.Albums)
        app.discair.ui.common.SegmentedTabs(
            listOf("Artists", "Albums"), tabs.indexOf(state.tab), { model.selectTab(tabs[it]) },
            Modifier.padding(start = 16.dp, top = 16.dp, end = 16.dp),
        )
        SortRow(state, model)
        Box(Modifier.weight(1f)) {
            when {
                state.failure != null && currentCount(state) == 0 -> ErrorBlock(state.failure!!, model::retry)
                state.indexState == "building" && currentCount(state) == 0 -> Message("Your library is still being indexed. Try again in a moment.")
                state.indexState == "unavailable" -> Message("The library index is unavailable.")
                !state.loading && currentCount(state) == 0 -> Message(
                    if (state.query.isBlank()) "Your library is empty." else "Nothing in your library matches “${state.query}”.",
                )
                grid -> GridRows(state, model, open, cell.dp)
                else -> Rows(state, model, open, list)
            }
        }
    }
}

/** Names the order in words that fit the field being sorted. */
private fun directionLabel(s: LibraryState): String {
    val desc = s.effectiveDescending
    val kind = if (s.tab == LibraryTab.Artists) when (s.artistSort) {
        ArtistSort.Name -> "text"; ArtistSort.Albums -> "number"; ArtistSort.Added -> "date"
    } else when (s.albumSort) {
        AlbumSort.Name, AlbumSort.Artist -> "text"; AlbumSort.Year, AlbumSort.Added -> "date"; AlbumSort.Tracks -> "number"
    }
    return when (kind) {
        "text" -> if (desc) "Z to A" else "A to Z"
        "date" -> if (desc) "Newest first" else "Oldest first"
        else -> if (desc) "Most first" else "Fewest first"
    }
}

private fun currentCount(s: LibraryState) = if (s.tab == LibraryTab.Artists) s.artists.size else s.albums.size

@Composable
private fun Message(text: String) {
    Box(Modifier.fillMaxSize().padding(24.dp), contentAlignment = Alignment.Center) {
        Text(text, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun SortRow(state: LibraryState, model: LibraryViewModel) {
    var open by remember { mutableStateOf(false) }
    val label = if (state.tab == LibraryTab.Artists) state.artistSort.label else state.albumSort.label
    val noun = if (state.tab == LibraryTab.Artists) "artists" else "albums"
    Row(
        Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            app.discair.ui.downloads.LibraryText.countLine(noun, state.total, directionLabel(state)),
            style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.weight(1f).semantics { liveRegion = LiveRegionMode.Polite },
        )
        Box {
            Row(
                Modifier.heightIn(min = Target).clip(RoundedCornerShape(24.dp)).clickable(role = Role.Button) { open = true }
                    .padding(horizontal = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                Text("Sort", style = MaterialTheme.typography.titleMedium)
                Text("· $label", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
                if (state.tab == LibraryTab.Artists) ArtistSort.entries.forEach { sort ->
                    DropdownMenuItem(text = { Text(sort.label) }, onClick = { open = false; model.sortArtists(sort) })
                } else AlbumSort.entries.forEach { sort ->
                    DropdownMenuItem(text = { Text(sort.label) }, onClick = { open = false; model.sortAlbums(sort) })
                }
                DropdownMenuItem(
                    text = { Text("Reverse: " + directionLabel(state)) },
                    onClick = { open = false; model.flipDirection() },
                )
            }
        }
    }
}

@Composable
private fun Rows(state: LibraryState, model: LibraryViewModel, open: Opener, list: LazyListState) {
    LaunchedEffect(list, state.nextCursor) {
        snapshotFlow { list.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0 }
            .collect { last -> if (last >= list.layoutInfo.totalItemsCount - 6) model.loadMore() }
    }
    LazyColumn(Modifier.fillMaxSize(), state = list, contentPadding = androidx.compose.foundation.layout.PaddingValues(bottom = app.discair.ui.LocalBottomClearance.current)) {
        if (state.tab == LibraryTab.Artists) {
            items(state.artists, key = { it.id }) { artist ->
                Row(
                    Modifier.animateItem().fillMaxWidth().heightIn(min = 68.dp)
                        .clickable(role = Role.Button) { open.artist(artist.name, artist.key, artist.id, null) }
                        .padding(horizontal = 16.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Cover(artist.artworkUrl?.let { LocalRepository.current.absolute(it) }, Modifier.size(48.dp))
                    Column(Modifier.weight(1f).padding(start = 16.dp)) {
                        Text(artist.name, style = MaterialTheme.typography.bodyLarge, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        Text(
                            plural(artist.albumCount, "album"),
                            style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    val play = app.discair.ui.player.LocalPlayActions.current
                    app.discair.ui.player.RowPlayButton(artist.name, { play.playArtist(artist.id, shuffle = false) })
                    app.discair.ui.player.RowMoreMenu(
                        artist.name,
                        listOf(
                            "Shuffle" to { play.playArtist(artist.id, shuffle = true) },
                            "Play next" to { play.queueArtist(artist.id, next = true) },
                            "Add to queue" to { play.queueArtist(artist.id, next = false) },
                        ),
                    )
                }
            }
        } else {
            items(state.albums, key = { it.id }) { album ->
                Row(
                    Modifier.fillMaxWidth().heightIn(min = 64.dp)
                        .clickable(role = Role.Button) { open.album(album.key, album.artist, album.name, album.id, album.year) }
                        .padding(horizontal = 16.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Cover(album.artworkUrl?.let { LocalRepository.current.absolute(it) }, Modifier.size(48.dp))
                    Column(Modifier.weight(1f).padding(start = 16.dp)) {
                        Text(album.name, style = MaterialTheme.typography.bodyLarge, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        Text(
                            listOfNotNull(album.artist, album.year?.toString(), plural(album.songCount, "song")).joinToString(" · "),
                            style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
                            maxLines = 1, overflow = TextOverflow.Ellipsis,
                        )
                    }
                    val play = app.discair.ui.player.LocalPlayActions.current
                    app.discair.ui.player.RowPlayButton(album.name, { play.playAlbum(album.id) })
                    app.discair.ui.player.RowMoreMenu(
                        album.name,
                        listOf(
                            "Shuffle" to { play.playAlbum(album.id, shuffle = true) },
                            "Play next" to { play.queueAlbum(album.id, next = true) },
                            "Add to queue" to { play.queueAlbum(album.id, next = false) },
                        ),
                    )
                }
            }
        }
        if (state.loading) item {
            Text("Loading…", Modifier.padding(16.dp), color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        if (state.failure != null) item {
            Column(Modifier.padding(16.dp)) {
                Text(state.failure.message, color = Ink.ChartRedText)
                OutlinedButton(onClick = model::loadMore, Modifier.heightIn(min = Target)) { Text("Try again") }
            }
        }
    }
}

/** The same pages as [Rows], as a grid of covers. The cell width follows the slider; names sit under the cover. */
@Composable
private fun GridRows(state: LibraryState, model: LibraryViewModel, open: Opener, cell: androidx.compose.ui.unit.Dp) {
    val grid = androidx.compose.foundation.lazy.grid.rememberLazyGridState()
    LaunchedEffect(grid, state.nextCursor) {
        snapshotFlow { grid.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0 }
            .collect { last -> if (last >= grid.layoutInfo.totalItemsCount - 6) model.loadMore() }
    }
    val repo = LocalRepository.current
    androidx.compose.foundation.lazy.grid.LazyVerticalGrid(
        columns = androidx.compose.foundation.lazy.grid.GridCells.Adaptive(cell),
        state = grid,
        modifier = Modifier.fillMaxSize(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(start = 16.dp, end = 16.dp, top = 4.dp, bottom = app.discair.ui.LocalBottomClearance.current),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        if (state.tab == LibraryTab.Artists) {
            gridItems(state.artists, key = { it.id }) { artist ->
                Column(Modifier.animateItem().clickable(role = Role.Button) { open.artist(artist.name, artist.key, artist.id, null) }) {
                    Cover(artist.artworkUrl?.let { repo.absolute(it) }, Modifier.fillMaxWidth().aspectRatio(1f), circle = true)
                    Text(artist.name, style = MaterialTheme.typography.bodyMedium, maxLines = 2, overflow = TextOverflow.Ellipsis, modifier = Modifier.padding(top = 8.dp))
                    Text(plural(artist.albumCount, "album"), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1)
                }
            }
        } else {
            gridItems(state.albums, key = { it.id }) { album ->
                Column(Modifier.animateItem().clickable(role = Role.Button) { open.album(album.key, album.artist, album.name, album.id, album.year) }) {
                    Cover(album.artworkUrl?.let { repo.absolute(it) }, Modifier.fillMaxWidth().aspectRatio(1f))
                    Text(album.name, style = MaterialTheme.typography.bodyMedium, maxLines = 2, overflow = TextOverflow.Ellipsis, modifier = Modifier.padding(top = 8.dp))
                    Text(
                        listOfNotNull(album.artist, album.year?.toString()).joinToString(" · "),
                        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1, overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }
    }
}
