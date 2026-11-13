package app.discair.ui.home

import app.discair.ui.common.ArtIcons
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import app.discair.data.RECENT_DAYS
import app.discair.data.recentlyAdded
import app.discair.model.LibraryAlbum
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.data.Shelves
import app.discair.model.FeedbackAction
import app.discair.model.GetState
import app.discair.model.GenreTile
import app.discair.model.InsightCard
import app.discair.model.InsightNarrative
import app.discair.model.Pick
import app.discair.model.RadioPlay
import app.discair.model.ShelfAlbum
import app.discair.ui.Opener
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.ArtistPhoto
import app.discair.ui.common.Button
import app.discair.ui.common.CoverStackDivider
import app.discair.ui.common.CoverStackRules
import app.discair.ui.common.Load
import app.discair.ui.common.LocalAcquisitions
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.OutlinedButton
import app.discair.ui.common.OutlinedIconButton
import app.discair.ui.common.Target
import app.discair.ui.common.aspectSquare
import app.discair.ui.common.coverStackFrame
import app.discair.ui.common.coverStackShadow
import app.discair.ui.common.pageMetadata
import app.discair.ui.common.rememberAlbumYear
import app.discair.ui.common.rememberLoad
import app.discair.ui.common.routeKey
import app.discair.ui.discover.lensName
import app.discair.ui.player.PlayerIcons
import app.discair.ui.theme.LocalFontPair
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.Palette
import java.time.Instant

/*
 * Soft Brut's Home (Layout.CoverStack): the owner's pick of dashboard N1 plus the Radio tile from N3. One column, in this order:
 * Today's picks (a pile of sleeves), In rotation, Arrival, Radio, Recently added, Recently played, Insight, Genres, Stat strip.
 * Spec: docs/ANDROID_ART_THEMES_PROPOSAL.md section 6.1; mockup: docs/design/android-art-themes/soft-brut/home.html.
 * Behaviour is the Home every theme has: the same data, Get, Save, the menu, the arrivals and the links.
 */

/** Everything Cover Stack's Home needs from [HomeScreen], so the screen's own loading is not repeated. */
internal class CoverStackHomeData(
    val picks: Load<List<Pick>>,
    val pickList: List<Pick>,
    val retryPicks: () -> Unit,
    val genres: Load<List<GenreTile>>,
    val hero: HeroFigures?,
    val arrivals: List<ArrivalRow>,
    val insight: InsightCard?,
    val banner: String?,
)

private val Gutter = 16.dp

