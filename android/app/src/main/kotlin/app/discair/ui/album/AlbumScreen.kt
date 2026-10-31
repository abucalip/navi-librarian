package app.discair.ui.album

import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.R
import app.discair.model.AlbumPage
import app.discair.ui.AlbumRoute
import app.discair.ui.Opener
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.ArtistCircle
import app.discair.ui.common.Heading
import app.discair.ui.common.Load
import app.discair.ui.common.LoadView
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.OverlayBack
import app.discair.ui.common.OwnedMark
import app.discair.ui.common.RankNumeral
import app.discair.ui.common.ReadMore
import app.discair.ui.common.RowDivider
import app.discair.ui.common.SimilarArtistsRow
import app.discair.ui.common.Target
import app.discair.ui.common.TintedPage
import app.discair.ui.common.aspectSquare
import app.discair.ui.common.plural
import app.discair.ui.common.rememberLoad
import app.discair.ui.theme.Display
import app.discair.ui.theme.Ink
import app.discair.ui.theme.Mono
import java.net.URLEncoder

private const val SIMILAR_ALBUMS_SHOWN = 6
private const val SIMILAR_ARTISTS_SHOWN = 5

@Composable
fun AlbumScreen(route: AlbumRoute, open: Opener) {
    val repo = LocalRepository.current
    val loaded = rememberLoad(route) { repo.albumPage(route.key, route.id, route.artist, route.name, route.year) }
    var tint by remember(route) { mutableStateOf<Color?>(null) }
    val list = androidx.compose.foundation.lazy.rememberLazyListState()
    TintedPage(tint, list) {
        LoadView(loaded) { page -> AlbumContent(route, page, open, list, onTint = { tint = it }) }
        if (loaded.state !is Load.Ready) OverlayBack(open.back, Modifier.statusBarsPadding().padding(12.dp))
    }
}

