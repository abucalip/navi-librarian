package app.discair.ui.player

import android.provider.Settings
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.MutableTransitionState
import androidx.compose.animation.core.tween
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.layout
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.CustomAccessibilityAction
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.customActions
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import app.discair.lyrics.LyricsTimeline
import app.discair.lyrics.LyricsUiState
import app.discair.lyrics.lyricsFailureText
import app.discair.model.trackImages
import app.discair.player.PlayerController
import app.discair.player.PlayerUiState
import app.discair.player.QueueItem
import app.discair.player.RepeatMode
import app.discair.player.qualityLabel
import app.discair.ui.common.Cover
import app.discair.ui.common.GalleryButton
import app.discair.ui.common.GalleryButtonKind
import app.discair.ui.common.GalleryIconButton
import app.discair.ui.common.GalleryIcons
import app.discair.ui.common.GalleryMenuButton
import app.discair.ui.common.GalleryPlayingBars
import app.discair.ui.common.GalleryPrint
import app.discair.ui.common.GalleryRow
import app.discair.ui.common.GalleryRule
import app.discair.ui.common.GalleryRules
import app.discair.ui.common.GalleryTag
import app.discair.ui.common.GallerySwitch
import app.discair.ui.common.GallerySectionHead
import app.discair.ui.common.GalleryState
import app.discair.ui.common.GalleryType
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.TransparentSystemBars
import app.discair.ui.common.gallerySpot
import app.discair.ui.theme.GalleryFaces
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.MotionFamily
import app.discair.ui.theme.MotionRules
import app.discair.ui.theme.rememberReducedMotion
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/*
 * Gallery (Layout.Gallery): Now Playing, Queue and Lyrics. Mockup: docs/design/gallery/pages/player. Reached only from NowPlayingSheet's Gallery
 * branch; no other theme draws any of this. Three views of one full-screen page (0 player, 1 lyrics, 2 queue) that share the seek line and the transport,
 * as in the mockup's three frames. Every control does what its Standard twin does.
 */

/** The pure rules of the Gallery player (unit-tested). The measurements are gallery.css (1 CSS px = 1dp). */
object GalleryPlayerRules {
    /** Now Playing's print (`.print.np`, 14dp mat) and the smallest it is drawn when the screen is short. */
    const val PRINT = 300
    const val PRINT_MIN = 140
    const val QUEUE_NOW_PRINT = 56
    const val ROW_PRINT = 48

    /** The share of the muted text colour a lyric line keeps once sung (`.was`) and while it waits (`.lyr p`). */
    const val LYRIC_SUNG_ALPHA = 0.8f
    const val LYRIC_WAITING_ALPHA = 0.55f

    /** Motion (docs/GALLERY_THEME.md section 8): the page rises in 440ms and falls in 360ms. */
    const val RISE_MS = 440
    const val FALL_MS = 360

    /** The bar's catalogue line: "Playing from Laughing Stock" on the player, the page's name on the other two. */
    fun barTitle(view: Int, album: String): String = when (view) {
        CoverStackPlayerRules.VIEW_QUEUE -> "Queue"
        CoverStackPlayerRules.VIEW_LYRICS -> "Lyrics"
        else -> album.trim().takeIf { it.isNotEmpty() }?.let { "Playing from $it" } ?: "Now playing"
    }

    /** "−6:27": the time left, with a true minus sign; "--:--" while the length is not known. */
    fun remaining(positionMs: Long, durationMs: Long): String =
        if (durationMs <= 0) "--:--" else "−" + formatTime((durationMs - positionMs).coerceAtLeast(0))

    /** The queue positions after the playing song, in order. */
    fun upcoming(index: Int, size: Int): List<Int> = if (index < 0 || index >= size - 1) emptyList() else ((index + 1) until size).toList()

    /** "Next · 5 songs" (the singular for one). */
    fun nextHeading(count: Int): String = "Next · $count ${if (count == 1) "song" else "songs"}"

    /** The playing song's line in the queue: "Talk Talk · playing, 3:12 of 9:39" (or "paused" while it is not playing; the time only when the length is known). */
    fun playingLine(artist: String, playing: Boolean, positionMs: Long, durationMs: Long): String {
        val word = if (playing) "playing" else "paused"
        val time = if (durationMs > 0) ", ${formatTime(positionMs)} of ${formatTime(durationMs)}" else ""
        return listOf(artist.trim().takeIf { it.isNotEmpty() }, word + time).filterNotNull().joinToString(" · ")
    }

