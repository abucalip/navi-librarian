package app.discair.ui.player

import androidx.activity.compose.BackHandler
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.tween
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.graphics.Brush
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.foundation.selection.selectable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.animation.core.spring
import androidx.compose.foundation.gestures.Orientation
import androidx.compose.foundation.gestures.draggable
import androidx.compose.foundation.gestures.rememberDraggableState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.Dp
import kotlinx.coroutines.launch
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledIconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.IconButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import app.discair.lyrics.LyricsController
import app.discair.lyrics.LyricsFollower
import app.discair.lyrics.LyricsTimeline
import app.discair.lyrics.LyricsUiState
import app.discair.player.PlayerController
import app.discair.player.PlayerUiState
import app.discair.player.RepeatMode
import app.discair.player.qualityLabel
import app.discair.ui.common.Cover
import app.discair.ui.common.Target
import app.discair.ui.theme.Ink
import app.discair.ui.theme.Mono

fun formatTime(ms: Long): String {
    val total = (ms.coerceAtLeast(0) / 1000).toInt()
    return "%d:%02d".format(total / 60, total % 60)
}

/** Spoken value of the seek bar, for example "1:23 of 4:10". */
fun seekDescription(positionMs: Long, durationMs: Long) = "${formatTime(positionMs)} of ${formatTime(durationMs)}"

/** The view last used in this session (lyrics contract 7); the sheet can be closed and reopened. */
private var lastView = 0

private val ViewLabels = listOf("Player", "Lyrics", "Queue")

private data class ViewTab(val view: Int, val icon: ImageVector, val label: String)

/** Left to right in the order the cards sit: queue, artwork, lyrics. */
private val ViewTabs = listOf(
    ViewTab(2, PlayerIcons.List, "Queue"),
    ViewTab(0, PlayerIcons.MusicNote, "Player"),
    ViewTab(1, PlayerIcons.Quote, "Lyrics"),
)

/** Three icons; the active one is larger and white, the others smaller and dim. Selection is also announced, not colour alone. */
@Composable
private fun ViewIcons(selected: Int, onSelect: (Int) -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        ViewTabs.forEach { tab ->
            val active = tab.view == selected
            val size by animateDpAsState(if (active) 24.dp else 18.dp, label = "viewIconSize")
            val tint by animateColorAsState(if (active) Color.White else Color.White.copy(alpha = 0.4f), label = "viewIconTint")
            Box(
                Modifier.size(Target).selectable(selected = active, role = Role.Tab) { onSelect(tab.view) },
                contentAlignment = Alignment.Center,
            ) { Icon(tab.icon, contentDescription = tab.label, tint = tint, modifier = Modifier.size(size)) }
        }
    }
}

/** Where each view sits on the flip axis: the queue is one flip to the left of the artwork, the lyrics one to the right. */
private fun viewToProgress(view: Int) = when (view) { 1 -> 1f; 2 -> -1f; else -> 0f }
private fun progressToView(progress: Float) = when { progress > 0.5f -> 1; progress < -0.5f -> 2; else -> 0 }

