package app.discair.ui.radio

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import app.discair.model.RadioDownload
import app.discair.model.RadioNow
import app.discair.model.RadioPlay
import app.discair.model.RadioStation
import app.discair.model.radioLogoRequest
import app.discair.player.PlayerController
import app.discair.player.PlayerUiState
import app.discair.player.QueueItem
import app.discair.player.RadioLive
import app.discair.player.RadioPlayback
import app.discair.player.SleepTimer
import app.discair.ui.LocalBottomClearance
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.Cover
import app.discair.ui.common.FlowDivider
import app.discair.ui.common.FlowLargeTitle
import app.discair.ui.common.FlowPageBar
import app.discair.ui.common.FlowRules
import app.discair.ui.common.FlowSmallButton
import app.discair.ui.common.FlowTag
import app.discair.ui.common.Load
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.Target
import app.discair.ui.common.flowDepth
import app.discair.ui.theme.accentText
import app.discair.ui.home.Inline
import app.discair.ui.home.Muted
import app.discair.ui.player.FlowTransportButton
import app.discair.ui.player.PlayerIcons
import app.discair.ui.theme.LocalPalette
import java.text.DateFormat
import java.util.Date

/*
 * Flow's (Layout.Flow) Radio pages. Mockup: flow/radio, frames 1 to 3. RadioScreen, HeardScreen and RadioNowPlayingSheet reach this behind
 * isFlow(); the data, polling, favourites, playing and Get are theirs, unchanged, and the words and choices are CoverStackRadioRules'.
 */

/** The sizes of the radio pages (flow.css `.lg`, `.li .cv`, `.npc`, `.cb`). */
object FlowRadioRules {
    const val LOGO = 48
    const val LOGO_RADIUS = 10
    const val HEARD_COVER_RADIUS = 8
    const val LIVE_COVER = 312
    const val LIVE_COVER_RADIUS = 18
    const val SIDE_BUTTON = 48
    const val PLAY_BUTTON = 72
    const val GLYPH = 30
}

private val Margin = 16.dp

// ----- 1. stations ------------------------------------------------------------------------------------------------

/** Back, "Radio" and an accent "Heard on radio" in the bar; the large title; then one row per station with its logo, live line and a heart. */
@Composable
internal fun FlowStations(
    onBack: () -> Unit, onOpenHeard: () -> Unit, stations: Load<List<RadioStation>>, reload: () -> Unit, message: String?,
    favourite: (RadioStation) -> Boolean, now: (RadioStation) -> RadioNow?, onAirId: String?,
    onPlay: (RadioStation) -> Unit, onFavourite: (RadioStation) -> Unit,
) {
    val p = LocalPalette.current
    Column(Modifier.fillMaxSize()) {
        FlowPageBar(onBack, emptyList(), title = "Radio", trailing = {
            Box(Modifier.heightIn(min = Target).clickable(role = Role.Button, onClick = onOpenHeard).padding(horizontal = 8.dp), contentAlignment = Alignment.Center) {
                Text("Heard on radio", color = p.accentText, style = MaterialTheme.typography.labelLarge.copy(fontSize = 14.sp, fontWeight = FontWeight.Medium))
            }
        })
        LazyColumn(Modifier.fillMaxWidth(), contentPadding = PaddingValues(bottom = 24.dp + LocalBottomClearance.current)) {
            item { FlowLargeTitle("Radio", Modifier.padding(start = Margin, end = Margin, top = 8.dp, bottom = 8.dp)) }
            message?.let { text ->
                item(key = "message") {
                    Text(text, Modifier.padding(horizontal = Margin, vertical = 8.dp).semantics { liveRegion = LiveRegionMode.Polite }, color = p.chartRedText, style = MaterialTheme.typography.bodyMedium)
                }
            }
            when (stations) {
                Load.Loading -> item { Muted("Loading…") }
                is Load.Failed -> item { Inline(stations.failure.message, reload) }
                is Load.Ready -> {
                    if (stations.value.isEmpty()) item { Muted("No radio stations. Add them in Navidrome and they appear here.") }
                    itemsIndexed(stations.value, key = { _, s -> s.id }) { i, station ->
                        Column(Modifier.animateItem().padding(horizontal = Margin)) {
                            StationRow(station, favourite(station), now(station), onAirId == station.id, { onPlay(station) }, { onFavourite(station) })
                            if (i < stations.value.lastIndex) FlowDivider()
                        }
                    }
                }
            }
        }
    }
}

