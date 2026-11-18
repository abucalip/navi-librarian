package app.discair.ui.search

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import app.discair.model.SearchResult
import app.discair.player.QueueItem
import app.discair.ui.Opener
import app.discair.ui.common.Cover
import app.discair.ui.common.IndexButtonBody
import app.discair.ui.common.IndexButtonKind
import app.discair.ui.common.IndexGet
import app.discair.ui.common.IndexGetButton
import app.discair.ui.common.IndexIconButton
import app.discair.ui.common.IndexIcons
import app.discair.ui.common.IndexLabel
import app.discair.ui.common.IndexListsRules
import app.discair.ui.common.IndexMuted
import app.discair.ui.common.IndexPageHead
import app.discair.ui.common.IndexRow
import app.discair.ui.common.IndexRules
import app.discair.ui.common.IndexSectionHead
import app.discair.ui.common.IndexState
import app.discair.ui.common.IndexType
import app.discair.ui.common.LocalAcquisitions
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.OutlinedTextField
import app.discair.ui.common.indexGetOf
import app.discair.ui.common.pageMetadata
import app.discair.ui.common.routeKey
import app.discair.ui.player.LocalPlayActions
import app.discair.ui.theme.LocalPalette

/*
 * Index's Search (Layout.Index). Spec: docs/plans/INDEX_THEME.md step I4; mockup: docs/design/index/pages/library-search.html, frame 3.
 * "Search" as the page head, the square 52dp field with its 2dp outline, the state of the search as a mono line, then three groups with counts: Artist,
 * In your library, Not in your library (last, with Get). The query, the streaming and every tap are the page every theme has (SearchScreen).
 */

private val Gutter = IndexRules.GUTTER.dp

@Composable
internal fun IndexSearch(
    text: String, onText: (String) -> Unit, state: SearchState, status: String?, focus: FocusRequester, onSearchKey: () -> Unit, open: Opener,
) {
    val p = LocalPalette.current
    Column(Modifier.fillMaxSize()) {
        IndexPageHead("Search", Modifier.semantics { heading() })
        // The shared field draws Index's square outline (BrutalComponents' Index branch).
        OutlinedTextField(
            value = text, onValueChange = { onText(it.take(200)) }, singleLine = true,
            placeholder = { Text("Artists, albums, songs, genres", color = p.textMuted, style = IndexType.field(), maxLines = 1) },
            leadingIcon = { Icon(IndexIcons.Search, null, tint = p.text, modifier = Modifier.size(IndexRules.ICON.dp)) },
            trailingIcon = { if (text.isNotEmpty()) IndexIconButton(IndexIcons.Close, "Clear search", { onText("") }) },
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search), keyboardActions = KeyboardActions(onSearch = { onSearchKey() }),
            modifier = Modifier.fillMaxWidth().padding(start = Gutter, end = Gutter, top = 12.dp).focusRequester(focus)
                .semantics { contentDescription = "Search artists, albums, songs, genres" },
        )
        if (text.isBlank()) IndexMuted("In your library first, then everything else.", Modifier.padding(horizontal = Gutter, vertical = 10.dp))
        status?.let {
            IndexLabel(
                it, Modifier.padding(horizontal = Gutter).padding(top = 8.dp).semantics { liveRegion = LiveRegionMode.Polite },
                color = if (state.error != null) p.chartRedText else p.textMuted, maxLines = 2,
            )
        }
        Results(state.results, open)
    }
}

/** The groups in the mockup's order, each a section head with its count and rows in the server's order. */
@Composable
private fun Results(results: List<SearchResult>, open: Opener) {
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 24.dp)) {
        for ((group, rows) in IndexListsRules.searchGroups(results)) {
            item(key = "h-${group.name}") { IndexSectionHead(group.title(rows.size), meta = rows.size.toString(), modifier = Modifier.padding(top = 0.dp)) }
            items(rows, key = { "${group.name}-" + IndexListsRules.searchKey(it) }) { ResultRow(it, open, Modifier.animateItem().padding(horizontal = Gutter)) }
        }
    }
}

/**
 * One result as an Index row: a 48dp square cover (the artist's photo), or for an owned song a ghost Play square; the name over the mono meta line; then the
 * trail: a chevron for an artist or a genre, IN LIBRARY for an owned album, Get for a missing one, Add to queue for an owned song.
 */
@Composable
private fun ResultRow(r: SearchResult, open: Opener, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    val repo = LocalRepository.current
    val play = LocalPlayActions.current
    val hub = LocalAcquisitions.current
    val ownedId = r.id.takeIf { r.owned }
    val artist = r.artist
    val album = r.album
    val ownedSong = if (r.type == "song" && r.owned && !r.albumId.isNullOrBlank()) QueueItem(
        songId = r.id, title = r.name, artist = r.artist.orEmpty(), album = r.album.orEmpty(), albumId = r.albumId,
        coverId = r.albumId, coverUrl = repo.absolute("/api/owned/artwork/${r.albumId}"), durationSec = r.duration ?: 0,
        year = r.year, bitRateKbps = r.bitRate, suffix = r.suffix.orEmpty(), bitDepth = r.bitDepth, samplingRateHz = r.samplingRate,
    ) else null
    val go: (() -> Unit)? = when {
        ownedSong != null -> { { play.playSong(ownedSong) } }
        r.type == "artist" -> { { open.artist(r.name, r.key, ownedId, r.mbid) } }
        r.type == "album" && artist != null -> { { open.album(r.key, artist, r.name, ownedId, r.year) } }
        // A song opens its album's page, which lists the track.
        r.type == "song" && artist != null && album != null -> { { open.album(routeKey(artist, album), artist, album, null, null) } }
        r.type == "genre" -> { { open.genre(r.tag ?: r.key, r.name) } }
        else -> null
    }
    IndexRow(
        r.name, modifier, meta = IndexListsRules.searchMeta(r), onClick = go,
        lead = when {
            ownedSong != null -> { { IndexButtonBody(IndexButtonKind.Ghost, { play.playSong(ownedSong) }, Modifier.size(48.dp), enabled = true) { Icon(IndexIcons.Play, null, Modifier.size(IndexRules.ICON_INLINE.dp)) } } }
            r.type == "genre" -> null
            else -> { { Cover(r.artworkUrl?.let(repo::absolute), Modifier.size(48.dp), rect = true) } }
        },
        trail = {
            when {
                ownedSong != null -> IndexIconButton(IndexIcons.QueueAdd, "Add ${r.name} to the queue", { play.queueSong(ownedSong, next = false) }, tint = p.textMuted, size = 20.dp)
                r.type == "album" && !r.owned && artist != null -> IndexGetButton(
                    indexGetOf(hub.getState(artist, r.name)), { hub.getAlbum(artist, r.name, pageMetadata(artist, r.name, r.year)) },
                    Modifier.semantics { contentDescription = "Get album ${r.name}" },
                )
                r.type == "artist" || r.type == "genre" -> Icon(IndexIcons.Chevron, null, tint = p.text, modifier = Modifier.size(IndexRules.ICON.dp))
                r.type == "album" && r.owned -> IndexGetButton(IndexGet.Owned, {})
                r.type != "song" && r.owned -> IndexState("In library", color = p.ok)
                else -> Unit
            }
        },
    )
}
