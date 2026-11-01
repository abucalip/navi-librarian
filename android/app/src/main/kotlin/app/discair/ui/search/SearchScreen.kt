package app.discair.ui.search

import androidx.compose.foundation.clickable
import androidx.compose.ui.semantics.Role
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.model.SearchEvent
import app.discair.model.SearchResult
import app.discair.net.ConnectionException
import app.discair.net.classifyException
import app.discair.ui.Opener
import app.discair.ui.common.Cover
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.OwnedMark
import app.discair.ui.common.PageHeading
import app.discair.ui.common.RowDivider
import app.discair.ui.common.Target
import app.discair.ui.common.routeKey
import app.discair.ui.theme.Ink
import kotlin.coroutines.cancellation.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.delay
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext

/** Where a search stands. Results stay in the order the server streamed them; nothing is re-ranked here. */
private data class SearchState(
    val results: List<SearchResult> = emptyList(),
    val running: Boolean = false,
    val done: Boolean = false,
    val partial: Boolean = false,
    val sourceProblem: Boolean = false,
    val error: String? = null,
)

private val typeOrder = listOf("artist" to "Artists", "album" to "Albums", "song" to "Songs", "genre" to "Genres")

@Composable
fun SearchScreen(open: Opener) {
    val repo = LocalRepository.current
    var text by rememberSaveable { mutableStateOf("") }
    var state by remember { mutableStateOf(SearchState()) }
    val focus = remember { FocusRequester() }
    val keyboard = androidx.compose.ui.platform.LocalSoftwareKeyboardController.current

    // A new query waits 400 ms for more typing, then replaces the running one (its stream is dropped).
    LaunchedEffect(text) {
        val query = text.trim()
        if (query.isEmpty()) { state = SearchState(); return@LaunchedEffect }
        delay(400)
        state = SearchState(running = true)
        val collected = ArrayList<SearchResult>()
        try {
            withContext(Dispatchers.IO) {
                val context = currentCoroutineContext()
                repo.search(query.take(200)) { event ->
                    // Throwing here ends the read and closes the connection once the query has changed.
                    context.ensureActive()
                    when (event) {
                        is SearchEvent.Result -> { collected += event.result; state = state.copy(results = collected.toList()) }
                        is SearchEvent.Source ->
                            if (event.source.state in setOf("failed", "timeout", "rate_limited")) state = state.copy(sourceProblem = true)
                        is SearchEvent.Done -> state = state.copy(running = false, done = true, partial = event.partial)
                        is SearchEvent.Error -> state = state.copy(running = false, error = event.message)
                        SearchEvent.Capabilities -> Unit
                    }
                }
            }
            if (state.running) state = state.copy(running = false, done = true)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            val failure = (e as? ConnectionException)?.failure ?: classifyException(e, networkAvailable = true)
            state = state.copy(running = false, error = failure.message)
        }
    }
    LaunchedEffect(Unit) { if (text.isEmpty()) focus.requestFocus() }

    Column(Modifier.fillMaxSize()) {
        PageHeading("Search", Modifier.padding(start = 16.dp, top = 12.dp, end = 16.dp), large = true)
        OutlinedTextField(
            value = text, onValueChange = { text = it.take(200) }, singleLine = true,
            label = { Text("Artists, albums, songs, genres") },
            leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
            trailingIcon = {
                if (text.isNotEmpty()) IconButton(onClick = { text = "" }, Modifier.size(Target)) {
                    Icon(Icons.Default.Clear, contentDescription = "Clear search")
                }
            },
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
            keyboardActions = KeyboardActions(onSearch = { keyboard?.hide() }), // typing already searches
            modifier = Modifier.fillMaxWidth().padding(16.dp).focusRequester(focus),
        )
        val status = when {
            state.error != null -> state.error
            text.isBlank() -> null
            state.running && state.results.isEmpty() -> "Searching…"
            state.running -> "Still searching…"
            state.done && state.results.isEmpty() -> "No matches."
            state.sourceProblem || state.partial -> "Some sources did not answer, so this may be incomplete."
            else -> null
        }
        status?.let {
            Text(
                it, style = MaterialTheme.typography.bodyMedium,
                color = if (state.error != null) Ink.ChartRedText else MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp).semantics { liveRegion = LiveRegionMode.Polite },
            )
        }
        Results(state.results, open)
    }
}

@Composable
private fun Results(results: List<SearchResult>, open: Opener) {
    val owned = results.filter { it.owned }
    val other = results.filter { !it.owned }
    LazyColumn(Modifier.fillMaxSize().imePadding(), contentPadding = PaddingValues(bottom = 24.dp)) {
        typeOrder.forEach { (type, title) ->
            val rows = owned.filter { it.type == type }
            if (rows.isNotEmpty()) {
                item(key = "h-$type") { GroupHeading(title) }
                items(rows.distinctBy { it.id }, key = { "o-${it.type}-${it.id}" }) { ResultRow(it, open) }
            }
        }
        if (other.isNotEmpty()) {
            item(key = "h-other") { GroupHeading("Not in your library") }
            items(other.distinctBy { it.type + it.id }, key = { "x-${it.type}-${it.id}" }) { ResultRow(it, open, showType = true) }
        }
    }
}

@Composable
private fun GroupHeading(text: String) {
    Text(
        text, style = MaterialTheme.typography.titleMedium,
        modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 20.dp, bottom = 4.dp).semantics { heading() },
    )
}

@Composable
private fun ResultRow(r: SearchResult, open: Opener, showType: Boolean = false) {
    val repo = LocalRepository.current
    val ownedId = r.id.takeIf { r.owned }
    val detail = when (r.type) {
        "artist" -> listOfNotNull(r.albumCount?.let { if (it == 1) "1 album" else "$it albums" }, r.genre).joinToString(" · ")
        "album" -> listOfNotNull(r.artist, r.year?.toString()).joinToString(" · ")
        "song" -> listOfNotNull(r.artist, r.album).joinToString(" · ")
        else -> ""
    }
    val subtitle = listOfNotNull(
        if (showType) r.type.replaceFirstChar { it.uppercase() } else null,
        detail.takeIf { it.isNotBlank() },
    ).joinToString(" · ")
    val artist = r.artist
    val album = r.album
    val go: (() -> Unit)? = when {
        r.type == "artist" -> { { open.artist(r.name, r.key, ownedId, r.mbid) } }
        r.type == "album" && artist != null -> { { open.album(r.key, artist, r.name, ownedId, r.year) } }
        // A song opens its album's page, which lists the track.
        r.type == "song" && artist != null && album != null -> { { open.album(routeKey(artist, album), artist, album, null, null) } }
        r.type == "genre" -> { { open.genre(r.tag ?: r.key, r.name) } }
        else -> null
    }
    Column {
        Row(
            Modifier.fillMaxWidth().heightIn(min = 64.dp).let { if (go != null) it.clickable(role = Role.Button, onClick = go) else it }
                .padding(horizontal = 16.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (r.type != "genre") Cover(r.artworkUrl?.let(repo::absolute), Modifier.size(48.dp), circle = r.type == "artist")
            Column(Modifier.weight(1f)) {
                Text(r.name, style = MaterialTheme.typography.bodyLarge, maxLines = 2, overflow = TextOverflow.Ellipsis)
                if (subtitle.isNotEmpty()) Text(
                    subtitle, style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis,
                )
            }
            OwnedMark(r.owned)
        }
        RowDivider()
    }
}
