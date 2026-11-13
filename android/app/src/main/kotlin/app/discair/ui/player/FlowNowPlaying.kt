package app.discair.ui.player

import app.discair.ui.common.ArtIcons
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.wrapContentHeight
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
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
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import app.discair.lyrics.LyricsUiState
import app.discair.model.trackImages
import app.discair.player.PlayerController
import app.discair.player.PlayerUiState
import app.discair.player.QueueItem
import app.discair.player.RepeatMode
import app.discair.player.qualityLabel
import app.discair.ui.common.Cover
import app.discair.ui.common.FlowDivider
import app.discair.ui.common.FlowEyebrow
import app.discair.ui.common.FlowRules
import app.discair.ui.common.FlowSwitch
import app.discair.ui.common.FlowTag
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.Target
import app.discair.ui.common.flowDepth
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.accentText
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.withContext

/*
 * Flow (Layout.Flow): Now Playing, Queue and Lyrics. Mockup: flow/player. Reached only from NowPlayingSheet's Flow branch; no other theme draws any
 * of this. Like Soft Brut's, the Queue and the Lyrics open as a sheet over Now Playing (as the Equalizer and Crossfade do), not as full pages of
 * their own, so [FlowPanel] has no top bar. Every control does what its Standard twin does.
 */

/** The pure rules of the Flow player (unit-tested). The Queue lists are the Soft Brut ones. */
object FlowPlayerRules {
    /** The word in the top bar's middle. */
    const val TITLE = "Now playing"

    /** Round buttons: Previous and Next 48dp, Play 72dp, Shuffle and Repeat plain 22dp glyphs (flow.css `.cb`). */
    const val SIDE_BUTTON = 48
    const val PLAY_BUTTON = 72
    const val FLAT_GLYPH = 22
    const val SIDE_GLYPH = 30
    const val PLAY_GLYPH = 32

    /** The cover (flow.css `.npc`): 312dp wide at most, radius 18, level 3 depth. */
    const val COVER = 312
    const val COVER_RADIUS = 18

    /** The Lyrics' size (flow.css `.lyr p`: Inter 700 22/30) and the share of the text colour the lines not being sung keep. */
    const val LYRIC_SIZE = 22
    const val LYRIC_LINE = 30
    const val LYRIC_QUIET_ALPHA = 0.5f
}

/** One plain Flow transport button: a glyph, no frame; [main] is the round text-colour Play. */
@Composable
internal fun FlowTransportButton(
    label: String, onClick: () -> Unit, modifier: Modifier = Modifier, size: Int = FlowPlayerRules.SIDE_BUTTON, main: Boolean = false,
    enabled: Boolean = true, state: String? = null, icon: @Composable (Color) -> Unit,
) {
    val p = LocalPalette.current
    val ink = when { main -> p.ink; !enabled -> p.edgeStrong; else -> p.text }
    Box(
        modifier.size(size.dp).clip(CircleShape).then(if (main) Modifier.background(p.text) else Modifier)
            .clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .semantics { contentDescription = label; if (state != null) stateDescription = state },
        contentAlignment = Alignment.Center,
    ) { icon(ink) }
}

