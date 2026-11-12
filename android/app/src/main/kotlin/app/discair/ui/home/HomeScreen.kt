package app.discair.ui.home

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.ui.semantics.Role
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.runtime.mutableStateListOf
import app.discair.ui.theme.enterStagger
import java.time.Instant
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import app.discair.ui.common.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.PlatformTextStyle
import androidx.compose.ui.text.style.LineHeightStyle
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.data.Shelves
import app.discair.model.GenreTile
import app.discair.model.Pick
import app.discair.model.ShelfAlbum
import app.discair.ui.Opener
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.GetAlbumButton
import app.discair.ui.common.pageMetadata
import app.discair.ui.common.Load
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.PageHeading
import app.discair.ui.common.Panel
import app.discair.ui.common.Target
import app.discair.ui.common.aspectSquare
import app.discair.ui.common.genreHue
import app.discair.ui.common.plural
import app.discair.ui.common.rememberAlbumYear
import app.discair.ui.common.rememberLoad
import app.discair.ui.common.routeKey
import app.discair.ui.theme.Ink
import app.discair.ui.theme.brutalShadow
import app.discair.ui.theme.forTheme
import kotlinx.coroutines.launch

/** The genre row shows this many, drawn at random each time Home opens. */
private const val GENRES_SHOWN = 6

