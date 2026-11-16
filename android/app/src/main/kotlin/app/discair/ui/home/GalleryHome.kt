package app.discair.ui.home

import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
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
import app.discair.model.RadioDownload
import app.discair.model.RadioPlay
import app.discair.model.RadioStation
import app.discair.model.ShelfAlbum
import app.discair.model.radioLogoRequest
import app.discair.ui.Opener
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.ArtistPhoto
import app.discair.ui.common.Cover
import app.discair.ui.common.GalleryBanner
import app.discair.ui.common.GalleryButton
import app.discair.ui.common.GalleryButtonKind
import app.discair.ui.common.GalleryIcons
import app.discair.ui.common.GalleryPrint
import app.discair.ui.common.GalleryRow
import app.discair.ui.common.GalleryRules
import app.discair.ui.common.GallerySectionHead
import app.discair.ui.common.GallerySourceSwitch
import app.discair.ui.common.GalleryState
import app.discair.ui.common.GalleryType
import app.discair.ui.common.Load
import app.discair.ui.common.LocalAcquisitions
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.gallerySpot
import app.discair.ui.common.pageMetadata
import app.discair.ui.common.rememberAlbumYear
import app.discair.ui.common.rememberLoad
import app.discair.ui.common.routeKey
import app.discair.ui.common.sharedCover
import app.discair.ui.discover.lensName
import app.discair.ui.player.LocalPlayActions
import app.discair.ui.radio.LocalRadio
import app.discair.ui.theme.LocalPalette
import java.time.Instant

/*
 * Gallery's Home (Layout.Gallery). Spec: docs/GALLERY_THEME.md section 9; mockup: docs/design/gallery/pages/home.html (six frames).
 * Top to bottom: service banner, source switch, the hero print with its placard and actions, Played lately, Artists you return to, Radio,
 * This week, Arrivals, Genres and the library line. The data and behaviour are the Home every theme has (Get, Save, the menu, the arrivals and the links).
 */

/** Everything Gallery's Home needs from [HomeScreen], so the screen's own loading is not repeated. */
internal class GalleryHomeData(
    val picks: Load<List<Pick>>,
    val pickList: List<Pick>,
    val retryPicks: () -> Unit,
    val genres: Load<List<GenreTile>>,
    val hero: HeroFigures?,
    val arrivals: List<ArrivalRow>,
    val insight: InsightCard?,
    val banner: String?,
)

private const val PREFS = "gallery_home"
private val Gutter = GalleryRules.GUTTER.dp

