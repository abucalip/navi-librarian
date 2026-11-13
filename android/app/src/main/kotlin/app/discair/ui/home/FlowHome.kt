package app.discair.ui.home

import app.discair.ui.common.FlowIcons
import android.content.Context
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.MoreVert
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
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.data.Shelves
import app.discair.model.FeedbackAction
import app.discair.model.GenreTile
import app.discair.model.GetState
import app.discair.model.InsightCard
import app.discair.model.InsightNarrative
import app.discair.model.Pick
import app.discair.model.RadioPlay
import app.discair.model.ShelfAlbum
import app.discair.ui.Opener
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.ArtistPhoto
import app.discair.ui.common.Button
import app.discair.ui.common.FlowCircleButton
import app.discair.ui.common.FlowGroup
import app.discair.ui.common.FlowIconTile
import app.discair.ui.common.FlowListRow
import app.discair.ui.common.FlowRules
import app.discair.ui.common.FlowTabs
import app.discair.ui.common.FlowTag
import app.discair.ui.common.Load
import app.discair.ui.common.LocalAcquisitions
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.OutlinedButton
import app.discair.ui.common.Target
import app.discair.ui.common.flowCard
import app.discair.ui.common.flowDepth
import app.discair.ui.common.pageMetadata
import app.discair.ui.common.rememberAlbumYear
import app.discair.ui.common.rememberLoad
import app.discair.ui.common.routeKey
import app.discair.ui.discover.lensName
import app.discair.ui.player.LocalPlayActions
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.accentText

/*
 * Flow's Home (Layout.Flow): the owner's pick of dashboard I4. A segmented control (Picks, New, Played) chooses what the cover carousel
 * shows; then the title and actions of the centred cover, Artists, Insight, Genres and a grouped list (arrivals, Radio, Library).
 * Spec: docs/ANDROID_ART_THEMES_PROPOSAL.md section 6.2; mockup: docs/design/android-art-themes/flow/home.html.
 * Behaviour is the Home every theme has: the same data, Get, Save, the menu, the arrivals and the links.
 */

