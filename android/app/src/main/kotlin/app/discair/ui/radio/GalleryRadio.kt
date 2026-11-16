package app.discair.ui.radio

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.graphics.vector.PathParser
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.model.RadioDownload
import app.discair.model.RadioNow
import app.discair.model.RadioNowState
import app.discair.model.RadioPlay
import app.discair.model.RadioStation
import app.discair.model.radioLogoRequest
import app.discair.model.radioNowText
import app.discair.player.PlayerController
import app.discair.player.PlayerUiState
import app.discair.player.QueueItem
import app.discair.player.RadioLive
import app.discair.player.RadioPlayback
import app.discair.player.SleepTimer
import app.discair.ui.LocalBottomClearance
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.Cover
import app.discair.ui.common.GalleryButton
import app.discair.ui.common.GalleryButtonKind
import app.discair.ui.common.GalleryIconButton
import app.discair.ui.common.GalleryIcons
import app.discair.ui.common.GalleryMenuButton
import app.discair.ui.common.GalleryPageBar
import app.discair.ui.common.GalleryPageHead
import app.discair.ui.common.GalleryPlayingBars
import app.discair.ui.common.GalleryPrint
import app.discair.ui.common.galleryArrive
import app.discair.ui.common.GalleryRow
import app.discair.ui.common.GalleryRules
import app.discair.ui.common.GalleryState
import app.discair.ui.common.GalleryType
import app.discair.ui.common.Load
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.gallerySpot
import app.discair.ui.home.GalleryHomeRules
import app.discair.ui.home.Inline
import app.discair.ui.home.Muted
import app.discair.ui.theme.LocalPalette
import java.text.DateFormat
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Date
import java.util.Locale

/*
 * Gallery's (Layout.Gallery) Radio pages. Mockup: docs/design/gallery/pages/radio, frames 1 to 3. RadioScreen, HeardScreen and RadioNowPlayingSheet reach this
 * behind isGallery(); the data, polling, favourites, playing and Get are theirs, unchanged, and the words are CoverStackRadioRules' where the other themes share them.
 */

/** The pure words of Gallery's Radio pages (unit-tested). */
object GalleryRadioRules {
    const val LOGO_PRINT = 52
    const val ROW_PRINT = 48
    const val LIVE_PRINT = 300

    /** "6 stations" (the singular for one); empty while none are known. */
    fun stationCount(count: Int): String = when (count) { 0 -> ""; 1 -> "1 station"; else -> "$count stations" }

    /** The live page's catalogue line: "On air · FIP", or "Paused · FIP" while it is not playing. */
    fun airLine(playing: Boolean, station: String): String =
        listOf(CoverStackRadioRules.airTag(playing), station.trim().takeIf { it.isNotEmpty() }).filterNotNull().joinToString(" · ")

    /** The line under the live song: the artist when the title was parsed, else what the other themes say ([fallback]). */
    fun byLine(now: RadioNow?, fallback: String): String =
        now?.takeIf { it.state == RadioNowState.Ok }?.artist?.takeIf { it.isNotBlank() } ?: fallback

    /** The Heard page's catalogue line, from when the newest song was heard: "Tonight", "This morning", "This afternoon", "Yesterday" or the date. Empty when no time is known. */
    fun heardEyebrow(plays: List<RadioPlay>, now: Instant, zone: ZoneId = ZoneId.systemDefault(), locale: Locale = Locale.getDefault()): String {
        val at = plays.mapNotNull { it.heardAt }.maxOrNull() ?: return ""
        val time = Instant.ofEpochMilli((at * 1000).toLong()).atZone(zone)
        val ago = java.time.temporal.ChronoUnit.DAYS.between(time.toLocalDate(), now.atZone(zone).toLocalDate())
        return when {
            ago <= 0 -> when { time.hour < 12 -> "This morning"; time.hour < 18 -> "This afternoon"; else -> "Tonight" }
            ago == 1L -> "Yesterday"
            else -> DateTimeFormatter.ofPattern("d MMMM", locale).format(time)
        }
    }

