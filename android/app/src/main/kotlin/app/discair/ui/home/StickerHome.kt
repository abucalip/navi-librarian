package app.discair.ui.home

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import app.discair.data.RECENT_DAYS
import app.discair.model.LibraryAlbum
import app.discair.model.Pick
import app.discair.ui.Opener
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.GetAlbumButton
import app.discair.ui.common.Sticker
import app.discair.ui.common.StickerTile
import app.discair.ui.common.StickerWall
import app.discair.ui.common.aspectSquare
import app.discair.ui.common.pageMetadata
import app.discair.ui.common.routeKey
import app.discair.ui.theme.LocalPalette

/** Sticker Wall: the picks as a wall of tilted tiles. A pick is an album the library lacks, so every sticker says Missing, with Get at the cover's top corner. */
@Composable
fun StickerPicksWall(items: List<Pick>, open: Opener) {
    val p = LocalPalette.current
    StickerWall(items, Modifier.padding(top = 4.dp)) { pick, index ->
        StickerTile(
            pick.album, pick.artist, Sticker.Missing, index, p,
            onClick = { open.album(routeKey(pick.artist, pick.album), pick.artist, pick.album, null, pick.year) },
            action = {
                GetAlbumButton(pick.artist, pick.album, pageMetadata(pick.artist, pick.album, pick.year), Modifier.align(Alignment.TopEnd).padding(8.dp), overlay = true)
            },
        ) { AlbumCover(pick.artist, pick.album, null, Modifier.fillMaxWidth().aspectSquare(), rect = true) }
    }
}

/** Sticker Wall: the albums added in the last [RECENT_DAYS] days as the same wall, each stickered New. */
@Composable
fun StickerRecentWall(albums: List<LibraryAlbum>, open: Opener) {
    val p = LocalPalette.current
    StickerWall(albums) { album, index ->
        StickerTile(
            album.name, album.artist, Sticker.New, index, p,
            onClick = { open.album(album.key, album.artist, album.name, album.id, album.year) },
        ) { AlbumCover(album.artist, album.name, album.artworkUrl, Modifier.fillMaxWidth().aspectSquare(), rect = true) }
    }
}