/** Everything Flow's Home needs from [HomeScreen], so the screen's own loading is not repeated. */
internal class FlowHomeData(
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
private const val PREFS = "flow_home"

@Composable
internal fun FlowHome(
    data: FlowHomeData, open: Opener, feedback: (FeedbackAction, Pick) -> Unit,
    onRadio: () -> Unit, onLibrary: () -> Unit, onStats: () -> Unit, onServer: () -> Unit, onDownloads: () -> Unit,
) {
    val repo = LocalRepository.current
    val context = LocalContext.current
    val newest = rememberLoad("shelf_newest_20") { repo.shelf(Shelves.Newest, 20).items }
    val recent = rememberLoad("shelf_recent_20") { repo.shelf(Shelves.Recent, 20).items }
    val frequent = rememberLoad("shelf_frequent_20") { repo.shelf(Shelves.Frequent, 20).items }
    val plays = rememberLoad("radio_plays") { repo.radioPlays() }
    val artists = HomeArtists.from((recent.state as? Load.Ready)?.value.orEmpty(), (frequent.state as? Load.Ready)?.value.orEmpty())
    val listeningKnown = recent.state !is Load.Loading && frequent.state !is Load.Loading
    var tab by remember { mutableStateOf(FlowHomeRules.tabOf(readTab(context))) }
    val bottom = 24.dp + app.discair.ui.LocalBottomClearance.current

    val modules: List<@Composable () -> Unit> = listOf(
        { Carousel(tab, { tab = it; writeTab(context, it) }, data, newest.state, newest.reload, recent.state, recent.reload, open, feedback) },
        { ArtistsBlock(artists, listeningKnown, open, onLibrary) },
        { data.insight?.let { InsightCardView(it, open) } },
        { GenresBlock(data.genres, open) },
        { GroupedList(data.arrivals, (plays.state as? Load.Ready)?.value, data.hero, open, onRadio, onStats) },
    )
    BoxWithConstraints(Modifier.fillMaxWidth()) {
        val wide = maxWidth >= DashboardRules.TWO_PANE_MIN_DP.dp
        if (wide) {
            // At 840dp and wider the carousel and artists take the primary pane, everything else the secondary (proposal 6.3).
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

/** The chosen tab is remembered; storage that refuses is not an error, the control then starts on Picks. */
private fun readTab(context: Context): String? = try { context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString("tab", null) } catch (e: Exception) { null }

private fun writeTab(context: Context, tab: FlowHomeRules.Tab) {
    try { context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString("tab", tab.name).apply() } catch (e: Exception) { /* the choice lasts until Home closes */ }
}

// ----- shared bits -----------------------------------------------------------------------------------------------

/** A section heading (Inter 700 20) with its accent link at the right. */
@Composable
private fun SectionHeading(title: String, link: String? = null, onLink: () -> Unit = {}) {
    val p = LocalPalette.current
    Row(Modifier.fillMaxWidth().padding(horizontal = Gutter), verticalAlignment = Alignment.CenterVertically) {
        Text(
            title, Modifier.weight(1f).semantics { heading() }, color = p.text,
            style = MaterialTheme.typography.titleLarge.copy(fontSize = 20.sp, lineHeight = 26.sp, fontWeight = FontWeight.Bold),
        )
        if (link != null) Box(Modifier.heightIn(min = Target).clickable(role = Role.Button, onClick = onLink).padding(start = 8.dp), contentAlignment = Alignment.Center) {
            Text(link, color = p.accentText, style = MaterialTheme.typography.labelLarge.copy(fontSize = 14.sp, fontWeight = FontWeight.Medium))
        }
    }
}

@Composable
private fun Muted(text: String, modifier: Modifier = Modifier) {
    Text(text, modifier.padding(horizontal = Gutter), color = LocalPalette.current.textMuted, style = MaterialTheme.typography.bodyMedium)
}

/** The caution banner under the top bar when a service fails (mockup frame 4): a tinted card of radius 12, a sentence and the Server link. */
@Composable
private fun ServiceBanner(text: String, onServer: () -> Unit) {
    val p = LocalPalette.current
    Row(
        Modifier.padding(horizontal = Gutter).fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(p.cautionDim).padding(horizontal = 12.dp, vertical = 10.dp)
            .semantics { contentDescription = "Warning. $text" },
        horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(FlowIcons.Info, contentDescription = null, tint = p.text, modifier = Modifier.size(20.dp))
        Text(text, Modifier.weight(1f), color = p.text, style = MaterialTheme.typography.bodySmall)
        Box(Modifier.heightIn(min = Target).clickable(role = Role.Button, onClick = onServer).padding(horizontal = 4.dp), contentAlignment = Alignment.Center) {
            Text("Server", color = p.accentText, style = MaterialTheme.typography.labelLarge.copy(fontSize = 14.sp, fontWeight = FontWeight.Medium))
        }
    }
}

// ----- 1 to 3. segmented control, carousel, title and actions ----------------------------------------------------

/** The control, the cover carousel and the title and actions under the centred cover. */
@Composable
private fun Carousel(
    tab: FlowHomeRules.Tab, onTab: (FlowHomeRules.Tab) -> Unit, data: FlowHomeData,
    newest: Load<List<ShelfAlbum>>, retryNewest: () -> Unit, recent: Load<List<ShelfAlbum>>, retryRecent: () -> Unit,
    open: Opener, feedback: (FeedbackAction, Pick) -> Unit,
) {
    val p = LocalPalette.current
    val state: Load<List<FlowHomeRules.Item>>
    val retry: () -> Unit
    when (tab) {
        FlowHomeRules.Tab.Picks -> {
            state = when (val s = data.picks) { Load.Loading -> Load.Loading; is Load.Failed -> s; is Load.Ready -> Load.Ready(data.pickList.map(FlowHomeRules::items)) }
            retry = data.retryPicks
        }
        FlowHomeRules.Tab.New -> { state = newest.mapItems(); retry = retryNewest }
        FlowHomeRules.Tab.Played -> { state = recent.mapItems(); retry = retryRecent }
    }
    val items = (state as? Load.Ready)?.value.orEmpty()
    var index by remember(tab) { mutableIntStateOf(0) }
    val at = FlowHomeRules.clamp(index, items.size)
    val item = items.getOrNull(at)
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        FlowTabs(FlowHomeRules.labels, tab.ordinal, { onTab(FlowHomeRules.Tab.entries[it]) }, Modifier.padding(horizontal = Gutter).fillMaxWidth())
        when {
            state is Load.Loading -> {
                Covers(null, null, null, 0, {}, {})
                Column(Modifier.fillMaxWidth().padding(horizontal = Gutter), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Box(Modifier.width(120.dp).height(26.dp).clip(RoundedCornerShape(10.dp)).background(p.raised))
                    Box(Modifier.width(210.dp).height(16.dp).clip(RoundedCornerShape(10.dp)).background(p.raised))
                }
            }
            state is Load.Failed -> app.discair.ui.home.Inline(state.failure.message, retry)
            item == null -> Muted(FlowHomeRules.empty(tab), Modifier.fillMaxWidth())
            else -> {
                val (prev, next) = FlowHomeRules.neighbours(at, items.size)
                Covers(item, prev?.let { items[it] }, next?.let { items[it] }, items.size, { delta -> index = FlowHomeRules.step(at, items.size, delta) }, {})
                val year = if (tab == FlowHomeRules.Tab.Picks) rememberAlbumYear(item.artist, item.title, item.year) else item.year
                Column(
                    Modifier.fillMaxWidth().padding(horizontal = Gutter).clickable(role = Role.Button) {
                        open.album(routeKey(item.artist, item.title), item.artist, item.title, item.albumId, year)
                    },
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text(
                        item.title, color = p.text, textAlign = TextAlign.Center, maxLines = 2, overflow = TextOverflow.Ellipsis,
                        style = MaterialTheme.typography.headlineMedium.copy(fontSize = 24.sp, lineHeight = 30.sp, fontWeight = FontWeight.Bold),
                    )
                    Text(
                        FlowHomeRules.line(item.copy(year = year)), color = p.textMuted, textAlign = TextAlign.Center, maxLines = 2, overflow = TextOverflow.Ellipsis,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
                if (tab == FlowHomeRules.Tab.Picks) data.pickList.getOrNull(at)?.let { PickActions(it, feedback) }
                else PlayActions(item)
            }
        }
    }
}

private fun Load<List<ShelfAlbum>>.mapItems(): Load<List<FlowHomeRules.Item>> = when (this) {
    Load.Loading -> Load.Loading
    is Load.Failed -> this
    is Load.Ready -> Load.Ready(value.map(FlowHomeRules::items))
}

/**
 * The cover carousel: the centred cover at 220dp with depth level 3, its neighbours at 160dp and 75% opacity, cut by the screen edge. A swipe
 * moves it; a tap on a neighbour brings it to the centre. With [centre] null it draws three blank covers (loading).
 */
@Composable
private fun Covers(centre: FlowHomeRules.Item?, left: FlowHomeRules.Item?, right: FlowHomeRules.Item?, count: Int, onSwipe: (Int) -> Unit, @Suppress("UNUSED_PARAMETER") unused: () -> Unit) {
    val p = LocalPalette.current
    val density = LocalDensity.current
    val small = RoundedCornerShape(FlowRules.RADIUS_COVER.dp)
    val sideSize = FlowHomeRules.SIDE_DP.dp
    val blank = centre == null
    Box(
        Modifier.fillMaxWidth().height(FlowHomeRules.CAROUSEL_HEIGHT_DP.dp).clip(androidx.compose.ui.graphics.RectangleShape)
            .pointerInput(count) {
                if (count < 2) return@pointerInput
                var drag = 0f
                detectHorizontalDragGestures(
                    onDragStart = { drag = 0f },
                    onHorizontalDrag = { _, amount -> drag += amount },
                    onDragEnd = { FlowHomeRules.swipeDelta(drag / density.density)?.let(onSwipe) },
                )
            }
            .semantics { if (!blank) stateDescription = "Swipe left or right for another album" },
    ) {
        if (blank || left != null) SideCover(left, Alignment.CenterStart, -FlowHomeRules.SIDE_OVERHANG_DP, sideSize, small, p, onTap = { onSwipe(-1) })
        if (blank || right != null) SideCover(right, Alignment.CenterEnd, FlowHomeRules.SIDE_OVERHANG_DP, sideSize, small, p, onTap = { onSwipe(1) })
        val centreModifier = Modifier.align(Alignment.Center).size(FlowHomeRules.CENTER_DP.dp).flowDepth(3, small, p).clip(small)
        if (centre != null) AlbumCover(centre.artist, centre.title, centre.artworkUrl, centreModifier, rect = true)
        else Box(centreModifier.background(p.raised))
    }
}

@Composable
private fun androidx.compose.foundation.layout.BoxScope.SideCover(
    item: FlowHomeRules.Item?, at: Alignment, offset: Int, size: androidx.compose.ui.unit.Dp,
    shape: RoundedCornerShape, p: app.discair.ui.theme.Palette, onTap: () -> Unit,
) {
    val m = Modifier.align(at).offset(x = offset.dp).size(size).alpha(FlowHomeRules.SIDE_ALPHA).clip(shape)
    if (item == null) Box(m.background(p.raised))
    else Box(m.clickable(role = Role.Button, onClickLabel = "Show ${item.title}", onClick = onTap)) {
        AlbumCover(item.artist, item.title, item.artworkUrl, Modifier.fillMaxSize(), rect = true)
    }
}

/** Get album (filled), Save, and the round three-dot menu with "Not this album" and "Never suggest artist". */
@Composable
private fun PickActions(pick: Pick, onFeedback: (FeedbackAction, Pick) -> Unit) {
    val hub = LocalAcquisitions.current
    val p = LocalPalette.current
    var saved by remember(pick) { mutableStateOf(false) }
    var menu by remember(pick) { mutableStateOf(false) }
    val get = hub.getState(pick.artist, pick.album)
    val busy = get is GetState.Pending || get is GetState.Requested
    Column(Modifier.fillMaxWidth().padding(horizontal = Gutter), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
            Button(onClick = { hub.getAlbum(pick.artist, pick.album, pageMetadata(pick.artist, pick.album, pick.year, pick.releaseGroupMbid)) }, enabled = !busy) {
                Icon(FlowIcons.Get, contentDescription = null, modifier = Modifier.size(20.dp))
                Text(
                    " " + when (get) {
                        GetState.Pending -> "Requesting…"
                        is GetState.Requested -> "Requested"
                        is GetState.Failed -> "Try again"
                        GetState.Idle -> "Get album"
                    },
                )
            }
            OutlinedButton(onClick = { saved = true; onFeedback(FeedbackAction.Save, pick) }, enabled = !saved) { Text(if (saved) "Saved" else "Save") }
            Box {
                FlowCircleButton(FlowIcons.More, "More for ${pick.album}", { menu = true }, size = 44)
                DropdownMenu(menu, onDismissRequest = { menu = false }) {
                    DropdownMenuItem(text = { Text("Not this album") }, onClick = { menu = false; onFeedback(FeedbackAction.Dismiss, pick) })
                    DropdownMenuItem(text = { Text("Never suggest artist") }, onClick = { menu = false; onFeedback(FeedbackAction.DismissArtist, pick) })
                }
            }
        }
        if (get is GetState.Failed) Text(get.message, style = MaterialTheme.typography.bodySmall, color = p.chartRedText)
    }
}

/** New and Played: Play (filled), Shuffle and the three-dot menu with Play next and Add to queue. Only an owned album can play. */
@Composable
private fun PlayActions(item: FlowHomeRules.Item) {
    val play = LocalPlayActions.current
    val id = item.albumId
    var menu by remember(item) { mutableStateOf(false) }
    Row(Modifier.fillMaxWidth().padding(horizontal = Gutter), horizontalArrangement = Arrangement.spacedBy(8.dp, Alignment.CenterHorizontally), verticalAlignment = Alignment.CenterVertically) {
        Button(onClick = { id?.let { play.playAlbum(it) } }, enabled = id != null) {
            Icon(FlowIcons.Play, contentDescription = null, modifier = Modifier.size(20.dp))
            Text(" Play")
        }
        OutlinedButton(onClick = { id?.let { play.playAlbum(it, shuffle = true) } }, enabled = id != null) { Text("Shuffle") }
        Box {
            FlowCircleButton(FlowIcons.More, "More for ${item.title}", { menu = true }, size = 44)
            DropdownMenu(menu, onDismissRequest = { menu = false }) {
                DropdownMenuItem(text = { Text("Play next") }, enabled = id != null, onClick = { menu = false; id?.let { play.queueAlbum(it, next = true) } })
                DropdownMenuItem(text = { Text("Add to queue") }, enabled = id != null, onClick = { menu = false; id?.let { play.queueAlbum(it, next = false) } })
            }
        }
    }
}

// ----- 4. artists ------------------------------------------------------------------------------------------------

/** Portrait cards, 150dp wide, 3:4, radius 18, the name over a dark fade; "All" opens Library. Fewer than three artists: a sentence instead. */
@Composable
private fun ArtistsBlock(artists: List<HomeArtist>, listeningKnown: Boolean, open: Opener, onLibrary: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        SectionHeading("Artists", if (HomeArtists.enough(artists)) "All" else null, onLibrary)
        if (!HomeArtists.enough(artists)) {
            Muted(if (listeningKnown) HomeArtists.EMPTY_SENTENCE else FlowHomeRules.ARTISTS_LOADING)
        } else LazyRow(contentPadding = PaddingValues(horizontal = Gutter), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            items(artists, key = { it.name }) { artist ->
                val card = RoundedCornerShape(18.dp)
                Box(
                    Modifier.width(150.dp).aspectRatio(3f / 4f).clip(card).background(LocalPalette.current.raised)
                        .clickable(role = Role.Button) { open.artist(artist.name, null, artist.id.ifBlank { null }, null) },
                ) {
                    ArtistPhoto(artist.name, null, Modifier.fillMaxSize())
                    Text(
                        artist.name, color = Color.White, maxLines = 2, overflow = TextOverflow.Ellipsis,
                        style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold, fontSize = 14.sp),
                        modifier = Modifier.align(Alignment.BottomStart).fillMaxWidth()
                            .background(Brush.verticalGradient(listOf(Color.Transparent, Color.Black.copy(alpha = 0.7f))))
                            .padding(start = 12.dp, end = 12.dp, top = 26.dp, bottom = 10.dp),
                    )
                }
            }
        }
    }
}

// ----- 5. insight ------------------------------------------------------------------------------------------------

/** One white card: cover 88, a tag, the title, the sentence, the open button and Why?. */
@Composable
private fun InsightCardView(card: InsightCard, open: Opener) {
    val p = LocalPalette.current
    var why by remember(card.id) { mutableStateOf(false) }
    val artist = card.subject.artist
    val title = card.subject.title
    Column(Modifier.padding(horizontal = Gutter).fillMaxWidth().flowCard(p).padding(12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.Top) {
            if (artist != null && title != null) AlbumCover(artist, title, null, Modifier.size(88.dp).clip(RoundedCornerShape(10.dp)), rect = true)
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                FlowTag(lensName(card.kind), tint = p.accentDim, labelColor = p.text)
                Text(card.title, color = p.text, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 15.sp))
                val sub = listOfNotNull(artist, card.body.ifBlank { null }).joinToString(" · ")
                if (sub.isNotEmpty()) Text(sub, color = p.textMuted, style = MaterialTheme.typography.bodySmall)
            }
        }
        if (why) Text(InsightNarrative.why(card), color = p.textMuted, style = MaterialTheme.typography.bodySmall)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            if (artist != null && title != null) Button(
                onClick = { open.album(routeKey(artist, title), artist, title, null, card.subject.year) }, Modifier.weight(1f),
            ) { Text("Open album") }
            else androidx.compose.foundation.layout.Spacer(Modifier.weight(1f))
            OutlinedButton(onClick = { why = !why }) { Text(if (why) "Hide why" else "Why?") }
        }
    }
}

