package app.discair.ui.player

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.wrapContentHeight
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import app.discair.player.PlayerController
import app.discair.player.PlayerUiState
import app.discair.player.QueueItem
import app.discair.player.RepeatMode
import app.discair.player.qualityLabel
import app.discair.ui.common.Cover
import app.discair.ui.common.CoverStackDivider
import app.discair.ui.common.CoverStackRules
import app.discair.ui.common.Target
import app.discair.ui.common.coverStackFrame
import app.discair.ui.common.coverStackShadow
import app.discair.ui.theme.LocalFontPair
import app.discair.ui.theme.LocalPalette
import app.discair.lyrics.LyricsUiState
import app.discair.ui.common.LocalRepository
import app.discair.model.trackImages
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.withContext

/*
 * Soft Brut (Layout.CoverStack): Now Playing, Queue and Lyrics. Mockup: soft-brut/player. Reached only from NowPlayingSheet's
 * CoverStack branch; no other theme draws any of this. Every control does what its Standard twin does.
 */

/** The pure rules of the Cover Stack player (unit-tested). */
object CoverStackPlayerRules {
    const val VIEW_PLAYER = 0
    const val VIEW_LYRICS = 1
    const val VIEW_QUEUE = 2

    /** The word in the top bar's middle (mockup: "Now playing", "Queue", "Lyrics"). */
    fun frameTitle(view: Int): String = when (view) { VIEW_QUEUE -> "Queue"; VIEW_LYRICS -> "Lyrics"; else -> "Now playing" }

    /** The left button closes the sheet on the player and goes back to it from the Queue and the Lyrics. */
    fun backLabel(view: Int): String = if (view == VIEW_PLAYER) "Close now playing" else "Back to now playing"

    /** Positions after the playing song, in order (the mockup's "Next up"). */
    fun nextUp(size: Int, index: Int): List<Int> = if (size <= 0) emptyList() else ((index + 1) until size).toList()

    /** Positions before the playing song; a state the mockup does not draw, so they stay reachable (listed in the PR). */
    fun earlier(size: Int, index: Int): List<Int> = if (size <= 0) emptyList() else (0 until index.coerceIn(0, size)).toList()

    fun songs(count: Int) = "$count ${if (count == 1) "song" else "songs"}"

    /** The eyebrow over the list: "Next up · 5 songs". */
    fun nextUpLabel(count: Int) = "Next up · ${songs(count)}"
}

private val Mono @Composable get() = LocalFontPair.current.mono

/** JetBrains Mono 500 11, caps, +0.08em, muted (mockup `.eb`). */
@Composable
private fun Eyebrow(text: String, modifier: Modifier = Modifier, heading: Boolean = false) {
    Text(
        text.uppercase(), modifier.then(if (heading) Modifier.semantics { heading() } else Modifier), color = LocalPalette.current.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis,
        style = MaterialTheme.typography.labelSmall.copy(fontFamily = Mono, fontSize = 11.sp, lineHeight = 16.sp, fontWeight = FontWeight.Medium, letterSpacing = 0.08.em),
    )
}

/** A cover with the 1.5dp outline, radius 6 (or [radius]); [shadow] is the hard shadow in dp (the large cover has one). */
@Composable
private fun OutlinedCover(item: QueueItem, size: Int, modifier: Modifier = Modifier, radius: Int = 6, onColor: ((Color) -> Unit)? = null, url: String = item.coverUrl.ifBlank { "" }) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(radius.dp)
    Box(modifier.size(size.dp).clip(shape).border(CoverStackRules.outline(p).dp, p.edgeStrong, shape)) {
        Cover(url.ifBlank { null }, Modifier.fillMaxSize(), rect = true, onColor = onColor)
    }
}

/**
 * One Cover Stack button: surface (or accent) fill, ink outline, hard shadow; pressed it moves onto its shadow. [flat] draws only the
 * glyph (the mockup's Shuffle and Repeat); a flat button that is on is filled and outlined so the state is not colour alone.
 */
