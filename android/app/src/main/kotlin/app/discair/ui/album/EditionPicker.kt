package app.discair.ui.album

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.model.ArtworkImage
import app.discair.model.ArtworkSize
import app.discair.ui.common.LocalImageLoader
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.Target
import coil3.compose.AsyncImage

/**
 * A small "N covers" stack on the album cover (docs/artwork.md, idea 7). It is a button of at least 48 dp, so it needs no
 * small tap target; its text says how many alternates exist.
 */
@Composable
fun EditionStack(count: Int, onClick: () -> Unit, modifier: Modifier = Modifier) {
    Box(
        modifier.heightIn(min = Target).clickable(role = Role.Button, onClick = onClick)
            .semantics { contentDescription = "Choose cover, $count editions" },
        contentAlignment = Alignment.Center,
    ) {
        Text(
            "$count covers", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurface,
            modifier = Modifier.clip(RoundedCornerShape(50)).background(MaterialTheme.colorScheme.surface.copy(alpha = 0.88f))
                .padding(horizontal = 10.dp, vertical = 4.dp),
        )
    }
}

/**
 * The covers to pick from, as a grid of thumbnails labelled with their edition ("1999 JP CD"). A tap picks one and closes
 * the sheet; "Use the automatic cover" removes the pick. The edition text is third-party data and is shown as plain text.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EditionPickerSheet(
    editions: List<ArtworkImage>, chosenId: Long?, onPick: (ArtworkImage) -> Unit, onAutomatic: () -> Unit, onDismiss: () -> Unit,
) {
    val repo = LocalRepository.current
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
        Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp)) {
            Text("Choose a cover", style = MaterialTheme.typography.titleLarge, modifier = Modifier.semantics { heading() })
            Text(
                "The cover you pick is used on every screen.", style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(bottom = 12.dp),
            )
            LazyVerticalGrid(
                GridCells.Adaptive(104.dp), Modifier.weightedHeight(), horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                items(editions, key = { it.imageId }) { image ->
                    val selected = image.imageId == chosenId
                    val label = image.label()
                    Column(
                        Modifier.heightIn(min = Target).clickable(role = Role.Button) { onPick(image) }
                            .semantics { this.selected = selected; contentDescription = if (selected) "$label, current cover" else label },
                    ) {
                        Box(
                            Modifier.fillMaxWidth().aspectRatio(1f).clip(RoundedCornerShape(8.dp))
                                .background(MaterialTheme.colorScheme.surfaceVariant)
                                .border(BorderStroke(if (selected) 3.dp else 0.dp, MaterialTheme.colorScheme.primary), RoundedCornerShape(8.dp)),
                        ) {
                            repo.artworkImageUrl(image, ArtworkSize.Thumb)?.let {
                                AsyncImage(it, null, imageLoader = LocalImageLoader.current, contentScale = ContentScale.Crop, modifier = Modifier.fillMaxWidth().aspectRatio(1f))
                            }
                        }
                        Text(
                            image.edition.ifBlank { "Front" }, style = MaterialTheme.typography.labelMedium, maxLines = 1,
                            overflow = TextOverflow.Ellipsis, modifier = Modifier.padding(top = 4.dp),
                        )
                    }
                }
            }
            TextButton(onAutomatic, Modifier.heightIn(min = Target).padding(vertical = 8.dp)) { Text("Use the automatic cover") }
        }
    }
}

private fun Modifier.weightedHeight(): Modifier = this.heightIn(max = 480.dp)
