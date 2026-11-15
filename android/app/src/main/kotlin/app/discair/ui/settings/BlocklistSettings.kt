package app.discair.ui.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.size
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import app.discair.model.Blocklist
import app.discair.model.Lean
import app.discair.ui.common.ArtIcons
import app.discair.ui.common.LocalRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * The blocklist (Star Operation S2c): blocked genres, artists hidden with "Not this artist", and artists marked More or Less like
 * this, each with a button that lifts it. It lives on the server, so this reads it live and writes each change at once. A block
 * hides picks only; the library and Saved are never touched. Lifting a "Not this artist" also lifts its score penalty.
 */
@Composable
fun BlocklistSettings() {
    val repo = LocalRepository.current
    val scope = rememberCoroutineScope()
    var list by remember { mutableStateOf<Blocklist?>(null) }
    var note by remember { mutableStateOf<String?>(null) }
    var failed by remember { mutableStateOf(false) }
    var busy by remember { mutableStateOf(false) }
    var expanded by rememberSaveable { mutableStateOf(false) }
    var reload by remember { mutableIntStateOf(0) }

    LaunchedEffect(repo, reload, expanded) {
        if (!expanded && list != null) return@LaunchedEffect
        try {
            list = withContext(Dispatchers.IO) { repo.blocklist() }
            failed = false
        } catch (e: Exception) {
            failed = true
            note = "Could not read this from the server."
        }
    }

    fun lift(call: () -> Unit) {
        busy = true; note = null; failed = false
        scope.launch {
            try {
                withContext(Dispatchers.IO) { call() }
                reload++
            } catch (e: Exception) {
                failed = true
                note = e.message ?: "The server did not do that. Try again."
            }
            busy = false
        }
    }

    val l = list
    val count = l?.let { it.genres.size + it.hiddenArtists.size + it.leans.size }
    Column(Modifier.fillMaxWidth()) {
        SettingsRow(
            ArtIcons.Delete, "Blocklist",
            when { count == null && failed -> "Could not read this"; count == null -> "Checking the server."; count == 0 -> "Nothing blocked"; else -> "$count on the list" },
            onClick = { expanded = !expanded },
            trailing = { androidx.compose.material3.Icon(if (expanded) app.discair.ui.player.PlayerIcons.Down else app.discair.ui.player.PlayerIcons.Right, contentDescription = if (expanded) "Collapse" else "Expand") },
        )
        if (expanded && l != null) Column(Modifier.fillMaxWidth()) {
            Text(
                "A block hides picks only. Your library and Saved are not affected. Unblocking brings them back on the next refresh.",
                style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            BlockGroup("Blocked genres", "No blocked genres.", l.genres.map { g -> BlockRow(g, "Unblock") { lift { repo.unblockGenre(g) } } }, busy)
            BlockGroup(
                "Hidden with Not this artist", "No hidden artists.",
                l.hiddenArtists.map { a -> BlockRow(a, "Unblock") { lift { repo.unblockArtist(a) } } }, busy,
            )
            BlockGroup(
                "More and Less like this", "No artists marked.",
                l.leans.map { it -> BlockRow("${it.artist} · ${if (it.lean == Lean.More) "More" else "Less"} like this", "Clear") { lift { repo.clearArtistLean(it.artist) } } },
                busy,
            )
        }
        note?.let {
            Text(it, style = MaterialTheme.typography.bodySmall, color = if (failed) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

/** One row of a group: its words, the label of its button, and what the button does. */
private class BlockRow(val label: String, val button: String, val onLift: () -> Unit)

/** One titled group of rows, each a name and a button of at least 48dp that lifts it. */
@Composable
private fun BlockGroup(title: String, empty: String, rows: List<BlockRow>, busy: Boolean) {
    Spacer(Modifier.size(8.dp))
    Text(title, style = MaterialTheme.typography.titleSmall, modifier = Modifier.semantics { heading() })
    if (rows.isEmpty()) Text(empty, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    for (row in rows) {
        Row(Modifier.fillMaxWidth().heightIn(min = 48.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(row.label, Modifier.weight(1f).padding(end = 8.dp), style = MaterialTheme.typography.bodyMedium)
            TextButton(
                onClick = row.onLift, enabled = !busy,
                modifier = Modifier.heightIn(min = 48.dp).semantics { contentDescription = "${row.button} ${row.label}" },
            ) { Text(row.button) }
        }
    }
}
