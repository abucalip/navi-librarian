package app.discair.ui.artist

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewmodel.compose.viewModel
import app.discair.model.PathAlbum
import app.discair.model.PathKind
import app.discair.model.PathLink
import app.discair.model.PathPane
import app.discair.model.PathStop
import app.discair.model.PathsResponse
import app.discair.model.PathsView
import app.discair.model.heading
import app.discair.model.pane
import app.discair.model.pathsFailure
import app.discair.model.sentence
import app.discair.model.groupByLink
import app.discair.model.trailLink
import app.discair.model.view
import app.discair.ui.Opener
import app.discair.ui.common.PathRowCover
import app.discair.ui.common.ArtistPhoto
import app.discair.ui.common.TrailHeader
import app.discair.ui.common.TrailList
import app.discair.ui.common.TrailOpenStep
import app.discair.ui.common.TrailSizes
import app.discair.ui.common.TrailStepRow
import app.discair.ui.common.TrailTabs
import app.discair.ui.common.Load
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.ModalBottomSheet
import app.discair.ui.common.OutlinedButton
import app.discair.ui.common.Target
import app.discair.ui.common.routeKey
import app.discair.ui.player.PlayerIcons
import app.discair.ui.theme.Ink
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

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
        // Back with a step open closes the step; Back with none open closes the sheet.
        BackHandler(enabled = step in stops.indices) { step = -1 }
        Box(Modifier.fillMaxWidth().weight(1f)) { // the sheet height left after its handle; a fixed fraction overflowed the Soft Brut outline
            PathList(
                artistName, mbid, kind, state, step, lists.getValue(kind), go,
                onKind = { step = -1; kindWire = it.wire },
                onStep = { step = it }, onRetry = { attempt++ },
            )
        }
    }
}

private fun PathLink.go(open: Opener) {
    if (album) open.album(routeKey(by.orEmpty(), name), by.orEmpty(), name, null, null) else open.artist(name, null, null, mbid)
}

// ---------------------------------------------------------------- the trail

@Composable
private fun PathList(
    artistName: String, mbid: String, kind: PathKind, state: Load<PathsResponse>, step: Int, list: LazyListState, go: (PathLink) -> Unit,
    onKind: (PathKind) -> Unit, onStep: (Int) -> Unit, onRetry: () -> Unit,
) {
    Column(Modifier.fillMaxSize()) {
        TrailHeader(artistName, { ArtistPhoto(artistName, null, Modifier.size(TrailSizes.HeaderPicture), circle = true) }, Modifier.padding(horizontal = 16.dp))
        TrailTabs(PathKind.entries.map { it.label }, PathKind.entries.indexOf(kind), { onKind(PathKind.entries[it]) })
        Text(
            kindDescription(kind, artistName, (state as? Load.Ready)?.value?.startType.orEmpty()),
            style = MaterialTheme.typography.bodyMedium,
            color = Ink.TextMuted,
            modifier = Modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 8.dp),
        )
        Box(Modifier.fillMaxWidth().weight(1f)) {
            when (state) {
                Load.Loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(Modifier.semantics { contentDescription = "Loading paths" })
                }
                is Load.Failed -> Column(Modifier.fillMaxSize().padding(horizontal = 16.dp), verticalArrangement = Arrangement.Center) {
                    Text(state.failure.message, style = MaterialTheme.typography.bodyLarge, color = Ink.ChartRedText)
                    Spacer(Modifier.size(16.dp))
                    OutlinedButton(onClick = onRetry, Modifier.heightIn(min = Target)) { Text("Try again") }
                    if ((state.failure as? app.discair.net.ConnectionFailure.Server)?.code == 404) {
                        Spacer(Modifier.size(8.dp))
                        app.discair.ui.common.RequestUpdateButton("artist", mbid, byMbid = true, onDone = onRetry)
                    }
                }
                is Load.Ready -> when (val view = state.value.view()) {
                    is PathsView.Stops -> {
                        // The link of each step is built from its first reason, so the trail is stable; steps that share a link sit under it.
                        val groups = remember(view, kind, artistName) { groupByLink(view.response.stops) { it.trailLink(kind, artistName) } }
                        val notes = state.value.truncated?.let { listOf("The server stopped this path early (${truncatedWords(it)}), so later steps may be missing.") }.orEmpty()
                        TrailList(groups, step, list, notes) { entry, open ->
                            PathStep(kind, entry.item, artistName, open, go, onOpen = { onStep(entry.index) }, onClose = { onStep(-1) })
                        }
                    }
                    PathsView.Empty -> Text(
                        "No ${kind.label.lowercase()} path from $artistName yet. A path appears only when every step has evidence.",
                        style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted, modifier = Modifier.padding(horizontal = 16.dp),
                    )
                }
            }
        }
    }
}

