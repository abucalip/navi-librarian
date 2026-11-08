package app.discair.ui.artist

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import app.discair.model.PathKind
import app.discair.model.PathReason
import app.discair.model.heading
import app.discair.model.isArtist
import app.discair.model.PathStop
import app.discair.model.PathsResponse
import app.discair.model.PathsView
import app.discair.model.pathsFailure
import app.discair.model.view
import app.discair.ui.common.FilterChip
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.Load
import app.discair.ui.common.ModalBottomSheet
import app.discair.ui.common.OutlinedButton
import app.discair.ui.common.Target
import app.discair.ui.common.routeKey
import app.discair.ui.Opener
import app.discair.ui.theme.Ink
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** Body height: a fixed box, so the list scrolls inside the sheet and a failure never fills an unbounded space. */
private val BodyHeight = 300.dp

/**
 * The paths view, opened from the artist page: pick one of the five kinds and see the server's path as a short list.
 * The server is asked only when the sheet is open and a kind is chosen; nothing is saved on the phone.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ArtistPathsSheet(artistName: String, mbid: String, open: Opener, onDismiss: () -> Unit) {
    val repo = LocalRepository.current
    var kind by remember { mutableStateOf(PathKind.FollowTheMusician) }
    var attempt by remember { mutableIntStateOf(0) }
    val state by produceState<Load<PathsResponse>>(Load.Loading, kind, mbid, attempt) {
        value = Load.Loading
        value = withContext(Dispatchers.IO) {
            try {
                Load.Ready(repo.paths(kind, mbid))
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                Load.Failed(pathsFailure(e))
            }
        }
    }

    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(
            Modifier.fillMaxWidth().padding(horizontal = 16.dp).padding(top = 2.dp, bottom = 8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                "Paths from $artistName",
                style = MaterialTheme.typography.titleLarge,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth().semantics { heading() },
            )
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                items(PathKind.entries, key = { it.wire }) { option ->
                    FilterChip(
                        selected = option == kind,
                        onClick = { kind = option },
                        label = { Text(option.label) },
                        modifier = Modifier.heightIn(min = Target),
                    )
                }
            }
            Text(
                kindDescription(kind, artistName),
                style = MaterialTheme.typography.bodySmall,
                color = Ink.TextMuted,
                modifier = Modifier.fillMaxWidth(),
            )
            Box(Modifier.fillMaxWidth().height(BodyHeight)) {
                when (val s = state) {
                    Load.Loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator(Modifier.semantics { contentDescription = "Loading paths" })
                    }
                    is Load.Failed -> Column(Modifier.fillMaxSize(), verticalArrangement = Arrangement.Center) {
                        Text(s.failure.message, style = MaterialTheme.typography.bodyLarge, color = Ink.ChartRedText)
                        Spacer(Modifier.size(12.dp))
                        OutlinedButton(onClick = { attempt++ }, Modifier.heightIn(min = Target)) { Text("Try again") }
                    }
                    is Load.Ready -> PathBody(artistName, kind, s.value, open, onDismiss)
                }
            }
        }
    }
}

@Composable
private fun PathBody(artistName: String, kind: PathKind, response: PathsResponse, open: Opener, onDismiss: () -> Unit) {
    // Only one row is open at a time; a new kind or a new answer starts closed.
    var expanded by remember(response) { mutableIntStateOf(-1) }
    when (val view = response.view()) {
        is PathsView.Stops -> LazyColumn(
            Modifier.fillMaxSize(),
            contentPadding = PaddingValues(bottom = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            itemsIndexed(view.response.stops) { index, stop ->
                StepRow(
                    index + 1, kind, stop, expanded == index,
                    onToggle = { expanded = if (expanded == index) -1 else index },
                    open = open, onDismiss = onDismiss,
                )
            }
            response.truncated?.let { reason ->
                item {
                    Text(
                        "The server stopped this path early (${truncatedWords(reason)}), so later steps may be missing.",
                        style = MaterialTheme.typography.bodySmall, color = Ink.TextMuted,
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

private fun kindDescription(kind: PathKind, artist: String) = when (kind) {
    PathKind.FollowTheMusician -> "Songs, not in your library, by musicians who also played with $artist."
    PathKind.SidemanToLeader -> "Artists whose records $artist played on as a sideman."
    PathKind.LabelPath -> "Albums released on the same labels as $artist's records."
    PathKind.CompositionPath -> "Other recordings of the same compositions as $artist's, covers and live versions included."
    PathKind.ScenePath -> "Artists from the same place and era as $artist."
}

/** One step: its place in the path, the main name with its bracketed detail, and a chevron that opens the relationship. */
@Composable
private fun StepRow(number: Int, kind: PathKind, stop: PathStop, expanded: Boolean, onToggle: () -> Unit, open: Opener, onDismiss: () -> Unit) {
    val heading = stop.heading(kind)
    Column(Modifier.fillMaxWidth().animateContentSize()) {
        Row(
            Modifier.fillMaxWidth().heightIn(min = Target)
                .clickable(onClick = onToggle)
                .semantics(mergeDescendants = true) {
                    role = Role.Button
                    stateDescription = if (expanded) "Expanded" else "Collapsed"
                },
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.Top,
        ) {
            Text("$number", style = MaterialTheme.typography.labelLarge, color = Ink.TextMuted, modifier = Modifier.padding(top = 2.dp))
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(
                    buildString {
                        append(heading.title)
                        heading.detail?.let { append(" ($it)") }
                    },
                    style = MaterialTheme.typography.bodyLarge, maxLines = if (expanded) Int.MAX_VALUE else 2,
                )
                if (!expanded) Text(stop.reason, style = MaterialTheme.typography.bodySmall, color = Ink.TextMuted, maxLines = 2)
            }
            Icon(
                if (expanded) Icons.Default.KeyboardArrowUp else Icons.Default.KeyboardArrowDown,
                contentDescription = if (expanded) "Collapse" else "Expand",
                modifier = Modifier.size(24.dp),
            )
        }
        if (expanded) StepDetails(kind, stop, heading.detail, open, onDismiss)
    }
}

