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
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.model.FeedbackAction
import app.discair.ui.Opener
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.ArtistPhoto
import app.discair.ui.common.GalleryPagesRules
import app.discair.ui.common.GetSongButton
import app.discair.ui.common.IndexButton
import app.discair.ui.common.IndexButtonKind
import app.discair.ui.common.IndexDataList
import app.discair.ui.common.IndexDiscHeading
import app.discair.ui.common.IndexGetButton
import app.discair.ui.common.IndexIconButton
import app.discair.ui.common.IndexIcons
import app.discair.ui.common.IndexKeyValueGrid
import app.discair.ui.common.IndexLabel
import app.discair.ui.common.IndexMuted
import app.discair.ui.common.IndexPageBar
import app.discair.ui.common.IndexPagesRules
import app.discair.ui.common.IndexPlayingBars
import app.discair.ui.common.IndexRule
import app.discair.ui.common.IndexRules
import app.discair.ui.common.IndexSectionHead
import app.discair.ui.common.IndexTabs
import app.discair.ui.common.IndexType
import app.discair.ui.common.Load
import app.discair.ui.common.LocalAcquisitions
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.indexArrive
import app.discair.ui.common.indexGetOf
import app.discair.ui.common.pageMetadata
import app.discair.ui.common.rememberLoad
import app.discair.ui.common.sharedCover
import app.discair.ui.player.LocalPlayActions
import app.discair.ui.player.LocalPlayingNow
import app.discair.ui.theme.LocalPalette
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private val Gutter = IndexRules.GUTTER.dp

