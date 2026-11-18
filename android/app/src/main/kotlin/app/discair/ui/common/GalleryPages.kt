package app.discair.ui.common

import android.provider.Settings
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.serialization.json.JsonObject
import app.discair.model.GetState
import app.discair.ui.theme.LocalPalette

/*
 * Pieces shared by Gallery's Album, Artist and Genre pages (G3). Spec: docs/archive/completed/GALLERY_THEME.md sections 7 and 10;
 * mockup: docs/design/gallery/pages/album-artist-genre.html. The measurements are gallery.css (1 CSS px = 1dp).
 */

/** One option of a Gallery menu sheet: a 22dp icon, the label (Manrope 600 15) and an optional small explanation under it. */
data class GalleryMenuItem(val label: String, val icon: ImageVector? = null, val detail: String? = null, val enabled: Boolean = true, val run: () -> Unit)

/** The sheet's header (mockup sheets, frames 1 and 2): a 58dp print, the work title (Fraunces italic) and its catalogue line, then a rule. */
class GalleryMenuHeader(val title: String, val line: String, val cover: @Composable () -> Unit)

/** The three-dot button of a page bar or a row, with the menu it opens. Draws nothing when there is nothing to offer. */
@Composable
fun GalleryMenuButton(label: String, items: List<Pair<String, () -> Unit>>, modifier: Modifier = Modifier) {
    GalleryMenuButton(label, items.map { (text, run) -> GalleryMenuItem(text, run = run) }, modifier, header = null)
}

/** The three-dot button with a sheet of [items] under an optional [header]. Draws nothing when there is nothing to offer. */
@Composable
fun GalleryMenuButton(label: String, items: List<GalleryMenuItem>, modifier: Modifier = Modifier, header: GalleryMenuHeader?) {
    if (items.isEmpty()) return
    var open by remember { mutableStateOf(false) }
    Box(modifier) {
        GalleryIconButton(GalleryIcons.More, label, { open = true })
        if (open) GalleryMenuSheet(items, onDismiss = { open = false }, header = header)
    }
}

/**
 * The pick and song menus as Gallery draws them (mockup sheets, frames 1 and 2): a bottom sheet with the optional print header, then 62dp option rows
 * (icon 22, Manrope 600 15, a small explanation) divided by hairlines. Choosing a row closes the sheet and runs it; a swipe, the scrim and Back close it
 * without running anything.
 */
@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
fun GalleryMenuSheet(items: List<GalleryMenuItem>, onDismiss: () -> Unit, header: GalleryMenuHeader? = null) {
    val p = LocalPalette.current
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = androidx.compose.material3.rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
        Column(Modifier.fillMaxWidth().padding(horizontal = GalleryRules.GUTTER.dp).padding(bottom = 16.dp)) {
            if (header != null) {
                Row(
                    Modifier.fillMaxWidth().padding(bottom = 14.dp).semantics(mergeDescendants = true) { },
                    horizontalArrangement = Arrangement.spacedBy(14.dp), verticalAlignment = Alignment.CenterVertically,
                ) {
                    GalleryPrint(GalleryPagesRules.MENU_PRINT_DP.dp, Modifier.width(GalleryPagesRules.MENU_PRINT_DP.dp), small = true) {
                        Box(Modifier.fillMaxWidth().aspectRatio(1f)) { header.cover() }
                    }
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                        Text(header.title, color = p.text, style = GalleryType.workM, maxLines = 2, overflow = TextOverflow.Ellipsis)
                        if (header.line.isNotEmpty()) GalleryEyebrow(header.line)
                    }
                }
                GalleryRule()
            }
            items.forEachIndexed { i, item ->
                if (i > 0) GalleryRule()
                val tint = if (item.enabled) p.text else p.textMuted
                Row(
                    Modifier.fillMaxWidth().heightIn(min = 62.dp)
                        .clickable(enabled = item.enabled, role = Role.Button, onClick = { onDismiss(); item.run() })
                        .semantics(mergeDescendants = true) { },
                    horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.CenterVertically,
                ) {
                    item.icon?.let { Icon(it, null, tint = if (item.enabled) p.control else p.textMuted, modifier = Modifier.size(GalleryRules.ICON.dp)) }
                    Column(Modifier.weight(1f).padding(vertical = 10.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Text(item.label, color = tint, style = GalleryType.rowTitle())
                        item.detail?.let { Text(it, color = p.textMuted, style = GalleryType.small()) }
                    }
                }
            }
        }
    }
}

