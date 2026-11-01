package app.discair.ui.album

import androidx.compose.foundation.border
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
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
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
import app.discair.model.Description
import app.discair.model.Done
import app.discair.ui.AlbumRoute
import app.discair.ui.Opener
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.ArtistCircle
import app.discair.ui.common.GetAlbumButton
import app.discair.ui.common.GetSongButton
import app.discair.ui.common.pageMetadata
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
import app.discair.ui.common.rememberStreamLoad
import app.discair.ui.theme.Ink
import app.discair.ui.theme.Mono
import java.net.URLEncoder

private const val SIMILAR_ALBUMS_SHOWN = 6
private const val SIMILAR_ARTISTS_SHOWN = 5

@Composable
fun AlbumScreen(route: AlbumRoute, open: Opener) {
    val repo = LocalRepository.current
    val loaded = rememberStreamLoad<AlbumPage>(route) { show -> repo.albumPageStream(route.key, route.id, route.artist, route.name, route.year, show) }
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
    // Playback is for albums in the library only; the id is the Navidrome album id the page already carries.
    val albumId = (info?.id ?: route.id)?.takeIf { owned && it.isNotBlank() }
    val play = app.discair.ui.player.LocalPlayActions.current

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
                    title, style = MaterialTheme.typography.headlineLarge,
                    textAlign = TextAlign.Center, modifier = Modifier.padding(top = 8.dp).semantics { heading() },
                )
                Text(
                    artist, style = MaterialTheme.typography.titleMedium, textAlign = TextAlign.Center,
                    modifier = Modifier.heightIn(min = Target)
                        .clickable(role = Role.Button) { open.artist(artist, info?.artistKey?.ifBlank { null }, info?.artistId, null) }
                        .padding(vertical = 12.dp),
                )
                val genre = s.genre.genre
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (!genre.isNullOrBlank()) Text(
                        genre.lowercase(), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.heightIn(min = Target).clickable(role = Role.Button) { open.genre(genre.lowercase(), genre) }.padding(vertical = 14.dp),
                    )
                    if (!genre.isNullOrBlank() && year != null) Text("·", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    if (year != null) Text("$year", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                if (!owned) Text("Not in your library", style = MaterialTheme.typography.bodyMedium, color = Ink.Caution)
                if (albumId != null) app.discair.ui.player.PlayRow(
                    onPlay = { play.playAlbum(albumId) }, onShuffle = { play.playAlbum(albumId, shuffle = true) },
                    modifier = Modifier.padding(top = 8.dp),
                    onPlayNext = { play.queueAlbum(albumId, next = true) }, onAddToQueue = { play.queueAlbum(albumId, next = false) },
                )
                // The album-level Get stays until every track is in the library (ACQ-08).
                if (!owned || tracks.any { !it.owned }) GetAlbumButton(
                    artist, title, pageMetadata(artist, title, year, info?.releaseGroupMbid),
                )
            }
        }
        item { InfoReviewsTabs(artist, title, s.description.description, finished = page.done != Done()) }
        if (tracks.isNotEmpty()) {
            item { RowDivider(Modifier.padding(horizontal = 12.dp).padding(top = 12.dp)) }
            items(tracks.size) { i ->
                val t = tracks[i]
                Column {
                    Row(
                        // An owned track plays the album from that track.
                        Modifier.fillMaxWidth().heightIn(min = 52.dp)
                            .let { if (t.owned && albumId != null) it.clickable(onClickLabel = "Play ${t.title}", role = Role.Button) { play.playAlbum(albumId, t.title, t.number) } else it }
                            .padding(horizontal = 16.dp),
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
                        Box(Modifier.size(Target), contentAlignment = Alignment.Center) {
                            if (t.owned) OwnedMark(true) else GetSongButton(artist, title, t.title, t.number, year)
                        }
                        if (t.owned && albumId != null) app.discair.ui.player.RowMoreMenu(
                            t.title,
                            listOf(
                                "Play next" to { play.queueTrack(albumId, t.title, t.number, next = true) },
                                "Add to queue" to { play.queueTrack(albumId, t.title, t.number, next = false) },
                            ),
                        )
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
                            .clickable(role = Role.Button) { open.album(album.key, album.artist, album.name, null, album.year) }
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
                    .clickable(role = Role.Button) { uri.openUri(target) }
                    .semantics { contentDescription = "Open ${service.name}" },
                contentAlignment = Alignment.Center,
            ) { androidx.compose.foundation.Image(painterResource(service.icon), contentDescription = null, modifier = Modifier.size(24.dp)) }
        }
    }
}

