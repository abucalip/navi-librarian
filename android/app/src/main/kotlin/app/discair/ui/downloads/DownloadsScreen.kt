package app.discair.ui.downloads

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
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
import androidx.compose.ui.semantics.Role
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Warning
import app.discair.ui.common.ConfirmSheet
import app.discair.ui.common.ConfirmSpec
import app.discair.ui.common.ConfirmSpecs
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import app.discair.ui.common.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import app.discair.ui.common.OutlinedButton
import androidx.compose.material3.Text
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
import app.discair.ui.common.ReleaseEditionCovers
import app.discair.ui.common.BackBar
import app.discair.ui.common.LocalAcquisitions
import app.discair.ui.common.PageHeading
import app.discair.ui.common.RowDivider
import app.discair.ui.common.Target
import app.discair.ui.common.plural
import app.discair.ui.common.routeKey
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
        val softBrut = app.discair.ui.common.isCoverStack() // Soft Brut: a cover-stack bar and title, outlined cards (CoverStackDownloads.kt)
        val flow = app.discair.ui.common.isFlow() // Flow: its own bar, large title and white cards (FlowDownloads.kt)
        if (softBrut) app.discair.ui.common.CoverStackTopBar(open.back, emptyList(), title = "Downloads")
        else if (flow) app.discair.ui.common.FlowPageBar(open.back, emptyList(), title = "Downloads")
        else BackBar(open.back)
        if (softBrut) app.discair.ui.common.CoverStackTitle("Downloads", Modifier.padding(start = 16.dp, end = 16.dp, top = 8.dp), maxLines = 1)
        else if (flow) app.discair.ui.common.FlowLargeTitle("Downloads", Modifier.padding(start = 16.dp, end = 16.dp, top = 8.dp))
        else PageHeading("Downloads", Modifier.padding(start = 16.dp, end = 16.dp), large = true)
        StatusLine(hub, jobs)
        val imported = jobs.orEmpty().count { it.isImported }
        if (imported > 0 && softBrut) app.discair.ui.discover.CoverStackLink("Dismiss all successful imports", Modifier.padding(start = 16.dp)) { confirm = Confirm.Imported(imported) }
        else if (imported > 0 && flow) FlowDismissAll { confirm = Confirm.Imported(imported) }
        else if (imported > 0) Row(
            Modifier.padding(horizontal = 16.dp, vertical = 4.dp).heightIn(min = Target)
                .clickable(role = Role.Button, onClickLabel = "Dismiss all successful imports") { confirm = Confirm.Imported(imported) },
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(app.discair.ui.player.PlayerIcons.Close, contentDescription = null, tint = Ink.Text, modifier = Modifier.size(24.dp))
            Text("Dismiss all successful imports", color = Ink.Text, modifier = Modifier.padding(start = 16.dp))
        }
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
            else -> LazyColumn(Modifier.fillMaxSize(), contentPadding = androidx.compose.foundation.layout.PaddingValues(bottom = app.discair.ui.LocalBottomClearance.current)) {
                items(jobs, key = { it.key }) { job ->
                    Column(Modifier.animateItem()) {
                        JobRow(job, hub, now, open, onDismiss = { confirm = Confirm.One(job) })
                        if (!softBrut && !flow) RowDivider()
                    }
                }
            }
        }
    }

    // Nothing is sent until the destructive button of this sheet is tapped (ConfirmSheet).
    confirm?.let { ask ->
        ConfirmSheet(
            spec = ask.spec,
            onKeep = { confirm = null },
            onConfirm = {
                confirm = null
                when (ask) {
                    is Confirm.One -> hub.dismiss(ask.job)
                    is Confirm.Imported -> hub.dismissImported()
                }
            },
        )
    }
}

private sealed class Confirm(val spec: ConfirmSpec) {
    class One(val job: AcquisitionJob) : Confirm(ConfirmSpecs.dismissJob(job.title))
    class Imported(count: Int) : Confirm(ConfirmSpecs.dismissImports(count))
}

