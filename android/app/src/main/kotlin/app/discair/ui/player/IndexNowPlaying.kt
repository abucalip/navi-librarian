package app.discair.ui.player

import android.provider.Settings
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.EnterTransition
import androidx.compose.animation.ExitTransition
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.MutableTransitionState
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.gestures.Orientation
import androidx.compose.foundation.gestures.draggable
import androidx.compose.foundation.gestures.rememberDraggableState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.runtime.withFrameNanos
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.layout.layout
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.CustomAccessibilityAction
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.customActions
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
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
import app.discair.ui.common.GalleryPlayerFlight
import app.discair.ui.common.IndexButton
import app.discair.ui.common.IndexButtonKind
import app.discair.ui.common.IndexFlight
import app.discair.ui.common.IndexIconButton
import app.discair.ui.common.IndexIcons
import app.discair.ui.common.IndexLabel
import app.discair.ui.common.IndexMuted
import app.discair.ui.common.IndexPageHead
import app.discair.ui.common.IndexPlayingBars
import app.discair.ui.common.IndexRow
import app.discair.ui.common.IndexRule
import app.discair.ui.common.IndexRules
import app.discair.ui.common.IndexSectionHead
import app.discair.ui.common.IndexState
import app.discair.ui.common.IndexTag
import app.discair.ui.common.IndexType
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.TransparentSystemBars
import app.discair.ui.common.indexTones
import app.discair.ui.theme.IndexMotion
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.rememberReducedMotion
import kotlin.math.roundToInt
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/*
 * Index (Layout.Index): Now Playing, Queue and Lyrics. Spec: docs/INDEX_THEME.md step I5; mockup: docs/design/index/pages/player (three frames). Reached only
 * from NowPlayingSheet's Index branch. One full-screen page that rises from the strip (motion #8) with three views (0 player, 1 lyrics, 2 queue); every control
 * does what its Standard twin does. The live radio page uses the same frame (IndexRadio.kt).
 */

/** The pure rules of the Index player (unit-tested). Measurements are index.css (1 CSS px = 1dp). */
object IndexPlayerRules {
    /** The cover on Now Playing is the width less the gutters (328dp on the mockup's 360dp screen), and never smaller than this on a short screen. */
    const val COVER_MIN = 120

    /** Height the player view needs under the cover (a two-line title, the status or lyric line, seek, transport, tools); the cover takes what is left. */
    const val BELOW_COVER = 340
    const val QUEUE_COVER = 48
    const val PLAY_BUTTON = 64
    const val TOOL_HEIGHT = 56

    /** Lyric lines (Inter Tight 800): 22sp, the line being sung 26sp; the time stamp column is 30dp. */
    const val LYRIC_SP = 22
    const val LYRIC_CURRENT_SP = 26
    const val STAMP_COLUMN = 30

    /** "05 / 10": a place in the queue and its size, each at least two digits; empty when the queue is empty or the place unknown. */
    fun position(index: Int, size: Int): String = if (size <= 0 || index !in 0 until size) "" else "%02d / %02d".format(index + 1, size)

    /** The bar's catalogue line: "Now playing · 05 / 10", "Queue · 14", "Lyrics". */
    fun barTitle(view: Int, index: Int, size: Int): String = when (view) {
        CoverStackPlayerRules.VIEW_QUEUE -> if (size > 0) "Queue · $size" else "Queue"
        CoverStackPlayerRules.VIEW_LYRICS -> "Lyrics"
        else -> position(index, size).let { if (it.isEmpty()) "Now playing" else "Now playing · $it" }
    }

    /** A queue row's number: its place in the whole queue ("06"), so Up next continues from the playing song's place. */
    fun number(queueIndex: Int): String = "%02d".format(queueIndex + 1)

    /** The playing band's meta line: "Now · 1:37 / 3:51" ("Paused · …" while it is not playing); just the word while the length is unknown. */
    fun nowLine(playing: Boolean, positionMs: Long, durationMs: Long): String {
        val word = if (playing) "Now" else "Paused"
        return if (durationMs > 0) "$word · ${formatTime(positionMs)} / ${formatTime(durationMs)}" else word
    }

    /** An Up next row's meta line: "Khruangbin · 5:07", each part only when known. */
    fun rowMeta(artist: String, durationSec: Int): String =
        listOfNotNull(artist.trim().ifEmpty { null }, durationSec.takeIf { it > 0 }?.let { formatTime(it * 1000L) }).joinToString(" · ")

