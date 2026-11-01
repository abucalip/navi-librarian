package app.discair.ui

import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.Spacer
import androidx.compose.ui.graphics.Color
import androidx.compose.foundation.layout.fillMaxSize
import app.discair.ui.common.Target
import app.discair.ui.common.RowDivider
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.Alignment
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.IconButton
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Info
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Star
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
import androidx.compose.ui.unit.dp
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavDestination.Companion.hasRoute
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.compose.animation.AnimatedContentTransitionScope
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
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
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.contentDescription
import app.discair.R
import kotlinx.coroutines.Dispatchers
import app.discair.ui.common.LocalRepository
import app.discair.ui.home.HomeScreen
import app.discair.ui.library.LibraryScreen

private data class Tab(val route: Any, val label: String, val icon: ImageVector)

/** Signed-in shell: bottom bar on the two top-level tabs, stack destinations for every page. */
@Composable
fun MainShell(state: UiState, model: AppViewModel, container: AppContainer) {
    val repo = remember(state.saved) { container.repository(state.saved, onSessionLost = model::sessionExpired) }
    val nav = rememberNavController()
    val scope = rememberCoroutineScope()
    val hub = remember(repo) { AcquisitionHub({ repo }, scope, Dispatchers.IO) }
    val snackbar = remember { SnackbarHostState() }
    DisposableEffect(hub) {
        hub.start()
        onDispose { hub.stop() }
    }
    // Outcomes of Get, retry, skip and dismiss: spoken by the snackbar, one at a time.
    LaunchedEffect(hub) { hub.messages.collect { snackbar.showSnackbar(it) } }
    val entry by nav.currentBackStackEntryAsState()
    val destination = entry?.destination
    val tabs = listOf(
        Tab(HomeRoute, "Home", Icons.Default.Home),
        Tab(DiscoverRoute, "Discover", Icons.Default.Star),
        Tab(SearchRoute, "Search", Icons.Default.Search),
        Tab(LibraryRoute, "Library", Icons.AutoMirrored.Filled.List),
    )
    val onTopLevel = tabs.any { destination?.hasRoute(it.route::class) == true }
    val tabIndex = tabs.indexOfFirst { destination?.hasRoute(it.route::class) == true }
    val goTab: (Tab) -> Unit = { tab ->
        nav.navigate(tab.route) {
            popUpTo(nav.graph.findStartDestination().id) { saveState = true }
            launchSingleTop = true
            restoreState = true
        }
    }
    /** Which top-level tab a route is, for choosing the slide direction; -1 for every other page. */
    fun indexOf(e: androidx.navigation.NavBackStackEntry) = tabs.indexOfFirst { e.destination.hasRoute(it.route::class) }

    val open = remember(nav) {
        Opener(
            artist = { name, key, id, mbid ->
                nav.navigate(ArtistRoute(key = key?.ifBlank { null } ?: name.trim().lowercase(), name = name, id = id, mbid = mbid))
            },
            album = { key, artist, name, id, year -> nav.navigate(AlbumRoute(key, artist, name, id, year)) },
            genre = { tag, name -> nav.navigate(GenreRoute(tag, name)) },
            back = { nav.popBackStack() },
        )
    }

    CompositionLocalProvider(
        LocalRepository provides repo, LocalImageLoader provides container.imageLoader, LocalAcquisitions provides hub,
    ) {
        Scaffold(
            snackbarHost = { SnackbarHost(snackbar) },
            topBar = {
                if (onTopLevel) AppHeader(
                    active = hub.activeDownloads,
                    onDownloads = { nav.navigate(DownloadsRoute) { launchSingleTop = true } },
                    onSettings = { nav.navigate(SettingsRoute) },
                )
            },
            bottomBar = {
                if (onTopLevel) NavigationBar {
                    tabs.forEach { tab ->
                        NavigationBarItem(
                            selected = destination?.hasRoute(tab.route::class) == true,
                            onClick = { goTab(tab) },
                            // Icons only; the name is still spoken by TalkBack.
                            icon = { Icon(tab.icon, contentDescription = tab.label) },
                        )
                    }
                }
            },
        ) { padding ->
            Column(Modifier.padding(padding).fillMaxSize()) {
            OfflineBanner(repo.staleSince)
            val swipeThreshold = with(androidx.compose.ui.platform.LocalDensity.current) { 72.dp.toPx() }
            // Swiping sideways on a top-level page moves to the next tab. Carousels and rows inside the
            // page take their own swipes first; only a drag nothing else used reaches this.
            val swipe = if (!onTopLevel) Modifier.pointerInput(Unit) {
                // On an artist, album, genre or other stacked page, a swipe to the right goes back.
                var total = 0f
                detectHorizontalDragGestures(
                    onDragStart = { total = 0f },
                    onDragCancel = { total = 0f },
                    onDragEnd = { if (total > swipeThreshold) nav.popBackStack() },
                ) { _, delta -> total += delta }
            } else Modifier.pointerInput(tabIndex) {
                var total = 0f
                detectHorizontalDragGestures(
                    onDragStart = { total = 0f },
                    onDragCancel = { total = 0f },
                    onDragEnd = {
                        val target = tabIndex + if (total < -swipeThreshold) 1 else if (total > swipeThreshold) -1 else 0
                        if (target != tabIndex && target in tabs.indices) goTab(tabs[target])
                    },
                ) { _, delta -> total += delta }
            }
            NavHost(
                nav, startDestination = HomeRoute, modifier = Modifier.weight(1f).fillMaxWidth().then(swipe),
                enterTransition = {
                    val from = indexOf(initialState); val to = indexOf(targetState)
                    if (from >= 0 && to >= 0) slideIntoContainer(
                        if (to > from) AnimatedContentTransitionScope.SlideDirection.Start else AnimatedContentTransitionScope.SlideDirection.End,
                    ) else fadeIn()
                },
                exitTransition = {
                    val from = indexOf(initialState); val to = indexOf(targetState)
                    if (from >= 0 && to >= 0) slideOutOfContainer(
                        if (to > from) AnimatedContentTransitionScope.SlideDirection.Start else AnimatedContentTransitionScope.SlideDirection.End,
                    ) else fadeOut()
                },
                popEnterTransition = { fadeIn() },
                popExitTransition = { fadeOut() },
            ) {
                composable<HomeRoute> { HomeScreen(open) }
                composable<DiscoverRoute> { DiscoverScreen(open) }
                composable<SearchRoute> { SearchScreen(open) }
                composable<LibraryRoute> { LibraryScreen(open) }
                composable<DownloadsRoute> { DownloadsScreen(open) }
                composable<SettingsRoute> { SettingsScreen(state, model, onBack = { nav.popBackStack() }) }
                composable<ArtistRoute> { ArtistScreen(it.toRoute(), open) }
                composable<AlbumRoute> { AlbumScreen(it.toRoute(), open) }
                composable<GenreRoute> { GenreScreen(it.toRoute(), open) }
            }
            }
        }
    }
}