/** One polite line: how many records, whether updates are live, and any problem reading the list. */
@Composable
private fun StatusLine(hub: AcquisitionHub, jobs: List<AcquisitionJob>?) {
    val text = when {
        hub.listProblem != null -> hub.listProblem!!
        jobs == null -> "Connecting to acquisition status…"
        jobs.isEmpty() -> "No acquisition records to show."
        else -> DownloadsRules.summary(jobs, java.time.LocalDate.now().atStartOfDay(java.time.ZoneId.systemDefault()).toEpochSecond().toDouble())
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
    val repo = app.discair.ui.common.LocalRepository.current
    val play = app.discair.ui.player.LocalPlayActions.current
    // An arrived album plays from the library: its id is looked up by artist and album name (null until found).
    val ownedId by produceState<String?>(null, job.key, job.isImported) {
        if (job.isImported && !job.isSong) value = try {
            kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
                DownloadsRules.ownedAlbumId(repo.albums(job.albumName, app.discair.data.AlbumSort.Name, null, null).items, job.artist, job.albumName)
            }
        } catch (e: kotlin.coroutines.cancellation.CancellationException) { throw e } catch (e: Exception) { null }
    }
    val openAlbum = { open.album(routeKey(job.artist, job.albumName), job.artist, job.albumName, null, job.year) }
    if (app.discair.ui.common.isCoverStack()) {
        val arrived = job.updatedAt?.let { DateFormat.getTimeInstance(DateFormat.SHORT).format(Date((it * 1000).toLong())) }
        CoverStackJob(
            job, busy, job.skipSecondsLeft(now), ownedId != null, arrived, openAlbum,
            onPlay = { ownedId?.let { play.playAlbum(it) } }, onSkip = { hub.skipSource(job) }, onRetry = { hub.retry(job) }, onDismiss = onDismiss,
        )
        return
    }
    if (app.discair.ui.common.isFlow()) {
        val arrived = job.updatedAt?.let { DateFormat.getTimeInstance(DateFormat.SHORT).format(Date((it * 1000).toLong())) }
        FlowJob(
            job, busy, job.skipSecondsLeft(now), ownedId != null, arrived, openAlbum,
            onPlay = { ownedId?.let { play.playAlbum(it) } }, onSkip = { hub.skipSource(job) }, onRetry = { hub.retry(job) }, onDismiss = onDismiss,
        )
        return
    }
    Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 16.dp)) {
        AlbumCover(job.artistName, job.albumName, null, Modifier.size(64.dp).clickable(role = Role.Button, onClick = openAlbum))
        Column(Modifier.weight(1f).padding(start = 16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(
                job.title, style = MaterialTheme.typography.titleLarge, maxLines = 2, overflow = TextOverflow.Ellipsis,
                modifier = Modifier.clickable(role = Role.Button, onClick = openAlbum),
            )
            Text(
                listOfNotNull(job.artistName, if (job.isSong) "Song on ${job.albumName}" else null, job.qualityProfile.takeIf { it != "Not reported" }).joinToString(" · "),
                style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2, overflow = TextOverflow.Ellipsis,
            )
            job.releaseGroup?.let { ReleaseEditionCovers(it) }
            // Four named steps (docs/redesign.md section 3); the words below still say the exact state.
            val step = DownloadsRules.step(job.status)
            app.discair.ui.common.StageTracker(step.current, Modifier.padding(vertical = 4.dp), failed = step.failed, progress = DownloadsRules.fill(job))
            // The icon and the words are the status; the colour only adds emphasis (rule 4).
            val info = job.info
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Icon(statusIcon(job), contentDescription = null, tint = toneColor(info.tone), modifier = Modifier.size(18.dp))
                Text(info.label, style = MaterialTheme.typography.titleMedium, color = toneColor(info.tone))
                if (job.isImported) job.updatedAt?.let {
                    Text("· arrived " + DateFormat.getTimeInstance(DateFormat.SHORT).format(Date((it * 1000).toLong())), style = MaterialTheme.typography.bodyMedium)
                }
            }
            DownloadsRules.progressLine(job)?.let {
                Text(it, style = MaterialTheme.typography.titleMedium, modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
            }
            // What the server said about a problem stays: it is the reason the record needs the owner.
            listOfNotNull(job.message, job.error).forEach {
                Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            // One action row: Play on an arrived album, Use next source while one is offered, Try again, Dismiss.
            if (job.isImported && !job.isSong) app.discair.ui.common.Button(
                onClick = { ownedId?.let { play.playAlbum(it) } },
                enabled = ownedId != null,
                modifier = Modifier.fillMaxWidth().heightIn(min = Target).padding(top = 8.dp),
            ) {
                Icon(app.discair.ui.player.PlayerIcons.Play, contentDescription = null, Modifier.size(18.dp))
                Text("Play", Modifier.padding(start = 8.dp))
            }
            job.skipSecondsLeft(now)?.let { left ->
                OutlinedButton(
                    onClick = { hub.skipSource(job) },
                    enabled = left > 0 && busy == null,
                    modifier = Modifier.fillMaxWidth().heightIn(min = Target).padding(top = 8.dp),
                ) {
                    Text(
                        when {
                            busy == RowBusy.Skipping -> "Requesting source switch…"
                            left > 0 -> "Use next source (${left}s)"
                            else -> "Switching source…"
                        },
                    )
                }
            }
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (job.canRetry) OutlinedButton(onClick = { hub.retry(job) }, enabled = busy == null, modifier = Modifier.heightIn(min = Target)) {
                    Text(if (busy == RowBusy.Retrying) "Trying again…" else "Try again")
                }
                if (job.canDismiss) androidx.compose.material3.TextButton(onClick = onDismiss, enabled = busy == null, modifier = Modifier.heightIn(min = Target)) {
                    Text(if (busy == RowBusy.Dismissing) "Dismissing…" else "Dismiss")
                }
            }
        }
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

@Composable
private fun toneColor(tone: Tone): Color = when (tone) {
    Tone.Ok -> Ink.Ok
    Tone.Error -> Ink.ChartRedText
    Tone.Caution -> Ink.Caution
    Tone.Active -> Ink.Accent
    Tone.Muted -> Ink.TextMuted
}