/** Player artwork is requested large (the server caps `size` at 1000); the rest of the app keeps the small default. */
const val PLAYER_ARTWORK_PX = 1000
fun playerArtworkUrl(url: String): String? =
    url.takeIf { it.isNotBlank() }?.let { if ("size=" in it) it else it + (if ('?' in it) "&" else "?") + "size=$PLAYER_ARTWORK_PX" }

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NowPlayingSheet(state: PlayerUiState, controller: PlayerController, lyrics: LyricsController, onDismiss: () -> Unit, onSignIn: () -> Unit) {
    val sheet = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var view by remember { mutableStateOf(lastView) }
    var tint by remember { mutableStateOf<Color?>(null) }
    var eqOpen by remember { mutableStateOf(false) }
    var crossfadeOpen by remember { mutableStateOf(false) }
    val container = (androidx.compose.ui.platform.LocalContext.current.applicationContext as app.discair.DiscairApplication).container
    BackHandler(enabled = view != 0) { view = 0; lastView = 0 }
    val scope = androidx.compose.runtime.rememberCoroutineScope()
    // -1 = queue, 0 = artwork, +1 = lyrics; fractions are mid-flip while a finger is down or the flip settles.
    val flip = remember { Animatable(viewToProgress(view)) }
    LaunchedEffect(view) { flip.animateTo(viewToProgress(view), spring(dampingRatio = 0.85f, stiffness = 220f)) }
    val follower = remember { LyricsFollower(scope, controller::livePositionMs) }
    val lyricsState by lyrics.state.collectAsState()
    val songId = state.current?.songId
    val nextId = state.queue.nextIndex()?.let { state.queue.items.getOrNull(it)?.songId }?.takeIf { it != songId }
    val lyricsOpen = view == 1 || flip.value > 0.5f
    // Fetch only while the Lyrics view is open for the song that is playing; close stops everything.
    LaunchedEffect(lyricsOpen, songId, nextId) {
        if (lyricsOpen && songId != null) lyrics.open(songId, nextId) else lyrics.close()
    }
    DisposableEffect(Unit) { onDispose { lyrics.close(); follower.setVisible(false) } }
    val ready = (lyricsState as? LyricsUiState.Ready)?.takeIf { it.songId == songId }
    LaunchedEffect(ready) { follower.setTimeline(ready?.let { LyricsTimeline(it.lyrics) }) }
    LaunchedEffect(lyricsOpen) { follower.setVisible(lyricsOpen) }
    LaunchedEffect(state.isPlaying) { follower.setPlaying(state.isPlaying) }
    LaunchedEffect(songId, state.positionMs) { follower.refresh() } // a seek or skip shows at once, also while paused
    val currentLine by follower.line.collectAsState()
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheet, containerColor = Ink.Ink) {
        val item = state.current
        if (item == null) { onDismiss(); return@ModalBottomSheet }
        // The artwork's colour washes down from the top, as on the album and artist pages.
        val wash by animateColorAsState(tint ?: Ink.Ink, animationSpec = tween(500), label = "artworkTint")
        LaunchedEffect(item.coverUrl) { if (item.coverUrl.isBlank()) tint = null }
        Column(
            Modifier.fillMaxWidth().drawBehind {
                // Starts above the content so the drag handle sits on the tint too.
                val top = -48.dp.toPx()
                drawRect(Brush.verticalGradient(listOf(wash, Ink.Ink), startY = top, endY = size.height * 0.9f), topLeft = androidx.compose.ui.geometry.Offset(0f, top), size = androidx.compose.ui.geometry.Size(size.width, size.height - top))
            }.padding(horizontal = 16.dp),
        ) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = onDismiss, Modifier.size(Target)) { Icon(PlayerIcons.Down, contentDescription = "Close now playing") }
                Spacer(Modifier.weight(1f))
                // Three labelled views; the selected one is announced as selected and drawn raised (not colour alone).
                ViewIcons(view) { view = it; lastView = it }
                Spacer(Modifier.weight(1f))
                Spacer(Modifier.size(Target)) // balances the close button so the tabs sit in the middle
            }
            Spacer(Modifier.height(12.dp)) // the tabs must not touch the cover, the lyrics note or the queue title
            Player(
                state, controller, onSignIn, { eqOpen = true }, { crossfadeOpen = true },
                card = {
                    FlipCard(
                        progress = flip.value,
                        onDrag = { next -> scope.launch { flip.snapTo(next) } },
                        onSettle = { target, velocity ->
                            val changed = target != view
                            view = target; lastView = target
                            // An unchanged view does not retrigger the effect above, so spring back here.
                            if (!changed) scope.launch { flip.animateTo(viewToProgress(target), spring(dampingRatio = 0.85f, stiffness = 220f), velocity) }
                        },
                        base = viewToProgress(view),
                        front = { Cover(playerArtworkUrl(item.coverUrl), Modifier.fillMaxSize(), onColor = { tint = it }) },
                        lyricsFace = {
                            LyricsPanel(
                                if (lyricsState.songIdOrNull() == songId) lyricsState else LyricsUiState.Idle,
                                currentLine, songId.orEmpty(), onTryAgain = { if (songId != null) lyrics.retry(songId, nextId) },
                                Modifier.fillMaxSize().padding(12.dp),
                            )
                        },
                        queueFace = { QueuePanel(state, controller, Modifier.fillMaxSize().padding(horizontal = 12.dp)) },
                    )
                },
            )
        }
        // Settings come up from the bottom over the player, each in its own sheet.
        if (eqOpen) SettingsSheet({ eqOpen = false }) { EqualizerScreen(container, onBack = null) }
        if (crossfadeOpen) SettingsSheet({ crossfadeOpen = false }) { CrossfadeScreen(container, onBack = null) }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SettingsSheet(onDismiss: () -> Unit, content: @Composable () -> Unit) {
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true), containerColor = Ink.Surface) {
        content()
    }
}