@OptIn(ExperimentalFoundationApi::class)
@Composable
internal fun CoverStackHome(
    data: CoverStackHomeData, open: Opener, feedback: (FeedbackAction, Pick) -> Unit,
    onRadio: () -> Unit, onLibrary: () -> Unit, onStats: () -> Unit, onServer: () -> Unit, onDownloads: () -> Unit,
) {
    val repo = LocalRepository.current
    val recent = rememberLoad("shelf_recent_20") { repo.shelf(Shelves.Recent, 20).items }
    val frequent = rememberLoad("shelf_frequent_20") { repo.shelf(Shelves.Frequent, 20).items }
    val newest = rememberLoad("recently_added") { repo.recentlyAdded() } // the last month, newest first; the row scrolls and More lists them all
    val plays = rememberLoad("radio_plays") { repo.radioPlays() }
    val artists = HomeArtists.from((recent.state as? Load.Ready)?.value.orEmpty(), (frequent.state as? Load.Ready)?.value.orEmpty())
    val listeningKnown = recent.state !is Load.Loading && frequent.state !is Load.Loading
    val bottom = 24.dp + app.discair.ui.LocalBottomClearance.current

    val modules: List<@Composable () -> Unit> = listOf(
        { PickPile(data, open, feedback) },
        { InRotation(artists, listeningKnown, open, onLibrary) },
        { if (data.arrivals.isNotEmpty()) ArrivalCards(data.arrivals, open, onDownloads) },
        { RadioTile((plays.state as? Load.Ready)?.value, onRadio) },
        { RecentlyAddedRow(newest.state, newest.reload, open) },
        { RecentlyPlayed(recent.state, open) },
        { data.insight?.let { InsightCardView(it, open) } },
        { GenresBlock(data.genres, open) },
        { StatStrip(data.hero, onStats) },
    )
    androidx.compose.foundation.layout.BoxWithConstraints(Modifier.fillMaxWidth()) {
        val wide = maxWidth >= DashboardRules.TWO_PANE_MIN_DP.dp
        if (wide) {
            // At 840dp and wider the picks and artists take the primary pane, everything else the secondary (proposal 6.3).
            Row(Modifier.fillMaxWidth().padding(horizontal = 24.dp), horizontalArrangement = Arrangement.spacedBy(24.dp)) {
                LazyColumn(Modifier.weight(2f), contentPadding = PaddingValues(top = 8.dp, bottom = bottom), verticalArrangement = Arrangement.spacedBy(20.dp)) {
                    data.banner?.let { item(key = "banner") { ServiceBanner(it, onServer) } }
                    items(2) { modules[it]() }
                }
                LazyColumn(Modifier.weight(1f), contentPadding = PaddingValues(top = 8.dp, bottom = bottom), verticalArrangement = Arrangement.spacedBy(20.dp)) {
                    items(modules.size - 2) { modules[it + 2]() }
                }
            }
        } else {
            LazyColumn(Modifier.fillMaxWidth(), contentPadding = PaddingValues(top = 8.dp, bottom = bottom), verticalArrangement = Arrangement.spacedBy(20.dp)) {
                data.banner?.let { item(key = "banner") { ServiceBanner(it, onServer) } }
                items(modules.size) { modules[it]() }
            }
        }
    }
}

// ----- shared bits -----------------------------------------------------------------------------------------------

@Composable
internal fun Eyebrow(text: String, modifier: Modifier = Modifier) {
    Text(
        text.uppercase(), modifier, color = LocalPalette.current.textMuted, maxLines = 1,
        style = MaterialTheme.typography.labelSmall.copy(fontFamily = LocalFontPair.current.mono, fontWeight = FontWeight.Medium, fontSize = 11.sp, lineHeight = 16.sp, letterSpacing = 0.88.sp),
    )
}

/** A section heading (Space Grotesk 700 18) with its underlined ink link at the right. */
@Composable
private fun SectionHeading(title: String, link: String? = null, onLink: () -> Unit = {}) {
    val p = LocalPalette.current
    Row(Modifier.fillMaxWidth().padding(horizontal = Gutter), verticalAlignment = Alignment.CenterVertically) {
        Text(
            title, Modifier.weight(1f).semantics { heading() }, color = p.text,
            style = MaterialTheme.typography.titleLarge.copy(fontSize = 18.sp, lineHeight = 24.sp, fontWeight = FontWeight.Bold),
        )
        if (link != null) Box(Modifier.heightIn(min = Target).clickable(role = Role.Button, onClick = onLink).padding(start = 8.dp), contentAlignment = Alignment.Center) {
            Text(
                link, color = p.text, textDecoration = TextDecoration.Underline,
                style = MaterialTheme.typography.labelLarge.copy(fontSize = 13.sp, fontWeight = FontWeight.SemiBold),
            )
        }
    }
}

/** An outlined cover: 1.5dp ink outline, radius 6 (mockup `.cv`). */
@Composable
private fun OutlinedCover(artist: String, album: String, ownedPath: String?, modifier: Modifier = Modifier, radius: Int = 6) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(radius.dp)
    AlbumCover(
        artist, album, ownedPath,
        modifier.aspectSquare().clip(shape).border(CoverStackRules.outline(p).dp, p.edgeStrong, shape), rect = true,
    )
}

@Composable
private fun Muted(text: String, modifier: Modifier = Modifier) {
    Text(text, modifier.padding(horizontal = Gutter), color = LocalPalette.current.textMuted, style = MaterialTheme.typography.bodyMedium)
}

// ----- banner ----------------------------------------------------------------------------------------------------

