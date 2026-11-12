package app.discair.ui.album

import androidx.compose.foundation.background
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
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.model.AlbumInfo
import app.discair.model.ArtworkImage
import app.discair.model.BookletView
import app.discair.model.SimilarAlbum
import app.discair.model.SimilarArtist
import app.discair.model.Track
import app.discair.ui.AlbumRoute
import app.discair.ui.Opener
import app.discair.ui.common.AlbumCover
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
import app.discair.ui.common.Target
import app.discair.ui.common.coverStackShadow
import app.discair.ui.common.describedAs
import app.discair.ui.common.pageMetadata
import app.discair.ui.common.sharedCover
import app.discair.ui.player.LocalPlayActions
import app.discair.ui.player.LocalPlayingNow
import app.discair.ui.player.NowPlayingIndicator
import app.discair.ui.player.PlayerIcons
import app.discair.ui.player.RowMoreMenu
import app.discair.ui.theme.LocalPalette

/** What the Album page has loaded and decided; the Cover Stack page only draws it. */
internal class CoverStackAlbumData(
    val route: AlbumRoute,
    val info: AlbumInfo?,
    val title: String,
    val artist: String,
    val year: Int?,
    val genre: String?,
    val owned: Boolean,
    val albumId: String?,
    val tracks: List<Track>,
    val coverUrl: String?,
    val backs: List<ArtworkImage>,
    val editionCount: Int,
    val canPickEdition: Boolean,
    val onPickEdition: () -> Unit,
    val booklet: BookletView?,
    val description: app.discair.model.Description?,
    val descriptionFinished: Boolean,
    val similarAlbums: List<SimilarAlbum>,
    val similarArtists: List<SimilarArtist>,
    val pathsOn: Boolean,
    val onPaths: () -> Unit,
)

/**
 * Soft Brut's Album page (mockup soft-brut/album-artist-genre, frame 1): the cover at the left on a tilted lavender second sleeve,
 * the title, the artist as an ink link, one meta line, Play, Shuffle and a download button, then the song rows (the playing song is a
 * filled row) and a strip of similar albums. Behaviour is the Standard page's: only the arrangement differs.
 */
