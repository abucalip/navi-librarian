package app.discair.ui.downloads

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.clickable
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.LifecycleStartEffect
import app.discair.data.AcquisitionHub
import app.discair.data.RowBusy
import app.discair.model.AcquisitionJob
import app.discair.model.Tone
import app.discair.model.formatBytes
import app.discair.model.formatSpeed
import app.discair.ui.Opener
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.BackBar
import app.discair.ui.common.LocalAcquisitions
import app.discair.ui.common.PageHeading
import app.discair.ui.common.RowDivider
import app.discair.ui.common.Target
import app.discair.ui.common.plural
import app.discair.ui.common.routeKey
import app.discair.ui.theme.Display
import app.discair.ui.theme.Ink
import java.text.DateFormat
import kotlinx.coroutines.launch
import java.util.Date
import kotlin.math.roundToInt

/**
 * The Downloads page (contract 5.3, Phase 4): every acquisition record with live progress, Try again,
 * Use next source and Dismiss. Rows come in the order the hub gives (newest request first, like the web).
 * The stream is read only while the page is visible; no notifications or background progress (owner decision).
 */
@Composable
fun DownloadsScreen(open: Opener) {
    val hub = LocalAcquisitions.current
    LifecycleStartEffect(hub) {
        hub.watch()
        onStopOrDispose { hub.unwatch() }
    }
    val jobs = hub.jobs
    var confirm by remember { mutableStateOf<Confirm?>(null) }
    val ticking = jobs.orEmpty().any { it.skipSecondsLeft(System.currentTimeMillis() / 1000.0) != null }
    val now by produceState(System.currentTimeMillis() / 1000.0, ticking) {
        while (ticking) {
            kotlinx.coroutines.delay(1000)
            value = System.currentTimeMillis() / 1000.0
        }
    }

    Column(Modifier.fillMaxSize()) {
        BackBar(open.back)
        PageHeading("Downloads", Modifier.padding(start = 16.dp, end = 16.dp), large = true)
        StatusLine(hub, jobs)
        val imported = jobs.orEmpty().count { it.isImported }
        if (imported > 0) OutlinedButton(
            onClick = { confirm = Confirm.Imported(imported) },
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp).heightIn(min = Target),
        ) { Text("Dismiss all successful imports") }
        when {
            jobs == null && hub.listProblem == null -> Column(
                Modifier.fillMaxSize(), verticalArrangement = Arrangement.Center, horizontalAlignment = Alignment.CenterHorizontally,
            ) { CircularProgressIndicator(Modifier.semantics { contentDescription = "Loading" }) }
            jobs == null -> {
                // The first read failed: the status line says why; offer the way out (the screen never dead-ends).
                val scope = androidx.compose.runtime.rememberCoroutineScope()
                OutlinedButton(
                    onClick = { scope.launch { hub.refreshOnce() } },
                    modifier = Modifier.padding(16.dp).heightIn(min = Target),
                ) { Text("Try again") }
            }
            jobs.isEmpty() -> Text(
                "No acquisition records yet. Requests you make from a discovery page appear here.",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(16.dp),
            )
            else -> LazyColumn(Modifier.fillMaxSize()) {
                items(jobs, key = { it.key }) { job ->
                    JobRow(job, hub, now, open, onDismiss = { confirm = Confirm.One(job) })
                    RowDivider()
                }
            }
        }
    }

    confirm?.let { ask ->
        AlertDialog(
            onDismissRequest = { confirm = null },
            title = { Text(ask.title) },
            text = {
                Text(
                    "This removes the record and deletes the downloaded files the server identifies for it. " +
                        "The server refuses if it cannot do that safely.",
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        confirm = null
                        when (ask) {
                            is Confirm.One -> hub.dismiss(ask.job)
                            is Confirm.Imported -> hub.dismissImported()
                        }
                    },
                    Modifier.heightIn(min = Target),
                ) { Text("Dismiss") }
            },
            dismissButton = { TextButton(onClick = { confirm = null }, Modifier.heightIn(min = Target)) { Text("Cancel") } },
        )
    }
}

private sealed class Confirm(val title: String) {
    class One(val job: AcquisitionJob) : Confirm("Dismiss ${job.title}?")
    class Imported(count: Int) : Confirm("Dismiss ${plural(count, "import")}?")
}