/** Shuffle and Repeat are plain muted glyphs, accent when on (and so also said in words); Previous, Play and Next are the big ones. */
@Composable
private fun FlowTransport(state: PlayerUiState, controller: PlayerController) {
    val p = LocalPalette.current
    val shuffle = state.queue.shuffle
    val repeat = state.queue.repeat
    Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
        FlowTransportButton("Shuffle", { controller.setShuffle(!shuffle) }, state = if (shuffle) "On" else "Off") {
            Icon(ArtIcons.Shuffle, null, tint = if (shuffle) p.accentText else p.textMuted, modifier = Modifier.size(FlowPlayerRules.FLAT_GLYPH.dp))
        }
        FlowTransportButton("Previous song", controller::previous) { Icon(ArtIcons.Previous, null, tint = it, modifier = Modifier.size(FlowPlayerRules.SIDE_GLYPH.dp)) }
        FlowTransportButton(if (state.isPlaying) "Pause" else "Play", controller::playPause, size = FlowPlayerRules.PLAY_BUTTON, main = true) {
            Icon(if (state.isPlaying) ArtIcons.Pause else ArtIcons.Play, null, tint = it, modifier = Modifier.size(FlowPlayerRules.PLAY_GLYPH.dp))
        }
        FlowTransportButton("Next song", controller::next, enabled = state.queue.items.size > 1) { Icon(ArtIcons.Next, null, tint = it, modifier = Modifier.size(FlowPlayerRules.SIDE_GLYPH.dp)) }
        FlowTransportButton(
            "Repeat", controller::cycleRepeat,
            state = when (repeat) { RepeatMode.Off -> "Off"; RepeatMode.All -> "Repeat all"; RepeatMode.One -> "Repeat one" },
        ) {
            Icon(
                if (repeat == RepeatMode.One) ArtIcons.RepeatOne else ArtIcons.Repeat, null,
                tint = if (repeat != RepeatMode.Off) p.accentText else p.textMuted, modifier = Modifier.size(FlowPlayerRules.FLAT_GLYPH.dp),
            )
        }
    }
}

/** The 4dp seek line with a round thumb ([SeekBar] draws it for Flow) and the two times under it. */
@Composable
private fun FlowSeekRow(state: PlayerUiState, controller: PlayerController, peaks: FloatArray? = null) {
    val p = LocalPalette.current
    var dragging by remember { mutableStateOf<Float?>(null) }
    val duration = state.durationMs
    val fraction = dragging ?: if (duration > 0) (state.positionMs.toFloat() / duration).coerceIn(0f, 1f) else 0f
    val shown = if (dragging != null) (fraction * duration).toLong() else state.positionMs
    val timeStyle = MaterialTheme.typography.labelSmall.copy(fontSize = 12.sp, lineHeight = 16.sp)
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

/** The top bar: a Down button (accent glyph) at the left, the title in the middle, the three-dot menu at the right (flow.css `.bar`). */
@Composable
private fun FlowTopBar(onClose: () -> Unit, menu: List<Pair<String, () -> Unit>>) {
    val p = LocalPalette.current
    Row(Modifier.fillMaxWidth().heightIn(min = 48.dp), verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(Target).clip(CircleShape).clickable(role = Role.Button, onClick = onClose), contentAlignment = Alignment.Center) {
            Icon(ArtIcons.Down, contentDescription = "Close now playing", tint = p.accentText)
        }
        Box(Modifier.weight(1f).semantics { heading() }, contentAlignment = Alignment.Center) { FlowEyebrow(FlowPlayerRules.TITLE) }
        var open by remember { mutableStateOf(false) }
        Box {
            Box(Modifier.size(Target).clip(CircleShape).clickable(role = Role.Button) { open = true }, contentAlignment = Alignment.Center) {
                Icon(ArtIcons.More, contentDescription = "More", tint = p.accentText)
            }
            DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
                menu.forEach { (label, run) -> DropdownMenuItem(text = { Text(label) }, onClick = { open = false; run() }) }
            }
        }
    }
}

/**
 * The Flow player: the top bar, the 312dp cover over the wash, title and artist, the seek line, the transport and the four entries under it
 * (Queue, Lyrics, Equalizer, Crossfade). The mockup's heart (no favourite action) and Sonic path (no Now Playing action; Crossfade takes its
 * slot) are not drawn, as on Soft Brut. [onView] opens the Queue (2) or the Lyrics (1) as a sheet.
 */