/** A 48dp logo (radius 10), the name (accent while on air) and the live line, a heart (flow.css `.li`, `.li.on h4`). */
@Composable
private fun StationRow(station: RadioStation, favourite: Boolean, now: RadioNow?, onAir: Boolean, onPlay: () -> Unit, onFavourite: () -> Unit) {
    val p = LocalPalette.current
    val repo = LocalRepository.current
    Row(
        Modifier.fillMaxWidth().heightIn(min = FlowRules.ROW_MIN.dp).clickable(onClickLabel = "Play ${station.name}", role = Role.Button, onClick = onPlay)
            .padding(vertical = 8.dp).semantics { if (onAir) stateDescription = "On air" },
        horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
    ) {
        Cover(radioLogoRequest(repo.absolute(station.logoUrl), 128), Modifier.size(FlowRadioRules.LOGO.dp).clip(RoundedCornerShape(FlowRadioRules.LOGO_RADIUS.dp)), rect = true)
        Column(Modifier.weight(1f)) {
            Text(
                station.name, color = if (onAir) p.accentText else p.text, maxLines = 1, overflow = TextOverflow.Ellipsis,
                style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 15.sp, lineHeight = 20.sp),
            )
            Text(stripText(station, now), color = p.textMuted, maxLines = 2, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall.copy(fontSize = 12.sp, lineHeight = 18.sp))
        }
        Box(
            Modifier.size(Target).clip(CircleShape).clickable(role = Role.Button, onClick = onFavourite)
                .semantics { contentDescription = if (favourite) "Remove ${station.name} from favourites" else "Add ${station.name} to favourites" },
            contentAlignment = Alignment.Center,
        ) { Icon(if (favourite) Icons.Default.Favorite else Icons.Default.FavoriteBorder, contentDescription = null, tint = p.text) }
    }
}

// ----- 3. heard on radio ------------------------------------------------------------------------------------------

