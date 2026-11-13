package app.discair.ui.downloads

import app.discair.ui.common.ArtIcons
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.graphics.vector.ImageVector
import app.discair.data.RowBusy
import app.discair.model.AcquisitionJob
import app.discair.model.Tone
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.ChartRules
import app.discair.ui.common.CoverStackRules
import app.discair.ui.common.ReleaseEditionCovers
import app.discair.ui.common.Target
import app.discair.ui.common.coverStackFrame
import app.discair.ui.player.PlayerIcons
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.Palette

/*
 * Soft Brut's (Layout.CoverStack) Downloads cards. Mockup: soft-brut/downloads-stats-server, frame 1. DownloadsScreen reaches this behind
 * isCoverStack(); the stream, the rows' order and every action (Play, Use next source, Try again, Dismiss) are the Standard page's.
 */

/** The words on a card. */
object CoverStackDownloadsRules {
    /** "Downloading · 64% · 7 of 9 files": the server's status, the progress figures, and when an arrived record came in. */
    fun stateLine(label: String, progress: String?, arrived: String?): String = listOfNotNull(label, progress, arrived?.let { "arrived $it" }).joinToString(" · ")

    /** "Slowdive · 1995": the artist, "Song on Album" for a song, the year, then the quality when the server reported one. */
    fun subLine(artist: String, song: Boolean, album: String, year: Int?, quality: String?): String =
        listOfNotNull(artist, if (song) "Song on $album" else null, year?.toString(), quality?.takeIf { it != "Not reported" }).joinToString(" · ")
}

