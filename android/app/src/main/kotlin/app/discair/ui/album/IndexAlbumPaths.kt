package app.discair.ui.album

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.model.AlbumAnswer
import app.discair.model.AlbumStep
import app.discair.model.AlbumTab
import app.discair.model.PathLink
import app.discair.model.albumPathsEmpty
import app.discair.model.albumTabDescription
import app.discair.model.isArtist
import app.discair.model.yearGap
import app.discair.ui.common.IndexButton
import app.discair.ui.common.IndexButtonKind
import app.discair.ui.common.IndexIconButton
import app.discair.ui.common.IndexIcons
import app.discair.ui.common.IndexLabel
import app.discair.ui.common.IndexMuted
import app.discair.ui.common.IndexPagesRules
import app.discair.ui.common.IndexRule
import app.discair.ui.common.IndexRules
import app.discair.ui.common.IndexSheetHeader
import app.discair.ui.common.IndexTabs
import app.discair.ui.common.IndexType
import app.discair.ui.common.Load
import app.discair.ui.common.PathAlbumCover
import app.discair.ui.common.PathRowCover
import app.discair.ui.common.SameRoomPhotos
import app.discair.ui.common.indexArrive
import app.discair.ui.theme.LocalPalette

private val Gutter = IndexRules.GUTTER.dp

/** A lettered reason: the letter and its word in `accent` mono, an optional name in the Section face at 20sp, then the server's sentence; a heavy rule above. */
internal class IndexReason(val word: String, val title: String?, val text: String?)

/*
 * Index's Album Paths (Layout.Index). Spec: docs/INDEX_THEME.md step I3; mockup: docs/design/index/pages/paths.html, frames 1 and 2.
 * The sheet keeps its behaviour (AlbumPathsSheet asks the server, keeps the answers and the open step, and Back closes the step): only the drawing is
 * Index's. The list: the header (cover, PATHS · FROM, title, kinds and steps), the kinds as tabs and the numbered steps with the server's sentence and the
 * library state. An opened step: a back arrow and "STUDIO CREW · STEP 01 / 04", the album, lettered reasons, then Open album and the person.
 */
@Composable
internal fun IndexAlbumPathList(
    albumName: String, artistName: String, albumId: String, tab: AlbumTab, tabs: List<AlbumTab>, state: Load<AlbumAnswer>, seeds: Int,
    step: Int, list: LazyListState, go: (PathLink) -> Unit,
    onTab: (AlbumTab) -> Unit, onStep: (Int) -> Unit, onRetry: () -> Unit,
) {
    val steps = (state as? Load.Ready)?.value?.steps.orEmpty()
    // The covers turned by a long press, kept across opening and closing a step.
    val covers = remember(tab) { mutableStateMapOf<Int, Int>() }
    if (step in steps.indices) {
        IndexAlbumStep(tab, steps, step, albumName, artistName, covers[step] ?: 0, go, onStep)
        return
    }
    Column(Modifier.fillMaxSize()) {
        IndexSheetHeader(
            albumName, eyebrow = "Paths · from", line = IndexPagesRules.pathsLine(tabs.size, (state as? Load.Ready)?.value?.steps?.size),
            art = { PathAlbumCover(artistName, albumName, Modifier.size(72.dp)) },
        )
        IndexTabs(tabs.map { it.label }, tabs.indexOf(tab), { onTab(tabs[it]) })
        IndexMuted(albumTabDescription(tab, albumName, seeds), Modifier.fillMaxWidth().padding(start = Gutter, end = Gutter, top = 10.dp, bottom = 4.dp))
        Box(Modifier.fillMaxWidth().weight(1f)) {
            IndexPathState(state, onRetry, "album", albumId, byMbid = false) { answer ->
                if (answer.steps.isEmpty()) IndexMuted(answer.empty ?: albumPathsEmpty(tab, albumName), Modifier.padding(horizontal = Gutter))
                else LazyColumn(Modifier.fillMaxSize(), state = list, contentPadding = PaddingValues(start = Gutter, end = Gutter, bottom = 32.dp)) {
                    answer.steps.forEachIndexed { i, s ->
                        item(key = "step:$i") {
                            StepRow(s, i, covers[i] ?: 0, Modifier.indexArrive(i, tab), onOpen = { onStep(i) }, onNextCover = { covers[i] = (covers[i] ?: 0) + 1 })
                        }
                    }
                    answer.notes.forEach { note -> item { IndexMuted(note, Modifier.padding(top = 16.dp)) } }
                }
            }
        }
    }
}

/** Loading, failure (with Try again, and Request update for a start the server does not know) or the answer. Shared by the album and artist sheets. */
@Composable
internal fun <T> IndexPathState(state: Load<T>, onRetry: () -> Unit, kind: String, id: String, byMbid: Boolean, ready: @Composable (T) -> Unit) {
    when (state) {
        Load.Loading -> IndexMuted("Loading paths…", Modifier.padding(Gutter).semantics { contentDescription = "Loading paths" })
        is Load.Failed -> Column(Modifier.fillMaxWidth().padding(Gutter), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(state.failure.message, style = IndexType.body(), color = LocalPalette.current.chartRedText)
            IndexButton("Try again", onRetry, kind = IndexButtonKind.Ghost, icon = IndexIcons.Refresh)
            if ((state.failure as? app.discair.net.ConnectionFailure.Server)?.code == 404) {
                app.discair.ui.common.RequestUpdateButton(kind, id, byMbid = byMbid, onDone = onRetry)
            }
        }
        is Load.Ready -> ready(state.value)
    }
}

