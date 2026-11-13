package app.discair.ui

import coil3.toBitmap
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Spacer
import androidx.compose.ui.graphics.Color
import androidx.compose.foundation.layout.fillMaxSize
import app.discair.ui.common.flowBackdropSource
import app.discair.ui.common.Target
import app.discair.ui.common.RowDivider
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.Alignment
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.IconButton
import androidx.compose.material.icons.filled.Info
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.background
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.draw.clip
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.clickable
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.automirrored.filled.List
import app.discair.ui.discover.DiscoverScreen
import app.discair.ui.search.SearchScreen
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.unit.dp
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavDestination.Companion.hasRoute
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.compose.animation.AnimatedContentTransitionScope
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.core.tween
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.animation.EnterTransition
import androidx.compose.animation.ExitTransition
import androidx.compose.animation.slideInVertically
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalDensity
import app.discair.ui.theme.MotionPlans
import app.discair.ui.theme.currentMotionFamily
import app.discair.ui.theme.rememberReducedMotion
import app.discair.ui.theme.toTween
import androidx.compose.ui.input.pointer.pointerInput
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.toRoute
import app.discair.AppContainer
import app.discair.AppViewModel
import app.discair.UiState
import app.discair.ui.album.AlbumScreen
import app.discair.ui.artist.ArtistScreen
import app.discair.ui.common.LocalAcquisitions
import app.discair.ui.common.LocalImageLoader
import app.discair.ui.downloads.DownloadsScreen
import app.discair.data.AcquisitionHub
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.Badge
import app.discair.ui.common.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import app.discair.ui.player.MiniPlayer
import app.discair.ui.player.NowPlayingSheet
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.contentDescription
import app.discair.R
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import app.discair.ui.common.LocalRepository
import app.discair.ui.home.HomeScreen
import app.discair.ui.library.LibraryScreen

/** Pages slide over each other, so each paints the app background: the one underneath must not show through. */
@Composable
private fun androidx.compose.animation.AnimatedVisibilityScope.Opaque(content: @Composable () -> Unit) {
    androidx.compose.runtime.CompositionLocalProvider(app.discair.ui.common.LocalNavVisibilityScope provides this) {
        Box(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) { content() }
    }
}

private fun androidx.navigation.NavDestination?.isHome() = this?.hasRoute(HomeRoute::class) == true

private data class Tab(val route: Any, val label: String, val icon: ImageVector)