    /** How a lyric line is drawn. */
    enum class LineLook { Sung, Current, Waiting, Plain }

    /** A line of timed lyrics is sung before the current one and waiting after it; untimed lyrics are all plain. With no current line yet every timed line waits. */
    fun lineLook(timed: Boolean, index: Int, currentLine: Int): LineLook = when {
        !timed -> LineLook.Plain
        currentLine < 0 -> LineLook.Waiting
        index < currentLine -> LineLook.Sung
        index == currentLine -> LineLook.Current
        else -> LineLook.Waiting
    }
}

private val RiseEase = CubicBezierEasing(0.3f, 0f, 0.1f, 1f)

/**
 * The player's frame: a full-screen page that rises from the bottom (440ms) and falls back (360ms, then it is dismissed). It is a dialog window, so the mini
 * player's cover cannot travel into the print (docs/GALLERY_THEME.md G3: where a screen is not under the shared-element layout it falls back to the rise).
 * [content] gets [close] to run the fall; the system back button and the scrim-less edge use it too.
 */
@Composable
fun GalleryPlayerFrame(onDismiss: () -> Unit, content: @Composable (close: () -> Unit) -> Unit) {
    val p = LocalPalette.current
    val reduced = rememberReducedMotion()
    val visible = remember { MutableTransitionState(false).apply { targetState = true } }
    val close: () -> Unit = { visible.targetState = false }
    LaunchedEffect(visible.currentState, visible.targetState) { if (!visible.currentState && !visible.targetState) onDismiss() }
    val rise = MotionRules.duration(GalleryPlayerRules.RISE_MS, MotionFamily.Standard, reduced)
    val fall = MotionRules.duration(GalleryPlayerRules.FALL_MS, MotionFamily.Standard, reduced)
    Dialog(
        onDismissRequest = close,
        properties = DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false, dismissOnBackPress = false),
    ) {
        TransparentSystemBars(lightBars = p.light)
        AnimatedVisibility(
            visibleState = visible,
            enter = slideInVertically(tween(rise, easing = RiseEase)) { it },
            exit = slideOutVertically(tween(fall, easing = RiseEase)) { it },
        ) { content(close) }
    }
}

/** A negative top margin: the element is drawn [by] higher and the next one follows it up. */
private fun Modifier.pullUp(by: Dp): Modifier = layout { measurable, constraints ->
    val placeable = measurable.measure(constraints)
    val shift = by.roundToPx()
    layout(placeable.width, (placeable.height - shift).coerceAtLeast(0)) { placeable.place(0, -shift) }
}

/** The bar (52dp): a Down button at the left, the catalogue line centred, and the three-dot menu at the right. */
@Composable
private fun GalleryPlayerBar(title: String, onClose: () -> Unit, menu: List<Pair<String, () -> Unit>>) {
    val p = LocalPalette.current
    Box(Modifier.fillMaxWidth().statusBarsPadding().height(GalleryRules.PAGE_BAR.dp).padding(horizontal = 4.dp)) {
        GalleryIconButton(GalleryIcons.Down, "Close now playing", onClose, Modifier.align(Alignment.CenterStart))
        Text(
            title.uppercase(), style = GalleryType.catalogue, color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis,
            modifier = Modifier.align(Alignment.Center).padding(horizontal = 52.dp).semantics { heading() },
        )
        GalleryMenuButton("More", menu, Modifier.align(Alignment.CenterEnd))
    }
}

/**
 * The Gallery player: the bar, one of the three views, then the seek line and the transport that every view keeps; the player view ends with the four tools
 * (Lyrics, Queue, Equalizer, Crossfade). The mockup's heart (no favourite action on songs) is not drawn, as on every theme.
 * [onView] switches between the three views (0 player, 1 lyrics, 2 queue).
 */
