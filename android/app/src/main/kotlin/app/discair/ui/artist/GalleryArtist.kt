package app.discair.ui.artist

import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.model.MissingAlbum
import app.discair.model.TopSong
import app.discair.ui.Opener
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.ArtistPhoto
import app.discair.ui.common.GalleryArtistPlate
import app.discair.ui.common.GalleryButton
import app.discair.ui.common.GalleryButtonKind
import app.discair.ui.common.GalleryCaption
import app.discair.ui.common.GalleryEyebrow
import app.discair.ui.common.GalleryIcons
import app.discair.ui.common.GalleryMenuButton
import app.discair.ui.common.GalleryPageBar
import app.discair.ui.common.GalleryPagesRules
import app.discair.ui.common.GalleryPrint
import app.discair.ui.common.GalleryMenuItem
import app.discair.ui.common.GalleryMenuHeader
import app.discair.ui.common.galleryArrive
import app.discair.ui.common.GalleryReadMore
import app.discair.ui.common.GalleryRow
import app.discair.ui.common.GalleryRules
import app.discair.ui.common.GallerySectionHead
import app.discair.ui.common.GalleryType
import app.discair.ui.common.GetAlbumButton
import app.discair.ui.common.GetSongButton
import app.discair.ui.common.pageMetadata
import app.discair.ui.player.LocalPlayActions
import app.discair.ui.theme.LocalPalette

/*
 * Gallery's Artist page (Layout.Gallery). Spec: docs/archive/completed/GALLERY_THEME.md section 10; mockup: docs/design/gallery/pages/album-artist-genre.html, frame 3.
 * A 200dp photo print, the catalogue line (albums in the library, the years they span), the name in Fraunces italic and the genres, Play / Shuffle / Paths,
 * then Top songs as rows, In your library as captioned prints, Missing albums with Get, the biography and similar artists. The data is [CoverStackArtistData].
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun GalleryArtistContent(d: CoverStackArtistData, open: Opener, list: LazyListState, showAllSongs: Boolean, onAllSongs: () -> Unit, showAllMissing: Boolean, onAllMissing: () -> Unit) {
    val p = LocalPalette.current
    val play = LocalPlayActions.current
    val artistId = d.artistId
    val menu = buildList {
        if (artistId != null) {
            add("Play next" to { play.queueArtist(artistId, next = true) })
            add("Add to queue" to { play.queueArtist(artistId, next = false) })
        }
    }
    val gutter = GalleryRules.GUTTER.dp
    var showAllAlbums by remember(d.route) { mutableStateOf(false) }
    val owned = d.owned
    val genres = d.sections.tags.items.map { it.name }.ifEmpty { listOfNotNull(d.sections.artist.artist?.genre) }.take(3)

    LazyColumn(Modifier.fillMaxSize(), state = list, contentPadding = PaddingValues(bottom = 32.dp + app.discair.ui.LocalBottomClearance.current)) {
        item { GalleryPageBar("Artist", open.back, action = { GalleryMenuButton("More for ${d.name}", menu) }) }
        item {
            Box(Modifier.fillMaxWidth().galleryArrive(0).padding(top = 8.dp), contentAlignment = Alignment.TopCenter) {
                GalleryPrint(GalleryPagesRules.ARTIST_PRINT_DP.dp) {
                    ArtistPhoto(d.name, owned.firstOrNull()?.artworkUrl, Modifier.fillMaxWidth().aspectRatio(1f), rect = true)
                }
            }
        }
        item {
            Column(Modifier.fillMaxWidth().galleryArrive(1).padding(start = gutter, end = gutter, top = 22.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                GalleryEyebrow(GalleryPagesRules.artistEyebrow(d.inLibrary, d.ownedAlbumCount ?: owned.size, owned.map { it.year }))
                Text(d.name, Modifier.padding(top = 4.dp).semantics { heading() }, color = p.text, style = GalleryType.workXL, maxLines = 3, overflow = TextOverflow.Ellipsis)
                if (genres.isNotEmpty()) Row {
                    genres.forEachIndexed { i, g ->
                        Text(
                            if (i < genres.lastIndex) "$g, " else g, color = p.textMuted, style = GalleryType.body(), maxLines = 1, overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.clickable(role = Role.Button) { open.genre(g.lowercase(), g) },
                        )
                    }
                }
            }
        }
        if (artistId != null || d.canPaths) item {
            FlowRow(
                Modifier.fillMaxWidth().galleryArrive(2).padding(start = gutter, end = gutter, top = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(6.dp), itemVerticalAlignment = Alignment.CenterVertically,
            ) {
                if (artistId != null) {
                    GalleryButton("Play", { play.playArtist(artistId, shuffle = false) }, icon = GalleryIcons.Play)
                    GalleryButton("Shuffle", { play.playArtist(artistId, shuffle = true) }, kind = GalleryButtonKind.Text, icon = GalleryIcons.Shuffle)
                }
                if (d.canPaths) GalleryButton("Paths", d.onPaths, kind = GalleryButtonKind.Text, icon = GalleryIcons.Paths)
            }
        }
        val allSongs = d.sections.topSongs.items
        if (allSongs.isNotEmpty()) {
            val more = allSongs.size > GalleryPagesRules.SONGS_SHOWN && !showAllSongs
            item { Column(Modifier.galleryArrive(3)) { GallerySectionHead("Top songs", link = if (more) "All top songs" else null, onLink = onAllSongs) } }
            val shown = if (showAllSongs) allSongs else allSongs.take(GalleryPagesRules.SONGS_SHOWN)
            itemsIndexed(shown) { i, song -> Column(Modifier.galleryArrive(3)) { TopSongRow(d, song, i < shown.lastIndex) } }
        }
        if (owned.isNotEmpty()) {
            val more = owned.size > GalleryPagesRules.ALBUMS_SHOWN && !showAllAlbums
            item { Column(Modifier.galleryArrive(4)) { GallerySectionHead("In your library", link = if (more) "All albums" else null, onLink = { showAllAlbums = true }) } }
            val shown = if (showAllAlbums) owned else owned.take(GalleryPagesRules.ALBUMS_SHOWN)
            items2(shown) { pair ->
                Row(Modifier.fillMaxWidth().padding(horizontal = gutter).padding(bottom = 20.dp), horizontalArrangement = Arrangement.spacedBy(18.dp)) {
                    pair.forEach { album ->
                        GalleryCaption(album.name, album.year?.toString().orEmpty(), Modifier.weight(1f), sharedKey = album.key, onClick = { open.album(album.key, d.name, album.name, album.id, album.year) }) {
                            AlbumCover(d.name, album.name, album.artworkUrl, Modifier.fillMaxWidth().aspectRatio(1f), rect = true)
                        }
                    }
                    if (pair.size == 1) Box(Modifier.weight(1f))
                }
            }
        }
        val missing = d.sections.missingAlbums.items
        if (missing.isNotEmpty()) {
            // Missing albums read like the album page's Similar albums: one row of prints; the album page they open has Get.
            item { GallerySectionHead("Missing albums") }
            item {
                LazyRow(contentPadding = PaddingValues(horizontal = gutter), horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                    itemsIndexed(missing, key = { i, it -> "$i|${it.key}|${it.name}" }) { _, album ->
                        val said = listOfNotNull(album.name, d.name, GalleryPagesRules.missingSub(album.year, album.popularity).ifBlank { null }).joinToString(", ")
                        GalleryPrint(
                            GalleryPagesRules.SIMILAR_PRINT_DP.dp,
                            Modifier.clickable(role = Role.Button) { open.album(album.key, d.name, album.name, null, album.year) }.semantics { contentDescription = said },
                        ) { AlbumCover(d.name, album.name, null, Modifier.fillMaxWidth().aspectRatio(1f), rect = true) }
                    }
                }
            }
        }
        val bio = d.sections.bio.bio?.text.orEmpty()
        if (bio.isNotBlank()) {
            item { GallerySectionHead("About") }
            item { GalleryReadMore(bio, Modifier.padding(horizontal = gutter)) }
        }
        if (d.collage.isNotEmpty()) item { ArtistPhotoStrip(d.collage, d.name, open) }
        if (d.similar.isNotEmpty()) {
            item { GallerySectionHead("Similar artists") }
            item {
                LazyRow(contentPadding = PaddingValues(horizontal = gutter), horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                    itemsIndexed(d.similar, key = { i, it -> "$i|${it.name}" }) { _, a ->
                        GalleryArtistPlate(a.name, null, a.artworkUrl) { open.artist(a.name, a.key, a.id, a.mbid) }
                    }
                }
            }
        }
    }
}

/** Items of two, for the captioned prints of the library (a grid of two columns, 18dp apart). */
private fun <T> androidx.compose.foundation.lazy.LazyListScope.items2(list: List<T>, content: @Composable (List<T>) -> Unit) {
    list.chunked(2).forEach { pair -> item { content(pair) } }
}

