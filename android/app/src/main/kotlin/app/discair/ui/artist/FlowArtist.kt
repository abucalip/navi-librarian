package app.discair.ui.artist

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
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
import android.app.Activity
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import app.discair.model.MissingAlbum
import app.discair.model.TopSong
import app.discair.ui.Opener
import app.discair.ui.common.ArtistPhoto
import app.discair.ui.common.FlowArtistChip
import app.discair.ui.common.FlowCover
import app.discair.ui.common.FlowDivider
import app.discair.ui.common.FlowHeading
import app.discair.ui.common.FlowPageBar
import app.discair.ui.common.FlowPagesRules
import app.discair.ui.common.GetAlbumButton
import app.discair.ui.common.GetSongButton
import app.discair.ui.common.ReadMore
import app.discair.ui.common.Target
import app.discair.ui.common.describedAs
import app.discair.ui.common.pageMetadata
import app.discair.ui.common.plural
import app.discair.ui.player.LocalPlayActions
import app.discair.ui.player.RowMoreMenu
import app.discair.ui.player.PlayerIcons
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.accentText

private const val SONGS_SHOWN = 5
private const val MISSING_SHOWN = 10

/**
 * Flow's Artist page (mockup flow/album-artist-genre, frame 2): the photo runs full width behind the status bar with the name, the album count
 * and a round Play button over a dark fade at its foot, Top songs as plain rows, then strips of the albums in the library, the missing albums
 * (with Get) and similar artists. Paths sits beside Play, as on the Soft Brut page; Shuffle, Play next and Add to queue are in the three-dot menu.
 * The data is [CoverStackArtistData], the same the Soft Brut page takes.
 */
