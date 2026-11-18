package app.discair.ui.stats

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.data.ArtistSort
import app.discair.ui.common.ChartRules
import app.discair.ui.common.IndexLabel
import app.discair.ui.common.IndexNumeral
import app.discair.ui.common.IndexRule
import app.discair.ui.common.IndexRules
import app.discair.ui.common.IndexTabs
import app.discair.ui.common.IndexType
import app.discair.ui.common.Load
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.rememberLoad
import app.discair.ui.theme.LocalPalette

/*
 * Index's Library stats pieces (I6). Spec: docs/plans/INDEX_THEME.md sections 7 and 10; mockup: docs/design/index/pages/downloads-stats-server.html, frame 2.
 * StatsScreen reaches these behind isIndex(); the ranges, the series and the charts are the Standard page's. The figures are the ones the phone can know:
 * the albums (the library list's total) and the artists (the artist list's total). The mockup's hours this month and lossless share are not served yet
 * (docs/plans/INDEX_THEME.md 11a), so they are not drawn.
 */

/** The pure words of the figures block. */
object IndexStatsRules {
    /** The figures to draw, in order: a label and the formatted number; a figure the phone does not know is left out, never shown as zero. */
    fun figures(albums: Int?, artists: Int?): List<Pair<String, String>> = listOfNotNull(
        albums?.let { "Albums" to ChartRules.formatCount(it.toDouble()) },
        artists?.let { "Artists" to ChartRules.formatCount(it.toDouble()) },
    )
}

/** The figures (frame 2): two columns, each a heavy `text` rule, the mono label and the number rolling in (motion #7). */
@Composable
internal fun IndexStatsFigures(albums: Int?) {
    val repo = LocalRepository.current
    val artists = rememberLoad("stats_artist_total") { repo.artists("", ArtistSort.Name, null, null).total }
    val figures = IndexStatsRules.figures(albums, (artists.state as? Load.Ready)?.value)
    if (figures.isEmpty()) return
    val p = LocalPalette.current
    Row(Modifier.fillMaxWidth().padding(start = IndexRules.GUTTER.dp, end = IndexRules.GUTTER.dp, top = 16.dp), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
        figures.forEach { (label, value) ->
            Column(Modifier.weight(1f).semantics(mergeDescendants = true) { contentDescription = "$label, $value" }) {
                IndexRule(heavy = true, draw = true, key = "stats-$label")
                IndexLabel(label, Modifier.padding(top = 10.dp))
                IndexNumeral(value, IndexType.numeral().copy(fontSize = 52.sp, lineHeight = 52.sp), p.text)
            }
        }
        if (figures.size == 1) Spacer(Modifier.weight(1f))
    }
}

/** The range switch: mono tabs with the moving bar. */
@Composable
internal fun IndexRanges(selected: StatsRange, onSelect: (StatsRange) -> Unit) {
    IndexTabs(StatsRange.entries.map { CoverStackStatsRules.rangeLabel(it) }, StatsRange.entries.indexOf(selected), { onSelect(StatsRange.entries[it]) }, Modifier.padding(top = 20.dp))
}

/** A stats section: 28dp above, the heavy 2dp `text` rule (drawn on arrival), 10dp, then the chart (its title is the section's). No box, no fill. */
@Composable
internal fun IndexStatsCard(key: String, content: @Composable () -> Unit) {
    Column(Modifier.fillMaxWidth().padding(horizontal = IndexRules.GUTTER.dp).padding(top = 28.dp)) {
        IndexRule(heavy = true, draw = true, key = "stats-card-$key")
        Spacer(Modifier.height(10.dp))
        Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(6.dp)) { content() }
    }
}