    /** The song's whole length under the seek line ("3:51"), or "--:--" while it is not known. Index shows the length, not the time left. */
    fun total(durationMs: Long): String = if (durationMs > 0) formatTime(durationMs) else "--:--"

    /** A lyric line's time stamp ("0:12"); null for an untimed line, which then has no stamp column. */
    fun stamp(startMs: Long?): String? = startMs?.let { formatTime(it) }

    /** The tools under the player: what each cell says (mono capitals) and what a screen reader says. */
    val tools: List<Pair<String, String>> = listOf("Lyrics" to "Lyrics", "Queue" to "Queue", "EQ" to "Equalizer", "Fade" to "Crossfade")
}

// ---------------------------------------------------------------- the frame (motion #8)

/**
 * The player's frame (docs/INDEX_THEME.md 8.2 #8): a full-screen page that slides up from the strip over 420ms on the Firm curve, with no fade, and back down
 * over 320ms before it is dismissed. The strip's 38dp cover flies to the player's cover: the page is a dialog window outside the shared-element layout, so the
 * flight is drawn by hand from the strip cover's bounds ([IndexFlight]), interpolating the rectangle only, square throughout. The player's own cover waits hidden
 * until the flying one lands. With no cover on screen (Queue, Lyrics, live radio) the page just rises. A downward drag lowers the page; past a quarter of the
 * screen, or on a quick flick, it falls. [content] gets `close` to run the fall; the system back button uses it too.
 */
@Composable
fun IndexPlayerFrame(onDismiss: () -> Unit, content: @Composable (close: () -> Unit) -> Unit) {
    val p = LocalPalette.current
    val reduced = rememberReducedMotion()
    val flight = IndexFlight
    val scope = rememberCoroutineScope()
    val visible = remember { MutableTransitionState(false).apply { targetState = true } }
    val close: () -> Unit = {
        if (visible.targetState) {
            visible.targetState = false
            flight.playerUp = false
            // The cover flies back to the strip while the page falls, when both ends are known.
            if (!reduced && flight.mini != null && flight.target() != null) scope.launch {
                flight.flying = true
                flight.progress.animateTo(0f, IndexMotion.firm(IndexMotion.PLAYER_FALL_MS, reduced))
            }
        }
    }
    LaunchedEffect(visible.currentState, visible.targetState) { if (!visible.currentState && !visible.targetState) onDismiss() }
    LaunchedEffect(Unit) {
        flight.playerUp = true
        if (reduced || flight.mini == null) return@LaunchedEffect
        flight.progress.snapTo(0f)
        // The cover is laid out in the page's first frame (still below the screen); the flight starts only once both ends are known.
        withFrameNanos { }
        if (flight.target() == null) { flight.progress.snapTo(1f); return@LaunchedEffect }
        flight.flying = true
        flight.progress.animateTo(1f, IndexMotion.firm(IndexMotion.PLAYER_RISE_MS, reduced))
        flight.flying = false
    }
    DisposableEffect(Unit) { onDispose { flight.playerUp = false; flight.flying = false; flight.page = null; flight.cover = null } }
    Dialog(onDismissRequest = close, properties = DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false, dismissOnBackPress = false)) {
        TransparentSystemBars(lightBars = p.light)
        Box(Modifier.fillMaxSize()) {
            AnimatedVisibility(
                visibleState = visible,
                enter = if (reduced) EnterTransition.None else slideInVertically(IndexMotion.firm(IndexMotion.PLAYER_RISE_MS, reduced)) { it },
                exit = if (reduced) ExitTransition.None else slideOutVertically(IndexMotion.firm(IndexMotion.PLAYER_FALL_MS, reduced)) { it },
            ) {
                // Swipe down lowers the page. On Queue and Lyrics the list scrolls first; once it is at its top, the rest of a downward drag lowers the page.
                val drag = remember { Animatable(0f) }
                val flickPx = with(LocalDensity.current) { 1200.dp.toPx() }
                suspend fun release(velocity: Float) {
                    val far = drag.value > (flight.page?.size?.height ?: 0) / 4f
                    if (far || velocity > flickPx) close() else drag.animateTo(0f, IndexMotion.firm(IndexMotion.SNACK_MS, reduced))
                }
                val lists = remember(drag) { dragConnection(drag, scope) { v -> release(v) } }
                Box(
                    Modifier.fillMaxSize()
                        .graphicsLayer { translationY = drag.value }
                        .nestedScroll(lists)
                        .draggable(rememberDraggableState { d -> scope.launch { drag.snapTo((drag.value + d).coerceAtLeast(0f)) } }, Orientation.Vertical, onDragStopped = { v -> release(v) })
                        .onGloballyPositioned { flight.page = it },
                ) { content(close) }
            }
            if (flight.flying) FlyingCover(flight)
        }
    }
}

