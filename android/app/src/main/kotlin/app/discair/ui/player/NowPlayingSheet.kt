package app.discair.ui.player

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
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
import androidx.compose.material3.Slider
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
import app.discair.ui.common.Cover
import app.discair.ui.common.SegmentedTabs
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NowPlayingSheet(state: PlayerUiState, controller: PlayerController, lyrics: LyricsController, onDismiss: () -> Unit, onSignIn: () -> Unit, onEqualizer: () -> Unit = {}) {
    val sheet = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var view by remember { mutableStateOf(lastView) }
    BackHandler(enabled = view != 0) { view = 0; lastView = 0 }
    val scope = androidx.compose.runtime.rememberCoroutineScope()
    val follower = remember { LyricsFollower(scope, controller::livePositionMs) }
    val lyricsState by lyrics.state.collectAsState()
    val songId = state.current?.songId
    val nextId = state.queue.nextIndex()?.let { state.queue.items.getOrNull(it)?.songId }?.takeIf { it != songId }
    val lyricsOpen = view == 1
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
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheet, containerColor = Ink.Surface) {
        val item = state.current
        if (item == null) { onDismiss(); return@ModalBottomSheet }
        Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = onDismiss, Modifier.size(Target)) { Icon(PlayerIcons.Down, contentDescription = "Close now playing") }
                Spacer(Modifier.weight(1f))
                // Three labelled views; the selected one is announced as selected and drawn raised (not colour alone).
                SegmentedTabs(ViewLabels, view, { view = it; lastView = it })
                Spacer(Modifier.weight(1f))
                Spacer(Modifier.size(Target)) // balances the close button so the tabs sit in the middle
            }
            Spacer(Modifier.height(12.dp)) // the tabs must not touch the cover, the lyrics note or the queue title
            when (view) {
                1 -> LyricsPanel(
                    if (lyricsState.songIdOrNull() == songId) lyricsState else LyricsUiState.Idle,
                    currentLine, songId.orEmpty(), onTryAgain = { if (songId != null) lyrics.retry(songId, nextId) },
                )
                2 -> QueuePanel(state, controller)
                else -> Player(state, controller, onSignIn, onEqualizer)
            }
        }
    }
}

@Composable
private fun Player(state: PlayerUiState, controller: PlayerController, onSignIn: () -> Unit, onEqualizer: () -> Unit) {
    val item = state.current ?: return
    var confirmClear by remember { mutableStateOf(false) }
    var dragging by remember { mutableStateOf<Float?>(null) }
    val duration = state.durationMs
    val fraction = dragging ?: if (duration > 0) (state.positionMs.toFloat() / duration).coerceIn(0f, 1f) else 0f
    Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()), horizontalAlignment = Alignment.CenterHorizontally) {
        Cover(
            item.coverUrl.ifBlank { null },
            Modifier.widthIn(max = 320.dp).fillMaxWidth().aspectRatio(1f),
        )
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

        Slider(
            value = fraction,
            onValueChange = { dragging = it },
            onValueChangeFinished = { dragging?.let { controller.seekTo((it * duration).toLong()) }; dragging = null },
            enabled = duration > 0,
            modifier = Modifier.fillMaxWidth().padding(top = 8.dp).semantics {
                contentDescription = "Seek"
                stateDescription = seekDescription(if (dragging != null) (fraction * duration).toLong() else state.positionMs, duration)
            },
        )
        Row(Modifier.fillMaxWidth().padding(horizontal = 4.dp), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(formatTime(if (dragging != null) (fraction * duration).toLong() else state.positionMs), style = MaterialTheme.typography.bodySmall.copy(fontFamily = Mono))
            Text(if (duration > 0) formatTime(duration) else "--:--", style = MaterialTheme.typography.bodySmall.copy(fontFamily = Mono))
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
        Text("Volume follows the phone's volume buttons.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        EqualizerLink(onEqualizer)
        Spacer(Modifier.height(32.dp)) // the destructive-looking action sits well away from the transport controls
        TextButton(onClick = { confirmClear = true }, Modifier.heightIn(min = Target)) { Text("Clear queue and stop") }
        Spacer(Modifier.height(24.dp))
    }
    if (confirmClear) {
        AlertDialog(
            onDismissRequest = { confirmClear = false },
            title = { Text("Clear the queue?") },
            text = { Text("Playback stops and the ${state.queue.items.size} songs in the queue are removed. Your library is not changed.") },
            dismissButton = { TextButton(onClick = { confirmClear = false }) { Text("Cancel") } },
            confirmButton = { TextButton(onClick = { confirmClear = false; controller.clear() }) { Text("Clear queue") } },
        )
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
