package app.discair.ui.search

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
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
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextStyle
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
import app.discair.ui.common.FlowChevron
import app.discair.ui.common.FlowDivider
import app.discair.ui.common.FlowEyebrow
import app.discair.ui.common.FlowGetButton
import app.discair.ui.common.FlowLargeTitle
import app.discair.ui.common.FlowPagesRules
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.Target
import app.discair.ui.common.pageMetadata
import app.discair.ui.common.routeKey
import app.discair.ui.player.LocalPlayActions
import app.discair.ui.player.PlayerIcons
import app.discair.ui.theme.LocalPalette

/*
 * Flow's Search. Mockup: flow/library-search, frame 3 (flow.css `.field`, `.li`, `.eb`).
 * SearchScreen reaches this behind isFlow(); the query, the streaming and every tap are the Standard page's. Search is a sheet over the page, so
 * it carries its own large title; the mockup's two round buttons beside it belong to the shell's bar, which the sheet covers.
 */

/** The large title, the 44dp field, the status line, then results grouped by kind with the owned state said in words. */
@Composable
internal fun FlowSearch(
    text: String, onText: (String) -> Unit, state: SearchState, status: String?, focus: FocusRequester,
    onSearchKey: () -> Unit, open: Opener,
) {
    val p = LocalPalette.current
    Column(Modifier.fillMaxSize()) {
        FlowLargeTitle("Search", Modifier.padding(start = 16.dp, top = 16.dp, end = 16.dp))
        FlowSearchField(text, onText, focus, onSearchKey, Modifier.padding(start = 16.dp, end = 16.dp, top = 12.dp, bottom = 8.dp))
        if (text.isBlank()) Text(
            "In your library first, then everything else.", color = p.textMuted, style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
        )
        status?.let {
            Text(
                it, color = if (state.error != null) p.chartRedText else p.textMuted, style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp).semantics { liveRegion = LiveRegionMode.Polite },
            )
        }
        FlowResults(state.results, open)
    }
}

/** The field (`.field`): 44dp, radius 12, `raised`, a muted search glyph, 16sp text, and a clear button once something is typed. */
@Composable
private fun FlowSearchField(text: String, onText: (String) -> Unit, focus: FocusRequester, onSearchKey: () -> Unit, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    Row(
        modifier.fillMaxWidth().height(FlowPagesRules.FIELD_HEIGHT.dp).clip(RoundedCornerShape(12.dp)).background(p.raised).padding(start = 12.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Icon(Icons.Default.Search, contentDescription = null, tint = p.textMuted, modifier = Modifier.size(20.dp))
        Box(Modifier.weight(1f), contentAlignment = Alignment.CenterStart) {
            if (text.isEmpty()) Text("Artists, albums, songs, genres", color = p.textMuted, maxLines = 1, style = MaterialTheme.typography.bodyLarge.copy(fontSize = 16.sp))
            BasicTextField(
                value = text, onValueChange = { onText(it.take(200)) }, singleLine = true,
                textStyle = TextStyle(color = p.text, fontSize = 16.sp, fontFamily = MaterialTheme.typography.bodyLarge.fontFamily),
                cursorBrush = SolidColor(p.accent),
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                keyboardActions = KeyboardActions(onSearch = { onSearchKey() }),
                modifier = Modifier.fillMaxWidth().focusRequester(focus).semantics { contentDescription = "Search artists, albums, songs, genres" },
            )
        }
        if (text.isNotEmpty()) IconButton(onClick = { onText("") }, Modifier.size(Target)) {
            Icon(Icons.Default.Clear, contentDescription = "Clear search", tint = p.textMuted, modifier = Modifier.size(20.dp))
        }
    }
}

/** One group per kind, in the Standard order, headed by a small caption in capitals; inside a group the owned results come first, then the ones to Get. */
@Composable
private fun FlowResults(results: List<SearchResult>, open: Opener) {
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 24.dp)) {
        typeOrder.forEach { (type, title) ->
            val rows = results.filter { it.type == type }.distinctBy { it.id.ifEmpty { it.name } }.sortedByDescending { it.owned }
            if (rows.isNotEmpty()) {
                item(key = "h-$type") { FlowEyebrow(title, Modifier.padding(start = 16.dp, end = 16.dp, top = 18.dp, bottom = 6.dp).semantics { heading() }) }
                items(rows, key = { "r-${it.type}-${it.id.ifEmpty { it.name }}-${it.owned}" }) { FlowResultRow(it, open, Modifier.animateItem()) }
            }
        }
    }
}

@Composable
private fun FlowResultRow(r: SearchResult, open: Opener, modifier: Modifier = Modifier) {
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
        val owned = when {
            r.type == "genre" || r.type == "song" -> null
            r.owned -> "In your library"
            else -> "Not in your library"
        }
        if (owned != null) {
            if (base.isNotEmpty()) append(" · ")
            if (r.owned) withStyle(SpanStyle(color = p.ok, fontWeight = FontWeight.SemiBold)) { append(owned) } else append(owned)
        }
    }
    Column(modifier) {
        Row(
            Modifier.fillMaxWidth().heightIn(min = 64.dp).let { if (go != null) it.clickable(role = Role.Button, onClick = go) else it }
                .padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 8.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (r.type != "genre") {
                val shape = if (r.type == "artist") CircleShape else RoundedCornerShape(8.dp)
                Cover(r.artworkUrl?.let(repo::absolute), Modifier.size(FlowPagesRules.ROW_COVER.dp).clip(shape), circle = r.type == "artist")
            }
            Column(Modifier.weight(1f)) {
                Text(r.name, color = p.text, maxLines = 2, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 15.sp, lineHeight = 20.sp))
                if (detail.isNotEmpty()) Text(detail, color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall.copy(fontSize = 13.sp, lineHeight = 18.sp))
            }
            when {
                ownedSong != null -> IconButton(onClick = { play.queueSong(ownedSong, next = false) }, Modifier.size(Target)) {
                    Icon(PlayerIcons.QueueAdd, contentDescription = "Add ${r.name} to the queue", tint = p.text)
                }
                r.type == "album" && !r.owned && artist != null -> FlowGetButton(artist, r.name, pageMetadata(artist, r.name, r.year))
                go != null -> FlowChevron()
            }
        }
        FlowDivider(Modifier.padding(horizontal = 16.dp))
    }
}
