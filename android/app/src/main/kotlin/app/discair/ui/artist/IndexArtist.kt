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
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.model.TopSong
import app.discair.ui.Opener
import app.discair.ui.album.MoreMenu
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.ArtistPhoto
import app.discair.ui.common.GetSongButton
import app.discair.ui.common.IndexButton
import app.discair.ui.common.IndexButtonBody
import app.discair.ui.common.IndexButtonKind
import app.discair.ui.common.IndexDataList
import app.discair.ui.common.IndexDatum
import app.discair.ui.common.IndexIcons
import app.discair.ui.common.IndexLabel
import app.discair.ui.common.IndexPageBar
import app.discair.ui.common.IndexPagesRules
import app.discair.ui.common.IndexRow
import app.discair.ui.common.IndexRules
import app.discair.ui.common.IndexSectionHead
import app.discair.ui.common.IndexType
import app.discair.ui.common.indexArrive
import app.discair.ui.player.LocalPlayActions
import app.discair.ui.theme.LocalPalette

private val Gutter = IndexRules.GUTTER.dp

/** One square of the Albums grid: an album in the library, or one the provider lists and the library lacks (drawn at half strength, with GET). */
private class GridAlbum(val name: String, val year: Int?, val key: String, val id: String?, val artworkUrl: String?, val owned: Boolean)

/*
 * Index's Artist page (Layout.Index). Spec: docs/plans/INDEX_THEME.md step I3; mockup: docs/design/index/pages/album-artist-genre.html, frame 3.
 * A 150 by 180 photo beside the name and the data list (Genre, Owned "5 of 9", Plays, Active), then Play / Shuffle / Paths, numbered top songs, the albums as
 * a four-column grid with the ones to get, the biography, the photo strip and similar artists. The data is [CoverStackArtistData]; the new I0 fields
 * (plays, active years, owned of total) are shown only when the server sends them.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun IndexArtistContent(d: CoverStackArtistData, open: Opener, list: LazyListState, showAllSongs: Boolean, onAllSongs: () -> Unit) {
    val p = LocalPalette.current
    val play = LocalPlayActions.current
    val artistId = d.artistId
    val info = d.sections.artist.artist
    val menu = buildList {
        if (artistId != null) {
            add("Play next" to { play.queueArtist(artistId, next = true) })
            add("Add to queue" to { play.queueArtist(artistId, next = false) })
        }
    }
    val genres = d.sections.tags.items.map { it.name }.ifEmpty { listOfNotNull(info?.genre) }.filter { it.isNotBlank() }.take(3)
    var allAlbums by remember(d.route) { mutableStateOf(false) }
    val missing = d.sections.missingAlbums.items
    val grid = remember(d.owned, missing) {
        // The library's albums first, then the ones to get, each by year: an artist with many to get still shows what the owner has.
        d.owned.map { GridAlbum(it.name, it.year, it.key, it.id, it.artworkUrl, true) }.sortedWith(compareBy(nullsLast()) { it.year }) +
            missing.map { GridAlbum(it.name, it.year, it.key, null, null, false) }.sortedWith(compareBy(nullsLast()) { it.year })
    }
    val rows = remember(d.sections, genres, d.owned.size) {
        val base = IndexPagesRules.artistRows(
            genres.firstOrNull(), d.sections.albums.ownedCount, d.sections.albums.albumCount, d.ownedAlbumCount ?: d.owned.size, d.inLibrary, info?.playCount, info?.activeYears,
        )
        // The other genres follow the first under the same key, each a link to its genre page.
        base.flatMap { row -> if (row.key == "Genre") genres.mapIndexed { i, g -> IndexDatum(if (i == 0) "Genre" else "", g, onClick = { open.genre(g.lowercase(), g) }) } else listOf(row) }
    }

    LazyColumn(Modifier.fillMaxSize(), state = list, contentPadding = PaddingValues(bottom = 32.dp + app.discair.ui.LocalBottomClearance.current)) {
        item { IndexPageBar("Artist", open.back, action = { if (menu.isNotEmpty()) MoreMenu("More for ${d.name}", menu) }) }
        item {
            val h = IndexPagesRules.ARTIST_PHOTO_H_DP.dp
            Row(Modifier.fillMaxWidth().indexArrive(0).padding(start = Gutter, end = Gutter, top = 4.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                ArtistPhoto(d.name, d.owned.firstOrNull()?.artworkUrl, Modifier.size(IndexPagesRules.ARTIST_PHOTO_W_DP.dp, h), rect = true)
                Column(Modifier.weight(1f).heightIn(min = h), verticalArrangement = Arrangement.SpaceBetween) {
                    Text(d.name, Modifier.semantics { heading() }, style = IndexType.leadTitle(), color = p.text, maxLines = 4, overflow = TextOverflow.Ellipsis)
                    IndexDataList(rows, Modifier.padding(top = 10.dp))
                }
            }
        }
        if (artistId != null || d.canPaths) item {
            FlowRow(
                Modifier.fillMaxWidth().indexArrive(1).padding(start = Gutter, end = Gutter, top = 14.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(6.dp), itemVerticalAlignment = Alignment.CenterVertically,
            ) {
                if (artistId != null) IndexButton("Play", { play.playArtist(artistId, shuffle = false) }, icon = IndexIcons.Play)
                if (artistId != null) IndexButtonBody(IndexButtonKind.Ghost, { play.playArtist(artistId, shuffle = true) }, Modifier.semantics { contentDescription = "Shuffle" }, enabled = true, small = false) {
                    Icon(IndexIcons.Shuffle, null, Modifier.size(IndexRules.ICON_INLINE.dp))
                }
                if (d.canPaths) IndexButton("Paths", d.onPaths, kind = IndexButtonKind.Ghost, icon = IndexIcons.Paths)
            }
        }
        val allSongs = d.sections.topSongs.items
        if (allSongs.isNotEmpty()) {
            val more = allSongs.size > IndexPagesRules.SONGS_SHOWN && !showAllSongs
            item { IndexSectionHead("Top songs", Modifier.indexArrive(2), meta = "Plays", link = if (more) "All" else null, onLink = onAllSongs) }
            val shown = if (showAllSongs) allSongs else allSongs.take(IndexPagesRules.SONGS_SHOWN)
            shown.forEachIndexed { i, song -> item { TopSongRow(d, song, i, Modifier.indexArrive(3 + i)) } }
        }
        if (grid.isNotEmpty()) {
            val more = grid.size > IndexPagesRules.ALBUMS_SHOWN && !allAlbums
            item { IndexSectionHead("Albums", meta = IndexPagesRules.toGet(missing.size) ?: grid.size.toString(), link = if (more) "All" else null, onLink = { allAlbums = true }) }
            val shown = if (allAlbums) grid else grid.take(IndexPagesRules.ALBUMS_SHOWN)
            shown.chunked(IndexPagesRules.COLUMNS).forEach { row ->
                item {
                    Row(Modifier.fillMaxWidth().padding(start = Gutter, end = Gutter, top = 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        row.forEach { a -> AlbumSquare(d.name, a, open, Modifier.weight(1f)) }
                        repeat(IndexPagesRules.COLUMNS - row.size) { Box(Modifier.weight(1f)) }
                    }
                }
            }
        }
        val bio = d.sections.bio.bio?.text.orEmpty()
        if (bio.isNotBlank()) {
            item { IndexSectionHead("About") }
            item { About(bio) }
        }
        if (d.collage.isNotEmpty()) item { ArtistPhotoStrip(d.collage, d.name, open) }
        if (d.similar.isNotEmpty()) {
            item { IndexSectionHead("Similar artists", meta = d.similar.size.toString()) }
            d.similar.forEachIndexed { i, a ->
                item {
                    IndexRow(
                        a.name, Modifier.padding(horizontal = Gutter), meta = if (a.owned) "In library" else "Not in library", number = IndexPagesRules.number(i),
                        onClick = { open.artist(a.name, a.key, a.id, a.mbid) },
                        lead = { ArtistPhoto(a.name, a.artworkUrl, Modifier.size(48.dp), rect = true) },
                    )
                }
            }
        }
    }
}

/** A top song: its number, a 48dp cover of its album, the song over the album in mono, then Get (a song the library lacks) or the three dots. */
@Composable
private fun TopSongRow(d: CoverStackArtistData, song: TopSong, i: Int, modifier: Modifier) {
    val play = LocalPlayActions.current
    val onAlbum = song.album?.takeIf { it.isNotBlank() }
    val ownedAlbum = onAlbum?.let { a -> d.owned.firstOrNull { it.name.equals(a, ignoreCase = true) } }
    // An owned top song plays from its album when the album is in the library.
    val albumId = ownedAlbum?.id?.takeIf { it.isNotBlank() }
    IndexRow(
        song.name, modifier.padding(horizontal = Gutter), meta = onAlbum.orEmpty(), number = IndexPagesRules.number(i),
        onClick = if (song.owned && albumId != null) ({ play.playAlbum(albumId, song.name, null) }) else null,
        lead = { AlbumCover(d.name, onAlbum ?: song.name, ownedAlbum?.artworkUrl, Modifier.size(48.dp), rect = true) },
        trail = {
            // Only a song that names its album can be filed with it (ACQ-08).
            if (!song.owned && onAlbum != null) GetSongButton(d.name, onAlbum, song.name, null, null)
            if (song.owned && albumId != null) MoreMenu(
                "More ways to play ${song.name}",
                listOf(
                    "Play next" to { play.queueTrack(albumId, song.name, null, next = true) },
                    "Add to queue" to { play.queueTrack(albumId, song.name, null, next = false) },
                    "Download to device" to { play.downloadTrack(albumId, song.name, null) },
                ),
            )
        },
    )
}

