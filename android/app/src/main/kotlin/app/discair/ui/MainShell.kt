package app.discair.ui

import androidx.compose.foundation.layout.fillMaxSize
import app.discair.ui.common.Target
import app.discair.ui.common.RowDivider
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.Alignment
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.IconButton
import androidx.compose.material.icons.filled.Settings
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
    val repo = remember(state.saved) { container.repository(state.saved) }
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
                // Four labelled tabs cannot fit at 200% text: cap this bar at 130% so labels never split mid-word.
                if (onTopLevel) CompositionLocalProvider(
                    androidx.compose.ui.platform.LocalDensity provides androidx.compose.ui.unit.Density(
                        androidx.compose.ui.platform.LocalDensity.current.density,
                        minOf(androidx.compose.ui.platform.LocalDensity.current.fontScale, 1.3f),
                    ),
                ) { NavigationBar {
                    tabs.forEach { tab ->
                        NavigationBarItem(
                            selected = destination?.hasRoute(tab.route::class) == true,
                            onClick = {
                                nav.navigate(tab.route) {
                                    popUpTo(nav.graph.findStartDestination().id) { saveState = true }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = { Icon(tab.icon, contentDescription = null) },
                            label = { Text(tab.label, maxLines = 1) },
                        )
                    }
                } }
            },
        ) { padding ->
            NavHost(nav, startDestination = HomeRoute, modifier = Modifier.padding(padding).fillMaxSize()) {
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

/** The bar over every top-level page: the app name in the display face, Downloads (with the active count, as the web nav has) and Settings. */
@Composable
private fun AppHeader(active: Int, onDownloads: () -> Unit, onSettings: () -> Unit) {
    Column(Modifier.background(app.discair.ui.theme.Ink.Rail)) {
        Row(
            Modifier.fillMaxWidth().statusBarsPadding().heightIn(min = 56.dp).padding(start = 16.dp, end = 4.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                "DISCAIR", style = MaterialTheme.typography.headlineMedium,
                modifier = Modifier.weight(1f).semantics { heading() },
            )
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
