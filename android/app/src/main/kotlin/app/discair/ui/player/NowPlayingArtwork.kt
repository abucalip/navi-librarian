package app.discair.ui.player

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.PowerManager
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshots.SnapshotStateMap
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.ui.draw.BlurredEdgeTreatment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import app.discair.model.ArtworkImage
import app.discair.model.ArtworkIndex
import app.discair.model.ArtworkIndexResult
import app.discair.model.ArtworkSize
import app.discair.model.loadArtworkIndex
import app.discair.model.slideshowFrame
import app.discair.player.QueueItem
import app.discair.ui.common.LocalImageLoader
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.rememberReducedMotion
import app.discair.ui.common.routeKey
import coil3.compose.AsyncImage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** Release groups found for the albums played this session, so a song change inside an album asks the album page once. */
private object NowPlayingGroups {
    val byAlbum = HashMap<String, String>()
}

/**
 * The playing album's images (disc and slideshow). The release group comes from the album page the app already reads; the index is
 * asked for until it is built. Null while loading and for an album with no images, an unknown group or a failed lookup: nothing extra
 * is shown then, and nothing is said about the album.
 */
@Composable
fun rememberAlbumArtIndex(item: QueueItem?): ArtworkIndex? {
    val repo = LocalRepository.current
    val artist = item?.artist.orEmpty()
    val album = item?.album.orEmpty()
    val state = produceState<ArtworkIndex?>(null, artist, album) {
        value = null
        if (album.isBlank()) return@produceState
        value = withContext(Dispatchers.IO) {
            try {
                val key = "${artist.lowercase()}|${album.lowercase()}"
                var rgid = synchronized(NowPlayingGroups) { NowPlayingGroups.byAlbum[key] }
                if (rgid == null) {
                    val page = repo.albumPage(routeKey(artist, album), item?.albumId?.ifBlank { null }, artist, album, item?.year)
                    rgid = page.sections.album.album?.releaseGroupMbid?.takeIf { it.isNotBlank() } ?: return@withContext null
                    synchronized(NowPlayingGroups) { NowPlayingGroups.byAlbum[key] = rgid }
                }
                (loadArtworkIndex { repo.artworkIndex(rgid, null) } as? ArtworkIndexResult.Ready)?.index
            } catch (e: kotlinx.coroutines.CancellationException) { throw e } catch (e: Exception) { null }
        }
    }
    return state.value
}

/**
 * The record on Now Playing (idea 3): a Medium image cut to a disc with a spindle hole. It turns slowly (10 rpm) only while [spinning]
 * and never under Reduce Motion; it holds its angle when paused.
 */
@Composable
fun DiscImage(image: ArtworkImage, size: Dp, spinning: Boolean, modifier: Modifier = Modifier) {
    val repo = LocalRepository.current
    val reduced = rememberReducedMotion()
    val url = remember(image) { repo.artworkImageUrl(image, ArtworkSize.Display) } ?: return
    val angle = remember { Animatable(0f) }
    LaunchedEffect(spinning && !reduced) {
        if (!spinning || reduced) return@LaunchedEffect
        while (true) {
            angle.animateTo(angle.value + 360f, tween(6000, easing = LinearEasing))
            angle.snapTo(angle.value % 360f)
        }
    }
    Box(modifier.size(size).semantics { contentDescription = "Disc: ${image.label()}" }) {
        Box(Modifier.fillMaxSize().graphicsLayer { rotationZ = angle.value }.clip(CircleShape).background(Color.Black)) {
            AsyncImage(model = url, contentDescription = null, imageLoader = LocalImageLoader.current, contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize())
        }
        Box(Modifier.matchParentSize().border(1.5.dp, Color.Black.copy(alpha = 0.35f), CircleShape))
        Box(Modifier.align(androidx.compose.ui.Alignment.Center).size(size * 0.07f).clip(CircleShape).background(Color.Black.copy(alpha = 0.85f)).border(1.dp, Color.White.copy(alpha = 0.7f), CircleShape))
    }
}