/** Signed-in shell: bottom bar on the two top-level tabs, stack destinations for every page. */
@Composable
fun MainShell(state: UiState, model: AppViewModel, container: AppContainer) {
    val repo = remember(state.saved) { container.repository(state.saved, onSessionLost = model::sessionExpired) }
    val nav = rememberNavController()
    val scope = rememberCoroutineScope()
    val lifecycleOwner = androidx.lifecycle.compose.LocalLifecycleOwner.current
    val hub = remember(repo) { AcquisitionHub({ repo }, scope, Dispatchers.IO) }
    val snackbar = remember { SnackbarHostState() }
    DisposableEffect(hub) {
        hub.start()
        onDispose { hub.stop() }
    }
    // Outcomes of Get, retry, skip and dismiss: spoken by the snackbar, one at a time.
    LaunchedEffect(hub) { hub.messages.collect { snackbar.showSnackbar(it) } }
    // Playback: one controller for the whole signed-in session. It is created on first use.
    container.servers = state.saved
    val player = container.player
    val playerState by player.state.collectAsState()
    var nowPlayingOpen by rememberSaveable { mutableStateOf(false) }
    val context = androidx.compose.ui.platform.LocalContext.current
    val askNotifications = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { }
    var askedNotifications by rememberSaveable { mutableStateOf(false) }
    // The media notification needs this permission on Android 13; asked once, when playback first starts.
    LaunchedEffect(playerState.isPlaying) {
        if (playerState.isPlaying && !askedNotifications &&
            context.checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) != android.content.pm.PackageManager.PERMISSION_GRANTED
        ) {
            askedNotifications = true
            askNotifications.launch(android.Manifest.permission.POST_NOTIFICATIONS)
        }
    }
    val playActions = remember(repo) {
        app.discair.player.PlayActions(
            app.discair.player.OfflineAwareSongSource(
                app.discair.player.SubsonicSongSource(okhttp3.OkHttpClient(), { container.servers.let { Triple(it.navidromeUrl, it.navidromeUser, it.navidromePassword) } }),
                container.offline,
            ),
            player, scope, Dispatchers.IO, { id -> repo.absolute("/api/owned/artwork/$id") },
            offline = container.offline,
            sonic = { id, count -> repo.sonicSimilar(id, count) },
            sonicPath = { start, end, count -> repo.sonicPath(start, end, count) },
        )
    }
    val radio = remember(repo) {
        app.discair.player.RadioPlayback(
            player, scope, Dispatchers.IO,
            nowFor = { id -> repo.radioNowFor(id) },
            getPlay = { id -> repo.radioGetPlay(id) },
            saveFavourite = { id, wanted -> repo.setRadioFavourite(id, wanted) },
            absolute = { repo.absolute(it) },
            artwork = { url -> radioArtworkBytes(context, container.imageLoader, url) },
            inForeground = { lifecycleOwner.lifecycle.currentState.isAtLeast(androidx.lifecycle.Lifecycle.State.STARTED) },
        )
    }
    val sleepTimer = remember(player) { app.discair.player.SleepTimer(scope, onExpire = { player.pause() }) }
    LaunchedEffect(playerState.current?.isRadio) { if (playerState.current?.isRadio != true) sleepTimer.cancel() }
    val playerExtras = remember(repo) { app.discair.ui.player.PlayerExtras(peaks = { repo.songPeaks(it) }, facts = { repo.songFacts(it) }) }
    LaunchedEffect(playActions) { playActions.messages.collect { snackbar.showSnackbar(it) } }
    var islandPx by remember { mutableStateOf(0) }
    var islandTint by remember { mutableStateOf<Color?>(null) }
    LaunchedEffect(playerState.current?.coverUrl) { if (playerState.current?.coverUrl.isNullOrBlank()) islandTint = null }
    val clearance = with(androidx.compose.ui.platform.LocalDensity.current) { islandPx.toDp() }
    val entry by nav.currentBackStackEntryAsState()
    val destination = entry?.destination
    // The layout the owner chose (not the artwork tint): it decides which navigation is drawn and where Discover sits.
    val chosenLayout = (app.discair.ui.theme.LocalThemePalette.current ?: app.discair.ui.theme.LocalPalette.current).layout
    val rail = NavRules.railShown(LocalConfiguration.current.screenWidthDp)
    val playerLabel = playerState.current?.let { "Now playing: ${it.title}, ${it.artist}. Open player" } ?: "Player, nothing playing"
    // Motion (docs/design/redesign 7.4): tabs fade through, pages slide on a shared axis; nothing moves when the phone reduces motion.
    val motionFamily = currentMotionFamily()
    val reducedMotion = rememberReducedMotion()
    val density = LocalDensity.current
    val fadePlan = MotionPlans.fadeThrough(motionFamily, reducedMotion)
    val axisPlan = MotionPlans.sharedAxisX(motionFamily, reducedMotion)
    val risePx = with(density) { fadePlan.riseDp.dp.roundToPx() }
    val slidePx = with(density) { axisPlan.slideDp.dp.roundToPx() }
    val tabs = listOf(
        Tab(HomeRoute, "Home", Icons.Default.Home),
        Tab(DiscoverRoute, "Discover", Icons.Default.Star),
        Tab(LibraryRoute, "Library", Icons.AutoMirrored.Filled.List),
    )
    val onTopLevel = tabs.any { destination?.hasRoute(it.route::class) == true }
    val tabIndex = tabs.indexOfFirst { destination?.hasRoute(it.route::class) == true }
    // Discover, Library and Settings are buttons on Home now; they open as pages and Back returns to Home.
    val goPage: (Any) -> Unit = { route -> nav.navigate(route) { launchSingleTop = true } }
    val goHome: () -> Unit = {
        nav.navigate(HomeRoute) { popUpTo(nav.graph.findStartDestination().id); launchSingleTop = true }
    }
    /** The player button: opens Now Playing, or says nothing is playing. */
    val openPlayer: () -> Unit = {
        if (playerState.visible) nowPlayingOpen = true
        else scope.launch { snackbar.showSnackbar("Nothing is playing.") }
    }
    var searchOpen by rememberSaveable { mutableStateOf(false) }
    var searchText by rememberSaveable { mutableStateOf("") }
    /** Which top-level tab a route is, for choosing the slide direction; -1 for every other page. */
    fun indexOf(e: androidx.navigation.NavBackStackEntry) = tabs.indexOfFirst { e.destination.hasRoute(it.route::class) }

    val open = remember(nav) {
        Opener(
            artist = { name, key, id, mbid ->
                nav.navigate(ArtistRoute(key = key?.ifBlank { null } ?: app.discair.ui.common.routePart(name), name = name, id = id, mbid = mbid))
            },
            album = { key, artist, name, id, year -> nav.navigate(AlbumRoute(key, artist, name, id, year)) },
            genre = { tag, name -> nav.navigate(GenreRoute(tag, name)) },
            back = { nav.popBackStack() },
        )
    }

    CompositionLocalProvider(
        LocalBottomClearance provides clearance, LocalRepository provides repo, LocalImageLoader provides container.imageLoader, LocalAcquisitions provides hub,
        app.discair.ui.player.LocalPlayActions provides playActions,
        app.discair.ui.radio.LocalRadio provides radio,
        app.discair.ui.player.LocalPlayingNow provides playerState.current?.let {
            app.discair.ui.player.PlayingNow(it.albumId, it.title, playerState.isPlaying, it.track, it.disc)
        },
    ) {
        // Inside the provider: the sheet's cover needs the image loader, which only exists here.
        if (nowPlayingOpen && playerState.visible) {
            // The sheet is drawn over an artwork tint, which is dark whatever the theme: it keeps light text.
            app.discair.ui.theme.OnArtwork(keepBrutal = true) {
                if (playerState.current?.isRadio == true) app.discair.ui.radio.RadioNowPlayingSheet(
                    playerState, player, radio, sleepTimer, onDismiss = { nowPlayingOpen = false },
                    onOpenHeard = { nowPlayingOpen = false; nav.navigate(HeardRoute) { launchSingleTop = true } },
                ) else NowPlayingSheet(
                    playerState, player, container.lyrics, extras = playerExtras, settings = container.playerSettings, onDismiss = { nowPlayingOpen = false }, onSignIn = { nowPlayingOpen = false; model.sessionExpired() },
                    onOpenArtist = { song -> nowPlayingOpen = false; open.artist(song.artist, null, null, null) },
                    onOpenAlbum = { song ->
                        nowPlayingOpen = false
                        open.album(app.discair.ui.common.routeKey(song.artist, song.album), song.artist, song.album, song.albumId.ifBlank { null }, song.year)
                    },
                )
            }
        }
        if (searchOpen) {
            // Opening a result closes the sheet first, so the page opens on the app, not under the sheet.
            val fromSheet = Opener(
                artist = { n, k, i, m -> searchOpen = false; open.artist(n, k, i, m) },
                album = { k, a, n, i, y -> searchOpen = false; open.album(k, a, n, i, y) },
                genre = { t, n -> searchOpen = false; open.genre(t, n) },
                back = { searchOpen = false },
            )
            SearchSheet(searchText, { searchText = it }, fromSheet, onDismiss = { searchOpen = false })
        }
        Box(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxSize()) {
        if (rail) NavRail(
            homeSelected = destination?.hasRoute(HomeRoute::class) == true,
            discoverSelected = destination?.hasRoute(DiscoverRoute::class) == true,
            librarySelected = destination?.hasRoute(LibraryRoute::class) == true,
            playing = playerState.isPlaying,
            playerLabel = playerLabel,
            showPlayer = NavRules.playerButtonShown(chosenLayout),
            onHome = goHome,
            onDiscover = { goPage(DiscoverRoute) },
            onLibrary = { goPage(LibraryRoute) },
            onSearch = { searchOpen = true },
            onPlayer = openPlayer,
        )
        val flowBackdrop = app.discair.ui.common.rememberFlowBackdrop()
        Box(Modifier.weight(1f).fillMaxSize()) {
        androidx.compose.runtime.CompositionLocalProvider(app.discair.ui.common.LocalFlowBackdrop provides flowBackdrop) {
        Scaffold(
            // Flow's bars blur the page behind them; no other theme records it.
            modifier = if (app.discair.ui.common.isFlow()) Modifier.flowBackdropSource(flowBackdrop) else Modifier,
            snackbarHost = { SnackbarHost(snackbar, Modifier.padding(bottom = clearance)) },
            // Pages run behind the system navigation bar; the island and each page's end padding clear it.
            contentWindowInsets = androidx.compose.foundation.layout.WindowInsets(0),
            topBar = {
                if (onTopLevel) AppHeader(
                    active = hub.activeDownloads,
                    showDiscover = NavRules.discoverInTopBar(chosenLayout, rail),
                    onDiscover = { goPage(DiscoverRoute) },
                    onDownloads = { nav.navigate(DownloadsRoute) { launchSingleTop = true } },
                    onSettings = { goPage(SettingsRoute) },
                )
            },
        ) { padding ->
            Column(Modifier.padding(padding).fillMaxSize()) {
            OfflineBanner(repo.staleSince)
            val swipeThreshold = with(androidx.compose.ui.platform.LocalDensity.current) { 72.dp.toPx() }
            // On any page but Home, a drag nothing else used (carousels, rows and pagers take theirs first) to the right goes back.
            val swipe = if (!destination.isHome()) Modifier.pointerInput(Unit) {
                var total = 0f
                detectHorizontalDragGestures(
                    onDragStart = { total = 0f },
                    onDragCancel = { total = 0f },
                    onDragEnd = { if (total > swipeThreshold) nav.popBackStack() },
                ) { _, delta -> total += delta }
            } else Modifier
            @OptIn(androidx.compose.animation.ExperimentalSharedTransitionApi::class)
            androidx.compose.animation.SharedTransitionLayout(Modifier.weight(1f).fillMaxWidth()) {
            androidx.compose.runtime.CompositionLocalProvider(app.discair.ui.common.LocalSharedTransitionScope provides this) {
            NavHost(
                nav, startDestination = HomeRoute, modifier = Modifier.fillMaxSize().then(swipe),
                // Tab to tab fades through (the new tab rises a little); a push slides in on a shared axis from the right, and Back
                // (button or swipe) slides the page out to the right while the one under it comes back from the left.
                enterTransition = {
                    val tabToTab = indexOf(initialState) >= 0 && indexOf(targetState) >= 0
                    when {
                        reducedMotion -> EnterTransition.None
                        tabToTab -> fadeIn(fadePlan.arrive.toTween(fadePlan.arriveDelayMs)) +
                            slideInVertically(fadePlan.arrive.toTween(fadePlan.arriveDelayMs)) { risePx }
                        else -> slideInHorizontally(axisPlan.arrive.toTween()) { slidePx } + fadeIn(axisPlan.arrive.toTween())
                    }
                },
                exitTransition = {
                    val tabToTab = indexOf(initialState) >= 0 && indexOf(targetState) >= 0
                    when {
                        reducedMotion -> ExitTransition.None
                        tabToTab -> fadeOut(fadePlan.leave.toTween())
                        else -> slideOutHorizontally(axisPlan.leave.toTween()) { -slidePx } + fadeOut(axisPlan.leave.toTween())
                    }
                },
                popEnterTransition = {
                    val tabToTab = indexOf(initialState) >= 0 && indexOf(targetState) >= 0
                    when {
                        reducedMotion -> EnterTransition.None
                        tabToTab -> fadeIn(fadePlan.arrive.toTween(fadePlan.arriveDelayMs))
                        else -> slideInHorizontally(axisPlan.arrive.toTween()) { -slidePx } + fadeIn(axisPlan.arrive.toTween())
                    }
                },
                popExitTransition = {
                    when {
                        reducedMotion -> ExitTransition.None
                        else -> slideOutHorizontally(axisPlan.leave.toTween()) { slidePx } + fadeOut(axisPlan.leave.toTween())
                    }
                },
            ) {
                composable<HomeRoute> {
                    Opaque { HomeScreen(open, onRadio = { nav.navigate(RadioRoute) { launchSingleTop = true } }, onDownloads = { nav.navigate(DownloadsRoute) { launchSingleTop = true } }, onStats = { goPage(StatsRoute) }, onServer = { goPage(ServerRoute) }, onLibrary = { goPage(LibraryRoute) }) }
                }
                composable<DiscoverRoute> { Opaque { DiscoverScreen(open) } }
                composable<LibraryRoute> { Opaque { LibraryScreen(open) } }
                composable<DownloadsRoute> { Opaque { DownloadsScreen(open) } }
                composable<RadioRoute> { Opaque { app.discair.ui.radio.RadioScreen(onBack = { nav.popBackStack() }, onOpenHeard = { nav.navigate(HeardRoute) { launchSingleTop = true } }, onOpenPlayer = { nowPlayingOpen = true }) } }
                composable<HeardRoute> { Opaque { app.discair.ui.radio.HeardScreen(radio, onBack = { nav.popBackStack() }) } }
                composable<SettingsRoute> { Opaque { SettingsScreen(state, model, onBack = { nav.popBackStack() }, onEqualizer = { nav.navigate(EqualizerRoute) { launchSingleTop = true } }, onCrossfade = { nav.navigate(CrossfadeRoute) { launchSingleTop = true } }, onAppearance = { nav.navigate(AppearanceRoute) { launchSingleTop = true } }, onServer = { goPage(ServerRoute) }) } }
                composable<StatsRoute> { Opaque { app.discair.ui.stats.StatsScreen(onBack = { nav.popBackStack() }) } }
                composable<ServerRoute> { Opaque { app.discair.ui.settings.ServerScreen(navidromeDirect = state.navidrome.let { c -> when (c) { app.discair.Check.Ok -> true; is app.discair.Check.Failed -> false; else -> null } }, onBack = { nav.popBackStack() }) } }
                composable<AppearanceRoute> { Opaque { app.discair.ui.settings.AppearanceScreen(container.appearance, onBack = { nav.popBackStack() }) } }
                composable<EqualizerRoute> { Opaque { app.discair.ui.player.EqualizerScreen(container, onBack = { nav.popBackStack() }) } }
                composable<CrossfadeRoute> { Opaque { app.discair.ui.player.CrossfadeScreen(container, onBack = { nav.popBackStack() }) } }
                composable<ArtistRoute> { Opaque { ArtistScreen(it.toRoute(), open) } }
                composable<AlbumRoute> { Opaque { AlbumScreen(it.toRoute(), open) } }
                composable<GenreRoute> { Opaque { GenreScreen(it.toRoute(), open) } }
            }
            }
            }
            }
        }
        // The bottom navigation floats over the pages, with no bar behind it; a wide screen (600 dp and over) has the rail instead.
        // It is drawn over a dark artwork tint, so it keeps light icons on every theme. The mini player (Cassette Deck only) sits
        // above its bar while a song is queued. The hidden cover load below gives the island its tint.
        Column(Modifier.align(Alignment.BottomCenter).onSizeChanged { islandPx = it.height }) {
            if (app.discair.ui.common.TapeDeckRules.miniPlayerShown(app.discair.ui.theme.LocalPalette.current.layout, playerState.current != null)) {
                app.discair.ui.player.TapeMiniPlayer(playerState, player, onOpen = { if (playerState.visible) nowPlayingOpen = true })
            }
            if (app.discair.ui.theme.LocalPalette.current.layout == app.discair.ui.theme.Layout.CoverStack && playerState.current != null) {
                app.discair.ui.player.CoverStackMiniPlayer(playerState, player, onOpen = { if (playerState.visible) nowPlayingOpen = true }, modifier = Modifier.padding(bottom = if (rail) 12.dp else 8.dp))
            }
            if (app.discair.ui.theme.LocalPalette.current.layout == app.discair.ui.theme.Layout.Flow && playerState.current != null) {
                app.discair.ui.player.FlowMiniPlayer(playerState, player, onOpen = { if (playerState.visible) nowPlayingOpen = true }, modifier = Modifier.padding(bottom = if (rail) 12.dp else 8.dp))
            }
            if (!rail) app.discair.ui.theme.OnArtwork {
                NavIsland(
                    tint = islandTint,
                    homeSelected = destination?.hasRoute(HomeRoute::class) == true,
                    discoverSelected = destination?.hasRoute(DiscoverRoute::class) == true,
                    librarySelected = destination?.hasRoute(LibraryRoute::class) == true,
                    playing = playerState.isPlaying,
                    playerLabel = playerLabel,
                    onSearch = { searchOpen = true },
                    onHome = goHome,
                    onDiscover = { goPage(DiscoverRoute) },
                    onLibrary = { goPage(LibraryRoute) },
                    onPlayer = openPlayer,
                )
            }
        }
        }
        }
        }
        playerState.current?.coverUrl?.takeIf { it.isNotBlank() }?.let { url ->
            app.discair.ui.common.Cover(app.discair.ui.player.playerArtworkUrl(url), Modifier.size(1.dp), onColor = { islandTint = it })
        }
        }
    }
}

