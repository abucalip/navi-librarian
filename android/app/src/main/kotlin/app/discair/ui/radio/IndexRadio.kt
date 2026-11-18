package app.discair.ui.radio

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.CustomAccessibilityAction
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.customActions
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
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
import app.discair.ui.common.IndexButton
import app.discair.ui.common.IndexButtonKind
import app.discair.ui.common.IndexGet
import app.discair.ui.common.IndexGetButton
import app.discair.ui.common.IndexIcons
import app.discair.ui.common.IndexLabel
import app.discair.ui.common.IndexMuted
import app.discair.ui.common.IndexPageBar
import app.discair.ui.common.IndexPageHead
import app.discair.ui.common.IndexPlayingBars
import app.discair.ui.common.IndexRow
import app.discair.ui.common.IndexRules
import app.discair.ui.common.IndexState
import app.discair.ui.common.IndexTabs
import app.discair.ui.common.IndexTag
import app.discair.ui.common.IndexType
import app.discair.ui.common.Load
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.indexArrive
import app.discair.ui.common.rememberLoad
import app.discair.ui.home.GalleryHomeRules
import app.discair.ui.home.Inline
import app.discair.ui.player.IndexPlayerBar
import app.discair.ui.theme.LocalPalette
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/*
 * Index's (Layout.Index) Radio pages. Spec: docs/INDEX_THEME.md step I5; mockup: docs/design/index/pages/radio, frames 1 to 3. RadioScreen, HeardScreen and
 * RadioNowPlayingSheet reach this behind isIndex(); the data, polling, favourites, playing and Get are theirs, unchanged. Radio's Stations and Heard are two tabs
 * of one page, as the mockup draws them; the Heard route (from Home and from the live page) shows the same Heard list on its own.
 */

/** The pure words of Index's Radio pages (unit-tested). */
object IndexRadioRules {
    const val TAB_STATIONS = 0
    const val TAB_HEARD = 1
    val tabs: List<String> = listOf("Stations", "Heard")

    /** The live page's plate height and the initials on it (index.css: 300dp, Inter Tight 120). */
    const val PLATE = 300
    const val PLATE_INITIALS_SP = 120

    /** "01": a row's number. */
    fun number(index: Int): String = "%02d".format(index + 1)

    /** When a station was last heard: the station's own last play, or the newest song heard on it (by name), whichever is later; null when neither is known. */
    fun lastHeardAt(station: RadioStation, plays: List<RadioPlay>): Double? =
        (plays.filter { it.stationName == station.name }.mapNotNull { it.heardAt } + listOfNotNull(station.lastPlayedAt)).maxOrNull()

    /**
     * A station row's meta line. The station on air says what is playing (or why nothing is said); another says "Last heard · Today" when that is known, and
     * otherwise the same honest live words every theme shows.
     */
    fun stationMeta(onAir: Boolean, lastHeard: String, live: String): String = when {
        onAir -> live
        lastHeard.isNotEmpty() -> "Last heard · $lastHeard"
        else -> live
    }

    /** When a song was heard, for a Heard row: "08:12" today, "Yesterday 22:40", else "12 Nov 22:40"; null when no time is known. [heardAt] is epoch seconds. */
    fun heardWhen(heardAt: Double?, now: Instant, zone: ZoneId = ZoneId.systemDefault()): String? {
        if (heardAt == null) return null
        val time = Instant.ofEpochMilli((heardAt * 1000).toLong()).atZone(zone)
        val clock = DateTimeFormatter.ofPattern("HH:mm").format(time)
        val ago = java.time.temporal.ChronoUnit.DAYS.between(time.toLocalDate(), now.atZone(zone).toLocalDate())
        return when {
            ago <= 0 -> clock
            ago == 1L -> "Yesterday $clock"
            else -> DateTimeFormatter.ofPattern("d MMM", java.util.Locale.ENGLISH).format(time) + " $clock"
        }
    }

    /** A Heard row's meta line: "Massive Attack · FIP · 08:12". A song with no artist leaves the artist out; its row says "No artist" at the end instead. */
    fun heardMeta(play: RadioPlay, time: String?): String =
        listOfNotNull(play.artist?.takeIf { it.isNotBlank() }, play.stationName.takeIf { it.isNotBlank() }, time).joinToString(" · ")

