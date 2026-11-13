package app.discair.ui.album

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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import app.discair.ui.Opener
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.Button
import app.discair.ui.common.FlowArtistChip
import app.discair.ui.common.FlowCircleButton
import app.discair.ui.common.FlowCover
import app.discair.ui.common.FlowDivider
import app.discair.ui.common.FlowHeading
import app.discair.ui.common.FlowPageBar
import app.discair.ui.common.FlowPagesRules
import app.discair.ui.common.FlowRules
import app.discair.ui.common.GetAlbumButton
import app.discair.ui.common.GetSongButton
import app.discair.ui.common.OutlinedButton
import app.discair.ui.common.Target
import app.discair.ui.common.flowDepth
import app.discair.ui.common.pageMetadata
import app.discair.ui.common.sharedCover
import app.discair.ui.player.LocalPlayActions
import app.discair.ui.player.LocalPlayingNow
import app.discair.ui.player.NowPlayingIndicator
import app.discair.ui.player.PlayerIcons
import app.discair.ui.player.RowMoreMenu
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.accentText

/**
 * Flow's Album page (mockup flow/album-artist-genre, frame 1): the cover in front at 232dp on a wash of its own colour, the title large and
 * centred, the artist as an accent link, one muted meta line, Play, Shuffle and a round button, then plain song rows with hairlines (the playing
 * song in accent), and a strip of similar albums. The data is [CoverStackAlbumData], the same the Soft Brut page takes; only the arrangement differs.
 * [onTint] receives the cover's colour for the wash behind the page.
 */
