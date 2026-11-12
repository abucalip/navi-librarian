package app.discair.ui.album

import androidx.compose.animation.Crossfade
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.clickable
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.customActions
import androidx.compose.ui.semantics.CustomAccessibilityAction
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import app.discair.model.ArtworkImage
import app.discair.model.ArtworkSize
import app.discair.model.faceAfter
import app.discair.ui.common.LocalImageLoader
import app.discair.ui.common.LocalRepository
import app.discair.ui.theme.rememberReducedMotion
import coil3.compose.AsyncImage
import kotlin.math.roundToInt
import kotlinx.coroutines.launch

private const val FLIP_MS = 420
private val SWIPE_THRESHOLD = 48.dp

/**
 * The album cover as a card that swipes over to its Back image, then Tray and Spine when the album has them
 * (docs/artwork.md, idea 1). With no [backs] it is just [front]: no gesture, no hint. A tap does the same as a swipe, for
 * switch access and TalkBack, which also gets a "Flip cover" action. Reduced motion (animations removed in system
 * settings) swaps the faces with a cross-fade instead of turning the card.
 */
@Composable
fun FlipCover(backs: List<ArtworkImage>, size: Dp, modifier: Modifier = Modifier, front: @Composable () -> Unit) {
    if (backs.isEmpty()) {
        Box(modifier.size(size)) { front() }
        return
    }
    val reduced = rememberReducedMotion()
    val scope = rememberCoroutineScope()
    val turn = remember { Animatable(0f) }
    var steps by remember { mutableIntStateOf(0) }
    val density = LocalDensity.current
    val thresholdPx = with(density) { SWIPE_THRESHOLD.toPx() }
    fun flip(direction: Int) {
        steps += direction
        if (!reduced) scope.launch { turn.animateTo(steps * 180f, tween(FLIP_MS)) }
    }
    val face = faceAfter(steps, backs.size)
    val label = if (face == 0) "Front cover" else backs[face - 1].label()
    var drag = 0f
    Box(
        modifier.size(size)
            .semantics {
                contentDescription = "$label. Swipe to flip the cover."
                customActions = listOf(CustomAccessibilityAction("Flip cover") { flip(1); true })
            }
            .clickable(role = Role.Button, onClickLabel = "Flip cover") { flip(1) }
            .pointerInput(backs) {
                detectHorizontalDragGestures(
                    onDragStart = { drag = 0f },
                    onHorizontalDrag = { _, dx -> drag += dx },
                    onDragEnd = { if (drag > thresholdPx) flip(-1) else if (drag < -thresholdPx) flip(1) },
                )
            },
    ) {
        if (reduced) {
            Crossfade(face, label = "cover face", animationSpec = tween(FLIP_MS)) { f -> FaceContent(f, backs, front, Modifier.fillMaxSize()) }
        } else {
            // The card turns by half a turn per step. Whichever face is nearer the viewer (the nearer half turn) is drawn; an
            // odd number of half turns mirrors it, so it is turned back.
            val half = (turn.value / 180f).roundToInt()
            FaceContent(
                faceAfter(half, backs.size), backs, front,
                Modifier.fillMaxSize().graphicsLayer {
                    rotationY = turn.value
                    cameraDistance = 14f * density.density
                }.graphicsLayer { rotationY = if (Math.floorMod(half, 2) == 1) 180f else 0f },
            )
        }
    }
}

@Composable
private fun FaceContent(face: Int, backs: List<ArtworkImage>, front: @Composable () -> Unit, modifier: Modifier) {
    Box(modifier) {
        if (face == 0) front() else {
            val image = backs[face - 1]
            val repo = LocalRepository.current
            val url = remember(image) { repo.artworkImageUrl(image, ArtworkSize.Display) }
            Box(Modifier.fillMaxSize().clip(MaterialTheme.shapes.small).background(MaterialTheme.colorScheme.surfaceVariant)) {
                if (url != null) AsyncImage(
                    model = url, contentDescription = image.label(), imageLoader = LocalImageLoader.current,
                    contentScale = ContentScale.Fit, modifier = Modifier.fillMaxSize(),
                )
            }
        }
    }
}