@Composable
internal fun GalleryHome(
    data: GalleryHomeData, open: Opener, feedback: (FeedbackAction, Pick) -> Unit,
    onRadio: () -> Unit, onOpenPlayer: () -> Unit, onLibrary: () -> Unit, onStats: () -> Unit, onServer: () -> Unit, onDownloads: () -> Unit,
) {
    val repo = LocalRepository.current
    val context = LocalContext.current
    val now = remember { Instant.now() }
    val newest = rememberLoad("shelf_newest_20") { repo.shelf(Shelves.Newest, 20).items }
    val recent = rememberLoad("shelf_recent_20") { repo.shelf(Shelves.Recent, 20).items }
    val frequent = rememberLoad("shelf_frequent_20") { repo.shelf(Shelves.Frequent, 20).items }
    val stations = rememberLoad("radio_stations") { repo.radioStations() }
    val plays = rememberLoad("radio_plays") { repo.radioPlays() }
    val artistPage = rememberLoad("home_artist_counts") { repo.artists("", app.discair.data.ArtistSort.Albums, true, null) }
    val recentList = (recent.state as? Load.Ready)?.value.orEmpty()
    val artists = HomeArtists.from(recentList, (frequent.state as? Load.Ready)?.value.orEmpty())
    val counts = (artistPage.state as? Load.Ready)?.value?.items.orEmpty().associate { it.name.lowercase() to it.albumCount }
    val artistTotal = (artistPage.state as? Load.Ready)?.value?.total
    val listeningKnown = recent.state !is Load.Loading && frequent.state !is Load.Loading
    var tab by remember { mutableStateOf(FlowHomeRules.tabOf(readTab(context))) }
    val bottom = 24.dp + app.discair.ui.LocalBottomClearance.current

    LazyColumn(Modifier.fillMaxWidth(), contentPadding = PaddingValues(top = 0.dp, bottom = bottom)) {
        data.banner?.let { item(key = "banner") { GalleryBanner(it, link = "Server", onLink = onServer) } }
        item(key = "hero") {
            Hero(tab, { tab = it; writeTab(context, it) }, data, newest.state, newest.reload, recent.state, recent.reload, open, feedback)
        }
        if (recentList.isNotEmpty()) item(key = "lately") { PlayedLately(recentList.take(GalleryHomeRules.PLAYED_SHOWN), open, onLibrary) }
        item(key = "artists") { ArtistsBlock(artists, counts, listeningKnown, open, onLibrary) }
        val stationList = (stations.state as? Load.Ready)?.value.orEmpty()
        if (stationList.isNotEmpty()) item(key = "radio") {
            RadioBlock(stationList, (plays.state as? Load.Ready)?.value.orEmpty(), now, onRadio, onOpenPlayer)
        }
        data.insight?.let { card -> item(key = "week") { ThisWeek(card, open) } }
        if (data.arrivals.isNotEmpty()) item(key = "arrivals") { Arrivals(data.arrivals.take(2), open, onDownloads) }
        item(key = "genres") { Genres(data.genres, open, onLibrary) }
        item(key = "library") { LibraryLine(GalleryHomeRules.libraryLine(data.hero, artistTotal), onStats) }
    }
}

/** The chosen source is remembered; storage that refuses is not an error, the switch then starts on Picks. */
private fun readTab(context: Context): String? = try { context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString("tab", null) } catch (e: Exception) { null }

private fun writeTab(context: Context, tab: FlowHomeRules.Tab) {
    try { context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString("tab", tab.name).apply() } catch (e: Exception) { /* the choice lasts until Home closes */ }
}

@Composable
private fun Muted(text: String, modifier: Modifier = Modifier) {
    Text(text, modifier, color = LocalPalette.current.textMuted, style = GalleryType.small())
}

/** One catalogue line: DM Mono capitals in `textMuted`. */
@Composable
private fun Eyebrow(text: String, modifier: Modifier = Modifier, color: androidx.compose.ui.graphics.Color = LocalPalette.current.textMuted) {
    Text(text.uppercase(), modifier, color = color, style = GalleryType.catalogue)
}

/** A cover in a print that is not drawn yet or has none: the empty mat holds the `note` icon. */
@Composable
private fun EmptyCover(modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    Box(modifier.aspectRatio(1f).background(p.raised), contentAlignment = Alignment.Center) {
        Icon(GalleryIcons.MusicNote, null, tint = p.textMuted, modifier = Modifier.size(GalleryRules.ICON.dp))
    }
}

@Composable
private fun Skeleton(modifier: Modifier) {
    Box(modifier.background(LocalPalette.current.raised))
}

// ----- 2 and 3. source switch, hero print, placard, actions ----------------------------------------------------

/** What the hero shows for one album, from a pick or a shelf album. */
private class HeroItem(val artist: String, val title: String, val year: Int?, val genre: String?, val albumId: String?, val artworkUrl: String?, val owned: Boolean)

private fun Pick.hero() = HeroItem(artist, album, year, genres.firstOrNull(), null, null, false)

private fun ShelfAlbum.hero() = HeroItem(artist, name, year, null, id.ifBlank { null }, artworkUrl, owned)

private fun Load<List<ShelfAlbum>>.heroes(): Load<List<HeroItem>> = when (this) {
    Load.Loading -> Load.Loading
    is Load.Failed -> this
    is Load.Ready -> Load.Ready(value.map { it.hero() })
}