    /** A title in Fraunces italic is a named work: a song with no artist ("Untitled", "Artist not named") is set upright. */
    fun italicTitle(play: RadioPlay): Boolean = play.hasArtist
}

/** The favourite heart, filled: the same path as [GalleryIcons.Heart] with a fill (the icon set draws outlines only). */
private val HeartOn: ImageVector by lazy {
    ImageVector.Builder("heartOn", 24.dp, 24.dp, 24f, 24f).addPath(
        PathParser().parsePathString("M12 19.5s-7-4.2-7-9.3A3.9 3.9 0 0 1 12 8a3.9 3.9 0 0 1 7 2.2c0 5.1-7 9.3-7 9.3z").toNodes(),
        fill = SolidColor(Color.Black), stroke = SolidColor(Color.Black), strokeLineWidth = 1.4f, strokeLineCap = StrokeCap.Round, strokeLineJoin = StrokeJoin.Round,
    ).build()
}

/** A station's logo on an initials tile: the tile shows while the logo loads and when there is none. */
@Composable
private fun StationLogo(station: RadioStation?, name: String, artwork: String?, initialsSize: Float) {
    val repo = LocalRepository.current
    val p = LocalPalette.current
    Box(Modifier.fillMaxWidth().aspectRatio(1f).background(p.raised), contentAlignment = Alignment.Center) {
        Text(GalleryHomeRules.initials(name), color = p.textMuted, style = GalleryType.rowTitle().copy(fontSize = initialsSize.sp), maxLines = 1)
        Cover(artwork ?: station?.let { radioLogoRequest(repo.absolute(it.logoUrl), 128) }, Modifier.fillMaxWidth().aspectRatio(1f), rect = true)
    }
}

// ----- 1. stations ------------------------------------------------------------------------------------------------

/** Back, "Radio" and an underlined "Heard on radio" in the bar; the count and the large title; then one row per station with its logo print, live line and a heart. */
@Composable
internal fun GalleryStations(
    onBack: () -> Unit, onOpenHeard: () -> Unit, stations: Load<List<RadioStation>>, reload: () -> Unit, message: String?,
    favourite: (RadioStation) -> Boolean, now: (RadioStation) -> RadioNow?, onAirId: String?, playing: Boolean,
    onPlay: (RadioStation) -> Unit, onFavourite: (RadioStation) -> Unit,
) {
    val p = LocalPalette.current
    Column(Modifier.fillMaxSize()) {
        GalleryPageBar("Radio", onBack, action = {
            Box(Modifier.heightIn(min = 48.dp).clickable(role = Role.Button, onClick = onOpenHeard).padding(horizontal = 12.dp), contentAlignment = Alignment.Center) {
                Text("Heard on radio", style = GalleryType.body().copy(fontSize = 12.5.sp), color = p.text, textDecoration = TextDecoration.Underline, maxLines = 1)
            }
        })
        LazyColumn(Modifier.fillMaxWidth(), contentPadding = PaddingValues(bottom = 24.dp + LocalBottomClearance.current)) {
            item {
                val count = (stations as? Load.Ready)?.value?.size ?: 0
                GalleryPageHead("Radio", Modifier.galleryArrive(0), eyebrow = GalleryRadioRules.stationCount(count).ifEmpty { null })
                Spacer(Modifier.height(12.dp))
            }
            message?.let { text ->
                item(key = "message") {
                    Text(text, Modifier.padding(horizontal = GalleryRules.GUTTER.dp, vertical = 8.dp).semantics { liveRegion = LiveRegionMode.Polite }, color = p.chartRedText, style = GalleryType.body())
                }
            }
            when (stations) {
                Load.Loading -> item { Muted("Loading…") }
                is Load.Failed -> item { Inline(stations.failure.message, reload) }
                is Load.Ready -> {
                    if (stations.value.isEmpty()) item { Muted("No radio stations. Add them in Navidrome and they appear here.") }
                    itemsIndexed(stations.value, key = { _, s -> s.id }) { i, station ->
                        val fav = favourite(station)
                        val onAir = onAirId == station.id
                        Column(Modifier.animateItem().galleryArrive(i + 1).padding(horizontal = GalleryRules.GUTTER.dp)) {
                            GalleryRow(
                                station.name, sub = stripText(station, now(station)), onClick = { onPlay(station) },
                                modifier = Modifier.semantics { if (onAir) stateDescription = "On air" },
                                lead = { GalleryPrint(GalleryRadioRules.LOGO_PRINT.dp, Modifier.size(GalleryRadioRules.LOGO_PRINT.dp), small = true) { StationLogo(station, station.name, null, 13f) } },
                                trail = {
                                    // The playing station shows the moving bars where the others show their heart; it is also said in words above.
                                    if (onAir) GalleryPlayingBars(playing, Modifier.padding(horizontal = 16.dp))
                                    else GalleryIconButton(
                                        if (fav) HeartOn else GalleryIcons.Heart,
                                        if (fav) "Remove ${station.name} from favourites" else "Add ${station.name} to favourites", { onFavourite(station) },
                                    )
                                },
                            )
                        }
                    }
                }
            }
        }
    }
}