/** The Heard list: the large title and its line, then a 48dp cover, the song, "Artist · Station · time" with the state in words, and Get, a check or the requested mark. */
@Composable
internal fun FlowHeard(onBack: () -> Unit, plays: Load<List<RadioPlay>>, reload: () -> Unit, live: RadioLive, onDownload: (Long) -> Unit) {
    val p = LocalPalette.current
    Column(Modifier.fillMaxSize()) {
        FlowPageBar(onBack, emptyList(), title = "Heard on radio")
        LazyColumn(Modifier.fillMaxWidth(), contentPadding = PaddingValues(bottom = 24.dp + LocalBottomClearance.current)) {
            item {
                Column(Modifier.padding(start = Margin, end = Margin, top = 8.dp, bottom = 8.dp)) {
                    FlowLargeTitle("Heard on radio")
                    Text("Songs the stations played while you listened", color = p.textMuted, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(top = 2.dp))
                }
            }
            live.message?.let { text ->
                item(key = "message") { Text(text, Modifier.padding(horizontal = Margin, vertical = 8.dp).semantics { liveRegion = LiveRegionMode.Polite }, color = p.text, style = MaterialTheme.typography.bodyMedium) }
            }
            when (plays) {
                Load.Loading -> item { Muted("Loading…") }
                is Load.Failed -> item { Inline(plays.failure.message, reload) }
                is Load.Ready -> {
                    if (plays.value.isEmpty()) item { Muted("Nothing heard yet. A song is logged once you have listened to it for about 30 seconds.") }
                    itemsIndexed(plays.value, key = { _, play -> play.id }) { i, play ->
                        Column(Modifier.animateItem().padding(horizontal = Margin)) {
                            HeardRow(play, live.downloadFor(play.id, play.grabbed, play.inLibrary), live.failed[play.id]) { onDownload(play.id) }
                            if (i < plays.value.lastIndex) FlowDivider()
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun HeardRow(play: RadioPlay, download: RadioDownload, failure: String?, onDownload: () -> Unit) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(FlowRadioRules.HEARD_COVER_RADIUS.dp)
    val trailing = CoverStackRadioRules.trailing(play.hasArtist, download)
    val time = play.heardAt?.let { DateFormat.getTimeInstance(DateFormat.SHORT).format(Date((it * 1000).toLong())) }
    val words = CoverStackRadioRules.stateWords(trailing)
    val line: AnnotatedString = buildAnnotatedString {
        append(CoverStackRadioRules.heardLine(play, time))
        if (words != null) { append(" · "); withStyle(SpanStyle(color = if (trailing == CoverStackRadioRules.Trailing.InLibrary) p.ok else p.textMuted, fontWeight = FontWeight.Medium)) { append(words) } }
    }
    Row(
        Modifier.fillMaxWidth().heightIn(min = FlowRules.ROW_MIN.dp).padding(vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
    ) {
        val album = play.album?.takeIf { it.isNotBlank() }
        val artist = play.artist?.takeIf { it.isNotBlank() }
        val frame = Modifier.size(FlowRadioRules.LOGO.dp).clip(shape)
        if (artist != null && album != null) AlbumCover(artist, album, null, frame, rect = true) else Box(frame.background(p.raised))
        Column(Modifier.weight(1f)) {
            Text(play.title, color = p.text, maxLines = 2, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 15.sp, lineHeight = 20.sp))
            Text(line, color = p.textMuted, maxLines = 2, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall.copy(fontSize = 12.sp, lineHeight = 18.sp))
            failure?.let { Text(it, color = p.chartRedText, style = MaterialTheme.typography.bodySmall) }
        }
        when (trailing) {
            CoverStackRadioRules.Trailing.Get -> FlowSmallButton("Get", null, true, "Download: ${play.title}", onClick = onDownload)
            CoverStackRadioRules.Trailing.TryAgain -> FlowSmallButton("Try again", null, true, "Try again: ${play.title}", onClick = onDownload)
            CoverStackRadioRules.Trailing.InLibrary -> Icon(Icons.Default.Check, contentDescription = "In your library: ${play.title}", tint = p.ok, modifier = Modifier.size(24.dp))
            CoverStackRadioRules.Trailing.Requested -> Icon(PlayerIcons.DownloadToDevice, contentDescription = "Requested. Follow it under Downloads: ${play.title}", tint = p.text, modifier = Modifier.size(24.dp))
            CoverStackRadioRules.Trailing.Working -> Unit // the line above says "Requesting…"
            CoverStackRadioRules.Trailing.None -> Unit
        }
    }
}

// ----- 2. live radio ----------------------------------------------------------------------------------------------

/** The sheet's whole body for Flow: the bar, the 312dp station tile with depth, On air, the song, the three buttons and Get this song. */
@Composable
internal fun FlowRadioNow(
    state: PlayerUiState, controller: PlayerController, radio: RadioPlayback, sleep: SleepTimer, live: RadioLive, item: QueueItem,
    artwork: String?, status: String?, onDismiss: () -> Unit, onOpenHeard: () -> Unit,
) {
    val p = LocalPalette.current
    val coverShape = RoundedCornerShape(FlowRadioRules.LIVE_COVER_RADIUS.dp)
    val (headline, under) = CoverStackRadioRules.headline(item.title, live.now, item.artist)
    Column(Modifier.fillMaxWidth().fillMaxHeight()) { // full height, like Now Playing, so the sheet's top edge is the top of the screen
        Row(Modifier.fillMaxWidth().heightIn(min = 48.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(Target).clip(CircleShape).clickable(role = Role.Button, onClick = onDismiss), contentAlignment = Alignment.Center) {
                Icon(PlayerIcons.Down, contentDescription = "Close now playing", tint = p.accentText)
            }
            Box(Modifier.weight(1f).semantics { heading() }, contentAlignment = Alignment.Center) { app.discair.ui.common.FlowEyebrow("Live radio") }
            Box(Modifier.size(Target).clip(CircleShape).clickable(role = Role.Button, onClick = onOpenHeard), contentAlignment = Alignment.Center) {
                Icon(PlayerIcons.List, contentDescription = "Heard on radio", tint = p.accentText)
            }
        }
        Column(Modifier.fillMaxWidth().weight(1f).verticalScroll(rememberScrollState()), horizontalAlignment = Alignment.CenterHorizontally) {
            Box(Modifier.fillMaxWidth().padding(top = 8.dp, bottom = 16.dp), contentAlignment = Alignment.Center) {
                Box(Modifier.widthIn(max = FlowRadioRules.LIVE_COVER.dp).fillMaxWidth().aspectRatio(1f).flowDepth(3, coverShape, p).clip(coverShape)) {
                    Cover(artwork, Modifier.fillMaxSize(), rect = true)
                }
            }
            FlowTag(CoverStackRadioRules.airTag(state.isPlaying), tint = p.accentDim, labelColor = p.text)
            Text(
                headline, color = p.text, textAlign = TextAlign.Center, maxLines = 2, overflow = TextOverflow.Ellipsis,
                style = MaterialTheme.typography.headlineMedium.copy(fontSize = 24.sp, lineHeight = 28.sp, fontWeight = FontWeight.Bold, letterSpacing = (-0.02).em),
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp).semantics { heading() },
            )
            if (under.isNotBlank()) Text(
                under, color = p.textMuted, textAlign = TextAlign.Center, style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.fillMaxWidth().padding(top = 2.dp).semantics { liveRegion = LiveRegionMode.Polite },
            )
            live.now?.let { Note(it, live.proxied) }
            // Trouble with the stream, in words, with the ways out (unchanged).
            if (status != null) Text(
                status, color = p.text, textAlign = TextAlign.Center, style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp).semantics { liveRegion = LiveRegionMode.Polite },
            )
            if (state.signInRequired) TextButton(onClick = { controller.dismissSignIn(); onDismiss() }, Modifier.heightIn(min = Target)) { Text("Sign in again", color = p.accentText, textDecoration = TextDecoration.Underline) }
            if (state.waitingForNetwork || live.unreachable) TextButton(onClick = radio::retry, Modifier.heightIn(min = Target)) { Text("Retry now", color = p.accentText, textDecoration = TextDecoration.Underline) }
            Row(Modifier.fillMaxWidth().padding(vertical = 16.dp), horizontalArrangement = Arrangement.spacedBy(28.dp, Alignment.CenterHorizontally), verticalAlignment = Alignment.CenterVertically) {
                FlowTransportButton(
                    if (live.favourite) "Remove ${item.title} from favourites" else "Add ${item.title} to favourites", radio::toggleFavourite,
                    state = if (live.favourite) "Favourite" else "Not a favourite",
                ) { ink -> Icon(if (live.favourite) Icons.Default.Favorite else Icons.Default.FavoriteBorder, contentDescription = null, tint = ink, modifier = Modifier.size(24.dp)) }
                FlowTransportButton(if (state.isPlaying) "Pause" else "Play", controller::playPause, size = FlowRadioRules.PLAY_BUTTON, main = true) { ink ->
                    Icon(if (state.isPlaying) PlayerIcons.Pause else PlayerIcons.Play, contentDescription = null, tint = ink, modifier = Modifier.size(32.dp))
                }
                FlowTransportButton("Heard on radio", onOpenHeard) { ink -> Icon(PlayerIcons.List, contentDescription = null, tint = ink, modifier = Modifier.size(FlowRadioRules.GLYPH.dp)) }
            }
            if (live.proxied) {
                val download = live.download
                WideButton(CoverStackRadioRules.getLabel(download), download.enabled, "${download.label}: this song") { live.now?.playId?.let(radio::download) }
            }
            live.message?.let {
                Text(it, Modifier.fillMaxWidth().padding(top = 10.dp).semantics { liveRegion = LiveRegionMode.Polite }, color = p.textMuted, textAlign = TextAlign.Center, style = MaterialTheme.typography.bodySmall)
            }
            Spacer(Modifier.height(8.dp))
            SleepTimerControl(sleep)
            Spacer(Modifier.height(16.dp))
        }
    }
}

/** The full-width 44dp capsule with the download glyph (flow.css `.btn.p`). A disabled one is `raised` with muted words. */
@Composable
private fun WideButton(label: String, enabled: Boolean, description: String, onClick: () -> Unit) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(22.dp)
    Row(
        Modifier.fillMaxWidth().height(44.dp).clip(shape).background(if (enabled) p.accent else p.raised)
            .clickable(enabled = enabled, role = Role.Button, onClick = onClick).semantics { contentDescription = description },
        horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(PlayerIcons.DownloadToDevice, contentDescription = null, tint = if (enabled) p.onAccent else p.textMuted, modifier = Modifier.size(20.dp))
        Text(label, Modifier.padding(start = 8.dp), color = if (enabled) p.onAccent else p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.labelLarge.copy(fontSize = 15.sp, fontWeight = FontWeight.SemiBold))
    }
}
