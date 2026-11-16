package app.discair.ui.common

import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.tween
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.SnackbarData
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.player.PlayerController
import app.discair.player.PlayerUiState
import app.discair.ui.player.playerSubtitle
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.LocalThemePalette
import app.discair.ui.theme.Palette
import app.discair.ui.theme.rememberReducedMotion

/**
 * Gallery's shell (docs/GALLERY_THEME.md 7.3, mockups gallery/pages/components and home): the dock is the `rail` colour with a 1dp `edge` rule on top;
 * the mini player (58dp) sits above the bar (62dp), divided by a 1dp rule; the page bars are plain, with no fill of their own and no rule under them.
 */

/** The curve of the bar marker, the sheet and the snackbar: cubic-bezier(0.2, 0.8, 0.2, 1). */
private val GalleryEase = CubicBezierEasing(0.2f, 0.8f, 0.2f, 1f)

/** The bar: four equal cells with a 22dp icon over a Manrope 600 11 label; the selected cell is `control`, with a 22 by 2dp marker on its top edge that slides between cells. */
@Composable
fun GalleryNavBar(
    palette: Palette, homeSelected: Boolean, discoverSelected: Boolean, librarySelected: Boolean,
    onHome: () -> Unit, onDiscover: () -> Unit, onLibrary: () -> Unit, onSearch: () -> Unit, modifier: Modifier = Modifier,
    searchSelected: Boolean = false,
) {
    val selected = when { homeSelected -> 0; discoverSelected -> 1; librarySelected -> 2; searchSelected -> 3; else -> -1 }
    val reduced = rememberReducedMotion()
    Column(modifier.fillMaxWidth().background(palette.rail).navigationBarsPadding()) {
        Box(Modifier.fillMaxWidth().height(1.dp).background(palette.edge))
        BoxWithConstraints(Modifier.fillMaxWidth().height((GalleryRules.DOCK_BAR - 1f).dp)) {
            val cell = maxWidth / 4
            val markerX by animateDpAsState(
                cell * (selected.coerceAtLeast(0)) + (cell - 22.dp) / 2,
                tween(if (reduced) 0 else 450, easing = GalleryEase), label = "galleryMarker",
            )
            Row(Modifier.fillMaxSize()) {
                GalleryCell(palette, "Home", GalleryIcons.Home, homeSelected, onHome)
                GalleryCell(palette, "Discover", GalleryIcons.Disc, discoverSelected, onDiscover)
                GalleryCell(palette, "Library", GalleryIcons.Lib, librarySelected, onLibrary)
                GalleryCell(palette, "Search", GalleryIcons.Search, searchSelected, onSearch)
            }
            if (selected >= 0) Box(Modifier.offset(x = markerX).size(width = 22.dp, height = 2.dp).background(palette.control))
        }
    }
}

@Composable
private fun RowScope.GalleryCell(palette: Palette, label: String, icon: ImageVector, selected: Boolean, onClick: () -> Unit) {
    val tint = if (selected) palette.control else palette.textMuted
    Column(
        Modifier.weight(1f).fillMaxSize().clickable(role = Role.Button, onClick = onClick).semantics { contentDescription = label; this.selected = selected },
        horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(3.dp, Alignment.CenterVertically),
    ) {
        // Icons are always `control` (spec 6); the inactive cell is muted like its label so only the chosen destination reads as the control colour.
        Icon(icon, null, tint = tint, modifier = Modifier.size(GalleryRules.ICON.dp))
        Text(label, style = GalleryType.barLabel(), color = tint, maxLines = 1, modifier = Modifier.clearAndSetSemantics { })
    }
}

/**
 * The mini player: 58dp, 16dp inset, a 38dp cover with no mat, the row work title (Fraunces italic 16) over the artist (Manrope 12), and a pause or play icon button.
 * A 1.5dp `accent` line on its top edge shows the progress. The `rail` fill and the 1dp rules above and below make it part of the dock.
 */