@Composable
internal fun FlowAlbumContent(d: CoverStackAlbumData, open: Opener, list: LazyListState, onTint: (Color) -> Unit) {
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
        item { FlowPageBar(open.back, menu) }
        item {
            Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Cover(d, onTint)
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        d.title, color = p.text, textAlign = TextAlign.Center,
                        style = MaterialTheme.typography.headlineMedium.copy(fontSize = 24.sp, lineHeight = 28.sp, fontWeight = FontWeight.Bold, letterSpacing = (-0.02).em),
                        modifier = Modifier.semantics { heading() },
                    )
                    Box(
                        Modifier.heightIn(min = Target).clickable(role = Role.Button) { open.artist(d.artist, d.info?.artistKey?.ifBlank { null }, d.info?.artistId, null) },
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(d.artist, color = p.accentText, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Medium, fontSize = 14.sp))
                    }
                    MetaLine(d, open)
                    if (!d.owned) Text("Not in your library", color = p.caution, style = MaterialTheme.typography.bodyMedium)
                }
                if (albumId != null) Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Button(onClick = { play.playAlbum(albumId) }) {
                        Icon(PlayerIcons.Play, contentDescription = null, Modifier.size(20.dp)); Text(" Play")
                    }
                    OutlinedButton(onClick = { play.playAlbum(albumId, shuffle = true) }) {
                        Icon(PlayerIcons.Shuffle, contentDescription = null, Modifier.size(20.dp)); Text(" Shuffle")
                    }
                    // The round button of the mockup's download slot: the album's Paths, as on the Soft Brut page (the per-song actions stay on the rows).
                    if (d.pathsOn) FlowCircleButton(PlayerIcons.Paths, "Paths from this album", d.onPaths, size = 44)
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
            item { FlowHeading("Similar albums", Modifier.padding(top = 20.dp, bottom = 10.dp)) }
            item {
                LazyRow(contentPadding = PaddingValues(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    items(d.similarAlbums, key = { it.key + it.name }) { album ->
                        Column(
                            Modifier.width(FlowPagesRules.SIMILAR_COVER.dp).clip(RoundedCornerShape(8.dp))
                                .clickable(role = Role.Button) { open.album(album.key, album.artist, album.name, null, album.year) },
                            verticalArrangement = Arrangement.spacedBy(2.dp),
                        ) {
                            FlowCover(album.artist, album.name, null, Modifier.fillMaxWidth())
                            Text(album.name, Modifier.padding(top = 6.dp), color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold, fontSize = 14.sp))
                            Text(album.artist, color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall.copy(fontSize = 13.sp, lineHeight = 18.sp))
                            // The owned state is said in words, never by colour alone.
                            if (album.owned) Text("In your library", color = p.ok, maxLines = 1, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
        }
        if (d.similarArtists.isNotEmpty()) {
            item { FlowHeading("Similar artists", Modifier.padding(top = 20.dp, bottom = 10.dp)) }
            item {
                LazyRow(contentPadding = PaddingValues(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    items(d.similarArtists, key = { it.name }) { a -> FlowArtistChip(a.name, a.artworkUrl, { open.artist(a.name, a.key, a.id, a.mbid) }) }
                }
            }
        }
    }
}

/** The cover in front: 232dp, radius 14, level 3 depth (flow.css `.hero .art`). Keeps the flip and the edition stack; its colour feeds the wash. */
@Composable
private fun Cover(d: CoverStackAlbumData, onTint: (Color) -> Unit) {
    val p = LocalPalette.current
    val size = FlowPagesRules.ALBUM_COVER.dp
    val shape = RoundedCornerShape(FlowRules.RADIUS_COVER.dp)
    Box(Modifier.padding(top = 2.dp, bottom = 8.dp).size(size).flowDepth(3, shape, p).clip(shape)) {
        FlipCover(d.backs, size) {
            Box(Modifier.size(size)) {
                AlbumCover(d.artist, d.title, d.coverUrl, Modifier.size(size).sharedCover(d.route.key), rect = true, onColor = onTint)
                if (d.canPickEdition) EditionStack(d.editionCount, d.onPickEdition, Modifier.align(Alignment.BottomStart))
            }
        }
    }
}

/** "1991 · Art rock · 6 songs · FLAC", centred; the genre opens its page. */
@Composable
private fun MetaLine(d: CoverStackAlbumData, open: Opener) {
    val p = LocalPalette.current
    val small = MaterialTheme.typography.bodySmall
    val songs = if (d.tracks.isNotEmpty()) "${d.tracks.size} ${if (d.tracks.size == 1) "song" else "songs"}" else null
    val before = listOfNotNull(d.year?.toString()).joinToString(" · ")
    val after = listOfNotNull(songs, d.info?.quality?.takeIf { it.isNotBlank() }).joinToString(" · ")
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.Center) {
        if (before.isNotEmpty()) Text(before, color = p.textMuted, style = small, maxLines = 1)
        val genre = d.genre
        if (!genre.isNullOrBlank()) {
            if (before.isNotEmpty()) Text(" · ", color = p.textMuted, style = small)
            Box(
                Modifier.weight(1f, fill = false).heightIn(min = Target).clickable(role = Role.Button) { open.genre(genre.lowercase(), genre) },
                contentAlignment = Alignment.CenterStart,
            ) { Text(genre, color = p.textMuted, style = small, maxLines = 1, overflow = TextOverflow.Ellipsis) }
        }
        if (after.isNotEmpty()) Text(((if (before.isNotEmpty() || !genre.isNullOrBlank()) " · " else "") + after), color = p.textMuted, style = small, maxLines = 1)
    }
}

/** A song (flow.css `.trow`): number or the playing mark in a 24dp column, title, length, a hairline; 48dp or more. The playing song is accent, 600. */
@Composable
private fun SongRow(d: CoverStackAlbumData, i: Int, albumId: String?) {
    val p = LocalPalette.current
    val play = LocalPlayActions.current
    val t = d.tracks[i]
    val playingNow = LocalPlayingNow.current
    val current = t.owned && playingNow?.matches(albumId, t.title, t.number, t.disc ?: 1) == true
    Column {
        Row(
            Modifier.fillMaxWidth().heightIn(min = 48.dp)
                .let { if (t.owned && albumId != null) it.clickable(onClickLabel = "Play ${t.title}", role = Role.Button) { play.playAlbum(albumId, t.title, t.number, startDisc = t.disc) } else it }
                .padding(horizontal = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(Modifier.width(24.dp)) {
                if (current) NowPlayingIndicator(playingNow!!.isPlaying)
                else Text("${trackNumberShown(d.tracks, i)}", color = p.textMuted, style = MaterialTheme.typography.bodySmall)
            }
            Text(
                t.title, Modifier.weight(1f), color = if (current) p.accentText else p.text, maxLines = 2, overflow = TextOverflow.Ellipsis,
                style = MaterialTheme.typography.bodyMedium.copy(fontSize = 15.sp, lineHeight = 20.sp, fontWeight = if (current) FontWeight.SemiBold else FontWeight.Normal),
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
        if (i < d.tracks.lastIndex) FlowDivider(Modifier.padding(horizontal = 16.dp))
    }
}
