package app.discair.ui.home

import androidx.compose.animation.core.Animatable
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.model.FeedbackAction
import app.discair.model.GetState
import app.discair.model.InsightCard
import app.discair.model.InsightNarrative
import app.discair.model.Pick
import app.discair.model.TasteCard
import app.discair.model.TasteCardState
import app.discair.model.TasteProfiles
import app.discair.ui.Opener
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.Button
import app.discair.ui.common.ChartState
import app.discair.ui.common.Dumbbell
import app.discair.ui.common.LineChart
import app.discair.ui.common.LocalAcquisitions
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.OutlinedButton
import app.discair.ui.common.StageTracker
import app.discair.ui.common.Target
import app.discair.ui.common.aspectSquare
import app.discair.ui.common.pageMetadata
import app.discair.ui.common.rememberAlbumYear
import app.discair.ui.common.routeKey
import app.discair.ui.discover.TasteSheet
import app.discair.ui.discover.lensName
import app.discair.ui.theme.Ink
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.MotionRole
import app.discair.ui.theme.MotionRules
import app.discair.ui.theme.MotionTokens
import app.discair.ui.theme.currentMotionFamily
import app.discair.ui.theme.discairType
import app.discair.ui.theme.rememberReducedMotion
import app.discair.ui.theme.themeShape
import app.discair.ui.theme.toTween
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.time.Instant

/** A module's card: tonal on the page, 1 dp edge, radius 20 (Day); the theme's own shape elsewhere. */
@Composable
internal fun DashCard(modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    val p = LocalPalette.current
    val shape = themeShape(20.dp)
    Column(
        modifier.fillMaxWidth().clip(shape).background(p.surface)
            .then(if (p.brutal) Modifier else Modifier.border(BorderStroke(1.dp, p.edge), shape))
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) { content() }
}

@Composable
internal fun Eyebrow(text: String) =
    Text(text.uppercase(), style = MaterialTheme.typography.labelSmall, color = Ink.TextMuted)

@Composable
internal fun ModuleTitle(text: String, action: String? = null, onAction: () -> Unit = {}) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(text, style = MaterialTheme.typography.titleLarge, modifier = Modifier.weight(1f).semantics { heading() })
        if (action != null) TextButton(onClick = onAction, Modifier.heightIn(min = Target)) { Text(action) }
    }
}

// ----- 1. hero ---------------------------------------------------------------------------------------------------

/** The last count the hero showed in this app launch; the next count-up starts here. None on first launch (no count). */
private var lastHeroCount: Int? = null

@Composable
fun HeroModule(figures: HeroFigures?, loading: Boolean) {
    val type = discairType()
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Eyebrow("Your library")
        when {
            figures != null -> {
                val shown = rememberCountUp(figures.count)
                Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        DashboardRules.formatCount(shown), style = type.displayMetric,
                        modifier = Modifier.semantics { heading(); contentDescription = "${DashboardRules.formatCount(figures.count)} albums in your library" },
                    )
                    Text("albums", style = MaterialTheme.typography.titleMedium, color = Ink.TextMuted, modifier = Modifier.padding(bottom = 8.dp))
                }
                val trend = DashboardRules.heroTrend(figures)
                val arrow = when (trend) { "Up" -> "▲"; "Down" -> "▼"; else -> "●" }
                Text(
                    "$arrow ${DashboardRules.heroSentence(figures)}", style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.semantics { contentDescription = "$trend. ${DashboardRules.heroSentence(figures)}" },
                )
            }
            loading -> Text("Counting your albums…", style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted)
            else -> Text(
                "The album count is not available right now. Pull down to try again.",
                style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted,
            )
        }
    }
}

/** Counts up from the last shown value over `emphasis`; no count on first launch, and none when motion is reduced. */
@Composable
private fun rememberCountUp(target: Int): Int {
    val reduced = rememberReducedMotion()
    val from = lastHeroCount
    val progress = remember(target) { Animatable(if (reduced || from == null || from == target) 1f else 0f) }
    val timing = MotionRules.timing(MotionTokens.EMPHASIS_MS, MotionRole.Arrive, currentMotionFamily(), reduced)
    LaunchedEffect(target) {
        if (progress.value < 1f) progress.animateTo(1f, timing.toTween())
        lastHeroCount = target
    }
    val start = from ?: target
    return (start + (target - start) * progress.value).toInt()
}

