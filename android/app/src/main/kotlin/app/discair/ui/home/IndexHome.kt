package app.discair.ui.home

import android.content.Context
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import app.discair.data.Shelves
import app.discair.model.FeedbackAction
import app.discair.model.GenreTile
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
import app.discair.ui.common.IndexButton
import app.discair.ui.common.IndexButtonKind
import app.discair.ui.common.IndexDataList
import app.discair.ui.common.IndexGet
import app.discair.ui.common.IndexGetButton
import app.discair.ui.common.IndexIconButton
import app.discair.ui.common.IndexIcons
import app.discair.ui.common.IndexInsightBlock
import app.discair.ui.common.IndexLabel
import app.discair.ui.common.IndexPageHead
import app.discair.ui.common.IndexRow
import app.discair.ui.common.IndexRule
import app.discair.ui.common.IndexRules
import app.discair.ui.common.IndexSectionHead
import app.discair.ui.common.IndexSourceSwitch
import app.discair.ui.common.IndexTracker
import app.discair.ui.common.IndexType
import app.discair.ui.common.indexArrive
import app.discair.ui.common.indexGetOf
import app.discair.ui.common.Load
import app.discair.ui.common.LocalAcquisitions
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.pageMetadata
import app.discair.ui.common.plural
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
 * Index's Home (Layout.Index). Spec: docs/INDEX_THEME.md section 9; mockup: docs/design/index/pages/home.html (four frames).
 * Top to bottom: the service banner, the head with its source switch, the lead pick with its data list and actions, the strip (02 to 05), Played, Artists,
 * Radio, This week (the insight block), Arrivals, Genres and the library line. The data and behaviour are the Home every theme has; the Home bar is the shell's.
 */

private const val PREFS = "index_home"
private val Gutter = IndexRules.GUTTER.dp

@Composable
internal fun IndexHome(
    data: GalleryHomeData, open: Opener, feedback: (FeedbackAction, Pick) -> Unit,
    onRadio: () -> Unit, onLibrary: () -> Unit, onStats: () -> Unit, onServer: () -> Unit, onDownloads: () -> Unit,
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
    // The lead is the album the owner picked from the strip (a long press); it starts on the first album and again whenever the source changes.
    var leadAt by remember(tab) { mutableStateOf(0) }
    val bottom = 24.dp + app.discair.ui.LocalBottomClearance.current

    val state: Load<List<LeadItem>>
    val retry: () -> Unit
    when (tab) {
        FlowHomeRules.Tab.Picks -> {
            state = when (val s = data.picks) { Load.Loading -> Load.Loading; is Load.Failed -> s; is Load.Ready -> Load.Ready(data.pickList.map { it.lead() }) }
            retry = data.retryPicks
        }
        FlowHomeRules.Tab.New -> { state = newest.state.leads(); retry = newest.reload }
        FlowHomeRules.Tab.Played -> { state = recent.state.leads(); retry = recent.reload }
    }
    val items = (state as? Load.Ready)?.value.orEmpty()
    val at = IndexHomeRules.leadAt(leadAt, items.size)
    val stripAt = IndexHomeRules.strip(items.size, at)
    // One cover per album per screen is the shared element: the lead's and the strip's keys are taken, so a Played row of the same album leaves its cover out.
    val taken = (listOf(at) + stripAt).mapNotNull { items.getOrNull(it) }.map { routeKey(it.artist, it.title) }.toSet()

    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = bottom)) {
        var block = 0
        data.banner?.let { item(key = "banner") { Banner(it, retry = data.retryPicks, onServer = onServer) } }
        val headAt = block++
        item(key = "head") {
            IndexPageHead(
                tab.label, Modifier.indexArrive(headAt), count = IndexHomeRules.count((state as? Load.Ready)?.value?.size),
                trailing = { IndexSourceSwitch(FlowHomeRules.labels, tab.ordinal, { tab = FlowHomeRules.Tab.entries[it]; writeTab(context, tab) }) },
            )
        }
        val leadBlock = block++
        item(key = "lead") {
            Column(Modifier.indexArrive(leadBlock, tab.name)) {
                when {
                    state is Load.Loading -> LeadSkeleton()
                    state is Load.Failed -> Failed(state.failure.message, retry)
                    items.isEmpty() -> Muted(IndexHomeRules.empty(tab), Modifier.padding(horizontal = Gutter, vertical = 16.dp))
                    else -> Lead(tab, items[at], at, data.pickList.getOrNull(at), open, feedback)
                }
            }
        }
        if (items.isNotEmpty() && stripAt.isNotEmpty()) {
            val stripBlock = block++
            item(key = "strip") { Strip(items, stripAt, open, onLead = { leadAt = it }, Modifier.indexArrive(stripBlock, tab.name)) }
        }
        val playedBlock = block++
        item(key = "played") { Played(recentList.take(IndexHomeRules.PLAYED_SHOWN), listeningKnown, taken, open, onLibrary, Modifier.indexArrive(playedBlock)) }
        val artistsBlock = block++
        item(key = "artists") { Artists(artists.take(IndexHomeRules.COLUMNS), counts, listeningKnown, open, onLibrary, Modifier.indexArrive(artistsBlock)) }
        val stationList = (stations.state as? Load.Ready)?.value.orEmpty()
        if (stationList.isNotEmpty()) {
            val radioBlock = block++
            item(key = "radio") { Radio(stationList, (plays.state as? Load.Ready)?.value.orEmpty(), now, onRadio, Modifier.indexArrive(radioBlock)) }
        }
        data.insight?.let { card -> val weekBlock = block++; item(key = "week") { ThisWeek(card, open, Modifier.indexArrive(weekBlock)) } }
        if (data.arrivals.isNotEmpty()) {
            val arrivalsBlock = block++
            item(key = "arrivals") { Arrivals(data.arrivals.take(2), open, onDownloads, Modifier.indexArrive(arrivalsBlock)) }
        }
        item(key = "genres") { Genres(data.genres, open, onLibrary) }
        item(key = "library") { LibraryLine(IndexHomeRules.libraryLine(data.hero?.count, artistTotal, data.hero?.added30), onStats) }
    }
}