@Composable
private fun CsButton(
    label: String, size: Int, onClick: () -> Unit, modifier: Modifier = Modifier, radius: Int = 10, primary: Boolean = false, flat: Boolean = false,
    on: Boolean = false, enabled: Boolean = true, state: String? = null, icon: @Composable (Color) -> Unit,
) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(radius.dp)
    val source = remember { MutableInteractionSource() }
    val pressed by source.collectIsPressedAsState()
    val drop = if (pressed && enabled && !flat) CoverStackRules.shadow(p).dp else 0.dp
    val filled = primary || on
    val fill = if (!enabled) p.raised else if (filled) p.accent else p.surface
    val ink = if (!enabled) p.textMuted else if (filled) p.onAccent else p.text
    val framed = !flat || on
    Box(
        modifier.size(size.dp).offset { IntOffset(drop.roundToPx(), drop.roundToPx()) }
            .then(if (framed && !flat && drop == 0.dp && enabled) Modifier.coverStackShadow(shape, p) else Modifier)
            .clip(shape)
            .then(if (framed) Modifier.background(fill).border(CoverStackRules.outline(p).dp, p.edgeStrong, shape) else Modifier)
            .clickable(enabled = enabled, interactionSource = source, indication = null, role = Role.Button, onClick = onClick)
            .semantics { contentDescription = label; if (state != null) stateDescription = state },
        contentAlignment = Alignment.Center,
    ) { icon(ink) }
}

/** The top bar: close or back at the left, the view's name in the middle, a three-dot menu at the right (mockup `.bar`). */
@Composable
private fun TopBar(view: Int, onBack: () -> Unit, menu: List<Pair<String, () -> Unit>>) {
    val p = LocalPalette.current
    Row(Modifier.fillMaxWidth().heightIn(min = 48.dp), verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(Target).clip(CircleShape).clickable(role = Role.Button, onClick = onBack), contentAlignment = Alignment.Center) {
            Icon(if (view == CoverStackPlayerRules.VIEW_PLAYER) PlayerIcons.Down else PlayerIcons.Left, contentDescription = CoverStackPlayerRules.backLabel(view), tint = p.text)
        }
        Box(Modifier.weight(1f), contentAlignment = Alignment.Center) { Eyebrow(CoverStackPlayerRules.frameTitle(view), heading = true) }
        var open by remember { mutableStateOf(false) }
        Box {
            Box(Modifier.size(Target).clip(CircleShape).clickable(role = Role.Button) { open = true }, contentAlignment = Alignment.Center) {
                Icon(Icons.Default.MoreVert, contentDescription = "More", tint = p.text)
            }
            DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
                menu.forEach { (label, run) -> DropdownMenuItem(text = { Text(label) }, onClick = { open = false; run() }) }
            }
        }
    }
}

/** The outlined seek bar with a block thumb, and the two times under it (mockup `.seek` and `.num`). */
@Composable
private fun SeekRow(state: PlayerUiState, controller: PlayerController, peaks: FloatArray? = null) {
    val p = LocalPalette.current
    var dragging by remember { mutableStateOf<Float?>(null) }
    val duration = state.durationMs
    val fraction = dragging ?: if (duration > 0) (state.positionMs.toFloat() / duration).coerceIn(0f, 1f) else 0f
    val shown = if (dragging != null) (fraction * duration).toLong() else state.positionMs
    val timeStyle = MaterialTheme.typography.labelSmall.copy(fontFamily = Mono, fontSize = 12.sp)
    Column(Modifier.fillMaxWidth()) {
        SeekBar(
            fraction = fraction, enabled = duration > 0,
            onChange = { dragging = it },
            onFinish = { dragging?.let { controller.seekTo((it * duration).toLong()) }; dragging = null },
            modifier = Modifier.semantics { contentDescription = "Seek"; stateDescription = seekDescription(shown, duration) },
            peaks = peaks,
        )
        Row(Modifier.fillMaxWidth().padding(horizontal = 4.dp), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(formatTime(shown), style = timeStyle, color = p.textMuted)
            Text(if (duration > 0) formatTime(duration) else "--:--", style = timeStyle, color = p.textMuted)
        }
    }
}