@Composable
private fun AlbumContent(route: AlbumRoute, page: AlbumPage, open: Opener, list: androidx.compose.foundation.lazy.LazyListState, onTint: (Color) -> Unit) {
    val s = page.sections
    val info = s.album.album
    val title = info?.name?.ifBlank { null } ?: route.name
    val artist = info?.artist?.ifBlank { null } ?: route.artist
    val owned = info?.owned == true
    val year = info?.year ?: route.year
    var showAllSimilar by remember { mutableStateOf(false) }
    val similarArtists = remember(page) { s.similarArtists.items.shuffled().take(SIMILAR_ARTISTS_SHOWN) }
    val tracks = s.tracks.items

    LazyColumn(Modifier.fillMaxSize(), state = list, contentPadding = PaddingValues(bottom = 32.dp)) {
        item {
            Box(Modifier.statusBarsPadding().fillMaxWidth().padding(12.dp)) {
                OverlayBack(open.back, Modifier.align(Alignment.TopStart))
                AlbumCover(
                    artist, title, info?.artworkUrl,
                    Modifier.align(Alignment.TopCenter).size(240.dp).aspectSquare(),
                    onColor = onTint,
                )
            }
        }
        item {
            Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    title, style = MaterialTheme.typography.headlineLarge.copy(fontFamily = Display),
                    textAlign = TextAlign.Center, modifier = Modifier.padding(top = 8.dp).semantics { heading() },
                )
                Text(
                    artist, style = MaterialTheme.typography.titleMedium, textAlign = TextAlign.Center,
                    modifier = Modifier.heightIn(min = Target)
                        .clickable { open.artist(artist, info?.artistKey?.ifBlank { null }, info?.artistId, null) }
                        .padding(vertical = 12.dp),
                )
                val genre = s.genre.genre
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (!genre.isNullOrBlank()) Text(
                        genre.lowercase(), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.heightIn(min = Target).clickable { open.genre(genre.lowercase(), genre) }.padding(vertical = 14.dp),
                    )
                    if (!genre.isNullOrBlank() && year != null) Text("·", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    if (year != null) Text("$year", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                if (!owned) Text("Not in your library", style = MaterialTheme.typography.bodyMedium, color = Ink.Caution)
            }
        }
        val notes = s.description.description?.paragraphs.orEmpty().joinToString("\n\n")
        if (notes.isNotBlank()) item { ReadMore(notes, Modifier.padding(horizontal = 16.dp, vertical = 12.dp)) }
        if (tracks.isNotEmpty()) {
            item { RowDivider(Modifier.padding(horizontal = 12.dp).padding(top = 12.dp)) }
            items(tracks.size) { i ->
                val t = tracks[i]
                Column {
                    Row(
                        Modifier.fillMaxWidth().heightIn(min = 52.dp).padding(horizontal = 16.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            "${t.number ?: i + 1}", style = MaterialTheme.typography.bodyLarge,
                            color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.width(32.dp),
                        )
                        Text(t.title, style = MaterialTheme.typography.bodyLarge, maxLines = 2, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f).padding(end = 8.dp))
                        t.durationSeconds?.let {
                            Text("%d:%02d".format(it / 60, it % 60), style = MaterialTheme.typography.labelMedium.copy(fontFamily = Mono), color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        Box(Modifier.size(Target), contentAlignment = Alignment.Center) { OwnedMark(t.owned) }
                    }
                    RowDivider(Modifier.padding(horizontal = 12.dp))
                }
            }
            item { Summary(tracks.size, tracks.sumOf { it.durationSeconds ?: 0 }, tracks.count { it.owned }) }
        }
        item { ServiceLinks(artist, title, info?.releaseGroupMbid) }
        val similarAlbums = s.similarAlbums.items
        if (similarAlbums.isNotEmpty()) {
            item { Heading("Similar albums", Modifier.padding(horizontal = 16.dp)) }
            val shown = if (showAllSimilar) similarAlbums else similarAlbums.take(SIMILAR_ALBUMS_SHOWN)
            items(shown.size) { i ->
                val album = shown[i]
                Column {
                    Row(
                        Modifier.fillMaxWidth().heightIn(min = 64.dp)
                            .clickable { open.album(album.key, album.artist, album.name, null, album.year) }
                            .padding(horizontal = 16.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        RankNumeral(i + 1)
                        AlbumCover(album.artist, album.name, null, Modifier.size(48.dp))
                        Column(Modifier.weight(1f).padding(start = 12.dp)) {
                            Text(album.name, style = MaterialTheme.typography.bodyLarge, maxLines = 1, overflow = TextOverflow.Ellipsis)
                            Text(
                                listOfNotNull(album.artist.ifBlank { null }, album.year?.toString()).joinToString(" · "),
                                style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
                                maxLines = 1, overflow = TextOverflow.Ellipsis,
                            )
                        }
                        OwnedMark(album.owned)
                    }
                    RowDivider(Modifier.padding(horizontal = 16.dp))
                }
            }
            if (similarAlbums.size > SIMILAR_ALBUMS_SHOWN && !showAllSimilar) item {
                OutlinedButton(
                    onClick = { showAllSimilar = true },
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp).fillMaxWidth().heightIn(min = Target),
                ) { Text("All albums (${similarAlbums.size})") }
            }
        }
        if (similarArtists.isNotEmpty()) {
            item { Heading("Similar artists", Modifier.padding(horizontal = 16.dp)) }
            item {
                SimilarArtistsRow {
                    items(similarArtists.size) { i ->
                        val a = similarArtists[i]
                        ArtistCircle(a.name, a.artworkUrl, a.owned, { open.artist(a.name, a.key, a.id, a.mbid) }, Modifier.width(112.dp))
                    }
                }
            }
        }
    }
}

/** "27 songs, 1 hour 19 minutes · 10 in your library", centred under the tracklist. */
@Composable
private fun Summary(songs: Int, seconds: Int, inLibrary: Int) {
    val minutes = seconds / 60
    val length = when {
        minutes >= 60 -> plural(minutes / 60, "hour") + (if (minutes % 60 > 0) " " + plural(minutes % 60, "minute") else "")
        minutes > 0 -> plural(minutes, "minute")
        else -> null
    }
    val parts = listOfNotNull(plural(songs, "song"), length).joinToString(", ")
    Text(
        parts + if (inLibrary > 0) " · $inLibrary in your library" else "",
        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
        textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth().padding(16.dp),
    )
}

private class Service(val name: String, val icon: Int, val search: String, val exact: (app.discair.model.AlbumLinks) -> String?)

private val SERVICES = listOf(
    Service("Apple Music", R.drawable.ic_service_apple_music, "https://music.apple.com/search?term=") { it.appleMusic },
    Service("Deezer", R.drawable.ic_service_deezer, "https://www.deezer.com/search/") { it.deezer },
    Service("MusicBrainz", R.drawable.ic_service_musicbrainz, "https://musicbrainz.org/search?type=release_group&query=") { it.musicbrainz },
    Service("Qobuz", R.drawable.ic_service_qobuz, "https://www.qobuz.com/us-en/search/albums/") { null },
)

/** Logo-only service links. Each opens a search at once and is upgraded to the album's own page when the server finds an exact match. */
@Composable
private fun ServiceLinks(artist: String, album: String, mbid: String?) {
    val repo = LocalRepository.current
    val uri = LocalUriHandler.current
    val exact = (rememberLoad(artist, album, mbid) { repo.albumLinks(artist, album, mbid) }.state as? Load.Ready)?.value
    val query = URLEncoder.encode("$artist $album".trim(), "UTF-8")
    Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), horizontalArrangement = Arrangement.Center) {
        SERVICES.forEach { service ->
            val target = exact?.let(service.exact) ?: (service.search + query)
            Box(
                Modifier.padding(horizontal = 4.dp).size(Target).clip(RoundedCornerShape(6.dp))
                    .border(1.dp, Ink.EdgeStrong, RoundedCornerShape(6.dp))
                    .clickable { uri.openUri(target) }
                    .semantics { contentDescription = "Open ${service.name}" },
                contentAlignment = Alignment.Center,
            ) { androidx.compose.foundation.Image(painterResource(service.icon), contentDescription = null, modifier = Modifier.size(24.dp)) }
        }
    }
}
