package app.discair.ui.player

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.wrapContentHeight
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.DiscairApplication
import app.discair.player.PlayerController
import app.discair.player.PlayerUiState
import app.discair.player.QueueItem
import app.discair.player.RepeatMode
import app.discair.player.eq.EQ_MAX_GAIN_DB
import app.discair.player.qualityLabel
import app.discair.ui.common.Cover
import app.discair.ui.common.SheetStackRules
import app.discair.ui.common.StickerWallRules
import app.discair.ui.common.Target
import app.discair.ui.theme.LocalFontPair
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.brutalShadow
import app.discair.ui.theme.themeShape

private val PanelHeight = 380.dp

/**
 * Sticker Wall only: Now Playing as a poster. The cover leans a little in a round frame, the title is stacked in large letters, the
 * equalizer is three stacked pill bars (bass, mid, treble) that open the real Equalizer when pressed, the crossfade switch is the real
 * crossfade setting, and the transport is round. The queue and the lyrics open as panels under the poster from two pill buttons.
 * Every control does what its Standard twin does; the tilt is static.
 */
@Composable
fun StickerPlayer(
    state: PlayerUiState, controller: PlayerController, view: Int, onView: (Int) -> Unit,
    onSignIn: () -> Unit, onEqualizer: () -> Unit, onCrossfade: () -> Unit,
    onOpenArtist: (QueueItem) -> Unit, onOpenAlbum: (QueueItem) -> Unit,
    onCoverColor: (Color) -> Unit, lyricsPanel: @Composable () -> Unit,
) {
    val item = state.current ?: return
    val p = LocalPalette.current
    val rule = (p.shape?.outline ?: 3).dp
    val shape = themeShape(18.dp)
    val mono = LocalFontPair.current.mono
    var dragging by remember { mutableStateOf<Float?>(null) }
    val duration = state.durationMs
    val fraction = dragging ?: if (duration > 0) (state.positionMs.toFloat() / duration).coerceIn(0f, 1f) else 0f
    val shown = if (dragging != null) (fraction * duration).toLong() else state.positionMs
    val timeStyle = MaterialTheme.typography.labelSmall.copy(fontFamily = mono)
    val muted = MaterialTheme.colorScheme.onSurfaceVariant

    Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(bottom = 24.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        // The poster: the cover, leaning, in a round hard-shadowed frame.
        Box(Modifier.widthIn(max = 340.dp).fillMaxWidth(0.82f).graphicsLayer { rotationZ = -2f }.padding(end = 8.dp, bottom = 8.dp)) {
            Box(Modifier.fillMaxWidth().brutalShadow(shape).clip(shape).border(rule, p.edgeStrong, shape).background(p.raised)) {
                Cover(playerArtworkUrl(item.coverUrl), Modifier.fillMaxWidth().height(300.dp), rect = true, onColor = onCoverColor)
            }
        }
        Spacer(Modifier.height(16.dp))
        // The title, stacked in large letters. It is one heading for a screen reader, spoken whole.
        val stack = StickerWallRules.stackTitle(item.title)
        Column(
            Modifier.fillMaxWidth().padding(horizontal = 16.dp).semantics(mergeDescendants = true) { contentDescription = item.title; heading(); liveRegion = LiveRegionMode.Polite },
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            stack.forEach { line ->
                Text(
                    line, textAlign = TextAlign.Center, maxLines = 1, overflow = TextOverflow.Ellipsis,
                    style = MaterialTheme.typography.headlineLarge.copy(fontSize = 34.sp, lineHeight = 36.sp),
                    modifier = Modifier.clearAndSetSemantics { },
                )
            }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
            val link = MaterialTheme.typography.bodyMedium
            if (item.artist.isNotBlank()) Text(
                item.artist, style = link, color = muted, maxLines = 1, overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f, fill = false).heightIn(min = Target).clickable(onClickLabel = "Open artist", role = Role.Button) { onOpenArtist(item) }
                    .wrapContentHeight(Alignment.CenterVertically),
            )
            if (item.artist.isNotBlank() && item.album.isNotBlank()) Text(" · ", style = link, color = muted)
            if (item.album.isNotBlank()) Text(
                item.album, style = link, color = muted, maxLines = 1, overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f, fill = false).heightIn(min = Target).clickable(onClickLabel = "Open album", role = Role.Button) { onOpenAlbum(item) }
                    .wrapContentHeight(Alignment.CenterVertically),
            )
        }
        // Status in words: loading, buffering, lost connection, unavailable, queue full.
        if (state.status != null || state.buffering) {
            Text(
                playerSubtitle(state), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.primary, textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth().padding(top = 4.dp).semantics { liveRegion = LiveRegionMode.Polite },
            )
        }
        if (state.signInRequired) TextButton(onClick = { controller.dismissSignIn(); onSignIn() }, Modifier.heightIn(min = Target)) { Text("Sign in again") }
        if (state.waitingForNetwork) TextButton(onClick = controller::retryNow, Modifier.heightIn(min = Target)) { Text("Retry now") }
        qualityLabel(item)?.let {
            Text(it, style = timeStyle, color = muted, maxLines = 1, modifier = Modifier.padding(top = 4.dp).border(1.dp, p.edgeStrong, CircleShape).padding(horizontal = 8.dp, vertical = 1.dp))
        }
        Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(formatTime(shown), style = timeStyle, color = muted, modifier = Modifier.padding(end = 8.dp))
            SeekBar(
                fraction = fraction, enabled = duration > 0,
                onChange = { dragging = it },
                onFinish = { dragging?.let { controller.seekTo((it * duration).toLong()) }; dragging = null },
                modifier = Modifier.weight(1f).semantics {
                    contentDescription = "Seek"
                    stateDescription = seekDescription(shown, duration)
                },
            )
            Text(if (duration > 0) formatTime(duration) else "--:--", style = timeStyle, color = muted, modifier = Modifier.padding(start = 8.dp))
        }
        // The round transport.
        Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            val shuffle = state.queue.shuffle
            val repeat = state.queue.repeat
            RoundButton("Shuffle", 48, selected = shuffle, state = if (shuffle) "On" else "Off", onClick = { controller.setShuffle(!shuffle) }) { Icon(PlayerIcons.Shuffle, contentDescription = null, tint = it) }
            RoundButton("Previous song", 48, onClick = controller::previous) { Icon(PlayerIcons.Previous, contentDescription = null, tint = it) }
            RoundButton(if (state.isPlaying) "Pause" else "Play", 72, primary = true, onClick = controller::playPause) {
                Icon(if (state.isPlaying) PlayerIcons.Pause else PlayerIcons.Play, contentDescription = null, tint = it, modifier = Modifier.size(36.dp))
            }
            RoundButton("Next song", 48, enabled = state.queue.items.size > 1, onClick = controller::next) { Icon(PlayerIcons.Next, contentDescription = null, tint = it) }
            RoundButton(
                "Repeat", 48, selected = repeat != RepeatMode.Off,
                state = when (repeat) { RepeatMode.Off -> "Off"; RepeatMode.All -> "Repeat all"; RepeatMode.One -> "Repeat one" }, onClick = controller::cycleRepeat,
            ) { Icon(if (repeat == RepeatMode.One) PlayerIcons.RepeatOne else PlayerIcons.Repeat, contentDescription = null, tint = it) }
        }
        // The equalizer as three stacked pill bars, and the crossfade switch: both are the real settings.
        StickerEqualizer(onEqualizer)
        CrossfadeSwitchRow(onCrossfade)
        // The queue and the lyrics, from two pill buttons.
        Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            PillToggle("Queue", view == SHEET_VIEW_QUEUE, Modifier.weight(1f)) { onView(SheetStackRules.toggleView(view, SHEET_VIEW_QUEUE)) }
            PillToggle("Lyrics", view == SHEET_VIEW_LYRICS, Modifier.weight(1f)) { onView(SheetStackRules.toggleView(view, SHEET_VIEW_LYRICS)) }
        }
        if (view == SHEET_VIEW_QUEUE || view == SHEET_VIEW_LYRICS) {
            Box(
                Modifier.padding(start = 16.dp, end = 24.dp, bottom = 8.dp).fillMaxWidth().height(PanelHeight).brutalShadow(shape).clip(shape)
                    .background(p.surface).border(rule, p.edgeStrong, shape).padding(horizontal = 16.dp),
            ) {
                if (view == SHEET_VIEW_QUEUE) QueuePanel(state, controller, Modifier.fillMaxSize()) else lyricsPanel()
            }
        }
    }
}