/** Shuffle and Repeat flat, Previous and Next outlined 48, Play a 68 lavender block (mockup `.ctl`). */
@Composable
private fun Transport(state: PlayerUiState, controller: PlayerController) {
    val shuffle = state.queue.shuffle
    val repeat = state.queue.repeat
    Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
        CsButton("Shuffle", 48, { controller.setShuffle(!shuffle) }, flat = true, on = shuffle, state = if (shuffle) "On" else "Off") { Icon(PlayerIcons.Shuffle, null, tint = it) }
        CsButton("Previous song", 48, controller::previous) { Icon(PlayerIcons.Previous, null, tint = it) }
        CsButton(if (state.isPlaying) "Pause" else "Play", 68, controller::playPause, radius = 14, primary = true) {
            Icon(if (state.isPlaying) PlayerIcons.Pause else PlayerIcons.Play, null, tint = it, modifier = Modifier.size(32.dp))
        }
        CsButton("Next song", 48, controller::next, enabled = state.queue.items.size > 1) { Icon(PlayerIcons.Next, null, tint = it) }
        CsButton(
            "Repeat", 48, controller::cycleRepeat, flat = true, on = repeat != RepeatMode.Off,
            state = when (repeat) { RepeatMode.Off -> "Off"; RepeatMode.All -> "Repeat all"; RepeatMode.One -> "Repeat one" },
        ) { Icon(if (repeat == RepeatMode.One) PlayerIcons.RepeatOne else PlayerIcons.Repeat, null, tint = it) }
    }
}

/** What the Now Playing sheet hands the Cover Stack player besides the player itself. */
class CoverStackPlayerInput(
    val lyricsState: LyricsUiState, val currentLine: Int, val songId: String, val onTryAgain: () -> Unit,
    val line: LineUi, val hasPhotos: Boolean, val photosOn: Boolean, val onPhotos: () -> Unit,
)

/**
 * The whole Cover Stack player for the three views (0 player, 1 lyrics, 2 queue). The sheet's own top row is not drawn for this theme;
 * [TopBar] replaces it. [onBack] closes the sheet from the player and returns to it from the other two.
 */
@Composable
fun CoverStackPlayer(
    state: PlayerUiState, controller: PlayerController, view: Int, onView: (Int) -> Unit, onClose: () -> Unit,
    onSignIn: () -> Unit, onEqualizer: () -> Unit, onCrossfade: () -> Unit,
    onOpenArtist: (QueueItem) -> Unit, onOpenAlbum: (QueueItem) -> Unit, onCoverColor: (Color) -> Unit,
    input: CoverStackPlayerInput, photos: @Composable androidx.compose.foundation.layout.BoxScope.() -> Unit,
) {
    val item = state.current ?: return
    val menu = buildList {
        add((if (input.line.showLyrics) "Hide the lyric line" else "Show the lyric line") to input.line.onLyrics)
        add((if (input.line.showFacts) "Hide facts" else "Show facts") to input.line.onFacts)
        if (item.artist.isNotBlank()) add("Open artist" to { onOpenArtist(item) })
        if (item.album.isNotBlank()) add("Open album" to { onOpenAlbum(item) })
    }
    Column(Modifier.fillMaxWidth().fillMaxHeight()) {
        TopBar(view, onBack = { if (view == CoverStackPlayerRules.VIEW_PLAYER) onClose() else onView(CoverStackPlayerRules.VIEW_PLAYER) }, menu = menu)
        when (view) {
            CoverStackPlayerRules.VIEW_QUEUE -> QueueView(state, controller)
            CoverStackPlayerRules.VIEW_LYRICS -> LyricsView(state, controller, item, input, photos)
            else -> NowPlayingView(state, controller, item, onView, onSignIn, onEqualizer, onCrossfade, onOpenArtist, onOpenAlbum, onCoverColor, input)
        }
    }
}

