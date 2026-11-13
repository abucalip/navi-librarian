package app.discair.ui.artist

import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.model.ArtistSections
import app.discair.model.MissingAlbum
import app.discair.model.OwnedAlbum
import app.discair.model.SimilarArtist
import app.discair.model.TopSong
import app.discair.ui.ArtistRoute
import app.discair.ui.Opener
import app.discair.ui.common.ArtistPhoto
import app.discair.ui.common.Button
import app.discair.ui.common.CoverStackArtistChip
import app.discair.ui.common.CoverStackCover
import app.discair.ui.common.CoverStackDivider
import app.discair.ui.common.CoverStackHeading
import app.discair.ui.common.CoverStackRules
import app.discair.ui.common.CoverStackTitle
import app.discair.ui.common.CoverStackTopBar
import app.discair.ui.common.GetAlbumButton
import app.discair.ui.common.GetSongButton
import app.discair.ui.common.OutlinedButton
import app.discair.ui.common.ReadMore
import app.discair.ui.common.Target
import app.discair.ui.common.coverStackShadow
import app.discair.ui.common.describedAs
import app.discair.ui.common.pageMetadata
import app.discair.ui.common.plural
import app.discair.ui.player.LocalPlayActions
import app.discair.ui.player.PlayerIcons
import app.discair.ui.player.RowMoreMenu
import app.discair.ui.theme.LocalPalette

private const val SONGS_SHOWN = 5
private const val MISSING_SHOWN = 10

/** What the Artist page has loaded and decided; the Cover Stack page only draws it. */
internal class CoverStackArtistData(
    val route: ArtistRoute,
    val name: String,
    val sections: ArtistSections,
    val owned: List<OwnedAlbum>,
    val ownedAlbumCount: Int?,
    val inLibrary: Boolean,
    val artistId: String?,
    val similar: List<SimilarArtist>,
    val collage: List<app.discair.model.CollageEntry>,
    val canPaths: Boolean,
    val onPaths: () -> Unit,
)

/**
 * Soft Brut's Artist page (mockup soft-brut/album-artist-genre, frame 2): a round outlined photo beside the name, Play and Shuffle,
 * Top songs as plain rows, then strips of the albums in the library, the missing albums (with Get) and similar artists.
 */