/**
 * One step of the trail: closed, a row that opens it in place; open, the step's pane under a header row. The cover turned by a
 * long press (also a TalkBack action, when the album has more than one) is kept across closing and opening.
 */
@Composable
private fun PathStep(kind: PathKind, stop: PathStop, startName: String, open: Boolean, go: (PathLink) -> Unit, onOpen: () -> Unit, onClose: () -> Unit) {
    var cover by remember { mutableIntStateOf(0) }
    if (!open) {
        TrailStepRow(
            title = stop.heading(kind).title, line = rowDetail(kind, stop),
            picture = { PathThumb(kind, stop, 48, cover) }, onOpen = onOpen, onShowNextCover = { cover++ },
        )
        return
    }
    // Each time a step opens, the pane picks again among the reasons the server sent.
    val pane = remember(stop, kind) { stop.pane(kind, startName) }
    val library = if (stop.owned) "In your library" else "Not in your library"
    val heading = stop.heading(kind)
    val (title, lines) = when (pane) {
        is PathPane.Song -> pane.title to listOfNotNull(pane.album?.let { "on $it" }, pane.artist?.let { "by $it" }, library)
        is PathPane.Leader -> pane.name to listOf(pane.typeLabel, library)
        is PathPane.LabelAlbum -> pane.album to listOfNotNull(pane.artist, library)
        is PathPane.Recording -> heading.title to listOfNotNull(heading.detail)
        is PathPane.Place -> pane.name to listOf(pane.typeLabel, library)
    }
    TrailOpenStep(
        title = title, lines = lines, picture = { PathThumb(kind, stop, TrailSizes.OpenPicture.value.toInt(), cover) }, onClose = onClose,
        // Sideman: the picture and the name open the leader's page, and only the chevron closes the step.
        onOpenTitle = (pane as? PathPane.Leader)?.let { leader -> { go(PathLink(false, leader.name, null, leader.mbid)) } },
    ) { PaneBody(pane, stop, startName, go) }
}

/** The second line of a row, per kind: what the server sent for it, and the first reason when it sent nothing better. */
internal fun rowDetail(kind: PathKind, stop: PathStop): String {
    val firstReason = stop.reasons.firstOrNull()
    val line = when (kind) {
        PathKind.FollowTheMusician -> listOfNotNull(stop.album, stop.albumArtist).joinToString(" · ")
        // The record and the place are the link above the row, so the line says the library state instead of repeating them.
        PathKind.SidemanToLeader, PathKind.ScenePath -> if (stop.owned) "In your library" else "Not in your library"
        PathKind.LabelPath -> stop.albumArtist ?: stop.displayContext.orEmpty()
        PathKind.CompositionPath -> stop.heading(kind).detail.orEmpty()
    }
    return line.ifBlank { firstReason?.sentence() ?: stop.reason }
}

/** The picture beside a step: the album cover or the artist's photo where the step has one to look up, else a plain tile. */
@Composable
internal fun PathThumb(kind: PathKind, stop: PathStop, size: Int, cover: Int = 0) {
    val modifier = Modifier.size(size.dp)
    when (kind) {
        PathKind.FollowTheMusician -> {
            val covers = stop.albums.ifEmpty { if (stop.album != null && stop.albumArtist != null) listOf(PathAlbum(stop.album, stop.albumArtist)) else emptyList() }
            val first = covers.firstOrNull()
            if (cover > 0 && first != null) PathRowCover(first.artist, first.album, cover, modifier)
            else CandidateCover(covers, modifier) { PathTile(PlayerIcons.MusicNote, size) }
        }
        PathKind.LabelPath -> {
            if (stop.albumArtist != null) PathRowCover(stop.albumArtist, stop.name, cover, modifier) else PathTile(PlayerIcons.Album, size)
        }
        PathKind.SidemanToLeader, PathKind.ScenePath -> ArtistPhoto(stop.name, null, modifier, circle = true)
        PathKind.CompositionPath -> {
            // A recording's cover is its album's, when the server named the album.
            val by = stop.albumArtist ?: stop.artist
            if (stop.album != null && by != null) PathRowCover(by, stop.album, cover, modifier) else PathTile(PlayerIcons.MusicNote, size)
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