/** Lists scroll first; a downward drag at a list's top lowers the page, and an upward drag lifts a lowered page before the list moves. Only a finger lowers it. */
private fun dragConnection(drag: Animatable<Float, *>, scope: kotlinx.coroutines.CoroutineScope, release: suspend (Float) -> Unit) =
    object : androidx.compose.ui.input.nestedscroll.NestedScrollConnection {
        override fun onPreScroll(available: androidx.compose.ui.geometry.Offset, source: androidx.compose.ui.input.nestedscroll.NestedScrollSource): androidx.compose.ui.geometry.Offset {
            if (drag.value <= 0f || available.y >= 0f) return androidx.compose.ui.geometry.Offset.Zero
            val used = maxOf(available.y, -drag.value)
            scope.launch { drag.snapTo(drag.value + used) }
            return androidx.compose.ui.geometry.Offset(0f, used)
        }
        override fun onPostScroll(consumed: androidx.compose.ui.geometry.Offset, available: androidx.compose.ui.geometry.Offset, source: androidx.compose.ui.input.nestedscroll.NestedScrollSource): androidx.compose.ui.geometry.Offset {
            if (available.y <= 0f || source != androidx.compose.ui.input.nestedscroll.NestedScrollSource.UserInput) return androidx.compose.ui.geometry.Offset.Zero
            scope.launch { drag.snapTo(drag.value + available.y) }
            return androidx.compose.ui.geometry.Offset(0f, available.y)
        }
        override suspend fun onPreFling(available: androidx.compose.ui.unit.Velocity): androidx.compose.ui.unit.Velocity {
            if (drag.value <= 0f) return androidx.compose.ui.unit.Velocity.Zero
            release(available.y)
            return available
        }
    }

/** The cover in flight, from the strip cover's place to the player's cover at the flight's progress: the rectangle only, square corners, no fade. */
@Composable
private fun FlyingCover(flight: GalleryPlayerFlight) {
    val from = flight.mini ?: return
    val to = flight.target() ?: return
    Box(
        Modifier.fillMaxSize().layout { measurable, constraints ->
            val r = androidx.compose.ui.geometry.lerp(from, to, flight.progress.value)
            val placeable = measurable.measure(androidx.compose.ui.unit.Constraints.fixed(r.width.roundToInt().coerceAtLeast(1), r.height.roundToInt().coerceAtLeast(1)))
            layout(constraints.maxWidth, constraints.maxHeight) { placeable.place(r.left.roundToInt(), r.top.roundToInt()) }
        },
    ) { Cover(flight.coverUrl, Modifier.fillMaxSize(), rect = true) }
}

/** A negative top margin: the element is drawn [by] higher and the next one follows it up. */
private fun Modifier.pullUp(by: Dp): Modifier = layout { measurable, constraints ->
    val placeable = measurable.measure(constraints)
    val shift = by.roundToPx()
    layout(placeable.width, (placeable.height - shift).coerceAtLeast(0)) { placeable.place(0, -shift) }
}

/** The bar (52dp): the Down button, the mono catalogue line centred, and the three dots with the player's menu. */
@Composable
internal fun IndexPlayerBar(title: String, backLabel: String, onBack: () -> Unit, menu: List<Pair<String, () -> Unit>>) {
    var open by remember { mutableStateOf(false) }
    Box(Modifier.fillMaxWidth().statusBarsPadding().height(IndexRules.PAGE_BAR.dp).padding(horizontal = 4.dp)) {
        IndexIconButton(IndexIcons.Down, backLabel, onBack, Modifier.align(Alignment.CenterStart))
        IndexLabel(title, Modifier.align(Alignment.Center).padding(horizontal = 52.dp).semantics { heading() })
        if (menu.isNotEmpty()) Box(Modifier.align(Alignment.CenterEnd)) {
            IndexIconButton(IndexIcons.More, "More", { open = true })
            DropdownMenu(open, onDismissRequest = { open = false }) {
                menu.forEach { (label, run) -> DropdownMenuItem(text = { Text(label) }, onClick = { open = false; run() }) }
            }
        }
    }
}

