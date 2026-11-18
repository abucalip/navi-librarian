package app.discair.ui.library

import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectVerticalDragGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.data.AlbumSort
import app.discair.data.ArtistSort
import app.discair.model.GenreTile
import app.discair.ui.LocalBottomClearance
import app.discair.ui.Opener
import app.discair.ui.common.Cover
import app.discair.ui.common.ErrorBlock
import app.discair.ui.common.IndexIconButton
import app.discair.ui.common.IndexIcons
import app.discair.ui.common.IndexLabel
import app.discair.ui.common.IndexListsRules
import app.discair.ui.common.IndexMuted
import app.discair.ui.common.IndexPageHead
import app.discair.ui.common.IndexRow
import app.discair.ui.common.IndexRules
import app.discair.ui.common.IndexTabs
import app.discair.ui.common.IndexType
import app.discair.ui.common.Load
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.indexArrive
import app.discair.ui.common.rememberLoad
import app.discair.ui.common.sharedCover
import app.discair.ui.player.LocalPlayActions
import app.discair.ui.theme.LocalPalette
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/*
 * Index's Library (Layout.Index). Spec: docs/plans/INDEX_THEME.md step I4; mockup: docs/design/index/pages/library-search.html, frames 1 and 2.
 * "Library" with the tab's count as a superscript, tabs Artists / Albums / Genres each with its count once known, the sort line, then artists as rows with the
 * letter in the number column and a letter rail (A to Z by name only), albums as a two-column grid, genres as numbered rows. The paging, the sort and every tap
 * are the page every theme has (LibraryScreen); Genres is Index's own tab over the same genre list as Home.
 */

private val Gutter = IndexRules.GUTTER.dp

/** Index's three tabs: the view model's two, and Genres, which only Index shows. */
private enum class IndexLibraryTab { Artists, Albums, Genres }