/**
 * The artwork with the lyrics on its right-hand back and the queue on its left-hand back. Dragging
 * left turns the card towards the lyrics, dragging right towards the queue; a flick or half a turn
 * commits. Only one face is composed at a time, so the hidden one never takes touches or focus.
 */
@Composable
private fun FlipCard(
    progress: Float, base: Float, onDrag: (Float) -> Unit, onSettle: (view: Int, velocity: Float) -> Unit,
    front: @Composable () -> Unit, lyricsFace: @Composable () -> Unit, queueFace: @Composable () -> Unit,
) {
    val p = progress.coerceIn(-1f, 1f)
    val angle = -p * 180f
    val showFront = kotlin.math.abs(p) < 0.5f
    var widthPx by remember { mutableStateOf(1f) }
    val density = LocalDensity.current.density
    Box(
        Modifier.widthIn(max = 480.dp).fillMaxWidth().aspectRatio(1f)
            .onSizeChanged { widthPx = it.width.toFloat().coerceAtLeast(1f) }
            .draggable(
                orientation = Orientation.Horizontal,
                state = rememberDraggableState { delta ->
                    // Dragging left (negative) moves towards the lyrics; one view per gesture at most.
                    onDrag((p - delta / widthPx).coerceIn(base - 1f, base + 1f).coerceIn(-1f, 1f))
                },
                onDragStopped = { velocity ->
                    val target = when {
                        velocity < -900f -> base + 1f
                        velocity > 900f -> base - 1f
                        else -> p
                    }.coerceIn(base - 1f, base + 1f).coerceIn(-1f, 1f)
                    val snapped = if (target == p) Math.round(p).toFloat() else Math.round(target).toFloat()
                    onSettle(progressToView(snapped), -velocity / widthPx)
                },
            )
            .graphicsLayer {
                rotationY = if (showFront) angle else if (p > 0f) angle + 180f else angle - 180f
                cameraDistance = 14f * density
            }
            .clip(RoundedCornerShape(12.dp))
            .background(MaterialTheme.colorScheme.surfaceVariant),
    ) {
        when {
            showFront -> front()
            p > 0f -> lyricsFace()
            else -> queueFace()
        }
    }
}