/**
 * The Index player: the bar, then one of the three views. The player view is a `surface` page (white on the day palettes); Queue and Lyrics sit on `ink`, as
 * the mockup draws them. [onView] switches views (0 player, 1 lyrics, 2 queue); Down on Queue or Lyrics returns to the player.
 */
@Composable
fun IndexPlayer(
    state: PlayerUiState, controller: PlayerController, view: Int, onView: (Int) -> Unit, onClose: () -> Unit,
    onSignIn: () -> Unit, onEqualizer: () -> Unit, onCrossfade: () -> Unit,
    onOpenArtist: (QueueItem) -> Unit, onOpenAlbum: (QueueItem) -> Unit, input: CoverStackPlayerInput,
) {
    val p = LocalPalette.current
    val item = state.current ?: return
    val menu = buildList {
        add((if (input.line.showLyrics) "Hide the lyric line" else "Show the lyric line") to input.line.onLyrics)
        add((if (input.line.showFacts) "Hide facts" else "Show facts") to input.line.onFacts)
        if (item.artist.isNotBlank()) add("Open artist" to { onOpenArtist(item) })
        if (item.album.isNotBlank()) add("Open album" to { onOpenAlbum(item) })
    }
    val player = view == CoverStackPlayerRules.VIEW_PLAYER
    Column(Modifier.fillMaxSize().background(if (player) p.surface else p.ink).navigationBarsPadding()) {
        IndexPlayerBar(
            IndexPlayerRules.barTitle(view, state.queue.index, state.queue.items.size), CoverStackPlayerRules.backLabel(view),
            { if (player) onClose() else onView(CoverStackPlayerRules.VIEW_PLAYER) }, menu,
        )
        Box(Modifier.weight(1f).fillMaxWidth()) {
            when (view) {
                CoverStackPlayerRules.VIEW_LYRICS -> IndexLyricsView(input)
                CoverStackPlayerRules.VIEW_QUEUE -> IndexQueueView(state, controller)
                else -> IndexNowView(state, controller, item, input, onSignIn, onOpenArtist, onOpenAlbum, onView, onEqualizer, onCrossfade)
            }
        }
    }
}

// ---------------------------------------------------------------- 1. Now Playing

/** The square cover, the title and "Artist · Album" with the quality tag, the seek line with the times, the transport, then the four tool cells at the bottom. */
@Composable
private fun IndexNowView(
    state: PlayerUiState, controller: PlayerController, item: QueueItem, input: CoverStackPlayerInput, onSignIn: () -> Unit,
    onOpenArtist: (QueueItem) -> Unit, onOpenAlbum: (QueueItem) -> Unit, onView: (Int) -> Unit, onEqualizer: () -> Unit, onCrossfade: () -> Unit,
) {
    val p = LocalPalette.current
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val side = minOf(maxWidth - (IndexRules.GUTTER * 2).dp, maxHeight - IndexPlayerRules.BELOW_COVER.dp).coerceAtLeast(IndexPlayerRules.COVER_MIN.dp)
        Column(Modifier.fillMaxSize()) {
            val flight = IndexFlight
            val url = playerArtworkUrl(item.coverUrl)
            SideEffect { flight.coverUrl = url }
            // While the cover flies in from the strip (or back), this cover waits hidden; nothing fades.
            Box(Modifier.padding(start = IndexRules.GUTTER.dp, top = 6.dp).size(side).background(p.raised)) {
                Cover(url, Modifier.fillMaxSize().onGloballyPositioned { flight.cover = it }.graphicsLayer { alpha = if (flight.flying) 0f else 1f }, rect = true)
            }
            Row(
                Modifier.fillMaxWidth().padding(start = IndexRules.GUTTER.dp, end = IndexRules.GUTTER.dp, top = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.Top,
            ) {
                Column(Modifier.weight(1f)) {
                    Text(
                        item.title, style = IndexType.display().copy(fontSize = 36.sp, lineHeight = 33.sp), color = p.text, maxLines = 2, overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite; heading() },
                    )
                    // The artist and the album each open their own page, as on every other theme.
                    Row(Modifier.padding(top = 2.dp), verticalAlignment = Alignment.CenterVertically) {
                        val body = IndexType.body()
                        if (item.artist.isNotBlank()) Text(
                            item.artist, style = body, color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.weight(1f, fill = false).heightIn(min = 32.dp).clickable(onClickLabel = "Open artist", role = Role.Button) { onOpenArtist(item) }.padding(top = 6.dp),
                        )
                        if (item.artist.isNotBlank() && item.album.isNotBlank()) Text(" · ", style = body, color = p.textMuted, modifier = Modifier.padding(top = 6.dp))
                        if (item.album.isNotBlank()) Text(
                            item.album, style = body, color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.weight(1f, fill = false).heightIn(min = 32.dp).clickable(onClickLabel = "Open album", role = Role.Button) { onOpenAlbum(item) }.padding(top = 6.dp),
                        )
                    }
                }
                qualityLabel(item)?.let { IndexTag(it, Modifier.padding(top = 6.dp)) }
            }
            // States the mockup does not draw, said in words: the lyric or fact line (when switched on), and the status.
            Column(Modifier.fillMaxWidth().padding(horizontal = IndexRules.GUTTER.dp)) {
                if (input.line.showLyrics || input.line.showFacts) PlayerLineText(input.line.line, Modifier.padding(top = 2.dp), align = androidx.compose.ui.text.style.TextAlign.Start)
                if (state.status != null || state.buffering) Text(
                    playerSubtitle(state), style = IndexType.body(), color = p.text,
                    modifier = Modifier.fillMaxWidth().padding(top = 4.dp).semantics { liveRegion = LiveRegionMode.Polite },
                )
                if (state.signInRequired) IndexButton("Sign in again", { controller.dismissSignIn(); onSignIn() }, kind = IndexButtonKind.Ghost, small = true)
                if (state.waitingForNetwork) IndexButton("Retry now", controller::retryNow, kind = IndexButtonKind.Ghost, small = true)
            }
            IndexSeek(state, controller, input.line.peaks)
            IndexTransport(state, controller)
            Spacer(Modifier.weight(1f))
            IndexTools(onView, onEqualizer, onCrossfade)
        }
    }
}

