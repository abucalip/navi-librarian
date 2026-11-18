package app.discair.ui.stats

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import app.discair.ui.common.GalleryRule
import app.discair.ui.common.GalleryRules
import app.discair.ui.common.GallerySourceSwitch
import app.discair.ui.common.GalleryType
import app.discair.ui.theme.LocalPalette

/*
 * Gallery's Library stats pieces (G6). Spec: docs/archive/completed/GALLERY_THEME.md sections 5.3 and 7; mockup: docs/design/gallery/pages/downloads-stats-server.html,
 * frame 2. StatsScreen reaches these behind isGallery(); the ranges (CoverStackStatsRules words), the series and the charts are the Standard page's.
 */

/** The range switch: Fraunces words under a hairline, the chosen one underlined (section 7.2's source switch). */
@Composable
internal fun GalleryRanges(selected: StatsRange, onSelect: (StatsRange) -> Unit) {
    Column(Modifier.fillMaxWidth()) {
        GallerySourceSwitch(StatsRange.entries.map { CoverStackStatsRules.rangeLabel(it) }, StatsRange.entries.indexOf(selected), { onSelect(StatsRange.entries[it]) })
        GalleryRule(Modifier.padding(horizontal = GalleryRules.GUTTER.dp))
    }
}

/** "1,241 albums on 12 November 2026": the numeral in Fraunces 40 and the unit muted beside it. */
@Composable
internal fun GalleryFigure(figure: String, unit: String) {
    val p = LocalPalette.current
    Row(Modifier.padding(top = 6.dp), verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(figure, color = p.text, style = GalleryType.numeral, modifier = Modifier.semantics { contentDescription = "$figure $unit" })
        Text(unit, color = p.textMuted, style = GalleryType.small(), modifier = Modifier.padding(bottom = 6.dp))
    }
}

/** A stats section: a 1dp rule, 14dp, the chart (its title is the section's Fraunces heading), then 30dp of air. No box, no fill. */
@Composable
internal fun GalleryStatsCard(content: @Composable () -> Unit) {
    Column(Modifier.fillMaxWidth().padding(horizontal = GalleryRules.GUTTER.dp).padding(top = 22.dp)) {
        GalleryRule()
        Spacer(Modifier.height(14.dp))
        Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(6.dp)) { content() }
        Spacer(Modifier.height(10.dp))
    }
}
