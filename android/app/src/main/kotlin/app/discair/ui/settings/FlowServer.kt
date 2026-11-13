package app.discair.ui.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.model.ServerReads
import app.discair.ui.common.FlowGroup
import app.discair.ui.common.FlowSmallButton
import app.discair.ui.common.Load
import app.discair.ui.common.flowCard
import app.discair.ui.home.Inline
import app.discair.ui.home.Muted
import app.discair.ui.player.PlayerIcons
import app.discair.ui.theme.LocalPalette
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/*
 * Flow's (Layout.Flow) Server page. Mockup: flow/downloads-stats-server, frame 3. ServerScreen reaches this behind isFlow(); the reads, the
 * words and the tones are ServerRules' (ServerModel.kt), unchanged.
 */

/** The summary card, the services card and the activity card, under a bar and a large title. [reload] is "Check now". */
@Composable
internal fun FlowServer(state: Load<ServerReads>, reload: () -> Unit, onBack: () -> Unit) {
    FlowSettingsColumn {
        FlowSettingsHead("Server", onBack)
        when (state) {
            Load.Loading -> Muted("Checking the services…")
            is Load.Failed -> Inline(state.failure.message, reload)
            is Load.Ready -> {
                val zone = remember { ZoneId.systemDefault() }
                val clock = DateTimeFormatter.ofPattern("HH:mm").format(Instant.ofEpochMilli(state.value.checkedAtMillis).atZone(zone))
                val view = remember(state.value) { ServerRules.build(state.value, clock) }
                Summary(view.summary, reload)
                FlowGroupEyebrow("Services")
                FlowGroup {
                    view.services.forEachIndexed { i, row ->
                        SettingsRow(PlayerIcons.Server, row.name, row.status.word, stateColor = toneColor(row.status.tone), onClick = null, trailing = {}, divider = i > 0)
                    }
                }
                if (view.activity.isNotEmpty()) {
                    FlowGroupEyebrow("Server activity")
                    FlowGroup {
                        view.activity.forEachIndexed { i, row ->
                            // A warning or a failure says its word first; a finished job shows only its line (mockup).
                            val calm = row.status.tone == ServerTone.Success || row.status.tone == ServerTone.Neutral
                            val line = if (calm) row.line else "${row.status.word}. ${row.line}"
                            SettingsRow(PlayerIcons.Wave, row.name, line, stateColor = if (calm) Color.Unspecified else toneColor(row.status.tone), onClick = null, trailing = {}, divider = i > 0)
                        }
                    }
                }
            }
        }
    }
}

/** "One service needs attention", when it was checked, and Check now (mockup: a white card with the icon, two lines and a capsule). */
@Composable
private fun Summary(summary: ServerSummary, reload: () -> Unit) {
    val p = LocalPalette.current
    Row(
        Modifier.padding(horizontal = 16.dp).fillMaxWidth().flowCard(p).padding(start = 14.dp, top = 12.dp, bottom = 12.dp, end = 8.dp).semantics { liveRegion = LiveRegionMode.Polite },
        horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(if (summary.tone == ServerTone.Success) Icons.Default.Check else PlayerIcons.Info, contentDescription = null, tint = toneColor(summary.tone), modifier = Modifier.size(24.dp))
        Column(Modifier.weight(1f)) {
            Text(summary.title, color = p.text, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 15.sp, lineHeight = 20.sp))
            Text(summary.detail, color = p.textMuted, style = MaterialTheme.typography.bodySmall.copy(fontSize = 12.sp, lineHeight = 18.sp))
        }
        FlowSmallButton("Check now", null, false, "Check the services again", onClick = reload)
    }
}
