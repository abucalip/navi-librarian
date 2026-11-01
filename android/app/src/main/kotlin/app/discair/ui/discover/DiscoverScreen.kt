package app.discair.ui.discover

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items as gridItems
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.SnackbarResult
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.input.nestedscroll.NestedScrollConnection
import androidx.compose.ui.input.nestedscroll.NestedScrollSource
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.unit.Velocity
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import app.discair.model.DiscoveryEntry
import app.discair.model.DiscoveryList
import app.discair.model.DiscoveryResult
import app.discair.model.FeedbackAction
import app.discair.model.LensLists
import app.discair.ui.Opener
import app.discair.ui.common.Load
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.PageHeading
import app.discair.ui.common.EditorTabs
import app.discair.ui.common.SegmentedTabs
import app.discair.ui.common.SaveState
import app.discair.ui.common.Target
import app.discair.ui.common.rememberLoad
import app.discair.ui.theme.Ink
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull

/** How long Undo stays on screen before a dismissal is sent. Longer than the web's 4.2 s for TalkBack. */
private const val UNDO_MS = 6000L

private fun countFor(list: DiscoveryList) = when (list) {
    DiscoveryList.DeepDive -> 60
    DiscoveryList.Saved -> 150
    else -> 30
}

/** A list name (or one lens) with what the server returned for it, or why it could not be read. */
private data class Section(val title: String?, val path: String, val result: DiscoveryResult?, val error: String?)