@Composable
private fun Hero(
    tab: FlowHomeRules.Tab, onTab: (FlowHomeRules.Tab) -> Unit, data: GalleryHomeData,
    newest: Load<List<ShelfAlbum>>, retryNewest: () -> Unit, recent: Load<List<ShelfAlbum>>, retryRecent: () -> Unit,
    open: Opener, feedback: (FeedbackAction, Pick) -> Unit,
) {
    val p = LocalPalette.current
    val density = LocalDensity.current
    val state: Load<List<HeroItem>>
    val retry: () -> Unit
    when (tab) {
        FlowHomeRules.Tab.Picks -> {
            state = when (val s = data.picks) { Load.Loading -> Load.Loading; is Load.Failed -> s; is Load.Ready -> Load.Ready(data.pickList.map { it.hero() }) }
            retry = data.retryPicks
        }
        FlowHomeRules.Tab.New -> { state = newest.heroes(); retry = retryNewest }
        FlowHomeRules.Tab.Played -> { state = recent.heroes(); retry = retryRecent }
    }
    val items = (state as? Load.Ready)?.value.orEmpty()
    var index by remember(tab) { mutableIntStateOf(0) }
    val at = FlowHomeRules.clamp(index, items.size)
    val item = items.getOrNull(at)
    val step = { delta: Int -> index = FlowHomeRules.step(at, items.size, delta) }
    Column {
        GallerySourceSwitch(FlowHomeRules.labels, tab.ordinal, { onTab(FlowHomeRules.Tab.entries[it]) }, Modifier.padding(top = 6.dp))
        Column(
            Modifier.fillMaxWidth().gallerySpot(p).padding(top = 20.dp)
                .pointerInput(items.size) {
                    if (items.size < 2) return@pointerInput
                    var drag = 0f
                    detectHorizontalDragGestures(
                        onDragStart = { drag = 0f },
                        onHorizontalDrag = { _, amount -> drag += amount },
                        onDragEnd = { FlowHomeRules.swipeDelta(drag / density.density)?.let(step) },
                    )
                }
                .then(if (item != null && items.size > 1) Modifier.semantics { stateDescription = "Swipe left or right for another album" } else Modifier),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            val width = GalleryHomeRules.HERO_DP.dp
            when {
                state is Load.Loading -> {
                    GalleryPrint(width) { Skeleton(Modifier.fillMaxWidth().aspectRatio(1f)) }
                    Column(Modifier.width(width).padding(top = 20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Skeleton(Modifier.width(110.dp).height(12.dp))
                        Skeleton(Modifier.width(150.dp).height(28.dp))
                        Skeleton(Modifier.width(190.dp).height(14.dp))
                    }
                }
                state is Load.Failed -> Column(Modifier.padding(horizontal = Gutter), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(state.failure.message, color = p.chartRedText, style = GalleryType.body())
                    GalleryButton("Try again", retry, kind = GalleryButtonKind.Outlined)
                }
                item == null -> Muted(FlowHomeRules.empty(tab), Modifier.padding(horizontal = Gutter))
                else -> {
                    val year = if (tab == FlowHomeRules.Tab.Picks) rememberAlbumYear(item.artist, item.title, item.year) else item.year
                    val key = routeKey(item.artist, item.title)
                    val openAlbum = { open.album(key, item.artist, item.title, item.albumId, year) }
                    GalleryPrint(width, Modifier.clickable(role = Role.Button, onClickLabel = "Open ${item.title}", onClick = openAlbum)) {
                        AlbumCover(item.artist, item.title, item.artworkUrl, Modifier.fillMaxWidth().aspectRatio(1f).sharedCover(key), rect = true)
                    }
                    Column(Modifier.width(width).padding(top = 20.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                            Eyebrow(GalleryHomeRules.eyebrow(tab))
                            if (items.size > 1) Pager(at, items.size, step)
                        }
                        Text(
                            item.title, color = p.text, maxLines = 2, overflow = TextOverflow.Ellipsis,
                            style = GalleryType.work, modifier = Modifier.padding(top = 4.dp).clickable(role = Role.Button, onClick = openAlbum),
                        )
                        Text(GalleryHomeRules.by(item.artist, year), color = p.text, style = GalleryType.body(), maxLines = 1, overflow = TextOverflow.Ellipsis)
                        Muted(GalleryHomeRules.status(tab, item.genre, item.owned))
                    }
                    Row(Modifier.width(width).padding(top = 16.dp), horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                        if (tab == FlowHomeRules.Tab.Picks) data.pickList.getOrNull(at)?.let { PickActions(it, feedback, Modifier.weight(1f)) }
                        else PlayActions(item, Modifier.weight(1f))
                    }
                }
            }
        }
    }
}

/** "‹ 01 / 12 ›": two chevrons round the catalogue count. A swipe on the print does the same. */
@Composable
private fun Pager(index: Int, count: Int, step: (Int) -> Unit) {
    val p = LocalPalette.current
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(2.dp)) {
        Icon(
            GalleryIcons.Back, "Previous", tint = p.control,
            modifier = Modifier.size(28.dp).clickable(role = Role.Button) { step(-1) }.padding(5.dp),
        )
        Eyebrow(GalleryHomeRules.pagerLabel(index, count))
        Icon(
            GalleryIcons.Chevron, "Next", tint = p.control,
            modifier = Modifier.size(28.dp).clickable(role = Role.Button) { step(1) }.padding(5.dp),
        )
    }
}

