package app.discair.ui.common

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import app.discair.model.ArtworkImage
import app.discair.model.ArtworkIndexResult
import app.discair.model.ArtworkSize
import app.discair.model.discoverPeekFaces
import app.discair.model.loadArtworkIndex
import coil3.compose.AsyncImage
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Up to three covers of one album under a Discover row (docs/artwork.md, idea 9): the Back, the first booklet page and the
 * Medium. Composed only while the reader has opened the row's covers, so the lookup happens then and not while scrolling.
 * Nothing shows while loading, when the album has no such pictures or when the lookup fails.
 */
@Composable
fun DiscoverPeek(releaseGroup: String, modifier: Modifier = Modifier) {
    val repo = LocalRepository.current
    val faces by produceState<List<ArtworkImage>?>(null, releaseGroup) {
        value = withContext(Dispatchers.IO) {
            try {
                discoverPeekFaces((loadArtworkIndex { repo.artworkIndex(releaseGroup, null) } as? ArtworkIndexResult.Ready)?.index)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                emptyList()
            }
        }
    }
    val shown = faces.orEmpty()
    if (shown.isEmpty()) return
    Row(modifier.fillMaxWidth().padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        shown.forEach { face ->
            val url = remember(face.imageId) { repo.artworkImageUrl(face, ArtworkSize.Thumb) }
            Box(
                Modifier.size(64.dp).clip(RoundedCornerShape(6.dp)).background(MaterialTheme.colorScheme.surfaceVariant)
                    .semantics { contentDescription = face.label() },
            ) {
                if (url != null) {
                    AsyncImage(
                        model = url, contentDescription = null, imageLoader = LocalImageLoader.current,
                        contentScale = ContentScale.Crop, modifier = Modifier.size(64.dp),
                    )
                }
            }
        }
    }
}