@Composable
fun DiscoverScreen(open: Opener) {
    val repo = LocalRepository.current
    val scope = rememberCoroutineScope()
    val snackbar = remember { SnackbarHostState() }
    var selected by rememberSaveable { mutableStateOf(DiscoveryList.Daily.name) }
    val list = DiscoveryList.valueOf(selected)
    var statusLine by remember { mutableStateOf<String?>(null) }
    val saves = remember { mutableStateMapOf<String, SaveState>() }
    val hidden = remember { mutableStateMapOf<String, Boolean>() }
    var pending by remember { mutableStateOf<(suspend () -> Unit)?>(null) }

    val loaded = rememberLoad(list) {
        if (list == DiscoveryList.Daily) kotlinx.coroutines.runBlocking {
            // The four lens lists are read together, not one after the other.
            val cacheOnly = app.discair.data.ReadMode.isCacheOnly
            LensLists.map { (path, title) ->
                async(Dispatchers.IO) {
                    try {
                        app.discair.data.ReadMode.only(cacheOnly) {
                        Section(title, path, repo.discovery(path, 10), null)
                        }
                    } catch (e: Exception) {
                        // A missing saved copy fails the whole first paint, so the page waits for the server.
                        if (cacheOnly) throw e
                        Section(title, path, null, e.message ?: "Request failed.")
                    }
                }
            }.map { it.await() }
        } else listOf(Section(null, list.path, repo.discovery(list.path, countFor(list)), null))
    }

    /** Commits the dismissal waiting in [pending], if any, so only one waits at a time (as on the web). */
    suspend fun commitPending() {
        pending?.let { pending = null; it() }
    }

    fun dismiss(entry: DiscoveryEntry, artistToo: Boolean) {
        val action = if (artistToo) FeedbackAction.DismissArtist else FeedbackAction.Dismiss
        val label = if (artistToo) "Dismissed ${entry.item.artistName}." else "Dismissed ${entry.item.album}."
        scope.launch {
            commitPending()
            hidden[entry.key] = true
            val send: suspend () -> Unit = {
                try {
                    withContext(Dispatchers.IO) {
                        repo.feedback(action, entry.item.artistName, entry.item.album, entry.raw)
                    }
                } catch (e: Exception) {
                    hidden.remove(entry.key)
                    statusLine = e.message ?: "The dismissal was not saved."
                }
            }
            pending = send
            val result = withTimeoutOrNull(UNDO_MS) {
                snackbar.showSnackbar(label, actionLabel = "Undo", withDismissAction = false,
                    duration = androidx.compose.material3.SnackbarDuration.Indefinite)
            }
            if (result == SnackbarResult.ActionPerformed) {
                if (pending === send) pending = null
                hidden.remove(entry.key)
            } else if (pending === send) {
                pending = null
                send()
            }
        }
    }

    fun save(entry: DiscoveryEntry, inSavedList: Boolean) {
        val current = saves[entry.key] ?: if (inSavedList) SaveState.Saved else SaveState.Idle
        val wasSaved = current == SaveState.Saved
        saves[entry.key] = SaveState.Pending
        scope.launch {
            saves[entry.key] = try {
                withContext(Dispatchers.IO) {
                    repo.feedback(
                        if (wasSaved) FeedbackAction.RemoveSaved else FeedbackAction.Save,
                        entry.item.artistName, entry.item.album, entry.raw,
                    )
                }
                if (wasSaved) SaveState.Idle else SaveState.Saved
            } catch (e: Exception) {
                statusLine = e.message ?: "Could not update the bookmark."
                // Back to the last state the server confirmed, marked as failed so Retry is clear.
                if (wasSaved) SaveState.Saved else SaveState.Failed
            }
        }
    }

    // Leaving the tab must not lose a dismissal that is still inside its Undo window.
    androidx.compose.runtime.DisposableEffect(Unit) {
        onDispose {
            pending?.let { send ->
                pending = null
                kotlinx.coroutines.CoroutineScope(Dispatchers.IO).launch { send() }
            }
        }
    }

    // The shell's Scaffold already insets for the bars, so this one adds none (it left a gap under the header).
    Scaffold(snackbarHost = { SnackbarHost(snackbar) }, contentWindowInsets = androidx.compose.foundation.layout.WindowInsets(0)) { padding ->
        fun switchBy(step: Int) {
            val options = DiscoveryList.entries
            val target = options.indexOf(list) + step
            if (target in options.indices) { selected = options[target].name; statusLine = null }
        }
        val swipeThreshold = with(androidx.compose.ui.platform.LocalDensity.current) { 72.dp.toPx() }
        // A sideways swipe moves between Discover's own tabs and never reaches the app's tab swipe, so it cannot
        // leave for Home or Search. Swipes the card pager uses (Daily picks, Deep dives) are used there first;
        // one it cannot use, past its last page, moves to the next tab here.
        Column(Modifier.padding(padding).fillMaxSize().pointerInput(list) {
            var total = 0f
            detectHorizontalDragGestures(
                onDragStart = { total = 0f },
                onDragCancel = { total = 0f },
                onDragEnd = { switchBy(if (total < -swipeThreshold) 1 else if (total > swipeThreshold) -1 else 0) },
            ) { _, delta -> total += delta }
        }) {
            PageHeading("Discover", Modifier.padding(start = 16.dp, top = 12.dp, end = 16.dp), large = true)
            val options = DiscoveryList.entries
            SegmentedTabs(
                options.map { it.label }, options.indexOf(list),
                onSelect = { i -> if (options[i] != list) { selected = options[i].name; statusLine = null } },
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
            )
            statusLine?.let {
                Text(
                    it, color = Ink.ChartRedText, style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp)
                        .semantics { liveRegion = LiveRegionMode.Polite },
                )
            }
            when (val state = loaded.state) {
                Load.Loading -> Column(Modifier.fillMaxSize(), verticalArrangement = Arrangement.Center,
                    horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally) {
                    CircularProgressIndicator(Modifier.semantics { contentDescription = "Loading" })
                }
                is Load.Failed -> Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(state.failure.message, color = Ink.ChartRedText)
                    OutlinedButton(onClick = loaded.reload, Modifier.heightIn(min = Target)) { Text("Try again") }
                }
                is Load.Ready -> ListBody(
                    list, state.value, open, saves, hidden,
                    onSave = { save(it, list == DiscoveryList.Saved) },
                    onDismiss = ::dismiss,
                    onEdgeSwipe = ::switchBy,
                    onRefresh = {
                        scope.launch {
                            statusLine = try {
                                withContext(Dispatchers.IO) { list.takeIf { it != DiscoveryList.Saved && it != DiscoveryList.Daily }?.let { repo.refreshList(it.path) } }
                                delay(3000)
                                loaded.reload()
                                "Rebuilding this list. Pull it again in a moment if it is still empty."
                            } catch (e: Exception) {
                                e.message ?: "The list could not be rebuilt."
                            }
                        }
                    },
                )
            }
        }
    }
}

/** One swipeable page of a list: a tab title (null when the list has no tabs) and the cards on it. */
private data class CardPage(val title: String?, val entries: List<DiscoveryEntry>, val empty: String)

