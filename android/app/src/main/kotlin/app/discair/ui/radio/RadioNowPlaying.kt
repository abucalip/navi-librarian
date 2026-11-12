package app.discair.ui.radio

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.IconButtonDefaults
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.RectangleShape
import app.discair.ui.player.ArtworkBackdrop
import app.discair.ui.player.canBlur
import app.discair.ui.theme.brutalShadow
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import app.discair.ui.common.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
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
import app.discair.model.RadioDownload
import app.discair.model.RadioNow
import app.discair.model.radioNowText
import app.discair.player.PlayerController
import app.discair.player.PlayerUiState
import app.discair.player.RadioPlayback
import app.discair.player.SLEEP_TIMER_MINUTES
import app.discair.player.SleepTimer
import app.discair.player.sleepTimerText
import app.discair.ui.common.Cover
import app.discair.ui.common.FilledIconButton
import app.discair.ui.common.ModalBottomSheet
import app.discair.ui.common.PlayerIconButton
import app.discair.ui.common.Target
import app.discair.ui.player.PlayerIcons
import app.discair.ui.player.playerArtworkUrl
import app.discair.ui.theme.Ink

/** The station logo is served at 128 or 512 only; the song cover goes through the player's usual large request. */
internal fun radioArtworkUrl(url: String): String? =
    if ("/logo" in url) url.takeIf { it.isNotBlank() }?.let { if ("size=" in it) it else app.discair.model.radioLogoRequest(it, 512) }
    else playerArtworkUrl(url)

/**
 * Now Playing for a station (docs/RADIO_PLAYBACK_CONTRACT.md section 4), built like the song sheet: the same sheet, the
 * artwork tint or blurred backdrop, header, themed artwork card, title block, status words and round primary Play button.
 * A live stream has no seek bar, queue, lyrics, shuffle or repeat, so those are left out; it adds the favourite toggle,
 * the Download control and a link to the Heard list.
 */