/** A top song (gallery.css `.row`): a 48dp print of its album, the song in Fraunces italic over the album, then Get or the menu of ways to play. */
@Composable
private fun TopSongRow(d: CoverStackArtistData, song: TopSong, divider: Boolean) {
    val play = LocalPlayActions.current
    val onAlbum = song.album?.takeIf { it.isNotBlank() }
    val ownedAlbum = onAlbum?.let { a -> d.owned.firstOrNull { it.name.equals(a, ignoreCase = true) } }
    // An owned top song plays from its album when the album is in the library.
    val albumId = ownedAlbum?.id?.takeIf { it.isNotBlank() }
    GalleryRow(
        song.name, Modifier.padding(horizontal = GalleryRules.GUTTER.dp), sub = onAlbum.orEmpty(), divider = divider, italicTitle = true,
        onClick = if (song.owned && albumId != null) ({ play.playAlbum(albumId, song.name, null) }) else null,
        lead = { GalleryPrint(GalleryPagesRules.ROW_PRINT_DP.dp) { AlbumCover(d.name, onAlbum ?: song.name, ownedAlbum?.artworkUrl, Modifier.fillMaxWidth().aspectRatio(1f), rect = true) } },
        trail = {
            // Only a song that names its album can be filed with it (ACQ-08).
            if (!song.owned && onAlbum != null) Box(Modifier.padding(end = 0.dp)) { GetSongButton(d.name, onAlbum, song.name, null, null) }
            if (song.owned && albumId != null) GalleryMenuButton(
                "More ways to play ${song.name}",
                listOf(
                    GalleryMenuItem("Play next", GalleryIcons.Next) { play.queueTrack(albumId, song.name, null, next = true) },
                    GalleryMenuItem("Add to queue", GalleryIcons.QueueAdd) { play.queueTrack(albumId, song.name, null, next = false) },
                    GalleryMenuItem("Download to device", GalleryIcons.Download) { play.downloadTrack(albumId, song.name, null) },
                ),
                header = GalleryMenuHeader(song.name, GalleryPagesRules.menuLine(d.name, onAlbum)) {
                    AlbumCover(d.name, onAlbum ?: song.name, ownedAlbum?.artworkUrl, Modifier.fillMaxSize(), rect = true)
                },
            )
        },
    )
}