// ----- 6. genres -------------------------------------------------------------------------------------------------

/** The genre row shows this many, drawn at random each time Home opens (as on every theme). */
private const val GENRES_SHOWN = 6

/** Capsule chips, 34dp, `raised`, in one side-scrolling row; a tap opens the genre. */
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
                LazyRow(contentPadding = PaddingValues(horizontal = Gutter), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(tiles, key = { it.tag }) { genre ->
                        Box(
                            Modifier.heightIn(min = 34.dp).clip(CircleShape).background(p.raised)
                                .clickable(role = Role.Button) { open.genre(genre.tag, genre.name) }.padding(horizontal = 14.dp)
                                .semantics { contentDescription = "${genre.name}, " + app.discair.ui.common.plural(genre.albumCount, "album") },
                            contentAlignment = Alignment.Center,
                        ) {
                            Text(genre.name, color = p.text, maxLines = 1, style = MaterialTheme.typography.labelLarge.copy(fontSize = 14.sp, fontWeight = FontWeight.Medium))
                        }
                    }
                }
            }
        }
    }
}

// ----- 7. grouped list ---------------------------------------------------------------------------------------------

/** One white card of rows with chevrons: each arrival, Radio (last heard) and Library (album count and added this month, opens Library stats). */
@Composable
private fun GroupedList(
    arrivals: List<ArrivalRow>, plays: List<RadioPlay>?, hero: HeroFigures?, open: Opener,
    onRadio: () -> Unit, onStats: () -> Unit,
) {
    FlowGroup {
        arrivals.forEachIndexed { i, row ->
            val job = row.job
            FlowListRow(
                job.title, state = FlowHomeRules.arrivalLine(row), divider = i > 0,
                onClick = { open.album(routeKey(job.artistName, job.albumName), job.artistName, job.albumName, null, job.year) },
                leading = { AlbumCover(job.artistName, job.albumName, null, Modifier.size(32.dp).clip(RoundedCornerShape(FlowRules.RADIUS_COVER_SMALL.dp)), rect = true) },
            )
        }
        FlowListRow("Radio", state = FlowHomeRules.radioLine(plays), divider = arrivals.isNotEmpty(), onClick = onRadio, leading = { FlowIconTile(FlowIcons.Radio) })
        FlowListRow("Library", state = FlowHomeRules.libraryLine(hero), divider = true, onClick = onStats, leading = { FlowIconTile(FlowIcons.Lib) })
    }
}