/** Picks: Get album, Save and the three dots with "Not this album" and "Never suggest artist". */
@Composable
private fun androidx.compose.foundation.layout.RowScope.PickActions(pick: Pick, onFeedback: (FeedbackAction, Pick) -> Unit, modifier: Modifier) {
    val hub = LocalAcquisitions.current
    val p = LocalPalette.current
    var saved by remember(pick) { mutableStateOf(false) }
    var menu by remember(pick) { mutableStateOf(false) }
    val get = hub.getState(pick.artist, pick.album)
    val busy = get is GetState.Pending || get is GetState.Requested
    GalleryButton(
        when (get) {
            GetState.Pending -> "Requesting…"
            is GetState.Requested -> "Requested"
            is GetState.Failed -> "Try again"
            GetState.Idle -> "Get album"
        },
        { hub.getAlbum(pick.artist, pick.album, pageMetadata(pick.artist, pick.album, pick.year, pick.releaseGroupMbid)) },
        icon = GalleryIcons.Get, enabled = !busy,
    )
    GalleryButton(if (saved) "Saved" else "Save", { saved = true; onFeedback(FeedbackAction.Save, pick) }, kind = GalleryButtonKind.Text, icon = GalleryIcons.Bookmark, enabled = !saved)
    Box(modifier, contentAlignment = Alignment.CenterEnd) {
        app.discair.ui.common.GalleryIconButton(GalleryIcons.More, "More for ${pick.album}", { menu = true })
        DropdownMenu(menu, onDismissRequest = { menu = false }) {
            DropdownMenuItem(text = { Text("Not this album") }, onClick = { menu = false; onFeedback(FeedbackAction.Dismiss, pick) })
            DropdownMenuItem(text = { Text("Never suggest artist") }, onClick = { menu = false; onFeedback(FeedbackAction.DismissArtist, pick) })
        }
    }
}

/** New and Played: Play, Shuffle and the three dots with Play next and Add to queue. Only an album in the library can play. */
@Composable
private fun androidx.compose.foundation.layout.RowScope.PlayActions(item: HeroItem, modifier: Modifier) {
    val play = LocalPlayActions.current
    val id = item.albumId
    var menu by remember(item) { mutableStateOf(false) }
    GalleryButton("Play", { id?.let { play.playAlbum(it) } }, icon = GalleryIcons.Play, enabled = id != null)
    GalleryButton("Shuffle", { id?.let { play.playAlbum(it, shuffle = true) } }, kind = GalleryButtonKind.Text, icon = GalleryIcons.Shuffle, enabled = id != null)
    Box(modifier, contentAlignment = Alignment.CenterEnd) {
        app.discair.ui.common.GalleryIconButton(GalleryIcons.More, "More for ${item.title}", { menu = true })
        DropdownMenu(menu, onDismissRequest = { menu = false }) {
            DropdownMenuItem(text = { Text("Play next") }, enabled = id != null, onClick = { menu = false; id?.let { play.queueAlbum(it, next = true) } })
            DropdownMenuItem(text = { Text("Add to queue") }, enabled = id != null, onClick = { menu = false; id?.let { play.queueAlbum(it, next = false) } })
        }
    }
}

