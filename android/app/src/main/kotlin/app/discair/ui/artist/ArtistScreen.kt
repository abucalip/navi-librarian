package app.discair.ui.artist

import app.discair.ui.common.sharedCover
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.ui.semantics.Role
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import app.discair.ui.common.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.model.ArtistPage
import app.discair.ui.ArtistRoute
import app.discair.ui.Opener
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.ArtistCircle
import app.discair.ui.common.ArtistPhoto
import app.discair.ui.common.CheckBadge
import app.discair.ui.common.GetAlbumButton
import app.discair.ui.common.GetSongButton
import app.discair.ui.common.pageMetadata
import app.discair.ui.common.Heading
import app.discair.ui.common.LoadView
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.OverlayBack
import app.discair.ui.common.OwnedMark
import app.discair.ui.common.Panel
import app.discair.ui.common.RankNumeral
import app.discair.ui.common.ReadMore
import app.discair.ui.common.RowDivider
import app.discair.ui.common.SimilarArtistsRow
import app.discair.ui.common.Target
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import app.discair.ui.common.TintedPage
import app.discair.ui.common.abbreviate
import app.discair.ui.common.aspectSquare
import app.discair.ui.common.plural
import app.discair.ui.common.rememberLoad
import app.discair.ui.common.rememberStreamLoad
import app.discair.ui.theme.Ink

private const val SONGS_SHOWN = 5
private const val ALBUMS_SHOWN = 6
private const val SIMILAR_SHOWN = 5
private const val MISSING_SHOWN = 10

@Composable
fun ArtistScreen(route: ArtistRoute, open: Opener) {
    val repo = LocalRepository.current
    val loaded = rememberStreamLoad<ArtistPage>(route) { show -> repo.artistPageStream(route.key, route.id, route.name, route.mbid, show) }
    var tint by remember(route) { mutableStateOf<Color?>(null) }
    val list = androidx.compose.foundation.lazy.rememberLazyListState()
    // The paths entry shows only when the server reports the feature (live, never from the saved copies).
    var pathsOn by remember(route) { mutableStateOf(false) }
    LaunchedEffect(route) { pathsOn = withContext(Dispatchers.IO) { repo.pathsAvailable() } }
    TintedPage(tint, list) {
        LoadView(loaded) { page -> ArtistContent(route, page, open, list, onTint = { tint = it }, pathsOn = pathsOn) }
        // Back stays reachable while the page loads or fails.
        if (loaded.state !is app.discair.ui.common.Load.Ready) {
            OverlayBack(open.back, Modifier.statusBarsPadding().padding(16.dp))
        }
    }
}

