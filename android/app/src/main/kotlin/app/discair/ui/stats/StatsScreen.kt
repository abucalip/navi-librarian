package app.discair.ui.stats

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import app.discair.ui.common.BackBar
import app.discair.ui.common.CoverStackTitle
import app.discair.ui.common.CoverStackTopBar
import app.discair.ui.common.isCoverStack
import app.discair.ui.common.ChartState
import app.discair.ui.common.ColumnChart
import app.discair.ui.common.FilterChip
import app.discair.ui.common.Load
import app.discair.ui.common.LineChart
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.PairedBars
import app.discair.ui.common.RankedBars
import app.discair.ui.common.Target
import app.discair.ui.common.rememberLoad
import app.discair.ui.home.DashCard
import app.discair.ui.home.Inline
import app.discair.ui.theme.Ink
import app.discair.ui.theme.discairType
import java.time.Instant
import java.time.ZoneOffset

/**
 * Library stats (docs/redesign.md 8.2, mockup `stats`): range chips, the collection over time with the selected value above the
 * plot, own and play by decade, shelf life and when you listen. The library list is read once and shared by the charts.
 */
@Composable
fun StatsScreen(onBack: () -> Unit) {
    val repo = LocalRepository.current
    val now = remember { Instant.now() }
    val library = rememberLoad("stats_library") { StatsRules.read(repo) }
    val taste = rememberLoad("dashboard_taste") { repo.taste() }
    var range by rememberSaveable { mutableStateOf(StatsRange.OneYear) }
    val read = (library.state as? Load.Ready)?.value
    val tasteBody = (taste.state as? Load.Ready)?.value

    Column(Modifier.fillMaxSize()) {
        val softBrut = isCoverStack() // Soft Brut: a cover-stack bar and title, word chips and outlined cards (CoverStackStats.kt)
        if (softBrut) CoverStackTopBar(onBack, emptyList(), title = "Library stats") else BackBar(onBack)
        LazyColumn(
            Modifier.fillMaxSize(),
            contentPadding = PaddingValues(start = 16.dp, end = if (softBrut) 19.dp else 16.dp, top = 0.dp, bottom = 24.dp + app.discair.ui.LocalBottomClearance.current),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            item(key = "title") {
                if (softBrut) CoverStackTitle("Library stats", maxLines = 1)
                else Text("Library stats", style = MaterialTheme.typography.headlineMedium, modifier = Modifier.semantics { heading() })
            }
            if (softBrut) item(key = "ranges") { CoverStackRanges(range) { range = it } }
            else item(key = "ranges") {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    StatsRange.entries.forEach { r ->
                        FilterChip(
                            selected = range == r, onClick = { range = r }, label = { Text(r.label) },
                            modifier = Modifier.heightIn(min = Target).semantics { contentDescription = "${r.label} range" },
                        )
                    }
                }
            }
            item(key = "collection") { CollectionCard(read, library.state is Load.Loading, library.state, library.reload, range, now) }
            item(key = "decades") { DecadesCard(read, tasteBody, library.state is Load.Loading) }
            item(key = "shelf") { ShelfLifeCard() }
            item(key = "listen") { TimeOfDayCard(tasteBody, taste.state is Load.Loading, taste.state is Load.Failed) }
        }
    }
}

@Composable
private fun CollectionCard(
    read: StatsRead?, loading: Boolean, state: Load<StatsRead>, retry: () -> Unit, range: StatsRange, now: Instant,
) {
    val series = remember(read, range) { read?.let { StatsRules.collection(it, range, now) } }
    StatsCard {
        if (state is Load.Failed) {
            Text("Collection over time", style = MaterialTheme.typography.titleLarge, modifier = Modifier.semantics { heading() })
            Inline(state.failure.message, retry)
            return@StatsCard
        }
        if (series != null) {
            val today = StatsRules.dateWords(now.atZone(ZoneOffset.UTC).toLocalDate())
            if (!isCoverStack()) Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    app.discair.ui.common.ChartRules.formatCount(series.total.toDouble()), style = discairType().displayMetric,
                    modifier = Modifier.semantics { contentDescription = "${series.total} albums on $today" },
                )
                Text("albums on $today", style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted, modifier = Modifier.padding(bottom = 8.dp))
            }
        }
        LineChart(
            title = "Collection over time",
            subtitle = series?.let { StatsRules.collectionSubtitle(it) } ?: "Albums in your library",
            points = series?.points.orEmpty(),
            state = StatsRules.collectionState(series, read, loading),
            // Soft Brut puts the figure under the eyebrow, inside the chart's frame (mockup frame 2).
            header = if (isCoverStack() && series != null) ({
                CoverStackFigure(app.discair.ui.common.ChartRules.formatCount(series.total.toDouble()), "albums on " + StatsRules.dateWords(now.atZone(ZoneOffset.UTC).toLocalDate()))
            }) else null,
        )
        if (series != null) Text("Touch and drag the chart to read a date.", style = MaterialTheme.typography.bodySmall, color = Ink.TextMuted)
    }
}

@Composable
private fun DecadesCard(read: StatsRead?, taste: app.discair.model.TasteResponse?, loading: Boolean) {
    val shares = remember(read, taste) { StatsRules.decades(read, taste?.profiles) }
    StatsCard {
        val title = "Own and play, by decade"
        when {
            loading -> RankedBars(title, "Share of the albums you own", emptyList(), state = ChartState.Loading)
            shares == null -> RankedBars(
                title, "Share of albums against share of listens",
                emptyList(), state = ChartState.Insufficient("No album in the library has a release year yet."),
            )
            shares.hasListens -> PairedBars(
                title, StatsRules.decadesSubtitle(shares, taste?.profiles?.recentDays ?: 90), shares.rows, "Albums you own", "Listens",
            )
            else -> RankedBars(title, StatsRules.decadesSubtitle(shares, 0), StatsRules.ownedRanked(shares))
        }
    }
}

@Composable
private fun ShelfLifeCard() {
    StatsCard {
        // No Android source for last-played dates, so the chart says so instead of drawing zeros; no button is offered.
        ColumnChart(
            "Shelf life", "Albums by time since the last play", emptyList(),
            state = ChartState.Unavailable(StatsRules.SHELF_LIFE_UNAVAILABLE),
        )
    }
}

@Composable
private fun TimeOfDayCard(taste: app.discair.model.TasteResponse?, loading: Boolean, failed: Boolean) {
    val points = remember(taste) { StatsRules.timeOfDay(taste?.timeOfDay) }
    StatsCard {
        ColumnChart(
            "When you listen", StatsRules.timeOfDaySubtitle(taste?.timeOfDayZone ?: "UTC"), points.orEmpty(),
            state = if (failed) ChartState.Unavailable("The taste profile could not be read.") else StatsRules.timeOfDayState(points, loading),
        )
    }
}

/** A stats card: the Standard dashboard card, or Soft Brut's outlined one. */
@Composable
private fun StatsCard(content: @Composable () -> Unit) {
    if (isCoverStack()) app.discair.ui.discover.CoverStackCardBox(content = content) else DashCard(content = content)
}