    /** The live page's line over the song: "FIP Groove · now", or "FIP Groove · paused" while it is not playing. */
    fun airLine(station: String, playing: Boolean): String =
        listOfNotNull(station.trim().takeIf { it.isNotEmpty() }, if (playing) "now" else "paused").joinToString(" · ")
}

/** A station's logo on its initials tile (`raised`, Inter Tight): the tile shows while the logo loads and when there is none. */
@Composable
private fun StationTile(name: String, logo: String?, side: androidx.compose.ui.unit.Dp, initialsSp: Int, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    Box(modifier.size(side).background(p.raised), contentAlignment = Alignment.Center) {
        Text(GalleryHomeRules.initials(name), color = p.text, style = IndexType.section().copy(fontSize = initialsSp.sp, lineHeight = initialsSp.sp), maxLines = 1)
        Cover(logo, Modifier.size(side), rect = true)
    }
}

// ----- 1 and 3. the Radio page: Stations and Heard -----------------------------------------------------------------

/**
 * The Radio page: the page bar, "Radio" with the station count, the STATIONS · HEARD tabs, then the chosen list. Stations: numbered rows with the logo tile
 * and when each was last heard; the station on air shows the playing bars, the others a play glyph. A tap plays (or opens the live page of the one on air); a
 * long press, or the screen reader's action, adds or removes the favourite. Heard: the songs heard on the radio, with Get, a state word or "No artist".
 */