@Composable
fun GalleryPlayer(
    state: PlayerUiState, controller: PlayerController, view: Int, onView: (Int) -> Unit, onClose: () -> Unit,
    onSignIn: () -> Unit, onEqualizer: () -> Unit, onCrossfade: () -> Unit,
    onOpenArtist: (QueueItem) -> Unit, onOpenAlbum: (QueueItem) -> Unit, input: CoverStackPlayerInput,
) {
    val item = state.current ?: return
    val menu = buildList {
        add((if (input.line.showLyrics) "Hide the lyric line" else "Show the lyric line") to input.line.onLyrics)
        add((if (input.line.showFacts) "Hide facts" else "Show facts") to input.line.onFacts)
        if (item.artist.isNotBlank()) add("Open artist" to { onOpenArtist(item) })
        if (item.album.isNotBlank()) add("Open album" to { onOpenAlbum(item) })
    }
    Column(Modifier.fillMaxSize().navigationBarsPadding()) {
        GalleryPlayerBar(GalleryPlayerRules.barTitle(view, item.album), onClose, menu)
        Box(Modifier.weight(1f).fillMaxWidth()) {
            when (view) {
                CoverStackPlayerRules.VIEW_LYRICS -> GalleryLyricsView(state, item, input)
                CoverStackPlayerRules.VIEW_QUEUE -> GalleryQueueView(state, controller)
                else -> GalleryNowView(state, controller, item, input, onSignIn, onOpenArtist, onOpenAlbum)
            }
        }
        GallerySeek(state, controller, input.line.peaks)
        GalleryTransport(state, controller)
        if (view == 0) GalleryTools(onView, onEqualizer, onCrossfade) else Spacer(Modifier.height(20.dp))
    }
}

// ---------------------------------------------------------------- 1. Now Playing

/** The print (300dp, 14dp mat) on the wall, then the placard: the work in Fraunces italic, "Artist — Album", and the quality tag at the right. */
@Composable
private fun GalleryNowView(
    state: PlayerUiState, controller: PlayerController, item: QueueItem, input: CoverStackPlayerInput, onSignIn: () -> Unit,
    onOpenArtist: (QueueItem) -> Unit, onOpenAlbum: (QueueItem) -> Unit,
) {
    val p = LocalPalette.current
    Column(Modifier.fillMaxSize()) {
        // The print takes the room the rest leaves, up to 300dp square and never wider than the screen less 20dp each side.
        BoxWithConstraints(Modifier.weight(1f, fill = true).fillMaxWidth().gallerySpot(p).padding(top = 14.dp), contentAlignment = Alignment.TopCenter) {
            val side = minOf(maxWidth - 40.dp, maxHeight, GalleryPlayerRules.PRINT.dp).coerceAtLeast(GalleryPlayerRules.PRINT_MIN.dp)
            GalleryPrint(side, Modifier.size(side), player = true) {
                Cover(playerArtworkUrl(item.coverUrl), Modifier.fillMaxSize(), rect = true)
            }
        }
        Row(
            Modifier.fillMaxWidth().padding(start = 24.dp, end = 24.dp, top = 24.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.Bottom,
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    item.title, style = GalleryType.work, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite; heading() },
                )
                // The artist and the album each open their own page, as on every other theme.
                Row(verticalAlignment = Alignment.CenterVertically) {
                    val body = GalleryType.body()
                    if (item.artist.isNotBlank()) Text(
                        item.artist, style = body, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f, fill = false).heightIn(min = 40.dp).clickable(onClickLabel = "Open artist", role = Role.Button) { onOpenArtist(item) }
                            .padding(top = 8.dp),
                    )
                    if (item.artist.isNotBlank() && item.album.isNotBlank()) Text(" — ", style = body, color = p.text, modifier = Modifier.padding(top = 8.dp))
                    if (item.album.isNotBlank()) Text(
                        item.album, style = body.copy(fontStyle = FontStyle.Italic), color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f, fill = false).heightIn(min = 40.dp).clickable(onClickLabel = "Open album", role = Role.Button) { onOpenAlbum(item) }
                            .padding(top = 8.dp),
                    )
                }
            }
            qualityLabel(item)?.let { GalleryTag(it, Modifier.padding(bottom = 10.dp)) }
        }
        // States the mockup does not draw, said in words: the lyric or fact line (when switched on), and the status.
        Column(Modifier.fillMaxWidth().padding(horizontal = 24.dp), horizontalAlignment = Alignment.Start) {
            if (input.line.showLyrics || input.line.showFacts) PlayerLineText(input.line.line, Modifier.padding(top = 2.dp), align = TextAlign.Start)
            if (state.status != null || state.buffering) Text(
                playerSubtitle(state), style = GalleryType.body(), color = p.text,
                modifier = Modifier.fillMaxWidth().padding(top = 4.dp).semantics { liveRegion = LiveRegionMode.Polite },
            )
            if (state.signInRequired) GalleryButton("Sign in again", { controller.dismissSignIn(); onSignIn() }, kind = GalleryButtonKind.Text)
            if (state.waitingForNetwork) GalleryButton("Retry now", controller::retryNow, kind = GalleryButtonKind.Text)
        }
    }
}