@Composable
fun FlowPlayer(
    state: PlayerUiState, controller: PlayerController, onView: (Int) -> Unit, onClose: () -> Unit,
    onSignIn: () -> Unit, onEqualizer: () -> Unit, onCrossfade: () -> Unit,
    onOpenArtist: (QueueItem) -> Unit, onOpenAlbum: (QueueItem) -> Unit, onCoverColor: (Color) -> Unit, input: CoverStackPlayerInput,
) {
    val item = state.current ?: return
    val p = LocalPalette.current
    val menu = buildList {
        add((if (input.line.showLyrics) "Hide the lyric line" else "Show the lyric line") to input.line.onLyrics)
        add((if (input.line.showFacts) "Hide facts" else "Show facts") to input.line.onFacts)
        if (item.artist.isNotBlank()) add("Open artist" to { onOpenArtist(item) })
        if (item.album.isNotBlank()) add("Open album" to { onOpenAlbum(item) })
    }
    val coverShape = RoundedCornerShape(FlowPlayerRules.COVER_RADIUS.dp)
    Column(Modifier.fillMaxWidth().fillMaxHeight()) {
        FlowTopBar(onClose, menu)
        Column(Modifier.weight(1f, fill = true).fillMaxWidth().verticalScroll(rememberScrollState())) {
            Box(Modifier.fillMaxWidth().padding(top = 8.dp, bottom = 20.dp), contentAlignment = Alignment.Center) {
                Box(
                    Modifier.widthIn(max = FlowPlayerRules.COVER.dp).fillMaxWidth().aspectRatio(1f).flowDepth(3, coverShape, p).clip(coverShape),
                ) { Cover(playerArtworkUrl(item.coverUrl), Modifier.fillMaxSize(), rect = true, onColor = onCoverColor) }
            }
            Column(Modifier.fillMaxWidth()) {
                Text(
                    item.title, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis,
                    style = MaterialTheme.typography.headlineLarge.copy(fontSize = 26.sp, lineHeight = 30.sp, fontWeight = FontWeight.ExtraBold, letterSpacing = (-0.02).em),
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
                qualityLabel(item)?.let { FlowTag(it, Modifier.padding(top = 2.dp, bottom = 4.dp)) }
                // States the mockup does not draw, said in words: the lyric or fact line (when switched on), and the status.
                if (input.line.showLyrics || input.line.showFacts) PlayerLineText(input.line.line, Modifier.padding(top = 2.dp), align = TextAlign.Start)
                if (state.status != null || state.buffering) Text(
                    playerSubtitle(state), style = MaterialTheme.typography.bodyMedium, color = p.text,
                    modifier = Modifier.fillMaxWidth().padding(top = 4.dp).semantics { liveRegion = LiveRegionMode.Polite },
                )
                if (state.signInRequired) TextButton(onClick = { controller.dismissSignIn(); onSignIn() }, Modifier.heightIn(min = Target)) { Text("Sign in again", color = p.accentText, textDecoration = TextDecoration.Underline) }
                if (state.waitingForNetwork) TextButton(onClick = controller::retryNow, Modifier.heightIn(min = Target)) { Text("Retry now", color = p.accentText, textDecoration = TextDecoration.Underline) }
            }
            Spacer(Modifier.height(14.dp))
            FlowSeekRow(state, controller, input.line.peaks)
            FlowTransport(state, controller)
        }
        Row(Modifier.fillMaxWidth().padding(top = 8.dp, bottom = 12.dp), horizontalArrangement = Arrangement.SpaceAround) {
            Entry("Queue", ArtIcons.Queue) { onView(CoverStackPlayerRules.VIEW_QUEUE) }
            Entry("Lyrics", ArtIcons.Quote) { onView(CoverStackPlayerRules.VIEW_LYRICS) }
            Entry("Equalizer", ArtIcons.Tune, onEqualizer)
            Entry("Crossfade", ArtIcons.Swap, onCrossfade)
        }
    }
}

/** An icon over a small muted label, at least 48dp to touch (mockup: the row under the transport). */
@Composable
private fun Entry(label: String, icon: ImageVector, onClick: () -> Unit) {
    val p = LocalPalette.current
    Column(
        Modifier.widthIn(min = 64.dp).heightIn(min = 52.dp).clip(RoundedCornerShape(10.dp)).clickable(role = Role.Button, onClick = onClick).padding(horizontal = 6.dp, vertical = 4.dp)
            .semantics(mergeDescendants = true) { contentDescription = label },
        horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center,
    ) {
        Icon(icon, contentDescription = null, tint = p.textMuted, modifier = Modifier.size(24.dp))
        Text(label, style = MaterialTheme.typography.labelSmall.copy(fontSize = 12.sp), color = p.textMuted, maxLines = 1, modifier = Modifier.clearAndSetSemantics { })
    }
}

/**
 * The Queue and the Lyrics as a sheet over Now Playing, like Equalizer and Crossfade ([NowPlayingSheet] hosts it in its settings sheet).
 * [view] is VIEW_QUEUE or VIEW_LYRICS; the sheet's own handle closes it, so there is no top bar.
 */
@Composable
fun FlowPanel(
    state: PlayerUiState, controller: PlayerController, view: Int, input: CoverStackPlayerInput,
    photos: @Composable androidx.compose.foundation.layout.BoxScope.() -> Unit,
) {
    val item = state.current ?: return
    Column(Modifier.fillMaxWidth().fillMaxHeight(0.92f).padding(horizontal = 16.dp)) {
        if (view == CoverStackPlayerRules.VIEW_QUEUE) FlowQueue(state, controller, input.line.peaks) else FlowLyrics(state, controller, item, input, photos)
    }
}

/** A cover with Flow's soft corners and no outline. */
@Composable
private fun FlowThumb(url: String, size: Int, radius: Int = FlowRules.RADIUS_COVER_SMALL.toInt()) {
    Box(Modifier.size(size.dp).clip(RoundedCornerShape(radius.dp))) { Cover(url.ifBlank { null }, Modifier.fillMaxSize(), rect = true) }
}

/** The playing song at the top of the Queue and Lyrics: a 56dp cover, then the eyebrow, title and artist. */
@Composable
private fun FlowPlayingHeader(item: QueueItem, eyebrow: String?, trailing: @Composable () -> Unit = {}) {
    val p = LocalPalette.current
    Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        FlowThumb(item.coverUrl, 56)
        Column(Modifier.weight(1f)) {
            if (eyebrow != null) FlowEyebrow(eyebrow)
            Text(item.title, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold), modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
            Text(item.artist, color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall)
        }
        trailing()
    }
}

