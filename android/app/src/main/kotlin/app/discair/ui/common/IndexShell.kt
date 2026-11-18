package app.discair.ui.common

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.EnterTransition
import androidx.compose.animation.ExitTransition
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.SnackbarData
import androidx.compose.material3.SnackbarDuration
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.boundsInWindow
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalAccessibilityManager
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.player.PlayerController
import app.discair.player.PlayerUiState
import app.discair.ui.player.playerSubtitle
import app.discair.ui.theme.IndexMotion
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.Palette
import app.discair.ui.theme.rememberReducedMotion
import java.time.LocalDate
import java.time.format.TextStyle as DateTextStyle
import java.util.Locale
import kotlinx.coroutines.delay

/**
 * Index's shell (docs/INDEX_THEME.md 7, mockups index/pages/components and sheets): the dock is the ink strip (56dp) over a white four-cell bar (60dp) with
 * the signal block on its top edge; the Home bar (54dp) carries the wordmark and the mono date; the page bar (52dp) a back button, a mono catalogue line and an
 * action. Nothing has a shadow.
 */
object IndexShellRules {
    /** The Home bar's date in mono capitals: "TUE 17.11" (weekday, day.month). */
    fun dateLabel(date: LocalDate): String =
        "${date.dayOfWeek.getDisplayName(DateTextStyle.SHORT, Locale.ENGLISH)} ${"%02d".format(date.dayOfMonth)}.${"%02d".format(date.monthValue)}".uppercase()

    /** "1:37" for a position in milliseconds (minutes, then two-digit seconds; hours roll into minutes as the mockup's times do). */
    fun clock(ms: Long): String {
        val total = (ms.coerceAtLeast(0L) / 1000L)
        return "${total / 60}:${"%02d".format(total % 60)}"
    }

    /** The strip's mono meta line: the artist (or the status), then "1:37 / 3:51" when the song has a length and nothing else is being said. */
    fun stripMeta(subtitle: String, positionMs: Long, durationMs: Long, showTime: Boolean): String =
        if (showTime && durationMs > 0L) "$subtitle · ${clock(positionMs)} / ${clock(durationMs)}" else subtitle

    /** The strip's progress line, 0 to 1; 0 when the length is unknown (radio). */
    fun progress(positionMs: Long, durationMs: Long): Float = if (durationMs > 0L) (positionMs.toFloat() / durationMs).coerceIn(0f, 1f) else 0f

    /** Which bar cell a route is: 0 Home, 1 Discover, 2 Library, 3 Search, -1 for any other page. */
    fun selectedCell(home: Boolean, discover: Boolean, library: Boolean, search: Boolean): Int = when { home -> 0; discover -> 1; library -> 2; search -> 3; else -> -1 }
}

// ---------------------------------------------------------------- navigation transitions (motion #1 and #2)

/**
 * The NavHost's transitions for Index (docs/INDEX_THEME.md 8.2 #1 and #2). [from] and [to] are bar positions (Home 0, Discover 1, Library 2) or -1 for any
 * other page. Between two bar pages the page slides the full width in the direction of the bar order, with no fade, whether the move is a push or a pop
 * (Home from Library pops, and must still slide the right way). Every other move is a push: the new page enters from +30% of the width with a 200ms
 * fade and the page under it leaves to -12% and dims to 85%; Back mirrors it.
 */
object IndexNav {
    private fun tabDir(from: Int, to: Int): Int? = if (from >= 0 && to >= 0 && from != to) IndexMotion.tabDirection(from, to) else null

    fun enter(from: Int, to: Int, reduced: Boolean): EnterTransition {
        if (reduced) return EnterTransition.None
        val dir = tabDir(from, to)
        return if (dir != null) slideInHorizontally(IndexMotion.firm(IndexMotion.TAB_SLIDE_MS, reduced)) { w -> dir * w }
        else slideInHorizontally(IndexMotion.firm(IndexMotion.PUSH_MS, reduced)) { w -> (w * IndexMotion.PUSH_ENTER_FRACTION).toInt() } + fadeIn(IndexMotion.fade(IndexMotion.PUSH_FADE_MS, reduced))
    }

    fun exit(from: Int, to: Int, reduced: Boolean): ExitTransition {
        if (reduced) return ExitTransition.None
        val dir = tabDir(from, to)
        return if (dir != null) slideOutHorizontally(IndexMotion.firm(IndexMotion.TAB_SLIDE_MS, reduced)) { w -> -dir * w }
        else slideOutHorizontally(IndexMotion.firm(IndexMotion.PUSH_MS, reduced)) { w -> -(w * IndexMotion.PUSH_EXIT_FRACTION).toInt() } +
            fadeOut(IndexMotion.fade(IndexMotion.PUSH_FADE_MS, reduced), targetAlpha = IndexMotion.PUSH_DIM)
    }

