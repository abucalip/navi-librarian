package app.discair.ui.album

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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.model.FeedbackAction
import app.discair.ui.Opener
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.GalleryArtistPlate
import app.discair.ui.common.GalleryButton
import app.discair.ui.common.GalleryButtonKind
import app.discair.ui.common.GalleryDiscHeading
import app.discair.ui.common.GalleryEyebrow
import app.discair.ui.common.GalleryGetAlbumButton
import app.discair.ui.common.GalleryIcons
import app.discair.ui.common.GalleryMenuButton
import app.discair.ui.common.GalleryMuted
import app.discair.ui.common.GalleryNote
import app.discair.ui.common.GalleryPageBar
import app.discair.ui.common.GalleryPagesRules
import app.discair.ui.common.GalleryPlayingBars
import app.discair.ui.common.GalleryPrint
import app.discair.ui.common.GalleryMenuItem
import app.discair.ui.common.GalleryMenuHeader
import app.discair.ui.common.galleryArrive
import app.discair.ui.common.GalleryReadMore
import app.discair.ui.common.GalleryRule
import app.discair.ui.common.GalleryRules
import app.discair.ui.common.GallerySectionHead
import app.discair.ui.common.GalleryTabs
import app.discair.ui.common.GalleryTextLink
import app.discair.ui.common.GalleryType
import app.discair.ui.common.GetSongButton
import app.discair.ui.common.Load
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.pageMetadata
import app.discair.ui.common.rememberLoad
import app.discair.ui.player.LocalPlayActions
import app.discair.ui.player.LocalPlayingNow
import app.discair.ui.theme.LocalPalette
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/*
 * Gallery's Album page (Layout.Gallery). Spec: docs/archive/completed/GALLERY_THEME.md section 10; mockup: docs/design/gallery/pages/album-artist-genre.html, frames 1 and 2.
 * The cover is a 228dp print; under it the catalogue placard (year, songs, length, quality), the title in Fraunces italic and the artist; then Play, Shuffle and Paths
 * (or Get album, Save), tabs Songs / Info / Reviews / Booklet, and a strip of similar albums. The data and the taps are the page every theme has ([CoverStackAlbumData]).
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun GalleryAlbumContent(d: CoverStackAlbumData, open: Opener, list: LazyListState) {
    val p = LocalPalette.current
    val play = LocalPlayActions.current
    val albumId = d.albumId
    val serviceMenu = rememberServiceMenu(d.artist, d.title, d.info?.releaseGroupMbid)
    val menu = buildList {
        if (albumId != null) {
            add("Play next" to { play.queueAlbum(albumId, next = true) })
            add("Add to queue" to { play.queueAlbum(albumId, next = false) })
        }
        if (d.canPickEdition) add("Choose cover" to d.onPickEdition)
        addAll(serviceMenu)
    }
    val tabs = GalleryPagesRules.albumTabs(d.tracks.isNotEmpty(), d.booklet != null)
    var chosen by remember(d.route) { mutableStateOf<String?>(null) }
    val tab = chosen?.let { tabs.indexOf(it) }?.takeIf { it >= 0 }
        ?: GalleryPagesRules.defaultTab(tabs, d.descriptionFinished, d.description?.paragraphs.isNullOrEmpty())
    val missing = d.tracks.count { !it.owned }
    val note = GalleryPagesRules.note(d.owned, missing)
    val metadata = pageMetadata(d.artist, d.title, d.year, d.info?.releaseGroupMbid)
    val gutter = GalleryRules.GUTTER.dp

    LazyColumn(Modifier.fillMaxSize(), state = list, contentPadding = PaddingValues(bottom = 32.dp + app.discair.ui.LocalBottomClearance.current)) {
        item { GalleryPageBar("Album", open.back, action = { GalleryMenuButton("More for ${d.title}", menu) }) }
        item {
            Box(Modifier.fillMaxWidth().galleryArrive(0).padding(top = 20.dp), contentAlignment = Alignment.TopCenter) {
                val print = GalleryPagesRules.ALBUM_PRINT_DP.dp
                val cover = print - (GalleryRules.MAT_LARGE * 2).dp
                GalleryPrint(print, sharedKey = d.route.key) {
                    FlipCover(d.backs, cover) {
                        Box(Modifier.size(cover)) {
                            AlbumCover(d.artist, d.title, d.coverUrl, Modifier.size(cover), rect = true)
                            if (d.canPickEdition) EditionStack(d.editionCount, d.onPickEdition, Modifier.align(Alignment.BottomStart))
                        }
                    }
                }
            }
        }
        item {
            Column(Modifier.fillMaxWidth().galleryArrive(1).padding(start = gutter, end = gutter, top = 22.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                GalleryEyebrow(GalleryPagesRules.albumEyebrow(d.year, d.tracks.size, d.tracks.sumOf { it.durationSeconds ?: 0 }, d.info?.quality))
                Text(d.title, Modifier.padding(top = 4.dp).semantics { heading() }, color = p.text, style = GalleryType.workXL)
                Row(verticalAlignment = Alignment.CenterVertically) {
                    GalleryTextLink(d.artist, Modifier.weight(1f, fill = false)) { open.artist(d.artist, d.info?.artistKey?.ifBlank { null }, d.info?.artistId, null) }
                    val genre = d.genre
                    if (!genre.isNullOrBlank()) {
                        Text(" · ", color = p.text, style = GalleryType.body())
                        Text(
                            genre, color = p.text, style = GalleryType.body(), maxLines = 1, overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.weight(1f, fill = false).clickable(role = Role.Button) { open.genre(genre.lowercase(), genre) },
                        )
                    }
                }
            }
        }
        item {
            FlowRow(
                Modifier.fillMaxWidth().galleryArrive(2).padding(start = gutter, end = gutter, top = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(6.dp), itemVerticalAlignment = Alignment.CenterVertically,
            ) {
                if (albumId != null) {
                    GalleryButton("Play", { play.playAlbum(albumId) }, icon = GalleryIcons.Play)
                    GalleryButton("Shuffle", { play.playAlbum(albumId, shuffle = true) }, kind = GalleryButtonKind.Text, icon = GalleryIcons.Shuffle)
                    // The server builds album paths from an album in the library, by its Navidrome id.
                    if (d.pathsOn) GalleryButton("Paths", d.onPaths, kind = GalleryButtonKind.Text, icon = GalleryIcons.Paths)
                } else {
                    GalleryGetAlbumButton(d.artist, d.title, metadata)
                    GallerySaveButton(d.artist, d.title, metadata)
                }
            }
        }
        if (note != null) item {
            // Every song of an album in the library keeps its own Get; the album-level Get stays until every track is in the library (ACQ-08).
            GalleryNote(note, Modifier.padding(top = 14.dp), trailing = if (d.owned) ({ GalleryGetAlbumButton(d.artist, d.title, metadata, primary = false) }) else null)
        }
        item { GalleryTabs(tabs, tab, { chosen = tabs[it] }, Modifier.galleryArrive(3).padding(top = if (d.owned) 24.dp else 20.dp)) }
        when (tabs[tab]) {
            "Songs" -> {
                for (i in d.tracks.indices) {
                    // The song list rises as one block, after the tabs.
                    if (startsDisc(d.tracks, i)) item(key = "disc-${d.tracks[i].disc}") { GalleryDiscHeading(d.tracks[i].disc ?: 1, Modifier.galleryArrive(4)) }
                    item { Column(Modifier.galleryArrive(4)) { SongRow(d, i, albumId) } }
                }
            }
            "Info" -> item { Column(Modifier.galleryArrive(4)) { InfoTab(d) } }
            "Reviews" -> item { Column(Modifier.galleryArrive(4)) { ReviewsTab(d.artist, d.title) } }
            "Booklet" -> d.booklet?.let { b -> item { Column(Modifier.galleryArrive(4)) { BookletTab(b) } } }
        }
        if (d.similarAlbums.isNotEmpty()) {
            item { Column(Modifier.galleryArrive(5)) { GallerySectionHead("Similar albums") } }
            item {
                LazyRow(Modifier.galleryArrive(5), contentPadding = PaddingValues(horizontal = gutter), horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                    itemsIndexed(d.similarAlbums, key = { i, it -> "$i|${it.key}|${it.name}" }) { _, album ->
                        val said = listOfNotNull(album.name, album.artist.ifBlank { null }, album.year?.toString(), if (album.owned) "in your library" else null).joinToString(", ")
                        GalleryPrint(
                            GalleryPagesRules.SIMILAR_PRINT_DP.dp,
                            Modifier.clickable(role = Role.Button) { open.album(album.key, album.artist, album.name, null, album.year) }.semantics { contentDescription = said },
                            // The page's own print already carries this album's key; a similar album travels into the page it opens.
                            sharedKey = album.key.takeIf { it != d.route.key },
                        ) { AlbumCover(album.artist, album.name, null, Modifier.fillMaxWidth().aspectRatio(1f), rect = true) }
                    }
                }
            }
        }
        if (d.similarArtists.isNotEmpty()) {
            item { GallerySectionHead("Similar artists") }
            item {
                LazyRow(contentPadding = PaddingValues(horizontal = gutter), horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                    itemsIndexed(d.similarArtists, key = { i, it -> "$i|${it.name}" }) { _, a ->
                        GalleryArtistPlate(a.name, null, a.artworkUrl) { open.artist(a.name, a.key, a.id, a.mbid) }
                    }
                }
            }
        }
    }
}

/** Save for an album that is not in the library: the same feedback the picks send, with its states in words. Saved cannot be pressed again. */
@Composable
private fun GallerySaveButton(artist: String, album: String, metadata: kotlinx.serialization.json.JsonObject) {
    val repo = LocalRepository.current
    val scope = rememberCoroutineScope()
    var state by remember(artist, album) { mutableStateOf(SaveState.Idle) }
    GalleryButton(
        when (state) { SaveState.Idle -> "Save"; SaveState.Pending -> "Saving…"; SaveState.Saved -> "Saved"; SaveState.Failed -> "Try again" },
        {
            state = SaveState.Pending
            scope.launch {
                state = try {
                    withContext(Dispatchers.IO) { repo.feedback(FeedbackAction.Save, artist, album, metadata) }
                    SaveState.Saved
                } catch (e: kotlinx.coroutines.CancellationException) { throw e } catch (e: Exception) { SaveState.Failed }
            }
        },
        kind = GalleryButtonKind.Text, icon = GalleryIcons.Bookmark, enabled = state == SaveState.Idle || state == SaveState.Failed,
    )
}

