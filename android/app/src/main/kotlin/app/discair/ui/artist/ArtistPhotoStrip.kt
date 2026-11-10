package app.discair.ui.artist

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.State
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.model.ArtworkIndexResult
import app.discair.model.ArtworkSize
import app.discair.model.COLLAGE_ALBUM_LIMIT
import app.discair.model.CollageEntry
import app.discair.model.OwnedAlbum
import app.discair.model.artistCollage
import app.discair.model.loadArtworkIndex
import app.discair.ui.Opener
import app.discair.ui.common.Heading
import app.discair.ui.common.LocalImageLoader
import app.discair.ui.common.LocalRepository
import coil3.compose.AsyncImage
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.withContext

/**
 * The artist's session and band pictures (docs/artwork.md, idea 8): the indexes of the first owned albums that have a release group,
 * asked for together and read live. Empty while loading, when nothing qualifies or when a lookup fails; the page then shows no strip.
 */
@Composable
fun rememberArtistCollage(owned: List<OwnedAlbum>): State<List<CollageEntry>> {
    val repo = LocalRepository.current
    val albums = owned.filter { !it.releaseGroupMbid.isNullOrBlank() }.take(COLLAGE_ALBUM_LIMIT)
    val key = albums.joinToString(",") { it.releaseGroupMbid.orEmpty() }
    return produceState(emptyList<CollageEntry>(), key) {
        value = emptyList()
        if (albums.isEmpty()) return@produceState
        value = withContext(Dispatchers.IO) {
            try {
                val found = coroutineScope {
                    albums.map { album ->
                        async {
                            val rgid = album.releaseGroupMbid.orEmpty()
                            (loadArtworkIndex { repo.artworkIndex(rgid, null) } as? ArtworkIndexResult.Ready)?.let { album to it.index }
                        }
                    }.awaitAll().filterNotNull()
                }
                artistCollage(found)
            } catch (e: CancellationException) { throw e } catch (e: Exception) { emptyList() }
        }
    }
}

/** The photo strip on the artist page: a row of pictures, each opening the album it is from. Only shown with a qualifying set. */
@Composable
fun ArtistPhotoStrip(entries: List<CollageEntry>, artist: String, open: Opener) {
    val repo = LocalRepository.current
    Column(Modifier.fillMaxWidth().padding(vertical = 16.dp)) {
        Heading("Photos from the albums", Modifier.padding(horizontal = 16.dp))
        LazyRow(contentPadding = PaddingValues(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            items(entries, key = { it.image.imageId }) { entry ->
                val album = entry.album
                val url = remember(entry.image) { repo.artworkImageUrl(entry.image, ArtworkSize.Display) }
                Column(
                    Modifier.width(160.dp)
                        .clickable(role = Role.Button) { open.album(album.key, artist, album.name, album.id, album.year) }
                        .semantics(mergeDescendants = true) { contentDescription = "${entry.image.label()}, from ${album.name}" },
                ) {
                    Box(
                        Modifier.fillMaxWidth().height(120.dp).clip(RoundedCornerShape(8.dp))
                            .background(MaterialTheme.colorScheme.surfaceVariant),
                    ) {
                        if (url != null) {
                            AsyncImage(
                                model = url, contentDescription = null, imageLoader = LocalImageLoader.current,
                                contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize(),
                            )
                        }
                    }
                    Text(
                        album.name, style = MaterialTheme.typography.bodySmall, maxLines = 1, overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.padding(top = 6.dp),
                    )
                }
            }
        }
    }
}