/** The seek line (a 6dp square `edge` track with the played part in `accent`; [SeekBar] draws it for Index), then the position and the length in the numeral face. */
@Composable
private fun IndexSeek(state: PlayerUiState, controller: PlayerController, peaks: FloatArray?) {
    val p = LocalPalette.current
    var dragging by remember { mutableStateOf<Float?>(null) }
    val duration = state.durationMs
    val fraction = dragging ?: if (duration > 0) (state.positionMs.toFloat() / duration).coerceIn(0f, 1f) else 0f
    val shown = if (dragging != null) (fraction * duration).toLong() else state.positionMs
    Column(Modifier.fillMaxWidth().padding(horizontal = 4.dp).padding(top = 6.dp)) {
        SeekBar(
            fraction = fraction, enabled = duration > 0,
            onChange = { dragging = it },
            onFinish = { dragging?.let { controller.seekTo((it * duration).toLong()) }; dragging = null },
            modifier = Modifier.semantics { contentDescription = "Seek"; stateDescription = seekDescription(shown, duration) },
            peaks = peaks,
        )
        // The bar's touch area is 48dp tall with the line in its middle; the mockup sets the times 6dp under the line. A waveform fills the area, so the times stay under it.
        Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp).pullUp(if (peaks == null) 14.dp else 0.dp).clearAndSetSemantics { }, horizontalArrangement = Arrangement.SpaceBetween) {
            Text(formatTime(shown), style = IndexType.time(), color = p.text)
            Text(IndexPlayerRules.total(duration), style = IndexType.time(), color = p.textMuted)
        }
    }
}

/** One transport glyph: 22dp in `text`, 48dp to touch; [on] draws it in `accent` with a 3dp `accent` mark under it (said in words too). */
@Composable
private fun RowScope.TransportButton(icon: ImageVector, label: String, onClick: () -> Unit, enabled: Boolean = true, on: Boolean? = null, state: String? = null) {
    val p = LocalPalette.current
    Box(Modifier.weight(1f), contentAlignment = Alignment.Center) {
        Box(
            Modifier.size(IndexRules.TOUCH_MIN.dp).clickable(enabled = enabled, role = Role.Button, onClick = onClick)
                .semantics { contentDescription = label; if (state != null) stateDescription = state },
            contentAlignment = Alignment.Center,
        ) {
            Icon(icon, null, tint = if (!enabled) p.edgeStrong else if (on == true) p.accent else p.text, modifier = Modifier.size(IndexRules.ICON.dp))
            if (on == true) Box(Modifier.align(Alignment.BottomCenter).padding(bottom = 6.dp).size(width = 14.dp, height = 3.dp).background(p.accent))
        }
    }
}