private enum class SaveState { Idle, Pending, Saved, Failed }

/** A song (gallery.css `.trk-list li`): old-style number or the playing bars in a 30dp column, title, length in DM Mono, then the menu or Get; 56dp or more, a hairline under each. */
@Composable
private fun SongRow(d: CoverStackAlbumData, i: Int, albumId: String?) {
    val p = LocalPalette.current
    val play = LocalPlayActions.current
    val t = d.tracks[i]
    val playingNow = LocalPlayingNow.current
    val current = t.owned && playingNow?.matches(albumId, t.title, t.number, t.disc ?: 1) == true
    Column(Modifier.padding(start = GalleryRules.GUTTER.dp, end = 4.dp)) {
        Row(
            Modifier.fillMaxWidth().heightIn(min = GalleryRules.ROW_MIN_TRACKS.dp)
                .let { if (t.owned && albumId != null) it.clickable(onClickLabel = "Play ${t.title}", role = Role.Button) { play.playAlbum(albumId, t.title, t.number, startDisc = t.disc) } else it },
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(Modifier.width(30.dp)) {
                if (current) GalleryPlayingBars(playingNow!!.isPlaying)
                else Text("${trackNumberShown(d.tracks, i)}", color = p.textMuted, style = GalleryType.trackNumber)
            }
            Text(
                t.title, Modifier.weight(1f).padding(end = 8.dp), color = if (current) p.accent else p.text, maxLines = 2, overflow = TextOverflow.Ellipsis,
                style = GalleryType.rowTitle().copy(fontWeight = if (current) FontWeight.Bold else FontWeight.Medium),
            )
            t.durationSeconds?.let { Text(GalleryPagesRules.clock(it), color = p.textMuted, style = GalleryType.time, modifier = Modifier.padding(end = 4.dp)) }
            // Only a song the library lacks has a Get slot; an owned row keeps its menu of ways to play.
            if (!t.owned) Box(Modifier.size(48.dp), contentAlignment = Alignment.Center) { GetSongButton(d.artist, d.title, t.title, t.number, d.year) }
            else if (albumId != null) GalleryMenuButton(
                "More ways to play ${t.title}",
                listOf(
                    GalleryMenuItem("Play next", GalleryIcons.Next) { play.queueTrack(albumId, t.title, t.number, next = true, disc = t.disc) },
                    GalleryMenuItem("Add to queue", GalleryIcons.QueueAdd) { play.queueTrack(albumId, t.title, t.number, next = false, disc = t.disc) },
                    GalleryMenuItem("Download to device", GalleryIcons.Download) { play.downloadTrack(albumId, t.title, t.number, disc = t.disc) },
                ),
                header = GalleryMenuHeader(t.title, GalleryPagesRules.menuLine(d.artist, d.title, t.durationSeconds?.let(GalleryPagesRules::clock))) {
                    AlbumCover(d.artist, d.title, d.coverUrl, Modifier.fillMaxSize(), rect = true)
                },
            ) else Box(Modifier.size(48.dp))
        }
        GalleryRule()
    }
}