/** True while Battery Saver is on; the slideshow holds still then. */
@Composable
private fun rememberPowerSave(): Boolean {
    val context = LocalContext.current
    var saving by remember { mutableStateOf((context.getSystemService(Context.POWER_SERVICE) as? PowerManager)?.isPowerSaveMode == true) }
    DisposableEffect(context) {
        val receiver = object : BroadcastReceiver() {
            override fun onReceive(c: Context?, i: Intent?) { saving = (context.getSystemService(Context.POWER_SERVICE) as? PowerManager)?.isPowerSaveMode == true }
        }
        androidx.core.content.ContextCompat.registerReceiver(context, receiver, IntentFilter(PowerManager.ACTION_POWER_SAVE_MODE_CHANGED), androidx.core.content.ContextCompat.RECEIVER_NOT_EXPORTED)
        onDispose { context.unregisterReceiver(receiver) }
    }
    return saving
}

/**
 * The session and booklet photos drifting, blurred, behind the lyrics (idea 4). Call inside a Box over the blurred cover, which shows until
 * the first photo has loaded. Each photo is held, then cross-faded into the next with a slow zoom and pan. The drift holds still under
 * Reduce Motion, Battery Saver and pause. Needs the blur (Android 12 and up): older phones keep the cover tint.
 */
@Composable
fun BoxScope.SlideshowBackdrop(slides: List<ArtworkImage>, playing: Boolean) {
    if (!canBlur || slides.isEmpty()) return
    val repo = LocalRepository.current
    val reduced = rememberReducedMotion()
    val powerSave = rememberPowerSave()
    val running = playing && !reduced && !powerSave
    var elapsed by remember(slides) { mutableFloatStateOf(0f) }
    LaunchedEffect(running, slides) {
        if (!running) return@LaunchedEffect
        var last = withFrameNanosCompat()
        while (true) {
            val now = withFrameNanosCompat()
            elapsed += (now - last) / 1_000_000_000f
            last = now
        }
    }
    val loaded: SnapshotStateMap<Long, Boolean> = remember(slides) { mutableStateMapOf() }
    val frame = slideshowFrame(elapsed.toDouble(), slides.size) ?: return
    Box(Modifier.matchParentSize().blur(36.dp, BlurredEdgeTreatment.Unbounded)) {
        @Composable fun layer(i: Int, progress: Float, alpha: Float) {
            val image = slides.getOrNull(i) ?: return
            val url = remember(image) { repo.artworkImageUrl(image, ArtworkSize.Display) } ?: return
            AsyncImage(
                model = url, contentDescription = null, imageLoader = LocalImageLoader.current, contentScale = ContentScale.Crop,
                onSuccess = { loaded[image.imageId] = true },
                modifier = Modifier.matchParentSize()
                    .alpha(if (loaded[image.imageId] == true) alpha else 0f)
                    .graphicsLayer { val s = 1.18f + 0.1f * progress; scaleX = s; scaleY = s; translationX = (progress - 0.5f) * 30f },
            )
        }
        layer(frame.index, frame.progress, 1f)
        if (frame.mix > 0f) layer(frame.next, 0f, frame.mix)
    }
    Box(Modifier.matchParentSize().background(Color.Black.copy(alpha = 0.38f)))
}

private suspend fun withFrameNanosCompat(): Long = androidx.compose.runtime.withFrameNanos { it }

/**
 * Standard layout: the disc sits behind the cover card and slides out to its right once it has loaded (a plain appearance under Reduce
 * Motion). With no disc this is just [content]: nothing is reserved and nothing moves.
 */
@Composable
fun DiscSleeve(disc: ArtworkImage?, spinning: Boolean, content: @Composable () -> Unit) {
    if (disc == null) { content(); return }
    val reduced = rememberReducedMotion()
    val reserve = 44.dp
    var out by remember(disc.imageId) { mutableStateOf(false) }
    LaunchedEffect(disc.imageId) { kotlinx.coroutines.delay(400); out = true }
    androidx.compose.foundation.layout.BoxWithConstraints(Modifier.androidxWidthIn480()) {
        val cardWidth = maxWidth - reserve
        val diameter = cardWidth * 0.9f
        val slide by androidx.compose.animation.core.animateDpAsState(
            if (out) cardWidth * 0.05f + 40.dp else 0.dp,
            animationSpec = if (reduced) tween(0) else androidx.compose.animation.core.spring(dampingRatio = 0.7f, stiffness = 120f), label = "discSlide",
        )
        DiscImage(disc, diameter, spinning, Modifier.align(androidx.compose.ui.Alignment.CenterStart).offset(x = (cardWidth - diameter) / 2 + slide))
        Box(Modifier.padding(end = reserve)) { content() }
    }
}

private fun Modifier.androidxWidthIn480(): Modifier = this.then(Modifier.fillMaxWidth().widthIn(max = 480.dp))