/** The caution banner under the top bar when a service fails (mockup frame 5): outlined, caution fill, a sentence and the Server link. */
@Composable
private fun ServiceBanner(text: String, onServer: () -> Unit) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(CoverStackRules.radius(p).dp)
    Row(
        Modifier.padding(horizontal = Gutter).fillMaxWidth().clip(shape).background(p.cautionDim)
            .border(CoverStackRules.outline(p).dp, p.edgeStrong, shape).padding(horizontal = 12.dp, vertical = 10.dp)
            .semantics { contentDescription = "Warning. $text" },
        horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(ArtIcons.Info, contentDescription = null, tint = p.text, modifier = Modifier.size(20.dp))
        Text(text, Modifier.weight(1f), color = p.text, style = MaterialTheme.typography.bodySmall)
        Box(Modifier.heightIn(min = Target).clickable(role = Role.Button, onClick = onServer).padding(horizontal = 4.dp), contentAlignment = Alignment.Center) {
            Text(
                "Server", color = p.text, textDecoration = TextDecoration.Underline,
                style = MaterialTheme.typography.labelLarge.copy(fontSize = 13.sp, fontWeight = FontWeight.SemiBold),
            )
        }
    }
}

// ----- 1. today's picks ------------------------------------------------------------------------------------------

/**
 * A pile of three sleeves: the current pick in front (248dp, 4dp shadow), the next two behind it at 2.5 and 5 degrees. A swipe or a
 * tap on a back sleeve changes the pick. Below: title, "artist · year · genre", then Get album, Save and the three-dot menu.
 */
@Composable
private fun PickPile(data: CoverStackHomeData, open: Opener, feedback: (FeedbackAction, Pick) -> Unit) {
    val p = LocalPalette.current
    val picks = data.pickList
    var index by remember { mutableIntStateOf(0) }
    val at = CoverStackHomeRules.clamp(index, picks.size)
    val pick = picks.getOrNull(at)
    val loading = data.picks is Load.Loading
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(Modifier.fillMaxWidth().padding(horizontal = Gutter), verticalAlignment = Alignment.CenterVertically) {
            Eyebrow("Today's picks", Modifier.weight(1f))
            when {
                loading -> Eyebrow(CoverStackHomeRules.LOADING)
                pick != null -> Eyebrow(
                    CoverStackHomeRules.counter(at, picks.size),
                    Modifier.semantics { contentDescription = "Pick ${at + 1} of ${picks.size}" },
                )
            }
        }
        when {
            loading -> {
                Sleeves(null, emptyList(), 0, {}, {})
                Column(Modifier.padding(horizontal = Gutter), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Box(Modifier.width(120.dp).height(26.dp).background(p.raised))
                    Box(Modifier.width(210.dp).height(16.dp).background(p.raised))
                }
                PickActions(null, feedback)
            }
            data.picks is Load.Failed -> app.discair.ui.home.Inline(data.picks.failure.message, data.retryPicks)
            pick == null -> Muted(CoverStackHomeRules.NO_PICKS)
            else -> {
                val behind = CoverStackHomeRules.behind(at, picks.size).map { it to picks[it] }
                Sleeves(pick, behind, picks.size, { delta -> index = CoverStackHomeRules.step(at, picks.size, delta) }, { i -> index = i })
                val year = rememberAlbumYear(pick.artist, pick.album, pick.year)
                Column(
                    Modifier.padding(horizontal = Gutter).clickable(role = Role.Button) {
                        open.album(routeKey(pick.artist, pick.album), pick.artist, pick.album, null, pick.year)
                    },
                ) {
                    Text(
                        pick.album, color = p.text, maxLines = 2, overflow = TextOverflow.Ellipsis,
                        style = MaterialTheme.typography.headlineMedium.copy(fontSize = 26.sp, lineHeight = 30.sp, fontWeight = FontWeight.Bold),
                    )
                    Text(
                        CoverStackHomeRules.pickLine(pick.artist, year, pick.genres.firstOrNull()), color = p.textMuted,
                        style = MaterialTheme.typography.bodyMedium, maxLines = 2, overflow = TextOverflow.Ellipsis,
                    )
                }
                PickActions(pick, feedback)
            }
        }
    }
}