@Composable
private fun Player(state: PlayerUiState, controller: PlayerController, onSignIn: () -> Unit, onEqualizer: () -> Unit, onCrossfade: () -> Unit, card: @Composable () -> Unit) {
    val item = state.current ?: return
    var dragging by remember { mutableStateOf<Float?>(null) }
    val duration = state.durationMs
    val fraction = dragging ?: if (duration > 0) (state.positionMs.toFloat() / duration).coerceIn(0f, 1f) else 0f
    Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()), horizontalAlignment = Alignment.CenterHorizontally) {
        card()
        Spacer(Modifier.height(16.dp))
        Text(
            item.title, style = MaterialTheme.typography.titleLarge, textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth().semantics { liveRegion = LiveRegionMode.Polite; heading() },
        )
        Text(
            listOf(item.artist, item.album).filter { it.isNotBlank() }.joinToString(" · "),
            style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth(),
        )
        item.year?.let {
            Text(
                "$it", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth().padding(top = 2.dp),
            )
        }
        Spacer(Modifier.height(24.dp))
        // Status in words: loading, buffering, lost connection, unavailable, queue full.
        val subtitle = playerSubtitle(state)
        if (state.status != null || state.buffering) {
            Text(
                subtitle, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.primary,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp).semantics { liveRegion = LiveRegionMode.Polite },
            )
        }
        if (state.signInRequired) TextButton(onClick = { controller.dismissSignIn(); onSignIn() }, Modifier.heightIn(min = Target)) { Text("Sign in again") }
        if (state.waitingForNetwork) TextButton(onClick = controller::retryNow, Modifier.heightIn(min = Target)) { Text("Retry now") }

        val shown = if (dragging != null) (fraction * duration).toLong() else state.positionMs
        val timeStyle = MaterialTheme.typography.labelSmall.copy(fontFamily = Mono)
        val quality = qualityLabel(item)
        Box(Modifier.fillMaxWidth().padding(top = 8.dp)) {
            if (quality != null) {
                Text(
                    quality, style = timeStyle, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1,
                    modifier = Modifier.align(Alignment.TopCenter)
                        .border(1.dp, Ink.Edge, RoundedCornerShape(4.dp))
                        .padding(horizontal = 6.dp, vertical = 1.dp),
                )
            }
            Row(Modifier.fillMaxWidth().padding(top = if (quality != null) 14.dp else 0.dp), verticalAlignment = Alignment.CenterVertically) {
                Text(formatTime(shown), style = timeStyle, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(end = 8.dp))
                SeekBar(
                    fraction = fraction, enabled = duration > 0,
                    onChange = { dragging = it },
                    onFinish = { dragging?.let { controller.seekTo((it * duration).toLong()) }; dragging = null },
                    modifier = Modifier.weight(1f).semantics {
                        contentDescription = "Seek"
                        stateDescription = seekDescription(shown, duration)
                    },
                )
                Text(if (duration > 0) formatTime(duration) else "--:--", style = timeStyle, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(start = 8.dp))
            }
        }

        Row(Modifier.fillMaxWidth().padding(vertical = 8.dp), horizontalArrangement = Arrangement.SpaceEvenly, verticalAlignment = Alignment.CenterVertically) {
            val shuffle = state.queue.shuffle
            IconButton(
                onClick = { controller.setShuffle(!shuffle) },
                Modifier.size(Target).semantics { stateDescription = if (shuffle) "On" else "Off" },
            ) {
                Icon(PlayerIcons.Shuffle, contentDescription = "Shuffle", tint = if (shuffle) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant)
            }
            IconButton(onClick = controller::previous, Modifier.size(Target)) { Icon(PlayerIcons.Previous, contentDescription = "Previous song") }
            FilledIconButton(
                onClick = controller::playPause, Modifier.size(64.dp),
                colors = IconButtonDefaults.filledIconButtonColors(containerColor = MaterialTheme.colorScheme.primary, contentColor = MaterialTheme.colorScheme.onPrimary),
            ) {
                Icon(if (state.isPlaying) PlayerIcons.Pause else PlayerIcons.Play, contentDescription = if (state.isPlaying) "Pause" else "Play", modifier = Modifier.size(32.dp))
            }
            IconButton(onClick = controller::next, Modifier.size(Target), enabled = state.queue.items.size > 1) { Icon(PlayerIcons.Next, contentDescription = "Next song") }
            val repeat = state.queue.repeat
            IconButton(
                onClick = controller::cycleRepeat,
                Modifier.size(Target).semantics { stateDescription = when (repeat) { RepeatMode.Off -> "Off"; RepeatMode.All -> "Repeat all"; RepeatMode.One -> "Repeat one" } },
            ) {
                Icon(
                    if (repeat == RepeatMode.One) PlayerIcons.RepeatOne else PlayerIcons.Repeat, contentDescription = "Repeat",
                    tint = if (repeat == RepeatMode.Off) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.primary,
                )
            }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
            EqualizerLink(onEqualizer)
            Spacer(Modifier.size(16.dp))
            CrossfadeLink(onCrossfade)
        }
        Spacer(Modifier.height(24.dp))
    }
}

private fun LyricsUiState.songIdOrNull(): String? = when (this) {
    is LyricsUiState.Loading -> songId
    is LyricsUiState.Ready -> songId
    is LyricsUiState.None -> songId
    is LyricsUiState.Unsupported -> songId
    is LyricsUiState.Failed -> songId
    LyricsUiState.Idle -> null
}