// ----- 4. played lately ----------------------------------------------------------------------------------------

@Composable
private fun PlayedLately(albums: List<ShelfAlbum>, open: Opener, onAll: () -> Unit) {
    val p = LocalPalette.current
    GallerySectionHead("Played lately", link = "All", onLink = onAll)
    Row(Modifier.fillMaxWidth().padding(horizontal = Gutter), horizontalArrangement = Arrangement.spacedBy(18.dp)) {
        for (album in albums) {
            val key = routeKey(album.artist, album.name)
            Column(
                Modifier.weight(1f).clickable(role = Role.Button) { open.album(key, album.artist, album.name, album.id.ifBlank { null }, album.year) },
                verticalArrangement = Arrangement.spacedBy(9.dp),
            ) {
                GalleryPrint(151.dp, Modifier.fillMaxWidth(), small = true) {
                    AlbumCover(album.artist, album.name, album.artworkUrl, Modifier.fillMaxWidth().aspectRatio(1f), rect = true)
                }
                Text(album.name, color = p.text, style = GalleryType.rowWork, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(
                    GalleryHomeRules.by(album.artist, album.year), color = p.textMuted, style = GalleryType.small().copy(fontSize = 12.sp, lineHeight = 14.sp),
                    maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.padding(top = 0.dp),
                )
            }
        }
        // A single album keeps its column's width, so it is not stretched across the page.
        if (albums.size == 1) Box(Modifier.weight(1f))
    }
}

// ----- 5. artists you return to --------------------------------------------------------------------------------

@Composable
private fun ArtistsBlock(artists: List<HomeArtist>, counts: Map<String, Int>, listeningKnown: Boolean, open: Opener, onLibrary: () -> Unit) {
    val p = LocalPalette.current
    val enough = HomeArtists.enough(artists)
    GallerySectionHead("Artists you return to", link = if (enough) "All" else null, onLink = onLibrary)
    if (!enough) {
        Muted(if (listeningKnown) GalleryHomeRules.NO_LISTENING else "Loading…", Modifier.padding(horizontal = Gutter))
        return
    }
    LazyRow(contentPadding = PaddingValues(horizontal = Gutter), horizontalArrangement = Arrangement.spacedBy(14.dp)) {
        items(artists, key = { it.name }) { artist ->
            Column(
                Modifier.width(104.dp).clickable(role = Role.Button) { open.artist(artist.name, null, artist.id.ifBlank { null }, null) },
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                ArtistPhoto(artist.name, null, Modifier.fillMaxWidth().aspectRatio(4f / 5f))
                Text(artist.name, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = GalleryType.rowTitle().copy(fontSize = 13.sp, lineHeight = 16.sp))
                GalleryHomeRules.albumCount(counts[artist.name.lowercase()])?.let { Eyebrow(it) }
            }
        }
    }
}

// ----- 6. radio ------------------------------------------------------------------------------------------------

@Composable
private fun RadioBlock(stations: List<RadioStation>, plays: List<RadioPlay>, now: Instant, onRadio: () -> Unit, onOpenPlayer: () -> Unit) {
    val p = LocalPalette.current
    val radio = LocalRadio.current
    val live by radio.state.collectAsState()
    val plates = GalleryHomeRules.plates(stations, plays, now)
    GallerySectionHead("Radio", link = "All stations", onLink = onRadio)
    Row(Modifier.fillMaxWidth().padding(horizontal = Gutter), horizontalArrangement = Arrangement.spacedBy(14.dp)) {
        for (plate in plates) {
            val tint = if (plate.today) p.accent else p.text
            Column(
                Modifier.width(GalleryHomeRules.STATION_DP.dp)
                    .clickable(role = Role.Button, onClickLabel = "Play ${plate.station.name}") { radio.play(plate.station); onOpenPlayer() },
                verticalArrangement = Arrangement.spacedBy(7.dp),
            ) {
                GalleryPrint(GalleryHomeRules.STATION_DP.dp, Modifier.fillMaxWidth(), small = true) { StationLogo(plate.station) }
                Text(plate.station.name, color = tint, maxLines = 2, overflow = TextOverflow.Ellipsis, style = GalleryType.rowTitle().copy(fontSize = 12.5.sp, lineHeight = 16.sp))
                if (plate.heard.isNotEmpty()) Eyebrow(plate.heard, color = if (plate.today) p.accent else p.textMuted)
            }
        }
    }
    val newest = GalleryHomeRules.newestPlays(plays)
    if (newest.isNotEmpty()) {
        Column(Modifier.fillMaxWidth().padding(horizontal = Gutter).padding(top = 20.dp)) {
            Eyebrow(GalleryHomeRules.heardHeading(newest.first(), now), Modifier.padding(bottom = 6.dp))
            app.discair.ui.common.GalleryRule()
            newest.forEachIndexed { i, play ->
                val download = live.downloadFor(play.id, play.grabbed, play.inLibrary)
                val shown = play.copy(inLibrary = download == RadioDownload.Owned, grabbed = download == RadioDownload.Done || download == RadioDownload.Working)
                GalleryRow(
                    play.title, sub = GalleryHomeRules.playLine(play), italicTitle = true, divider = i < newest.size - 1,
                    lead = { GalleryPrint(48.dp, Modifier.width(48.dp), small = true) { EmptyCover() } },
                    trail = {
                        when (GalleryHomeRules.trailing(shown)) {
                            GalleryHomeRules.Trailing.InLibrary -> GalleryState("In library", color = p.ok)
                            GalleryHomeRules.Trailing.Requested -> GalleryState(if (download == RadioDownload.Working) "Requesting…" else "Requested")
                            GalleryHomeRules.Trailing.Get -> GalleryButton("Get", { radio.download(play.id) }, kind = GalleryButtonKind.Outlined, icon = GalleryIcons.Get, small = true)
                            GalleryHomeRules.Trailing.None -> Unit
                        }
                    },
                )
            }
        }
    }
}

/** A station's logo on an initials tile: the tile shows while the logo loads and when there is none. */
@Composable
private fun StationLogo(station: RadioStation) {
    val repo = LocalRepository.current
    val p = LocalPalette.current
    Box(Modifier.fillMaxWidth().aspectRatio(1f).background(p.raised), contentAlignment = Alignment.Center) {
        Text(GalleryHomeRules.initials(station.name), color = p.textMuted, style = GalleryType.rowTitle().copy(fontSize = 17.sp), maxLines = 1)
        Cover(radioLogoRequest(repo.absolute(station.logoUrl), 128), Modifier.fillMaxWidth().aspectRatio(1f), rect = true)
    }
}

// ----- 7. this week --------------------------------------------------------------------------------------------

@Composable
private fun ThisWeek(card: InsightCard, open: Opener) {
    val p = LocalPalette.current
    var why by remember(card.id) { mutableStateOf(false) }
    val artist = card.subject.artist
    val title = card.subject.title
    GallerySectionHead("This week")
    Column(Modifier.fillMaxWidth().padding(horizontal = Gutter)) {
        Row(horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.Top) {
            if (artist != null && title != null) GalleryPrint(96.dp, Modifier.width(96.dp), small = true) {
                AlbumCover(artist, title, null, Modifier.fillMaxWidth().aspectRatio(1f), rect = true)
            }
            Column(Modifier.weight(1f)) {
                Eyebrow(lensName(card.kind), color = p.accent)
                Text(card.title, color = p.text, style = GalleryType.workM, modifier = Modifier.padding(top = 6.dp))
                val sub = listOfNotNull(artist, card.body.ifBlank { null }).joinToString(" · ")
                if (sub.isNotEmpty()) Muted(sub, Modifier.padding(top = 4.dp))
            }
        }
        if (why) Muted(InsightNarrative.why(card), Modifier.padding(top = 10.dp))
        Row(Modifier.padding(top = 14.dp), horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
            // An insight names an album but carries no library id, so the button opens the album page (where Play is) rather than guessing.
            if (artist != null && title != null) GalleryButton("Open album", { open.album(routeKey(artist, title), artist, title, null, card.subject.year) }, small = true, icon = GalleryIcons.Play)
            GalleryButton(if (why) "Hide why" else "Why this?", { why = !why }, kind = GalleryButtonKind.Text)
        }
    }
}

// ----- 8. arrivals ---------------------------------------------------------------------------------------------

@Composable
private fun Arrivals(rows: List<ArrivalRow>, open: Opener, onDownloads: () -> Unit) {
    val p = LocalPalette.current
    GallerySectionHead("Arrivals", link = "Downloads", onLink = onDownloads)
    Column(Modifier.fillMaxWidth().padding(horizontal = Gutter)) {
        rows.forEachIndexed { i, row ->
            val job = row.job
            GalleryRow(
                job.album, sub = CoverStackHomeRules.arrivalLine(row), italicTitle = true, divider = i < rows.size - 1,
                onClick = { open.album(routeKey(job.artist, job.album), job.artist, job.album, null, null) },
                lead = { GalleryPrint(48.dp, Modifier.width(48.dp), small = true) { AlbumCover(job.artist, job.album, null, Modifier.fillMaxWidth().aspectRatio(1f), rect = true) } },
                trail = {
                    if (row.stage >= 4 && !row.failed) GalleryState("New", color = p.ok)
                    else Icon(GalleryIcons.Chevron, null, tint = p.control, modifier = Modifier.size(GalleryRules.ICON.dp))
                },
            )
        }
    }
}

// ----- 9. genres -----------------------------------------------------------------------------------------------

/** The genre row shows this many, drawn at random each time Home opens (as on every theme). */
private const val GENRES_SHOWN = 5

/** One Fraunces line of genre names divided by thin slashes, the one with most albums in italic; each name opens its genre. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun Genres(state: Load<List<GenreTile>>, open: Opener, onAll: () -> Unit) {
    val p = LocalPalette.current
    GallerySectionHead("Genres", link = "All", onLink = onAll)
    when (state) {
        Load.Loading -> Muted("Loading…", Modifier.padding(horizontal = Gutter))
        is Load.Failed -> Muted(state.failure.message, Modifier.padding(horizontal = Gutter))
        is Load.Ready -> {
            val tiles = remember(state.value) { state.value.shuffled().take(GENRES_SHOWN) }
            val favourite = tiles.maxByOrNull { it.albumCount }?.tag
            FlowRow(Modifier.fillMaxWidth().padding(horizontal = Gutter)) {
                tiles.forEachIndexed { i, genre ->
                    Row {
                        Text(
                            genre.name, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis,
                            style = GalleryType.genreList.copy(fontStyle = if (genre.tag == favourite) FontStyle.Italic else FontStyle.Normal),
                            modifier = Modifier.heightIn(min = 32.dp).clickable(role = Role.Button) { open.genre(genre.tag, genre.name) }
                                .semantics { contentDescription = "${genre.name}, " + app.discair.ui.common.plural(genre.albumCount, "album") },
                        )
                        if (i < tiles.size - 1) Text("/", color = p.edge, style = GalleryType.genreList, modifier = Modifier.padding(horizontal = 6.dp))
                    }
                }
            }
        }
    }
}

// ----- 10. library line ----------------------------------------------------------------------------------------

@Composable
private fun LibraryLine(line: String, onStats: () -> Unit) {
    val p = LocalPalette.current
    Row(
        Modifier.fillMaxWidth().padding(top = 8.dp).heightIn(min = 48.dp).clickable(role = Role.Button, onClick = onStats)
            .padding(horizontal = Gutter, vertical = 24.dp),
        horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(line.uppercase(), color = p.control, style = GalleryType.catalogue, modifier = Modifier.weight(1f))
        Icon(GalleryIcons.Chevron, null, tint = p.control, modifier = Modifier.size(GalleryRules.ICON.dp))
    }
}