private fun pagesFor(list: DiscoveryList, sections: List<Section>, hidden: Map<String, Boolean>): List<CardPage> {
    fun visible(s: Section) = s.result?.entries.orEmpty().distinctBy { it.key }.filter { hidden[it.key] != true }
    return when (list) {
        // Each lens list is its own tab, in the server's order.
        DiscoveryList.Daily -> sections.map {
            CardPage(
                it.title, visible(it),
                it.error?.let { e -> "${it.title} could not be loaded: $e" }
                    ?: if (it.result?.disabled == true) "Daily picks are turned off in Settings." else it.result?.message ?: "No albums today.",
            )
        }
        // The server groups deep dives by genre row; each group is a tab.
        DiscoveryList.DeepDive -> {
            val rows = sections.flatMap { visible(it) }
            val groups = rows.groupBy { it.item.genreRowLabel ?: "" }
            if (groups.keys.all { it.isEmpty() }) listOf(CardPage(null, rows, list.empty))
            else groups.map { (label, entries) -> CardPage(label.ifEmpty { "More" }, entries, list.empty) }
        }
        else -> listOf(CardPage(null, sections.flatMap { visible(it) }, list.empty))
    }
}

@Composable
private fun ListBody(
    list: DiscoveryList,
    sections: List<Section>,
    open: Opener,
    saves: Map<String, SaveState>,
    hidden: Map<String, Boolean>,
    onSave: (DiscoveryEntry) -> Unit,
    onDismiss: (DiscoveryEntry, Boolean) -> Unit,
    onEdgeSwipe: (Int) -> Unit,
    onRefresh: () -> Unit,
) {
    val pages = pagesFor(list, sections, hidden)
    val first = sections.firstOrNull()?.result
    // A single plain list says why it is empty, and offers to build it; tabbed lists say it per tab.
    val emptyNote: @Composable () -> Unit = {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(
                when {
                    first?.disabled == true -> "Daily picks are turned off in Settings."
                    else -> first?.message ?: sections.firstNotNullOfOrNull { it.error } ?: list.empty
                },
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (list != DiscoveryList.Saved && list != DiscoveryList.Daily) {
                OutlinedButton(onClick = onRefresh, Modifier.heightIn(min = Target)) { Text("Build this list") }
            }
        }
    }
    val cards: @Composable (CardPage) -> Unit = { page ->
        if (page.entries.isEmpty()) {
            if (page.title == null) emptyNote()
            else Text(page.empty, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(16.dp))
        } else CardGrid(list, page.entries, open, saves, onSave, onDismiss)
    }
    if (pages.size == 1) {
        cards(pages.single())
        return
    }
    key(list) {
        val pager = rememberPagerState { pages.size }
        val scope = rememberCoroutineScope()
        Column(Modifier.fillMaxSize()) {
            val titles = pages.map { it.title.orEmpty() }
            val pick: (Int) -> Unit = { scope.launch { pager.animateScrollToPage(it) } }
            EditorTabs(titles, pager.currentPage, pick)
            // Swipe left over the last page, or right over the first, is what the pager could not use: it moves to
            // the next or previous main tab. The distance is added up over the drag and decided when the finger lifts.
            val threshold = with(androidx.compose.ui.platform.LocalDensity.current) { 72.dp.toPx() }
            val edge = remember(pager, threshold) {
                object : NestedScrollConnection {
                    var overflow = 0f
                    override fun onPostScroll(consumed: Offset, available: Offset, source: NestedScrollSource): Offset {
                        if (source == NestedScrollSource.UserInput) overflow += available.x
                        return Offset.Zero
                    }
                    override suspend fun onPreFling(available: Velocity): Velocity {
                        val total = overflow
                        overflow = 0f
                        if (total < -threshold) onEdgeSwipe(1) else if (total > threshold) onEdgeSwipe(-1)
                        return Velocity.Zero
                    }
                }
            }
            HorizontalPager(pager, Modifier.weight(1f).fillMaxWidth().nestedScroll(edge), key = { pages[it].title ?: it }) { index ->
                cards(pages[index])
            }
        }
    }
}

/** Two cards to a row. */
@Composable
private fun CardGrid(
    list: DiscoveryList,
    entries: List<DiscoveryEntry>,
    open: Opener,
    saves: Map<String, SaveState>,
    onSave: (DiscoveryEntry) -> Unit,
    onDismiss: (DiscoveryEntry, Boolean) -> Unit,
) {
    LazyVerticalGrid(
        GridCells.Fixed(2), Modifier.fillMaxSize(),
        contentPadding = PaddingValues(12.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        gridItems(entries, key = { it.key }) { entry ->
            DiscoverCard(
                entry, open,
                saveState = saves[entry.key] ?: if (list == DiscoveryList.Saved) SaveState.Saved else SaveState.Idle,
                onSave = { onSave(entry) },
                onDismiss = { artistToo -> onDismiss(entry, artistToo) },
            )
        }
    }
}