/**
 * The bar over Home, Discover and Library: the app name in the display face, then the actions. Discover is here only where the
 * navigation does not carry it (every layout but the Cassette Deck, and not on a rail). Downloads shows the active count, as the
 * web nav has. Settings is last.
 */
@Composable
private fun AppHeader(active: Int, showDiscover: Boolean, onDiscover: () -> Unit, onDownloads: () -> Unit, onSettings: () -> Unit) {
    if (app.discair.ui.theme.LocalPalette.current.layout == app.discair.ui.theme.Layout.Flow) {
        FlowAppHeader(active, showDiscover, onDiscover, onDownloads, onSettings)
        return
    }
    Column(Modifier.background(app.discair.ui.theme.Ink.Rail)) {
        Row(
            Modifier.fillMaxWidth().statusBarsPadding().heightIn(min = 56.dp).padding(start = 16.dp, end = 16.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            app.discair.ui.common.Wordmark(30.dp)
            Spacer(Modifier.weight(1f))
            if (showDiscover) HeaderButton("Discover", Icons.Default.Star, badge = 0, onClick = onDiscover)
            HeaderButton(if (active == 0) "Downloads" else "Downloads, $active active", app.discair.ui.player.PlayerIcons.Cloud, badge = active, onClick = onDownloads)
            HeaderButton("Settings", Icons.Default.Settings, badge = 0, onClick = onSettings)
        }
        RowDivider()
    }
}

/**
 * Flow's top bar (flow/home): the app name large on the page colour, 36dp round `raised` buttons for the actions, no rule under it. The
 * Downloads button carries the active count as a badge. Every other theme keeps [AppHeader] above.
 */
@Composable
private fun FlowAppHeader(active: Int, showDiscover: Boolean, onDiscover: () -> Unit, onDownloads: () -> Unit, onSettings: () -> Unit) {
    Row(
        Modifier.background(app.discair.ui.theme.Ink.Rail).fillMaxWidth().statusBarsPadding().heightIn(min = 56.dp).padding(start = 16.dp, end = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        app.discair.ui.common.Wordmark(30.dp)
        Spacer(Modifier.weight(1f))
        if (showDiscover) app.discair.ui.common.FlowCircleButton(Icons.Default.Star, "Discover", onDiscover)
        Box {
            app.discair.ui.common.FlowCircleButton(
                app.discair.ui.player.PlayerIcons.Cloud, if (active == 0) "Downloads" else "Downloads, $active active", onDownloads,
            )
            if (active > 0) Badge(Modifier.align(Alignment.TopEnd).padding(top = 4.dp, end = 4.dp)) { Text("$active") }
        }
        app.discair.ui.common.FlowCircleButton(Icons.Default.Settings, "Settings", onSettings)
    }
}

/** A square icon button in the top bar; a count badge shows on it when [badge] is above zero. Neobrut gets an outline and a hard shadow. */
@Composable
private fun HeaderButton(label: String, icon: ImageVector, badge: Int, onClick: () -> Unit) {
    val frame = RoundedCornerShape(6.dp)
    if (app.discair.ui.theme.LocalPalette.current.brutal) {
        app.discair.ui.common.BrutalIconButton(onClick = onClick, modifier = Modifier.size(48.dp, 40.dp).semantics { contentDescription = label }) {
            Box(contentAlignment = Alignment.Center) {
                Icon(icon, contentDescription = null, modifier = Modifier.size(22.dp))
                if (badge > 0) Badge(Modifier.align(Alignment.TopEnd).offset(x = 10.dp, y = (-8).dp)) { Text("$badge") }
            }
        }
    } else Box(
        Modifier.size(48.dp, 38.dp).clip(frame).background(app.discair.ui.theme.Ink.Surface)
            .border(1.dp, app.discair.ui.theme.Ink.EdgeStrong, frame)
            .clickable(role = Role.Button, onClick = onClick)
            .semantics { contentDescription = label },
        contentAlignment = Alignment.Center,
    ) {
        Icon(icon, contentDescription = null, tint = app.discair.ui.theme.Ink.TextMuted, modifier = Modifier.size(20.dp))
        if (badge > 0) Badge(Modifier.align(Alignment.TopEnd).padding(top = 4.dp, end = 4.dp)) { Text("$badge") }
    }
}

/**
 * Shown while pages are being answered from saved copies because the phone cannot reach Librarian.
 * Words and an icon say it; the line is announced politely when it appears.
 */
@Composable
private fun OfflineBanner(staleSince: Long?) {
    if (staleSince == null) return
    val saved = android.text.format.DateUtils.getRelativeTimeSpanString(
        staleSince, System.currentTimeMillis(), android.text.format.DateUtils.MINUTE_IN_MILLIS,
    )
    Row(
        Modifier.fillMaxWidth().background(app.discair.ui.theme.Ink.Raised).padding(horizontal = 16.dp, vertical = 8.dp)
            .semantics { liveRegion = androidx.compose.ui.semantics.LiveRegionMode.Polite },
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(Icons.Default.Info, contentDescription = null, tint = app.discair.ui.theme.Ink.Caution, modifier = Modifier.size(18.dp))
        Text(
            "Can't reach Librarian. Showing a copy saved $saved.",
            style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(start = 8.dp),
        )
    }
}

/** Search as a full-height sheet over the current page; the typed text is kept while the app is open. */
@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
private fun SearchSheet(text: String, onText: (String) -> Unit, open: Opener, onDismiss: () -> Unit) {
    app.discair.ui.common.ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = androidx.compose.material3.rememberModalBottomSheetState(skipPartiallyExpanded = true),
        containerColor = app.discair.ui.theme.Ink.Ink,
        shape = androidx.compose.ui.graphics.RectangleShape,
    ) {
        app.discair.ui.common.TransparentNavigationBar()
        CompositionLocalProvider(LocalBottomClearance provides 0.dp) { SearchScreen(open, text, onText) }
    }
}

/** A station logo or song cover as JPEG bytes for the notification and lock screen; null when it cannot be loaded. Kept small: it crosses the session. */
private suspend fun radioArtworkBytes(context: android.content.Context, loader: coil3.ImageLoader, url: String): ByteArray? {
    val result = loader.execute(coil3.request.ImageRequest.Builder(context).data(url).size(512).build())
    val bitmap = (result as? coil3.request.SuccessResult)?.image?.toBitmap() ?: return null
    return java.io.ByteArrayOutputStream().also { bitmap.compress(android.graphics.Bitmap.CompressFormat.JPEG, 85, it) }.toByteArray()
}
