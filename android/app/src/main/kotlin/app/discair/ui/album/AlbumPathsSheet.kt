package app.discair.ui.album

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
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
import app.discair.model.AlbumAnswer
import app.discair.model.AlbumStep
import app.discair.model.AlbumStepReason
import app.discair.model.AlbumTab
import app.discair.model.PathAlbum
import app.discair.model.PathLink
import app.discair.model.albumPathsEmpty
import app.discair.model.albumPathsFailure
import app.discair.model.albumTabDescription
import app.discair.model.albumTabs
import app.discair.model.groupByLink
import app.discair.model.trailLink
import app.discair.model.isArtist
import app.discair.model.reasonEyebrow
import app.discair.model.toAlbumAnswer
import app.discair.model.yearGap
import app.discair.ui.Opener
import app.discair.ui.artist.Eyebrow
import app.discair.ui.artist.FindRow
import app.discair.ui.artist.InfoCard
import app.discair.ui.artist.LibraryLine
import app.discair.ui.common.PathAlbumCover
import app.discair.ui.common.PathRowCover
import app.discair.ui.common.SameRoomPhotos
import app.discair.ui.common.TrailHeader
import app.discair.ui.common.TrailList
import app.discair.ui.common.TrailOpenStep
import app.discair.ui.common.TrailSizes
import app.discair.ui.common.TrailStepRow
import app.discair.ui.common.TrailTabs
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.draw.clip
import app.discair.ui.common.Load
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.ModalBottomSheet
import app.discair.ui.common.OutlinedButton
import app.discair.ui.common.Target
import app.discair.ui.common.routeKey
import app.discair.ui.theme.Ink
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** Reasons a pane lists; the rest are counted by the server, not aloud. */
private const val PaneReasons = 3

/** The answers the album sheet has read, kept with the album page on the back stack so Back from an opened album finds them. */
class AlbumPathsModel : ViewModel() {
    val answers = mutableStateMapOf<AlbumTab, Load<AlbumAnswer>>()
}

/**
 * The paths view of an album page, built like the artist's sheet: pick a path, see its owned albums as a list, open a step
 * in its own pane. Neighbours by ear is offered only when the server reports sonic similarity. The server is asked only when
 * the sheet is open and a tab is chosen; nothing is saved on the phone.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AlbumPathsSheet(albumName: String, artistName: String, albumId: String, sonicAvailable: Boolean, open: Opener, onDismiss: () -> Unit) {
    val repo = LocalRepository.current
    val model = viewModel<AlbumPathsModel>(key = "album-paths:$albumId")
    val tabs = albumTabs(sonicAvailable)
    var tabName by rememberSaveable { mutableStateOf(AlbumTab.StudioCrew.name) }
    var step by rememberSaveable { mutableIntStateOf(-1) }
    var attempt by remember { mutableIntStateOf(0) }
    var away by remember { mutableStateOf(false) }
    val tab = tabs.firstOrNull { it.name == tabName } ?: tabs.first()
    val lists = AlbumTab.entries.associateWith { rememberLazyListState() }

    LaunchedEffect(tab, albumId, attempt) {
        if (model.answers[tab] is Load.Ready) return@LaunchedEffect
        model.answers[tab] = Load.Loading
        model.answers[tab] = withContext(Dispatchers.IO) {
            try {
                Load.Ready(
                    tab.graph?.let { repo.albumPaths(it, albumId).toAlbumAnswer() } ?: repo.sonicAlbumNeighbours(albumId).toAlbumAnswer(),
                )
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                Load.Failed(albumPathsFailure(e))
            }
        }
    }

    if (away) return
    val go: (PathLink) -> Unit = { link ->
        away = true
        if (link.album) open.album(routeKey(link.by.orEmpty(), link.name), link.by.orEmpty(), link.name, null, null)
        else open.artist(link.name, null, null, link.mbid)
    }
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
        val state = model.answers[tab] ?: Load.Loading
        val steps = (state as? Load.Ready)?.value?.steps.orEmpty()
        // Back with a step open closes the step; Back with none open closes the sheet.
        BackHandler(enabled = step in steps.indices) { step = -1 }
        Box(Modifier.fillMaxWidth().weight(1f)) { // the sheet height left after its handle; a fixed fraction overflowed the Soft Brut outline
            val seeds = (model.answers[AlbumTab.NeighboursByEar] as? Load.Ready)?.value?.seeds ?: 0
            AlbumPathList(
                albumName, artistName, albumId, tab, tabs, state, seeds, step, lists.getValue(tab), go,
                onTab = { step = -1; tabName = it.name }, onStep = { step = it }, onRetry = { attempt++ },
            )
        }
    }
}

// ---------------------------------------------------------------- the trail

@Composable
private fun AlbumPathList(
    albumName: String, artistName: String, albumId: String, tab: AlbumTab, tabs: List<AlbumTab>, state: Load<AlbumAnswer>, seeds: Int,
    step: Int, list: LazyListState, go: (PathLink) -> Unit,
    onTab: (AlbumTab) -> Unit, onStep: (Int) -> Unit, onRetry: () -> Unit,
) {
    Column(Modifier.fillMaxSize()) {
        TrailHeader(albumName, { PathAlbumCover(artistName, albumName, Modifier.size(TrailSizes.HeaderPicture).clip(RoundedCornerShape(4.dp))) }, Modifier.padding(horizontal = 16.dp))
        TrailTabs(tabs.map { it.label }, tabs.indexOf(tab), { onTab(tabs[it]) })
        Text(
            albumTabDescription(tab, albumName, seeds), style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted,
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
                        app.discair.ui.common.RequestUpdateButton("album", albumId, byMbid = false, onDone = onRetry)
                    }
                }
                is Load.Ready -> {
                    val answer = state.value
                    if (answer.steps.isEmpty()) {
                        Text(
                            answer.empty ?: albumPathsEmpty(tab, albumName), style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted,
                            modifier = Modifier.padding(horizontal = 16.dp),
                        )
                    } else {
                        // The link of each step is built from its first reason, so the trail is stable; steps that share a link sit under it.
                        val groups = remember(answer, tab) { groupByLink(answer.steps) { it.trailLink(tab, answer.seeds) } }
                        TrailList(groups, step, list, answer.notes) { entry, open ->
                            AlbumStepItem(tab, entry.item, albumName, artistName, open, go, onOpen = { onStep(entry.index) }, onClose = { onStep(-1) })
                        }
                    }
                }
            }
        }
    }
}

/**
 * One step of the trail: closed, the album's row, which opens it in place; open, the album's pane under a header row. A long press
 * (also offered to TalkBack as "Show next cover") turns the cover to the album's next alternate cover, when it has more than one.
 */