    fun popEnter(from: Int, to: Int, reduced: Boolean): EnterTransition {
        if (reduced) return EnterTransition.None
        val dir = tabDir(from, to)
        return if (dir != null) slideInHorizontally(IndexMotion.firm(IndexMotion.TAB_SLIDE_MS, reduced)) { w -> dir * w }
        else slideInHorizontally(IndexMotion.firm(IndexMotion.PUSH_MS, reduced)) { w -> -(w * IndexMotion.PUSH_EXIT_FRACTION).toInt() } +
            fadeIn(IndexMotion.fade(IndexMotion.PUSH_FADE_MS, reduced), initialAlpha = IndexMotion.PUSH_DIM)
    }

    fun popExit(from: Int, to: Int, reduced: Boolean): ExitTransition {
        if (reduced) return ExitTransition.None
        val dir = tabDir(from, to)
        return if (dir != null) slideOutHorizontally(IndexMotion.firm(IndexMotion.TAB_SLIDE_MS, reduced)) { w -> -dir * w }
        else slideOutHorizontally(IndexMotion.firm(IndexMotion.PUSH_MS, reduced)) { w -> (w * IndexMotion.PUSH_ENTER_FRACTION).toInt() } + fadeOut(IndexMotion.fade(IndexMotion.PUSH_FADE_MS, reduced))
    }
}

// ---------------------------------------------------------------- the dock

/**
 * The bar: 60dp on `rail`, a 1dp `edge` rule on top, four cells (a 22dp icon over a mono label) and a 3dp `accent` signal block, 14% of the bar's width, on the
 * top edge over the selected cell. The block slides between cells over 380ms (motion #3); the selected label and icon change colour at once. Drawn from
 * [palette], the owner's theme, never the artwork tint.
 */
@Composable
fun IndexNavBar(
    palette: Palette, homeSelected: Boolean, discoverSelected: Boolean, librarySelected: Boolean,
    onHome: () -> Unit, onDiscover: () -> Unit, onLibrary: () -> Unit, onSearch: () -> Unit, modifier: Modifier = Modifier,
    searchSelected: Boolean = false,
) {
    val selected = IndexShellRules.selectedCell(homeSelected, discoverSelected, librarySelected, searchSelected)
    val reduced = rememberReducedMotion()
    val density = LocalDensity.current
    Column(modifier.fillMaxWidth().background(palette.rail).navigationBarsPadding()) {
        BoxWithConstraints(Modifier.fillMaxWidth().height(IndexRules.DOCK_BAR.dp)) {
            val barPx = with(density) { maxWidth.toPx() }
            val blockX by animateDpAsState(with(density) { IndexMotion.signalX(selected, barPx).toDp() }, IndexMotion.firm(IndexMotion.SIGNAL_MS, reduced), label = "indexSignalBlock")
            Row(Modifier.fillMaxSize()) {
                IndexCell(palette, "Home", IndexIcons.Home, homeSelected, onHome)
                IndexCell(palette, "Discover", IndexIcons.Disc, discoverSelected, onDiscover)
                IndexCell(palette, "Library", IndexIcons.Lib, librarySelected, onLibrary)
                IndexCell(palette, "Search", IndexIcons.Search, searchSelected, onSearch)
            }
            Box(Modifier.fillMaxWidth().height(1.dp).background(palette.edge))
            if (selected >= 0) Box(Modifier.offset { IntOffset(blockX.roundToPx(), 0) }.size(width = maxWidth * IndexMotion.SIGNAL_WIDTH_FRACTION, height = IndexMotion.SIGNAL_HEIGHT_DP.dp).background(palette.accent))
        }
    }
}

@Composable
private fun RowScope.IndexCell(palette: Palette, label: String, icon: ImageVector, selected: Boolean, onClick: () -> Unit) {
    val tint = if (selected) palette.text else palette.textMuted
    Column(
        Modifier.weight(1f).fillMaxSize().clickable(role = Role.Button, onClick = onClick).semantics { contentDescription = label; this.selected = selected },
        horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(4.dp, Alignment.CenterVertically),
    ) {
        Icon(icon, null, tint = tint, modifier = Modifier.size(IndexRules.ICON.dp))
        Text(label.uppercase(), style = IndexType.navLabel(), color = tint, maxLines = 1, modifier = Modifier.clearAndSetSemantics { })
    }
}

/**
 * The ink strip, the mini player: 56dp, a solid `strip` band with a 38dp square cover, the title (Inter 600 14) over a mono meta line in `stripMuted`
 * ("KHRUANGBIN · 1:37 / 3:51"), and a pause or play button. A 3dp `stripProgress` line along its top edge shows the position (linear, no tween: motion #12).
 */
