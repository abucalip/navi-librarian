package app.discair.ui.search

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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.model.SearchResult
import app.discair.player.QueueItem
import app.discair.ui.Opener
import app.discair.ui.common.Cover
import app.discair.ui.common.GalleryEyebrow
import app.discair.ui.common.GalleryGetAlbumButton
import app.discair.ui.common.GalleryIconButton
import app.discair.ui.common.GalleryIcons
import app.discair.ui.common.GalleryListsRules
import app.discair.ui.common.GalleryMuted
import app.discair.ui.common.GalleryPrint
import app.discair.ui.common.GalleryRow
import app.discair.ui.common.GalleryRules
import app.discair.ui.common.GalleryState
import app.discair.ui.common.GalleryType
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.pageMetadata
import app.discair.ui.common.routeKey
import app.discair.ui.player.LocalPlayActions
import app.discair.ui.theme.LocalPalette

/*
 * Gallery's Search (Layout.Gallery). Spec: docs/GALLERY_THEME.md section 10; mockup: docs/design/gallery/pages/library-search.html, frame 3.
 * "Search" as the catalogue line over "What are you looking for?", the field as Fraunces text over a 1.5dp rule, then results in groups (Artists, Albums, Songs,
 * Genres) with a count at the right of each heading; owned is said in words ("In library"), a missing album has a small Get. The query, the streaming and every
 * tap are the page every theme has (SearchScreen).
 */

private val Gutter = GalleryRules.GUTTER.dp

@Composable
internal fun GallerySearch(
    text: String, onText: (String) -> Unit, state: SearchState, status: String?, focus: FocusRequester, onSearchKey: () -> Unit, open: Opener,
) {
    val p = LocalPalette.current
    Column(Modifier.fillMaxSize()) {
        Column(Modifier.fillMaxWidth().padding(start = Gutter, end = Gutter, top = 16.dp)) {
            GalleryEyebrow("Search", Modifier.padding(bottom = 4.dp))
            Text("What are you looking for?", Modifier.semantics { heading() }, color = p.text, style = GalleryType.largeTitle.copy(fontSize = 26.sp, lineHeight = 30.sp))
        }
        Field(text, onText, focus, onSearchKey)
        if (text.isBlank()) GalleryMuted("In your library first, then everything else.", Modifier.padding(horizontal = Gutter, vertical = 14.dp))
        status?.let {
            Text(
                it, Modifier.padding(horizontal = Gutter, vertical = 10.dp).semantics { liveRegion = LiveRegionMode.Polite },
                color = if (state.error != null) p.chartRedText else p.textMuted, style = GalleryType.small(),
            )
        }
        Results(state.results, open)
    }
}

/** The field (gallery.css `.field`): no box, Fraunces 22 over a 1.5dp `text` rule, a `control` search icon at the left and a clear button at the right once typed. */
@Composable
private fun Field(text: String, onText: (String) -> Unit, focus: FocusRequester, onSearchKey: () -> Unit) {
    val p = LocalPalette.current
    Row(
        Modifier.fillMaxWidth().padding(horizontal = Gutter).padding(top = 6.dp)
            .drawBehind { drawRect(p.text, Offset(0f, size.height - 1.5.dp.toPx()), Size(size.width, 1.5.dp.toPx())) }
            .padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Icon(GalleryIcons.Search, null, tint = p.control, modifier = Modifier.size(GalleryRules.ICON.dp))
        Box(Modifier.weight(1f), contentAlignment = Alignment.CenterStart) {
            if (text.isEmpty()) Text("Artists, albums, songs, genres", color = p.textMuted, maxLines = 1, style = GalleryType.searchField)
            BasicTextField(
                value = text, onValueChange = { onText(it.take(200)) }, singleLine = true, textStyle = GalleryType.searchField.copy(color = p.text),
                cursorBrush = SolidColor(p.control),
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search), keyboardActions = KeyboardActions(onSearch = { onSearchKey() }),
                modifier = Modifier.fillMaxWidth().focusRequester(focus).semantics { contentDescription = "Search artists, albums, songs, genres" },
            )
        }
        if (text.isNotEmpty()) GalleryIconButton(GalleryIcons.Close, "Clear search", { onText("") }, Modifier.size(40.dp), size = 20.dp)
    }
}

/** One group per kind in the Standard order; inside a group the owned results come first, then the ones to Get. The count sits at the right of the heading. */
@Composable
private fun Results(results: List<SearchResult>, open: Opener) {
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 24.dp)) {
        typeOrder.forEach { (type, title) ->
            val rows = results.filter { it.type == type }.distinctBy { it.id.ifEmpty { it.name } }.sortedByDescending { it.owned }
            if (rows.isNotEmpty()) {
                item(key = "h-$type") {
                    Row(
                        Modifier.fillMaxWidth().padding(start = Gutter, end = Gutter, top = 22.dp, bottom = 4.dp).semantics { heading() },
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        GalleryEyebrow(title)
                        GalleryEyebrow(rows.size.toString())
                    }
                }
                items(rows, key = { "r-${it.type}-${it.id.ifEmpty { it.name }}-${it.owned}" }) { ResultRow(it, open, Modifier.animateItem()) }
            }
        }
    }
}

@Composable
private fun ResultRow(r: SearchResult, open: Opener, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    val repo = LocalRepository.current
    val play = LocalPlayActions.current
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
    val photo = r.type == "artist"
    val printSize = if (photo) 52.dp else 48.dp
    val lead: @Composable () -> Unit = {
        GalleryPrint(printSize, Modifier.width(printSize)) { Cover(r.artworkUrl?.let(repo::absolute), Modifier.fillMaxWidth().aspectRatio(1f), rect = true) }
    }
    GalleryRow(
        r.name, modifier.padding(horizontal = Gutter), sub = GalleryListsRules.searchDetail(r.type, r.owned, r.artist, r.album, r.year, r.albumCount, r.genre),
        onClick = go, italicTitle = r.type == "album" || r.type == "song", minHeight = if (photo) 72.dp else GalleryRules.ROW_MIN.dp,
        lead = if (r.type == "genre") null else lead,
        trail = {
            when {
                ownedSong != null -> GalleryIconButton(GalleryIcons.QueueAdd, "Add ${r.name} to the queue", { play.queueSong(ownedSong, next = false) })
                r.type == "album" && !r.owned && artist != null -> GalleryGetAlbumButton(artist, r.name, pageMetadata(artist, r.name, r.year), primary = false)
                r.type == "genre" -> Icon(GalleryIcons.Chevron, null, tint = p.control, modifier = Modifier.size(GalleryRules.ICON_INLINE.dp))
                r.type != "song" && r.owned -> GalleryState("In library", color = p.ok)
                r.type == "artist" -> GalleryState("Not in library")
                else -> Unit
            }
        },
    )
}