@Composable
private fun AlbumStepItem(
    tab: AlbumTab, step: AlbumStep, startName: String, startArtist: String, open: Boolean, go: (PathLink) -> Unit,
    onOpen: () -> Unit, onClose: () -> Unit,
) {
    var cover by remember { mutableIntStateOf(0) }
    if (!open) {
        TrailStepRow(
            title = step.album, line = step.detail, picture = { PathRowCover(step.artist, step.album, cover, Modifier.size(TrailSizes.StepPicture)) },
            onOpen = onOpen, onShowNextCover = { cover++ },
        )
        return
    }
    TrailOpenStep(
        title = step.album, lines = listOfNotNull(step.artist.takeIf { it.isNotBlank() }, step.year?.toString(), "In your library"),
        picture = { PathRowCover(step.artist, step.album, cover, Modifier.size(TrailSizes.OpenPicture)) }, onClose = onClose,
    ) { AlbumPaneBody(tab, step, startName, startArtist, go) }
}

/**
 * The body of an opened step: a card per reason the server sent (the first three), and the person and album to open; the album
 * itself is the step's header row (every step is in the library). The cards sit on the sheet's ground, against the raised panel. The sentence is the server's own; a fact it did not send is left out.
 */
@Composable
private fun AlbumPaneBody(tab: AlbumTab, step: AlbumStep, startName: String, startArtist: String, go: (PathLink) -> Unit) {
    step.play?.let { play ->
        InfoCard() {
            Eyebrow("Your listening")
            Spacer(Modifier.size(8.dp))
            Text(play, style = MaterialTheme.typography.titleLarge)
        }
    }
    if (tab == AlbumTab.SameRoom) SameRoomPhotos(startArtist, startName, step.artist, step.album)
    val reasons = step.reasons.take(PaneReasons)
    reasons.forEach { ReasonCard(tab, it) }
    if (reasons.isEmpty()) InfoCard { Text("In your library.", style = MaterialTheme.typography.bodyMedium) }
    val person = step.reasons.firstNotNullOfOrNull { it.via?.takeIf { v -> v.isArtist } }
    FindRow(
        person = person?.let { it.name to PathLink(false, it.name, null, it.mbid) },
        album = step.artist.takeIf { it.isNotBlank() }?.let { by -> Triple(step.album, PathLink(true, step.album, by), listOf(PathAlbum(step.album, by))) },
        go = go,
    )
}

/** One reason: what kind of link it is and who or what it goes through, then the server's sentence. */
@Composable
private fun ReasonCard(tab: AlbumTab, reason: AlbumStepReason) {
    val via = reason.via?.name
    if (tab == AlbumTab.SameYearSameScene && via != null) {
        // The link and the period side by side, as Same place and Same era on a scene pane.
        val gap = yearGap(reason.text)
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            InfoCard(Modifier.weight(1f)) {
                Eyebrow(reasonEyebrow(reason.code))
                Spacer(Modifier.size(8.dp))
                Text(via, style = MaterialTheme.typography.titleLarge)
            }
            if (gap != null) InfoCard(Modifier.weight(1f)) {
                Eyebrow("Same period")
                Spacer(Modifier.size(8.dp))
                Text(gap, style = MaterialTheme.typography.titleLarge)
            }
        }
        Text(reason.text, style = MaterialTheme.typography.bodyLarge)
        return
    }
    InfoCard() {
        Eyebrow(reasonEyebrow(reason.code))
        if (via != null) {
            Spacer(Modifier.size(8.dp))
            Text(via, style = MaterialTheme.typography.titleLarge)
        }
    }
    Text(reason.text, style = MaterialTheme.typography.bodyLarge)
}
