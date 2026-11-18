package app.discair.ui.artist

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.model.PathKind
import app.discair.model.PathLink
import app.discair.model.PathPane
import app.discair.model.PathStop
import app.discair.model.PathsResponse
import app.discair.model.PathsView
import app.discair.model.heading
import app.discair.model.pane
import app.discair.model.sentence
import app.discair.model.view
import app.discair.ui.album.IndexPathState
import app.discair.ui.album.IndexReason
import app.discair.ui.album.IndexReasonBlock
import app.discair.ui.album.IndexStepBar
import app.discair.ui.common.ArtistPhoto
import app.discair.ui.common.IndexButton
import app.discair.ui.common.IndexButtonKind
import app.discair.ui.common.IndexDataList
import app.discair.ui.common.IndexDatum
import app.discair.ui.common.IndexIcons
import app.discair.ui.common.IndexLabel
import app.discair.ui.common.IndexMuted
import app.discair.ui.common.IndexPagesRules
import app.discair.ui.common.IndexRow
import app.discair.ui.common.IndexRule
import app.discair.ui.common.IndexRules
import app.discair.ui.common.IndexSheetHeader
import app.discair.ui.common.IndexTabs
import app.discair.ui.common.IndexType
import app.discair.ui.common.Load
import app.discair.ui.common.PathAlbumCover
import app.discair.ui.common.indexArrive
import app.discair.ui.theme.LocalPalette

private val Gutter = IndexRules.GUTTER.dp

/*
 * Index's Artist Paths (Layout.Index). Spec: docs/INDEX_THEME.md step I3; mockup: docs/design/index/pages/paths.html, frames 3 and 4.
 * The sheet keeps its behaviour (ArtistPathsSheet asks the server per kind, keeps the answers and the open step); only the drawing is Index's. The list: the
 * header (photo, PATHS · FROM, the name, the kinds and steps), the five kinds as tabs and the numbered steps, each with the server's sentence and the library
 * state. An opened step: the bar line, the stop with its data list (for a sideman, With and Owned from the server's shared albums), lettered reasons, the
 * albums together, then what to open and the next step.
 */
@Composable
internal fun IndexArtistPathList(
    artistName: String, mbid: String, kind: PathKind, state: Load<PathsResponse>, step: Int, list: LazyListState, go: (PathLink) -> Unit,
    onKind: (PathKind) -> Unit, onStep: (Int) -> Unit, onRetry: () -> Unit,
) {
    val response = (state as? Load.Ready)?.value
    val stops = (response?.view() as? PathsView.Stops)?.response?.stops.orEmpty()
    val covers = remember(kind) { mutableStateMapOf<Int, Int>() }
    if (step in stops.indices) {
        IndexArtistStep(kind, stops, step, artistName, covers[step] ?: 0, go, onStep)
        return
    }
    Column(Modifier.fillMaxSize()) {
        IndexSheetHeader(
            artistName, eyebrow = "Paths · from", line = IndexPagesRules.pathsLine(PathKind.entries.size, response?.let { stops.size }),
            art = { ArtistPhoto(artistName, null, Modifier.size(72.dp), rect = true) },
        )
        IndexTabs(PathKind.entries.map { it.label }, PathKind.entries.indexOf(kind), { onKind(PathKind.entries[it]) })
        IndexMuted(kindDescription(kind, artistName, response?.startType.orEmpty()), Modifier.fillMaxWidth().padding(start = Gutter, end = Gutter, top = 10.dp, bottom = 4.dp))
        Box(Modifier.fillMaxWidth().weight(1f)) {
            IndexPathState(state, onRetry, "artist", mbid, byMbid = true) { answer ->
                when (val view = answer.view()) {
                    is PathsView.Stops -> LazyColumn(Modifier.fillMaxSize(), state = list, contentPadding = PaddingValues(start = Gutter, end = Gutter, bottom = 32.dp)) {
                        view.response.stops.forEachIndexed { i, stop ->
                            item(key = "stop:$i") {
                                StopRow(kind, stop, i, covers[i] ?: 0, Modifier.indexArrive(i, kind), onOpen = { onStep(i) }, onNextCover = { covers[i] = (covers[i] ?: 0) + 1 })
                            }
                        }
                        answer.truncated?.let { t -> item { IndexMuted("The server stopped this path early (${truncatedWords(t)}), so later steps may be missing.", Modifier.padding(top = 16.dp)) } }
                    }
                    PathsView.Empty -> IndexMuted(
                        "No ${kind.label.lowercase()} path from $artistName yet. A path appears only when every step has evidence.", Modifier.padding(horizontal = Gutter),
                    )
                }
            }
        }
    }
}