/** What the row opens to: every reason the server gave, the library state, and buttons to the pages involved. */
@Composable
private fun StepDetails(kind: PathKind, stop: PathStop, detail: String?, open: Opener, onDismiss: () -> Unit) {
    val targets = pathTargets(kind, stop)
    Column(Modifier.fillMaxWidth().padding(start = 26.dp, top = 4.dp, bottom = 4.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        val reasons: List<PathReason> = stop.reasons.ifEmpty { listOf(PathReason(stop.reason, "", null, null)) }
        reasons.take(3).forEach { Text(it.text, style = MaterialTheme.typography.bodyMedium) }
        if (stop.reasonCount > 3) {
            Text("${stop.reasonCount - 3} more reasons on the server.", style = MaterialTheme.typography.bodySmall, color = Ink.TextMuted)
        }
        Text(
            if (stop.owned) "In your library" else "Not in your library",
            style = MaterialTheme.typography.bodySmall, color = Ink.TextMuted,
        )
        targets.forEach { target ->
            OutlinedButton(
                onClick = { onDismiss(); target.go(open) },
                Modifier.fillMaxWidth().heightIn(min = Target),
            ) { Text(target.label, maxLines = 1) }
        }
    }
}

private class PathTarget(val label: String, val go: (Opener) -> Unit)

/** The artist and album pages a row can open. An album needs its artist's name to be opened, so one without is not offered. */
private fun pathTargets(kind: PathKind, stop: PathStop): List<PathTarget> {
    val out = mutableListOf<PathTarget>()
    fun artist(name: String, mbid: String?) {
        if (out.none { it.label == "Artist: $name" }) out += PathTarget("Artist: $name") { it.artist(name, null, null, mbid) }
    }
    fun album(name: String, by: String?) {
        if (by != null) out += PathTarget("Album: $name") { it.album(routeKey(by, name), by, name, null, null) }
    }
    when (kind) {
        PathKind.FollowTheMusician -> {
            stop.reasons.mapNotNull { it.via }.filter { it.isArtist }.distinctBy { it.name }.take(2).forEach { artist(it.name, it.mbid) }
            stop.album?.let { album(it, stop.albumArtist) }
            stop.albumArtist?.let { artist(it, null) }
        }
        PathKind.SidemanToLeader -> {
            artist(stop.name, stop.mbid)
            stop.reasons.firstNotNullOfOrNull { it.via?.takeIf { v -> v.type == "release" } }?.let { album(it.name, stop.name) }
        }
        PathKind.LabelPath -> {
            album(stop.name, stop.albumArtist)
            stop.albumArtist?.let { artist(it, null) }
        }
        PathKind.CompositionPath -> stop.artist?.let { artist(it, null) }
        PathKind.ScenePath -> artist(stop.name, stop.mbid)
    }
    return out
}

private fun truncatedWords(reason: String) = when (reason) {
    "rows" -> "row limit"
    "time" -> "time limit"
    "stops" -> "stop limit"
    else -> "limit"
}