@Composable
internal fun IndexRadioPage(
    onBack: () -> Unit, stations: Load<List<RadioStation>>, reload: () -> Unit, message: String?,
    favourite: (RadioStation) -> Boolean, now: (RadioStation) -> RadioNow?, onAirId: String?, playing: Boolean,
    onPlay: (RadioStation) -> Unit, onFavourite: (RadioStation) -> Unit,
) {
    val repo = LocalRepository.current
    val radio = LocalRadio.current
    val live by radio.state.collectAsState()
    val plays = rememberLoad("radio_plays") { repo.radioPlays() }
    var tab by rememberSaveable { mutableIntStateOf(IndexRadioRules.TAB_STATIONS) }
    val p = LocalPalette.current
    val heardPlays = (plays.state as? Load.Ready)?.value.orEmpty()
    val clock = remember { Instant.now() }
    Column(Modifier.fillMaxSize()) {
        IndexPageBar("Radio", onBack)
        LazyColumn(Modifier.fillMaxWidth(), contentPadding = PaddingValues(bottom = 24.dp + LocalBottomClearance.current)) {
            item(key = "head") {
                val count = (stations as? Load.Ready)?.value?.size?.takeIf { it > 0 }
                IndexPageHead("Radio", count = if (tab == IndexRadioRules.TAB_STATIONS) count?.toString() else null)
                IndexTabs(IndexRadioRules.tabs, tab, { tab = it }, Modifier.padding(top = 12.dp))
            }
            if (tab == IndexRadioRules.TAB_HEARD) {
                indexHeardItems(plays.state, plays.reload, live, clock) { radio.download(it) }
                return@LazyColumn
            }
            message?.let { text ->
                item(key = "message") {
                    Text(text, Modifier.padding(horizontal = IndexRules.GUTTER.dp, vertical = 8.dp).semantics { liveRegion = LiveRegionMode.Polite }, color = p.chartRedText, style = IndexType.body())
                }
            }
            when (stations) {
                Load.Loading -> item { IndexMuted("Loading…", Modifier.padding(IndexRules.GUTTER.dp)) }
                is Load.Failed -> item { Inline(stations.failure.message, reload) }
                is Load.Ready -> {
                    if (stations.value.isEmpty()) item { IndexMuted("No radio stations. Add them in Navidrome and they appear here.", Modifier.padding(IndexRules.GUTTER.dp)) }
                    itemsIndexed(stations.value, key = { _, s -> s.id }) { i, station ->
                        StationRow(
                            i, station, favourite(station), onAirId == station.id, playing,
                            IndexRadioRules.stationMeta(onAirId == station.id, GalleryHomeRules.lastHeard(IndexRadioRules.lastHeardAt(station, heardPlays), clock), stripText(station, now(station))),
                            { onPlay(station) }, { onFavourite(station) }, Modifier.animateItem().indexArrive(i + 1, tab),
                        )
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun StationRow(
    index: Int, station: RadioStation, favourite: Boolean, onAir: Boolean, playing: Boolean, meta: String, onPlay: () -> Unit, onFavourite: () -> Unit, modifier: Modifier,
) {
    val repo = LocalRepository.current
    var menu by remember { mutableStateOf(false) }
    val favouriteLabel = if (favourite) "Remove ${station.name} from favourites" else "Add ${station.name} to favourites"
    Box(
        modifier.padding(horizontal = IndexRules.GUTTER.dp)
            .combinedClickable(onClickLabel = "Play ${station.name}", role = Role.Button, onLongClickLabel = "Favourite", onLongClick = { menu = true }, onClick = onPlay)
            .semantics {
                if (onAir) stateDescription = "On air"
                customActions = listOf(CustomAccessibilityAction(favouriteLabel) { onFavourite(); true })
            },
    ) {
        IndexRow(
            station.name, meta = meta, number = IndexRadioRules.number(index),
            lead = { StationTile(station.name, radioLogoRequest(repo.absolute(station.logoUrl), 128), 48.dp, 16) },
            trail = {
                // The station on air shows the moving bars; the others a play glyph (the row itself plays). A favourite is said in words, never a mark alone.
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (favourite) IndexState("Favourite")
                    if (onAir) IndexPlayingBars(playing, Modifier.padding(end = 4.dp))
                    else Icon(IndexIcons.Play, null, tint = LocalPalette.current.text, modifier = Modifier.size(IndexRules.ICON_INLINE.dp))
                }
            },
        )
        DropdownMenu(menu, onDismissRequest = { menu = false }) {
            DropdownMenuItem(text = { Text(if (favourite) "Remove from favourites" else "Add to favourites") }, onClick = { menu = false; onFavourite() })
        }
    }
}

/** The Heard list's items: the message, the loading and empty words, then one numbered row per song heard. Shared by the Radio page's tab and the Heard route. */
private fun LazyListScope.indexHeardItems(plays: Load<List<RadioPlay>>, reload: () -> Unit, live: RadioLive, now: Instant, onDownload: (Long) -> Unit) {
    live.message?.let { text ->
        item(key = "heard-message") { IndexMuted(text, Modifier.padding(horizontal = IndexRules.GUTTER.dp, vertical = 8.dp).semantics { liveRegion = LiveRegionMode.Polite }) }
    }
    when (plays) {
        Load.Loading -> item { IndexMuted("Loading…", Modifier.padding(IndexRules.GUTTER.dp)) }
        is Load.Failed -> item { Inline(plays.failure.message, reload) }
        is Load.Ready -> {
            if (plays.value.isEmpty()) item { IndexMuted("Nothing heard yet. A song is logged once you have listened to it for about 30 seconds.", Modifier.padding(IndexRules.GUTTER.dp)) }
            itemsIndexed(plays.value, key = { _, play -> "heard-${play.id}" }) { i, play ->
                HeardRow(i, play, live.downloadFor(play.id, play.grabbed, play.inLibrary), live.failed[play.id], now, { onDownload(play.id) }, Modifier.animateItem().indexArrive(i + 1, "heard"))
            }
        }
    }
}

@Composable
private fun HeardRow(index: Int, play: RadioPlay, download: RadioDownload, failure: String?, now: Instant, onDownload: () -> Unit, modifier: Modifier) {
    val p = LocalPalette.current
    val trailing = CoverStackRadioRules.trailing(play.hasArtist, download)
    val meta = IndexRadioRules.heardMeta(play, IndexRadioRules.heardWhen(play.heardAt, now)) + (failure?.let { " · $it" } ?: "")
    val album = play.album?.takeIf { it.isNotBlank() }
    val artist = play.artist?.takeIf { it.isNotBlank() }
    IndexRow(
        play.title, modifier.padding(horizontal = IndexRules.GUTTER.dp), meta = meta, number = IndexRadioRules.number(index),
        lead = {
            if (artist != null && album != null) AlbumCover(artist, album, null, Modifier.size(48.dp), rect = true)
            else Box(Modifier.size(48.dp).background(p.raised), contentAlignment = Alignment.Center) { Icon(IndexIcons.MusicNote, null, tint = p.text, modifier = Modifier.size(IndexRules.ICON.dp)) }
        },
        trail = {
            when (trailing) {
                CoverStackRadioRules.Trailing.Get -> IndexGetButton(IndexGet.Idle, onDownload, Modifier.semantics { contentDescription = "Get ${play.title}" })
                CoverStackRadioRules.Trailing.TryAgain -> IndexButton("Try again", onDownload, Modifier.semantics { contentDescription = "Try again: ${play.title}" }, kind = IndexButtonKind.Ghost, small = true)
                CoverStackRadioRules.Trailing.InLibrary -> IndexState("In library", color = p.ok)
                CoverStackRadioRules.Trailing.Requested -> IndexState("Requested")
                CoverStackRadioRules.Trailing.Working -> IndexGetButton(IndexGet.Pending, {})
                CoverStackRadioRules.Trailing.None -> IndexState("No artist")
            }
        },
    )
}

/** The Heard route on Index: the page bar and "Heard" over the same list as the Radio page's Heard tab. */
@Composable
internal fun IndexHeard(onBack: () -> Unit, plays: Load<List<RadioPlay>>, reload: () -> Unit, live: RadioLive, onDownload: (Long) -> Unit) {
    val clock = remember { Instant.now() }
    Column(Modifier.fillMaxSize()) {
        IndexPageBar("Heard on radio", onBack)
        LazyColumn(Modifier.fillMaxWidth(), contentPadding = PaddingValues(bottom = 24.dp + LocalBottomClearance.current)) {
            item(key = "head") { IndexPageHead("Heard") }
            indexHeardItems(plays, reload, live, clock, onDownload)
        }
    }
}

// ----- 2. live radio ----------------------------------------------------------------------------------------------

/** One transport cell: a 22dp glyph in `text`, 48dp to touch. */
@Composable
private fun TransportCell(icon: ImageVector, label: String, onClick: () -> Unit, state: String? = null, tint: androidx.compose.ui.graphics.Color = LocalPalette.current.text) {
    Box(
        Modifier.size(IndexRules.TOUCH_MIN.dp).clickable(role = Role.Button, onClick = onClick).semantics { contentDescription = label; if (state != null) stateDescription = state },
        contentAlignment = Alignment.Center,
    ) { Icon(icon, null, tint = tint, modifier = Modifier.size(IndexRules.ICON.dp)) }
}

/**
 * The live page on the `surface` page, risen like Now Playing (IndexPlayerFrame): the bar, the station plate (300dp, `raised`, the initials under the logo or
 * the song's cover) with the ON AIR tag, "FIP Groove · now" in `accent`, the song, its artist line, Get this song, then the favourite, Play and Heard. The sleep
 * timer, the notes about the stream and the status words stay as on every theme.
 */
@Composable
internal fun IndexRadioNow(
    state: PlayerUiState, controller: PlayerController, radio: RadioPlayback, sleep: SleepTimer, live: RadioLive, item: QueueItem,
    artwork: String?, status: String?, onDismiss: () -> Unit, onOpenHeard: () -> Unit,
) {
    val p = LocalPalette.current
    val (headline, under) = CoverStackRadioRules.headline(item.title, live.now, item.artist)
    Column(Modifier.fillMaxSize().background(p.surface).navigationBarsPadding()) {
        IndexPlayerBar("Live radio", "Close now playing", onDismiss, listOf("Heard on radio" to onOpenHeard))
        Column(Modifier.fillMaxWidth().weight(1f).verticalScroll(rememberScrollState())) {
            Box(Modifier.padding(start = IndexRules.GUTTER.dp, end = IndexRules.GUTTER.dp, top = 6.dp).fillMaxWidth().height(IndexRadioRules.PLATE.dp).background(p.raised), contentAlignment = Alignment.Center) {
                Text(GalleryHomeRules.initials(item.title), color = p.text, style = IndexType.display().copy(fontSize = IndexRadioRules.PLATE_INITIALS_SP.sp, lineHeight = IndexRadioRules.PLATE_INITIALS_SP.sp), maxLines = 1)
                if (artwork != null) Cover(artwork, Modifier.size(IndexRadioRules.PLATE.dp), rect = true)
                IndexTag(CoverStackRadioRules.airTag(state.isPlaying), Modifier.align(Alignment.TopStart).padding(12.dp), accent = state.isPlaying)
            }
            Column(Modifier.fillMaxWidth().padding(start = IndexRules.GUTTER.dp, end = IndexRules.GUTTER.dp, top = 16.dp)) {
                IndexLabel(IndexRadioRules.airLine(item.title, state.isPlaying), color = p.accent)
                Text(
                    headline, style = IndexType.display().copy(fontSize = 36.sp, lineHeight = 33.sp), color = p.text, maxLines = 2, overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.padding(top = 6.dp, bottom = 2.dp).semantics { heading() },
                )
                val by = GalleryRadioRules.byLine(live.now, under)
                if (by.isNotBlank()) Text(by, style = IndexType.body(), color = p.textMuted, modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
                live.now?.let { LiveNote(it, live.proxied) }
                // Trouble with the stream, in words, with the ways out (unchanged).
                if (status != null) Text(status, style = IndexType.body(), color = p.text, modifier = Modifier.padding(top = 8.dp).semantics { liveRegion = LiveRegionMode.Polite })
                if (state.signInRequired) IndexButton("Sign in again", { controller.dismissSignIn(); onDismiss() }, kind = IndexButtonKind.Ghost, small = true)
                if (state.waitingForNetwork || live.unreachable) IndexButton("Retry now", radio::retry, kind = IndexButtonKind.Ghost, small = true)
            }
            if (live.proxied) {
                val download = live.download
                IndexButton(
                    CoverStackRadioRules.getLabel(download), { live.now?.playId?.let(radio::download) },
                    Modifier.padding(start = IndexRules.GUTTER.dp, top = 16.dp).semantics { contentDescription = "${download.label}: this song" },
                    icon = IndexIcons.Get, enabled = download.enabled,
                )
            }
            Row(Modifier.fillMaxWidth().padding(start = 60.dp, end = 60.dp, top = 22.dp), verticalAlignment = Alignment.CenterVertically) {
                // The favourite: the heart in `accent` with the word under it while the station is one (never the colour alone).
                Column(Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                    TransportCell(
                        IndexIcons.Heart, if (live.favourite) "Remove ${item.title} from favourites" else "Add ${item.title} to favourites", radio::toggleFavourite,
                        state = if (live.favourite) "Favourite" else "Not a favourite", tint = if (live.favourite) p.accent else p.text,
                    )
                    if (live.favourite) IndexLabel("Favourite", color = p.accent)
                }
                Box(Modifier.weight(1f), contentAlignment = Alignment.Center) {
                    Box(
                        Modifier.size(64.dp).clip(RoundedCornerShape(IndexRules.BUTTON_RADIUS.dp)).background(p.control)
                            .clickable(role = Role.Button, onClick = controller::playPause).semantics { contentDescription = if (state.isPlaying) "Pause" else "Play" },
                        contentAlignment = Alignment.Center,
                    ) { Icon(if (state.isPlaying) IndexIcons.Pause else IndexIcons.Play, null, tint = p.onControl, modifier = Modifier.size(IndexRules.ICON.dp)) }
                }
                Box(Modifier.weight(1f), contentAlignment = Alignment.Center) { TransportCell(IndexIcons.Queue, "Heard on radio", onOpenHeard) }
            }
            live.message?.let {
                IndexMuted(it, Modifier.fillMaxWidth().padding(horizontal = IndexRules.GUTTER.dp, vertical = 12.dp).semantics { liveRegion = LiveRegionMode.Polite })
            }
            Spacer(Modifier.height(8.dp))
            SleepTimerControl(sleep)
            Spacer(Modifier.height(16.dp))
        }
    }
}

/** The explanation under the song when there is no Get (no titles, unmatched title, relay off, unreachable): the same words as every theme. */
@Composable
private fun LiveNote(now: RadioNow, proxied: Boolean) {
    val words = when (now.state) {
        RadioNowState.Ok, RadioNowState.Idle -> null
        else -> radioNowText(now, proxied)
    } ?: return
    IndexMuted(words, Modifier.padding(top = 4.dp))
}