/** A catalogue line: DM Mono capitals in `textMuted`. */
@Composable
fun GalleryEyebrow(text: String, modifier: Modifier = Modifier) {
    Text(text.uppercase(), modifier, color = LocalPalette.current.textMuted, style = GalleryType.catalogue)
}

/** Underlined text link in `text` colour (`a.lk` with the colour set to the text, as the artist name under an album title). */
@Composable
fun GalleryTextLink(text: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Text(
        text, color = LocalPalette.current.text, style = GalleryType.body(), textDecoration = TextDecoration.Underline, maxLines = 1, overflow = TextOverflow.Ellipsis,
        modifier = modifier.clickable(role = Role.Button, onClick = onClick),
    )
}

/**
 * Get album: the primary button with its states as words (gallery Home's Get album). [primary] false draws the small outlined button used beside a note.
 * [small] makes the filled one 36dp high too (Discover's entries). One request at a time; Requested and Requesting cannot be pressed again.
 */
@Composable
fun GalleryGetAlbumButton(artist: String, album: String, metadata: JsonObject, modifier: Modifier = Modifier, primary: Boolean = true, small: Boolean = !primary) {
    val hub = LocalAcquisitions.current
    val get = hub.getState(artist, album)
    val busy = get is GetState.Pending || get is GetState.Requested
    GalleryButton(
        when (get) {
            GetState.Pending -> "Requesting…"
            is GetState.Requested -> "Requested"
            is GetState.Failed -> "Try again"
            GetState.Idle -> "Get album"
        },
        { hub.getAlbum(artist, album, metadata) }, modifier,
        kind = if (primary) GalleryButtonKind.Primary else GalleryButtonKind.Outlined,
        icon = GalleryIcons.Get, small = small, enabled = !busy,
    )
}

/** The note under the actions: a 1dp `edge` rule above and below, an info icon, the words, and an optional trailing control (gallery.css `.note`). */
@Composable
fun GalleryNote(text: String, modifier: Modifier = Modifier, trailing: (@Composable () -> Unit)? = null) {
    val p = LocalPalette.current
    Column(modifier.fillMaxWidth().padding(horizontal = GalleryRules.GUTTER.dp)) {
        GalleryRule()
        Row(Modifier.padding(vertical = 14.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(GalleryIcons.Info, null, tint = p.control, modifier = Modifier.size(24.dp))
            Text(text, Modifier.weight(1f), color = p.text, style = GalleryType.small())
            trailing?.invoke()
        }
        GalleryRule()
    }
}

/** "DISC 2" above the first song of each disc of an album that spans several discs. */
@Composable
fun GalleryDiscHeading(disc: Int, modifier: Modifier = Modifier) {
    Text(
        "Disc $disc".uppercase(), modifier.fillMaxWidth().padding(start = GalleryRules.GUTTER.dp, end = GalleryRules.GUTTER.dp, top = 16.dp, bottom = 4.dp),
        color = LocalPalette.current.textMuted, style = GalleryType.catalogue,
    )
}

/** The playing mark: three 2.5dp `accent` bars, 12dp tall, that move only while a song plays and stand still when animations are off (gallery.css `.bars`). */
@Composable
fun GalleryPlayingBars(playing: Boolean, modifier: Modifier = Modifier) {
    val accent = LocalPalette.current.accent
    val context = LocalContext.current
    val still = !playing || remember { Settings.Global.getFloat(context.contentResolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f) == 0f }
    val rest = listOf(6f / 12f, 1f, 8f / 12f)
    val fractions = if (still) rest else {
        val transition = rememberInfiniteTransition(label = "galleryBars")
        listOf(700, 560, 820).mapIndexed { i, ms ->
            val f by transition.animateFloat(0.35f, 1f, infiniteRepeatable(tween(ms, easing = FastOutSlowInEasing), RepeatMode.Reverse), label = "bar$i")
            f
        }
    }
    Canvas(modifier.size(width = 12.dp, height = 12.dp).semantics { contentDescription = if (playing) "Now playing" else "Paused here" }) {
        val w = 2.5.dp.toPx()
        val gap = 2.dp.toPx()
        fractions.forEachIndexed { i, f ->
            val h = size.height * f
            drawRect(accent, Offset(i * (w + gap), size.height - h), Size(w, h))
        }
    }
}

/** A cover in a print with its caption under it: the work in Fraunces italic, then a small line (gallery.css `.cap`). Two sit side by side in a grid. */
@Composable
fun GalleryCaption(
    title: String, sub: String, modifier: Modifier = Modifier, state: String? = null, sharedKey: String? = null, onClick: () -> Unit, cover: @Composable () -> Unit,
) {
    val p = LocalPalette.current
    Column(
        modifier.clickable(role = Role.Button, onClick = onClick).semantics(mergeDescendants = true) { contentDescription = if (sub.isEmpty()) title else "$title, $sub" },
        verticalArrangement = Arrangement.spacedBy(9.dp),
    ) {
        GalleryPrint(GalleryPagesRules.CAPTION_PRINT_DP.dp, Modifier.fillMaxWidth(), small = true, sharedKey = sharedKey) { cover() }
        Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
            Text(title, color = p.text, style = GalleryType.rowWork.copy(lineHeight = 19.sp), maxLines = 1, overflow = TextOverflow.Ellipsis)
            if (sub.isNotEmpty()) Text(sub, color = p.textMuted, style = GalleryType.small().copy(fontSize = 12.sp, lineHeight = 14.sp), maxLines = 1, overflow = TextOverflow.Ellipsis)
            if (state != null) GalleryState(state, color = p.ok)
        }
    }
}

