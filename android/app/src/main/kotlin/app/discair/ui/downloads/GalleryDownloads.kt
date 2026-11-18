package app.discair.ui.downloads

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
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
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.GalleryButton
import app.discair.ui.common.GalleryButtonKind
import app.discair.ui.common.GalleryIcons
import app.discair.ui.common.GalleryPrint
import app.discair.ui.common.GalleryRule
import app.discair.ui.common.GalleryRules
import app.discair.ui.common.GalleryTracker
import app.discair.ui.common.GalleryType
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.Palette

/*
 * Gallery's Downloads page (G6). Spec: docs/archive/completed/GALLERY_THEME.md sections 7 and 10; mockup: docs/design/gallery/pages/downloads-stats-server.html, frame 1.
 * DownloadsScreen reaches this behind isGallery(); the stream, the order, the actions (Play, Skip this source, Try again, Dismiss) and the
 * confirmation are the Standard page's. The state is always words; the tone colour only backs them up.
 */

/** The pure words of the page, apart from the drawing so the tests can pin them. */
object GalleryDownloadsRules {
    /** "2 in progress · 1 needs you": the catalogue line over the title. Nothing to report says so. */
    fun eyebrow(jobs: List<AcquisitionJob>): String {
        val way = jobs.count { it.isActive }
        val needs = jobs.count { DownloadsRules.step(it.status).failed }
        val parts = listOfNotNull(
            if (way > 0) "$way in progress" else null,
            if (needs > 0) "$needs need${if (needs == 1) "s" else ""} you" else null,
        )
        return if (parts.isEmpty()) "Nothing in progress" else parts.joinToString(" · ")
    }

    /** "64% · 7 of 9 songs": the live figures under a download in progress; null when the server gave none. */
    fun progress(job: AcquisitionJob): String? {
        val p = job.progress ?: return null
        val pct = p.percent?.let { "${it.toInt()}%" }
        val total = p.totalTracks
        val left = p.remainingTracks
        val songs = if (total != null && left != null) "${total - left} of $total song${if (total == 1) "" else "s"}" else null
        return listOfNotNull(pct, songs).joinToString(" · ").ifEmpty { null }
    }

    /** "Downloading · 64% · 7 of 9 songs", "In your library · arrived today": the server's status, the figures, then when an arrived record came in. */
    fun stateLine(label: String, progress: String?, arrived: String?): String =
        listOfNotNull(label, progress, arrived?.let { "arrived $it" }).joinToString(" · ")

    /** How many of the tracker's four segments are filled, and which one failed (-1 for none). A step under way counts as reached. */
    fun tracker(job: AcquisitionJob): Pair<Int, Int> {
        val step = DownloadsRules.step(job.status)
        return if (step.failed) step.current to step.current else (step.current + 1).coerceAtMost(4) to -1
    }

    val stageNames = listOf("Found", "Downloading", "Importing", "In library")
}

/** One download as a hairline-divided entry: print, work title, line and state, the tracker with its four names, then the actions. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun GalleryJob(
    job: AcquisitionJob, busy: RowBusy?, secondsLeft: Int?, canPlay: Boolean, arrivedAt: String?, openAlbum: () -> Unit,
    onPlay: () -> Unit, onSkip: () -> Unit, onRetry: () -> Unit, onDismiss: () -> Unit,
) {
    val p = LocalPalette.current
    val info = job.info
    val (reached, failedAt) = GalleryDownloadsRules.tracker(job)
    Column(Modifier.fillMaxWidth().padding(horizontal = GalleryRules.GUTTER.dp)) {
        Column(Modifier.padding(vertical = 18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                GalleryPrint(64.dp, Modifier.width(64.dp), small = true) {
                    AlbumCover(job.artistName, job.albumName, null, Modifier.fillMaxWidth().clickable(role = Role.Button, onClickLabel = "Open album", onClick = openAlbum), rect = true)
                }
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Text(
                        job.title, color = p.text, maxLines = 2, overflow = TextOverflow.Ellipsis,
                        style = GalleryType.rowWork.copy(fontSize = 19.sp, lineHeight = 22.sp),
                        modifier = Modifier.clickable(role = Role.Button, onClickLabel = "Open album", onClick = openAlbum),
                    )
                    Text(
                        CoverStackDownloadsRules.subLine(job.artistName, job.isSong, job.albumName, job.year, job.qualityProfile), color = p.textMuted,
                        maxLines = 2, overflow = TextOverflow.Ellipsis, style = GalleryType.small(),
                    )
                    Text(
                        GalleryDownloadsRules.stateLine(info.label, GalleryDownloadsRules.progress(job), arrivedAt.takeIf { job.isImported }),
                        color = tone(info.tone, p), style = GalleryType.small().copy(fontSize = 13.sp),
                        modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
                    )
                    // What the server said about a problem stays: it is the reason the record needs the owner.
                    listOfNotNull(job.message, job.error).forEach { Text(it, color = tone(info.tone, p), style = GalleryType.small().copy(fontSize = 13.sp)) }
                }
            }
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                GalleryTracker(reached, failedAt = failedAt)
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    GalleryDownloadsRules.stageNames.forEach {
                        Text(it.uppercase(), Modifier.weight(1f), maxLines = 1, color = p.textMuted, style = GalleryType.state.copy(fontSize = 10.sp, letterSpacing = 0.04.sp))
                    }
                }
            }
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                if (job.isImported && !job.isSong) GalleryButton("Play", onPlay, icon = GalleryIcons.Play, small = true, enabled = canPlay)
                secondsLeft?.let { left ->
                    GalleryButton(
                        when {
                            busy == RowBusy.Skipping -> "Requesting source switch…"
                            left > 0 -> "Skip this source (${left}s)"
                            else -> "Switching source…"
                        },
                        onSkip, kind = GalleryButtonKind.Outlined, small = true, enabled = left > 0 && busy == null,
                    )
                }
                if (job.canRetry) GalleryButton(if (busy == RowBusy.Retrying) "Trying again…" else "Try again", onRetry, icon = GalleryIcons.Refresh, small = true, enabled = busy == null)
                if (job.canDismiss) GalleryButton(if (busy == RowBusy.Dismissing) "Dismissing…" else "Dismiss", onDismiss, kind = GalleryButtonKind.Danger, small = true, enabled = busy == null)
                if (job.isImported && !job.isSong) GalleryButton("Open album", openAlbum, kind = GalleryButtonKind.Text, small = true)
            }
        }
        GalleryRule()
    }
}

private fun tone(tone: Tone, p: Palette): Color = when (tone) {
    Tone.Ok -> p.ok
    Tone.Error -> p.chartRedText
    Tone.Caution -> p.caution
    Tone.Active -> p.text
    Tone.Muted -> p.textMuted
}