@Composable
internal fun FlowArtistContent(d: CoverStackArtistData, open: Opener, list: LazyListState, showAllSongs: Boolean, onAllSongs: () -> Unit, showAllMissing: Boolean, onAllMissing: () -> Unit) {
    val p = LocalPalette.current
    val play = LocalPlayActions.current
    val artistId = d.artistId
    val menu = buildList {
        if (artistId != null) {
            add("Shuffle" to { play.playArtist(artistId, shuffle = true) })
            add("Play next" to { play.queueArtist(artistId, next = true) })
            add("Add to queue" to { play.queueArtist(artistId, next = false) })
        }
    }
    val owned = d.owned
    LightStatusBarIcons()
    LazyColumn(Modifier.fillMaxSize(), state = list, contentPadding = PaddingValues(bottom = 32.dp + app.discair.ui.LocalBottomClearance.current)) {
        item {
            BoxWithConstraints(Modifier.fillMaxWidth()) {
                Box(Modifier.fillMaxWidth().height(maxWidth * FlowPagesRules.ARTIST_PHOTO_RATIO)) {
                    ArtistPhoto(d.name, owned.firstOrNull()?.artworkUrl, Modifier.fillMaxSize())
                    // The fade at the foot (flow.css `.ahero .ov`): 78% black at the bottom, clear 60dp above the text.
                    Row(
                        Modifier.align(Alignment.BottomStart).fillMaxWidth()
                            .background(Brush.verticalGradient(listOf(Color.Transparent, Color.Black.copy(alpha = 0.78f))))
                            .padding(start = 16.dp, end = 16.dp, top = 60.dp, bottom = 14.dp),
                        horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.Bottom,
                    ) {
                        Column(Modifier.weight(1f)) {
                            Text(
                                d.name, color = Color.White, maxLines = 2, overflow = TextOverflow.Ellipsis,
                                style = MaterialTheme.typography.headlineMedium.copy(fontSize = 24.sp, lineHeight = 28.sp, fontWeight = FontWeight.Bold, letterSpacing = (-0.02).em),
                                modifier = Modifier.semantics { heading() },
                            )
                            Text(
                                if (d.inLibrary) plural(d.ownedAlbumCount ?: 0, "album") + " in your library" else "Not in your library",
                                color = Color.White.copy(alpha = 0.8f), style = MaterialTheme.typography.bodySmall,
                            )
                        }
                        // Paths beside Play, with Soft Brut's icon: a 44dp disc, a white glyph on 28% black as the bar's buttons are over the photo.
                        if (d.canPaths) Box(
                            Modifier.size(Target).clip(CircleShape).clickable(role = Role.Button, onClick = d.onPaths)
                                .semantics { contentDescription = "Paths from ${d.name}" },
                            contentAlignment = Alignment.Center,
                        ) {
                            Box(Modifier.size(44.dp).background(Color.Black.copy(alpha = 0.28f), CircleShape), contentAlignment = Alignment.Center) {
                                Icon(PlayerIcons.Paths, contentDescription = null, tint = Color.White, modifier = Modifier.size(20.dp))
                            }
                        }
                        if (artistId != null) Box(
                            Modifier.size(Target).clip(CircleShape).clickable(role = Role.Button) { play.playArtist(artistId, shuffle = false) }
                                .semantics { contentDescription = "Play ${d.name}" },
                            contentAlignment = Alignment.Center,
                        ) {
                            Box(Modifier.size(44.dp).background(p.accent, CircleShape), contentAlignment = Alignment.Center) {
                                Icon(PlayerIcons.Play, contentDescription = null, tint = p.onAccent, modifier = Modifier.size(20.dp))
                            }
                        }
                    }
                    FlowPageBar(open.back, menu, Modifier.align(Alignment.TopStart), over = true)
                }
            }
        }
        val genres = d.sections.tags.items.map { it.name }.ifEmpty { listOfNotNull(d.sections.artist.artist?.genre) }.take(3)
        if (genres.isNotEmpty()) item {
            Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                genres.forEach { g ->
                    Box(
                        Modifier.weight(1f, fill = false).heightIn(min = Target).clickable(role = Role.Button) { open.genre(g.lowercase(), g) },
                        contentAlignment = Alignment.CenterStart,
                    ) { Text(g, color = p.accentText, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Medium)) }
                }
            }
        }
        val allSongs = d.sections.topSongs.items
        if (allSongs.isNotEmpty()) {
            item {
                FlowHeading(
                    "Top songs", Modifier.padding(top = 12.dp, bottom = 4.dp),
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
            item { FlowHeading("In your library", Modifier.padding(top = 20.dp, bottom = 10.dp)) }
            item {
                LazyRow(contentPadding = PaddingValues(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    items(owned, key = { it.key + it.id }) { album ->
                        FlowCover(
                            d.name, album.name, album.artworkUrl,
                            Modifier.width(FlowPagesRules.LIBRARY_COVER.dp).clip(RoundedCornerShape(8.dp))
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
                FlowHeading(
                    "Missing albums", Modifier.padding(top = 20.dp, bottom = 10.dp),
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
            item { FlowHeading("Similar artists", Modifier.padding(top = 20.dp, bottom = 10.dp)) }
            item {
                LazyRow(contentPadding = PaddingValues(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    items(d.similar, key = { it.name }) { a -> FlowArtistChip(a.name, a.artworkUrl, { open.artist(a.name, a.key, a.id, a.mbid) }) }
                }
            }
        }
    }
}

/** A top song (flow.css `.li`): cover 48 at radius 8, title 600 15, album muted, then Get or the menu of ways to play; a hairline between rows. */
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
            FlowCover(d.name, onAlbum ?: song.name, ownedAlbum?.artworkUrl, Modifier.size(48.dp))
            Column(Modifier.weight(1f)) {
                Text(song.name, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold, fontSize = 15.sp, lineHeight = 20.sp))
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
        if (divider) FlowDivider(Modifier.padding(horizontal = 16.dp))
    }
}

/** A missing album (flow.css `.cap`): cover 104, name 600 14 on one line, and its small Get button. */
@Composable
private fun MissingCard(artist: String, album: MissingAlbum, open: Opener) {
    val p = LocalPalette.current
    Column(Modifier.width(FlowPagesRules.LIBRARY_COVER.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Column(
            Modifier.clip(RoundedCornerShape(8.dp)).clickable(role = Role.Button) { open.album(album.key, artist, album.name, null, album.year) },
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            FlowCover(artist, album.name, null, Modifier.fillMaxWidth())
            Text(album.name, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold, fontSize = 14.sp))
        }
        GetAlbumButton(artist, album.name, pageMetadata(artist, album.name, album.year))
    }
}

/**
 * The status bar's icons are white while this page is showing, because the photo runs behind them, and go back to what the theme set when the
 * page leaves. (The app draws edge to edge; on a light theme the icons are dark, which would vanish on a dark photo.)
 */
@Composable
private fun LightStatusBarIcons() {
    val view = LocalView.current
    if (view.isInEditMode) return
    DisposableEffect(view) {
        val window = (view.context as? Activity)?.window
        val controller = window?.let { WindowCompat.getInsetsController(it, view) }
        // Two artist pages can overlap while one replaces the other, so the theme's own setting is kept from the first and put back by the last.
        if (controller != null) {
            if (StatusBarOwners.count == 0) StatusBarOwners.theme = controller.isAppearanceLightStatusBars
            StatusBarOwners.count++
            controller.isAppearanceLightStatusBars = false
        }
        onDispose {
            if (controller != null) {
                StatusBarOwners.count--
                if (StatusBarOwners.count == 0) controller.isAppearanceLightStatusBars = StatusBarOwners.theme
            }
        }
    }
}

private object StatusBarOwners {
    var count = 0
    var theme = false
}