// ----- 2. stat row -----------------------------------------------------------------------------------------------

@Composable
private fun StatCard(label: String, value: String?, unit: String, line: String, modifier: Modifier = Modifier, onClick: (() -> Unit)? = null) {
    val type = MaterialTheme.typography
    DashCard(
        modifier.then(if (onClick != null) Modifier.clickable(role = Role.Button, onClick = onClick) else Modifier),
    ) {
        Eyebrow(label)
        if (value != null) Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(value, style = type.headlineMedium)
            Text(unit, style = type.bodyMedium, color = Ink.TextMuted, modifier = Modifier.padding(bottom = 2.dp))
        } else Text("—", style = type.headlineMedium, modifier = Modifier.semantics { contentDescription = "$label: not available" })
        Text(line, style = type.bodySmall, color = Ink.TextMuted)
    }
}

/** Listens come from the taste body (D2). Never played has no source on Android, so it says so; Waiting is today's picks. */
@Composable
fun StatRow(listens: ListensFigures?, listensLoaded: Boolean, waiting: WaitingFigures?, wide: Boolean, onWaiting: () -> Unit) {
    val cards: List<@Composable (Modifier) -> Unit> = listOf(
        { m ->
            if (listens != null) StatCard(
                "Listens · 7 days", DashboardRules.formatCount(listens.last7), "plays", DashboardRules.listensChange(listens), m,
            ) else StatCard("Listens · 7 days", null, "", if (listensLoaded) DashboardRules.NOT_AVAILABLE else "Loading…", m)
        },
        { m -> StatCard("Never played", null, "", DashboardRules.NOT_AVAILABLE, m) },
        { m ->
            if (waiting != null) StatCard(
                "Waiting", DashboardRules.formatCount(waiting.picks), if (waiting.picks == 1) "pick" else "picks",
                if (waiting.arrived == 0) "No arrivals yet" else "${waiting.arrived} arrived", m, onWaiting,
            ) else StatCard("Waiting", null, "", "Loading…", m)
        },
    )
    if (wide) Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(16.dp)) { cards.forEach { it(Modifier) } }
    else LazyRow(contentPadding = PaddingValues(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        items(cards.size) { i -> cards[i](Modifier.width(168.dp)) }
    }
}

// ----- 3. today's pick -------------------------------------------------------------------------------------------

@Composable
fun TodaysPick(items: List<Pick>, open: Opener, onFeedback: (FeedbackAction, Pick) -> Unit) {
    val pager = rememberPagerState { items.size }
    HorizontalPager(pager, Modifier.fillMaxWidth(), contentPadding = PaddingValues(horizontal = 16.dp), pageSpacing = 8.dp) { page ->
        PickCard(items[page], page, items.size, open, onFeedback)
    }
}