/** A closed step (paths.html frame 3): its number, a 52dp picture, the name over the server's sentence, the library state and a chevron. */
@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun StopRow(kind: PathKind, stop: PathStop, i: Int, cover: Int, modifier: Modifier, onOpen: () -> Unit, onNextCover: () -> Unit) {
    val p = LocalPalette.current
    val heading = stop.heading(kind)
    val sentence = IndexPagesRules.reasonSentence(stop.name, stop.reasons.firstOrNull()?.sentence() ?: stop.reason)
    Column(modifier) {
        Row(
            Modifier.fillMaxWidth()
                .combinedClickable(onClickLabel = "Open step", role = Role.Button, onClick = onOpen, onLongClickLabel = "Show next cover", onLongClick = onNextCover)
                .semantics { stateDescription = "Collapsed" }.padding(vertical = 10.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(IndexPagesRules.number(i), style = IndexType.label(), color = p.accent, modifier = Modifier.size(width = 26.dp, height = 16.dp))
            PathThumb(kind, stop, 52, cover)
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(heading.title, style = IndexType.rowTitle(), color = p.text, maxLines = 2, overflow = TextOverflow.Ellipsis)
                heading.detail?.takeIf { it.isNotBlank() }?.let { IndexLabel(it) }
                Text(sentence, style = IndexType.body().copy(fontSize = 13.5.sp, lineHeight = 19.sp), color = p.text, maxLines = 4, overflow = TextOverflow.Ellipsis)
                IndexLabel(if (stop.owned) "In library" else "Not in library", color = if (stop.owned) p.ok else p.textMuted)
            }
            Icon(IndexIcons.Chevron, null, tint = p.textMuted, modifier = Modifier.size(IndexRules.ICON_INLINE.dp))
        }
        IndexRule()
    }
}

/** The opened stop's title, data list and what it opens, per pane: each shows only what the server sent. */
private class StopFace(val title: String, val rows: List<IndexDatum>, val primary: Pair<String, PathLink>?, val secondary: Pair<String, PathLink>?)

private fun face(pane: PathPane, stop: PathStop, kind: PathKind): StopFace {
    val library = IndexDatum("Library", if (stop.owned) "In library" else "Not in library")
    return when (pane) {
        is PathPane.Song -> StopFace(
            pane.title,
            listOfNotNull(pane.album?.let { IndexDatum("On", it) }, pane.artist?.let { IndexDatum("By", it) }, library),
            pane.album?.let { a -> pane.artist?.let { by -> "Open album" to PathLink(true, a, by) } },
            pane.musician?.let { it.name to it },
        )
        is PathPane.Leader -> StopFace(
            pane.name,
            listOfNotNull(
                IndexDatum("Type", pane.typeLabel),
                IndexPagesRules.withYears(stop.years)?.let { IndexDatum("With", it) },
                IndexDatum("Owned", IndexPagesRules.sharedOwned(stop.sharedAlbums) ?: library.value),
            ),
            "Open artist" to PathLink(false, pane.name, null, pane.mbid), null,
        )
        is PathPane.LabelAlbum -> StopFace(
            pane.album,
            listOfNotNull(pane.artist?.let { IndexDatum("By", it) }, pane.reason?.label?.takeIf { it.isNotBlank() }?.let { IndexDatum("Label", it) }, library),
            pane.artist?.let { by -> "Open album" to PathLink(true, pane.album, by) },
            pane.artist?.let { it to PathLink(false, it) },
        )
        is PathPane.Recording -> StopFace(
            stop.heading(kind).title,
            listOfNotNull(pane.work?.let { IndexDatum("Work", it) }, pane.performer?.let { IndexDatum("By", it) }, pane.album?.let { IndexDatum("On", it) }, library),
            pane.album?.let { a -> (pane.albumArtist ?: pane.performer)?.let { by -> "Open album" to PathLink(true, a, by) } },
            pane.performer?.let { it to PathLink(false, it) },
        )
        is PathPane.Place -> StopFace(
            pane.name,
            listOfNotNull(IndexDatum("Type", pane.typeLabel), pane.place?.let { IndexDatum("From", it) }, (pane.era ?: pane.years?.let { "Within $it years" })?.let { IndexDatum("Era", it) }, library),
            "Open artist" to PathLink(false, pane.name, null, pane.mbid), null,
        )
    }
}