@Composable
fun IndexMiniPlayer(state: PlayerUiState, controller: PlayerController, onOpen: () -> Unit, modifier: Modifier = Modifier) {
    val item = state.current ?: return
    val showTime = state.status == null && !state.buffering && !item.isRadio
    // The strip's cover is where Now Playing's cover flies from (motion #8): measured only while the strip is at rest.
    val measure = Modifier.onGloballyPositioned { c -> if (IndexFlight.dock.value == 0f && !IndexFlight.dock.isRunning) IndexFlight.mini = c.boundsInWindow() }
    IndexStrip(
        title = item.title, meta = IndexShellRules.stripMeta(playerSubtitle(state), state.positionMs, state.durationMs, showTime),
        fraction = IndexShellRules.progress(state.positionMs, state.durationMs), playing = state.isPlaying, onOpen = onOpen, onToggle = controller::playPause,
        modifier = modifier.indexStripMotion(),
        cover = { Cover(item.coverUrl.ifBlank { null }, measure.size(IndexRules.STRIP_COVER.dp), rect = true) },
    )
}

/**
 * Index's one player flight (docs/INDEX_THEME.md 8.2 #8): the strip cover's place, the player's cover and the flight's progress. Its own instance of the shape
 * Gallery uses, so the two themes never share state.
 */
val IndexFlight = GalleryPlayerFlight()

/**
 * Motion #8's strip: while Now Playing is up the strip slides down under the bar (which is drawn after it and stays), and slides back up over the player's
 * fall (320ms, Firm). Nothing fades.
 */
@Composable
fun Modifier.indexStripMotion(): Modifier {
    val flight = IndexFlight
    val reduced = rememberReducedMotion()
    LaunchedEffect(flight.playerUp) {
        if (flight.playerUp) flight.dock.snapTo(1f) else flight.dock.animateTo(0f, IndexMotion.firm(IndexMotion.PLAYER_FALL_MS, reduced))
    }
    return graphicsLayer { translationY = flight.dock.value * size.height }
}