/** A round transport button: a circle with an outline and a hard shadow; [primary] fills it with the accent. At least 48dp. */
@Composable
private fun RoundButton(
    label: String, size: Int, primary: Boolean = false, selected: Boolean = false, enabled: Boolean = true, state: String? = null,
    onClick: () -> Unit, icon: @Composable (Color) -> Unit,
) {
    val p = LocalPalette.current
    val on = primary || selected
    val fill = if (!enabled) p.raised else if (on) p.accent else p.surface
    val ink = if (!enabled) p.textMuted else if (on) p.onAccent else p.text
    Box(
        Modifier.size(size.dp).brutalShadow(CircleShape, if (primary) 1f else 0.6f).clip(CircleShape).background(fill).border((p.shape?.outline ?: 3).dp, p.edgeStrong, CircleShape)
            .clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .semantics { contentDescription = label; if (state != null) stateDescription = state },
        contentAlignment = Alignment.Center,
    ) { icon(ink) }
}

@Composable
private fun PillToggle(label: String, open: Boolean, modifier: Modifier, onClick: () -> Unit) {
    val p = LocalPalette.current
    Box(
        modifier.heightIn(min = 48.dp).clip(CircleShape).background(if (open) p.accent else p.surface).border((p.shape?.outline ?: 3).dp, p.edgeStrong, CircleShape)
            .clickable(role = Role.Button, onClick = onClick).semantics { contentDescription = label; stateDescription = if (open) "Open" else "Closed" },
        contentAlignment = Alignment.Center,
    ) { Text(label, style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Bold), color = if (open) p.onAccent else p.text, modifier = Modifier.clearAndSetSemantics { }) }
}