@Composable
private fun ColumnScope.NowPlayingView(
    state: PlayerUiState, controller: PlayerController, item: QueueItem, onView: (Int) -> Unit, onSignIn: () -> Unit,
    onEqualizer: () -> Unit, onCrossfade: () -> Unit, onOpenArtist: (QueueItem) -> Unit, onOpenAlbum: (QueueItem) -> Unit,
    onCoverColor: (Color) -> Unit, input: CoverStackPlayerInput,
) {
    val p = LocalPalette.current
    val coverShape = RoundedCornerShape(14.dp)
    Column(Modifier.weight(1f, fill = true).fillMaxWidth().verticalScroll(rememberScrollState())) {
        // The large cover: 296dp, 1.5dp outline, radius 14, a 5dp hard shadow.
        Box(Modifier.fillMaxWidth().padding(top = 4.dp, bottom = 12.dp), contentAlignment = Alignment.Center) {
            Box(
                Modifier.widthIn(max = 296.dp).fillMaxWidth().aspectRatio(1f).coverStackShadow(coverShape, p, 5f).clip(coverShape)
                    .border(CoverStackRules.outline(p).dp, p.edgeStrong, coverShape),
            ) { Cover(playerArtworkUrl(item.coverUrl), Modifier.fillMaxSize(), rect = true, onColor = onCoverColor) }
        }
        Column(Modifier.fillMaxWidth()) {
            Text(
                item.title, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis,
                style = MaterialTheme.typography.headlineLarge.copy(fontSize = 26.sp, lineHeight = 30.sp, fontWeight = FontWeight.Bold),
                modifier = Modifier.fillMaxWidth().semantics { liveRegion = LiveRegionMode.Polite; heading() },
            )
            // The artist and the album each open their own page, as on every other theme.
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                val link = MaterialTheme.typography.bodyMedium
                if (item.artist.isNotBlank()) Text(
                    item.artist, style = link, color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f, fill = false).heightIn(min = Target).clickable(onClickLabel = "Open artist", role = Role.Button) { onOpenArtist(item) }.wrapContentHeight(Alignment.CenterVertically),
                )
                if (item.artist.isNotBlank() && item.album.isNotBlank()) Text(" · ", style = link, color = p.textMuted)
                if (item.album.isNotBlank()) Text(
                    item.album, style = link, color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f, fill = false).heightIn(min = Target).clickable(onClickLabel = "Open album", role = Role.Button) { onOpenAlbum(item) }.wrapContentHeight(Alignment.CenterVertically),
                )
            }
            // The quality tag: mono caps in an outlined radius-6 tag (the theme's tag recipe, on the surface fill).
            qualityLabel(item)?.let {
                Text(
                    it.uppercase(), color = p.text, maxLines = 1,
                    style = MaterialTheme.typography.labelSmall.copy(fontFamily = Mono, fontSize = 10.sp, lineHeight = 14.sp, fontWeight = FontWeight.Medium, letterSpacing = 0.07.em),
                    modifier = Modifier.padding(top = 2.dp, bottom = 4.dp).clip(RoundedCornerShape(6.dp)).background(p.accentDim)
                        .border(CoverStackRules.outline(p).dp, p.edgeStrong, RoundedCornerShape(6.dp)).padding(horizontal = 7.dp, vertical = 2.dp),
                )
            }
            // States the mockup does not draw, said in words: the lyric or fact line (when switched on), and the status.
            if (input.line.showLyrics || input.line.showFacts) PlayerLineText(input.line.line, Modifier.padding(top = 2.dp), align = TextAlign.Start)
            if (state.status != null || state.buffering) Text(
                playerSubtitle(state), style = MaterialTheme.typography.bodyMedium, color = p.text, modifier = Modifier.fillMaxWidth().padding(top = 4.dp).semantics { liveRegion = LiveRegionMode.Polite },
            )
            if (state.signInRequired) TextButton(onClick = { controller.dismissSignIn(); onSignIn() }, Modifier.heightIn(min = Target)) { Text("Sign in again", color = p.text, textDecoration = TextDecoration.Underline) }
            if (state.waitingForNetwork) TextButton(onClick = controller::retryNow, Modifier.heightIn(min = Target)) { Text("Retry now", color = p.text, textDecoration = TextDecoration.Underline) }
        }
        Spacer(Modifier.height(14.dp))
        SeekRow(state, controller, input.line.peaks)
        Transport(state, controller)
    }
    // The four entries under the transport: Queue, Lyrics, Equalizer and Crossfade (the mockup's Sonic path has no Now Playing action).
    Row(Modifier.fillMaxWidth().padding(top = 8.dp, bottom = 12.dp), horizontalArrangement = Arrangement.SpaceAround) {
        Entry("Queue", PlayerIcons.List) { onView(CoverStackPlayerRules.VIEW_QUEUE) }
        Entry("Lyrics", PlayerIcons.Quote) { onView(CoverStackPlayerRules.VIEW_LYRICS) }
        Entry("Equalizer", PlayerIcons.Tune, onEqualizer)
        Entry("Crossfade", PlayerIcons.Swap, onCrossfade)
    }
}

/** An icon over a small muted label, at least 48dp to touch (mockup: the row under the transport). */
@Composable
private fun Entry(label: String, icon: ImageVector, onClick: () -> Unit) {
    val p = LocalPalette.current
    Column(
        Modifier.widthIn(min = 64.dp).heightIn(min = 52.dp).clip(RoundedCornerShape(8.dp)).clickable(role = Role.Button, onClick = onClick).padding(horizontal = 6.dp, vertical = 4.dp)
            .semantics(mergeDescendants = true) { contentDescription = label },
        horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center,
    ) {
        Icon(icon, contentDescription = null, tint = p.textMuted, modifier = Modifier.size(24.dp))
        Text(label, style = MaterialTheme.typography.labelSmall.copy(fontSize = 12.sp), color = p.textMuted, maxLines = 1, modifier = Modifier.clearAndSetSemantics { })
    }
}

