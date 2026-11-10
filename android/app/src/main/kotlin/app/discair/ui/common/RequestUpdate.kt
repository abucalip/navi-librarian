package app.discair.ui.common

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.size
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import app.discair.model.StoreUpdate
import app.discair.ui.theme.Ink
import kotlin.coroutines.cancellation.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private const val PollMillis = 3_000L
private const val GiveUpAfterPolls = 60

/**
 * "Request update": asks the server's worker to add this artist or album to its knowledge store, then waits for it.
 * [onDone] runs once the worker reports the store updated, so the caller can read the path again.
 */
@Composable
fun RequestUpdateButton(subject: String, id: String, byMbid: Boolean, onDone: () -> Unit) {
    val repo = LocalRepository.current
    val scope = rememberCoroutineScope()
    var note by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }
    Column {
        OutlinedButton(
            onClick = {
                busy = true
                note = "Asking the server…"
                scope.launch {
                    var result: StoreUpdate? = null
                    try {
                        result = withContext(Dispatchers.IO) { repo.requestStoreUpdate(subject, id, byMbid) }
                        var polls = 0
                        while (result?.finished == false && polls++ < GiveUpAfterPolls) {
                            note = "The server is updating its store…"
                            delay(PollMillis)
                            result = withContext(Dispatchers.IO) { repo.storeUpdateStatus(subject, id, byMbid) }
                        }
                    } catch (e: CancellationException) {
                        throw e
                    } catch (e: Exception) {
                        result = null
                    }
                    busy = false
                    when (result?.state) {
                        "done" -> { note = null; onDone() }
                        "failed" -> note = result?.message ?: "The server could not add this."
                        null -> note = "The server could not be reached. Try again."
                        else -> note = "The server is still working on it. Try again in a minute."
                    }
                }
            },
            enabled = !busy,
            modifier = Modifier.heightIn(min = Target),
        ) { Text("Request update") }
        note?.let {
            Spacer(Modifier.size(8.dp))
            Text(it, style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted)
        }
    }
}