@Composable
internal fun CoverStackAlbumContent(d: CoverStackAlbumData, open: Opener, list: LazyListState) {
    val p = LocalPalette.current
    val play = LocalPlayActions.current
    val albumId = d.albumId
    val menu = buildList {
        if (albumId != null) {
            add("Play next" to { play.queueAlbum(albumId, next = true) })
            add("Add to queue" to { play.queueAlbum(albumId, next = false) })
        }
        if (d.pathsOn && albumId != null) add("Paths" to d.onPaths)
    }
    LazyColumn(Modifier.fillMaxSize(), state = list, contentPadding = PaddingValues(bottom = 32.dp + app.discair.ui.LocalBottomClearance.current)) {
        item { CoverStackTopBar(open.back, menu) }
        item {
            Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Sleeve(d)
                Column {
                    CoverStackTitle(d.title)
                    Box(
                        Modifier.heightIn(min = Target)
                            .clickable(role = Role.Button) { open.artist(d.artist, d.info?.artistKey?.ifBlank { null }, d.info?.artistId, null) },
                        contentAlignment = Alignment.CenterStart,
                    ) {
                        Text(
                            d.artist, color = p.text, textDecoration = TextDecoration.Underline,
                            style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold),
                        )
                    }
                    MetaLine(d, open)
                    if (!d.owned) Text("Not in your library", color = p.caution, style = MaterialTheme.typography.bodyMedium)
                }
                if (albumId != null) Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Button(onClick = { play.playAlbum(albumId) }, Modifier.heightIn(min = Target)) {
                        Icon(PlayerIcons.Play, contentDescription = null, Modifier.size(20.dp)); Text(" Play")
                    }
                    OutlinedButton(onClick = { play.playAlbum(albumId, shuffle = true) }, Modifier.heightIn(min = Target)) {
                        Icon(PlayerIcons.Shuffle, contentDescription = null, Modifier.size(20.dp)); Text(" Shuffle")
                    }
                    // Saves every song of the album the library holds, one by one, with the Standard page's per-song action.
                    OutlinedButton(
                        onClick = { d.tracks.filter { it.owned }.forEach { play.downloadTrack(albumId, it.title, it.number, disc = it.disc) } },
                        Modifier.size(Target), contentPadding = PaddingValues(0.dp),
                    ) { Icon(PlayerIcons.DownloadToDevice, contentDescription = "Download album to device", Modifier.size(20.dp)) }
                }
                // The album-level Get stays until every track is in the library (ACQ-08).
                if (!d.owned || d.tracks.any { !it.owned }) GetAlbumButton(d.artist, d.title, pageMetadata(d.artist, d.title, d.year, d.info?.releaseGroupMbid))
            }
        }
        if (d.tracks.isNotEmpty()) {
            for (i in d.tracks.indices) {
                if (startsDisc(d.tracks, i)) item(key = "disc-${d.tracks[i].disc}") { DiscHeading(d.tracks[i].disc ?: 1) }
                item { SongRow(d, i, albumId) }
            }
            item { Summary(d.tracks.size, d.tracks.sumOf { it.durationSeconds ?: 0 }, d.tracks.count { it.owned }) }
        }
        item { InfoReviewsTabs(d.artist, d.title, d.description, d.descriptionFinished, d.booklet) }
        item { ServiceLinks(d.artist, d.title, d.info?.releaseGroupMbid) }
        if (d.similarAlbums.isNotEmpty()) {
            item { CoverStackHeading("Similar albums", Modifier.padding(top = 16.dp, bottom = 8.dp)) }
            item {
                LazyRow(contentPadding = PaddingValues(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    items(d.similarAlbums, key = { it.key + it.name }) { album ->
                        Column(
                            Modifier.width(112.dp).clip(RoundedCornerShape(6.dp))
                                .clickable(role = Role.Button) { open.album(album.key, album.artist, album.name, null, album.year) },
                            verticalArrangement = Arrangement.spacedBy(2.dp),
                        ) {
                            CoverStackCover(album.artist, album.name, null, Modifier.fillMaxWidth())
                            Text(album.name, Modifier.padding(top = 6.dp), color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold))
                            Text(album.artist, color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall)
                            // The owned state is said in words, never by colour alone.
                            if (album.owned) Text("In your library", color = p.ok, maxLines = 1, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
        }
        if (d.similarArtists.isNotEmpty()) {
            item { CoverStackHeading("Similar artists", Modifier.padding(top = 16.dp, bottom = 8.dp)) }
            item {
                LazyRow(contentPadding = PaddingValues(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    items(d.similarArtists, key = { it.name }) { a -> CoverStackArtistChip(a.name, a.artworkUrl, { open.artist(a.name, a.key, a.id, a.mbid) }) }
                }
            }
        }
    }
}

/** The 216dp cover (radius 12, 4dp shadow) over a tilted lavender second sleeve (mockup `.hero .art`). Keeps the flip and the edition stack. */
@Composable
private fun Sleeve(d: CoverStackAlbumData) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(12.dp)
    val ol = CoverStackRules.outline(p).dp
    Box(Modifier.padding(start = 6.dp, top = 4.dp, bottom = 14.dp, end = 16.dp).size(216.dp)) {
        Box(Modifier.size(216.dp).offset(12.dp, 8.dp).graphicsLayer { rotationZ = 4f }.clip(shape).background(p.accent).border(ol, p.edgeStrong, shape))
        Box(Modifier.size(216.dp).coverStackShadow(shape, p, 4f).clip(shape)) {
            FlipCover(d.backs, 216.dp) {
                Box(Modifier.size(216.dp)) {
                    AlbumCover(d.artist, d.title, d.coverUrl, Modifier.size(216.dp).sharedCover(d.route.key), rect = true)
                    if (d.canPickEdition) EditionStack(d.editionCount, d.onPickEdition, Modifier.align(Alignment.BottomStart))
                }
            }
            Box(Modifier.size(216.dp).border(ol, p.edgeStrong, shape))
        }
    }
}

/** "1991 · Art rock · 6 songs · FLAC": the genre opens its page; the quality moved here from the cover's corner. */
@Composable
private fun MetaLine(d: CoverStackAlbumData, open: Opener) {
    val p = LocalPalette.current
    val small = MaterialTheme.typography.bodySmall
    val songs = if (d.tracks.isNotEmpty()) "${d.tracks.size} ${if (d.tracks.size == 1) "song" else "songs"}" else null
    val before = listOfNotNull(d.year?.toString()).joinToString(" · ")
    val after = listOfNotNull(songs, d.info?.quality?.takeIf { it.isNotBlank() }).joinToString(" · ")
    Row(verticalAlignment = Alignment.CenterVertically) {
        if (before.isNotEmpty()) Text(before, color = p.textMuted, style = small, maxLines = 1)
        val genre = d.genre
        if (!genre.isNullOrBlank()) {
            if (before.isNotEmpty()) Text(" · ", color = p.textMuted, style = small)
            Text(
                genre, color = p.textMuted, style = small, maxLines = 1, overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f, fill = false).heightIn(min = Target).clickable(role = Role.Button) { open.genre(genre.lowercase(), genre) }.padding(vertical = 14.dp),
            )
        }
        if (after.isNotEmpty()) Text(((if (before.isNotEmpty() || !genre.isNullOrBlank()) " · " else "") + after), color = p.textMuted, style = small, maxLines = 1)
    }
}

/** A song: number (or the playing mark), title, length. 52dp or more, a dashed divider; the playing song is a filled, ruled row (mockup `.trow`). */
@Composable
private fun SongRow(d: CoverStackAlbumData, i: Int, albumId: String?) {
    val p = LocalPalette.current
    val play = LocalPlayActions.current
    val t = d.tracks[i]
    val playingNow = LocalPlayingNow.current
    val current = t.owned && playingNow?.matches(albumId, t.title, t.number, t.disc ?: 1) == true
    val ol = CoverStackRules.outline(p)
    Column {
        Row(
            Modifier.fillMaxWidth().heightIn(min = 52.dp)
                .then(
                    if (current) Modifier.background(p.accentDim).drawBehind {
                        val w = ol.dp.toPx()
                        drawLine(p.edgeStrong, Offset(0f, w / 2), Offset(size.width, w / 2), w)
                        drawLine(p.edgeStrong, Offset(0f, size.height - w / 2), Offset(size.width, size.height - w / 2), w)
                    } else Modifier,
                )
                .let { if (t.owned && albumId != null) it.clickable(onClickLabel = "Play ${t.title}", role = Role.Button) { play.playAlbum(albumId, t.title, t.number, startDisc = t.disc) } else it }
                .padding(horizontal = 16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(Modifier.width(34.dp)) {
                if (current) NowPlayingIndicator(playingNow!!.isPlaying)
                else Text("${trackNumberShown(d.tracks, i)}", color = p.textMuted, style = MaterialTheme.typography.bodySmall)
            }
            Text(
                t.title, Modifier.weight(1f).padding(end = 8.dp), color = p.text, maxLines = 2, overflow = TextOverflow.Ellipsis,
                style = MaterialTheme.typography.bodyMedium.copy(fontSize = 14.sp, lineHeight = 20.sp),
            )
            t.durationSeconds?.let { Text("%d:%02d".format(it / 60, it % 60), color = p.textMuted, style = MaterialTheme.typography.bodySmall) }
            // Only a song the library lacks has a Get slot; an owned row keeps its menu of ways to play.
            if (!t.owned) Box(Modifier.size(Target), contentAlignment = Alignment.Center) { GetSongButton(d.artist, d.title, t.title, t.number, d.year) }
            if (t.owned && albumId != null) RowMoreMenu(
                t.title,
                listOf(
                    "Play next" to { play.queueTrack(albumId, t.title, t.number, next = true, disc = t.disc) },
                    "Add to queue" to { play.queueTrack(albumId, t.title, t.number, next = false, disc = t.disc) },
                    "Download to device" to { play.downloadTrack(albumId, t.title, t.number, disc = t.disc) },
                ),
            )
        }
        if (!current) CoverStackDivider(Modifier.padding(horizontal = 16.dp))
    }
}
