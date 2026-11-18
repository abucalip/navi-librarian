package app.discair.ui.downloads

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.data.RowBusy
import app.discair.model.AcquisitionJob
import app.discair.model.Tone
import app.discair.model.formatSpeed
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.IndexButton
import app.discair.ui.common.IndexButtonKind
import app.discair.ui.common.IndexIcons
import app.discair.ui.common.IndexLabel
import app.discair.ui.common.IndexNumeral
import app.discair.ui.common.IndexRule
import app.discair.ui.common.IndexRules
import app.discair.ui.common.IndexTracker
import app.discair.ui.common.IndexType
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.Palette

/*
 * Index's Downloads page (I6). Spec: docs/plans/INDEX_THEME.md sections 7 and 10; mockup: docs/design/index/pages/downloads-stats-server.html, frame 1.
 * DownloadsScreen reaches this behind isIndex(); the stream, the order, the actions (Play, Use next source, Try again, Dismiss) and the confirmation are the
 * Standard page's. Active, Done and Failed are tabs over the same list, counted on the phone (section 11a: served). The state is always words.
 */

/** The pure words and sorting of the page, apart from the drawing so the tests can pin them. */
object IndexDownloadsRules {
    enum class Tab(val label: String) { Active("Active"), Done("Done"), Failed("Failed") }

    /** Which tab a record sits under: a failed step is Failed, a record still moving is Active, everything else (imported, dismissed, stopped) is Done. */
    fun tabOf(job: AcquisitionJob): Tab = when {
        DownloadsRules.step(job.status).failed -> Tab.Failed
        job.isActive -> Tab.Active
        else -> Tab.Done
    }

    fun counts(jobs: List<AcquisitionJob>): Map<Tab, Int> = Tab.entries.associateWith { t -> jobs.count { tabOf(it) == t } }

    /** "Active 3", "Done 14", "Failed 1": the tab words with their counts. */
    fun tabLabels(jobs: List<AcquisitionJob>): List<String> = counts(jobs).let { c -> Tab.entries.map { "${it.label} ${c[it] ?: 0}" } }

    fun shown(jobs: List<AcquisitionJob>, tab: Tab): List<AcquisitionJob> = jobs.filter { tabOf(it) == tab }

    /** The first tab that has a record, so the page never opens on an empty tab while another has some. Active when there are none. */
    fun firstTab(jobs: List<AcquisitionJob>): Tab = Tab.entries.firstOrNull { t -> jobs.any { tabOf(it) == t } } ?: Tab.Active

    /** "01": a record's number in its tab. */
    fun number(index: Int): String = (index + 1).toString().padStart(2, '0')

    /** The big figure at the right: the percent while it is downloading ("62"), "!" when a step failed, nothing otherwise. */
    fun figure(job: AcquisitionJob): String? = when {
        DownloadsRules.step(job.status).failed -> "!"
        job.isActive -> job.progress?.percent?.let { it.coerceIn(0.0, 100.0).toInt().toString() }
        else -> null
    }

    /** "2.1 MB/s · 4 of 7 songs": the live figures under a download in progress; null when the server gave none. */
    fun progress(job: AcquisitionJob): String? {
        val p = job.progress ?: return null
        val speed = p.speedBytesPerSecond?.let { formatSpeed(it) }
        val total = p.totalTracks
        val left = p.remainingTracks
        val songs = if (total != null && left != null) "${total - left} of $total song${if (total == 1) "" else "s"}" else null
        return listOfNotNull(speed, songs).joinToString(" · ").ifEmpty { null }
    }

    /** "Bark Psychosis · Lossless": the mono line under the title. */
    fun meta(job: AcquisitionJob): String =
        listOfNotNull(job.artistName, if (job.isSong) "Song on ${job.albumName}" else null, job.qualityProfile.takeIf { it != "Not reported" }).joinToString(" · ")

