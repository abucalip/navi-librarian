package app.discair.ui.radio

import androidx.compose.foundation.border
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxHeight
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
import app.discair.model.RadioNowState
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
import app.discair.ui.common.CoverStackDivider
import app.discair.ui.common.CoverStackRules
import app.discair.ui.common.CoverStackTitle
import app.discair.ui.common.CoverStackTopBar
import app.discair.ui.common.Load
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.Target
import app.discair.ui.common.coverStackFrame
import app.discair.ui.common.coverStackShadow
import app.discair.ui.discover.CoverStackLink
import app.discair.ui.discover.SmallButton
import app.discair.ui.home.Inline
import app.discair.ui.home.Muted
import app.discair.ui.player.CsButton
import app.discair.ui.player.Eyebrow
import app.discair.ui.player.PlayerIcons
import app.discair.ui.theme.LocalPalette
import java.text.DateFormat
import java.util.Date

/*
 * Soft Brut's (Layout.CoverStack) Radio pages. Mockup: soft-brut/radio, frames 1 to 3. RadioScreen, HeardScreen and RadioNowPlayingSheet
 * reach this behind isCoverStack(); the data, polling, favourites, playing and Get are theirs, unchanged.
 */

/** The words and choices of the radio pages that are not drawing. */
object CoverStackRadioRules {
    /** What the Get control on a Heard row is. */
    enum class Trailing { Get, TryAgain, InLibrary, Requested, Working, None }

    fun trailing(hasArtist: Boolean, download: RadioDownload): Trailing = when {
        !hasArtist -> Trailing.None // a song with no named artist cannot be looked up, so no dead button
        else -> when (download) {
            RadioDownload.Ready, RadioDownload.Waiting -> Trailing.Get
            RadioDownload.Failed -> Trailing.TryAgain
            RadioDownload.Owned -> Trailing.InLibrary
            RadioDownload.Done -> Trailing.Requested
            RadioDownload.Working -> Trailing.Working
        }
    }

    /** The state said in words after the time on a Heard row; null when there is nothing to add. */
    fun stateWords(trailing: Trailing): String? = when (trailing) {
        Trailing.InLibrary -> "In your library"
        Trailing.Requested -> "Requested"
        Trailing.Working -> "Requesting…"
        else -> null
    }

    /** "Talk Talk · FIP · 21:09": the artist (or "Artist not named"), the station and the time heard, each only when known. */
    fun heardLine(play: RadioPlay, time: String?): String =
        listOfNotNull(play.artist?.takeIf { it.isNotBlank() } ?: "Artist not named", play.stationName.takeIf { it.isNotBlank() }, time).joinToString(" · ")

    /** The big line and the line under it on the live sheet: the song and "Artist · heard on Station", else the station and the live words. */
    fun headline(stationName: String, now: RadioNow?, liveLine: String): Pair<String, String> {
        val song = now?.takeIf { it.state == RadioNowState.Ok }?.title?.takeIf { it.isNotBlank() }
        if (song == null) return stationName to liveLine
        val artist = now.artist?.takeIf { it.isNotBlank() }
        val on = stationName.takeIf { it.isNotBlank() }
        return song to when {
            artist != null && on != null -> "$artist · heard on $on"
            artist != null -> artist
            on != null -> "Heard on $on"
            else -> ""
        }
    }

    /** The tag over the title. */
    fun airTag(playing: Boolean): String = if (playing) "On air" else "Paused"

    /** The wide button's words: "Get this song" while it can be asked for, the control's own words otherwise. */
    fun getLabel(download: RadioDownload): String = if (download == RadioDownload.Ready) "Get this song" else download.label
}

// ----- 1. stations ------------------------------------------------------------------------------------------------