@Composable
@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
fun RadioNowPlayingSheet(
    state: PlayerUiState,
    controller: PlayerController,
    radio: RadioPlayback,
    sleep: SleepTimer,
    onDismiss: () -> Unit,
    onOpenHeard: () -> Unit,
) {
    val live by radio.state.collectAsState()
    val item = state.current ?: return
    var tint by remember { mutableStateOf<Color?>(null) }
    val ground = Ink.Ink
    val palette = app.discair.ui.theme.LocalPalette.current
    val wash by animateColorAsState(if (palette.brutal) ground else tint ?: ground, animationSpec = tween(500), label = "artworkTint")
    LaunchedEffect(item.coverUrl) { if (item.coverUrl.isBlank()) tint = null }
    val artwork = radioArtworkUrl(item.coverUrl)
    val blurred = canBlur && !artwork.isNullOrBlank()
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true), containerColor = Ink.Ink, shape = RectangleShape) {
        app.discair.ui.common.TransparentNavigationBar()
        Box {
            if (blurred) ArtworkBackdrop(artwork)
            Column(
                Modifier.fillMaxWidth().drawBehind {
                    if (blurred) return@drawBehind
                    val top = -48.dp.toPx()
                    drawRect(Brush.verticalGradient(listOf(wash, ground), startY = top, endY = size.height * 0.9f), topLeft = Offset(0f, top), size = Size(size.width, size.height - top))
                }.padding(horizontal = 16.dp),
            ) {
                // Soft Brut draws its own live-radio sheet (mockup soft-brut/radio, frame 2): CoverStackRadio.kt.
                if (app.discair.ui.common.isCoverStack()) {
                    CoverStackRadioNow(state, controller, radio, sleep, live, item, artwork, radioStatusText(state, live), onDismiss, onOpenHeard)
                    return@Column
                }
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    PlayerIconButton(onClick = onDismiss, Modifier.size(Target)) { Icon(PlayerIcons.Down, contentDescription = "Close now playing") }
                    Spacer(Modifier.weight(1f))
                    Text("Live radio", style = MaterialTheme.typography.labelLarge.copy(fontFamily = app.discair.ui.theme.LocalFontPair.current.mono), modifier = Modifier.semantics { heading() })
                    Spacer(Modifier.weight(1f))
                    Spacer(Modifier.size(Target)) // balances the close button
                }
                Spacer(Modifier.height(16.dp))
                Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()), horizontalAlignment = Alignment.CenterHorizontally) {
                    val shape = app.discair.ui.theme.themeShape(12.dp)
                    Box(
                        Modifier.widthIn(max = 480.dp).fillMaxWidth().aspectRatio(1f)
                            .then(if (palette.brutal) Modifier.brutalShadow(shape) else Modifier)
                            .clip(shape).background(MaterialTheme.colorScheme.surfaceVariant)
                            .then(if (palette.brutal) Modifier.border(app.discair.ui.theme.brutalOutline(), shape) else Modifier),
                    ) { Cover(artwork, Modifier.fillMaxSize(), onColor = { tint = it }) }
                    Spacer(Modifier.height(16.dp))
                    Text(
                        item.title, style = MaterialTheme.typography.titleLarge, textAlign = TextAlign.Center,
                        modifier = Modifier.fillMaxWidth().semantics { heading() },
                    )
                    // The live song, where the song sheet has the artist; spoken when it changes.
                    Text(
                        item.artist, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, textAlign = TextAlign.Center,
                        modifier = Modifier.fillMaxWidth().padding(top = 4.dp).semantics { liveRegion = LiveRegionMode.Polite },
                    )
                    live.now?.let { Note(it, live.proxied) }
                    Spacer(Modifier.height(8.dp))
                    // Status in words: buffering, lost connection, unavailable.
                    val status = radioStatusText(state, live)
                    if (status != null) Text(
                        status, style = MaterialTheme.typography.bodyMedium, color = app.discair.ui.theme.Ink.AccentText, textAlign = TextAlign.Center,
                        modifier = Modifier.fillMaxWidth().padding(top = 8.dp).semantics { liveRegion = LiveRegionMode.Polite },
                    )
                    if (state.signInRequired) TextButton(onClick = { controller.dismissSignIn(); onDismiss() }, Modifier.heightIn(min = Target)) { Text("Sign in again") }
                    if (state.waitingForNetwork || live.unreachable) TextButton(onClick = radio::retry, Modifier.heightIn(min = Target)) { Text("Retry now") }
                    Row(Modifier.fillMaxWidth().padding(vertical = 16.dp), horizontalArrangement = Arrangement.SpaceEvenly, verticalAlignment = Alignment.CenterVertically) {
                        val buttonSize = if (palette.brutal) 48.dp else Target
                        PlayerIconButton(
                            onClick = radio::toggleFavourite,
                            Modifier.size(buttonSize).semantics { stateDescription = if (live.favourite) "Favourite" else "Not a favourite" },
                            selected = live.favourite,
                        ) {
                            if (live.favourite) Icon(Icons.Default.Favorite, contentDescription = "Remove ${item.title} from favourites", tint = Ink.AccentText)
                            else Icon(Icons.Default.FavoriteBorder, contentDescription = "Add ${item.title} to favourites")
                        }
                        FilledIconButton(
                            onClick = controller::playPause, Modifier.size(64.dp),
                            colors = IconButtonDefaults.filledIconButtonColors(containerColor = MaterialTheme.colorScheme.primary, contentColor = MaterialTheme.colorScheme.onPrimary),
                        ) {
                            Icon(if (state.isPlaying) PlayerIcons.Pause else PlayerIcons.Play, contentDescription = if (state.isPlaying) "Pause" else "Play", modifier = Modifier.size(32.dp))
                        }
                        PlayerIconButton(onClick = onOpenHeard, Modifier.size(buttonSize)) { Icon(PlayerIcons.List, contentDescription = "Heard on radio") }
                    }
                    SleepTimerControl(sleep)
                    if (live.proxied) DownloadControl(live.download, onClick = { live.now?.playId?.let(radio::download) })
                    live.message?.let {
                        Text(it, Modifier.fillMaxWidth().padding(top = 8.dp).semantics { liveRegion = LiveRegionMode.Polite }, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, textAlign = TextAlign.Center)
                    }
                    Spacer(Modifier.height(24.dp))
                }
            }
        }
    }
}