/** A closed step: its number, a 56dp cover (a long press turns it to the album's next cover), the album over ARTIST · YEAR, the server's line and the library state. */
@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun StepRow(s: AlbumStep, i: Int, cover: Int, modifier: Modifier, onOpen: () -> Unit, onNextCover: () -> Unit) {
    val p = LocalPalette.current
    Column(modifier) {
        Row(
            Modifier.fillMaxWidth()
                .combinedClickable(onClickLabel = "Open step", role = Role.Button, onClick = onOpen, onLongClickLabel = "Show next cover", onLongClick = onNextCover)
                .semantics { stateDescription = "Collapsed" }.padding(vertical = 12.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(IndexPagesRules.number(i), style = IndexType.label(), color = p.accent, modifier = Modifier.size(width = 26.dp, height = 16.dp))
            PathRowCover(s.artist, s.album, cover, Modifier.size(56.dp))
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(s.album, style = IndexType.rowTitle(), color = p.text, maxLines = 2, overflow = TextOverflow.Ellipsis)
                IndexLabel(listOfNotNull(s.artist.ifBlank { null }, s.year?.toString()).joinToString(" · "))
                // The server's line, unless it only repeats the artist the meta line already says.
                if (s.detail.isNotBlank() && !s.detail.trim().equals(s.artist.trim(), ignoreCase = true)) Text(s.detail, style = IndexType.body().copy(fontSize = 13.5.sp, lineHeight = 19.sp), color = p.text, maxLines = 3, overflow = TextOverflow.Ellipsis)
                s.play?.let { IndexLabel(it, color = p.accent) }
                IndexLabel(if (s.owned) "In library" else "Not in library", color = if (s.owned) p.ok else p.textMuted)
            }
        }
        IndexRule()
    }
}

/** An opened step, in place of the list: the bar line, the album, the listening line, the studio photos, lettered reasons, then what to open and the next step. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun IndexAlbumStep(tab: AlbumTab, steps: List<AlbumStep>, at: Int, startName: String, startArtist: String, cover: Int, go: (PathLink) -> Unit, onStep: (Int) -> Unit) {
    val p = LocalPalette.current
    val s = steps[at]
    val reasons = s.reasons.take(3).flatMap { r ->
        val gap = if (tab == AlbumTab.SameYearSameScene) yearGap(r.text) else null
        listOfNotNull(IndexReason(IndexPagesRules.reasonWord(r.code, tab.label), r.via?.name, r.text), gap?.let { IndexReason("Same period", it, null) })
    }
    val person = s.reasons.firstNotNullOfOrNull { it.via?.takeIf { v -> v.isArtist } }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(bottom = 32.dp)) {
        IndexStepBar(IndexPagesRules.stepLine(tab.label, at, steps.size)) { onStep(-1) }
        IndexSheetHeader(
            s.album, eyebrow = IndexPagesRules.stepEyebrow(s.year, s.owned), eyebrowColor = if (s.owned) p.ok else p.textMuted, line = s.artist.ifBlank { null },
            art = { PathRowCover(s.artist, s.album, cover, Modifier.size(72.dp)) },
        )
        Column(Modifier.padding(start = Gutter, end = Gutter, top = 12.dp)) {
            s.play?.let { IndexReasonBlock(IndexReason("Your listening", it, null), null) }
            if (tab == AlbumTab.SameRoom) SameRoomPhotos(startArtist, startName, s.artist, s.album)
            reasons.forEachIndexed { i, r -> IndexReasonBlock(r, IndexPagesRules.letter(i)) }
            if (reasons.isEmpty()) IndexMuted(if (s.owned) "In your library." else "Not in your library.", Modifier.padding(top = 10.dp))
        }
        FlowRow(
            Modifier.fillMaxWidth().padding(start = Gutter, end = Gutter, top = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            if (s.artist.isNotBlank()) IndexButton("Open ${s.album}", { go(PathLink(true, s.album, s.artist)) }, icon = IndexIcons.Album)
            if (person != null) IndexButton(person.name, { go(PathLink(false, person.name, null, person.mbid)) }, kind = IndexButtonKind.Ghost, icon = IndexIcons.Place)
            if (at + 1 < steps.size) IndexButton("Next step →", { onStep(at + 1) }, kind = IndexButtonKind.Ghost)
        }
    }
}

/** The opened step's bar: a back arrow that closes the step, and the mono line ("STUDIO CREW · STEP 01 / 04") beside it. */
@Composable
internal fun IndexStepBar(line: String, onClose: () -> Unit) {
    Row(Modifier.fillMaxWidth().padding(horizontal = 4.dp).padding(bottom = 6.dp), verticalAlignment = Alignment.CenterVertically) {
        IndexIconButton(IndexIcons.Back, "Close step", onClose)
        IndexLabel(line, Modifier.weight(1f).padding(start = 6.dp).semantics { heading() })
    }
}

/** A lettered reason (paths.html frame 2): a heavy rule, "A · MUSICIAN" in `accent` mono, the name in the Section face at 20sp, the server's sentence. */
@Composable
internal fun IndexReasonBlock(r: IndexReason, letter: String?) {
    val p = LocalPalette.current
    Column(Modifier.fillMaxWidth().padding(bottom = 12.dp).semantics(mergeDescendants = true) {}) {
        IndexRule(heavy = true)
        IndexLabel(if (letter != null) "$letter · ${r.word}" else r.word, Modifier.padding(top = 10.dp), color = p.accent)
        if (r.title != null) Text(r.title, Modifier.padding(top = 6.dp), style = IndexType.section().copy(fontSize = 20.sp, lineHeight = 22.sp), color = p.text)
        if (r.text != null) Text(r.text, Modifier.padding(top = 4.dp), style = IndexType.body(), color = p.text)
    }
}