/** Back, the title and "Heard on radio" in the bar; the title; then one row per station with its logo, live line and a heart. */
@Composable
internal fun CoverStackStations(
    onBack: () -> Unit, onOpenHeard: () -> Unit, stations: Load<List<RadioStation>>, reload: () -> Unit, message: String?,
    favourite: (RadioStation) -> Boolean, now: (RadioStation) -> RadioNow?, onAirId: String?,
    onPlay: (RadioStation) -> Unit, onFavourite: (RadioStation) -> Unit,
) {
    val p = LocalPalette.current
    Column(Modifier.fillMaxSize()) {
        CoverStackTopBar(onBack, emptyList(), title = "Radio", trailing = { CoverStackLink("Heard on radio", Modifier.padding(end = 12.dp), onOpenHeard) })
        LazyColumn(Modifier.fillMaxWidth(), contentPadding = PaddingValues(bottom = 24.dp + LocalBottomClearance.current)) {
            item { CoverStackTitle("Radio", Modifier.padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 8.dp), maxLines = 1) }
            message?.let { text ->
                item(key = "message") {
                    Text(text, Modifier.padding(horizontal = 16.dp, vertical = 8.dp).semantics { liveRegion = LiveRegionMode.Polite }, color = p.chartRedText, style = MaterialTheme.typography.bodyMedium)
                }
            }
            when (stations) {
                Load.Loading -> item { Muted("Loading…") }
                is Load.Failed -> item { Inline(stations.failure.message, reload) }
                is Load.Ready -> {
                    if (stations.value.isEmpty()) item { Muted("No radio stations. Add them in Navidrome and they appear here.") }
                    itemsIndexed(stations.value, key = { _, s -> s.id }) { i, station ->
                        Column(Modifier.animateItem()) {
                            StationRow(station, favourite(station), now(station), onAirId == station.id, { onPlay(station) }, { onFavourite(station) })
                            if (i < stations.value.lastIndex) CoverStackDivider(Modifier.padding(horizontal = 16.dp))
                        }
                    }
                }
            }
        }
    }
}

/** A 48dp outlined logo, the name and the live line, a heart. The station on air is filled with the pale accent (mockup `.li.on`). */
@Composable
private fun StationRow(station: RadioStation, favourite: Boolean, now: RadioNow?, onAir: Boolean, onPlay: () -> Unit, onFavourite: () -> Unit) {
    val p = LocalPalette.current
    val repo = LocalRepository.current
    val shape = RoundedCornerShape(6.dp)
    Row(
        Modifier.fillMaxWidth().padding(horizontal = 4.dp).then(if (onAir) Modifier.background(p.accentDim) else Modifier)
            .heightIn(min = 64.dp).clickable(onClickLabel = "Play ${station.name}", role = Role.Button, onClick = onPlay)
            .padding(start = 12.dp, end = 0.dp, top = 8.dp, bottom = 8.dp)
            .semantics { if (onAir) stateDescription = "On air" },
        horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
    ) {
        Cover(radioLogoRequest(repo.absolute(station.logoUrl), 128), Modifier.size(48.dp).clip(shape).border(CoverStackRules.outline(p).dp, p.edgeStrong, shape), rect = true)
        Column(Modifier.weight(1f)) {
            Text(station.name, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 14.sp))
            Text(stripText(station, now), color = p.textMuted, maxLines = 2, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall)
        }
        Box(
            Modifier.size(Target).clip(CircleShape).clickable(role = Role.Button, onClick = onFavourite)
                .semantics { contentDescription = if (favourite) "Remove ${station.name} from favourites" else "Add ${station.name} to favourites" },
            contentAlignment = Alignment.Center,
        ) { Icon(if (favourite) Icons.Default.Favorite else Icons.Default.FavoriteBorder, contentDescription = null, tint = p.text) }
    }
}

// ----- 3. heard on radio ------------------------------------------------------------------------------------------

