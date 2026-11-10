package app.discair.ui.common

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
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
import androidx.compose.ui.unit.dp
import app.discair.model.ArtworkImage
import app.discair.model.ArtworkIndexResult
import app.discair.model.ArtworkSize
import app.discair.model.editionCovers
import app.discair.model.loadArtworkIndex
import coil3.compose.AsyncImage
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * The covers of the release group a Downloads row is fetching (docs/artwork.md, idea 13): up to three Front images, each
 * labelled with its edition. Read-only; it does not change the download. The server does not record which pressing was
 * matched, so the caption says these are the album's editions. Nothing shows while loading, when the group has no Front image
 * or when the lookup fails.
 */
@Composable
fun ReleaseEditionCovers(releaseGroup: String, modifier: Modifier = Modifier) {
    val repo = LocalRepository.current
    val covers by produceState<List<ArtworkImage>?>(null, releaseGroup) {
        value = withContext(Dispatchers.IO) {
            try {
                editionCovers((loadArtworkIndex { repo.artworkIndex(releaseGroup, null) } as? ArtworkIndexResult.Ready)?.index)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                emptyList()
            }
        }
    }
    val shown = covers.orEmpty()
    if (shown.isEmpty()) return
    Column(modifier.fillMaxWidth().padding(top = 8.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            shown.forEach { face ->
                val url = remember(face.imageId) { repo.artworkImageUrl(face, ArtworkSize.Thumb) }
                Box(
                    Modifier.size(48.dp).clip(RoundedCornerShape(6.dp)).background(MaterialTheme.colorScheme.surfaceVariant)
                        .semantics { contentDescription = face.label() },
                ) {
                    if (url != null) {
                        AsyncImage(
                            model = url, contentDescription = null, imageLoader = LocalImageLoader.current,
                            contentScale = ContentScale.Crop, modifier = Modifier.size(48.dp),
                        )
                    }
                }
            }
        }
        Text(
            "Editions of this album. The pressing fetched is not recorded.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}