/** Shuffle, Previous, Play (a 64dp `control` square, radius 3, with an `onControl` glyph), Next, Repeat, in five equal cells. */
@Composable
private fun IndexTransport(state: PlayerUiState, controller: PlayerController) {
    val p = LocalPalette.current
    val shuffle = state.queue.shuffle
    val repeat = state.queue.repeat
    Row(Modifier.fillMaxWidth().padding(start = IndexRules.GUTTER.dp, end = IndexRules.GUTTER.dp, top = 10.dp), verticalAlignment = Alignment.CenterVertically) {
        TransportButton(IndexIcons.Shuffle, "Shuffle", { controller.setShuffle(!shuffle) }, on = shuffle, state = if (shuffle) "On" else "Off")
        TransportButton(IndexIcons.Previous, "Previous song", controller::previous)
        Box(Modifier.weight(1f), contentAlignment = Alignment.Center) {
            Box(
                Modifier.size(IndexPlayerRules.PLAY_BUTTON.dp).clip(RoundedCornerShape(IndexRules.BUTTON_RADIUS.dp)).background(p.control)
                    .clickable(role = Role.Button, onClick = controller::playPause).semantics { contentDescription = if (state.isPlaying) "Pause" else "Play" },
                contentAlignment = Alignment.Center,
            ) { Icon(if (state.isPlaying) IndexIcons.Pause else IndexIcons.Play, null, tint = p.onControl, modifier = Modifier.size(IndexRules.ICON.dp)) }
        }
        TransportButton(IndexIcons.Next, "Next song", controller::next, enabled = state.queue.items.size > 1)
        TransportButton(
            if (repeat == RepeatMode.One) IndexIcons.RepeatOne else IndexIcons.Repeat, "Repeat", controller::cycleRepeat, on = repeat != RepeatMode.Off,
            state = when (repeat) { RepeatMode.Off -> "Off"; RepeatMode.All -> "Repeat all"; RepeatMode.One -> "Repeat one" },
        )
    }
}

/** The four tool cells along the bottom (56dp, a 1dp `edge` rule above and between them): an 18dp icon over a mono word. Lyrics and Queue switch the view; EQ and Fade open their sheets. */
@Composable
private fun IndexTools(onView: (Int) -> Unit, onEqualizer: () -> Unit, onCrossfade: () -> Unit) {
    val p = LocalPalette.current
    val actions = listOf({ onView(CoverStackPlayerRules.VIEW_LYRICS) }, { onView(CoverStackPlayerRules.VIEW_QUEUE) }, onEqualizer, onCrossfade)
    val icons = listOf(IndexIcons.Quote, IndexIcons.Queue, IndexIcons.Tune, IndexIcons.Swap)
    Column(Modifier.fillMaxWidth()) {
        IndexRule()
        Row(Modifier.fillMaxWidth().height(IndexPlayerRules.TOOL_HEIGHT.dp)) {
            IndexPlayerRules.tools.forEachIndexed { i, (word, spoken) ->
                Column(
                    Modifier.weight(1f).fillMaxHeight().clickable(role = Role.Button, onClick = actions[i]).semantics(mergeDescendants = true) { contentDescription = spoken },
                    horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(4.dp, Alignment.CenterVertically),
                ) {
                    Icon(icons[i], null, tint = p.text, modifier = Modifier.size(IndexRules.ICON_INLINE.dp))
                    Text(word.uppercase(), style = IndexType.label(), color = p.text, maxLines = 1, modifier = Modifier.clearAndSetSemantics { })
                }
                if (i < IndexPlayerRules.tools.lastIndex) Box(Modifier.width(1.dp).fillMaxHeight().background(p.edge))
            }
        }
    }
}

// ---------------------------------------------------------------- 3. Lyrics

