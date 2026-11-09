package app.discair.ui.artist

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewmodel.compose.viewModel
import app.discair.model.PathAlbum
import app.discair.model.PathKind
import app.discair.model.PathLink
import app.discair.model.PathStop
import app.discair.model.PathsResponse
import app.discair.model.PathsView
import app.discair.model.heading
import app.discair.model.pane
import app.discair.model.pathsFailure
import app.discair.model.sentence
import app.discair.model.view
import app.discair.ui.Opener
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.ArtistPhoto
import app.discair.ui.common.FilterChip
import app.discair.ui.common.Load
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.ModalBottomSheet
import app.discair.ui.common.OutlinedButton
import app.discair.ui.common.OutlinedIconButton
import app.discair.ui.common.RowDivider
import app.discair.ui.common.Target
import app.discair.ui.common.routeKey
import app.discair.ui.player.PlayerIcons
import app.discair.ui.theme.Ink
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** The sheet's height as a share of the window: tall enough for a pane and its bottom button without scrolling away the header. */
private const val SheetHeight = 0.92f

/**
 * The answers the paths sheet has read, kept with the artist's page on the back stack. Opening an album or artist from the
 * sheet leaves the page, and Back returns to it: the sheet comes back with its answers, so nothing is asked again.
 */
class PathsModel : ViewModel() {
    val answers = mutableStateMapOf<PathKind, Load<PathsResponse>>()
}