/** A cover or a photo in the mat of a row or a strip: [size] decides the mat (5dp under 72dp). The photo is square inside it. */
@Composable
fun GalleryCoverBox(size: androidx.compose.ui.unit.Dp, modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    GalleryPrint(size, modifier) { Box(Modifier.fillMaxWidth().aspectRatio(1f)) { content() } }
}

/** An artist's photo in a 104dp column with name and (optional) album count under it, the Home "Artists you return to" look. */
@Composable
fun GalleryArtistPlate(name: String, albumCount: Int?, ownedPath: String?, modifier: Modifier = Modifier, onClick: () -> Unit) {
    val p = LocalPalette.current
    Column(
        modifier.width(GalleryPagesRules.SIMILAR_PRINT_DP.dp).clickable(role = Role.Button, onClick = onClick),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        ArtistPhoto(name, ownedPath, Modifier.fillMaxWidth().aspectRatio(4f / 5f), rect = true)
        Text(name, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = GalleryType.rowTitle().copy(fontSize = 13.sp, lineHeight = 16.sp))
        albumCount?.let { GalleryEyebrow(plural(it, "album")) }
    }
}

/** A grey skeleton block for a page that is still loading. */
@Composable
fun GallerySkeleton(modifier: Modifier) {
    Box(modifier.background(LocalPalette.current.raised))
}

/** One-line empty or missing-data message in `textMuted`. */
@Composable
fun GalleryMuted(text: String, modifier: Modifier = Modifier) {
    Text(text, modifier, color = LocalPalette.current.textMuted, style = GalleryType.small())
}

/** Running text cut to [lines] lines with a "Read more" link when it overflows (Manrope 12.5, gallery.css `.sm`). */
@Composable
fun GalleryReadMore(text: String, modifier: Modifier = Modifier, lines: Int = 4) {
    val p = LocalPalette.current
    var expanded by remember { mutableStateOf(false) }
    var overflows by remember { mutableStateOf(false) }
    Column(modifier) {
        Text(
            text, color = p.text, style = GalleryType.small().copy(fontSize = 13.sp, lineHeight = 19.sp),
            maxLines = if (expanded) Int.MAX_VALUE else lines, overflow = TextOverflow.Ellipsis,
            onTextLayout = { if (!expanded) overflows = it.hasVisualOverflow },
        )
        if (overflows || expanded) Text(
            if (expanded) "Show less" else "Read more", color = p.control, textDecoration = TextDecoration.Underline, style = GalleryType.tab(),
            modifier = Modifier.padding(top = 6.dp).clickable(role = Role.Button) { expanded = !expanded },
        )
    }
}
