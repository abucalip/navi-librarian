package app.discair.ui.player

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.model.sonicFailure
import app.discair.player.QueueItem
import app.discair.ui.common.Cover
import app.discair.ui.common.Load
import app.discair.ui.common.ModalBottomSheet
import app.discair.ui.common.OutlinedButton
import app.discair.ui.common.Target
import app.discair.ui.theme.Ink
import kotlinx.coroutines.CancellationException

private val BodyHeight = 360.dp

/**
 * A sonic path from the playing song to [target], as the server's ordered steps. Opened from a queue row; the server
 * is asked only while the sheet is open and nothing is saved on the phone. The steps are not scored or reordered.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SonicPathSheet(start: QueueItem, target: QueueItem, onDismiss: () -> Unit) {
    val play = LocalPlayActions.current
    var attempt by remember { mutableIntStateOf(0) }
    val state by produceState<Load<List<QueueItem>>>(Load.Loading, start.songId, target.songId, attempt) {
        value = Load.Loading
        value = try {
            Load.Ready(play.sonicPathItems(start.songId, target.songId))
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            Load.Failed(sonicFailure(e))
        }
    }
    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Sonic path", style = MaterialTheme.typography.titleLarge, modifier = Modifier.semantics { heading() })
            Text("${start.title} to ${target.title}", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Box(Modifier.fillMaxWidth().height(BodyHeight)) {
                when (val s = state) {
                    Load.Loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator(Modifier.semantics { contentDescription = "Loading the sonic path" })
                    }
                    is Load.Failed -> Column(Modifier.fillMaxSize(), verticalArrangement = Arrangement.Center) {
                        Text(s.failure.message, style = MaterialTheme.typography.bodyLarge, color = Ink.ChartRedText)
                        OutlinedButton(onClick = { attempt++ }, Modifier.heightIn(min = Target).padding(top = 12.dp)) { Text("Try again") }
                    }
                    is Load.Ready -> if (s.value.size < 2) {
                        Text("No sonic path between these songs yet.", style = MaterialTheme.typography.bodyLarge)
                    } else LazyColumn(Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        itemsIndexed(s.value) { index, step ->
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text("${index + 1}", style = MaterialTheme.typography.labelMedium, textAlign = TextAlign.End, modifier = Modifier.padding(end = 8.dp).size(24.dp))
                                Cover(step.coverUrl.ifBlank { null }, Modifier.padding(end = 12.dp).size(40.dp))
                                Column(Modifier.weight(1f)) {
                                    Text(step.title, style = MaterialTheme.typography.bodyMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                    Text(step.artist, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                }
                            }
                        }
                    }
                }
            }
            val steps = (state as? Load.Ready)?.value.orEmpty()
            if (steps.size >= 2) Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { play.useSonicPath(steps, playNow = false); onDismiss() }, Modifier.heightIn(min = Target)) { Text("Add to queue") }
                OutlinedButton(onClick = { play.useSonicPath(steps, playNow = true); onDismiss() }, Modifier.heightIn(min = Target)) { Text("Play now") }
            }
        }
    }
}