@Composable
private fun ArtistContent(route: ArtistRoute, page: ArtistPage, open: Opener, list: androidx.compose.foundation.lazy.LazyListState, onTint: (Color) -> Unit, pathsOn: Boolean) {
    val sections = page.sections
    val info = sections.artist.artist
    val name = info?.name?.ifBlank { null } ?: route.name
    var showAllAlbums by remember { mutableStateOf(false) }
    var showAllMissing by remember { mutableStateOf(false) }
    var showAllSongs by remember { mutableStateOf(false) }
    // Saved with the page: opening an album from the sheet leaves this page, and Back must find the sheet open again.
    var showPaths by androidx.compose.runtime.saveable.rememberSaveable(route) { mutableStateOf(false) }
    val pathsMbid = (route.mbid ?: info?.mbid)?.takeIf { it.isNotBlank() }
    // LIB-05: five similar artists chosen at random on each page load. Variety only; the server's list is the source.
    val similar = remember(page) { sections.similar.items.shuffled().take(SIMILAR_SHOWN) }
    val owned = sections.ownedAlbums.items
    val collage by rememberArtistCollage(owned)
    val artistId = (info?.id ?: route.id)?.takeIf { it.isNotBlank() && owned.isNotEmpty() }
    val play = app.discair.ui.player.LocalPlayActions.current

    if (showPaths && pathsMbid != null) ArtistPathsSheet(name, pathsMbid, open) { showPaths = false }

    // Soft Brut: its own arrangement, in CoverStackArtist.kt; every other theme continues below unchanged.
    if (app.discair.ui.theme.LocalPalette.current.layout == app.discair.ui.theme.Layout.CoverStack) {
        CoverStackArtistContent(
            CoverStackArtistData(
                route, name, sections, owned, info?.albumCount, info?.owned == true, artistId, similar, collage,
                pathsOn && pathsMbid != null, { showPaths = true },
            ),
            open, list, showAllSongs, { showAllSongs = true }, showAllMissing, { showAllMissing = true },
        )
        return
    }

    // Flow: its own arrangement, in FlowArtist.kt.
    if (app.discair.ui.common.isFlow()) {
        FlowArtistContent(
            CoverStackArtistData(
                route, name, sections, owned, info?.albumCount, info?.owned == true, artistId, similar, collage,
                pathsOn && pathsMbid != null, { showPaths = true },
            ),
            open, list, showAllSongs, { showAllSongs = true }, showAllMissing, { showAllMissing = true },
        )
        return
    }

    LazyColumn(Modifier.fillMaxSize(), state = list, contentPadding = PaddingValues(bottom = 32.dp + app.discair.ui.LocalBottomClearance.current)) {
        item {
            Box(
                Modifier.statusBarsPadding().padding(16.dp).fillMaxWidth().height(300.dp)
                    .clip(RoundedCornerShape(12.dp)),
            ) {
                ArtistPhoto(name, owned.firstOrNull()?.artworkUrl, Modifier.fillMaxSize(), onColor = onTint)
                Box(
                    Modifier.fillMaxSize().background(
                        Brush.verticalGradient(listOf(Color.Transparent, Ink.Ink.copy(alpha = 0.92f)), startY = 120f),
                    ),
                )
                OverlayBack(open.back, Modifier.align(Alignment.TopStart).padding(16.dp), onPhoto = true)
                Column(Modifier.align(Alignment.BottomStart).padding(16.dp)) {
                    Text(
                        name, style = MaterialTheme.typography.headlineLarge,
                        maxLines = 2, overflow = TextOverflow.Ellipsis, modifier = Modifier.semantics { heading() },
                    )
                    val genres = sections.tags.items.map { it.name }.ifEmpty { listOfNotNull(info?.genre) }.take(3)
                    if (genres.isNotEmpty()) Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                        genres.forEach { g ->
                            Text(
                                g, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.heightIn(min = Target).clickable(role = Role.Button) { open.genre(g.lowercase(), g) }.padding(vertical = 16.dp),
                            )
                        }
                    }
                    Text(
                        if (info?.owned == true) plural(info.albumCount, "album") + " in your library" else "Not in your library",
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
            }
        }
        val canPaths = pathsOn && pathsMbid != null
        if (artistId != null || canPaths) item {
            app.discair.ui.player.PlayRow(
                onPlay = artistId?.let { id -> { play.playArtist(id, shuffle = false) } },
                onShuffle = artistId?.let { id -> { play.playArtist(id, shuffle = true) } },
                onPaths = if (canPaths) ({ showPaths = true }) else null,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
            )
        }
        val allSongs = sections.topSongs.items
        val songs = if (showAllSongs) allSongs else allSongs.take(SONGS_SHOWN)
        if (songs.isNotEmpty()) {
            item {
                Panel(Modifier.padding(horizontal = 16.dp, vertical = 4.dp).fillMaxWidth()) {
                    Column(Modifier.padding(16.dp)) {
                        Text(
                            "Top songs", style = MaterialTheme.typography.headlineMedium,
                            modifier = Modifier.padding(bottom = 8.dp).semantics { heading() },
                        )
                        songs.forEachIndexed { i, song ->
                            if (i > 0) RowDivider()
                            val onAlbum = song.album?.takeIf { it.isNotBlank() }
                            // An owned top song plays from its album when the album is in the library.
                            val albumId = onAlbum?.let { a -> owned.firstOrNull { it.name.equals(a, ignoreCase = true) }?.id }?.takeIf { it.isNotBlank() }
                            Row(
                                Modifier.fillMaxWidth().heightIn(min = 64.dp)
                                    .let { if (song.owned && albumId != null) it.clickable(onClickLabel = "Play ${song.name}", role = Role.Button) { play.playAlbum(albumId, song.name, null) } else it },
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                RankNumeral(song.rank)
                                Column(Modifier.weight(1f).padding(end = 8.dp)) {
                                    Text(song.name, style = MaterialTheme.typography.bodyLarge, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                    song.album?.let {
                                        Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                    }
                                }
                                Text(abbreviate(song.listenCount), style = MaterialTheme.typography.labelMedium.copy(fontFamily = app.discair.ui.theme.LocalFontPair.current.mono), color = MaterialTheme.colorScheme.onSurfaceVariant)
                                Spacer(Modifier.width(8.dp))
                                // Only a song that names its album can be filed with it (ACQ-08).
                                if (!song.owned && onAlbum != null) Box(Modifier.size(Target), contentAlignment = Alignment.Center) {
                                    GetSongButton(name, onAlbum, song.name, null, null)
                                }
                                if (song.owned && albumId != null) app.discair.ui.player.RowMoreMenu(
                                    song.name,
                                    listOf(
                                        "Play next" to { play.queueTrack(albumId, song.name, null, next = true) },
                                        "Add to queue" to { play.queueTrack(albumId, song.name, null, next = false) },
                                        "Download to device" to { play.downloadTrack(albumId, song.name, null) },
                                    ),
                                )
                            }
                        }
                        if (allSongs.size > SONGS_SHOWN && !showAllSongs) {
                            OutlinedButton(
                                onClick = { showAllSongs = true },
                                modifier = Modifier.padding(top = 8.dp).fillMaxWidth().heightIn(min = Target),
                            ) { Text("All top songs") }
                        }
                    }
                }
            }
        }
        val bio = sections.bio.bio?.text.orEmpty()
        if (bio.isNotBlank()) item { ReadMore(bio, Modifier.padding(horizontal = 16.dp, vertical = 16.dp)) }
        if (collage.isNotEmpty()) item { ArtistPhotoStrip(collage, name, open) }
        if (owned.isNotEmpty()) {
            item { Heading("In your library", Modifier.padding(horizontal = 16.dp)) }
            val shown = if (showAllAlbums) owned else owned.take(ALBUMS_SHOWN)
            items(shown.chunked(2)) { row ->
                Row(Modifier.padding(horizontal = 16.dp)) {
                    row.forEach { album ->
                        Column(
                            Modifier.weight(1f).padding(4.dp).clickable(role = Role.Button) { open.album(album.key, name, album.name, album.id, album.year) },
                        ) {
                            Box {
                                AlbumCover(name, album.name, album.artworkUrl, Modifier.fillMaxWidth().aspectSquare().sharedCover(album.key))
                                CheckBadge(
                                    Modifier.align(Alignment.BottomEnd).padding(8.dp),
                                    onPlay = album.id.takeIf { it.isNotBlank() }?.let { id -> { play.playAlbum(id) } },
                                    label = album.name,
                                )
                            }
                            Text(album.name, style = MaterialTheme.typography.bodyLarge, maxLines = 2, overflow = TextOverflow.Ellipsis, modifier = Modifier.padding(top = 8.dp))
                            album.year?.let { Text("$it", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                        }
                    }
                    if (row.size == 1) Spacer(Modifier.weight(1f))
                }
            }
            if (owned.size > ALBUMS_SHOWN && !showAllAlbums) item {
                OutlinedButton(
                    onClick = { showAllAlbums = true },
                    modifier = Modifier.padding(horizontal = 16.dp).fillMaxWidth().heightIn(min = Target),
                ) { Text("All albums (${owned.size})") }
            }
        }
        val missing = sections.missingAlbums.items
        if (missing.isNotEmpty()) {
            item { Heading("Missing albums", Modifier.padding(horizontal = 16.dp)) }
            val shown = if (showAllMissing) missing else missing.take(MISSING_SHOWN)
            items(shown.size) { i ->
                val album = shown[i]
                Column {
                    Row(
                        Modifier.fillMaxWidth().heightIn(min = 64.dp)
                            .clickable(role = Role.Button) { open.album(album.key, name, album.name, null, album.year) }
                            .padding(horizontal = 16.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        RankNumeral(i + 1)
                        AlbumCover(name, album.name, null, Modifier.size(48.dp))
                        Column(Modifier.weight(1f).padding(start = 16.dp)) {
                            Text(album.name, style = MaterialTheme.typography.bodyLarge, maxLines = 1, overflow = TextOverflow.Ellipsis)
                            val sub = listOfNotNull(album.year?.toString(), if (album.popularity > 0) abbreviate(album.popularity) + " listens" else null).joinToString(" · ")
                            if (sub.isNotEmpty()) Text(sub, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        GetAlbumButton(name, album.name, pageMetadata(name, album.name, album.year))
                    }
                    RowDivider(Modifier.padding(horizontal = 16.dp))
                }
            }
            if (missing.size > MISSING_SHOWN && !showAllMissing) item {
                OutlinedButton(
                    onClick = { showAllMissing = true },
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp).fillMaxWidth().heightIn(min = Target),
                ) { Text("All missing albums") }
            }
        }
        if (similar.isNotEmpty()) {
            item { Heading("Similar artists", Modifier.padding(horizontal = 16.dp)) }
            item {
                SimilarArtistsRow {
                    items(similar.size) { i ->
                        val artist = similar[i]
                        ArtistCircle(
                            name = artist.name, ownedPath = artist.artworkUrl, owned = artist.owned,
                            onClick = { open.artist(artist.name, artist.key, artist.id, artist.mbid) },
                            modifier = Modifier.width(112.dp),
                        )
                    }
                }
            }
        }
    }
}