// ---------------------------------------------------------------- shared: seek, transport, tools

/** The seek line (1.5dp `edge` track, `text` played part, 10dp thumb; [SeekBar] draws it for Gallery), then DM Mono times: the position and the time left with a minus sign. */
@Composable
private fun GallerySeek(state: PlayerUiState, controller: PlayerController, peaks: FloatArray?) {
    val p = LocalPalette.current
    var dragging by remember { mutableStateOf<Float?>(null) }
    val duration = state.durationMs
    val fraction = dragging ?: if (duration > 0) (state.positionMs.toFloat() / duration).coerceIn(0f, 1f) else 0f
    val shown = if (dragging != null) (fraction * duration).toLong() else state.positionMs
    // The bar's touch area is 48dp tall with the line in its middle, the mockup's line is 16dp: pull the times up to the 4dp the mockup leaves under it.
    Column(Modifier.fillMaxWidth().padding(horizontal = 12.dp)) {
        SeekBar(
            fraction = fraction, enabled = duration > 0,
            onChange = { dragging = it },
            onFinish = { dragging?.let { controller.seekTo((it * duration).toLong()) }; dragging = null },
            modifier = Modifier.padding(top = 6.dp).semantics { contentDescription = "Seek"; stateDescription = seekDescription(shown, duration) },
            peaks = peaks,
        )
        Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp).pullUp(12.dp), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(formatTime(shown), style = GalleryType.time, color = p.textMuted)
            Text(GalleryPlayerRules.remaining(shown, duration), style = GalleryType.time, color = p.textMuted)
        }
    }
}

/** One transport glyph: 26dp in `control`, 48dp to touch; [on] adds a small `accent` mark under it (said in words too). */
@Composable
private fun TransportButton(icon: ImageVector, label: String, onClick: () -> Unit, enabled: Boolean = true, on: Boolean? = null, state: String? = null) {
    val p = LocalPalette.current
    Box(
        Modifier.size(48.dp).clip(CircleShape).clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .semantics { contentDescription = label; if (state != null) stateDescription = state },
        contentAlignment = Alignment.Center,
    ) {
        Icon(icon, null, tint = if (enabled) p.control else p.edgeStrong, modifier = Modifier.size(GalleryRules.ICON_TRANSPORT.dp))
        if (on == true) Box(Modifier.align(Alignment.BottomCenter).padding(bottom = 6.dp).size(4.dp).clip(CircleShape).background(p.accent))
    }
}