// ----- 3. heard on radio ------------------------------------------------------------------------------------------

/** The Heard list: the catalogue line, the large title and its line, then a 48dp print, the song, "Artist · Station · time", and Get, a state word or nothing. */
@Composable
internal fun GalleryHeard(onBack: () -> Unit, plays: Load<List<RadioPlay>>, reload: () -> Unit, live: RadioLive, onDownload: (Long) -> Unit) {
    val p = LocalPalette.current
    Column(Modifier.fillMaxSize()) {
        GalleryPageBar("Heard on radio", onBack)
        LazyColumn(Modifier.fillMaxWidth(), contentPadding = PaddingValues(bottom = 24.dp + LocalBottomClearance.current)) {
            item {
                val eyebrow = (plays as? Load.Ready)?.value?.let { GalleryRadioRules.heardEyebrow(it, Instant.now()) }.orEmpty()
                GalleryPageHead("Heard on radio", Modifier.galleryArrive(0), eyebrow = eyebrow.ifEmpty { null })
                Text(
                    "Songs the stations played while you listened", style = GalleryType.body(), color = p.textMuted,
                    modifier = Modifier.galleryArrive(0).padding(start = GalleryRules.GUTTER.dp, end = GalleryRules.GUTTER.dp, top = 4.dp, bottom = 12.dp),
                )
            }
            live.message?.let { text ->
                item(key = "message") { Text(text, Modifier.padding(horizontal = GalleryRules.GUTTER.dp, vertical = 8.dp).semantics { liveRegion = LiveRegionMode.Polite }, color = p.text, style = GalleryType.body()) }
            }
            when (plays) {
                Load.Loading -> item { Muted("Loading…") }
                is Load.Failed -> item { Inline(plays.failure.message, reload) }
                is Load.Ready -> {
                    if (plays.value.isEmpty()) item { Muted("Nothing heard yet. A song is logged once you have listened to it for about 30 seconds.") }
                    itemsIndexed(plays.value, key = { _, play -> play.id }) { i, play ->
                        Column(Modifier.animateItem().galleryArrive(i + 1).padding(horizontal = GalleryRules.GUTTER.dp)) {
                            HeardRow(play, live.downloadFor(play.id, play.grabbed, play.inLibrary), live.failed[play.id]) { onDownload(play.id) }
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
    val trailing = CoverStackRadioRules.trailing(play.hasArtist, download)
    val time = play.heardAt?.let { DateFormat.getTimeInstance(DateFormat.SHORT).format(Date((it * 1000).toLong())) }
    val sub = CoverStackRadioRules.heardLine(play, time) + (failure?.let { " · $it" } ?: "")
    val album = play.album?.takeIf { it.isNotBlank() }
    val artist = play.artist?.takeIf { it.isNotBlank() }
    GalleryRow(
        play.title, sub = sub, italicTitle = GalleryRadioRules.italicTitle(play),
        lead = {
            GalleryPrint(GalleryRadioRules.ROW_PRINT.dp, Modifier.size(GalleryRadioRules.ROW_PRINT.dp), small = true) {
                if (artist != null && album != null) AlbumCover(artist, album, null, Modifier.fillMaxSize(), rect = true)
                else Box(Modifier.fillMaxSize().background(p.raised), contentAlignment = Alignment.Center) { Icon(GalleryIcons.MusicNote, null, tint = p.textMuted, modifier = Modifier.size(GalleryRules.ICON.dp)) }
            }
        },
        trail = {
            when (trailing) {
                CoverStackRadioRules.Trailing.Get -> GalleryButton("Get", onDownload, Modifier.semantics { contentDescription = "Download: ${play.title}" }, kind = GalleryButtonKind.Outlined, icon = GalleryIcons.Get, small = true)
                CoverStackRadioRules.Trailing.TryAgain -> GalleryButton("Try again", onDownload, Modifier.semantics { contentDescription = "Try again: ${play.title}" }, kind = GalleryButtonKind.Outlined, small = true)
                CoverStackRadioRules.Trailing.InLibrary -> GalleryState("In library", color = p.ok)
                CoverStackRadioRules.Trailing.Requested -> GalleryState("Requested")
                CoverStackRadioRules.Trailing.Working -> GalleryState("Requesting…")
                CoverStackRadioRules.Trailing.None -> Unit
            }
        },
    )
}

// ----- 2. live radio ----------------------------------------------------------------------------------------------

/** One round transport button: a 26dp glyph in `control`, 48dp to touch. */
@Composable
private fun RoundButton(icon: ImageVector, label: String, onClick: () -> Unit, state: String? = null) {
    val p = LocalPalette.current
    Box(
        Modifier.size(48.dp).clip(CircleShape).clickable(role = Role.Button, onClick = onClick).semantics { contentDescription = label; if (state != null) stateDescription = state },
        contentAlignment = Alignment.Center,
    ) { Icon(icon, null, tint = p.control, modifier = Modifier.size(GalleryRules.ICON_TRANSPORT.dp)) }
}

/**
 * The live page, full screen like Now Playing: the bar, the station plate in a 300dp print, "On air · FIP", the song in Fraunces italic and its artist, the heart, Play and
 * Heard buttons, and "Get this song". The sleep timer and the notes about the stream stay as on every theme.
 */
@Composable
internal fun GalleryRadioNow(
    state: PlayerUiState, controller: PlayerController, radio: RadioPlayback, sleep: SleepTimer, live: RadioLive, item: QueueItem,
    artwork: String?, status: String?, onDismiss: () -> Unit, onOpenHeard: () -> Unit,
) {
    val p = LocalPalette.current
    val (headline, under) = CoverStackRadioRules.headline(item.title, live.now, item.artist)
    Column(Modifier.fillMaxSize().navigationBarsPadding()) {
        Box(Modifier.fillMaxWidth().statusBarsPadding().height(GalleryRules.PAGE_BAR.dp).padding(horizontal = 4.dp)) {
            GalleryIconButton(GalleryIcons.Down, "Close now playing", onDismiss, Modifier.align(Alignment.CenterStart))
            Text("LIVE RADIO", style = GalleryType.catalogue, color = p.textMuted, modifier = Modifier.align(Alignment.Center).semantics { heading() }, maxLines = 1)
            GalleryMenuButton("More", listOf("Heard on radio" to onOpenHeard), Modifier.align(Alignment.CenterEnd))
        }
        Column(Modifier.fillMaxWidth().weight(1f).verticalScroll(rememberScrollState())) {
            BoxWithConstraints(Modifier.fillMaxWidth().gallerySpot(p).padding(top = 14.dp), contentAlignment = Alignment.TopCenter) {
                val side = minOf(maxWidth - 40.dp, GalleryRadioRules.LIVE_PRINT.dp)
                GalleryPrint(side, Modifier.width(side), player = true) { StationLogo(null, item.title, artwork, 72f) }
            }
            Column(Modifier.fillMaxWidth().padding(start = GalleryRules.GUTTER.dp, end = GalleryRules.GUTTER.dp, top = 24.dp)) {
                Text(GalleryRadioRules.airLine(state.isPlaying, item.title).uppercase(), style = GalleryType.catalogue, color = p.accent, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(
                    headline, style = GalleryType.work, color = p.text, maxLines = 2, overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.padding(top = 4.dp).semantics { heading() },
                )
                val by = GalleryRadioRules.byLine(live.now, under)
                if (by.isNotBlank()) Text(by, style = GalleryType.body(), color = p.text, modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
                live.now?.let { LiveNote(it, live.proxied) }
                // Trouble with the stream, in words, with the ways out (unchanged).
                if (status != null) Text(status, style = GalleryType.body(), color = p.text, modifier = Modifier.padding(top = 8.dp).semantics { liveRegion = LiveRegionMode.Polite })
                if (state.signInRequired) GalleryButton("Sign in again", { controller.dismissSignIn(); onDismiss() }, kind = GalleryButtonKind.Text)
                if (state.waitingForNetwork || live.unreachable) GalleryButton("Retry now", radio::retry, kind = GalleryButtonKind.Text)
            }
            Row(Modifier.fillMaxWidth().padding(top = 22.dp), horizontalArrangement = Arrangement.spacedBy(34.dp, Alignment.CenterHorizontally), verticalAlignment = Alignment.CenterVertically) {
                RoundButton(
                    if (live.favourite) HeartOn else GalleryIcons.Heart,
                    if (live.favourite) "Remove ${item.title} from favourites" else "Add ${item.title} to favourites", radio::toggleFavourite,
                    state = if (live.favourite) "Favourite" else "Not a favourite",
                )
                Box(
                    Modifier.size(68.dp).clip(CircleShape).background(p.control).clickable(role = Role.Button, onClick = controller::playPause)
                        .semantics { contentDescription = if (state.isPlaying) "Pause" else "Play" },
                    contentAlignment = Alignment.Center,
                ) { Icon(if (state.isPlaying) GalleryIcons.Pause else GalleryIcons.Play, null, tint = p.onControl, modifier = Modifier.size(28.dp)) }
                RoundButton(GalleryIcons.Queue, "Heard on radio", onOpenHeard)
            }
            if (live.proxied) {
                val download = live.download
                GalleryButton(
                    CoverStackRadioRules.getLabel(download), { live.now?.playId?.let(radio::download) },
                    Modifier.padding(start = GalleryRules.GUTTER.dp, top = 22.dp).semantics { contentDescription = "${download.label}: this song" },
                    icon = GalleryIcons.Get, enabled = download.enabled,
                )
            }
            live.message?.let {
                Text(it, Modifier.fillMaxWidth().padding(horizontal = GalleryRules.GUTTER.dp, vertical = 12.dp).semantics { liveRegion = LiveRegionMode.Polite }, color = p.textMuted, style = GalleryType.small())
            }
            Spacer(Modifier.height(8.dp))
            SleepTimerControl(sleep)
            Spacer(Modifier.height(16.dp))
        }
    }
}

/** The explanation under the song when there is no Download (no titles, unmatched title, relay off, unreachable): the same words as every theme, left-aligned. */
@Composable
private fun LiveNote(now: RadioNow, proxied: Boolean) {
    val words = when (now.state) {
        RadioNowState.Ok, RadioNowState.Idle -> null
        else -> radioNowText(now, proxied)
    } ?: return
    Text(words, Modifier.padding(top = 4.dp), style = GalleryType.body(), color = LocalPalette.current.textMuted, textAlign = TextAlign.Start)
}
