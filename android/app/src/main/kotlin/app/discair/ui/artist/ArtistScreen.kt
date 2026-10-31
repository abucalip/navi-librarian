package app.discair.ui.artist

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
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
import app.discair.ui.common.TintedPage
import app.discair.ui.common.abbreviate
import app.discair.ui.common.aspectSquare
import app.discair.ui.common.plural
import app.discair.ui.common.rememberLoad
import app.discair.ui.theme.Display
import app.discair.ui.theme.Ink
import app.discair.ui.theme.Mono

private const val SONGS_SHOWN = 5
private const val ALBUMS_SHOWN = 6
private const val SIMILAR_SHOWN = 5
private const val MISSING_SHOWN = 10

@Composable
fun ArtistScreen(route: ArtistRoute, open: Opener) {
    val repo = LocalRepository.current
    val loaded = rememberLoad(route) { repo.artistPage(route.key, route.id, route.name, route.mbid) }
    var tint by remember(route) { mutableStateOf<Color?>(null) }
    val list = androidx.compose.foundation.lazy.rememberLazyListState()
    TintedPage(tint, list) {
        LoadView(loaded) { page -> ArtistContent(route, page, open, list, onTint = { tint = it }) }
        // Back stays reachable while the page loads or fails.
        if (loaded.state !is app.discair.ui.common.Load.Ready) {
            OverlayBack(open.back, Modifier.statusBarsPadding().padding(12.dp))
        }
    }
}

@Composable
private fun ArtistContent(route: ArtistRoute, page: ArtistPage, open: Opener, list: androidx.compose.foundation.lazy.LazyListState, onTint: (Color) -> Unit) {
    val sections = page.sections
    val info = sections.artist.artist
    val name = info?.name?.ifBlank { null } ?: route.name
    var showAllAlbums by remember { mutableStateOf(false) }
    var showAllMissing by remember { mutableStateOf(false) }
    var showAllSongs by remember { mutableStateOf(false) }
    // LIB-05: five similar artists chosen at random on each page load. Variety only; the server's list is the source.
    val similar = remember(page) { sections.similar.items.shuffled().take(SIMILAR_SHOWN) }
    val owned = sections.ownedAlbums.items

    LazyColumn(Modifier.fillMaxSize(), state = list, contentPadding = PaddingValues(bottom = 32.dp)) {
        item {
            Box(
                Modifier.statusBarsPadding().padding(12.dp).fillMaxWidth().height(300.dp)
                    .clip(RoundedCornerShape(12.dp)),
            ) {
                ArtistPhoto(name, owned.firstOrNull()?.artworkUrl, Modifier.fillMaxSize(), onColor = onTint)
                Box(
                    Modifier.fillMaxSize().background(
                        Brush.verticalGradient(listOf(Color.Transparent, Ink.Ink.copy(alpha = 0.92f)), startY = 120f),
                    ),
                )
                OverlayBack(open.back, Modifier.align(Alignment.TopStart).padding(12.dp))
                Column(Modifier.align(Alignment.BottomStart).padding(16.dp)) {
                    Text(
                        name, style = MaterialTheme.typography.headlineLarge.copy(fontFamily = Display),
                        maxLines = 2, overflow = TextOverflow.Ellipsis, modifier = Modifier.semantics { heading() },
                    )
                    val genres = sections.tags.items.map { it.name }.ifEmpty { listOfNotNull(info?.genre) }.take(3)
                    if (genres.isNotEmpty()) Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                        genres.forEach { g ->
                            Text(
                                g, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.heightIn(min = Target).clickable { open.genre(g.lowercase(), g) }.padding(vertical = 12.dp),
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
        val allSongs = sections.topSongs.items
        val songs = if (showAllSongs) allSongs else allSongs.take(SONGS_SHOWN)
        if (songs.isNotEmpty()) {
            item {
                Panel(Modifier.padding(horizontal = 12.dp, vertical = 4.dp).fillMaxWidth()) {
                    Column(Modifier.padding(16.dp)) {
                        Text(
                            "Top songs", style = MaterialTheme.typography.headlineMedium,
                            modifier = Modifier.padding(bottom = 8.dp).semantics { heading() },
                        )
                        songs.forEachIndexed { i, song ->
                            if (i > 0) RowDivider()
                            Row(Modifier.fillMaxWidth().heightIn(min = 64.dp), verticalAlignment = Alignment.CenterVertically) {
                                RankNumeral(song.rank)
                                Column(Modifier.weight(1f).padding(end = 8.dp)) {
                                    Text(song.name, style = MaterialTheme.typography.bodyLarge, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                    song.album?.let {
                                        Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                    }
                                }
                                Text(abbreviate(song.listenCount), style = MaterialTheme.typography.labelMedium.copy(fontFamily = Mono), color = MaterialTheme.colorScheme.onSurfaceVariant)
                                Spacer(Modifier.width(8.dp))
                                Box(Modifier.size(Target), contentAlignment = Alignment.Center) { OwnedMark(song.owned) }
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
        if (bio.isNotBlank()) item { ReadMore(bio, Modifier.padding(horizontal = 16.dp, vertical = 12.dp)) }
        if (owned.isNotEmpty()) {
            item { Heading("In your library", Modifier.padding(horizontal = 16.dp)) }
            val shown = if (showAllAlbums) owned else owned.take(ALBUMS_SHOWN)
            items(shown.chunked(2)) { row ->
                Row(Modifier.padding(horizontal = 12.dp)) {
                    row.forEach { album ->
                        Column(
                            Modifier.weight(1f).padding(4.dp).clickable { open.album(album.key, name, album.name, album.id, album.year) },
                        ) {
                            Box {
                                AlbumCover(name, album.name, album.artworkUrl, Modifier.fillMaxWidth().aspectSquare())
                                CheckBadge(Modifier.align(Alignment.TopEnd).padding(8.dp))
                            }
                            Text(album.name, style = MaterialTheme.typography.bodyLarge, maxLines = 2, overflow = TextOverflow.Ellipsis, modifier = Modifier.padding(top = 6.dp))
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
                            .clickable { open.album(album.key, name, album.name, null, album.year) }
                            .padding(horizontal = 16.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        RankNumeral(i + 1)
                        AlbumCover(name, album.name, null, Modifier.size(48.dp))
                        Column(Modifier.weight(1f).padding(start = 12.dp)) {
                            Text(album.name, style = MaterialTheme.typography.bodyLarge, maxLines = 1, overflow = TextOverflow.Ellipsis)
                            val sub = listOfNotNull(album.year?.toString(), if (album.popularity > 0) abbreviate(album.popularity) + " listens" else null).joinToString(" · ")
                            if (sub.isNotEmpty()) Text(sub, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
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