/** The bar over every top-level page: the app name in the display face, Downloads (with the active count, as the web nav has) and Settings. */
@Composable
private fun AppHeader(active: Int, onDownloads: () -> Unit, onSettings: () -> Unit) {
    Column(Modifier.background(app.discair.ui.theme.Ink.Rail)) {
        Row(
            Modifier.fillMaxWidth().statusBarsPadding().heightIn(min = 56.dp).padding(start = 16.dp, end = 4.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                painterResource(R.drawable.ic_wordmark), contentDescription = "Discair", tint = Color.Unspecified,
                modifier = Modifier.weight(1f, fill = false).height(30.dp).semantics { heading() },
            )
            Spacer(Modifier.weight(1f))
            IconButton(onClick = onDownloads, Modifier.size(Target)) {
                val label = if (active == 0) "Downloads" else "Downloads, $active active"
                BadgedBox(
                    badge = { if (active > 0) Badge { Text("$active") } },
                    modifier = Modifier.semantics { contentDescription = label },
                ) { Icon(painterResource(R.drawable.ic_get_cloud), contentDescription = null) }
            }
            IconButton(onClick = onSettings, Modifier.size(Target)) {
                Icon(Icons.Default.Settings, contentDescription = "Settings")
            }
        }
        RowDivider()
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