/** One polite line: how many records, whether updates are live, and any problem reading the list. */
@Composable
private fun StatusLine(hub: AcquisitionHub, jobs: List<AcquisitionJob>?) {
    val text = when {
        hub.listProblem != null -> hub.listProblem!!
        jobs == null -> "Connecting to acquisition status…"
        jobs.isEmpty() -> "No acquisition records to show."
        else -> plural(jobs.size, "acquisition record") + if (hub.live) ". Updating live." else ". Refreshing every few seconds."
    }
    Text(
        text,
        style = MaterialTheme.typography.bodyMedium,
        color = if (hub.listProblem != null) Ink.ChartRedText else MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp).semantics { liveRegion = LiveRegionMode.Polite },
    )
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun JobRow(job: AcquisitionJob, hub: AcquisitionHub, now: Double, open: Opener, onDismiss: () -> Unit) {
    val busy = hub.busy(job)
    Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp)) {
        AlbumCover(
            job.artistName, job.albumName, null,
            Modifier.size(64.dp).clickable { open.album(routeKey(job.artist, job.albumName), job.artist, job.albumName, null, job.year) },
        )
        Column(Modifier.weight(1f).padding(start = 12.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(
                job.title, style = MaterialTheme.typography.titleLarge.copy(fontFamily = Display),
                maxLines = 2, overflow = TextOverflow.Ellipsis,
                modifier = if (job.isSong) Modifier else Modifier.clickable {
                    open.album(routeKey(job.artist, job.albumName), job.artist, job.albumName, null, job.year)
                },
            )
            Text(
                job.artistName, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.primary,
                maxLines = 1, overflow = TextOverflow.Ellipsis,
                modifier = Modifier.heightIn(min = Target).clickable { open.artist(job.artistName, null, null, null) }
                    .padding(vertical = 12.dp),
            )
            if (job.isSong) Text(
                "Song on ${job.albumName}", style = MaterialTheme.typography.bodyMedium,
                maxLines = 1, overflow = TextOverflow.Ellipsis,
                modifier = Modifier.heightIn(min = Target).clickable {
                    open.album(routeKey(job.artist, job.albumName), job.artist, job.albumName, null, job.year)
                }.padding(vertical = 12.dp),
            )
            Text(
                "Quality profile: ${job.qualityProfile}", style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            // The icon and the words are the status; the colour only adds emphasis (rule 4).
            val info = job.info
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Icon(statusIcon(job), contentDescription = null, tint = toneColor(info.tone), modifier = Modifier.size(18.dp))
                Text(info.label, style = MaterialTheme.typography.titleMedium, color = toneColor(info.tone))
            }
            job.progress?.let { Progress(it) }
            listOfNotNull(
                job.message, job.error,
                job.peer?.let { "Peer: $it" },
                job.updatedAt?.let { "Updated: " + DateFormat.getDateTimeInstance(DateFormat.MEDIUM, DateFormat.SHORT).format(Date((it * 1000).toLong())) },
            ).forEach {
                Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                job.skipSecondsLeft(now)?.let { left ->
                    OutlinedButton(
                        onClick = { hub.skipSource(job) },
                        enabled = left > 0 && busy == null,
                        modifier = Modifier.heightIn(min = Target),
                    ) {
                        Icon(Icons.AutoMirrored.Filled.ArrowForward, contentDescription = null, Modifier.size(18.dp))
                        Text(
                            when {
                                busy == RowBusy.Skipping -> "Requesting source switch…"
                                left > 0 -> "Use next source (${left}s)"
                                else -> "Switching source…"
                            },
                            Modifier.padding(start = 6.dp),
                        )
                    }
                }
                if (job.canDismiss) {
                    if (job.canRetry) OutlinedButton(
                        onClick = { hub.retry(job) }, enabled = busy == null, modifier = Modifier.heightIn(min = Target),
                    ) {
                        Icon(Icons.Default.Refresh, contentDescription = null, Modifier.size(18.dp))
                        Text(if (busy == RowBusy.Retrying) "Retrying…" else "Try again", Modifier.padding(start = 6.dp))
                    }
                    OutlinedButton(
                        onClick = onDismiss, enabled = busy == null,
                        modifier = Modifier.heightIn(min = Target).semantics { contentDescription = "Dismiss ${job.title}" },
                    ) {
                        Icon(Icons.Default.Delete, contentDescription = null, Modifier.size(18.dp))
                        Text(if (busy == RowBusy.Dismissing) "Dismissing…" else "Dismiss", Modifier.padding(start = 6.dp))
                    }
                }
            }
        }
    }
}

/** The bar scales with the figure and the percentage is also written out, so it never depends on the bar being seen. */
@Composable
private fun Progress(p: app.discair.model.LiveProgress) {
    val percent = p.percent
    Column(Modifier.padding(top = 4.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
        if (percent == null) LinearProgressIndicator(
            progress = { 0f }, modifier = Modifier.fillMaxWidth().semantics { contentDescription = "Download progress unavailable" },
            color = Ink.Accent, trackColor = Ink.Edge,
        ) else LinearProgressIndicator(
            progress = { (percent / 100.0).toFloat() },
            modifier = Modifier.fillMaxWidth().clearAndSetSemantics { contentDescription = "Download progress ${percent.roundToInt()} percent" },
            color = Ink.Accent, trackColor = Ink.Edge,
        )
        Text(
            if (percent == null) "Progress unavailable" else "${percent.roundToInt()}% complete",
            style = MaterialTheme.typography.bodySmall,
        )
        Text(formatSpeed(p.speedBytesPerSecond), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        val total = formatBytes(p.totalSizeBytes)
        val left = formatBytes(p.remainingSizeBytes)
        if (total != null && left != null) {
            Text("Total $total · $left remaining", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Text(
            if (p.remainingTracks == null) "Tracks remaining unavailable"
            else "${p.remainingTracks} of ${p.totalTracks ?: "?"} tracks remaining",
            style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun statusIcon(job: AcquisitionJob): androidx.compose.ui.graphics.vector.ImageVector = when (job.info.tone) {
    Tone.Ok -> Icons.Default.Check
    Tone.Error -> Icons.Default.Warning
    Tone.Caution -> Icons.Default.Info
    Tone.Muted -> Icons.Default.Close
    Tone.Active -> Icons.Default.Refresh
}

private fun toneColor(tone: Tone): Color = when (tone) {
    Tone.Ok -> Ink.Ok
    Tone.Error -> Ink.ChartRedText
    Tone.Caution -> Ink.Caution
    Tone.Active -> Ink.Accent
    Tone.Muted -> Ink.TextMuted
}