/** An opened stop, in place of the list (paths.html frame 4). */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun IndexArtistStep(kind: PathKind, stops: List<PathStop>, at: Int, startName: String, cover: Int, go: (PathLink) -> Unit, onStep: (Int) -> Unit) {
    val p = LocalPalette.current
    val stop = stops[at]
    // Each time a step opens, the pane picks again among the reasons the server sent.
    val pane = remember(stop, kind) { stop.pane(kind, startName) }
    val f = face(pane, stop, kind)
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(bottom = 32.dp)) {
        IndexStepBar("${kind.label} · ${IndexPagesRules.number(at)} / ${"%02d".format(stops.size)}") { onStep(-1) }
        IndexSheetHeader(f.title, art = { PathThumb(kind, stop, 96, cover) }, extra = { IndexDataList(f.rows, Modifier.padding(top = 6.dp)) })
        Column(Modifier.padding(start = Gutter, end = Gutter, top = 12.dp)) {
            stop.reasons.take(3).forEachIndexed { i, r ->
                IndexReasonBlock(IndexReason(IndexPagesRules.reasonWord(r.code, kind.label), null, IndexPagesRules.reasonSentence(stop.name, r.sentence())), IndexPagesRules.letter(i))
            }
            // A sideman's records: the server's shared albums with their states when it sends them, else the records the reasons name.
            val shared = stop.sharedAlbums
            if (pane is PathPane.Leader && !shared.isNullOrEmpty()) {
                Row(Modifier.padding(top = 4.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = androidx.compose.ui.Alignment.Bottom) {
                    Text("Albums together", style = IndexType.section().copy(fontSize = 20.sp, lineHeight = 22.sp), color = p.text)
                    IndexLabel(shared.size.toString(), Modifier.padding(bottom = 2.dp))
                }
                shared.chunked(IndexPagesRules.COLUMNS).forEach { row ->
                    Row(Modifier.fillMaxWidth().padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        row.forEach { a ->
                            val said = listOfNotNull(a.album, a.year?.toString(), if (a.owned) "in your library" else "not in your library").joinToString(", ")
                            Column(
                                Modifier.weight(1f).clickable(role = Role.Button) { go(PathLink(true, a.album, pane.name)) }.semantics(mergeDescendants = true) { contentDescription = said },
                                verticalArrangement = Arrangement.spacedBy(4.dp),
                            ) {
                                PathAlbumCover(pane.name, a.album, Modifier.fillMaxWidth().aspectRatio(1f))
                                IndexLabel(a.year?.toString() ?: "—")
                                IndexLabel(if (a.owned) "In library" else "Not in library", color = if (a.owned) p.ok else p.textMuted)
                            }
                        }
                        repeat(IndexPagesRules.COLUMNS - row.size) { Box(Modifier.weight(1f)) }
                    }
                }
            } else if (pane is PathPane.Leader && pane.records.isNotEmpty()) {
                Text("Records ${pane.name} led", style = IndexType.section().copy(fontSize = 20.sp, lineHeight = 22.sp), color = p.text, modifier = Modifier.padding(top = 4.dp))
                pane.records.forEachIndexed { i, record ->
                    IndexRow(
                        record.release, meta = record.carries.orEmpty(), number = IndexPagesRules.number(i), onClick = { go(PathLink(true, record.release, pane.name)) },
                        lead = { PathAlbumCover(pane.name, record.release, Modifier.size(48.dp)) },
                    )
                }
            }
        }
        FlowRow(
            Modifier.fillMaxWidth().padding(start = Gutter, end = Gutter, top = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            f.primary?.let { (label, link) -> IndexButton(label, { go(link) }, icon = if (link.album) IndexIcons.Album else IndexIcons.Place) }
            f.secondary?.let { (label, link) -> IndexButton(label, { go(link) }, kind = IndexButtonKind.Ghost, icon = IndexIcons.Place) }
            if (at + 1 < stops.size) IndexButton("Next step →", { onStep(at + 1) }, kind = IndexButtonKind.Ghost)
        }
    }
}
