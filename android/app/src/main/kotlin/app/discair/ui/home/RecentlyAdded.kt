package app.discair.ui.home

import androidx.compose.foundation.clickable
import androidx.compose.foundation.border
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyHorizontalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import app.discair.ui.common.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.data.RECENT_DAYS
import app.discair.data.recentlyAdded
import app.discair.model.LibraryAlbum
import app.discair.ui.Opener
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.CheckBadge
import app.discair.ui.common.Load
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.Target
import app.discair.ui.common.TapeDeckRules
import app.discair.ui.common.TapeMeter
import app.discair.ui.common.rememberReducedMotion
import app.discair.ui.common.aspectSquare
import app.discair.ui.common.plural
import app.discair.ui.common.rememberLoad
import app.discair.ui.common.routeKey
import app.discair.ui.player.LocalPlayActions
import app.discair.ui.theme.brutalShadow

private const val CARD_WIDTH = 156
private const val TEXT_BLOCK = 60
private const val GRID_GAP = 12

/**
 * "Recently added albums": albums that reached the library in the last month, two rows that slide
 * sideways. The arrow opens a sheet with every one of them in a list.
 */
@Composable
fun RecentlyAddedSection(open: Opener) {
    val repo = LocalRepository.current
    val loaded = rememberLoad("recently_added") { repo.recentlyAdded() }
    var sheet by remember { mutableStateOf(false) }
    Row(
        Modifier.fillMaxWidth().padding(start = 16.dp, end = 4.dp, top = 24.dp, bottom = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            "Recently added albums", style = MaterialTheme.typography.headlineMedium,
            modifier = Modifier.weight(1f).semantics { heading() },
        )
        IconButton(onClick = { sheet = true }, Modifier.size(Target)) {
            Icon(
                app.discair.ui.player.PlayerIcons.Right,
                contentDescription = "See all recently added albums", tint = MaterialTheme.colorScheme.primary,
            )
        }
    }
    when (val state = loaded.state) {
        Load.Loading -> Muted("Loading…")
        is Load.Failed -> Inline(state.failure.message, loaded.reload)
        is Load.Ready -> {
            if (state.value.isEmpty()) Muted("Nothing was added in the last $RECENT_DAYS days.")
            else if (app.discair.ui.theme.currentLayout() == app.discair.ui.theme.Layout.TapeDeck) TapeRecentList(state.value.take(TapeDeckRules.HOME_ROWS), open)
            else if (app.discair.ui.theme.currentLayout() == app.discair.ui.theme.Layout.StickerWall) StickerRecentWall(state.value.take(app.discair.ui.common.StickerWallRules.WALL_TILES), open)
            else LazyHorizontalGrid(
                rows = GridCells.Fixed(2),
                modifier = Modifier.fillMaxWidth().height((2 * (CARD_WIDTH + TEXT_BLOCK) + GRID_GAP).dp),
                contentPadding = PaddingValues(horizontal = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(GRID_GAP.dp),
                verticalArrangement = Arrangement.spacedBy(GRID_GAP.dp),
            ) {
                items(state.value, key = { it.id.ifBlank { it.key } }) { album -> RecentCard(album, open) }
            }
            if (sheet) RecentlyAddedSheet(state.value, open) { sheet = false }
        }
    }
    if (sheet && loaded.state !is Load.Ready) sheet = false
}

@Composable
private fun RecentCard(album: LibraryAlbum, open: Opener) {
    val play = LocalPlayActions.current
    Column(
        Modifier.width(CARD_WIDTH.dp).clip(RoundedCornerShape(12.dp))
            .clickable(role = Role.Button) { open.album(album.key, album.artist, album.name, album.id, album.year) },
    ) {
        Box {
            AlbumCover(album.artist, album.name, album.artworkUrl, Modifier.fillMaxWidth().aspectSquare(), rect = true)
            CheckBadge(
                Modifier.align(Alignment.BottomEnd).padding(8.dp),
                onPlay = album.id.takeIf { it.isNotBlank() }?.let { id -> { play.playAlbum(id) } },
                label = album.name,
            )
        }
        Column(Modifier.height(TEXT_BLOCK.dp).padding(horizontal = 4.dp, vertical = 8.dp)) {
            Text(album.name, style = MaterialTheme.typography.bodyLarge, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text(
                album.artist, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1, overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

/** Every album added in the last month, newest first. Tapping a row opens the album. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun RecentlyAddedSheet(albums: List<LibraryAlbum>, open: Opener, onDismiss: () -> Unit) {
    val play = LocalPlayActions.current
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
        app.discair.ui.common.TransparentNavigationBar()
        Column(Modifier.navigationBarsPadding()) {
            Text(
                "Recently added albums", style = MaterialTheme.typography.headlineMedium,
                modifier = Modifier.padding(horizontal = 16.dp).semantics { heading() },
            )
            Text(
                "Last $RECENT_DAYS days · " + plural(albums.size, "album"),
                style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 2.dp, bottom = 8.dp),
            )
            LazyColumn(Modifier.fillMaxWidth()) {
                items(albums, key = { it.id.ifBlank { it.key } }) { album ->
                    Row(
                        Modifier.fillMaxWidth().heightIn(min = 72.dp)
                            .clickable(role = Role.Button) {
                                onDismiss()
                                open.album(album.key, album.artist, album.name, album.id, album.year)
                            }
                            .padding(horizontal = 16.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        AlbumCover(album.artist, album.name, album.artworkUrl, Modifier.size(56.dp))
                        Column(Modifier.weight(1f).padding(horizontal = 12.dp)) {
                            Text(album.name, style = MaterialTheme.typography.bodyLarge, maxLines = 1, overflow = TextOverflow.Ellipsis)
                            Text(
                                listOfNotNull(album.artist.ifBlank { null }, album.year?.toString()).joinToString(" · "),
                                style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
                                maxLines = 1, overflow = TextOverflow.Ellipsis,
                            )
                        }
                        CheckBadge(
                            onPlay = album.id.takeIf { it.isNotBlank() }?.let { id -> { play.playAlbum(id) } },
                            label = album.name,
                        )
                    }
                }
            }
        }
    }
}

/**
 * Cassette Deck: the newest albums as one ruled list in a hard-shadowed frame (number, cover, title and artist, year). The row of
 * the album that is playing shows the live meter in place of its number, and is announced as playing or paused. Not lazy, so it
 * stops at [TapeDeckRules.HOME_ROWS]; the arrow above opens the full list.
 */
@Composable
private fun TapeRecentList(albums: List<LibraryAlbum>, open: Opener) {
    val p = app.discair.ui.theme.LocalPalette.current
    val play = LocalPlayActions.current
    val now = app.discair.ui.player.LocalPlayingNow.current
    val reduced = rememberReducedMotion()
    val rule = (p.shape?.outline ?: 2).dp
    val mono = app.discair.ui.theme.LocalFontPair.current.mono
    Column(
        Modifier.padding(start = 16.dp, end = 21.dp, top = 8.dp, bottom = 6.dp).fillMaxWidth()
            .brutalShadow(androidx.compose.ui.graphics.RectangleShape)
            .background(p.surface).border(rule, p.edgeStrong),
    ) {
        albums.forEachIndexed { index, album ->
            val playing = now != null && album.id.isNotBlank() && now.albumId == album.id
            Row(
                Modifier.fillMaxWidth().heightIn(min = 64.dp)
                    .background(if (playing) p.accentDim else p.surface)
                    .clickable(role = Role.Button) { open.album(album.key, album.artist, album.name, album.id, album.year) }
                    .semantics(mergeDescendants = true) {
                        if (playing && now != null) stateDescription = if (now.isPlaying) "Playing" else "Paused"
                    }
                    .padding(horizontal = 8.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Box(Modifier.width(32.dp), contentAlignment = Alignment.Center) {
                    if (playing && now != null) TapeMeter(3, TapeDeckRules.meterMoves(now.isPlaying, false, reduced), p.text, size = 16.dp)
                    else Text("%02d".format(index + 1), style = MaterialTheme.typography.labelMedium.copy(fontFamily = mono), color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                AlbumCover(album.artist, album.name, album.artworkUrl, Modifier.size(48.dp).border(rule, p.edgeStrong), rect = true)
                Column(Modifier.weight(1f).padding(horizontal = 12.dp)) {
                    Text(album.name, style = MaterialTheme.typography.bodyLarge, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text(
                        album.artist, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1, overflow = TextOverflow.Ellipsis,
                    )
                }
                album.year?.let { Text(it.toString(), style = MaterialTheme.typography.labelMedium.copy(fontFamily = mono), modifier = Modifier.padding(end = 4.dp)) }
                CheckBadge(
                    onPlay = album.id.takeIf { it.isNotBlank() }?.let { id -> { play.playAlbum(id) } },
                    label = album.name,
                )
            }
            if (index < albums.lastIndex) Box(Modifier.fillMaxWidth().height(rule).background(p.edgeStrong))
        }
    }
}