/** Info: the description (Apple Music, else Wikipedia) with its source and licence, or the reason there is none. */
@Composable
private fun InfoTab(d: CoverStackAlbumData) {
    val p = LocalPalette.current
    val uri = LocalUriHandler.current
    val paragraphs = d.description?.paragraphs.orEmpty()
    Column(Modifier.padding(start = GalleryRules.GUTTER.dp, end = GalleryRules.GUTTER.dp, top = 14.dp)) {
        if (paragraphs.isEmpty()) {
            GalleryMuted(if (d.descriptionFinished) "No description found for this album." else "Loading description…")
            return@Column
        }
        GalleryReadMore(paragraphs.joinToString("\n\n"))
        val credit = listOfNotNull(d.description?.source ?: "Apple Music", d.description?.license).joinToString(" · ")
        val link = d.description?.url
        Text(
            credit, color = if (link != null) p.control else p.textMuted, style = GalleryType.small(),
            textDecoration = if (link != null) TextDecoration.Underline else null,
            modifier = Modifier.padding(top = 10.dp).then(if (link != null) Modifier.clickable(role = Role.Button) { uri.openUri(link) } else Modifier),
        )
    }
}

/** Reviews: asked from the server on first open; each quote links to its source. Only "Try again" asks the failed outlets again. */
@Composable
private fun ReviewsTab(artist: String, album: String) {
    val p = LocalPalette.current
    val repo = LocalRepository.current
    val uri = LocalUriHandler.current
    val loaded = rememberLoad(artist, album) { repo.albumReviews(artist, album) }
    Column(Modifier.padding(start = GalleryRules.GUTTER.dp, end = GalleryRules.GUTTER.dp, top = 14.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        when (val state = loaded.state) {
            Load.Loading -> GalleryMuted("Loading reviews…")
            is Load.Failed -> {
                GalleryMuted("Reviews could not be loaded.")
                GalleryButton("Try again", loaded.reload, kind = GalleryButtonKind.Outlined, small = true)
            }
            is Load.Ready -> {
                val data = state.value
                data.reviews.forEach { review ->
                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text("“${review.quote}”", color = p.text, style = GalleryType.lyric.copy(fontSize = 17.sp, lineHeight = 25.sp))
                        Text(
                            "Read the full review at ${review.source}", color = p.control, style = GalleryType.small(), textDecoration = TextDecoration.Underline,
                            modifier = Modifier.clickable(role = Role.Button) { uri.openUri(review.url) },
                        )
                    }
                }
                val note = when {
                    data.reviews.isNotEmpty() -> if (data.retryable) "Some sources did not answer." else ""
                    data.retryable -> "No reviews found. Some sources did not answer."
                    else -> "No reviews found for this album."
                }
                if (note.isNotEmpty()) GalleryMuted(note)
                if (data.retryable) GalleryButton("Try again", loaded.reload, kind = GalleryButtonKind.Outlined, small = true)
            }
        }
    }
}