/** The pile itself: 262dp tall, front sleeve 248dp at the top left, back sleeves offset right and down and turned. */
@Composable
private fun Sleeves(front: Pick?, behind: List<Pair<Int, Pick>>, count: Int, onSwipe: (Int) -> Unit, onPick: (Int) -> Unit) {
    val p = LocalPalette.current
    val density = LocalDensity.current
    val shape = RoundedCornerShape(12.dp)
    val ol = CoverStackRules.outline(p).dp
    // Offsets of the sleeves (mockup `.stack .f / .b1 / .b2`): left, top.
    val spots = listOf(0 to 0, 18 to 10, 34 to 18)
    Box(
        Modifier.padding(start = 34.dp, end = 60.dp).fillMaxWidth().height(262.dp)
            .pointerInput(count) {
                if (count < 2) return@pointerInput
                var drag = 0f
                detectHorizontalDragGestures(
                    onDragStart = { drag = 0f },
                    onHorizontalDrag = { _, amount -> drag += amount },
                    onDragEnd = { CoverStackHomeRules.swipeDelta(drag / density.density)?.let(onSwipe) },
                )
            }
            .semantics { if (front != null) stateDescription = "Swipe left or right for another pick" },
    ) {
        // Back to front: the farthest sleeve first.
        for (slot in 2 downTo 1) {
            val entry = behind.getOrNull(slot - 1)
            val (left, top) = spots[slot]
            val sleeve = Modifier.offset(left.dp, top.dp).width(248.dp).aspectRatio(1f)
                .graphicsLayer { rotationZ = CoverStackHomeRules.behindTilt[slot - 1] }
            if (entry != null) {
                Box(
                    sleeve.clip(shape).border(ol, p.edgeStrong, shape)
                        .clickable(role = Role.Button, onClickLabel = "Show ${entry.second.album}") { onPick(entry.first) },
                ) { AlbumCover(entry.second.artist, entry.second.album, null, Modifier.fillMaxSize(), rect = true) }
            } else if (front == null) {
                Box(sleeve.clip(shape).background(p.raised).border(ol, p.edgeStrong, shape))
            }
        }
        val frontModifier = Modifier.width(248.dp).aspectRatio(1f)
        if (front != null) {
            Box(frontModifier.coverStackShadow(shape, p, 4f).clip(shape).border(ol, p.edgeStrong, shape)) {
                AlbumCover(front.artist, front.album, null, Modifier.fillMaxSize(), rect = true)
            }
        } else {
            Box(frontModifier.coverStackShadow(shape, p, 4f).clip(shape).background(p.raised).border(ol, p.edgeStrong, shape))
        }
    }
}

/** Get album (filled, wide), Save, and the three-dot menu with "Not this album" and "Never suggest artist". [pick] is null while loading. */
@Composable
private fun PickActions(pick: Pick?, onFeedback: (FeedbackAction, Pick) -> Unit) {
    val hub = LocalAcquisitions.current
    val p = LocalPalette.current
    var saved by remember(pick) { mutableStateOf(false) }
    var menu by remember(pick) { mutableStateOf(false) }
    val get = if (pick != null) hub.getState(pick.artist, pick.album) else GetState.Idle
    val busy = get is GetState.Pending || get is GetState.Requested
    Column(Modifier.padding(horizontal = Gutter), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
            Button(
                onClick = { pick?.let { hub.getAlbum(it.artist, it.album, pageMetadata(it.artist, it.album, it.year, it.releaseGroupMbid)) } },
                Modifier.weight(1f).heightIn(min = Target), enabled = pick != null && !busy,
            ) {
                Icon(ArtIcons.Get, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(8.dp))
                Text(
                    when (get) {
                        GetState.Pending -> "Requesting…"
                        is GetState.Requested -> "Requested"
                        is GetState.Failed -> "Try again"
                        GetState.Idle -> "Get album"
                    },
                )
            }
            OutlinedButton(onClick = { pick?.let { saved = true; onFeedback(FeedbackAction.Save, it) } }, Modifier.heightIn(min = Target), enabled = pick != null && !saved) {
                Text(if (saved) "Saved" else "Save")
            }
            Box {
                OutlinedIconButton(onClick = { menu = true }, Modifier.size(Target), enabled = pick != null) {
                    Icon(ArtIcons.More, contentDescription = "More for ${pick?.album.orEmpty()}")
                }
                DropdownMenu(menu, onDismissRequest = { menu = false }) {
                    DropdownMenuItem(text = { Text("Not this album") }, onClick = { menu = false; pick?.let { onFeedback(FeedbackAction.Dismiss, it) } })
                    DropdownMenuItem(text = { Text("Never suggest artist") }, onClick = { menu = false; pick?.let { onFeedback(FeedbackAction.DismissArtist, it) } })
                }
            }
        }
        if (get is GetState.Failed) Text(get.message, style = MaterialTheme.typography.bodySmall, color = p.chartRedText)
    }
}

