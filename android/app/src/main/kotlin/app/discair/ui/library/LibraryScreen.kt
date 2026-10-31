package app.discair.ui.library

import androidx.compose.foundation.clickable
import app.discair.ui.common.PageHeading
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.draw.clip
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.OutlinedIconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.Icons
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
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

    Column(Modifier.fillMaxSize()) {
        PageHeading("Library", Modifier.padding(start = 16.dp, top = 16.dp, end = 16.dp), large = true)
        Text(
            "Your Navidrome library by artist or album. Select one to see its page.",
            style = MaterialTheme.typography.bodyLarge,
            modifier = Modifier.padding(start = 16.dp, top = 12.dp, end = 16.dp),
        )
        OutlinedTextField(
            value = state.query,
            onValueChange = model::search,
            placeholder = { Text("Search your library") },
            trailingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
            singleLine = true,
            shape = RoundedCornerShape(28.dp),
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp)
                .semantics { contentDescription = "Search your library" },
        )
        SingleChoiceSegmentedButtonRow(Modifier.padding(horizontal = 16.dp)) {
            LibraryTab.entries.forEachIndexed { index, tab ->
                SegmentedButton(
                    selected = state.tab == tab,
                    onClick = { model.selectTab(tab) },
                    shape = SegmentedButtonDefaults.itemShape(index, LibraryTab.entries.size),
                    colors = SegmentedButtonDefaults.colors(
                        activeContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                        activeContentColor = MaterialTheme.colorScheme.primary,
                        inactiveContainerColor = MaterialTheme.colorScheme.background,
                    ),
                    icon = {},
                    modifier = Modifier.heightIn(min = Target),
                ) { Text(tab.name) }
            }
        }
        SortRow(state, model)
        Row(Modifier.padding(horizontal = 16.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Text("›", color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.titleMedium)
            Text(
                caption(state), style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(start = 8.dp),
            )
        }
        Box(Modifier.weight(1f)) {
            when {
                state.failure != null && currentCount(state) == 0 -> ErrorBlock(state.failure!!, model::retry)
                state.indexState == "building" && currentCount(state) == 0 -> Message("Your library is still being indexed. Try again in a moment.")
                state.indexState == "unavailable" -> Message("The library index is unavailable.")
                !state.loading && currentCount(state) == 0 -> Message(
                    if (state.query.isBlank()) "Your library is empty." else "Nothing in your library matches “${state.query}”.",
                )
                else -> Rows(state, model, open, list)
            }
        }
    }
}

/** "Showing 60 of 733 artists", as on the web. */
private fun caption(s: LibraryState): String {
    val noun = if (s.tab == LibraryTab.Artists) "artists" else "albums"
    val shown = currentCount(s)
    return if (s.total == null) "Loading…" else "Showing $shown of ${s.total} $noun"
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
    Row(
        Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text("Sort by", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Box(Modifier.weight(1f)) {
            Row(
                Modifier.fillMaxWidth().heightIn(min = Target).clip(RoundedCornerShape(24.dp))
                    .background(MaterialTheme.colorScheme.surface).clickable { open = true }
                    .padding(horizontal = 16.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(label, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
                Text("▾", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
                if (state.tab == LibraryTab.Artists) ArtistSort.entries.forEach { sort ->
                    DropdownMenuItem(text = { Text(sort.label) }, onClick = { open = false; model.sortArtists(sort) })
                } else AlbumSort.entries.forEach { sort ->
                    DropdownMenuItem(text = { Text(sort.label) }, onClick = { open = false; model.sortAlbums(sort) })
                }
            }
        }
        // The arrow points the way the list runs: up for ascending, down for descending.
        OutlinedIconButton(
            onClick = model::flipDirection,
            modifier = Modifier.size(Target).semantics { contentDescription = directionLabel(state) + ". Switch the order." },
        ) {
            Icon(
                Icons.AutoMirrored.Filled.ArrowBack, contentDescription = null,
                modifier = Modifier.rotate(if (state.effectiveDescending) -90f else 90f),
            )
        }
    }
}

@Composable
private fun Rows(state: LibraryState, model: LibraryViewModel, open: Opener, list: LazyListState) {
    LaunchedEffect(list, state.nextCursor) {
        snapshotFlow { list.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0 }
            .collect { last -> if (last >= list.layoutInfo.totalItemsCount - 6) model.loadMore() }
    }
    LazyColumn(Modifier.fillMaxSize(), state = list) {
        if (state.tab == LibraryTab.Artists) {
            items(state.artists, key = { it.id }) { artist ->
                Row(
                    Modifier.fillMaxWidth().heightIn(min = 68.dp)
                        .clickable { open.artist(artist.name, artist.key, artist.id, null) }
                        .padding(horizontal = 16.dp, vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Cover(artist.artworkUrl?.let { LocalRepository.current.absolute(it) }, Modifier.size(48.dp))
                    Column(Modifier.padding(start = 12.dp)) {
                        Text(artist.name, style = MaterialTheme.typography.bodyLarge, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        Text(
                            plural(artist.albumCount, "album"),
                            style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        } else {
            items(state.albums, key = { it.id }) { album ->
                Row(
                    Modifier.fillMaxWidth().heightIn(min = 64.dp)
                        .clickable { open.album(album.key, album.artist, album.name, album.id, album.year) }
                        .padding(horizontal = 16.dp, vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Cover(album.artworkUrl?.let { LocalRepository.current.absolute(it) }, Modifier.size(48.dp))
                    Column(Modifier.padding(start = 12.dp)) {
                        Text(album.name, style = MaterialTheme.typography.bodyLarge, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        Text(
                            listOfNotNull(album.artist, album.year?.toString(), plural(album.songCount, "song")).joinToString(" · "),
                            style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
                            maxLines = 1, overflow = TextOverflow.Ellipsis,
                        )
                    }
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