/** One download as an outlined card: cover, title, line and state, the four-step tracker, then the action row. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun CoverStackJob(
    job: AcquisitionJob, busy: RowBusy?, secondsLeft: Int?, canPlay: Boolean, arrivedAt: String?, openAlbum: () -> Unit,
    onPlay: () -> Unit, onSkip: () -> Unit, onRetry: () -> Unit, onDismiss: () -> Unit,
) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(CoverStackRules.radius(p).dp)
    val coverShape = RoundedCornerShape(6.dp)
    val info = job.info
    val step = DownloadsRules.step(job.status)
    Column(
        Modifier.padding(start = 16.dp, end = 16.dp + CoverStackRules.shadow(p).dp, bottom = 14.dp).fillMaxWidth()
            .coverStackFrame(shape, p).padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            AlbumCover(
                job.artistName, job.albumName, null,
                Modifier.size(64.dp).clip(coverShape).border(CoverStackRules.outline(p).dp, p.edgeStrong, coverShape).clickable(role = Role.Button, onClickLabel = "Open album", onClick = openAlbum),
                rect = true,
            )
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(
                    job.title, color = p.text, maxLines = 2, overflow = TextOverflow.Ellipsis,
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold, fontSize = 14.sp, lineHeight = 20.sp),
                    modifier = Modifier.clickable(role = Role.Button, onClickLabel = "Open album", onClick = openAlbum),
                )
                Text(
                    CoverStackDownloadsRules.subLine(job.artistName, job.isSong, job.albumName, job.year, job.qualityProfile), color = p.textMuted,
                    maxLines = 2, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall,
                )
                // The state is words; the tone colour only adds emphasis.
                Text(
                    CoverStackDownloadsRules.stateLine(info.label, DownloadsRules.progressLine(job), arrivedAt.takeIf { job.isImported }),
                    color = toneInk(info.tone, p), style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
                )
                // What the server said about a problem stays: it is the reason the record needs the owner.
                listOfNotNull(job.message, job.error).forEach { Text(it, color = p.textMuted, style = MaterialTheme.typography.bodySmall) }
            }
        }
        job.releaseGroup?.let { ReleaseEditionCovers(it) }
        CoverStackTracker(step.current, step.failed)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(0.dp)) {
            if (job.isImported && !job.isSong) Action("Play", ArtIcons.Play, filled = true, enabled = canPlay, onClick = onPlay)
            secondsLeft?.let { left ->
                Action(
                    when {
                        busy == RowBusy.Skipping -> "Requesting source switch…"
                        left > 0 -> "Use next source (${left}s)"
                        else -> "Switching source…"
                    },
                    null, enabled = left > 0 && busy == null, onClick = onSkip,
                )
            }
            if (job.canRetry) Action(if (busy == RowBusy.Retrying) "Trying again…" else "Try again", null, filled = true, enabled = busy == null, onClick = onRetry)
            if (job.isImported && !job.isSong) Action("Open album", null, onClick = openAlbum)
            if (job.canDismiss) Action(if (busy == RowBusy.Dismissing) "Dismissing…" else "Dismiss", null, danger = true, enabled = busy == null, onClick = onDismiss)
        }
    }
}

@Composable
private fun toneInk(tone: Tone, p: Palette): Color = when (tone) {
    Tone.Ok -> p.ok
    Tone.Error -> p.chartRedText
    Tone.Caution -> p.caution
    Tone.Active -> p.text
    Tone.Muted -> p.textMuted
}

/** The 10dp outlined segments Found, Downloading, Importing, In library; done and current ones are lavender, a failed one the pale red; the names are under them. */
@Composable
private fun CoverStackTracker(current: Int, failed: Boolean, names: List<String> = listOf("Found", "Downloading", "Importing", "In library")) {
    val p = LocalPalette.current
    val stages = ChartRules.stages(current, failed, names.size)
    val shape = RoundedCornerShape(3.dp)
    Column(
        Modifier.fillMaxWidth().semantics { contentDescription = names.indices.joinToString(". ") { ChartRules.stageLabel(names[it], stages[it]) } },
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            stages.forEach { stage ->
                val fill = when (stage) {
                    ChartRules.Stage.Done, ChartRules.Stage.Current -> p.accent
                    ChartRules.Stage.Failed -> p.dangerDim
                    ChartRules.Stage.Pending -> p.surface
                }
                Box(Modifier.weight(1f).height(10.dp).background(fill, shape).border(CoverStackRules.outline(p).dp, p.edgeStrong, shape))
            }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            names.forEachIndexed { i, name ->
                Text(
                    name, Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis,
                    color = if (stages[i] == ChartRules.Stage.Failed) p.chartRedText else p.textMuted,
                    style = MaterialTheme.typography.labelSmall.copy(fontSize = 11.sp, lineHeight = 16.sp),
                )
            }
        }
    }
}

/** A 36dp outlined button with a hard shadow inside a 48dp touch target, as wide as its words (mockup `.btn.sm`). */
@Composable
private fun Action(label: String, icon: ImageVector?, filled: Boolean = false, danger: Boolean = false, enabled: Boolean = true, onClick: () -> Unit) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(CoverStackRules.radius(p).dp)
    Box(Modifier.heightIn(min = Target).clickable(enabled = enabled, role = Role.Button, onClick = onClick), contentAlignment = Alignment.CenterStart) {
        val ink = if (!enabled) p.textMuted else if (danger) p.chartRedText else if (filled) p.onAccent else p.text
        Row(
            Modifier.padding(end = CoverStackRules.shadow(p).dp).height(36.dp)
                .then(if (enabled) Modifier.coverStackFrame(shape, p, if (filled) p.accent else p.surface) else Modifier.clip(shape).background(p.raised).border(CoverStackRules.outline(p).dp, p.edgeStrong, shape))
                .padding(horizontal = 12.dp),
            horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically,
        ) {
            if (icon != null) { Icon(icon, contentDescription = null, tint = ink, modifier = Modifier.size(18.dp)); Box(Modifier.width(6.dp)) }
            Text(label, color = ink, maxLines = 1, style = MaterialTheme.typography.labelLarge.copy(fontSize = 13.sp, fontWeight = FontWeight.Bold))
        }
    }
}