// ----- 2. in rotation --------------------------------------------------------------------------------------------

/** Round artist photos, 68dp, the name beneath; "All artists" opens Library. Fewer than three artists: a sentence instead. */
@Composable
private fun InRotation(artists: List<HomeArtist>, listeningKnown: Boolean, open: Opener, onLibrary: () -> Unit) {
    val p = LocalPalette.current
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        SectionHeading("In rotation", "All artists", onLibrary)
        if (!HomeArtists.enough(artists)) {
            Muted(if (listeningKnown) HomeArtists.EMPTY_SENTENCE else "Loading…")
        } else LazyRow(contentPadding = PaddingValues(horizontal = Gutter), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            items(artists, key = { it.name }) { artist ->
                Column(
                    Modifier.width(72.dp).clip(RoundedCornerShape(8.dp)).clickable(role = Role.Button) { open.artist(artist.name, null, artist.id.ifBlank { null }, null) },
                    horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    ArtistPhoto(
                        artist.name, null,
                        Modifier.size(68.dp).clip(CircleShape).border(CoverStackRules.outline(p).dp, p.edgeStrong, CircleShape), circle = true,
                    )
                    Text(
                        artist.name, color = p.text, textAlign = TextAlign.Center, maxLines = 2, overflow = TextOverflow.Ellipsis,
                        style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.SemiBold, lineHeight = 16.sp),
                    )
                }
            }
        }
    }
}

// ----- 3. arrival ------------------------------------------------------------------------------------------------

/** Up to two cards: cover 52, title, the state in words, an outlined progress bar. Hidden when empty. */
@Composable
private fun ArrivalCards(rows: List<ArrivalRow>, open: Opener, onAll: () -> Unit) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(CoverStackRules.radius(p).dp)
    val ol = CoverStackRules.outline(p).dp
    Column(Modifier.padding(horizontal = Gutter), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        rows.forEach { row ->
            val job = row.job
            Row(
                Modifier.fillMaxWidth().coverStackFrame(shape, p)
                    .clickable(role = Role.Button, onClickLabel = "Open ${job.title}") { open.album(routeKey(job.artistName, job.albumName), job.artistName, job.albumName, null, job.year) }
                    .padding(12.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
            ) {
                OutlinedCover(job.artistName, job.albumName, null, Modifier.size(52.dp))
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Text(job.title, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 14.sp))
                    Text(
                        CoverStackHomeRules.arrivalLine(row), maxLines = 2, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall,
                        color = if (row.failed) p.chartRedText else p.textMuted,
                    )
                    Spacer(Modifier.height(4.dp))
                    val bar = RoundedCornerShape(6.dp)
                    Box(Modifier.fillMaxWidth().height(10.dp).clip(bar).background(p.surface).border(ol, p.edgeStrong, bar)) {
                        Box(
                            Modifier.fillMaxHeight().fillMaxWidth(CoverStackHomeRules.arrivalFill(row)).background(if (row.failed) p.dangerDim else p.accent)
                                .border(ol, p.edgeStrong),
                        )
                    }
                }
            }
        }
    }
}

// ----- 4. radio --------------------------------------------------------------------------------------------------