@Composable
private fun PickCard(pick: Pick, page: Int, count: Int, open: Opener, onFeedback: (FeedbackAction, Pick) -> Unit) {
    val hub = LocalAcquisitions.current
    val p = LocalPalette.current
    var saved by remember(pick) { mutableStateOf(false) }
    var menu by remember(pick) { mutableStateOf(false) }
    val year = rememberAlbumYear(pick.artist, pick.album, pick.year)
    val get = hub.getState(pick.artist, pick.album)
    DashCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                "TODAY'S PICK", style = MaterialTheme.typography.labelSmall,
                modifier = Modifier.background(p.raised).padding(horizontal = 8.dp, vertical = 4.dp),
            )
            Box(Modifier.weight(1f))
            Text(
                "${page + 1} / $count", style = MaterialTheme.typography.labelMedium, color = Ink.TextMuted,
                modifier = Modifier.semantics { contentDescription = "Pick ${page + 1} of $count" },
            )
        }
        Row(
            Modifier.fillMaxWidth().clickable(role = Role.Button) {
                open.album(routeKey(pick.artist, pick.album), pick.artist, pick.album, null, pick.year)
            },
            horizontalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            AlbumCover(pick.artist, pick.album, null, Modifier.size(112.dp).aspectSquare())
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(pick.album, style = MaterialTheme.typography.headlineMedium, maxLines = 2, overflow = TextOverflow.Ellipsis)
                Text(
                    pick.artist + (year?.let { " · $it" } ?: ""), style = MaterialTheme.typography.bodyLarge,
                    color = Ink.TextMuted, maxLines = 2, overflow = TextOverflow.Ellipsis,
                )
                val tags = (pick.genres.filter { it.isNotBlank() }.take(1) + "not in your library").joinToString(" · ")
                Text(tags, style = MaterialTheme.typography.bodySmall, color = Ink.TextMuted)
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
            val busy = get is GetState.Pending || get is GetState.Requested
            Button(
                onClick = { hub.getAlbum(pick.artist, pick.album, pageMetadata(pick.artist, pick.album, pick.year, pick.releaseGroupMbid)) },
                Modifier.weight(1f).heightIn(min = Target), enabled = !busy,
            ) {
                Text(
                    when (get) {
                        GetState.Pending -> "Requesting…"
                        is GetState.Requested -> "Requested"
                        is GetState.Failed -> "Try again"
                        GetState.Idle -> "Get album"
                    },
                )
            }
            OutlinedButton(
                onClick = { saved = true; onFeedback(FeedbackAction.Save, pick) }, Modifier.heightIn(min = Target), enabled = !saved,
            ) { Text(if (saved) "Saved" else "Save") }
            Box {
                IconButton(onClick = { menu = true }, Modifier.size(Target)) {
                    Icon(Icons.Default.MoreVert, contentDescription = "More for ${pick.album}")
                }
                DropdownMenu(menu, onDismissRequest = { menu = false }) {
                    DropdownMenuItem(text = { Text("Not this album") }, onClick = { menu = false; onFeedback(FeedbackAction.Dismiss, pick) })
                    DropdownMenuItem(text = { Text("Never suggest artist") }, onClick = { menu = false; onFeedback(FeedbackAction.DismissArtist, pick) })
                }
            }
        }
        if (get is GetState.Failed) Text(get.message, style = MaterialTheme.typography.bodySmall, color = p.chartRedText)
    }
}

// ----- 4. arrivals -----------------------------------------------------------------------------------------------

@Composable
fun ArrivalsModule(rows: List<ArrivalRow>, open: Opener, onAll: () -> Unit) {
    DashCard {
        ModuleTitle("Arrivals", "All downloads", onAll)
        rows.forEachIndexed { i, row ->
            if (i > 0) Box(Modifier.fillMaxWidth().size(1.dp).background(Ink.Edge))
            val job = row.job
            Row(
                Modifier.fillMaxWidth().heightIn(min = 64.dp)
                    .clickable(role = Role.Button) { open.album(routeKey(job.artistName, job.albumName), job.artistName, job.albumName, null, job.year) },
                horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.CenterVertically,
            ) {
                AlbumCover(job.artistName, job.albumName, null, Modifier.size(56.dp).aspectSquare())
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(job.title, style = MaterialTheme.typography.titleMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text(
                        row.detail, style = MaterialTheme.typography.bodySmall,
                        color = if (row.failed) LocalPalette.current.chartRedText else Ink.TextMuted, maxLines = 2, overflow = TextOverflow.Ellipsis,
                    )
                    if (row.stage < 4 || row.failed) StageTracker(row.stage, failed = row.failed)
                }
            }
        }
    }
}

// ----- 5. taste --------------------------------------------------------------------------------------------------