/** The Heard list: a 48dp cover, the song, "Artist · Station · time" with the state in words, and Get, a check or the requested mark. */
@Composable
internal fun CoverStackHeard(
    onBack: () -> Unit, plays: Load<List<RadioPlay>>, reload: () -> Unit, live: RadioLive, onDownload: (Long) -> Unit,
) {
    val p = LocalPalette.current
    Column(Modifier.fillMaxSize()) {
        CoverStackTopBar(onBack, emptyList(), title = "Heard on radio")
        LazyColumn(Modifier.fillMaxWidth(), contentPadding = PaddingValues(bottom = 24.dp + LocalBottomClearance.current)) {
            item {
                Column(Modifier.padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 8.dp)) {
                    CoverStackTitle("Heard on radio", maxLines = 2)
                    Text("Songs the stations played while you listened", color = p.textMuted, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(top = 4.dp))
                }
            }
            live.message?.let { text ->
                item(key = "message") { Text(text, Modifier.padding(horizontal = 16.dp, vertical = 8.dp).semantics { liveRegion = LiveRegionMode.Polite }, color = p.text, style = MaterialTheme.typography.bodyMedium) }
            }
            when (plays) {
                Load.Loading -> item { Muted("Loading…") }
                is Load.Failed -> item { Inline(plays.failure.message, reload) }
                is Load.Ready -> {
                    if (plays.value.isEmpty()) item { Muted("Nothing heard yet. A song is logged once you have listened to it for about 30 seconds.") }
                    itemsIndexed(plays.value, key = { _, play -> play.id }) { i, play ->
                        Column(Modifier.animateItem()) {
                            HeardRow(play, live.downloadFor(play.id, play.grabbed, play.inLibrary), live.failed[play.id]) { onDownload(play.id) }
                            if (i < plays.value.lastIndex) CoverStackDivider(Modifier.padding(horizontal = 16.dp))
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
    val shape = RoundedCornerShape(6.dp)
    val trailing = CoverStackRadioRules.trailing(play.hasArtist, download)
    val time = play.heardAt?.let { DateFormat.getTimeInstance(DateFormat.SHORT).format(Date((it * 1000).toLong())) }
    val words = CoverStackRadioRules.stateWords(trailing)
    val line: AnnotatedString = buildAnnotatedString {
        append(CoverStackRadioRules.heardLine(play, time))
        if (words != null) { append(" · "); withStyle(SpanStyle(color = if (trailing == CoverStackRadioRules.Trailing.InLibrary) p.ok else p.textMuted, fontWeight = FontWeight.Medium)) { append(words) } }
    }
    Row(
        Modifier.fillMaxWidth().heightIn(min = 64.dp).padding(start = 16.dp, end = 12.dp, top = 8.dp, bottom = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
    ) {
        val album = play.album?.takeIf { it.isNotBlank() }
        val artist = play.artist?.takeIf { it.isNotBlank() }
        val frame = Modifier.size(48.dp).clip(shape).border(CoverStackRules.outline(p).dp, p.edgeStrong, shape)
        if (artist != null && album != null) AlbumCover(artist, album, null, frame, rect = true) else Box(frame.background(p.raised))
        Column(Modifier.weight(1f)) {
            Text(play.title, color = p.text, maxLines = 2, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 14.sp))
            Text(line, color = p.textMuted, maxLines = 2, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall)
            failure?.let { Text(it, color = p.chartRedText, style = MaterialTheme.typography.bodySmall) }
        }
        when (trailing) {
            CoverStackRadioRules.Trailing.Get -> SmallButton("Get", null, true, "Download: ${play.title}", Modifier.width64(), onClick = onDownload)
            CoverStackRadioRules.Trailing.TryAgain -> SmallButton("Try again", null, true, "Try again: ${play.title}", Modifier.size(width = 96.dp, height = Target), onClick = onDownload)
            CoverStackRadioRules.Trailing.InLibrary -> Icon(Icons.Default.Check, contentDescription = "In your library: ${play.title}", tint = p.ok, modifier = Modifier.size(24.dp))
            CoverStackRadioRules.Trailing.Requested -> Icon(PlayerIcons.DownloadToDevice, contentDescription = "Requested. Follow it under Downloads: ${play.title}", tint = p.text, modifier = Modifier.size(24.dp))
            CoverStackRadioRules.Trailing.Working -> Unit // the line above says "Requesting…"
            CoverStackRadioRules.Trailing.None -> Unit
        }
    }
}

private fun Modifier.width64(): Modifier = this.then(Modifier.size(width = 64.dp, height = Target))

// ----- 2. live radio ----------------------------------------------------------------------------------------------

/** The sheet's whole body for Soft Brut: the bar, the outlined station logo, On air, the song, the three buttons and Get this song. */
@Composable
internal fun CoverStackRadioNow(
    state: PlayerUiState, controller: PlayerController, radio: RadioPlayback, sleep: SleepTimer, live: RadioLive, item: QueueItem,
    artwork: String?, status: String?, onDismiss: () -> Unit, onOpenHeard: () -> Unit,
) {
    val p = LocalPalette.current
    val coverShape = RoundedCornerShape(14.dp)
    val (headline, under) = CoverStackRadioRules.headline(item.title, live.now, item.artist)
    Column(Modifier.fillMaxWidth().fillMaxHeight()) { // full height, like Now Playing, so the sheet's top edge is the top of the screen
        Row(Modifier.fillMaxWidth().heightIn(min = 48.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(Target).clip(CircleShape).clickable(role = Role.Button, onClick = onDismiss), contentAlignment = Alignment.Center) {
                Icon(PlayerIcons.Down, contentDescription = "Close now playing", tint = p.text)
            }
            Box(Modifier.weight(1f), contentAlignment = Alignment.Center) { Eyebrow("Live radio", heading = true) }
            Box(Modifier.size(Target).clip(CircleShape).clickable(role = Role.Button, onClick = onOpenHeard), contentAlignment = Alignment.Center) {
                Icon(PlayerIcons.List, contentDescription = "Heard on radio", tint = p.text)
            }
        }
        Column(Modifier.fillMaxWidth().weight(1f).verticalScroll(rememberScrollState()), horizontalAlignment = Alignment.CenterHorizontally) {
            Box(Modifier.fillMaxWidth().padding(top = 4.dp, bottom = 12.dp), contentAlignment = Alignment.Center) {
                Box(
                    Modifier.widthIn(max = 296.dp).fillMaxWidth().aspectRatio(1f).coverStackShadow(coverShape, p, 5f).clip(coverShape)
                        .border(CoverStackRules.outline(p).dp, p.edgeStrong, coverShape),
                ) { Cover(artwork, Modifier.fillMaxSize(), rect = true) }
            }
            CoverStackTag(CoverStackRadioRules.airTag(state.isPlaying))
            Text(
                headline, color = p.text, textAlign = TextAlign.Center, maxLines = 2, overflow = TextOverflow.Ellipsis,
                style = MaterialTheme.typography.headlineLarge.copy(fontSize = 26.sp, lineHeight = 30.sp, fontWeight = FontWeight.Bold),
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
            if (state.signInRequired) TextButton(onClick = { controller.dismissSignIn(); onDismiss() }, Modifier.heightIn(min = Target)) { Text("Sign in again", color = p.text, textDecoration = TextDecoration.Underline) }
            if (state.waitingForNetwork || live.unreachable) TextButton(onClick = radio::retry, Modifier.heightIn(min = Target)) { Text("Retry now", color = p.text, textDecoration = TextDecoration.Underline) }
            Row(Modifier.fillMaxWidth().padding(vertical = 16.dp), horizontalArrangement = Arrangement.spacedBy(28.dp, Alignment.CenterHorizontally), verticalAlignment = Alignment.CenterVertically) {
                CsButton(
                    if (live.favourite) "Remove ${item.title} from favourites" else "Add ${item.title} to favourites", 48, radio::toggleFavourite,
                    state = if (live.favourite) "Favourite" else "Not a favourite",
                ) { ink -> Icon(if (live.favourite) Icons.Default.Favorite else Icons.Default.FavoriteBorder, contentDescription = null, tint = ink) }
                CsButton(if (state.isPlaying) "Pause" else "Play", 68, controller::playPause, radius = 14, primary = true) { ink ->
                    Icon(if (state.isPlaying) PlayerIcons.Pause else PlayerIcons.Play, contentDescription = null, tint = ink, modifier = Modifier.size(32.dp))
                }
                CsButton("Heard on radio", 48, onOpenHeard) { ink -> Icon(PlayerIcons.List, contentDescription = null, tint = ink) }
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

/** The "On air" tag: mono caps in an outlined radius-6 tag on the accent (mockup `.tag.a`). */
@Composable
private fun CoverStackTag(text: String) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(6.dp)
    Text(
        text.uppercase(), color = p.onAccent, maxLines = 1,
        style = MaterialTheme.typography.labelSmall.copy(fontFamily = app.discair.ui.theme.LocalFontPair.current.mono, fontSize = 10.sp, lineHeight = 14.sp, fontWeight = FontWeight.Medium, letterSpacing = 0.07.em),
        modifier = Modifier.clip(shape).background(p.accent).border(CoverStackRules.outline(p).dp, p.edgeStrong, shape).padding(horizontal = 7.dp, vertical = 2.dp),
    )
}

/** The full-width 44dp primary button with the download glyph (mockup `.btn.p`). A disabled one is drawn flat on the raised fill. */
@Composable
private fun WideButton(label: String, enabled: Boolean, description: String, onClick: () -> Unit) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(CoverStackRules.radius(p).dp)
    Box(Modifier.fillMaxWidth().padding(end = CoverStackRules.shadow(p).dp)) {
        Row(
            Modifier.fillMaxWidth().height(48.dp).then(if (enabled) Modifier.coverStackFrame(shape, p, p.accent) else Modifier.clip(shape).background(p.raised).border(CoverStackRules.outline(p).dp, p.edgeStrong, shape))
                .clickable(enabled = enabled, role = Role.Button, onClick = onClick).semantics { contentDescription = description },
            horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(PlayerIcons.DownloadToDevice, contentDescription = null, tint = if (enabled) p.onAccent else p.textMuted, modifier = Modifier.size(20.dp))
            Text(label, Modifier.padding(start = 8.dp), color = if (enabled) p.onAccent else p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.labelLarge.copy(fontSize = 14.sp, fontWeight = FontWeight.Bold))
        }
    }
}