/** The words for the stream's trouble, or null when there is none: reconnect progress, "Station unreachable", buffering. */
internal fun radioStatusText(state: PlayerUiState, live: app.discair.player.RadioLive): String? = when {
    live.unreachable -> "Station unreachable. Tried $RECONNECT_TRIES times. Check the connection, then retry."
    state.signInRequired -> state.status
    state.waitingForNetwork && live.reconnectAttempt > 0 -> "Station unreachable. Reconnecting (try ${live.reconnectAttempt} of $RECONNECT_TRIES)…"
    state.waitingForNetwork -> "Station unreachable. Reconnecting soon…"
    state.status != null -> state.status
    state.buffering -> "Buffering…"
    else -> null
}

private val RECONNECT_TRIES get() = app.discair.player.DEFAULT_BACKOFF_MS.size

/** The sleep timer: a button that says what is set and opens the lengths (and Off while one runs). Reads aloud as a button with its state. */
@Composable
internal fun SleepTimerControl(sleep: SleepTimer) {
    val left by sleep.remainingMs.collectAsState()
    var open by remember { mutableStateOf(false) }
    val text = sleepTimerText(left)
    Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
        OutlinedButton(onClick = { open = true }, Modifier.heightIn(min = Target).semantics { contentDescription = "$text. Change" }) { Text(text) }
        androidx.compose.material3.DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
            SLEEP_TIMER_MINUTES.forEach { minutes ->
                androidx.compose.material3.DropdownMenuItem(
                    text = { Text("$minutes minutes") },
                    onClick = { sleep.start(minutes); open = false },
                    modifier = Modifier.heightIn(min = Target),
                )
            }
            if (left != null) androidx.compose.material3.DropdownMenuItem(text = { Text("Turn off") }, onClick = { sleep.cancel(); open = false }, modifier = Modifier.heightIn(min = Target))
        }
    }
    Spacer(Modifier.height(8.dp))
}

/** The explanation under the song when there is no Download: no titles, unmatched title, relay off, unreachable (contract section 6). */
@Composable
internal fun Note(now: RadioNow, proxied: Boolean) {
    val words = when (now.state) {
        app.discair.model.RadioNowState.Ok, app.discair.model.RadioNowState.Idle -> null
        else -> radioNowText(now, proxied)
    } ?: return
    Text(words, Modifier.padding(top = 4.dp), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, textAlign = TextAlign.Center)
}

/** A text button for Download, Downloading, Downloaded, Owned or Try again. The state is words, not colour alone. */
@Composable
internal fun DownloadControl(download: RadioDownload, onClick: () -> Unit, modifier: Modifier = Modifier, noun: String = "this song") {
    OutlinedButton(
        onClick = { if (download.enabled) onClick() },
        modifier.heightIn(min = Target).semantics {
            contentDescription = "${download.label}: $noun"
            stateDescription = when (download) {
                RadioDownload.Waiting -> "Available once the song has been heard for about 30 seconds"
                RadioDownload.Ready -> "Not downloaded"
                RadioDownload.Working -> "Requesting"
                RadioDownload.Done -> "Requested. Follow it under Downloads"
                RadioDownload.Owned -> "Already in your library"
                RadioDownload.Failed -> "Could not request. Select to try again"
            }
        },
        enabled = download.enabled,
    ) {
        if (download == RadioDownload.Done || download == RadioDownload.Owned) Icon(Icons.Default.Check, contentDescription = null, Modifier.size(18.dp).padding(end = 0.dp))
        Text(download.label)
    }
}