/** The mockup's Queue: the playing song, "Next up", rows with a remove X, "Add songs that sound like this", then the seek line and transport. */
@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun ColumnScope.FlowQueue(state: PlayerUiState, controller: PlayerController, peaks: FloatArray?) {
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

    FlowPlayingHeader(playing, "Playing")
    if (state.status != null) Text(state.status, style = MaterialTheme.typography.bodySmall, color = p.text, modifier = Modifier.padding(bottom = 6.dp))
    Row(Modifier.fillMaxWidth().padding(top = 10.dp, bottom = 4.dp), verticalAlignment = Alignment.CenterVertically) {
        FlowEyebrow(CoverStackPlayerRules.nextUpLabel(next.size), Modifier.weight(1f).semantics { heading() })
        if (next.isNotEmpty()) Box(
            Modifier.heightIn(min = Target).clickable(role = Role.Button, onClickLabel = "Remove every upcoming song") { next.asReversed().forEach(controller::remove) }.padding(start = 8.dp),
            contentAlignment = Alignment.Center,
        ) { Text("Clear", color = p.accentText, style = MaterialTheme.typography.labelLarge.copy(fontSize = 14.sp, fontWeight = FontWeight.Medium)) }
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
                FlowEyebrow("Earlier · ${CoverStackPlayerRules.songs(earlier.size)}", Modifier.padding(top = 14.dp, bottom = 4.dp).semantics { heading() })
            }
            var menu by remember { mutableStateOf(false) }
            val actions = buildList {
                if (position > 0) add("Move up" to { controller.move(position, position - 1) })
                if (position < items.lastIndex) add("Move down" to { controller.move(position, position + 1) })
                if (sonic) add("Add songs that sound like this" to { play.soundsLike(song.songId, queuedIds) })
                if (sonic) add("Sonic path from playing song to this one" to { pathTo = song })
            }
            Row(
                Modifier.fillMaxWidth().heightIn(min = FlowRules.ROW_MIN.dp)
                    .combinedClickable(onClickLabel = "Play this song", role = Role.Button, onLongClickLabel = "More actions", onLongClick = { menu = true }) { if (!unavailable) controller.skipTo(position) }
                    .semantics { customActions = actions.map { (label, run) -> CustomAccessibilityAction(label) { run(); true } } },
                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                FlowThumb(song.coverUrl, 48)
                Column(Modifier.weight(1f).padding(vertical = 8.dp)) {
                    if (unavailable) Text("Unavailable", style = MaterialTheme.typography.labelSmall, color = p.text, textDecoration = TextDecoration.Underline)
                    Text(song.title, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold))
                    Text(song.artist, color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall)
                }
                Box {
                    Box(Modifier.size(Target).clip(CircleShape).clickable(role = Role.Button) { controller.remove(position) }, contentAlignment = Alignment.Center) {
                        Icon(ArtIcons.Close, contentDescription = "Remove ${song.title} from queue", tint = p.text, modifier = Modifier.size(20.dp))
                    }
                    DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                        actions.forEach { (label, run) -> DropdownMenuItem(text = { Text(label) }, onClick = { menu = false; run() }) }
                        DropdownMenuItem(text = { Text("Remove from queue") }, onClick = { menu = false; controller.remove(position) })
                    }
                }
            }
            FlowDivider()
        }
        item { TrackImageCards(trackImages(rememberAlbumArtIndex(playing)), Modifier.padding(top = 8.dp)) }
    }
    if (sonic) Box(Modifier.fillMaxWidth().padding(vertical = 10.dp)) {
        Row(
            Modifier.heightIn(min = 44.dp).clip(RoundedCornerShape(22.dp)).background(p.raised).clickable(role = Role.Button) { play.soundsLike(playing.songId, queuedIds) }.padding(horizontal = 16.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Icon(ArtIcons.Wave, contentDescription = null, tint = p.text, modifier = Modifier.size(20.dp))
            Text("Add songs that sound like this", color = p.text, style = MaterialTheme.typography.labelLarge.copy(fontSize = 15.sp, fontWeight = FontWeight.SemiBold))
        }
    }
    FlowSeekRow(state, controller, peaks)
    FlowTransport(state, controller)
    Spacer(Modifier.height(12.dp))
}