/*
 * Index's Album page (Layout.Index). Spec: docs/INDEX_THEME.md step I3; mockup: docs/design/index/pages/album-artist-genre.html, frames 1 and 2.
 * In the library: the catalogue bar ("ALBUM 0418 / 1284"), a 200dp cover beside the playing song's numeral ("05 / 10 PLAYING") and the data list, the title,
 * Play / Shuffle / Paths, tabs Songs · Info · Reviews · Booklet and numbered songs. Not in the library: "NOT IN YOUR LIBRARY", a 150dp cover beside the title,
 * the key/value grid, Get album / Save. Similar albums and artists follow both. The data and the taps are the page every theme has ([CoverStackAlbumData]).
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun IndexAlbumContent(d: CoverStackAlbumData, open: Opener, list: LazyListState) {
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
    val metadata = pageMetadata(d.artist, d.title, d.year, d.info?.releaseGroupMbid)
    val openArtist = { open.artist(d.artist, d.info?.artistKey?.ifBlank { null }, d.info?.artistId, null) }
    val genre = d.genre?.takeIf { it.isNotBlank() }
    val openGenre = genre?.let { g -> { open.genre(g.lowercase(), g) } }
    val catalogue = IndexPagesRules.albumCatalogue(d.owned, d.info?.libraryPosition, d.info?.libraryTotal)
    var allSimilar by remember(d.route) { mutableStateOf(false) }

    LazyColumn(Modifier.fillMaxSize(), state = list, contentPadding = PaddingValues(bottom = 32.dp + app.discair.ui.LocalBottomClearance.current)) {
        item { IndexPageBar(catalogue, open.back, action = { if (menu.isNotEmpty()) MoreMenu("More for ${d.title}", menu) }) }
        if (d.owned) {
            item { OwnedHead(d, albumId, openArtist, openGenre) }
            item {
                Text(
                    d.title, Modifier.fillMaxWidth().indexArrive(1).padding(start = Gutter, end = Gutter, top = 14.dp).semantics { heading() },
                    style = IndexType.pageTitle(), color = LocalPalette.current.text, maxLines = 4, overflow = TextOverflow.Ellipsis,
                )
            }
        } else {
            item { MissingHead(d) }
            item {
                IndexKeyValueGrid(
                    IndexPagesRules.missingAlbumGrid(d.artist, d.year, genre, d.tracks.size).map {
                        when (it.key) { "Artist" -> it.copy(onClick = openArtist); "Genre" -> it.copy(onClick = openGenre); else -> it }
                    },
                    Modifier.indexArrive(1).padding(start = Gutter, end = Gutter, top = 14.dp),
                )
            }
        }
        item {
            FlowRow(
                Modifier.fillMaxWidth().indexArrive(2).padding(start = Gutter, end = Gutter, top = 14.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(6.dp), itemVerticalAlignment = Alignment.CenterVertically,
            ) {
                val hub = LocalAcquisitions.current
                if (albumId != null) {
                    IndexButton("Play", { play.playAlbum(albumId) }, icon = IndexIcons.Play)
                    IndexButton("Shuffle", { play.playAlbum(albumId, shuffle = true) }, kind = IndexButtonKind.Ghost, icon = IndexIcons.Shuffle)
                    // The server builds album paths from an album in the library, by its Navidrome id.
                    if (d.pathsOn) IndexButton("Paths", d.onPaths, kind = IndexButtonKind.Ghost, icon = IndexIcons.Paths)
                }
                // The album-level Get stays until every track is in the library (ACQ-08).
                if (!d.owned || d.tracks.any { !it.owned }) {
                    IndexGetButton(
                        indexGetOf(hub.getState(d.artist, d.title)), { hub.getAlbum(d.artist, d.title, metadata) },
                        idleLabel = "Get album", small = d.owned,
                    )
                }
                if (!d.owned) SaveButton(d.artist, d.title, metadata)
            }
        }
        item { IndexTabs(tabs, tab, { chosen = tabs[it] }, Modifier.indexArrive(3).padding(top = 14.dp)) }
        when (tabs[tab]) {
            "Songs" -> {
                for (i in d.tracks.indices) {
                    if (startsDisc(d.tracks, i)) item(key = "disc-${d.tracks[i].disc}") { IndexDiscHeading(d.tracks[i].disc ?: 1, Modifier.indexArrive(4 + i, tab)) }
                    item { Column(Modifier.indexArrive(4 + i, tab)) { SongRow(d, i, albumId) } }
                }
            }
            "Info" -> item { Column(Modifier.indexArrive(4, tab)) { InfoTab(d) } }
            "Reviews" -> item { Column(Modifier.indexArrive(4, tab)) { ReviewsTab(d.artist, d.title) } }
            "Booklet" -> d.booklet?.let { b -> item { Column(Modifier.indexArrive(4, tab)) { BookletTab(b) } } }
        }
        if (d.similarAlbums.isNotEmpty()) {
            val more = d.similarAlbums.size > IndexPagesRules.COLUMNS && !allSimilar
            item { IndexSectionHead("Similar", meta = d.similarAlbums.size.toString(), link = if (more) "All" else null, onLink = { allSimilar = true }) }
            val shown = if (allSimilar) d.similarAlbums else d.similarAlbums.take(IndexPagesRules.COLUMNS)
            shown.chunked(IndexPagesRules.COLUMNS).forEach { row ->
                item {
                    Row(Modifier.fillMaxWidth().padding(start = Gutter, end = Gutter, top = 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        row.forEach { album ->
                            val said = listOfNotNull(album.name, album.artist.ifBlank { null }, album.year?.toString(), if (album.owned) "in your library" else null).joinToString(", ")
                            Box(Modifier.weight(1f).clickable(role = Role.Button) { open.album(album.key, album.artist, album.name, null, album.year) }.semantics { contentDescription = said }) {
                                // The page's own cover already carries this album's key; a similar album travels into the page it opens.
                                AlbumCover(
                                    album.artist, album.name, null,
                                    Modifier.fillMaxWidth().aspectRatio(1f).then(if (album.key != d.route.key) Modifier.sharedCover(album.key) else Modifier), rect = true,
                                )
                            }
                        }
                        repeat(IndexPagesRules.COLUMNS - row.size) { Box(Modifier.weight(1f)) }
                    }
                }
            }
        }
        if (d.similarArtists.isNotEmpty()) {
            item { IndexSectionHead("Similar artists", meta = d.similarArtists.size.toString()) }
            item {
                Row(Modifier.fillMaxWidth().padding(start = Gutter, end = Gutter, top = 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    d.similarArtists.take(IndexPagesRules.COLUMNS).forEach { a ->
                        Column(
                            Modifier.weight(1f).clickable(role = Role.Button) { open.artist(a.name, a.key, a.id, a.mbid) }.semantics(mergeDescendants = true) {},
                            verticalArrangement = Arrangement.spacedBy(5.dp),
                        ) {
                            ArtistPhoto(a.name, a.artworkUrl, Modifier.fillMaxWidth().aspectRatio(74f / 92f), rect = true)
                            Text(a.name, style = IndexType.dataValue().copy(fontWeight = FontWeight.SemiBold), color = LocalPalette.current.text, maxLines = 2, overflow = TextOverflow.Ellipsis)
                            IndexLabel(if (a.owned) "In library" else "Not in library", color = if (a.owned) LocalPalette.current.ok else LocalPalette.current.textMuted)
                        }
                    }
                    repeat(IndexPagesRules.COLUMNS - d.similarArtists.take(IndexPagesRules.COLUMNS).size) { Box(Modifier.weight(1f)) }
                }
            }
        }
    }
}

/** The owned album's head: the 200dp cover (it flips to the back when the index has one; the edition stack picks a cover), and beside it the numeral and the data list. */
@Composable
private fun OwnedHead(d: CoverStackAlbumData, albumId: String?, openArtist: () -> Unit, openGenre: (() -> Unit)?) {
    val p = LocalPalette.current
    val playingNow = LocalPlayingNow.current
    val playing = d.tracks.indices.firstOrNull { i -> val t = d.tracks[i]; t.owned && playingNow?.matches(albumId, t.title, t.number, t.disc ?: 1) == true }
    val numeral = IndexPagesRules.albumNumeral(playing, d.tracks.size)
    val cover = IndexPagesRules.ALBUM_COVER_DP.dp
    Row(Modifier.fillMaxWidth().indexArrive(0).padding(start = Gutter, end = Gutter, top = 4.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Box(Modifier.size(cover)) {
            FlipCover(d.backs, cover) {
                Box(Modifier.size(cover)) {
                    AlbumCover(d.artist, d.title, d.coverUrl, Modifier.size(cover).sharedCover(d.route.key), rect = true)
                    if (d.canPickEdition) EditionStack(d.editionCount, d.onPickEdition, Modifier.align(Alignment.BottomStart))
                }
            }
        }
        Column(Modifier.weight(1f).heightIn(min = cover), verticalArrangement = Arrangement.SpaceBetween) {
            if (numeral != null) Column(Modifier.semantics(mergeDescendants = true) {}) {
                Row(verticalAlignment = Alignment.Bottom) {
                    Text(numeral.big, style = IndexType.index(), color = if (numeral.accent) p.accent else p.text, maxLines = 1)
                    if (numeral.small != null) IndexLabel(numeral.small, Modifier.padding(start = 4.dp, bottom = 4.dp))
                }
                IndexLabel(numeral.word, Modifier.padding(top = 2.dp), color = if (numeral.accent) p.accent else p.textMuted)
            } else Box(Modifier)
            IndexDataList(
                IndexPagesRules.albumRows(d.artist, d.year, d.tracks.sumOf { it.durationSeconds ?: 0 }, d.info?.quality, d.genre).map {
                    when (it.key) { "Artist" -> it.copy(onClick = openArtist); "Genre" -> it.copy(onClick = openGenre); else -> it }
                },
            )
        }
    }
}

/** The head of an album the library lacks: a 150dp cover with the title beside it, at the foot of the column. */
@Composable
private fun MissingHead(d: CoverStackAlbumData) {
    val cover = IndexPagesRules.MISSING_COVER_DP.dp
    Row(Modifier.fillMaxWidth().indexArrive(0).padding(start = Gutter, end = Gutter, top = 4.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.Bottom) {
        Box(Modifier.size(cover)) {
            FlipCover(d.backs, cover) { AlbumCover(d.artist, d.title, d.coverUrl, Modifier.size(cover).sharedCover(d.route.key), rect = true) }
        }
        Text(
            d.title, Modifier.weight(1f).semantics { heading() }, style = IndexType.leadTitle().copy(fontSize = 32.sp, lineHeight = 30.sp),
            color = LocalPalette.current.text, maxLines = 5, overflow = TextOverflow.Ellipsis,
        )
    }
}

/** The three dots with the lettered sheet of what else the page or row can do, under an optional [header] (the song menu's cover and "SONG 05 / 10"). */
@Composable
internal fun MoreMenu(label: String, items: List<Pair<String, () -> Unit>>, header: app.discair.ui.common.IndexMenuHeader? = null) {
    app.discair.ui.common.IndexMenuButton(label, app.discair.ui.common.indexMenuItems(items), header = header)
}

/** Save for an album that is not in the library: the same feedback the picks send, with its states in words. Saved cannot be pressed again. */
@Composable
private fun SaveButton(artist: String, album: String, metadata: kotlinx.serialization.json.JsonObject) {
    val repo = LocalRepository.current
    val scope = rememberCoroutineScope()
    var state by remember(artist, album) { mutableStateOf(IndexSave.Idle) }
    IndexButton(
        when (state) { IndexSave.Idle -> "Save"; IndexSave.Pending -> "Saving…"; IndexSave.Saved -> "Saved"; IndexSave.Failed -> "Try again" },
        {
            state = IndexSave.Pending
            scope.launch {
                state = try {
                    withContext(Dispatchers.IO) { repo.feedback(FeedbackAction.Save, artist, album, metadata) }
                    IndexSave.Saved
                } catch (e: kotlinx.coroutines.CancellationException) { throw e } catch (e: Exception) { IndexSave.Failed }
            }
        },
        kind = IndexButtonKind.Ghost, icon = IndexIcons.Bookmark, enabled = state == IndexSave.Idle || state == IndexSave.Failed,
    )
}

private enum class IndexSave { Idle, Pending, Saved, Failed }

/** A song (section 7, track row): 40dp big pale number (playing: the bars, and the title in `accent` 700), the title, the mono time, then Get or the three dots. Min 54dp. */
@Composable
private fun SongRow(d: CoverStackAlbumData, i: Int, albumId: String?) {
    val p = LocalPalette.current
    val play = LocalPlayActions.current
    val t = d.tracks[i]
    val playingNow = LocalPlayingNow.current
    val current = t.owned && playingNow?.matches(albumId, t.title, t.number, t.disc ?: 1) == true
    Column(Modifier.padding(start = Gutter, end = 6.dp)) {
        Row(
            Modifier.fillMaxWidth().heightIn(min = IndexRules.ROW_MIN_TRACKS.dp)
                .let { if (t.owned && albumId != null) it.clickable(onClickLabel = "Play ${t.title}", role = Role.Button) { play.playAlbum(albumId, t.title, t.number, startDisc = t.disc) } else it },
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(Modifier.width(40.dp)) {
                if (current) IndexPlayingBars(playingNow!!.isPlaying)
                else Text("%02d".format(trackNumberShown(d.tracks, i)), style = IndexType.trackNumber(), color = p.edge, maxLines = 1)
            }
            Text(
                t.title, Modifier.weight(1f).padding(end = 8.dp), color = if (current) p.accent else p.text, maxLines = 2, overflow = TextOverflow.Ellipsis,
                style = IndexType.rowTitle().copy(fontWeight = if (current) FontWeight.Bold else FontWeight.Medium),
            )
            t.durationSeconds?.let { IndexLabel(IndexPagesRules.clock(it), Modifier.padding(end = 4.dp)) }
            // Only a song the library lacks has a Get slot; an owned row keeps its menu of ways to play.
            if (!t.owned) Box(Modifier.size(48.dp), contentAlignment = Alignment.Center) { GetSongButton(d.artist, d.title, t.title, t.number, d.year) }
            else if (albumId != null) MoreMenu(
                "More ways to play ${t.title}",
                listOf(
                    "Play next" to { play.queueTrack(albumId, t.title, t.number, next = true, disc = t.disc) },
                    "Add to queue" to { play.queueTrack(albumId, t.title, t.number, next = false, disc = t.disc) },
                    "Download to device" to { play.downloadTrack(albumId, t.title, t.number, disc = t.disc) },
                ),
                // The song menu's header (mockup sheets, frame 2): the album cover, "SONG 05 / 10 · ARTIST" and the song.
                header = app.discair.ui.common.IndexMenuHeader(t.title, app.discair.ui.common.IndexSheetRules.eyebrow("Song", i + 1, d.tracks.size, d.artist)) {
                    app.discair.ui.common.AlbumCover(d.artist, d.title, d.coverUrl, Modifier.size(app.discair.ui.common.IndexSheetRules.HEADER_ART.dp), rect = true)
                },
            ) else Box(Modifier.size(48.dp))
        }
        IndexRule()
    }
}

/** Info: the description (Apple Music, else Wikipedia) with its source and licence as a mono link, or the reason there is none. Long text folds behind MORE. */
@Composable
private fun InfoTab(d: CoverStackAlbumData) {
    val p = LocalPalette.current
    val uri = LocalUriHandler.current
    val paragraphs = d.description?.paragraphs.orEmpty()
    var all by remember(d.route) { mutableStateOf(false) }
    Column(Modifier.padding(start = Gutter, end = Gutter, top = 14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        if (paragraphs.isEmpty()) {
            IndexMuted(if (d.descriptionFinished) "No description found for this album." else "Loading description…")
            return@Column
        }
        Text(paragraphs.joinToString("\n\n"), style = IndexType.body(), color = p.text, maxLines = if (all) Int.MAX_VALUE else 8, overflow = TextOverflow.Ellipsis)
        if (!all) Text("MORE →", style = IndexType.label(), color = p.accent, modifier = Modifier.heightIn(min = 24.dp).clickable(role = Role.Button, onClickLabel = "Read the whole description") { all = true })
        val credit = listOfNotNull(d.description?.source ?: "Apple Music", d.description?.license).joinToString(" · ")
        val link = d.description?.url
        IndexLabel(credit, if (link != null) Modifier.heightIn(min = 24.dp).clickable(role = Role.Button) { uri.openUri(link) } else Modifier, color = if (link != null) p.accent else p.textMuted)
    }
}

/** Reviews: asked from the server on first open; each quote links to its source. Only "Try again" asks the failed outlets again. */
@Composable
private fun ReviewsTab(artist: String, album: String) {
    val p = LocalPalette.current
    val repo = LocalRepository.current
    val uri = LocalUriHandler.current
    val loaded = rememberLoad(artist, album) { repo.albumReviews(artist, album) }
    Column(Modifier.padding(start = Gutter, end = Gutter, top = 14.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        when (val state = loaded.state) {
            Load.Loading -> IndexMuted("Loading reviews…")
            is Load.Failed -> {
                IndexMuted("Reviews could not be loaded.")
                IndexButton("Try again", loaded.reload, kind = IndexButtonKind.Ghost, small = true)
            }
            is Load.Ready -> {
                val data = state.value
                data.reviews.forEachIndexed { i, review ->
                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        IndexLabel("${IndexPagesRules.letter(i)} · ${review.source}", color = p.accent)
                        Text("“${review.quote}”", style = IndexType.body().copy(fontSize = 15.sp, lineHeight = 22.sp), color = p.text)
                        Text(
                            "READ THE FULL REVIEW →", style = IndexType.label(), color = p.accent,
                            modifier = Modifier.heightIn(min = 24.dp).clickable(role = Role.Button, onClickLabel = "Read the full review at ${review.source}") { uri.openUri(review.url) },
                        )
                    }
                }
                val note = when {
                    data.reviews.isNotEmpty() -> if (data.retryable) "Some sources did not answer." else ""
                    data.retryable -> "No reviews found. Some sources did not answer."
                    else -> "No reviews found for this album."
                }
                if (note.isNotEmpty()) IndexMuted(note)
                if (data.retryable) IndexButton("Try again", loaded.reload, kind = IndexButtonKind.Ghost, small = true)
            }
        }
    }
}