    /** The tracker's four names in mono under its segments (mockup). */
    val stageNames = listOf("Found", "Loading", "Import", "Done")
}

/** One download as a numbered entry: number, 48dp cover, title, mono line, tracker with its names, the state in words, then the actions; the figure at the right. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun IndexJob(
    job: AcquisitionJob, number: String, busy: RowBusy?, secondsLeft: Int?, canPlay: Boolean, arrivedAt: String?, openAlbum: () -> Unit,
    onPlay: () -> Unit, onSkip: () -> Unit, onRetry: () -> Unit, onDismiss: () -> Unit,
) {
    val p = LocalPalette.current
    val info = job.info
    val (reached, failedAt) = GalleryDownloadsRules.tracker(job)
    Column(Modifier.fillMaxWidth().padding(horizontal = IndexRules.GUTTER.dp)) {
        Row(Modifier.fillMaxWidth().padding(vertical = 14.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(number, style = IndexType.label(), color = p.accent, maxLines = 1, modifier = Modifier.width(26.dp).padding(top = 3.dp))
            AlbumCover(job.artistName, job.albumName, null, Modifier.size(48.dp).clickable(role = Role.Button, onClickLabel = "Open album", onClick = openAlbum), rect = true)
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Text(
                            job.title, color = p.text, maxLines = 2, overflow = TextOverflow.Ellipsis, style = IndexType.rowTitle().copy(fontSize = 16.sp),
                            modifier = Modifier.clickable(role = Role.Button, onClickLabel = "Open album", onClick = openAlbum),
                        )
                        IndexLabel(IndexDownloadsRules.meta(job), maxLines = 2)
                    }
                    IndexDownloadsRules.figure(job)?.let { f ->
                        val ink = if (f == "!") p.chartRedText else p.text
                        if (f == "!") Text(f, color = ink, style = IndexType.section())
                        else IndexNumeral(f, IndexType.section(), ink)
                    }
                }
                Column(Modifier.padding(top = 2.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    IndexTracker(reached, failedAt = failedAt)
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        IndexDownloadsRules.stageNames.forEach { IndexLabel(it, Modifier.weight(1f)) }
                    }
                }
                Text(
                    listOfNotNull(info.label, IndexDownloadsRules.progress(job), arrivedAt?.takeIf { job.isImported }?.let { "arrived $it" }).joinToString(" · "),
                    color = tone(info.tone, p), style = IndexType.body(), modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
                )
                // What the server said about a problem stays: it is the reason the record needs the owner.
                listOfNotNull(job.message, job.error).forEach { Text(it, color = tone(info.tone, p), style = IndexType.body().copy(fontSize = 13.sp)) }
                FlowRow(Modifier.padding(top = 2.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (job.isImported && !job.isSong) IndexButton("Play", onPlay, icon = IndexIcons.Play, small = true, enabled = canPlay)
                    secondsLeft?.let { left ->
                        IndexButton(
                            when {
                                busy == RowBusy.Skipping -> "Requesting source switch…"
                                left > 0 -> "Use next source (${left}s)"
                                else -> "Switching source…"
                            },
                            onSkip, kind = IndexButtonKind.Ghost, small = true, enabled = left > 0 && busy == null,
                        )
                    }
                    if (job.canRetry) IndexButton(if (busy == RowBusy.Retrying) "Trying again…" else "Try again", onRetry, icon = IndexIcons.Refresh, small = true, enabled = busy == null)
                    if (job.canDismiss) IndexButton(if (busy == RowBusy.Dismissing) "Dismissing…" else "Dismiss", onDismiss, kind = IndexButtonKind.Ghost, small = true, enabled = busy == null)
                }
            }
        }
        IndexRule()
    }
}

private fun tone(tone: Tone, p: Palette): Color = when (tone) {
    Tone.Ok -> p.ok
    Tone.Error -> p.chartRedText
    Tone.Caution -> p.caution
    Tone.Active -> p.text
    Tone.Muted -> p.textMuted
}