/** The tile from N3: sky fill, radio icon, "Radio", "Last heard: FIP, 08:42", a chevron. Opens Radio. */
@Composable
private fun RadioTile(plays: List<RadioPlay>?, onRadio: () -> Unit) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(14.dp)
    val line = CoverStackHomeRules.radioLine(plays)
    Row(
        Modifier.padding(horizontal = Gutter).fillMaxWidth().coverStackFrame(shape, p, fill = p.accent2)
            .clickable(role = Role.Button, onClick = onRadio).padding(12.dp)
            .semantics(mergeDescendants = true) { contentDescription = "Radio. $line" },
        horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(ArtIcons.Radio, contentDescription = null, tint = p.onAccent, modifier = Modifier.size(24.dp))
        Column(Modifier.weight(1f)) {
            Text("Radio", color = p.onAccent, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 14.sp))
            Text(line, color = p.onAccent, style = MaterialTheme.typography.bodySmall)
        }
        Icon(ArtIcons.Chevron, contentDescription = null, tint = p.onAccent, modifier = Modifier.size(24.dp))
    }
}

// ----- 5. recently added -----------------------------------------------------------------------------------------

/** The albums added in the last month in one row that slides sideways; "More" opens the whole list. */
@Composable
private fun RecentlyAddedRow(state: Load<List<LibraryAlbum>>, retry: () -> Unit, open: Opener) {
    val p = LocalPalette.current
    var all by remember { mutableStateOf(false) }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        SectionHeading("Recently added", "More") { all = true }
        when (state) {
            Load.Loading -> Muted("Loading…")
            is Load.Failed -> app.discair.ui.home.Inline(state.failure.message, retry)
            is Load.Ready -> if (state.value.isEmpty()) Muted("Nothing was added in the last $RECENT_DAYS days.") else {
                LazyRow(contentPadding = PaddingValues(horizontal = Gutter), horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                    items(state.value, key = { it.id.ifBlank { it.key } }) { album ->
                        AlbumCaption(ShelfAlbum(album.id, album.name, album.artist, "", album.year, album.artworkUrl), open, p, radius = CoverStackRules.radius(p).toInt(), modifier = Modifier.width(148.dp))
                    }
                }
                if (all) RecentlyAddedSheet(state.value, open) { all = false }
            }
        }
    }
    if (all && state !is Load.Ready) all = false
}

@Composable
private fun AlbumCaption(album: ShelfAlbum, open: Opener, p: Palette, radius: Int = 6, modifier: Modifier = Modifier) {
    Column(
        modifier.clip(RoundedCornerShape(6.dp)).clickable(role = Role.Button) { open.album(routeKey(album.artist, album.name), album.artist, album.name, album.id.ifBlank { null }, album.year) },
        verticalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        OutlinedCover(album.artist, album.name, album.artworkUrl, Modifier.fillMaxWidth(), radius)
        Spacer(Modifier.height(6.dp))
        Text(album.name, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold))
        if (album.artist.isNotBlank()) Text(album.artist, color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall)
    }
}

// ----- 6. recently played ----------------------------------------------------------------------------------------

/** A cover shelf, 112dp wide. Hidden while there is nothing played. */
@Composable
private fun RecentlyPlayed(state: Load<List<ShelfAlbum>>, open: Opener) {
    val p = LocalPalette.current
    val items = (state as? Load.Ready)?.value.orEmpty()
    if (items.isEmpty()) return
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        SectionHeading("Recently played")
        LazyRow(contentPadding = PaddingValues(horizontal = Gutter), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            items(items, key = { it.id.ifBlank { it.artist + '/' + it.name } }) { album ->
                AlbumCaption(album, open, p, modifier = Modifier.width(112.dp))
            }
        }
    }
}

// ----- 7. insight ------------------------------------------------------------------------------------------------