/** One square of the Albums grid: the cover, the year in mono, and GET in `accent` under an album the library lacks (half strength); it opens the album, which has Get. */
@Composable
private fun AlbumSquare(artist: String, a: GridAlbum, open: Opener, modifier: Modifier) {
    val p = LocalPalette.current
    val said = listOfNotNull(a.name, a.year?.toString(), if (a.owned) "in your library" else "not in your library").joinToString(", ")
    Column(
        modifier.clickable(role = Role.Button) { open.album(a.key, artist, a.name, a.id, a.year) }.semantics(mergeDescendants = true) { contentDescription = said },
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        AlbumCover(artist, a.name, a.artworkUrl, Modifier.fillMaxWidth().aspectRatio(1f).alpha(if (a.owned) 1f else 0.5f), rect = true)
        IndexLabel(a.year?.toString() ?: "—")
        if (!a.owned) IndexLabel("Get", color = p.accent)
    }
}

/** The biography, folded after eight lines behind MORE. */
@Composable
private fun About(text: String) {
    val p = LocalPalette.current
    var all by remember(text) { mutableStateOf(false) }
    Column(Modifier.padding(start = Gutter, end = Gutter, top = 6.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(text, style = IndexType.body(), color = p.text, maxLines = if (all) Int.MAX_VALUE else 8, overflow = TextOverflow.Ellipsis)
        if (!all) Text(
            "MORE →", style = IndexType.label().copy(fontWeight = FontWeight.Medium), color = p.accent,
            modifier = Modifier.heightIn(min = 24.dp).clickable(role = Role.Button, onClickLabel = "Read the whole biography") { all = true },
        )
    }
}