/** The mockup's Lyrics: the playing song with the Photos switch, the lines, then the seek line and transport. */
@Composable
private fun ColumnScope.FlowLyrics(
    state: PlayerUiState, controller: PlayerController, item: QueueItem, input: CoverStackPlayerInput,
    photos: @Composable androidx.compose.foundation.layout.BoxScope.() -> Unit,
) {
    val p = LocalPalette.current
    FlowPlayingHeader(item, null) {
        if (input.hasPhotos) Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("Photos", color = p.textMuted, style = MaterialTheme.typography.bodySmall, modifier = Modifier.clearAndSetSemantics { })
            Box(
                Modifier.size(width = 60.dp, height = Target).clickable(onClick = input.onPhotos)
                    .semantics { role = Role.Switch; contentDescription = "Photos behind the lyrics"; stateDescription = if (input.photosOn) "On" else "Off" },
                contentAlignment = Alignment.Center,
            ) { FlowSwitch(input.photosOn) }
        }
    }
    Box(Modifier.weight(1f).fillMaxWidth()) {
        photos()
        CoverStackLyricsPanel(
            input.lyricsState, input.currentLine, input.songId, input.onTryAgain, Modifier.fillMaxSize().padding(top = 8.dp),
            overPhotos = input.hasPhotos && input.photosOn, flow = true,
        )
    }
    FlowSeekRow(state, controller, input.line.peaks)
    FlowTransport(state, controller)
    Spacer(Modifier.height(12.dp))
}