/**
 * The paths view, opened from the artist page: pick one of the five kinds, see the server's path as a list, and open a step to
 * read it in its own pane. The server is asked only when the sheet is open and a kind is chosen; nothing is saved on the phone.
 *
 * Opening an album or artist closes the sheet's window but not its state (the kind, the open step and each list's scroll are
 * saved with the page), so Back and the swipe back return to the sheet at the same step, not to the page it belongs to.
 * Only the sheet's own close (drag down, tap outside) goes to the artist page.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ArtistPathsSheet(artistName: String, mbid: String, open: Opener, onDismiss: () -> Unit) {
    val repo = LocalRepository.current
    val model = viewModel<PathsModel>(key = "paths:$mbid")
    var kindWire by rememberSaveable { mutableStateOf(PathKind.FollowTheMusician.wire) }
    var step by rememberSaveable { mutableIntStateOf(-1) }
    var attempt by remember { mutableIntStateOf(0) }
    // True from the tap that leaves for another page: the sheet's window goes at once instead of riding over the next page.
    var away by remember { mutableStateOf(false) }
    val kind = PathKind.entries.firstOrNull { it.wire == kindWire } ?: PathKind.FollowTheMusician
    val lists = PathKind.entries.associateWith { rememberLazyListState() }

    LaunchedEffect(kind, mbid, attempt) {
        if (model.answers[kind] is Load.Ready) return@LaunchedEffect
        model.answers[kind] = Load.Loading
        model.answers[kind] = withContext(Dispatchers.IO) {
            try {
                Load.Ready(repo.paths(kind, mbid))
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                Load.Failed(pathsFailure(e))
            }
        }
    }

    if (away) return
    val go: (PathLink) -> Unit = { link -> away = true; link.go(open) }
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
    ) {
        val state = model.answers[kind] ?: Load.Loading
        val response = (state as? Load.Ready)?.value
        val stops = (response?.view() as? PathsView.Stops)?.response?.stops.orEmpty()
        // Back from a pane goes to the list first; Back from the list closes the sheet.
        BackHandler(enabled = step in stops.indices) { step = -1 }
        Box(Modifier.fillMaxWidth().fillMaxHeight(SheetHeight)) {
            if (step in stops.indices) {
                PathDetail(
                    artistName, kind, stops, step,
                    onBack = { step = -1 }, onStep = { step = it }, go = go,
                )
            } else {
                PathList(
                    artistName, kind, state, lists.getValue(kind),
                    onKind = { step = -1; kindWire = it.wire },
                    onStep = { step = it }, onRetry = { attempt++ },
                )
            }
        }
    }
}

private fun PathLink.go(open: Opener) {
    if (album) open.album(routeKey(by.orEmpty(), name), by.orEmpty(), name, null, null) else open.artist(name, null, null, mbid)
}

// ---------------------------------------------------------------- the list

@Composable
private fun PathList(
    artistName: String, kind: PathKind, state: Load<PathsResponse>, list: LazyListState,
    onKind: (PathKind) -> Unit, onStep: (Int) -> Unit, onRetry: () -> Unit,
) {
    Column(Modifier.fillMaxSize().padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            "Paths from $artistName",
            style = MaterialTheme.typography.titleLarge,
            modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp).semantics { heading() },
        )
        LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            items(PathKind.entries, key = { it.wire }) { option ->
                FilterChip(
                    selected = option == kind,
                    onClick = { onKind(option) },
                    label = { Text(option.label) },
                    modifier = Modifier.heightIn(min = Target),
                )
            }
        }
        Text(
            kindDescription(kind, artistName, (state as? Load.Ready)?.value?.startType.orEmpty()),
            style = MaterialTheme.typography.bodyMedium,
            color = Ink.TextMuted,
            modifier = Modifier.fillMaxWidth(),
        )
        Box(Modifier.fillMaxWidth().weight(1f)) {
            when (state) {
                Load.Loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(Modifier.semantics { contentDescription = "Loading paths" })
                }
                is Load.Failed -> Column(Modifier.fillMaxSize(), verticalArrangement = Arrangement.Center) {
                    Text(state.failure.message, style = MaterialTheme.typography.bodyLarge, color = Ink.ChartRedText)
                    Spacer(Modifier.size(16.dp))
                    OutlinedButton(onClick = onRetry, Modifier.heightIn(min = Target)) { Text("Try again") }
                }
                is Load.Ready -> when (val view = state.value.view()) {
                    is PathsView.Stops -> LazyColumn(Modifier.fillMaxSize(), state = list, contentPadding = PaddingValues(bottom = 32.dp)) {
                        itemsIndexed(view.response.stops) { index, stop ->
                            PathRow(index + 1, kind, stop) { onStep(index) }
                            RowDivider()
                        }
                        state.value.truncated?.let { reason ->
                            item {
                                Text(
                                    "The server stopped this path early (${truncatedWords(reason)}), so later steps may be missing.",
                                    style = MaterialTheme.typography.bodySmall, color = Ink.TextMuted,
                                    modifier = Modifier.padding(top = 16.dp),
                                )
                            }
                        }
                    }
                    PathsView.Empty -> Text(
                        "No ${kind.label.lowercase()} path from $artistName yet. A path appears only when every step has evidence.",
                        style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted,
                    )
                }
            }
        }
    }
}

/** One step of the list: its number, a picture, the main name with one line of detail, and a chevron. One tap opens its pane. */
@Composable
private fun PathRow(number: Int, kind: PathKind, stop: PathStop, onClick: () -> Unit) {
    val heading = stop.heading(kind)
    val detail = rowDetail(kind, stop)
    Row(
        Modifier.fillMaxWidth().heightIn(min = 64.dp)
            .clickable(onClickLabel = "Open step $number", role = Role.Button, onClick = onClick)
            .padding(vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(16.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            "$number", style = MaterialTheme.typography.labelLarge, color = Ink.TextMuted,
            textAlign = TextAlign.End, modifier = Modifier.width(24.dp),
        )
        PathThumb(kind, stop, 48)
        Column(Modifier.weight(1f)) {
            Text(heading.title, style = MaterialTheme.typography.titleMedium, maxLines = 2, overflow = TextOverflow.Ellipsis)
            Text(detail, style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted, maxLines = 2, overflow = TextOverflow.Ellipsis)
        }
        Icon(PlayerIcons.Right, contentDescription = null, modifier = Modifier.size(24.dp))
    }
}

/** The second line of a row, per kind: what the server sent for it, and the first reason when it sent nothing better. */
internal fun rowDetail(kind: PathKind, stop: PathStop): String {
    val firstReason = stop.reasons.firstOrNull()
    val line = when (kind) {
        PathKind.FollowTheMusician -> listOfNotNull(stop.album, stop.albumArtist).joinToString(" · ")
        PathKind.SidemanToLeader -> firstReason?.via?.takeIf { it.type == "release" }?.let { "Led ${it.name}" }.orEmpty()
        PathKind.LabelPath -> stop.albumArtist ?: stop.displayContext.orEmpty()
        PathKind.CompositionPath -> stop.heading(kind).detail.orEmpty()
        PathKind.ScenePath -> firstReason?.via?.name?.let { "From $it" }.orEmpty()
    }
    return line.ifBlank { firstReason?.sentence() ?: stop.reason }
}

/** The picture beside a step: the album cover or the artist's photo where the step has one to look up, else a plain tile. */
@Composable
internal fun PathThumb(kind: PathKind, stop: PathStop, size: Int) {
    val modifier = Modifier.size(size.dp)
    when (kind) {
        PathKind.FollowTheMusician -> {
            val covers = stop.albums.ifEmpty { if (stop.album != null && stop.albumArtist != null) listOf(PathAlbum(stop.album, stop.albumArtist)) else emptyList() }
            CandidateCover(covers, modifier) { PathTile(PlayerIcons.MusicNote, size) }
        }
        PathKind.LabelPath -> {
            if (stop.albumArtist != null) AlbumCover(stop.albumArtist, stop.name, null, modifier) else PathTile(PlayerIcons.Album, size)
        }
        PathKind.SidemanToLeader, PathKind.ScenePath -> ArtistPhoto(stop.name, null, modifier, circle = true)
        PathKind.CompositionPath -> {
            // A recording's cover is its album's, when the server named the album.
            val by = stop.albumArtist ?: stop.artist
            if (stop.album != null && by != null) AlbumCover(by, stop.album, null, modifier) else PathTile(PlayerIcons.MusicNote, size)
        }
    }
}

private fun kindDescription(kind: PathKind, artist: String, startType: String) = when (kind) {
    PathKind.FollowTheMusician -> "Songs, not in your library, by musicians who also played with $artist."
    PathKind.SidemanToLeader -> when (startType) {
        "group" -> "Artists whose records $artist appeared on as guests."
        "person" -> "Artists whose records $artist played on as a sideman."
        else -> "Artists whose records $artist played on as a guest."
    }
    PathKind.LabelPath -> "Albums released on the same labels as $artist's records."
    PathKind.CompositionPath -> "Other recordings of the same compositions as $artist's, covers and live versions included."
    PathKind.ScenePath -> "Artists from the same place and era as $artist."
}

private fun truncatedWords(reason: String) = when (reason) {
    "rows" -> "row limit"
    "time" -> "time limit"
    "stops" -> "stop limit"
    else -> "limit"
}

// ---------------------------------------------------------------- the pane

/**
 * A step's pane. The top has only the way back to the list; the bottom, below a line, has the path and step on the left and
 * the arrows to the previous and next step on the right. The pane's own pictures open the pages.
 */
@Composable
private fun PathDetail(
    artistName: String, kind: PathKind, stops: List<PathStop>, index: Int,
    onBack: () -> Unit, onStep: (Int) -> Unit, go: (PathLink) -> Unit,
) {
    val stop = stops[index]
    // Each time a step opens, the pane picks again among the reasons the server sent.
    val pane = remember(stop, kind) { stop.pane(kind, artistName) }
    Column(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp, bottom = 16.dp)) {
            OutlinedIconButton(onClick = onBack, Modifier.size(Target)) {
                Icon(PlayerIcons.Left, contentDescription = "Back to the list")
            }
        }
        // A new step starts at the top of its pane.
        key(index) {
            Column(
                Modifier.weight(1f).fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                PaneBody(pane, stop, artistName, go)
                Spacer(Modifier.size(8.dp))
            }
        }
        Box(Modifier.fillMaxWidth().height(2.dp).background(Ink.EdgeStrong))
        Row(
            Modifier.fillMaxWidth().padding(start = 16.dp, end = 8.dp, top = 8.dp, bottom = 24.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(kind.label, style = MaterialTheme.typography.titleMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text("Step ${index + 1} of ${stops.size}", style = MaterialTheme.typography.bodySmall, color = Ink.TextMuted)
            }
            IconButton(onClick = { onStep(index - 1) }, Modifier.size(Target), enabled = index > 0) {
                Icon(Icons.Default.KeyboardArrowUp, contentDescription = "Previous step")
            }
            IconButton(onClick = { onStep(index + 1) }, Modifier.size(Target), enabled = index < stops.lastIndex) {
                Icon(Icons.Default.KeyboardArrowDown, contentDescription = "Next step")
            }
        }
    }
}