@Composable
internal fun IndexLibrary(state: LibraryState, model: LibraryViewModel, open: Opener, list: LazyListState) {
    val repo = LocalRepository.current
    var genres by rememberSaveable { mutableStateOf(false) }
    val tab = if (genres) IndexLibraryTab.Genres else if (state.tab == LibraryTab.Artists) IndexLibraryTab.Artists else IndexLibraryTab.Albums
    val genreList = rememberLoad("genres") { repo.genres().items }

    // Each tab's total, once a first page has said it: the tab on screen from its own load, the other from one first page read here. Never a placeholder.
    val totals = remember { mutableStateMapOf<LibraryTab, Int>() }
    LaunchedEffect(state.tab, state.loading, state.total, state.failure, state.query) {
        if (!state.loading && state.failure == null && state.query.isBlank()) state.total?.let { totals[state.tab] = it }
    }
    LaunchedEffect(Unit) {
        val other = if (state.tab == LibraryTab.Artists) LibraryTab.Albums else LibraryTab.Artists
        if (totals[other] == null) try {
            val total = withContext(Dispatchers.IO) {
                if (other == LibraryTab.Artists) repo.artists("", ArtistSort.Name, null, null).total else repo.albums("", AlbumSort.Name, null, null).total
            }
            if (total != null) totals[other] = total
        } catch (e: Exception) {
            // The count stays hidden; the tab still works.
        }
    }
    val genreCount = (genreList.state as? Load.Ready)?.value?.let { IndexListsRules.genreCount(it.size) }
    val headCount = when (tab) {
        IndexLibraryTab.Artists -> totals[LibraryTab.Artists]
        IndexLibraryTab.Albums -> totals[LibraryTab.Albums]
        IndexLibraryTab.Genres -> genreCount
    }

    Column(Modifier.fillMaxSize()) {
        IndexPageHead("Library", Modifier.semantics { heading() }, count = headCount?.toString())
        val labels = listOf(
            IndexListsRules.libraryTab("Artists", totals[LibraryTab.Artists]),
            IndexListsRules.libraryTab("Albums", totals[LibraryTab.Albums]),
            IndexListsRules.libraryTab("Genres", genreCount),
        )
        IndexTabs(labels, tab.ordinal, { i ->
            when (IndexLibraryTab.entries[i]) {
                IndexLibraryTab.Artists -> { genres = false; model.selectTab(LibraryTab.Artists) }
                IndexLibraryTab.Albums -> { genres = false; model.selectTab(LibraryTab.Albums) }
                IndexLibraryTab.Genres -> genres = true
            }
        }, Modifier.padding(top = 12.dp))
        if (tab == IndexLibraryTab.Genres) {
            Genres(genreList.state, genreList.reload, open)
            return@Column
        }
        SortLine(state, model)
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
    Box(Modifier.fillMaxSize().padding(Gutter)) { IndexMuted(text) }
}

/** "SORT · DATE ADDED ↓" in mono, one button that opens the sort menu (the Standard page's choices and Reverse). */
@Composable
private fun SortLine(state: LibraryState, model: LibraryViewModel) {
    val p = LocalPalette.current
    var open by remember { mutableStateOf(false) }
    val label = if (state.tab == LibraryTab.Artists) state.artistSort.label else state.albumSort.label
    val noun = if (state.tab == LibraryTab.Artists) "artists" else "albums"
    Box(Modifier.padding(start = Gutter, end = Gutter, top = 4.dp)) {
        Row(
            Modifier.heightIn(min = IndexRules.TOUCH_MIN.dp).clickable(role = Role.Button) { open = true }
                .semantics(mergeDescendants = true) { contentDescription = "Sort $noun, now $label, ${directionLabel(state)}"; liveRegion = LiveRegionMode.Polite },
            verticalAlignment = Alignment.CenterVertically,
        ) { IndexLabel(IndexListsRules.sortLine(label, state.effectiveDescending), color = p.text) }
        if (open) app.discair.ui.common.IndexMenuSheet(
            buildList {
                if (state.tab == LibraryTab.Artists) ArtistSort.entries.forEach { sort ->
                    add(app.discair.ui.common.IndexMenuItem(sort.label, icon = if (sort == state.artistSort) IndexIcons.Check else null) { model.sortArtists(sort) })
                } else AlbumSort.entries.forEach { sort ->
                    add(app.discair.ui.common.IndexMenuItem(sort.label, icon = if (sort == state.albumSort) IndexIcons.Check else null) { model.sortAlbums(sort) })
                }
                add(app.discair.ui.common.IndexMenuItem("Reverse", detail = "Now " + directionLabel(state)) { model.flipDirection() })
            },
            onDismiss = { open = false },
        )
    }
}

/**
 * Artists as rows (frame 2): the index letter in mono `accent` in the number column, a 48dp square photo, the name over "5 ALBUMS · 212 PLAYS", and the three
 * dots with Play and the ways to queue. Sorted A to Z by name with no filter, a letter rail at the right jumps to the first loaded artist of a letter.
 */
@Composable
private fun ArtistRows(state: LibraryState, model: LibraryViewModel, open: Opener, list: LazyListState) {
    val repo = LocalRepository.current
    LaunchedEffect(list, state.nextCursor) {
        snapshotFlow { list.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0 }
            .collect { last -> if (last >= list.layoutInfo.totalItemsCount - 6) model.loadMore() }
    }
    val rail = state.artistSort == ArtistSort.Name && !state.effectiveDescending && state.query.isBlank()
    // Filed by the server's sort key (articles and accents already dropped), so each letter is where the list puts it.
    val letters = remember(state.artists, rail) { if (rail) IndexListsRules.letters(state.artists.map { it.key.ifBlank { it.name } }) else emptyList() }
    Row(Modifier.fillMaxSize()) {
        LazyColumn(Modifier.weight(1f).fillMaxHeight(), state = list, contentPadding = PaddingValues(start = Gutter, end = if (letters.size > 1) 4.dp else Gutter, bottom = LocalBottomClearance.current)) {
            itemsIndexed(state.artists, key = { _, it -> it.id }) { i, artist ->
                IndexRow(
                    artist.name, Modifier.animateItem().indexArrive(i, "artists"), meta = IndexListsRules.artistMeta(artist.albumCount, artist.plays),
                    number = IndexListsRules.letter(artist.key.ifBlank { artist.name }), onClick = { open.artist(artist.name, artist.key, artist.id, null) },
                    lead = { Cover(artist.artworkUrl?.let { repo.absolute(it) }, Modifier.size(48.dp), rect = true) },
                    trail = { ArtistMenu(artist.name, artist.id, artist.artworkUrl?.let { repo.absolute(it) }) },
                )
            }
            if (state.loading) item { IndexMuted("Loading…", Modifier.padding(vertical = Gutter)) }
            if (state.failure != null) item {
                Column(Modifier.padding(vertical = Gutter), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(state.failure.message, color = LocalPalette.current.chartRedText, style = IndexType.body())
                    app.discair.ui.common.IndexButton("Try again", model::loadMore, kind = app.discair.ui.common.IndexButtonKind.Ghost, small = true)
                }
            }
        }
        if (letters.size > 1) LetterRail(letters, list)
    }
}

/** The three dots on an artist row: Play, Shuffle, Play next, Add to queue (the Standard row's play button and menu, in one place). */
@Composable
private fun ArtistMenu(name: String, id: String, artwork: String?) {
    val play = LocalPlayActions.current
    app.discair.ui.common.IndexMenuButton(
        "Play or queue $name",
        app.discair.ui.common.indexMenuItems(
            listOf(
                "Play" to { play.playArtist(id, shuffle = false) },
                "Shuffle" to { play.playArtist(id, shuffle = true) },
                "Play next" to { play.queueArtist(id, next = true) },
                "Add to queue" to { play.queueArtist(id, next = false) },
            ),
        ),
        header = app.discair.ui.common.IndexMenuHeader(name, "Artist") { Cover(artwork, Modifier.size(app.discair.ui.common.IndexSheetRules.HEADER_ART.dp), rect = true) },
        tint = LocalPalette.current.textMuted, size = 20.dp,
    )
}

/**
 * The letter rail: the loaded letters in mono `accent`, 6dp apart, in one 32dp-wide strip. A tap or a drag anywhere on it jumps to the first artist of the
 * letter under the finger. It is one control for touch; a screen reader scrolls the list itself, so the rail is hidden from it.
 */
@Composable
private fun LetterRail(letters: List<Pair<String, Int>>, list: LazyListState) {
    val p = LocalPalette.current
    val scope = rememberCoroutineScope()
    var height by remember { mutableStateOf(0f) }
    fun jump(y: Float) {
        val at = IndexListsRules.letterAt(y, height, letters.size)
        scope.launch { list.scrollToItem(letters[at].second) }
    }
    Box(Modifier.width(32.dp).fillMaxHeight().padding(bottom = LocalBottomClearance.current), contentAlignment = Alignment.Center) {
        Column(
            Modifier.width(32.dp).onSizeChanged { height = it.height.toFloat() }
                .pointerInput(letters) { detectTapGestures { jump(it.y) } }
                .pointerInput(letters) { detectVerticalDragGestures { change, _ -> jump(change.position.y) } }
                .clearAndSetSemantics {},
            horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            letters.forEach { (l, _) -> Text(l, style = IndexType.label(), color = p.accent, maxLines = 1) }
        }
    }
}

/** Albums as two columns (frame 1): a square cover, the name in Inter 600 14 on one line, then "ARTIST · YEAR" in mono. 8dp across, 16dp down. */
@Composable
private fun AlbumGrid(state: LibraryState, model: LibraryViewModel, open: Opener) {
    val p = LocalPalette.current
    val repo = LocalRepository.current
    val grid = rememberLazyGridState()
    LaunchedEffect(grid, state.nextCursor) {
        snapshotFlow { grid.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0 }
            .collect { last -> if (last >= grid.layoutInfo.totalItemsCount - 6) model.loadMore() }
    }
    LazyVerticalGrid(
        columns = GridCells.Fixed(2), state = grid, modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(start = Gutter, end = Gutter, top = 8.dp, bottom = 24.dp + LocalBottomClearance.current),
        horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        items(state.albums.size, key = { state.albums[it].id }) { i ->
            val album = state.albums[i]
            Column(
                Modifier.animateItem().indexArrive(i, "albums").clickable(role = Role.Button) { open.album(album.key, album.artist, album.name, album.id, album.year) }
                    .semantics(mergeDescendants = true) {},
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                Cover(album.artworkUrl?.let { repo.absolute(it) }, Modifier.fillMaxWidth().aspectRatio(1f).sharedCover(album.key), rect = true)
                Text(album.name, color = p.text, style = IndexType.rowTitle().copy(fontSize = 14.sp, lineHeight = 18.sp), maxLines = 1, overflow = TextOverflow.Ellipsis)
                IndexLabel(IndexListsRules.maker(album.artist, album.year), maxLines = 2)
            }
        }
    }
}

/** Genres (Index's third tab): numbered rows with each genre's album count, opening the genre page. The same list as Home's Genres. */
@Composable
private fun Genres(state: Load<List<GenreTile>>, retry: () -> Unit, open: Opener) {
    when (state) {
        Load.Loading -> IndexMuted("Loading…", Modifier.padding(Gutter))
        is Load.Failed -> ErrorBlock(state.failure, retry)
        is Load.Ready -> if (state.value.isEmpty()) Note("No genres yet.") else LazyColumn(
            Modifier.fillMaxSize(), contentPadding = PaddingValues(start = Gutter, end = Gutter, top = 4.dp, bottom = 24.dp + LocalBottomClearance.current),
        ) {
            itemsIndexed(state.value, key = { _, g -> g.tag.ifEmpty { g.name } }) { i, g ->
                IndexRow(
                    g.name, Modifier.indexArrive(i, "genres"), meta = IndexListsRules.albumCount(g.albumCount), number = IndexListsRules.number(i),
                    onClick = { open.genre(g.tag.ifEmpty { g.name }, g.name) }, minHeight = 56.dp,
                    trail = { androidx.compose.material3.Icon(IndexIcons.Chevron, null, tint = LocalPalette.current.textMuted, modifier = Modifier.size(IndexRules.ICON_INLINE.dp)) },
                )
            }
        }
    }
}