/**
 * The description area as two tabs, like the web. Info is the description (Apple Music, else Wikipedia with its
 * source and licence); Reviews asks the server on first open. With no description the Reviews tab opens by
 * itself, unless the reader has already picked a tab.
 */
@Composable
private fun InfoReviewsTabs(artist: String, album: String, description: Description?, finished: Boolean) {
    val paragraphs = description?.paragraphs.orEmpty()
    var chosen by remember(artist, album) { mutableStateOf<Int?>(null) }
    val tab = chosen ?: if (finished && paragraphs.isEmpty()) 1 else 0
    Column(Modifier.fillMaxWidth().padding(top = 12.dp)) {
        TabRow(
            selectedTabIndex = tab, containerColor = Color.Transparent, contentColor = Ink.Accent,
            divider = { RowDivider(Modifier.padding(horizontal = 12.dp)) },
        ) {
            listOf("Info", "Reviews").forEachIndexed { i, label ->
                Tab(
                    selected = tab == i, onClick = { chosen = i }, modifier = Modifier.heightIn(min = Target),
                    selectedContentColor = Ink.Accent, unselectedContentColor = MaterialTheme.colorScheme.onSurfaceVariant,
                    text = { Text(label, style = MaterialTheme.typography.labelLarge) },
                )
            }
        }
        if (tab == 0) InfoTab(description, paragraphs, finished) else ReviewsTab(artist, album)
    }
}

@Composable
private fun InfoTab(description: Description?, paragraphs: List<String>, finished: Boolean) {
    val uri = LocalUriHandler.current
    Column(Modifier.padding(horizontal = 16.dp, vertical = 12.dp)) {
        if (paragraphs.isEmpty()) {
            Text(
                if (finished) "No description found for this album." else "Loading description…",
                style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            return@Column
        }
        ReadMore(paragraphs.joinToString("\n\n"))
        val source = description?.source ?: "Apple Music"
        val credit = listOfNotNull(source, description?.license).joinToString(" · ")
        val link = description?.url
        Text(
            credit, style = MaterialTheme.typography.bodySmall,
            color = if (link != null) Ink.Accent else MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.heightIn(min = Target).then(
                if (link != null) Modifier.clickable(role = Role.Button) { uri.openUri(link) } else Modifier,
            ).padding(vertical = 14.dp),
        )
    }
}

@Composable
private fun ReviewsTab(artist: String, album: String) {
    val repo = LocalRepository.current
    val uri = LocalUriHandler.current
    val loaded = rememberLoad(artist, album) { repo.albumReviews(artist, album) }
    Column(Modifier.padding(horizontal = 16.dp, vertical = 12.dp)) {
        when (val state = loaded.state) {
            Load.Loading -> Text("Loading reviews…", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            is Load.Failed -> {
                Text("Reviews could not be loaded.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                OutlinedButton(onClick = loaded.reload, Modifier.heightIn(min = Target)) { Text("Try again") }
            }
            is Load.Ready -> {
                val data = state.value
                data.reviews.forEach { review ->
                    Column(Modifier.padding(bottom = 16.dp)) {
                        Text("\u201c${review.quote}\u201d", style = MaterialTheme.typography.bodyMedium)
                        Text(
                            "Read the full review at ${review.source}", style = MaterialTheme.typography.bodySmall, color = Ink.Accent,
                            modifier = Modifier.heightIn(min = Target).clickable(role = Role.Button) { uri.openUri(review.url) }.padding(vertical = 14.dp),
                        )
                    }
                }
                val note = when {
                    data.reviews.isNotEmpty() -> if (data.retryable) "Some sources did not answer." else ""
                    data.retryable -> "No reviews found. Some sources did not answer."
                    else -> "No reviews found for this album."
                }
                if (note.isNotEmpty()) Text(note, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                // Only the button asks the failed outlets again, so switching tabs never re-requests.
                if (data.retryable) OutlinedButton(onClick = loaded.reload, Modifier.heightIn(min = Target)) { Text("Try again") }
            }
        }
    }
}