@Composable
fun TasteModule(profiles: TasteProfiles?, loaded: Boolean) {
    var sheet by remember { mutableStateOf(false) }
    val state = TasteCard.state(profiles)
    DashCard {
        val label = (state as? TasteCardState.Ready)?.let { TasteCard.windowLabel(it.headline.window, profiles?.recentDays ?: 90) }
        Eyebrow("Your taste" + (label?.let { " · last $it" } ?: ""))
        when (state) {
            TasteCardState.Empty -> Text(
                if (loaded) "Taste needs listening history." else "Reading your saved profile.",
                style = discairType().headlineSentence,
            )
            is TasteCardState.Thin -> {
                Text("Still getting to know you.", style = discairType().headlineSentence)
                Text(
                    "${state.have} of ${state.need} listens so far. A shift is named only once there are enough.",
                    style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted,
                )
            }
            is TasteCardState.Ready -> {
                // The server's sentence, as sent.
                Text(state.headline.text, style = discairType().headlineSentence)
                val rows = DashboardRules.tasteRows(profiles)
                if (rows.isNotEmpty()) Dumbbell("Shares of your listening", "Share of listens, before and now", rows)
                Text(
                    "${DashboardRules.formatCount(state.windowListens)} listens against ${DashboardRules.formatCount(state.allTimeListens)} overall",
                    style = MaterialTheme.typography.bodySmall, color = Ink.TextMuted,
                )
            }
        }
        if (state !is TasteCardState.Empty) TextButton(onClick = { sheet = true }, Modifier.heightIn(min = Target)) { Text("Details") }
    }
    if (sheet && profiles != null) TasteSheet(profiles) { sheet = false }
}

// ----- 6. insight ------------------------------------------------------------------------------------------------

@Composable
fun InsightModule(card: InsightCard, open: Opener) {
    var why by remember(card.id) { mutableStateOf(false) }
    DashCard {
        Eyebrow(lensName(card.kind))
        Text(card.title, style = MaterialTheme.typography.titleLarge)
        card.subject.artist?.let { Text(it, style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted) }
        if (card.body.isNotEmpty()) Text(card.body, style = MaterialTheme.typography.bodyMedium)
        if (why) Text(InsightNarrative.why(card), style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            val artist = card.subject.artist
            val title = card.subject.title
            if (artist != null && title != null) Button(
                onClick = { open.album(routeKey(artist, title), artist, title, null, card.subject.year) }, Modifier.heightIn(min = Target),
            ) { Text("Open album") }
            OutlinedButton(onClick = { why = !why }, Modifier.heightIn(min = Target)) { Text(if (why) "Hide why" else "Why?") }
        }
    }
}

// ----- 7. library in numbers -------------------------------------------------------------------------------------

@Composable
fun LibraryNumbers(read: LibraryRead?, loading: Boolean, now: Instant) {
    val points = if (read == null) null else DashboardRules.growth(read, now)
    DashCard {
        ModuleTitle("Library in numbers")
        LineChart(
            title = "Albums over the last 12 months",
            subtitle = points?.let { DashboardRules.growthSubtitle(it, now) } ?: "Albums at the end of each month",
            points = points.orEmpty(),
            state = DashboardRules.growthState(points, loading),
        )
    }
}

// ----- 10. server ------------------------------------------------------------------------------------------------

@Composable
fun ServerRow(problem: String?) {
    val p = LocalPalette.current
    Column(Modifier.fillMaxWidth().heightIn(min = 56.dp).padding(horizontal = 16.dp), verticalArrangement = Arrangement.Center) {
        Text(DashboardRules.serverLine(problem), style = MaterialTheme.typography.titleMedium)
        Text(
            problem ?: "Downloads are reading normally.", style = MaterialTheme.typography.bodySmall,
            color = if (problem != null) p.caution else Ink.TextMuted,
        )
    }
}

/** The warning banner under the top bar, as the offline banner is drawn. */
@Composable
fun DashboardBanner(text: String) {
    val p = LocalPalette.current
    Text(
        "▲ $text", style = MaterialTheme.typography.bodySmall, color = p.caution,
        modifier = Modifier.padding(horizontal = 16.dp).fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(p.cautionDim).padding(12.dp)
            .semantics { contentDescription = "Warning. $text" },
    )
}

/** Sends a pick's Save or dismissal off the main thread; a failure is silent here, the pick reappears on the next read. */
@Composable
fun rememberPickFeedback(onDismissed: (Pick) -> Unit): (FeedbackAction, Pick) -> Unit {
    val repo = LocalRepository.current
    val scope = rememberCoroutineScope()
    return { action, pick ->
        scope.launch {
            val ok = try {
                withContext(Dispatchers.IO) { repo.feedback(action, pick.artist, pick.album, pageMetadata(pick.artist, pick.album, pick.year, pick.releaseGroupMbid)) }
                true
            } catch (e: Exception) { false }
            if (ok && action != FeedbackAction.Save) onDismissed(pick)
        }
    }
}