/** The strip's drawing, without the player: what the mini player and the components board share. */
@Composable
fun IndexStrip(
    title: String, meta: String, fraction: Float, playing: Boolean, onOpen: () -> Unit, onToggle: () -> Unit, modifier: Modifier = Modifier, cover: @Composable () -> Unit,
) {
    val tones = indexTones()
    Row(
        modifier.fillMaxWidth().height(IndexRules.DOCK_STRIP.dp).background(tones.strip).drawBehind {
            drawRect(tones.stripProgress, Offset.Zero, Size(size.width * fraction.coerceIn(0f, 1f), IndexRules.STRIP_PROGRESS.dp.toPx()))
        }.padding(start = 12.dp, end = 2.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        cover()
        Column(
            Modifier.weight(1f).heightIn(min = IndexRules.TOUCH_MIN.dp).clickable(onClickLabel = "Open now playing", role = Role.Button, onClick = onOpen),
            verticalArrangement = Arrangement.Center,
        ) {
            Text(
                title, color = tones.onStrip, maxLines = 1, overflow = TextOverflow.Ellipsis, style = IndexType.rowTitle().copy(fontSize = 14.sp, lineHeight = 17.5.sp),
                modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
            )
            Text(meta.uppercase(), color = tones.stripMuted, maxLines = 1, overflow = TextOverflow.Ellipsis, style = IndexType.label())
        }
        IndexIconButton(if (playing) IndexIcons.Pause else IndexIcons.Play, if (playing) "Pause" else "Play", onToggle, tint = tones.onStrip)
    }
}

// ---------------------------------------------------------------- top bars

/**
 * The Home top bar (54dp): the wordmark at 16dp, the mono date beside it, then the downloads button (with its square `accent` badge) and settings; Discover
 * sits here only where the bar does not carry it (the rail). [date] is the label to show (IndexShellRules.dateLabel).
 */
@Composable
fun IndexHomeBar(
    active: Int, onDownloads: () -> Unit, onSettings: () -> Unit, modifier: Modifier = Modifier, showDiscover: Boolean = false, onDiscover: () -> Unit = {},
    date: String = IndexShellRules.dateLabel(LocalDate.now()),
) {
    val p = LocalPalette.current
    Row(
        modifier.background(p.ink).fillMaxWidth().statusBarsPadding().height(IndexRules.HOME_BAR.dp).padding(start = IndexRules.GUTTER.dp, end = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text("discair", style = IndexType.wordmark(), color = p.text, maxLines = 1, modifier = Modifier.semantics { contentDescription = "Discair" })
        IndexLabel(date, Modifier.padding(start = 10.dp))
        Box(Modifier.weight(1f))
        if (showDiscover) IndexIconButton(IndexIcons.Disc, "Discover", onDiscover)
        Box {
            IndexIconButton(IndexIcons.Download, if (active == 0) "Downloads" else "Downloads, $active active", onDownloads)
            if (active > 0) IndexBadge(active, Modifier.align(Alignment.TopEnd).padding(top = 8.dp, end = 6.dp))
        }
        IndexIconButton(IndexIcons.Gear, "Settings", onSettings)
    }
}

/**
 * The page top bar (52dp): a back button at the left, a mono catalogue line in the middle ("ALBUM 0418 / 1284", "ARTIST 0031 / 312", "NOT IN YOUR LIBRARY")
 * and [action] at the right. The line is centred between the two buttons, which are the same width.
 */
@Composable
fun IndexPageBar(catalogue: String, onBack: () -> Unit, modifier: Modifier = Modifier, action: (@Composable () -> Unit)? = null) {
    val p = LocalPalette.current
    Box(modifier.background(p.ink).fillMaxWidth().statusBarsPadding().height(IndexRules.PAGE_BAR.dp).padding(horizontal = 4.dp)) {
        IndexIconButton(IndexIcons.Back, "Back", onBack, Modifier.align(Alignment.CenterStart))
        IndexLabel(catalogue, Modifier.align(Alignment.Center))
        if (action != null) Box(Modifier.align(Alignment.CenterEnd)) { action() }
    }
}

// ---------------------------------------------------------------- snackbar and sheet

/**
 * Index's snackbar host (docs/INDEX_THEME.md 8.2 #10): the toast slides up from 56dp below over 220ms with no fade, holds 4s (longer when the phone's
 * accessibility settings ask for more time) and slides back down over 180ms.
 */
@Composable
fun IndexSnackbarHost(hostState: SnackbarHostState, modifier: Modifier = Modifier) {
    val reduced = rememberReducedMotion()
    val current = hostState.currentSnackbarData
    val a11y = LocalAccessibilityManager.current
    LaunchedEffect(current) {
        if (current == null) return@LaunchedEffect
        val base = when (current.visuals.duration) {
            SnackbarDuration.Short -> IndexMotion.SNACK_HOLD_MS
            SnackbarDuration.Long -> 10_000L
            SnackbarDuration.Indefinite -> Long.MAX_VALUE
        }
        val hold = a11y?.calculateRecommendedTimeoutMillis(base, containsIcons = false, containsText = true, containsControls = current.visuals.actionLabel != null) ?: base
        delay(hold)
        current.dismiss()
    }
    // The last toast stays drawn while it slides out.
    val last = remember { arrayOfNulls<SnackbarData>(1) }
    if (current != null) last[0] = current
    val off = with(LocalDensity.current) { IndexMotion.SNACK_FROM_DP.dp.roundToPx() }
    Box(modifier.fillMaxWidth()) {
        AnimatedVisibility(
            visible = current != null,
            enter = if (reduced) EnterTransition.None else slideInVertically(IndexMotion.firm(IndexMotion.SNACK_MS, reduced)) { off },
            exit = if (reduced) ExitTransition.None else slideOutVertically(IndexMotion.firm(IndexMotion.SNACK_OUT_MS, reduced)) { off },
        ) { last[0]?.let { IndexSnackbar(it) } }
    }
}

/** Index's toast: 52dp, radius 3, a `strip` fill with `onStrip` text (Inter 500 14) and a mono UNDO in `stripProgress`. 12dp from the sides and above whatever is under it. */
@Composable
fun IndexSnackbar(data: SnackbarData) {
    val tones = indexTones()
    Box(Modifier.padding(horizontal = 12.dp, vertical = 12.dp)) {
        Row(
            Modifier.fillMaxWidth().heightIn(min = IndexRules.SNACK_HEIGHT.dp).clip(RoundedCornerShape(IndexRules.SNACK_RADIUS.dp)).background(tones.strip).padding(start = 14.dp, end = 2.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                data.visuals.message, Modifier.weight(1f).padding(vertical = 10.dp), color = tones.onStrip,
                style = IndexType.rowTitle().copy(fontWeight = FontWeight.Medium, fontSize = 14.sp, lineHeight = 20.sp),
            )
            data.visuals.actionLabel?.let { label ->
                Box(Modifier.heightIn(min = IndexRules.TOUCH_MIN.dp).clickable(role = Role.Button, onClick = { data.performAction() }).padding(horizontal = 12.dp), contentAlignment = Alignment.Center) {
                    Text(label.uppercase(), color = tones.stripProgress, style = IndexType.label())
                }
            }
        }
    }
}

/** The sheet's handle: 32 by 3dp in `text`, 8dp from the top and 14dp above the content (index.css `.handle`). */
@Composable
fun IndexSheetHandle() {
    Box(Modifier.padding(top = 8.dp, bottom = 14.dp).size(width = 32.dp, height = 3.dp).background(LocalPalette.current.text))
}
