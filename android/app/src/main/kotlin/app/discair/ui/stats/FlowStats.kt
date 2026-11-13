package app.discair.ui.stats

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import app.discair.ui.common.Target
import app.discair.ui.common.flowCard
import app.discair.ui.theme.LocalPalette

/*
 * Flow's (Layout.Flow) Library stats pieces. Mockup: flow/downloads-stats-server, frame 2. StatsScreen reaches these behind isFlow(); the ranges
 * (CoverStackStatsRules.rangeLabel words), the series and the charts are the Standard page's, drawn with the theme's chart roles (Charts.kt).
 */

/** The range chips in one scrolling row: 34dp capsules, the selected one filled with the text colour (flow.css `.chip`, `.chip.on`). */
@Composable
internal fun FlowRanges(selected: StatsRange, onSelect: (StatsRange) -> Unit) {
    val p = LocalPalette.current
    Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
        StatsRange.entries.forEach { r ->
            val on = selected == r
            Box(
                Modifier.heightIn(min = Target).clickable(role = Role.RadioButton, onClick = { onSelect(r) }).semantics { this.selected = on },
                contentAlignment = Alignment.Center,
            ) {
                Box(Modifier.height(34.dp).background(if (on) p.text else p.raised, RoundedCornerShape(17.dp)).padding(horizontal = 14.dp), contentAlignment = Alignment.Center) {
                    Text(CoverStackStatsRules.rangeLabel(r), color = if (on) p.ink else p.text, maxLines = 1, style = MaterialTheme.typography.labelLarge.copy(fontSize = 14.sp, fontWeight = FontWeight.Medium))
                }
            }
        }
    }
}

/** "1,241 albums on 12 Nov 2026": the numeral in Inter 700 28/32 (flow.css `.numeral`) and the unit muted beside it. */
@Composable
internal fun FlowFigure(figure: String, unit: String) {
    val p = LocalPalette.current
    Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(
            figure, color = p.text, style = MaterialTheme.typography.headlineLarge.copy(fontSize = 28.sp, lineHeight = 32.sp, fontWeight = FontWeight.Bold, letterSpacing = (-0.02).em),
            modifier = Modifier.semantics { contentDescription = "$figure $unit" },
        )
        Text(unit, color = p.textMuted, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(bottom = 4.dp))
    }
}

/** A white card of radius 16 at level 1 depth with 14dp inside (flow.css `.card`). */
@Composable
internal fun FlowStatsCard(content: @Composable () -> Unit) {
    Column(Modifier.fillMaxWidth().flowCard(LocalPalette.current).padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) { content() }
}
