package app.discair.ui.search

import app.discair.ui.common.ArtIcons
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.model.SearchResult
import app.discair.player.QueueItem
import app.discair.ui.Opener
import app.discair.ui.common.Cover
import app.discair.ui.common.CoverStackDivider
import app.discair.ui.common.CoverStackRules
import app.discair.ui.common.CoverStackTitle
import app.discair.ui.common.GetAlbumButton
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.OutlinedTextField
import app.discair.ui.common.Target
import app.discair.ui.common.pageMetadata
import app.discair.ui.common.routeKey
import app.discair.ui.home.Eyebrow
import app.discair.ui.player.LocalPlayActions
import app.discair.ui.player.PlayerIcons
import app.discair.ui.theme.Ink
import app.discair.ui.theme.LocalPalette

/*
 * Soft Brut's (Layout.CoverStack) Search. Mockup: soft-brut/library-search, frame 3.
 * SearchScreen reaches this behind isCoverStack(); the query, the streaming and every tap are the Standard page's.
 */

/** Title, the outlined field, the status line, then results grouped by kind with the owned state said in words. */
@Composable
internal fun CoverStackSearch(
    text: String, onText: (String) -> Unit, state: SearchState, status: String?, focus: FocusRequester,
    onSearchKey: () -> Unit, open: Opener,
) {
    val p = LocalPalette.current
    Column(Modifier.fillMaxSize()) {
        CoverStackTitle("Search", Modifier.padding(start = 16.dp, top = 16.dp, end = 16.dp), maxLines = 1)
        OutlinedTextField(
            value = text, onValueChange = { onText(it.take(200)) }, singleLine = true,
            placeholder = { Text("Artists, albums, songs, genres", color = p.textMuted) },
            leadingIcon = { Icon(ArtIcons.Search, contentDescription = null, tint = p.text) },
            trailingIcon = {
                if (text.isNotEmpty()) IconButton(onClick = { onText("") }, Modifier.size(Target)) {
                    Icon(ArtIcons.Close, contentDescription = "Clear search", tint = p.text)
                }
            },
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
            keyboardActions = KeyboardActions(onSearch = { onSearchKey() }),
            modifier = Modifier.fillMaxWidth().padding(start = 16.dp, end = 19.dp, top = 12.dp, bottom = 8.dp).heightIn(min = 56.dp).focusRequester(focus),
        )
        if (text.isBlank()) Text(
            "In your library first, then everything else.", color = p.textMuted, style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
        )
        status?.let {
            Text(
                it, color = if (state.error != null) Ink.ChartRedText else p.textMuted, style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp).semantics { liveRegion = LiveRegionMode.Polite },
            )
        }
        CoverStackResults(state.results, open)
    }
}

/** One group per kind, in the Standard order; inside a group the owned results come first, then the ones to Get. */
@Composable
private fun CoverStackResults(results: List<SearchResult>, open: Opener) {
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 24.dp)) {
        typeOrder.forEach { (type, title) ->
            val rows = results.filter { it.type == type }.distinctBy { it.id.ifEmpty { it.name } }.sortedByDescending { it.owned }
            if (rows.isNotEmpty()) {
                item(key = "h-$type") { Eyebrow(title, Modifier.padding(start = 16.dp, end = 16.dp, top = 18.dp, bottom = 6.dp).semantics { heading() }) }
                items(rows, key = { "r-${it.type}-${it.id.ifEmpty { it.name }}-${it.owned}" }) { CoverStackResultRow(it, open, Modifier.animateItem()) }
            }
        }
    }
}

@Composable
private fun CoverStackResultRow(r: SearchResult, open: Opener, modifier: Modifier = Modifier) {
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
        r.type == "song" && artist != null && album != null -> { { open.album(routeKey(artist, album), artist, album, null, null) } }
        r.type == "genre" -> { { open.genre(r.tag ?: r.key, r.name) } }
        else -> null
    }
    // Detail line; the owned state is a word, coloured as well, never colour alone.
    val detail = buildAnnotatedString {
        val base = when (r.type) {
            "artist" -> listOfNotNull(r.albumCount?.let { if (it == 1) "1 album" else "$it albums" }, r.genre).joinToString(" · ")
            "album" -> listOfNotNull(r.artist, r.year?.toString()).joinToString(" · ")
            "song" -> listOfNotNull(r.artist, r.album).joinToString(" · ")
            else -> ""
        }
        append(base)
        val state = when {
            r.type == "genre" || r.type == "song" -> null
            r.owned -> "In your library"
            else -> "Not in your library"
        }
        if (state != null) {
            if (base.isNotEmpty()) append(" · ")
            if (r.owned) withStyle(SpanStyle(color = p.ok, fontWeight = FontWeight.SemiBold)) { append(state) } else append(state)
        }
    }
    Column(modifier) {
        Row(
            Modifier.fillMaxWidth().heightIn(min = 64.dp).let { if (go != null) it.clickable(role = Role.Button, onClick = go) else it }
                .padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 8.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (r.type != "genre") {
                val shape = if (r.type == "artist") CircleShape else RoundedCornerShape(6.dp)
                Cover(r.artworkUrl?.let(repo::absolute), Modifier.size(48.dp).clip(shape).border(CoverStackRules.outline(p).dp, p.edgeStrong, shape), circle = r.type == "artist")
            }
            Column(Modifier.weight(1f)) {
                Text(r.name, color = p.text, maxLines = 2, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 14.sp))
                if (detail.isNotEmpty()) Text(detail, color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall)
            }
            when {
                ownedSong != null -> IconButton(onClick = { play.queueSong(ownedSong, next = false) }, Modifier.size(Target)) {
                    Icon(ArtIcons.QueueAdd, contentDescription = "Add ${r.name} to the queue", tint = p.text)
                }
                r.type == "album" && !r.owned && artist != null -> GetAlbumButton(artist, r.name, pageMetadata(artist, r.name, r.year))
                go != null -> Icon(ArtIcons.Chevron, contentDescription = null, tint = p.text)
            }
        }
        CoverStackDivider(Modifier.padding(horizontal = 16.dp))
    }
}