@Composable
fun HomeScreen(open: Opener, onRadio: () -> Unit = {}, onDownloads: () -> Unit = {}, onStats: () -> Unit = {}, onServer: () -> Unit = {}) {
    val repo = LocalRepository.current
    val hub = app.discair.ui.common.LocalAcquisitions.current
    val now = remember { Instant.now() }
    val picks = rememberLoad("picks") { repo.picks(10).items }
    val genres = rememberLoad("genres") { repo.genres().items }
    val library = rememberLoad("dashboard_library") { DashboardRules.read(repo, now) }
    val taste = rememberLoad("dashboard_taste") { repo.taste() }
    val insights = rememberLoad("dashboard_insights") { repo.insights(20) }
    val layout = app.discair.ui.theme.currentLayout()
    val sheetStack = layout == app.discair.ui.theme.Layout.SheetStack
    // Sticker Wall: the picks are a wall of tilted, stickered tiles; it keeps that form inside module 3.
    val stickerWall = layout == app.discair.ui.theme.Layout.StickerWall
    val gone = remember { mutableStateListOf<String>() }
    val feedback = rememberPickFeedback { pick -> gone += pick.artist + "/" + pick.album }
    val pickList = (picks.state as? Load.Ready)?.value.orEmpty().filter { (it.artist + "/" + it.album) !in gone }
    val libraryRead = (library.state as? Load.Ready)?.value
    val jobs = hub.jobs

    val data = DashboardData(
        hero = libraryRead?.let { DashboardRules.hero(it, now) },
        heroLoading = library.state is Load.Loading,
        listens = DashboardRules.listens((taste.state as? Load.Ready)?.value?.listensByDay),
        listensLoaded = taste.state !is Load.Loading,
        waiting = DashboardRules.waiting((picks.state as? Load.Ready)?.let { pickList.size }, jobs),
        arrivals = DashboardRules.arrivals(jobs),
        picks = pickList,
        picksState = picks.state,
        retryPicks = picks.reload,
        tasteProfiles = (taste.state as? Load.Ready)?.value?.profiles,
        tasteLoaded = taste.state !is Load.Loading,
        tasteFailed = taste.state is Load.Failed,
        insight = DashboardRules.insightOfTheDay((insights.state as? Load.Ready)?.value, emptySet(), java.time.LocalDate.now().toEpochDay()),
        libraryRead = libraryRead,
        libraryLoading = library.state is Load.Loading,
        now = now,
        problem = hub.listProblem,
    )
    val banner = DashboardRules.banner(data.problem)

    @Composable
    fun Module(m: DashModule, wide: Boolean) {
        when (m) {
            DashModule.Hero -> HeroModule(data.hero, data.heroLoading)
            DashModule.Stats -> StatRow(data.listens, data.listensLoaded, data.waiting, wide, onWaiting = {}, onStats = onStats)
            DashModule.Pick -> Box(Modifier.heightIn(min = 120.dp)) {
                when (val state = data.picksState) {
                    Load.Loading -> Muted("Loading…")
                    is Load.Failed -> Inline(state.failure.message, data.retryPicks)
                    is Load.Ready ->
                        if (data.picks.isEmpty()) Muted("Nothing recommended right now.")
                        else if (stickerWall) StickerPicksWall(data.picks.take(app.discair.ui.common.StickerWallRules.WALL_TILES), open)
                        else TodaysPick(data.picks, open, feedback)
                }
            }
            DashModule.Arrivals ->
                if (sheetStack) SheetRequestsSection(open)
                else if (data.arrivals.isNotEmpty()) Box(Modifier.padding(horizontal = if (wide) 0.dp else 16.dp)) { ArrivalsModule(data.arrivals, open, onDownloads) }
            DashModule.Taste -> if (!data.tasteFailed || data.tasteProfiles != null) {
                Box(Modifier.padding(horizontal = if (wide) 0.dp else 16.dp)) { TasteModule(data.tasteProfiles, data.tasteLoaded) }
            }
            DashModule.Insight -> data.insight?.let { Box(Modifier.padding(horizontal = if (wide) 0.dp else 16.dp)) { InsightModule(it, open) } }
            DashModule.Numbers -> Box(Modifier.padding(horizontal = if (wide) 0.dp else 16.dp)) { LibraryNumbers(data.libraryRead, data.libraryLoading, data.now, onStats) }
            DashModule.Shelves -> Column {
                RecentlyAddedSection(open)
                ShelfRow(Shelves.Recent.path, "Recently played", open) { repo.shelf(Shelves.Recent, 20).items }
            }
            DashModule.Genres -> Column {
                PageHeading("Genres", Modifier.padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 8.dp))
                when (val state = genres.state) {
                    Load.Loading -> Muted("Loading…")
                    is Load.Failed -> Inline(state.failure.message, genres.reload)
                    is Load.Ready -> GenreRow(state.value, open)
                }
            }
            DashModule.Radio -> Row(
                Modifier.fillMaxWidth().heightIn(min = 56.dp).clickable(role = Role.Button, onClick = onRadio).padding(horizontal = 16.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("Radio", style = MaterialTheme.typography.titleMedium, modifier = Modifier.semantics { heading() })
                Spacer(Modifier.weight(1f))
                Text("Stations", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            DashModule.Server -> ServerRow(data.problem, onServer)
        }
    }

    BoxWithConstraints(Modifier.fillMaxWidth()) {
        val wide = maxWidth >= DashboardRules.TWO_PANE_MIN_DP.dp
        val bottom = 24.dp + app.discair.ui.LocalBottomClearance.current
        if (wide) {
            Row(Modifier.fillMaxWidth().padding(horizontal = 24.dp), horizontalArrangement = Arrangement.spacedBy(24.dp)) {
                LazyColumn(Modifier.weight(2f), contentPadding = PaddingValues(top = 16.dp, bottom = bottom), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                    banner?.let { item(key = "banner") { DashboardBanner(it) } }
                    itemsIndexed(DashModule.primary, key = { _, m -> m.name }) { i, m -> Box(Modifier.enterStagger(i)) { Module(m, true) } }
                }
                LazyColumn(Modifier.weight(1f), contentPadding = PaddingValues(top = 16.dp, bottom = bottom), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                    itemsIndexed(DashModule.secondary, key = { _, m -> m.name }) { i, m -> Box(Modifier.enterStagger(i)) { Module(m, true) } }
                }
            }
        } else {
            LazyColumn(Modifier.fillMaxWidth(), contentPadding = PaddingValues(top = 16.dp, bottom = bottom), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                banner?.let { item(key = "banner") { DashboardBanner(it) } }
                itemsIndexed(DashModule.phone, key = { _, m -> m.name }) { i, m -> Box(Modifier.enterStagger(i)) { Module(m, false) } }
            }
        }
    }
}

@Composable
internal fun Muted(text: String) {
    Text(text, Modifier.padding(horizontal = 16.dp, vertical = 8.dp), color = MaterialTheme.colorScheme.onSurfaceVariant)
}

@Composable
internal fun Inline(message: String, retry: () -> Unit) {
    Column(Modifier.padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(message, color = Ink.ChartRedText, style = MaterialTheme.typography.bodyMedium)
        OutlinedButton(onClick = retry, Modifier.heightIn(min = Target)) { Text("Try again") }
    }
}

/** A slideable row of genre tiles: the name only. A new random few each time Home opens. */
@Composable
private fun GenreRow(all: List<GenreTile>, open: Opener) {
    val tiles = remember(all) { all.shuffled().take(GENRES_SHOWN) }
    LazyRow(contentPadding = PaddingValues(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        items(tiles, key = { it.tag }) { genre ->
            val brutal = app.discair.ui.theme.LocalPalette.current.brutal
            val tile = app.discair.ui.theme.themeShape(6.dp)
            // Neobrut: a tile filled with the genre's own hue, outlined, with a hard shadow-sm and black text (the hue is the same one the web uses).
            val hue = Color.hsv(app.discair.ui.common.genreHue(genre.tag).toFloat(), 0.42f, 0.97f)
            Row(
                Modifier.heightIn(min = Target)
                    .then(if (brutal) Modifier.brutalShadow(tile, 0.6f) else Modifier)
                    .clip(tile)
                    .background(if (brutal) hue else MaterialTheme.colorScheme.surfaceVariant)
                    .then(if (brutal) Modifier.border(app.discair.ui.theme.brutalOutline(), tile) else Modifier)
                    .clickable(role = Role.Button) { open.genre(genre.tag, genre.name) }
                    .semantics { contentDescription = "${genre.name}, " + plural(genre.albumCount, "album") },
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    genre.name, style = if (brutal) MaterialTheme.typography.bodyMedium.copy(fontWeight = androidx.compose.ui.text.font.FontWeight.Bold) else MaterialTheme.typography.bodyMedium,
                    color = if (brutal) Color.Black else MaterialTheme.colorScheme.onSurface, maxLines = 1,
                    overflow = TextOverflow.Ellipsis, modifier = Modifier.padding(horizontal = 16.dp),
                )
            }
        }
    }
}

@Composable
private fun ShelfRow(shelf: String, title: String, open: Opener, load: () -> List<ShelfAlbum>) {
    val loaded = rememberLoad(shelf) { load() }
    PageHeading(title, Modifier.padding(start = 16.dp, end = 16.dp, top = 24.dp, bottom = 8.dp))
    when (val state = loaded.state) {
        Load.Loading -> Muted("Loading…")
        is Load.Failed -> Inline(state.failure.message, loaded.reload)
        is Load.Ready -> if (state.value.isEmpty()) Muted("Nothing here yet.") else LazyRow(
            contentPadding = PaddingValues(horizontal = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            items(state.value, key = { it.id.ifBlank { it.artist + '/' + it.name } }) { album: ShelfAlbum ->
                Panel(Modifier.width(208.dp).clickable(role = Role.Button) {
                    open.album(routeKey(album.artist, album.name), album.artist, album.name, album.id, album.year)
                }) {
                    Column {
                        Box {
                            AlbumCover(album.artist, album.name, album.artworkUrl, Modifier.fillMaxWidth().aspectSquare(), rect = true)
                            // Only an album in the library can play; its id is the Navidrome album id.
                            if (album.owned) {
                                val play = app.discair.ui.player.LocalPlayActions.current
                                app.discair.ui.common.CheckBadge(
                                    Modifier.align(Alignment.BottomEnd).padding(8.dp),
                                    onPlay = album.id.takeIf { it.isNotBlank() }?.let { id -> { play.playAlbum(id) } },
                                    label = album.name,
                                )
                            }
                        }
                        Column(Modifier.padding(16.dp).heightIn(min = 76.dp)) {
                            Text(
                                album.name, style = MaterialTheme.typography.titleLarge,
                                maxLines = 2, overflow = TextOverflow.Ellipsis,
                            )
                            album.year?.let {
                                Text("$it", style = MaterialTheme.typography.labelMedium.copy(fontFamily = app.discair.ui.theme.LocalFontPair.current.mono), color = Ink.Accent)
                            }
                            if (album.artist.isNotBlank()) Text(
                                album.artist, style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis,
                            )
                        }
                    }
                }
            }
        }
    }
}