/** One card: cover 88, a yellow tag, the title, the sentence, the open button and Why?. */
@Composable
private fun InsightCardView(card: InsightCard, open: Opener) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(CoverStackRules.radius(p).dp)
    var why by remember(card.id) { mutableStateOf(false) }
    val artist = card.subject.artist
    val title = card.subject.title
    Column(Modifier.padding(horizontal = Gutter).fillMaxWidth().coverStackFrame(shape, p).padding(12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.Top) {
            if (artist != null && title != null) OutlinedCover(artist, title, null, Modifier.size(88.dp))
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                val tag = RoundedCornerShape(6.dp)
                Text(
                    lensName(card.kind).uppercase(), color = p.text, maxLines = 1,
                    style = MaterialTheme.typography.labelSmall.copy(fontFamily = LocalFontPair.current.mono, fontWeight = FontWeight.Medium, fontSize = 10.sp, lineHeight = 14.sp, letterSpacing = 0.7.sp),
                    modifier = Modifier.clip(tag).background(p.accent4).border(CoverStackRules.outline(p).dp, p.edgeStrong, tag).padding(horizontal = 7.dp, vertical = 2.dp),
                )
                Text(card.title, color = p.text, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 14.sp))
                val sub = listOfNotNull(artist, card.body.ifBlank { null }).joinToString(" · ")
                if (sub.isNotEmpty()) Text(sub, color = p.textMuted, style = MaterialTheme.typography.bodySmall)
            }
        }
        if (why) Text(InsightNarrative.why(card), color = p.textMuted, style = MaterialTheme.typography.bodySmall)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            if (artist != null && title != null) Button(
                onClick = { open.album(routeKey(artist, title), artist, title, null, card.subject.year) }, Modifier.weight(1f).heightIn(min = Target),
            ) { Text("Open album") }
            else Spacer(Modifier.weight(1f))
            OutlinedButton(onClick = { why = !why }, Modifier.heightIn(min = Target)) { Text(if (why) "Hide why" else "Why?") }
        }
    }
}

// ----- 8. genres -------------------------------------------------------------------------------------------------

/** The genre row shows this many, drawn at random each time Home opens (as on every theme). */
private const val GENRES_SHOWN = 6

/** Outlined pill chips, wrapping, 36dp high; a tap opens the genre. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun GenresBlock(state: Load<List<GenreTile>>, open: Opener) {
    val p = LocalPalette.current
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        SectionHeading("Genres")
        when (state) {
            Load.Loading -> Muted("Loading…")
            is Load.Failed -> Muted(state.failure.message)
            is Load.Ready -> {
                val tiles = remember(state.value) { state.value.shuffled().take(GENRES_SHOWN) }
                FlowRow(Modifier.padding(horizontal = Gutter), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    tiles.forEach { genre ->
                        Box(
                            Modifier.heightIn(min = 36.dp).clip(CircleShape).background(p.surface).border(CoverStackRules.outline(p).dp, p.edgeStrong, CircleShape)
                                .clickable(role = Role.Button) { open.genre(genre.tag, genre.name) }.padding(horizontal = 13.dp)
                                .semantics { contentDescription = "${genre.name}, " + app.discair.ui.common.plural(genre.albumCount, "album") },
                            contentAlignment = Alignment.Center,
                        ) {
                            Text(genre.name, color = p.text, maxLines = 1, style = MaterialTheme.typography.labelLarge.copy(fontSize = 13.sp, fontWeight = FontWeight.SemiBold))
                        }
                    }
                }
            }
        }
    }
}

// ----- 9. stat strip ---------------------------------------------------------------------------------------------

/** One mono line between dashed rules: albums, added this month, "Stats →". It opens Library stats. */
@Composable
private fun StatStrip(hero: HeroFigures?, onStats: () -> Unit) {
    val p = LocalPalette.current
    val cells = CoverStackHomeRules.statStrip(hero)
    Column(Modifier.padding(horizontal = Gutter).fillMaxWidth().clickable(role = Role.Button, onClickLabel = "Open Library stats", onClick = onStats)) {
        CoverStackDivider()
        Row(Modifier.fillMaxWidth().heightIn(min = Target).padding(vertical = 10.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            cells.forEach { cell ->
                Text(
                    cell.uppercase(), color = p.text, maxLines = 1,
                    style = MaterialTheme.typography.labelSmall.copy(fontFamily = LocalFontPair.current.mono, fontWeight = FontWeight.Medium, fontSize = 11.sp, lineHeight = 16.sp, letterSpacing = 0.44.sp),
                )
            }
        }
        CoverStackDivider()
    }
}
