package app.discair.ui.common

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import app.discair.model.ArtworkImage
import app.discair.model.ArtworkIndex
import app.discair.model.ArtworkIndexResult
import app.discair.model.ArtworkSize
import app.discair.model.loadArtworkIndex
import app.discair.model.pathCoverFaces
import app.discair.model.roomPhotos
import coil3.compose.AsyncImage
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** Release groups already found for a path step's album (artist and title), so a row asks the album page once. */
private object PathGroups {
    val byAlbum = HashMap<String, String>()
}

/**
 * The artwork index of the album a path step names. Steps carry only title and artist, so the release group comes from the album
 * page the app already reads. Null while [enabled] is false or loading, and for an unknown group, an empty index or a failed lookup:
 * the caller then draws nothing extra and says nothing about the album.
 */
@Composable
fun rememberPathAlbumIndex(artist: String, album: String, enabled: Boolean = true): ArtworkIndex? {
    val repo = LocalRepository.current
    val state = produceState<ArtworkIndex?>(null, artist, album, enabled) {
        if (!enabled || album.isBlank()) return@produceState
        value = withContext(Dispatchers.IO) {
            try {
                val key = "${artist.lowercase()}|${album.lowercase()}"
                var rgid = synchronized(PathGroups) { PathGroups.byAlbum[key] }
                if (rgid == null) {
                    val page = repo.albumPage(routeKey(artist, album), null, artist, album, null)
                    rgid = page.sections.album.album?.releaseGroupMbid?.takeIf { it.isNotBlank() } ?: return@withContext null
                    synchronized(PathGroups) { PathGroups.byAlbum[key] = rgid }
                }
                (loadArtworkIndex { repo.artworkIndex(rgid, null) } as? ArtworkIndexResult.Ready)?.index
            } catch (e: CancellationException) { throw e } catch (e: Exception) { null }
        }
    }
    return state.value
}

/**
 * A path row's cover that cycles through the album's alternate covers (idea 10). [step] counts long presses: 0 shows the usual cover
 * and so does an album with fewer than two covers. Nothing moves by itself, so there is no motion to turn off.
 */
@Composable
fun PathRowCover(artist: String, album: String, step: Int, modifier: Modifier = Modifier) {
    val repo = LocalRepository.current
    val faces = pathCoverFaces(rememberPathAlbumIndex(artist, album, enabled = step > 0))
    if (step <= 0 || faces.isEmpty()) {
        PathAlbumCover(artist, album, modifier)
        return
    }
    val face = faces[(step - 1) % faces.size]
    val url = remember(face.imageId) { repo.artworkImageUrl(face, ArtworkSize.Thumb) }
    Box(modifier.clip(RoundedCornerShape(4.dp)).background(MaterialTheme.colorScheme.surfaceVariant).semantics { contentDescription = face.label() }) {
        if (url != null) AsyncImage(model = url, contentDescription = null, imageLoader = LocalImageLoader.current, contentScale = ContentScale.Crop, modifier = Modifier.matchParentSize())
    }
}

/**
 * Same Room: the two albums' session photos side by side, each under its album's name. Drawn only when at least one album has a
 * photo; an album with none says "No session photos" and nothing is compared or inferred beyond what the pictures are.
 */
@Composable
fun SameRoomPhotos(startArtist: String, startAlbum: String, otherArtist: String, otherAlbum: String, modifier: Modifier = Modifier) {
    val start = roomPhotos(rememberPathAlbumIndex(startArtist, startAlbum))
    val other = roomPhotos(rememberPathAlbumIndex(otherArtist, otherAlbum))
    if (!app.discair.model.hasRoomPhotos(start, other)) return
    Row(modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        RoomColumn(startAlbum, start, Modifier.weight(1f))
        RoomColumn(otherAlbum, other, Modifier.weight(1f))
    }
}

@Composable
private fun RoomColumn(title: String, photos: List<ArtworkImage>, modifier: Modifier) {
    val repo = LocalRepository.current
    Column(modifier, verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(title, style = MaterialTheme.typography.labelLarge, maxLines = 1, overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis)
        if (photos.isEmpty()) Text("No session photos", style = MaterialTheme.typography.bodySmall)
        photos.forEach { photo ->
            val url = remember(photo.imageId) { repo.artworkImageUrl(photo, ArtworkSize.Display) }
            Box(
                Modifier.fillMaxWidth().aspectRatio(1.5f).clip(RoundedCornerShape(6.dp)).background(MaterialTheme.colorScheme.surfaceVariant)
                    .semantics { contentDescription = photo.label() },
            ) {
                if (url != null) AsyncImage(model = url, contentDescription = null, imageLoader = LocalImageLoader.current, contentScale = ContentScale.Crop, modifier = Modifier.matchParentSize())
            }
        }
    }
}