@Composable
fun GalleryMiniPlayer(state: PlayerUiState, controller: PlayerController, onOpen: () -> Unit, modifier: Modifier = Modifier) {
    val item = state.current ?: return
    val p = LocalThemePalette.current ?: LocalPalette.current
    val fraction = if (state.durationMs > 0) (state.positionMs.toFloat() / state.durationMs).coerceIn(0f, 1f) else 0f
    Column(modifier.fillMaxWidth().background(p.rail)) {
        Box(Modifier.fillMaxWidth().height(1.dp).background(p.edge))
        Row(
            Modifier.fillMaxWidth().height(GalleryRules.DOCK_MINI.dp).drawBehind {
                drawRect(p.accent, Offset(0f, -1.dp.toPx()), Size(size.width * fraction, 1.5.dp.toPx()))
            }.padding(start = 16.dp, end = 8.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            GalleryPrint(38.dp, bare = true) { Cover(item.coverUrl.ifBlank { null }, Modifier.fillMaxSize(), rect = true) }
            Column(
                Modifier.weight(1f).heightIn(min = 48.dp).clickable(onClickLabel = "Open now playing", role = Role.Button, onClick = onOpen),
                verticalArrangement = Arrangement.Center,
            ) {
                Text(item.title, style = GalleryType.rowWork, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
                Text(playerSubtitle(state), style = GalleryType.small().copy(fontSize = 12.sp, lineHeight = 15.sp), color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            GalleryIconButton(
                if (state.isPlaying) GalleryIcons.Pause else GalleryIcons.Play, if (state.isPlaying) "Pause" else "Play", controller::playPause, tint = p.control,
            )
        }
        Box(Modifier.fillMaxWidth().height(1.dp).background(p.edge))
    }
}

/** The Home top bar (54dp): the wordmark at the left (20dp in) and the downloads (with its badge) and settings icon buttons at the right. */
@Composable
fun GalleryHomeBar(active: Int, onDownloads: () -> Unit, onSettings: () -> Unit, modifier: Modifier = Modifier, showDiscover: Boolean = false, onDiscover: () -> Unit = {}) {
    val p = LocalPalette.current
    Row(
        modifier.background(p.ink).fillMaxWidth().statusBarsPadding().heightIn(min = GalleryRules.HOME_BAR.dp).padding(start = GalleryRules.GUTTER.dp, end = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text("discair", style = GalleryType.wordmark, color = p.text, modifier = Modifier.weight(1f).semantics { contentDescription = "Discair" })
        if (showDiscover) GalleryIconButton(GalleryIcons.Disc, "Discover", onDiscover)
        Box {
            GalleryIconButton(GalleryIcons.Download, if (active == 0) "Downloads" else "Downloads, $active active", onDownloads)
            if (active > 0) GalleryBadge(active, Modifier.align(Alignment.TopEnd).padding(top = 9.dp, end = 8.dp))
        }
        GalleryIconButton(GalleryIcons.Gear, "Settings", onSettings)
    }
}

/** The page top bar (52dp): a back icon button at the left, the DM Mono catalogue title centred ("ALBUM", "RADIO") and [action] at the right. */
@Composable
fun GalleryPageBar(title: String, onBack: () -> Unit, modifier: Modifier = Modifier, action: (@Composable () -> Unit)? = null) {
    val p = LocalPalette.current
    Box(modifier.background(p.ink).fillMaxWidth().statusBarsPadding().height(GalleryRules.PAGE_BAR.dp).padding(horizontal = 4.dp)) {
        GalleryIconButton(GalleryIcons.Back, "Back", onBack, Modifier.align(Alignment.CenterStart))
        Text(title.uppercase(), style = GalleryType.catalogue, color = p.textMuted, modifier = Modifier.align(Alignment.Center), maxLines = 1)
        if (action != null) Box(Modifier.align(Alignment.CenterEnd)) { action() }
    }
}

/** The page head under a page bar: a catalogue line (DM Mono caps) then the large title (Fraunces 34). */
@Composable
fun GalleryPageHead(title: String, modifier: Modifier = Modifier, eyebrow: String? = null) {
    val p = LocalPalette.current
    Column(modifier.fillMaxWidth().padding(start = GalleryRules.GUTTER.dp, end = GalleryRules.GUTTER.dp, top = 6.dp)) {
        if (eyebrow != null) Text(eyebrow.uppercase(), style = GalleryType.catalogue, color = p.textMuted, modifier = Modifier.padding(bottom = 4.dp))
        Text(title, style = GalleryType.largeTitle, color = p.text)
    }
}

/** Gallery's toast: `text` fill with `ink` text, radius 2, 14 by 16 padding, an underlined Manrope 700 Undo. Fades in and rises 14dp (the host places it 8dp above the dock). */
@Composable
fun GallerySnackbar(data: SnackbarData) {
    val p = LocalPalette.current
    val s = RoundedCornerShape(2.dp)
    Box(Modifier.padding(horizontal = 12.dp, vertical = 8.dp)) {
        Row(
            Modifier.fillMaxWidth().clip(s).background(p.text).padding(start = 16.dp, top = 4.dp, bottom = 4.dp, end = 4.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(data.visuals.message, Modifier.weight(1f).padding(vertical = 10.dp), color = p.ink, style = GalleryType.body().copy(fontSize = 14.sp, lineHeight = 20.sp))
            data.visuals.actionLabel?.let { label ->
                Box(Modifier.heightIn(min = 48.dp).clickable(role = Role.Button, onClick = { data.performAction() }).padding(horizontal = 12.dp), contentAlignment = Alignment.Center) {
                    Text(label, color = p.ink, textDecoration = TextDecoration.Underline, style = GalleryType.button())
                }
            }
        }
    }
}

/** The sheet's handle: 36 by 4dp in `edge`, 10dp from the top (the sheet's top radius is [GalleryRules.SHEET_TOP_RADIUS]). */
@Composable
fun GallerySheetHandle() {
    Box(Modifier.padding(top = 10.dp, bottom = 18.dp).size(width = 36.dp, height = 4.dp).clip(RoundedCornerShape(2.dp)).background(LocalPalette.current.edge))
}
