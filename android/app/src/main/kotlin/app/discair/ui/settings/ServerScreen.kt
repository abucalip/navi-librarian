package app.discair.ui.settings

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import app.discair.ui.common.BackBar
import app.discair.ui.common.Load
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.RowDivider
import app.discair.ui.common.Target
import app.discair.ui.common.rememberLoad
import app.discair.ui.home.Eyebrow
import app.discair.ui.home.Inline
import app.discair.ui.home.Muted
import app.discair.ui.theme.Ink
import app.discair.ui.theme.LocalPalette
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/** The glyph that goes with a tone: the words carry the state, the glyph and the tone only back them up. */
internal fun toneGlyph(tone: ServerTone): String = when (tone) {
    ServerTone.Success -> "✓"
    ServerTone.Warning -> "▲"
    ServerTone.Danger -> "✕"
    ServerTone.Info -> "ⓘ"
    ServerTone.Neutral -> "–"
}

@Composable
internal fun toneColor(tone: ServerTone): Color {
    val p = LocalPalette.current
    return when (tone) {
        ServerTone.Success -> p.ok
        ServerTone.Warning -> p.caution
        ServerTone.Danger -> p.chartRedText
        ServerTone.Info -> p.info
        ServerTone.Neutral -> p.textMuted
    }
}

@Composable
private fun toneBackground(tone: ServerTone): Color {
    val p = LocalPalette.current
    return when (tone) {
        ServerTone.Success -> p.okDim
        ServerTone.Warning -> p.cautionDim
        ServerTone.Danger -> p.dangerDim
        ServerTone.Info -> p.infoDim
        ServerTone.Neutral -> p.raised
    }
}

/** The state of one row: glyph and word, in the tone's colour. */
@Composable
internal fun StatusLabel(status: StatusWord, modifier: Modifier = Modifier) {
    Text(
        "${toneGlyph(status.tone)} ${status.word}", modifier, style = MaterialTheme.typography.bodyMedium, color = toneColor(status.tone),
    )
}

/**
 * The Server page (docs/redesign.md 8.2, frame 3 of `downloads-settings-server`): a summary card, the connected services with
 * their state words, and server activity. Read only on the phone: addresses are edited in the existing setup flow.
 * [navidromeDirect] is the phone's own check of Navidrome, kept when the Librarian does not answer.
 */
@Composable
fun ServerScreen(navidromeDirect: Boolean?, onBack: () -> Unit) {
    val repo = LocalRepository.current
    val reads = rememberLoad("server_reads", navidromeDirect) { repo.serverReads(navidromeDirect) }
    // Soft Brut draws its own page (CoverStackServer.kt); the reads and the words are shared.
    if (app.discair.ui.common.isCoverStack()) { CoverStackServer(reads.state, reads.reload, onBack); return }
    Column(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.weight(1f)) { BackBar(onBack) }
            IconButton(onClick = reads.reload, Modifier.size(Target)) {
                Text("↻", style = MaterialTheme.typography.titleLarge, modifier = Modifier.semantics { contentDescription = "Check again" })
            }
        }
        Text(
            "Server", style = MaterialTheme.typography.headlineMedium,
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp).semantics { heading() },
        )
        when (val state = reads.state) {
            Load.Loading -> Muted("Checking the services…")
            is Load.Failed -> Inline(state.failure.message, reads.reload)
            is Load.Ready -> {
                val zone = remember { ZoneId.systemDefault() }
                val clock = DateTimeFormatter.ofPattern("HH:mm").format(Instant.ofEpochMilli(state.value.checkedAtMillis).atZone(zone))
                val view = remember(state.value) { ServerRules.build(state.value, clock) }
                ServerBody(view)
            }
        }
    }
}

@Composable
internal fun ServerBody(view: ServerView) {
    LazyColumn(
        Modifier.fillMaxSize(),
        contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 24.dp + app.discair.ui.LocalBottomClearance.current),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        item(key = "summary") { SummaryCard(view.summary) }
        item(key = "services-head") { Box(Modifier.padding(top = 24.dp, bottom = 8.dp)) { Eyebrow("Services") } }
        items(view.services.size, key = { view.services[it].id.name }) { i ->
            val row = view.services[i]
            if (i > 0) RowDivider()
            StatusRow(row.name, row.role, row.status)
        }
        if (view.activity.isNotEmpty()) {
            item(key = "activity-head") { Box(Modifier.padding(top = 24.dp, bottom = 8.dp)) { Eyebrow("Server activity") } }
            items(view.activity.size, key = { view.activity[it].id }) { i ->
                val row = view.activity[i]
                if (i > 0) RowDivider()
                StatusRow(row.name, row.line, row.status)
            }
        }
    }
}

@Composable
private fun SummaryCard(summary: ServerSummary) {
    Row(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(20.dp)).background(toneBackground(summary.tone)).padding(16.dp)
            .semantics { liveRegion = LiveRegionMode.Polite },
        horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(toneGlyph(summary.tone), style = MaterialTheme.typography.headlineMedium, color = toneColor(summary.tone))
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(summary.title, style = app.discair.ui.theme.discairType().headlineSentence, color = Ink.Text)
            Text(summary.detail, style = MaterialTheme.typography.bodyMedium, color = Ink.Text)
        }
    }
}

@Composable
private fun StatusRow(name: String, line: String, status: StatusWord) {
    Row(
        Modifier.fillMaxWidth().heightIn(min = 64.dp).padding(vertical = 8.dp)
            .semantics(mergeDescendants = true) { contentDescription = "$name, ${status.word}. $line" },
        horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(name, style = MaterialTheme.typography.titleMedium)
            Text(line, style = MaterialTheme.typography.bodySmall, color = Ink.TextMuted)
        }
        StatusLabel(status)
    }
}