@Composable
internal fun CoverStackArtistContent(d: CoverStackArtistData, open: Opener, list: LazyListState, showAllSongs: Boolean, onAllSongs: () -> Unit, showAllMissing: Boolean, onAllMissing: () -> Unit) {
    val p = LocalPalette.current
    val play = LocalPlayActions.current
    val artistId = d.artistId
    val menu = buildList {
        if (artistId != null) {
            add("Play next" to { play.queueArtist(artistId, next = true) })
            add("Add to queue" to { play.queueArtist(artistId, next = false) })
        }
        if (d.canPaths) add("Paths" to d.onPaths)
    }
    val owned = d.owned
    LazyColumn(Modifier.fillMaxSize(), state = list, contentPadding = PaddingValues(bottom = 32.dp + app.discair.ui.LocalBottomClearance.current)) {
        item { CoverStackTopBar(open.back, menu) }
        item {
            Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(14.dp), verticalAlignment = Alignment.CenterVertically) {
                val ol = CoverStackRules.outline(p).dp
                ArtistPhoto(
                    d.name, owned.firstOrNull()?.artworkUrl,
                    Modifier.size(120.dp).coverStackShadow(CircleShape, p, 4f).clip(CircleShape).border(ol, p.edgeStrong, CircleShape), circle = true,
                )
                Column(Modifier.weight(1f)) {
                    CoverStackTitle(d.name, maxLines = 2)
                    Text(
                        if (d.inLibrary) plural(d.ownedAlbumCount ?: 0, "album") + " in your library" else "Not in your library",
                        color = p.textMuted, style = MaterialTheme.typography.bodySmall,
                    )
                    val genres = d.sections.tags.items.map { it.name }.ifEmpty { listOfNotNull(d.sections.artist.artist?.genre) }.take(3)
                    if (genres.isNotEmpty()) Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        genres.forEach { g ->
                            Box(
                                Modifier.weight(1f, fill = false).heightIn(min = Target).clickable(role = Role.Button) { open.genre(g.lowercase(), g) },
                                contentAlignment = Alignment.CenterStart,
                            ) { Text(g, color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall) }
                        }
                    }
                }
            }
        }
        if (artistId != null) item {
            Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                Button(onClick = { play.playArtist(artistId, shuffle = false) }, Modifier.heightIn(min = Target)) {
                    Icon(PlayerIcons.Play, contentDescription = null, Modifier.size(20.dp)); Text(" Play")
                }
                OutlinedButton(onClick = { play.playArtist(artistId, shuffle = true) }, Modifier.heightIn(min = Target)) {
                    Icon(PlayerIcons.Shuffle, contentDescription = null, Modifier.size(20.dp)); Text(" Shuffle")
                }
                if (d.canPaths) OutlinedButton(onClick = d.onPaths, Modifier.heightIn(min = Target)) {
                    Icon(PlayerIcons.Paths, contentDescription = null, Modifier.size(20.dp)); Text(" Paths")
                }
            }
        }
        val allSongs = d.sections.topSongs.items
        if (allSongs.isNotEmpty()) {
            item {
                CoverStackHeading(
                    "Top songs", Modifier.padding(top = 4.dp, bottom = 4.dp),
                    link = if (allSongs.size > SONGS_SHOWN && !showAllSongs) "All top songs" else null, onLink = onAllSongs,
                )
            }
            val shown = if (showAllSongs) allSongs else allSongs.take(SONGS_SHOWN)
            items(shown.size) { i -> TopSongRow(d, shown[i], i < shown.lastIndex) }
        }
        val bio = d.sections.bio.bio?.text.orEmpty()
        if (bio.isNotBlank()) item { ReadMore(bio, Modifier.padding(horizontal = 16.dp, vertical = 16.dp)) }
        if (d.collage.isNotEmpty()) item { ArtistPhotoStrip(d.collage, d.name, open) }
        if (owned.isNotEmpty()) {
            item { CoverStackHeading("In your library", Modifier.padding(top = 16.dp, bottom = 8.dp)) }
            item {
                LazyRow(contentPadding = PaddingValues(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    items(owned, key = { it.key + it.id }) { album ->
                        CoverStackCover(
                            d.name, album.name, album.artworkUrl,
                            Modifier.width(104.dp).clip(RoundedCornerShape(6.dp))
                                .clickable(role = Role.Button) { open.album(album.key, d.name, album.name, album.id, album.year) }
                                .describedAs(listOfNotNull(album.name, album.year?.toString()).joinToString(", ")),
                        )
                    }
                }
            }
        }
        val missing = d.sections.missingAlbums.items
        if (missing.isNotEmpty()) {
            item {
                CoverStackHeading(
                    "Missing albums", Modifier.padding(top = 16.dp, bottom = 8.dp),
                    link = if (missing.size > MISSING_SHOWN && !showAllMissing) "All missing albums" else null, onLink = onAllMissing,
                )
            }
            item {
                LazyRow(contentPadding = PaddingValues(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    items(if (showAllMissing) missing else missing.take(MISSING_SHOWN), key = { it.key + it.name }) { album -> MissingCard(d.name, album, open) }
                }
            }
        }
        if (d.similar.isNotEmpty()) {
            item { CoverStackHeading("Similar artists", Modifier.padding(top = 16.dp, bottom = 8.dp)) }
            item {
                LazyRow(contentPadding = PaddingValues(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    items(d.similar, key = { it.name }) { a -> CoverStackArtistChip(a.name, a.artworkUrl, { open.artist(a.name, a.key, a.id, a.mbid) }) }
                }
            }
        }
    }
}

/** A top song: outlined cover 48, title, album, then Get or the menu of ways to play (mockup `.li`). No rank or listen count. */
@Composable
private fun TopSongRow(d: CoverStackArtistData, song: TopSong, divider: Boolean) {
    val p = LocalPalette.current
    val play = LocalPlayActions.current
    val onAlbum = song.album?.takeIf { it.isNotBlank() }
    val ownedAlbum = onAlbum?.let { a -> d.owned.firstOrNull { it.name.equals(a, ignoreCase = true) } }
    // An owned top song plays from its album when the album is in the library.
    val albumId = ownedAlbum?.id?.takeIf { it.isNotBlank() }
    Column {
        Row(
            Modifier.fillMaxWidth().heightIn(min = 64.dp)
                .let { if (song.owned && albumId != null) it.clickable(onClickLabel = "Play ${song.name}", role = Role.Button) { play.playAlbum(albumId, song.name, null) } else it }
                .padding(horizontal = 16.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
        ) {
            CoverStackCover(d.name, onAlbum ?: song.name, ownedAlbum?.artworkUrl, Modifier.size(48.dp))
            Column(Modifier.weight(1f)) {
                Text(song.name, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold))
                onAlbum?.let { Text(it, color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall) }
            }
            // Only a song that names its album can be filed with it (ACQ-08).
            if (!song.owned && onAlbum != null) Box(Modifier.size(Target), contentAlignment = Alignment.Center) { GetSongButton(d.name, onAlbum, song.name, null, null) }
            if (song.owned && albumId != null) RowMoreMenu(
                song.name,
                listOf(
                    "Play next" to { play.queueTrack(albumId, song.name, null, next = true) },
                    "Add to queue" to { play.queueTrack(albumId, song.name, null, next = false) },
                    "Download to device" to { play.downloadTrack(albumId, song.name, null) },
                ),
            )
        }
        if (divider) CoverStackDivider(Modifier.padding(horizontal = 16.dp))
    }
}

/** A missing album: cover 104, bold name on one line, and its Get button (mockup `.cap` with a small primary button). */
@Composable
private fun MissingCard(artist: String, album: MissingAlbum, open: Opener) {
    val p = LocalPalette.current
    Column(Modifier.width(104.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Column(
            Modifier.clip(RoundedCornerShape(6.dp)).clickable(role = Role.Button) { open.album(album.key, artist, album.name, null, album.year) },
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            CoverStackCover(artist, album.name, null, Modifier.fillMaxWidth())
            Text(album.name, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold, fontSize = 14.sp))
        }
        GetAlbumButton(artist, album.name, pageMetadata(artist, album.name, album.year))
    }
}