/** Shuffle, Previous, Play (68dp `control` circle, 28dp `onControl` glyph), Next, Repeat. */
@Composable
private fun GalleryTransport(state: PlayerUiState, controller: PlayerController) {
    val p = LocalPalette.current
    val shuffle = state.queue.shuffle
    val repeat = state.queue.repeat
    Row(Modifier.fillMaxWidth().padding(start = 20.dp, end = 20.dp, top = 14.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
        TransportButton(GalleryIcons.Shuffle, "Shuffle", { controller.setShuffle(!shuffle) }, on = shuffle, state = if (shuffle) "On" else "Off")
        TransportButton(GalleryIcons.Previous, "Previous song", controller::previous)
        Box(
            Modifier.size(68.dp).clip(CircleShape).background(p.control).clickable(role = Role.Button, onClick = controller::playPause)
                .semantics { contentDescription = if (state.isPlaying) "Pause" else "Play" },
            contentAlignment = Alignment.Center,
        ) { Icon(if (state.isPlaying) GalleryIcons.Pause else GalleryIcons.Play, null, tint = p.onControl, modifier = Modifier.size(28.dp)) }
        TransportButton(GalleryIcons.Next, "Next song", controller::next, enabled = state.queue.items.size > 1)
        TransportButton(
            if (repeat == RepeatMode.One) GalleryIcons.RepeatOne else GalleryIcons.Repeat, "Repeat", controller::cycleRepeat, on = repeat != RepeatMode.Off,
            state = when (repeat) { RepeatMode.Off -> "Off"; RepeatMode.All -> "Repeat all"; RepeatMode.One -> "Repeat one" },
        )
    }
}

/** The four tools under a 1dp `edge` rule: icon 22 in `control` over Manrope 600 11 in `textMuted`. Lyrics and Queue switch the view; the other two open their sheets. */
@Composable
private fun GalleryTools(onView: (Int) -> Unit, onEqualizer: () -> Unit, onCrossfade: () -> Unit) {
    Column(Modifier.fillMaxWidth().padding(start = 12.dp, end = 12.dp, top = 14.dp, bottom = 22.dp)) {
        GalleryRule()
        Row(Modifier.fillMaxWidth().padding(top = 4.dp)) {
            Tool("Lyrics", GalleryIcons.Quote) { onView(CoverStackPlayerRules.VIEW_LYRICS) }
            Tool("Queue", GalleryIcons.Queue) { onView(CoverStackPlayerRules.VIEW_QUEUE) }
            Tool("Equalizer", GalleryIcons.Tune, onEqualizer)
            Tool("Crossfade", GalleryIcons.Swap, onCrossfade)
        }
    }
}

@Composable
private fun androidx.compose.foundation.layout.RowScope.Tool(label: String, icon: ImageVector, onClick: () -> Unit) {
    val p = LocalPalette.current
    Column(
        Modifier.weight(1f).heightIn(min = 48.dp).clickable(role = Role.Button, onClick = onClick).padding(vertical = 8.dp),
        horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(5.dp),
    ) {
        Icon(icon, null, tint = p.control, modifier = Modifier.size(GalleryRules.ICON.dp))
        Text(label, style = GalleryType.barLabel(), color = p.textMuted, maxLines = 1)
    }
}

// ---------------------------------------------------------------- 3. Lyrics

/** The playing song in a small row (print 48, work, artist) with the Photos switch when the album has photos, then the lyrics in Fraunces 24/32. */
@Composable
private fun GalleryLyricsView(state: PlayerUiState, item: QueueItem, input: CoverStackPlayerInput) {
    val p = LocalPalette.current
    Column(Modifier.fillMaxSize()) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = GalleryRules.GUTTER.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(14.dp), verticalAlignment = Alignment.CenterVertically,
        ) {
            GalleryPrint(GalleryPlayerRules.ROW_PRINT.dp, Modifier.size(GalleryPlayerRules.ROW_PRINT.dp), small = true) {
                Cover(item.coverUrl.ifBlank { null }, Modifier.fillMaxSize(), rect = true)
            }
            Column(Modifier.weight(1f)) {
                Text(item.title, style = GalleryType.rowWork, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(item.artist, style = GalleryType.small(), color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            if (input.hasPhotos) Row(
                Modifier.heightIn(min = 48.dp).clickable(role = Role.Switch, onClickLabel = "Photos behind the lyrics", onClick = input.onPhotos)
                    .semantics { stateDescription = if (input.photosOn) "On" else "Off" },
                horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("Photos", style = GalleryType.small(), color = p.textMuted)
                GallerySwitch(input.photosOn)
            }
        }
        GalleryLyricsBody(input.lyricsState, input.currentLine, input.songId, input.onTryAgain, Modifier.weight(1f).fillMaxWidth())
    }
}

@Composable
private fun GalleryLyricsBody(state: LyricsUiState, currentLine: Int, songId: String, onTryAgain: () -> Unit, modifier: Modifier) {
    val p = LocalPalette.current
    Column(modifier) {
        when (state) {
            LyricsUiState.Idle, is LyricsUiState.Loading -> Message("Loading lyrics…", progress = true)
            is LyricsUiState.None -> Message("No lyrics for this song.")
            is LyricsUiState.Unsupported -> Message("Your Navidrome doesn't provide lyrics.")
            is LyricsUiState.Failed -> {
                Message(lyricsFailureText(state.problem))
                GalleryButton("Try again", onTryAgain, Modifier.padding(horizontal = 14.dp), kind = GalleryButtonKind.Text)
            }
            is LyricsUiState.Ready -> {
                if (state.savedCopy) Note("Saved copy")
                if (!state.lyrics.timed) Note("These lyrics are not timed.")
                Lines(state, currentLine, songId, Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun Message(text: String, progress: Boolean = false) {
    val p = LocalPalette.current
    Column(Modifier.fillMaxWidth().padding(horizontal = 24.dp, vertical = 32.dp)) {
        if (progress) CircularProgressIndicator(Modifier.padding(bottom = 16.dp).size(24.dp).semantics { heading() }, color = p.control, strokeWidth = 1.5.dp)
        Text(text, style = GalleryType.body(), color = p.textMuted)
    }
}

@Composable
private fun Note(text: String) {
    Text(text.uppercase(), style = GalleryType.catalogue, color = LocalPalette.current.textMuted, modifier = Modifier.padding(start = 24.dp, end = 24.dp, bottom = 8.dp))
}

/** The lyric lines (Fraunces 24/32, 16dp apart): sung lines at 80%, waiting lines at 55%, the line being sung in italic ink. A hand scroll stops following; the song changing resumes it. */
@Composable
private fun Lines(state: LyricsUiState.Ready, currentLine: Int, songId: String, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    val list = rememberLazyListState()
    var following by remember(songId) { mutableStateOf(true) }
    var scrolling by remember(songId) { mutableStateOf(false) }
    val context = LocalContext.current
    val reduceMotion = remember { Settings.Global.getFloat(context.contentResolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f) == 0f }
    val timed = state.lyrics.timed
    LaunchedEffect(songId) { snapshotFlow { list.isScrollInProgress }.collect { moving -> if (moving && !scrolling) following = false } }
    LaunchedEffect(currentLine, following, songId) {
        if (!timed || !following || currentLine < 0) return@LaunchedEffect
        scrolling = true
        try {
            val offset = -(list.layoutInfo.viewportSize.height / 3)
            if (reduceMotion) list.scrollToItem(currentLine, offset) else list.animateScrollToItem(currentLine, offset)
        } finally { scrolling = false }
    }
    val upright = GalleryType.lyric
    val italic = upright.copy(fontFamily = GalleryFaces.fraunces(400, 36f, true), fontStyle = FontStyle.Italic)
    Box(modifier.fillMaxWidth()) {
        LazyColumn(Modifier.fillMaxSize(), state = list, contentPadding = androidx.compose.foundation.layout.PaddingValues(start = 24.dp, end = 24.dp, top = 10.dp, bottom = 24.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            itemsIndexed(state.lyrics.lines) { index, line ->
                if (line.text.isBlank()) { Spacer(Modifier.height(14.dp).fillMaxWidth().clearAndSetSemantics { }); return@itemsIndexed }
                when (GalleryPlayerRules.lineLook(timed, index, currentLine)) {
                    GalleryPlayerRules.LineLook.Current -> Text(line.text, style = italic, color = p.text, modifier = Modifier.fillMaxWidth().semantics { stateDescription = "Current line" })
                    GalleryPlayerRules.LineLook.Sung -> Text(line.text, style = upright, color = p.textMuted.copy(alpha = GalleryPlayerRules.LYRIC_SUNG_ALPHA), modifier = Modifier.fillMaxWidth())
                    GalleryPlayerRules.LineLook.Waiting -> Text(line.text, style = upright, color = p.textMuted.copy(alpha = GalleryPlayerRules.LYRIC_WAITING_ALPHA), modifier = Modifier.fillMaxWidth())
                    GalleryPlayerRules.LineLook.Plain -> Text(line.text, style = upright, color = p.text, modifier = Modifier.fillMaxWidth())
                }
            }
        }
        if (timed && !following && currentLine != LyricsTimeline.NONE) {
            GalleryButton("Back to the current line", { following = true }, Modifier.align(Alignment.BottomCenter).padding(bottom = 8.dp).background(p.ink), kind = GalleryButtonKind.Outlined, small = true)
        }
    }
}

// ---------------------------------------------------------------- 2. Queue

/**
 * The playing song at the top (print 56, work, "Artist · playing, 3:12 of 9:39", the moving bars), then "Next · 5 songs" with Clear, one row per song after it
 * (tap plays it, the X removes it), and the sound-alike button. Move up, Move down and the sonic path are a long press and screen-reader actions (never drag only).
 */
@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun GalleryQueueView(state: PlayerUiState, controller: PlayerController) {
    val p = LocalPalette.current
    val items = state.queue.items
    val repo = LocalRepository.current
    val play = LocalPlayActions.current
    val sonic by produceState(false, repo) { value = withContext(Dispatchers.IO) { repo.sonicAvailable() } }
    val queuedIds = items.mapTo(HashSet()) { it.songId }
    var pathTo by remember { mutableStateOf<QueueItem?>(null) }
    pathTo?.let { target -> state.current?.let { SonicPathSheet(it, target) { pathTo = null } } }
    val playing = state.current
    val next = GalleryPlayerRules.upcoming(state.queue.index, items.size)
    val list = rememberLazyListState()
    LazyColumn(Modifier.fillMaxSize(), state = list) {
        if (state.status != null) item(key = "status") {
            Text(state.status, style = GalleryType.small(), color = p.text, modifier = Modifier.padding(horizontal = GalleryRules.GUTTER.dp, vertical = 4.dp))
        }
        if (playing != null) item(key = "playing") {
            Column(Modifier.padding(start = GalleryRules.GUTTER.dp, end = GalleryRules.GUTTER.dp, top = 4.dp)) {
                GalleryRow(
                    playing.title, sub = GalleryPlayerRules.playingLine(playing.artist, state.isPlaying, state.positionMs, state.durationMs), italicTitle = true, divider = false,
                    lead = { GalleryPrint(GalleryPlayerRules.QUEUE_NOW_PRINT.dp, Modifier.size(GalleryPlayerRules.QUEUE_NOW_PRINT.dp), small = true) { Cover(playing.coverUrl.ifBlank { null }, Modifier.fillMaxSize(), rect = true) } },
                    trail = { GalleryPlayingBars(state.isPlaying) },
                )
            }
        }
        item(key = "next") {
            Spacer(Modifier.height(18.dp))
            GallerySectionHead(
                GalleryPlayerRules.nextHeading(next.size), first = true,
                link = if (next.isNotEmpty()) "Clear" else null,
                onLink = { next.asReversed().forEach { controller.remove(it) } },
            )
        }
        if (next.isEmpty()) item(key = "none") {
            Text("Nothing after this song.", style = GalleryType.body(), color = p.textMuted, modifier = Modifier.padding(horizontal = GalleryRules.GUTTER.dp))
        }
        itemsIndexed(next, key = { _, index -> "$index-${items[index].songId}" }) { _, index ->
            val song = items[index]
            val unavailable = song.songId in state.queue.unavailable
            var menu by remember { mutableStateOf(false) }
            val move = buildList {
                if (index > 0) add("Move up" to { controller.move(index, index - 1) })
                if (index < items.lastIndex) add("Move down" to { controller.move(index, index + 1) })
                if (sonic) add("Add songs that sound like this" to { play.soundsLike(song.songId, queuedIds) })
                if (sonic && playing != null) add("Sonic path from playing song to this one" to { pathTo = song })
            }
            Box(
                Modifier.padding(horizontal = GalleryRules.GUTTER.dp)
                    .combinedClickable(onClickLabel = "Play this song", role = Role.Button, onLongClickLabel = "More actions", onLongClick = { menu = true }) { if (!unavailable) controller.skipTo(index) }
                    .semantics { customActions = move.map { (label, run) -> CustomAccessibilityAction(label) { run(); true } } },
            ) {
                GalleryRow(
                    song.title, sub = if (unavailable) "" else song.artist, italicTitle = true, minHeight = 64.dp,
                    lead = { GalleryPrint(GalleryPlayerRules.ROW_PRINT.dp, Modifier.size(GalleryPlayerRules.ROW_PRINT.dp), small = true) { Cover(song.coverUrl.ifBlank { null }, Modifier.fillMaxSize(), rect = true) } },
                    trail = {
                        if (unavailable) GalleryState("Unavailable", color = p.chartRedText)
                        GalleryIconButton(GalleryIcons.Close, "Remove ${song.title} from the queue", { controller.remove(index) }, size = 20.dp)
                    },
                )
                DropdownMenu(menu, onDismissRequest = { menu = false }) {
                    move.forEach { (label, run) -> DropdownMenuItem(text = { Text(label) }, onClick = { menu = false; run() }) }
                    DropdownMenuItem(text = { Text("Remove from queue") }, onClick = { menu = false; controller.remove(index) })
                }
            }
        }
        if (sonic && playing != null) item(key = "soundslike") {
            GalleryButton(
                "Add songs that sound like this", { play.soundsLike(playing.songId, queuedIds) },
                Modifier.padding(start = GalleryRules.GUTTER.dp, top = 6.dp), kind = GalleryButtonKind.Outlined, icon = GalleryIcons.Wave,
            )
        }
        // The playing album's Track images (docs/artwork.md, idea 6): a card each, shown only when the album has some.
        item(key = "trackimages") { TrackImageCards(trackImages(rememberAlbumArtIndex(playing)), Modifier.padding(horizontal = GalleryRules.GUTTER.dp, vertical = 12.dp)) }
    }
}
