package app.discair.ui.artist

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
import androidx.compose.material3.CircularProgressIndicator
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
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import app.discair.model.PathKind
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
fun ArtistPathsSheet(artistName: String, mbid: String, onDismiss: () -> Unit) {
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
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(3.dp),
            ) {
                PathDescription("Follow the musician", "Songs by musicians who played with $artistName, not in your library.")
                PathDescription("Sideman", "$artistName also performed with:")
                PathDescription("Label", "Records under the same publishers.")
                PathDescription("Composition", "Other recordings of the same composition, including covers and live versions.")
                PathDescription("Scene", "Other artists from the same place and era.")
            }
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
                    is Load.Ready -> PathBody(artistName, kind, s.value)
                }
            }
        }
    }
}

@Composable
private fun PathBody(artistName: String, kind: PathKind, response: PathsResponse) {
    when (val view = response.view()) {
        is PathsView.Stops -> LazyColumn(
            Modifier.fillMaxSize(),
            contentPadding = PaddingValues(bottom = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            itemsIndexed(view.response.stops) { index, stop -> StepRow(index + 1, stop) }
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

@Composable
private fun PathDescription(label: String, description: String) {
    Text(
        "$label: $description",
        style = MaterialTheme.typography.bodySmall,
        color = Ink.TextMuted,
        textAlign = TextAlign.Start,
        modifier = Modifier.fillMaxWidth(),
    )
}

/** One step: its place in the path, the entity, and the server's one-line reason. */
@Composable
private fun StepRow(number: Int, stop: PathStop) {
    Row(Modifier.fillMaxWidth().semantics(mergeDescendants = true) {}, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("$number", style = MaterialTheme.typography.labelLarge, color = Ink.TextMuted, modifier = Modifier.padding(top = 2.dp))
        Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(stop.displayTitle ?: stop.name, style = MaterialTheme.typography.bodyLarge, maxLines = 2)
            stop.displayContext?.let { context ->
                Text("($context)", style = MaterialTheme.typography.bodySmall, color = Ink.TextMuted, maxLines = 2)
            }
            Text(stop.reason, style = MaterialTheme.typography.bodySmall, color = Ink.TextMuted, maxLines = 2)
        }
    }
}

private fun truncatedWords(reason: String) = when (reason) {
    "rows" -> "row limit"
    "time" -> "time limit"
    "stops" -> "stop limit"
    else -> "limit"
}