/** The lyrics on `ink`: a mono time stamp column (the current line's in `accent`) beside each line in Inter Tight; a 1dp `edge` rule under each. Untimed lyrics have no stamps. */
@Composable
private fun IndexLyricsView(input: CoverStackPlayerInput) {
    val state = input.lyricsState
    Column(Modifier.fillMaxSize()) {
        when (state) {
            LyricsUiState.Idle, is LyricsUiState.Loading -> Message("Loading lyrics…", progress = true)
            is LyricsUiState.None -> Message("No lyrics for this song.")
            is LyricsUiState.Unsupported -> Message("Your Navidrome doesn't provide lyrics.")
            is LyricsUiState.Failed -> {
                Message(lyricsFailureText(state.problem))
                IndexButton("Try again", input.onTryAgain, Modifier.padding(horizontal = IndexRules.GUTTER.dp), kind = IndexButtonKind.Ghost, small = true)
            }
            is LyricsUiState.Ready -> {
                if (state.savedCopy) Note("Saved copy")
                if (!state.lyrics.timed) Note("These lyrics are not timed.")
                Lines(state, input.currentLine, input.songId, Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun Message(text: String, progress: Boolean = false) {
    Column(Modifier.fillMaxWidth().padding(horizontal = IndexRules.GUTTER.dp, vertical = 24.dp)) {
        if (progress) CircularProgressIndicator(Modifier.padding(bottom = 16.dp).size(24.dp), color = LocalPalette.current.accent, strokeWidth = 2.dp)
        IndexMuted(text)
    }
}

@Composable
private fun Note(text: String) = IndexLabel(text, Modifier.padding(start = IndexRules.GUTTER.dp, end = IndexRules.GUTTER.dp, top = 8.dp))

/** The lines: a hand scroll stops following the song; the song changing resumes it, and so does "Back to the current line". */
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
    val line = IndexType.section().copy(fontSize = IndexPlayerRules.LYRIC_SP.sp, lineHeight = 24.sp)
    val current = line.copy(fontSize = IndexPlayerRules.LYRIC_CURRENT_SP.sp, lineHeight = 29.sp)
    Box(modifier.fillMaxWidth()) {
        LazyColumn(Modifier.fillMaxSize(), state = list, contentPadding = PaddingValues(start = IndexRules.GUTTER.dp, end = IndexRules.GUTTER.dp, top = 8.dp, bottom = 24.dp)) {
            itemsIndexed(state.lyrics.lines) { index, lyric ->
                if (lyric.text.isBlank()) { Spacer(Modifier.height(14.dp).fillMaxWidth().clearAndSetSemantics { }); return@itemsIndexed }
                val look = GalleryPlayerRules.lineLook(timed, index, currentLine)
                val stamp = if (timed) IndexPlayerRules.stamp(lyric.startMs) else null
                Column(Modifier.fillMaxWidth()) {
                    Row(Modifier.fillMaxWidth().padding(vertical = 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                        if (timed) Box(Modifier.width(IndexPlayerRules.STAMP_COLUMN.dp).clearAndSetSemantics { }) {
                            if (stamp != null) Text(stamp, style = IndexType.label(), color = if (look == GalleryPlayerRules.LineLook.Current) p.accent else p.textMuted, maxLines = 1)
                        }
                        when (look) {
                            GalleryPlayerRules.LineLook.Current -> Text(lyric.text, style = current, color = p.text, modifier = Modifier.weight(1f).semantics { stateDescription = "Current line" })
                            GalleryPlayerRules.LineLook.Plain -> Text(lyric.text, style = line, color = p.text, modifier = Modifier.weight(1f))
                            else -> Text(lyric.text, style = line, color = p.textMuted, modifier = Modifier.weight(1f))
                        }
                    }
                    IndexRule()
                }
            }
        }
        if (timed && !following && currentLine != LyricsTimeline.NONE) {
            IndexButton("Back to the current line", { following = true }, Modifier.align(Alignment.BottomCenter).padding(bottom = 8.dp).background(p.ink), kind = IndexButtonKind.Ghost, small = true)
        }
    }
}

// ---------------------------------------------------------------- 2. Queue

/**
 * "Queue" with its count, the playing song in a band of the strip colour (cover, title, "Now · 1:37 / 3:51", the playing bars), then "Up next" with Clear and one
 * numbered row per song after it: a tap plays it, the three dots (and a long press, and the screen reader's actions) hold Move up, Move down, the sound-alike
 * and sonic path actions and Remove. The sound-alike button and the album's track images stay under the list.
 */
@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun IndexQueueView(state: PlayerUiState, controller: PlayerController) {
    val p = LocalPalette.current
    val tones = indexTones()
    val items = state.queue.items
    val repo = LocalRepository.current
    val play = LocalPlayActions.current
    val sonic by produceState(false, repo) { value = withContext(Dispatchers.IO) { repo.sonicAvailable() } }
    val queuedIds = items.mapTo(HashSet()) { it.songId }
    var pathTo by remember { mutableStateOf<QueueItem?>(null) }
    pathTo?.let { target -> state.current?.let { SonicPathSheet(it, target) { pathTo = null } } }
    val playing = state.current
    val next = GalleryPlayerRules.upcoming(state.queue.index, items.size)
    LazyColumn(Modifier.fillMaxSize()) {
        item(key = "head") { IndexPageHead("Queue", count = items.size.takeIf { it > 0 }?.toString()) }
        if (state.status != null) item(key = "status") {
            IndexMuted(state.status, Modifier.padding(horizontal = IndexRules.GUTTER.dp, vertical = 6.dp).semantics { liveRegion = LiveRegionMode.Polite })
        }
        if (playing != null) item(key = "playing") {
            Row(
                Modifier.padding(start = IndexRules.GUTTER.dp, end = IndexRules.GUTTER.dp, top = 12.dp).fillMaxWidth().background(tones.strip).padding(horizontal = 12.dp, vertical = 10.dp)
                    .semantics(mergeDescendants = true) {},
                horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
            ) {
                Cover(playing.coverUrl.ifBlank { null }, Modifier.size(IndexPlayerRules.QUEUE_COVER.dp), rect = true)
                Column(Modifier.weight(1f)) {
                    Text(playing.title, style = IndexType.rowTitle(), color = tones.onStrip, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    IndexLabel(IndexPlayerRules.nowLine(state.isPlaying, state.positionMs, state.durationMs), color = tones.stripMuted)
                }
                IndexPlayingBars(state.isPlaying, Modifier.padding(end = 4.dp))
            }
        }
        item(key = "next") {
            IndexSectionHead("Up next", link = if (next.isNotEmpty()) "Clear" else null, onLink = { next.asReversed().forEach { controller.remove(it) } })
        }
        if (next.isEmpty()) item(key = "none") { IndexMuted("Nothing after this song.", Modifier.padding(horizontal = IndexRules.GUTTER.dp)) }
        itemsIndexed(next, key = { _, index -> "$index-${items[index].songId}" }) { _, index ->
            val song = items[index]
            val unavailable = song.songId in state.queue.unavailable
            var menu by remember { mutableStateOf(false) }
            val actions = buildList {
                if (index > 0) add("Move up" to { controller.move(index, index - 1) })
                if (index < items.lastIndex) add("Move down" to { controller.move(index, index + 1) })
                if (sonic) add("Add songs that sound like this" to { play.soundsLike(song.songId, queuedIds) })
                if (sonic && playing != null) add("Sonic path from playing song to this one" to { pathTo = song })
                add("Remove from queue" to { controller.remove(index) })
            }
            Box(
                Modifier.padding(horizontal = IndexRules.GUTTER.dp)
                    .combinedClickable(onClickLabel = "Play this song", role = Role.Button, onLongClickLabel = "More actions", onLongClick = { menu = true }) { if (!unavailable) controller.skipTo(index) }
                    .semantics { customActions = actions.map { (label, run) -> CustomAccessibilityAction(label) { run(); true } } },
            ) {
                IndexRow(
                    song.title, meta = IndexPlayerRules.rowMeta(song.artist, song.durationSec), number = IndexPlayerRules.number(index),
                    lead = { Cover(song.coverUrl.ifBlank { null }, Modifier.size(IndexPlayerRules.QUEUE_COVER.dp), rect = true) },
                    trail = {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            if (unavailable) IndexState("Unavailable", color = p.chartRedText)
                            Box {
                                IndexIconButton(IndexIcons.More, "More for ${song.title}", { menu = true }, tint = p.textMuted, size = 18.dp)
                                DropdownMenu(menu, onDismissRequest = { menu = false }) {
                                    actions.forEach { (label, run) -> DropdownMenuItem(text = { Text(label) }, onClick = { menu = false; run() }) }
                                }
                            }
                        }
                    },
                )
            }
        }
        if (sonic && playing != null) item(key = "soundslike") {
            IndexButton(
                "Add songs that sound like this", { play.soundsLike(playing.songId, queuedIds) },
                Modifier.padding(start = IndexRules.GUTTER.dp, top = 14.dp), kind = IndexButtonKind.Ghost, icon = IndexIcons.Wave, small = true,
            )
        }
        // The playing album's Track images (docs/artwork.md, idea 6): a card each, shown only when the album has some.
        item(key = "trackimages") { TrackImageCards(trackImages(rememberAlbumArtIndex(playing)), Modifier.padding(horizontal = IndexRules.GUTTER.dp, vertical = 12.dp)) }
    }
}
