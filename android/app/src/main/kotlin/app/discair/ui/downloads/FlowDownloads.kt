package app.discair.ui.downloads

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.data.RowBusy
import app.discair.model.AcquisitionJob
import app.discair.model.Tone
import app.discair.ui.common.ChartRules
import app.discair.ui.common.FlowCover
import app.discair.ui.common.ReleaseEditionCovers
import app.discair.ui.common.Target
import app.discair.ui.theme.accentText
import app.discair.ui.common.flowCard
import app.discair.ui.player.PlayerIcons
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.Palette

/*
 * Flow's (Layout.Flow) Downloads cards. Mockup: flow/downloads-stats-server, frame 1. DownloadsScreen reaches this behind isFlow(); the
 * stream, the rows' order, the words (CoverStackDownloadsRules) and every action (Play, Use next source, Try again, Dismiss) are the Standard page's.
 */

/** The look of a card's action: flow.css `.btn.sm` is `raised` with the text colour; `.p` the accent, `.t` an accent label, `.d` a danger label. */
enum class FlowActionKind { Neutral, Primary, Tonal, Danger }

/** One download as a white card: cover, title, line and state, the four-step tracker, then the action row. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun FlowJob(
    job: AcquisitionJob, busy: RowBusy?, secondsLeft: Int?, canPlay: Boolean, arrivedAt: String?, openAlbum: () -> Unit,
    onPlay: () -> Unit, onSkip: () -> Unit, onRetry: () -> Unit, onDismiss: () -> Unit,
) {
    val p = LocalPalette.current
    val info = job.info
    val step = DownloadsRules.step(job.status)
    Column(
        Modifier.padding(start = 16.dp, end = 16.dp, bottom = 14.dp).fillMaxWidth().flowCard(p).padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            FlowCover(job.artistName, job.albumName, null, Modifier.size(64.dp).clickable(role = Role.Button, onClickLabel = "Open album", onClick = openAlbum))
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(
                    job.title, color = p.text, maxLines = 2, overflow = TextOverflow.Ellipsis,
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold, fontSize = 15.sp, lineHeight = 20.sp),
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
        FlowTracker(step.current, step.failed)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(0.dp)) {
            if (job.isImported && !job.isSong) Action("Play", PlayerIcons.Play, FlowActionKind.Primary, enabled = canPlay, onClick = onPlay)
            secondsLeft?.let { left ->
                Action(
                    when {
                        busy == RowBusy.Skipping -> "Requesting source switch…"
                        left > 0 -> "Use next source (${left}s)"
                        else -> "Switching source…"
                    },
                    null, FlowActionKind.Neutral, enabled = left > 0 && busy == null, onClick = onSkip,
                )
            }
            if (job.canRetry) Action(if (busy == RowBusy.Retrying) "Trying again…" else "Try again", null, FlowActionKind.Primary, enabled = busy == null, onClick = onRetry)
            if (job.isImported && !job.isSong) Action("Open album", null, FlowActionKind.Tonal, onClick = openAlbum)
            if (job.canDismiss) Action(if (busy == RowBusy.Dismissing) "Dismissing…" else "Dismiss", null, FlowActionKind.Danger, enabled = busy == null, onClick = onDismiss)
        }
    }
}

private fun toneInk(tone: Tone, p: Palette): Color = when (tone) {
    Tone.Ok -> p.ok
    Tone.Error -> p.chartRedText
    Tone.Caution -> p.caution
    Tone.Active -> p.text
    Tone.Muted -> p.textMuted
}

/** Four 4dp lines Found, Downloading, Importing, In library; done and current ones the accent, a failed one the danger red (flow.css `.trk i`); the names under them. */
@Composable
private fun FlowTracker(current: Int, failed: Boolean, names: List<String> = listOf("Found", "Downloading", "Importing", "In library")) {
    val p = LocalPalette.current
    val stages = ChartRules.stages(current, failed, names.size)
    val line = RoundedCornerShape(2.dp)
    Column(
        Modifier.fillMaxWidth().semantics { contentDescription = names.indices.joinToString(". ") { ChartRules.stageLabel(names[it], stages[it]) } },
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            stages.forEach { stage ->
                val fill = when (stage) {
                    ChartRules.Stage.Done, ChartRules.Stage.Current -> p.accent
                    ChartRules.Stage.Failed -> p.chartRed
                    ChartRules.Stage.Pending -> p.raised
                }
                Box(Modifier.weight(1f).height(4.dp).background(fill, line))
            }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            names.forEach { name ->
                Text(name, Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis, color = p.textMuted, style = MaterialTheme.typography.labelSmall.copy(fontSize = 11.sp, lineHeight = 16.sp))
            }
        }
    }
}

/** A 34dp capsule inside a 48dp touch height, as wide as its words (flow.css `.btn.sm`). A disabled one keeps its fill with muted words. */
@Composable
private fun Action(label: String, icon: ImageVector?, kind: FlowActionKind, enabled: Boolean = true, onClick: () -> Unit) {
    val p = LocalPalette.current
    val fill = if (kind == FlowActionKind.Primary && enabled) p.accent else p.raised
    val ink = when {
        !enabled -> p.textMuted
        kind == FlowActionKind.Primary -> p.onAccent
        kind == FlowActionKind.Tonal -> p.accentText
        kind == FlowActionKind.Danger -> p.chartRedText
        else -> p.text
    }
    Box(Modifier.heightIn(min = Target).clickable(enabled = enabled, role = Role.Button, onClick = onClick), contentAlignment = Alignment.CenterStart) {
        Row(
            Modifier.height(34.dp).background(fill, RoundedCornerShape(17.dp)).padding(horizontal = 14.dp),
            horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically,
        ) {
            if (icon != null) { Icon(icon, contentDescription = null, tint = ink, modifier = Modifier.size(20.dp)); Spacer(Modifier.width(4.dp)) }
            Text(label, color = ink, maxLines = 1, style = MaterialTheme.typography.labelLarge.copy(fontSize = 14.sp, fontWeight = FontWeight.SemiBold))
        }
    }
}

/** "Dismiss all successful imports" as an accent link under the title (flow.css `.lk`). */
@Composable
internal fun FlowDismissAll(onClick: () -> Unit) {
    Box(Modifier.padding(start = 16.dp).heightIn(min = Target).clickable(role = Role.Button, onClickLabel = "Dismiss all successful imports", onClick = onClick), contentAlignment = Alignment.CenterStart) {
        Text("Dismiss all successful imports", color = LocalPalette.current.accentText, style = MaterialTheme.typography.labelLarge.copy(fontSize = 14.sp, fontWeight = FontWeight.Medium))
    }
}