/** The playing song at the top of the Queue and Lyrics: a 56dp cover, then the eyebrow, title and artist (mockup). */
@Composable
private fun PlayingHeader(item: QueueItem, eyebrow: String?, trailing: @Composable () -> Unit = {}) {
    val p = LocalPalette.current
    Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        OutlinedCover(item, 56)
        Column(Modifier.weight(1f)) {
            if (eyebrow != null) Eyebrow(eyebrow)
            Text(item.title, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold), modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
            Text(item.artist, color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall)
        }
        trailing()
    }
}

/** The mockup's Queue: the playing song, "Next up", rows with a remove X, "Add songs that sound like this", then the seek bar and transport. */
@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun ColumnScope.QueueView(state: PlayerUiState, controller: PlayerController) {
    val p = LocalPalette.current
    val items = state.queue.items
    val playing = state.current ?: return
    val repo = LocalRepository.current
    val play = LocalPlayActions.current
    val sonic by produceState(false, repo) { value = withContext(Dispatchers.IO) { repo.sonicAvailable() } }
    val queuedIds = items.mapTo(HashSet()) { it.songId }
    var pathTo by remember { mutableStateOf<QueueItem?>(null) }
    pathTo?.let { target -> SonicPathSheet(playing, target) { pathTo = null } }
    val next = CoverStackPlayerRules.nextUp(items.size, state.queue.index)
    val earlier = CoverStackPlayerRules.earlier(items.size, state.queue.index)

    PlayingHeader(playing, "Playing")
    if (state.status != null) Text(state.status, style = MaterialTheme.typography.bodySmall, color = p.text, modifier = Modifier.padding(bottom = 6.dp))
    Row(Modifier.fillMaxWidth().padding(top = 10.dp, bottom = 4.dp), verticalAlignment = Alignment.CenterVertically) {
        Eyebrow(CoverStackPlayerRules.nextUpLabel(next.size), Modifier.weight(1f), heading = true)
        if (next.isNotEmpty()) Box(
            Modifier.heightIn(min = Target).clickable(role = Role.Button, onClickLabel = "Remove every upcoming song") { next.asReversed().forEach(controller::remove) }.padding(start = 8.dp),
            contentAlignment = Alignment.Center,
        ) { Text("Clear", color = p.text, textDecoration = TextDecoration.Underline, style = MaterialTheme.typography.labelLarge.copy(fontSize = 13.sp, fontWeight = FontWeight.SemiBold)) }
    }
    val list = rememberLazyListState()
    LaunchedEffect(Unit) {
        if (items.isEmpty()) return@LaunchedEffect
        val shown = snapshotFlow { list.layoutInfo.visibleItemsInfo }.first { it.isNotEmpty() }
        if (shown.isNotEmpty() && next.isNotEmpty() && shown.none { it.index == 0 }) list.scrollToItem(0)
    }
    val rows = next + earlier
    LazyColumn(Modifier.fillMaxWidth().weight(1f), state = list) {
        itemsIndexed(rows, key = { _, position -> "$position-${items[position].songId}" }) { rowNo, position ->
            val song = items[position]
            val unavailable = song.songId in state.queue.unavailable
            if (rowNo == next.size && earlier.isNotEmpty()) {
                Eyebrow(CoverStackPlayerRules.songs(earlier.size).let { "Earlier · $it" }, Modifier.padding(top = 14.dp, bottom = 4.dp), heading = true)
            }
            var menu by remember { mutableStateOf(false) }
            val actions = buildList {
                if (position > 0) add("Move up" to { controller.move(position, position - 1) })
                if (position < items.lastIndex) add("Move down" to { controller.move(position, position + 1) })
                if (sonic) add("Add songs that sound like this" to { play.soundsLike(song.songId, queuedIds) })
                if (sonic) add("Sonic path from playing song to this one" to { pathTo = song })
            }
            Row(
                Modifier.fillMaxWidth().heightIn(min = 64.dp)
                    .combinedClickable(onClickLabel = "Play this song", role = Role.Button, onLongClickLabel = "More actions", onLongClick = { menu = true }) { if (!unavailable) controller.skipTo(position) }
                    .semantics { customActions = actions.map { (label, run) -> CustomAccessibilityAction(label) { run(); true } } },
                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                OutlinedCover(song, 48)
                Column(Modifier.weight(1f).padding(vertical = 8.dp)) {
                    if (unavailable) Text("Unavailable", style = MaterialTheme.typography.labelSmall, color = p.text, textDecoration = TextDecoration.Underline)
                    Text(song.title, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold))
                    Text(song.artist, color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall)
                }
                Box {
                    Box(Modifier.size(Target).clip(CircleShape).clickable(role = Role.Button) { controller.remove(position) }, contentAlignment = Alignment.Center) {
                        Icon(PlayerIcons.Close, contentDescription = "Remove ${song.title} from queue", tint = p.text, modifier = Modifier.size(20.dp))
                    }
                    DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                        actions.forEach { (label, run) -> DropdownMenuItem(text = { Text(label) }, onClick = { menu = false; run() }) }
                        DropdownMenuItem(text = { Text("Remove from queue") }, onClick = { menu = false; controller.remove(position) })
                    }
                }
            }
            CoverStackDivider()
        }
        item { TrackImageCards(trackImages(rememberAlbumArtIndex(playing)), Modifier.padding(top = 8.dp)) }
    }
    if (sonic) Box(Modifier.fillMaxWidth().padding(vertical = 10.dp)) {
        val shape = RoundedCornerShape(CoverStackRules.radius(p).dp)
        Row(
            Modifier.coverStackFrame(shape, p).heightIn(min = 44.dp).clickable(role = Role.Button) { play.soundsLike(playing.songId, queuedIds) }.padding(horizontal = 16.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Icon(PlayerIcons.Wave, contentDescription = null, tint = p.text, modifier = Modifier.size(20.dp))
            Text("Add songs that sound like this", color = p.text, style = MaterialTheme.typography.labelLarge.copy(fontSize = 14.sp, fontWeight = FontWeight.Bold))
        }
    }
    SeekRow(state, controller)
    Transport(state, controller)
    Spacer(Modifier.height(12.dp))
}