/**
 * The equalizer summary: bass, mid and treble as three stacked pill bars, each filled to that group's average gain (flat is half).
 * Pressing it opens the Equalizer, the real controls; nothing here changes the sound. When the equalizer is off the bars rest at half
 * and the words say so.
 */
@Composable
private fun StickerEqualizer(onOpen: () -> Unit) {
    val p = LocalPalette.current
    val store = (LocalContext.current.applicationContext as DiscairApplication).container.eqSettings
    var config by remember { mutableStateOf(store.load().config) }
    DisposableEffect(Unit) {
        val remove = store.addListener { config = store.load().config }
        onDispose { remove() }
    }
    val bars = StickerWallRules.EqBar.values()
    val spoken = if (!config.enabled) "Equalizer: off. Open the equalizer"
    else bars.joinToString(", ", prefix = "Equalizer: ") { StickerWallRules.barSpoken(it, StickerWallRules.barGainDb(config.bandGainsDb, it)) } + ". Open the equalizer"
    Column(
        Modifier.padding(horizontal = 16.dp, vertical = 8.dp).fillMaxWidth().clip(themeShape(16.dp)).clickable(role = Role.Button, onClick = onOpen)
            .semantics(mergeDescendants = true) { contentDescription = spoken },
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        bars.forEach { bar ->
            val level = if (config.enabled) StickerWallRules.barFraction(StickerWallRules.barGainDb(config.bandGainsDb, bar), EQ_MAX_GAIN_DB) else 0.5f
            Row(Modifier.heightIn(min = 44.dp), verticalAlignment = Alignment.CenterVertically) {
                Text(bar.label, style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold), modifier = Modifier.widthIn(min = 56.dp).clearAndSetSemantics { })
                Box(Modifier.weight(1f).height(26.dp).clip(CircleShape).background(p.surface).border((p.shape?.outline ?: 3).dp, p.edgeStrong, CircleShape).clearAndSetSemantics { }) {
                    Box(Modifier.fillMaxSize().padding(4.dp)) {
                        Box(Modifier.fillMaxWidth(level).fillMaxSize().clip(CircleShape).background(if (config.enabled) p.accent else p.raised))
                    }
                }
            }
        }
        if (!config.enabled) Text("Equalizer off · tap to open", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.clearAndSetSemantics { })
    }
}

/** The crossfade switch: the real setting (the same one the Crossfade page changes). The icon beside it opens that page for the length. */
@Composable
private fun CrossfadeSwitchRow(onOpenPage: () -> Unit) {
    val settings = (LocalContext.current.applicationContext as DiscairApplication).container.playerSettings
    val (xf, _) = rememberCrossfade(settings)
    Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp).heightIn(min = 48.dp), verticalAlignment = Alignment.CenterVertically) {
        Text("Crossfade", style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.Bold), modifier = Modifier.weight(1f).clearAndSetSemantics { })
        Switch(
            checked = xf.enabled, onCheckedChange = { settings.crossfadeEnabled = it },
            modifier = Modifier.semantics { contentDescription = "Crossfade"; stateDescription = if (xf.enabled) "On" else "Off" },
        )
        CrossfadeLink(onOpenPage)
    }
}