/** The chosen source is remembered; storage that refuses is not an error, the switch then starts on Picks. */
private fun readTab(context: Context): String? = try { context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString("tab", null) } catch (e: Exception) { null }

private fun writeTab(context: Context, tab: FlowHomeRules.Tab) {
    try { context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString("tab", tab.name).apply() } catch (e: Exception) { /* the choice lasts until Home closes */ }
}

@Composable
private fun Muted(text: String, modifier: Modifier = Modifier) {
    Text(text, modifier, color = LocalPalette.current.textMuted, style = IndexType.body())
}

@Composable
private fun Skeleton(modifier: Modifier) {
    Box(modifier.background(LocalPalette.current.raised))
}

@Composable
private fun Failed(message: String, retry: () -> Unit) {
    Column(Modifier.padding(horizontal = Gutter, vertical = 16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(message, color = LocalPalette.current.chartRedText, style = IndexType.body())
        IndexButton("Try again", retry, kind = IndexButtonKind.Ghost, small = true)
    }
}

/** Frame 4: a 2dp `caution` rule, the warning icon, the sentence and Retry, closed by a 1dp rule. The saved-copy time is not carried by the app, so it is not drawn. */
@Composable
private fun Banner(text: String, retry: () -> Unit, onServer: () -> Unit) {
    val p = LocalPalette.current
    Column(Modifier.fillMaxWidth().padding(horizontal = Gutter).padding(top = 12.dp)) {
        Box(Modifier.fillMaxWidth().height(2.dp).background(p.caution))
        Row(Modifier.fillMaxWidth().padding(vertical = 10.dp), horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(IndexIcons.Warning, null, tint = p.caution, modifier = Modifier.size(IndexRules.ICON.dp))
            Text(
                text, style = IndexType.rowTitle().copy(fontSize = 14.sp), color = p.text, modifier = Modifier.weight(1f).clickable(role = Role.Button, onClick = onServer)
                    .semantics { contentDescription = "Warning. $text" },
            )
            IndexButton("Retry", retry, kind = IndexButtonKind.Ghost, small = true)
        }
        IndexRule()
    }
}

// ----- the lead ------------------------------------------------------------------------------------------------

/** What the lead and the strip show for one album, from a pick or a shelf album. */
internal class LeadItem(val artist: String, val title: String, val year: Int?, val genre: String?, val albumId: String?, val artworkUrl: String?, val owned: Boolean, val playCount: Int?)

private fun Pick.lead() = LeadItem(artist, album, year, genres.firstOrNull(), null, null, false, null)

private fun ShelfAlbum.lead() = LeadItem(artist, name, year, null, id.ifBlank { null }, artworkUrl, owned, playCount)

private fun Load<List<ShelfAlbum>>.leads(): Load<List<LeadItem>> = when (this) {
    Load.Loading -> Load.Loading
    is Load.Failed -> this
    is Load.Ready -> Load.Ready(value.map { it.lead() })
}

@Composable
private fun LeadSkeleton() {
    Row(Modifier.fillMaxWidth().padding(start = Gutter, end = Gutter, top = 16.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Skeleton(Modifier.size(168.dp))
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Skeleton(Modifier.width(80.dp).height(30.dp))
            Skeleton(Modifier.fillMaxWidth(0.8f).height(30.dp))
            Skeleton(Modifier.fillMaxWidth().height(12.dp))
            Skeleton(Modifier.fillMaxWidth(0.7f).height(12.dp))
        }
    }
}

@Composable
private fun Lead(tab: FlowHomeRules.Tab, item: LeadItem, at: Int, pick: Pick?, open: Opener, feedback: (FeedbackAction, Pick) -> Unit) {
    val p = LocalPalette.current
    val year = if (tab == FlowHomeRules.Tab.Picks) rememberAlbumYear(item.artist, item.title, item.year) else item.year
    val key = routeKey(item.artist, item.title)
    val openAlbum = { open.album(key, item.artist, item.title, item.albumId, year) }
    Row(Modifier.fillMaxWidth().padding(start = Gutter, end = Gutter, top = 16.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        AlbumCover(
            item.artist, item.title, item.artworkUrl,
            Modifier.size(168.dp).sharedCover(key).clickable(role = Role.Button, onClickLabel = "Open ${item.title}", onClick = openAlbum), rect = true,
        )
        Column(Modifier.weight(1f).heightIn(min = 168.dp), verticalArrangement = Arrangement.SpaceBetween) {
            Column {
                Text(IndexHomeRules.number(at), style = IndexType.index(), color = p.accent, maxLines = 1)
                Text(
                    item.title, style = IndexType.leadTitle(), color = p.text, maxLines = 3, overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.padding(top = 6.dp).clickable(role = Role.Button, onClick = openAlbum),
                )
            }
            IndexDataList(IndexHomeRules.dataRows(item.artist, year, item.genre, owned = tab != FlowHomeRules.Tab.Picks && item.owned))
        }
    }
    Row(Modifier.fillMaxWidth().padding(start = Gutter, end = 4.dp, top = 14.dp), horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
        if (tab == FlowHomeRules.Tab.Picks) { if (pick != null) PickActions(pick, feedback) } else PlayActions(item)
    }
}

/** Picks: Get album, Save and the three dots with "Not this album" and "Never suggest artist". */
@Composable
private fun androidx.compose.foundation.layout.RowScope.PickActions(pick: Pick, onFeedback: (FeedbackAction, Pick) -> Unit) {
    val hub = LocalAcquisitions.current
    var saved by remember(pick) { mutableStateOf(false) }
    var menu by remember(pick) { mutableStateOf(false) }
    IndexGetButton(
        indexGetOf(hub.getState(pick.artist, pick.album)), { hub.getAlbum(pick.artist, pick.album, pageMetadata(pick.artist, pick.album, pick.year, pick.releaseGroupMbid)) },
        idleLabel = "Get album", small = false,
    )
    IndexButton(if (saved) "Saved" else "Save", { saved = true; onFeedback(FeedbackAction.Save, pick) }, kind = IndexButtonKind.Ghost, icon = IndexIcons.Bookmark, enabled = !saved)
    Box(Modifier.weight(1f), contentAlignment = Alignment.CenterEnd) {
        IndexIconButton(IndexIcons.More, "More for ${pick.album}", { menu = true })
        DropdownMenu(menu, onDismissRequest = { menu = false }) {
            DropdownMenuItem(text = { Text("Not this album") }, onClick = { menu = false; onFeedback(FeedbackAction.Dismiss, pick) })
            DropdownMenuItem(text = { Text("Never suggest artist") }, onClick = { menu = false; onFeedback(FeedbackAction.DismissArtist, pick) })
        }
    }
}

/** New and Played: Play, Shuffle and the three dots with Play next and Add to queue. Only an album in the library can play. */
@Composable
private fun androidx.compose.foundation.layout.RowScope.PlayActions(item: LeadItem) {
    val play = LocalPlayActions.current
    val id = item.albumId
    var menu by remember(item) { mutableStateOf(false) }
    IndexButton("Play", { id?.let { play.playAlbum(it) } }, icon = IndexIcons.Play, enabled = id != null)
    IndexButton("Shuffle", { id?.let { play.playAlbum(it, shuffle = true) } }, kind = IndexButtonKind.Ghost, icon = IndexIcons.Shuffle, enabled = id != null)
    Box(Modifier.weight(1f), contentAlignment = Alignment.CenterEnd) {
        IndexIconButton(IndexIcons.More, "More for ${item.title}", { menu = true })
        DropdownMenu(menu, onDismissRequest = { menu = false }) {
            DropdownMenuItem(text = { Text("Play next") }, enabled = id != null, onClick = { menu = false; id?.let { play.queueAlbum(it, next = true) } })
            DropdownMenuItem(text = { Text("Add to queue") }, enabled = id != null, onClick = { menu = false; id?.let { play.queueAlbum(it, next = false) } })
        }
    }
}

// ----- the strip -----------------------------------------------------------------------------------------------

/** Items 02 to 05 in four columns with their numbers under them; a tap opens the album, a long press makes it the lead. */
@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun Strip(items: List<LeadItem>, shown: List<Int>, open: Opener, onLead: (Int) -> Unit, modifier: Modifier) {
    Row(modifier.fillMaxWidth().padding(start = Gutter, end = Gutter, top = 18.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        for (slot in 0 until IndexHomeRules.COLUMNS) {
            val index = shown.getOrNull(slot)
            val item = index?.let { items.getOrNull(it) }
            if (index == null || item == null) { Box(Modifier.weight(1f)); continue }
            val key = routeKey(item.artist, item.title)
            Column(
                Modifier.weight(1f).combinedClickable(
                    role = Role.Button, onClickLabel = "Open ${item.title}", onLongClickLabel = "Make ${item.title} the lead",
                    onClick = { open.album(key, item.artist, item.title, item.albumId, item.year) }, onLongClick = { onLead(index) },
                ),
                verticalArrangement = Arrangement.spacedBy(5.dp),
            ) {
                AlbumCover(item.artist, item.title, item.artworkUrl, Modifier.fillMaxWidth().aspectRatio(1f).sharedCover(key), rect = true)
                IndexLabel(IndexHomeRules.number(index))
            }
        }
    }
}

// ----- played --------------------------------------------------------------------------------------------------

@Composable
private fun Played(albums: List<ShelfAlbum>, listeningKnown: Boolean, taken: Set<String>, open: Opener, onAll: () -> Unit, modifier: Modifier) {
    Column(modifier) {
        if (albums.isEmpty()) {
            IndexSectionHead("Played", meta = if (listeningKnown) "Nothing yet" else null)
            Text(
                if (listeningKnown) IndexHomeRules.NOTHING_PLAYED else "Loading…", style = IndexType.rowTitle().copy(fontWeight = FontWeight.Medium, fontSize = 15.sp, lineHeight = 22.sp),
                color = LocalPalette.current.text, modifier = Modifier.padding(horizontal = Gutter).padding(top = 10.dp),
            )
            return@Column
        }
        IndexSectionHead("Played", meta = "This week", link = "All", onLink = onAll)
        Column(Modifier.padding(horizontal = Gutter)) {
            albums.forEachIndexed { i, album ->
                val key = routeKey(album.artist, album.name)
                IndexRow(
                    album.name, meta = IndexHomeRules.meta(album.artist, album.year), number = IndexHomeRules.number(i), divider = i < albums.size - 1,
                    onClick = { open.album(key, album.artist, album.name, album.id.ifBlank { null }, album.year) },
                    lead = { AlbumCover(album.artist, album.name, album.artworkUrl, Modifier.size(48.dp).then(if (key in taken) Modifier else Modifier.sharedCover(key)), rect = true) },
                    trail = { IndexHomeRules.plays(album.playCount)?.let { IndexLabel(it) } },
                )
            }
        }
    }
}

// ----- artists -------------------------------------------------------------------------------------------------

@Composable
private fun Artists(artists: List<HomeArtist>, counts: Map<String, Int>, listeningKnown: Boolean, open: Opener, onAll: () -> Unit, modifier: Modifier) {
    val p = LocalPalette.current
    Column(modifier) {
        val enough = HomeArtists.enough(artists)
        IndexSectionHead("Artists", meta = "You return to", link = if (enough) "All" else null, onLink = onAll)
        if (!enough) {
            Muted(if (listeningKnown) HomeArtists.EMPTY_SENTENCE else "Loading…", Modifier.padding(horizontal = Gutter).padding(top = 10.dp))
            return@Column
        }
        Row(Modifier.fillMaxWidth().padding(horizontal = Gutter).padding(top = 10.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            for (slot in 0 until IndexHomeRules.COLUMNS) {
                val artist = artists.getOrNull(slot)
                if (artist == null) { Box(Modifier.weight(1f)); continue }
                Column(Modifier.weight(1f).clickable(role = Role.Button) { open.artist(artist.name, null, artist.id.ifBlank { null }, null) }, verticalArrangement = Arrangement.spacedBy(5.dp)) {
                    ArtistPhoto(artist.name, null, Modifier.fillMaxWidth().aspectRatio(74f / 92f), rect = true)
                    Text(artist.name, color = p.text, maxLines = 2, overflow = TextOverflow.Ellipsis, style = IndexType.rowTitle().copy(fontSize = 12.5.sp, lineHeight = 15.sp))
                    GalleryHomeRules.albumCount(counts[artist.name.lowercase()])?.let { IndexLabel(it) }
                }
            }
        }
    }
}

// ----- radio ---------------------------------------------------------------------------------------------------

@Composable
private fun Radio(stations: List<RadioStation>, plays: List<RadioPlay>, now: Instant, onRadio: () -> Unit, modifier: Modifier) {
    val p = LocalPalette.current
    val radio = LocalRadio.current
    val live by radio.state.collectAsState()
    val plates = GalleryHomeRules.plates(stations, plays, now)
    Column(modifier) {
        IndexSectionHead("Radio", meta = plural(stations.size, "station"), link = "All", onLink = onRadio)
        Row(Modifier.fillMaxWidth().padding(horizontal = Gutter).padding(top = 10.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            for (slot in 0 until IndexHomeRules.COLUMNS) {
                val plate = plates.getOrNull(slot)
                if (plate == null) { Box(Modifier.weight(1f)); continue }
                Column(
                    Modifier.weight(1f).clickable(role = Role.Button, onClickLabel = "Play ${plate.station.name}") { radio.play(plate.station); onRadio() },
                    verticalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    StationLogo(plate.station)
                    Text(plate.station.name, color = p.text, maxLines = 2, overflow = TextOverflow.Ellipsis, style = IndexType.rowTitle().copy(fontSize = 12.5.sp, lineHeight = 15.sp))
                    if (plate.heard.isNotEmpty()) IndexLabel(plate.heard, color = if (plate.today) p.accent else p.textMuted)
                }
            }
        }
        val newest = GalleryHomeRules.newestPlays(plays)
        if (newest.isNotEmpty()) {
            Column(Modifier.fillMaxWidth().padding(horizontal = Gutter).padding(top = 16.dp)) {
                IndexLabel(GalleryHomeRules.heardHeading(newest.first(), now))
                newest.forEachIndexed { i, play ->
                    val download = live.downloadFor(play.id, play.grabbed, play.inLibrary)
                    val shown = play.copy(inLibrary = download == RadioDownload.Owned, grabbed = download == RadioDownload.Done || download == RadioDownload.Working)
                    IndexRow(
                        play.title, meta = GalleryHomeRules.playLine(play), divider = i < newest.size - 1,
                        lead = { Box(Modifier.size(48.dp).background(p.raised), contentAlignment = Alignment.Center) { Icon(IndexIcons.MusicNote, null, tint = p.textMuted, modifier = Modifier.size(IndexRules.ICON.dp)) } },
                        trail = {
                            when (GalleryHomeRules.trailing(shown)) {
                                GalleryHomeRules.Trailing.InLibrary -> IndexGetButton(IndexGet.Owned, {})
                                GalleryHomeRules.Trailing.Requested -> IndexGetButton(if (download == RadioDownload.Working) IndexGet.Pending else IndexGet.Requested, {})
                                GalleryHomeRules.Trailing.Get -> IndexGetButton(IndexGet.Idle, { radio.download(play.id) })
                                GalleryHomeRules.Trailing.None -> Unit
                            }
                        },
                    )
                }
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
        Text(GalleryHomeRules.initials(station.name), color = p.text, style = IndexType.section().copy(fontSize = 22.sp), maxLines = 1)
        Cover(radioLogoRequest(repo.absolute(station.logoUrl), 128), Modifier.fillMaxWidth().aspectRatio(1f), rect = true)
    }
}

// ----- this week -----------------------------------------------------------------------------------------------

@Composable
private fun ThisWeek(card: InsightCard, open: Opener, modifier: Modifier) {
    var why by remember(card.id) { mutableStateOf(false) }
    val artist = card.subject.artist
    val title = card.subject.title
    Column(modifier.padding(top = 16.dp)) {
        IndexInsightBlock(
            "${lensName(card.kind)} · this week", listOf(card.title, card.body).filter { it.isNotBlank() }.joinToString(" "),
            Modifier.padding(horizontal = Gutter), numeral = IndexHomeRules.insightNumeral(card.title),
        )
        if (why) Muted(InsightNarrative.why(card), Modifier.padding(horizontal = Gutter).padding(top = 10.dp))
        Row(Modifier.padding(start = Gutter, end = Gutter, top = 14.dp), horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
            // An insight names an album but carries no library id, so the button opens the album page (where Play is) rather than guessing.
            if (artist != null && title != null) IndexButton("Play", { open.album(routeKey(artist, title), artist, title, null, card.subject.year) }, icon = IndexIcons.Play, small = true)
            IndexButton(if (why) "Hide why" else "Why this?", { why = !why }, kind = IndexButtonKind.Ghost, small = true)
        }
    }
}

// ----- arrivals ------------------------------------------------------------------------------------------------

@Composable
private fun Arrivals(rows: List<ArrivalRow>, open: Opener, onDownloads: () -> Unit, modifier: Modifier) {
    val p = LocalPalette.current
    Column(modifier) {
        IndexSectionHead("Arrivals", link = "Downloads", onLink = onDownloads)
        Column(Modifier.padding(horizontal = Gutter)) {
            rows.forEachIndexed { i, row ->
                val job = row.job
                val live = row.stage < 4 && !row.failed
                val percent = job.progress?.percent?.takeIf { live }
                Column {
                    IndexRow(
                        job.album, meta = row.detail, divider = !(live || row.failed) && i < rows.size - 1,
                        onClick = { open.album(routeKey(job.artist, job.album), job.artist, job.album, null, null) },
                        lead = { AlbumCover(job.artist, job.album, null, Modifier.size(48.dp), rect = true) },
                        trail = {
                            when {
                                percent != null -> Text("${Math.round(percent)}%", style = IndexType.label(), color = p.accent)
                                row.stage >= 4 && !row.failed -> IndexLabel("In library", color = p.ok)
                                row.failed -> IndexLabel("Try again", color = p.chartRedText)
                            }
                        },
                    )
                    if (live || row.failed) {
                        IndexTracker(IndexHomeRules.trackerReached(row.stage), Modifier.padding(start = 60.dp, bottom = 8.dp), failedAt = if (row.failed) row.stage else -1)
                        if (i < rows.size - 1) IndexRule()
                    }
                }
            }
        }
    }
}

// ----- genres and the library line -----------------------------------------------------------------------------

/** Mono capitals, each name with its album count in `accent` beside it; a name opens its genre. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun Genres(state: Load<List<GenreTile>>, open: Opener, onAll: () -> Unit) {
    val p = LocalPalette.current
    Column {
        IndexSectionHead("Genres", link = "All", onLink = onAll)
        when (state) {
            Load.Loading -> Muted("Loading…", Modifier.padding(horizontal = Gutter).padding(top = 10.dp))
            is Load.Failed -> Muted(state.failure.message, Modifier.padding(horizontal = Gutter).padding(top = 10.dp))
            is Load.Ready -> {
                val tiles = remember(state.value) { state.value.shuffled().take(IndexHomeRules.GENRES_SHOWN) }
                FlowRow(Modifier.fillMaxWidth().padding(horizontal = Gutter).padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                    tiles.forEach { genre ->
                        Row(
                            Modifier.heightIn(min = 32.dp).clickable(role = Role.Button) { open.genre(genre.tag, genre.name) }
                                .semantics { contentDescription = "${genre.name}, " + plural(genre.albumCount, "album") },
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(genre.name.uppercase(), style = IndexType.label().copy(fontSize = 12.sp, lineHeight = 20.sp, letterSpacing = 0.04.em), color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis)
                            Text(genre.albumCount.toString(), style = IndexType.label().copy(fontSize = 9.sp, lineHeight = 9.sp), color = p.accent, modifier = Modifier.padding(start = 2.dp, bottom = 8.dp))
                        }
                    }
                }
            }
        }
    }
}

/** One mono line, the only stats on Home; it opens Library stats. */
@Composable
private fun LibraryLine(line: String, onStats: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().heightIn(min = 48.dp).clickable(role = Role.Button, onClick = onStats).padding(horizontal = Gutter, vertical = 16.dp).padding(top = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        IndexLabel("$line →", Modifier.weight(1f), maxLines = 2)
    }
}
