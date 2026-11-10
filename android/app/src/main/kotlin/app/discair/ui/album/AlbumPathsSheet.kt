package app.discair.ui.album

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

/** The sheet's height as a share of the window, as the artist sheet. */
private const val SheetHeight = 0.92f

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
        BackHandler(enabled = step in steps.indices) { step = -1 }
        Box(Modifier.fillMaxWidth().fillMaxHeight(SheetHeight)) {
            if (step in steps.indices) {
                AlbumPathDetail(albumName, tab, steps, step, onBack = { step = -1 }, onStep = { step = it }, go = go)
            } else {
                val seeds = (model.answers[AlbumTab.NeighboursByEar] as? Load.Ready)?.value?.seeds ?: 0
                AlbumPathList(
                    albumName, tab, tabs, state, seeds, lists.getValue(tab),
                    onTab = { step = -1; tabName = it.name }, onStep = { step = it }, onRetry = { attempt++ },
                )
            }
        }
    }
}

// ---------------------------------------------------------------- the list

@Composable
private fun AlbumPathList(
    albumName: String, tab: AlbumTab, tabs: List<AlbumTab>, state: Load<AlbumAnswer>, seeds: Int, list: LazyListState,
    onTab: (AlbumTab) -> Unit, onStep: (Int) -> Unit, onRetry: () -> Unit,
) {
    Column(Modifier.fillMaxSize().padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            "Paths from $albumName", style = MaterialTheme.typography.titleLarge,
            modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp).semantics { heading() },
        )
        LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            items(tabs, key = { it.name }) { option ->
                FilterChip(selected = option == tab, onClick = { onTab(option) }, label = { Text(option.label) }, modifier = Modifier.heightIn(min = Target))
            }
        }
        Text(albumTabDescription(tab, albumName, seeds), style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted, modifier = Modifier.fillMaxWidth())
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
                is Load.Ready -> {
                    val answer = state.value
                    if (answer.steps.isEmpty()) {
                        Text(answer.empty ?: albumPathsEmpty(tab, albumName), style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted)
                    } else LazyColumn(Modifier.fillMaxSize(), state = list, contentPadding = PaddingValues(bottom = 32.dp)) {
                        itemsIndexed(answer.steps) { index, step ->
                            AlbumPathRow(index + 1, step) { onStep(index) }
                            RowDivider()
                        }
                        answer.notes.forEach { note ->
                            item {
                                Text(note, style = MaterialTheme.typography.bodySmall, color = Ink.TextMuted, modifier = Modifier.padding(top = 16.dp))
                            }
                        }
                    }
                }
            }
        }
    }
}

/** One step: its number, the album's cover, the album with one line of detail, and a chevron. One tap opens its pane. */
@Composable
private fun AlbumPathRow(number: Int, step: AlbumStep, onClick: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().heightIn(min = 64.dp)
            .clickable(onClickLabel = "Open step $number", role = Role.Button, onClick = onClick)
            .padding(vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(16.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text("$number", style = MaterialTheme.typography.labelLarge, color = Ink.TextMuted, textAlign = TextAlign.End, modifier = Modifier.width(24.dp))
        PathAlbumCover(step.artist, step.album, Modifier.size(48.dp))
        Column(Modifier.weight(1f)) {
            Text(step.album, style = MaterialTheme.typography.titleMedium, maxLines = 2, overflow = TextOverflow.Ellipsis)
            Text(step.detail, style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted, maxLines = 2, overflow = TextOverflow.Ellipsis)
        }
        Icon(PlayerIcons.Right, contentDescription = null, modifier = Modifier.size(24.dp))
    }
}

// ---------------------------------------------------------------- the pane

/** A step's pane: back to the list at the top, the path and step with the arrows at the bottom, as the artist sheet. */
@Composable
private fun AlbumPathDetail(
    startName: String, tab: AlbumTab, steps: List<AlbumStep>, index: Int,
    onBack: () -> Unit, onStep: (Int) -> Unit, go: (PathLink) -> Unit,
) {
    val step = steps[index]
    Column(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp, bottom = 16.dp)) {
            OutlinedIconButton(onClick = onBack, Modifier.size(Target)) { Icon(PlayerIcons.Left, contentDescription = "Back to the list") }
        }
        key(index) {
            Column(
                Modifier.weight(1f).fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                AlbumPaneBody(tab, step, startName, go)
                Spacer(Modifier.size(8.dp))
            }
        }
        Box(Modifier.fillMaxWidth().height(2.dp).background(Ink.EdgeStrong))
        Row(
            Modifier.fillMaxWidth().padding(start = 16.dp, end = 8.dp, top = 8.dp, bottom = 24.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(tab.label, style = MaterialTheme.typography.titleMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text("Step ${index + 1} of ${steps.size}", style = MaterialTheme.typography.bodySmall, color = Ink.TextMuted)
            }
            IconButton(onClick = { onStep(index - 1) }, Modifier.size(Target), enabled = index > 0) {
                Icon(Icons.Default.KeyboardArrowUp, contentDescription = "Previous step")
            }
            IconButton(onClick = { onStep(index + 1) }, Modifier.size(Target), enabled = index < steps.lastIndex) {
                Icon(Icons.Default.KeyboardArrowDown, contentDescription = "Next step")
            }
        }
    }
}

/**
 * One album and why it is here: the album as the hero (every step is in the library), a card per reason the server sent
 * (the first three), and the person and album to open. The sentence is the server's own; a fact it did not send is left out.
 */
@Composable
private fun AlbumPaneBody(tab: AlbumTab, step: AlbumStep, startName: String, go: (PathLink) -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.Bottom) {
        PathAlbumCover(step.artist, step.album, Modifier.size(144.dp))
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(step.album, style = MaterialTheme.typography.titleLarge, modifier = Modifier.semantics { heading() })
            if (step.artist.isNotBlank()) Text(step.artist, style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted)
            step.year?.let { Text("$it", style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted) }
            LibraryLine(true)
        }
    }
    step.play?.let { play ->
        InfoCard(raised = true) {
            Eyebrow("Your listening")
            Spacer(Modifier.size(8.dp))
            Text(play, style = MaterialTheme.typography.titleLarge)
        }
    }
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
            InfoCard(Modifier.weight(1f), raised = true) {
                Eyebrow(reasonEyebrow(reason.code))
                Spacer(Modifier.size(8.dp))
                Text(via, style = MaterialTheme.typography.titleLarge)
            }
            if (gap != null) InfoCard(Modifier.weight(1f), raised = true) {
                Eyebrow("Same period")
                Spacer(Modifier.size(8.dp))
                Text(gap, style = MaterialTheme.typography.titleLarge)
            }
        }
        Text(reason.text, style = MaterialTheme.typography.bodyLarge)
        return
    }
    InfoCard(raised = true) {
        Eyebrow(reasonEyebrow(reason.code))
        if (via != null) {
            Spacer(Modifier.size(8.dp))
            Text(via, style = MaterialTheme.typography.titleLarge)
        }
    }
    Text(reason.text, style = MaterialTheme.typography.bodyLarge)
}