/** The mockup's Lyrics: the playing song with the Photos switch, the lines, then the seek bar and transport. */
@Composable
private fun ColumnScope.LyricsView(state: PlayerUiState, controller: PlayerController, item: QueueItem, input: CoverStackPlayerInput, photos: @Composable androidx.compose.foundation.layout.BoxScope.() -> Unit) {
    val p = LocalPalette.current
    PlayingHeader(item, null) {
        if (input.hasPhotos) Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("Photos", color = p.textMuted, style = MaterialTheme.typography.bodySmall, modifier = Modifier.clearAndSetSemantics { })
            CsSwitch(input.photosOn, "Photos behind the lyrics", input.onPhotos)
        }
    }
    Box(Modifier.weight(1f).fillMaxWidth()) {
        photos()
        CoverStackLyricsPanel(input.lyricsState, input.currentLine, input.songId, input.onTryAgain, Modifier.fillMaxSize().padding(top = 8.dp), overPhotos = input.hasPhotos && input.photosOn)
    }
    SeekRow(state, controller)
    Transport(state, controller)
    Spacer(Modifier.height(12.dp))
}

/** The outlined 52 by 32 switch: on is filled with the accent and the knob moves right; its state is also spoken. */
@Composable
private fun CsSwitch(on: Boolean, label: String, onToggle: () -> Unit) {
    val p = LocalPalette.current
    val ol = CoverStackRules.outline(p).dp
    Box(Modifier.size(width = 60.dp, height = Target).clickable(role = Role.Switch, onClick = onToggle).semantics { contentDescription = label; stateDescription = if (on) "On" else "Off" }, contentAlignment = Alignment.Center) {
        Box(Modifier.size(width = 52.dp, height = 32.dp).clip(RoundedCornerShape(16.dp)).background(if (on) p.accent else p.surface).border(ol, p.edgeStrong, RoundedCornerShape(16.dp))) {
            Box(Modifier.align(if (on) Alignment.CenterEnd else Alignment.CenterStart).padding(horizontal = 4.dp).size(20.dp).clip(CircleShape).background(if (on) p.surface else p.raised).border(ol, p.edgeStrong, CircleShape))
        }
    }
}
