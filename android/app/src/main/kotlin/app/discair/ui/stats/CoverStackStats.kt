package app.discair.ui.stats

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.ui.discover.CoverStackChip
import app.discair.ui.theme.LocalPalette

/*
 * Soft Brut's (Layout.CoverStack) Library stats pieces. Mockup: soft-brut/downloads-stats-server, frame 2. StatsScreen reaches these behind
 * isCoverStack(); the ranges, the series and the charts are the Standard page's, drawn with the theme's chart roles (Charts.kt).
 */

/** The words on the range chips: the mockup's "12 months", "5 years" and "All time", with the 3-month range kept. */
object CoverStackStatsRules {
    fun rangeLabel(range: StatsRange): String = when (range) {
        StatsRange.ThreeMonths -> "3 months"
        StatsRange.OneYear -> "12 months"
        StatsRange.FiveYears -> "5 years"
        StatsRange.All -> "All time"
    }
}

/** The range chips in one scrolling row, the selected one filled with the accent (mockup `.hs`). */
@Composable
internal fun CoverStackRanges(selected: StatsRange, onSelect: (StatsRange) -> Unit) {
    Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
        StatsRange.entries.forEach { r -> CoverStackChip(CoverStackStatsRules.rangeLabel(r), selected == r) { onSelect(r) } }
    }
}

/** "1,241 albums on 12 Nov 2026": the numeral in the display face (Space Grotesk 700, 28/32) and the unit muted beside it. */
@Composable
internal fun CoverStackFigure(figure: String, unit: String) {
    val p = LocalPalette.current
    Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(
            figure, color = p.text, style = MaterialTheme.typography.headlineLarge.copy(fontSize = 28.sp, lineHeight = 32.sp, fontWeight = FontWeight.Bold),
            modifier = Modifier.semantics { contentDescription = "$figure $unit" },
        )
        Text(unit, color = p.textMuted, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(bottom = 4.dp))
    }
}
