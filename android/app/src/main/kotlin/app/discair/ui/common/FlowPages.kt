package app.discair.ui.common

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import app.discair.ui.player.PlayerIcons
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.Palette
import app.discair.ui.theme.accentText

/**
 * Numbers and rules of Flow's Album, Artist and Genre pages (mockup flow/album-artist-genre, flow.css `.hero`, `.ahero`, `.wash`).
 * Kept here, not in the composables, so the unit test can hold them.
 */
object FlowPagesRules {
    /** The wash behind an album page fades from the cover's colour to the page over this many dp (flow.css `.fl.wash .scr`). */
    const val WASH_HEIGHT = 420f

    /** The album cover in front (flow.css `.hero .art`). */
    const val ALBUM_COVER = 232

    /** The artist's photo is this tall for every unit of width (flow.css `.ahero .ar`, aspect 1 to .92). */
    const val ARTIST_PHOTO_RATIO = 0.92f

    /** Small covers in a strip: similar albums, the artist's own albums. */
    const val SIMILAR_COVER = 112
    const val LIBRARY_COVER = 104

    /** A round photo in the "who" strip and its cell (flow.css `.who`). */
    const val WHO_PHOTO = 80
    const val WHO_CELL = 84

    /** Genre grid: two columns, 14dp apart (shared.css `.g2`). */
    const val GRID_GAP = 14

    /** How far the wash has scrolled away: the whole way once the first item has left, else by the first item's offset (px). */
    fun washScroll(firstVisibleIndex: Int, firstVisibleOffset: Int, height: Float): Float =
        if (firstVisibleIndex > 0) height else firstVisibleOffset.toFloat().coerceIn(0f, height)
}

/**
 * The page colour with the cover's wash on top: the wash at the top, fading to the page over [FlowPagesRules.WASH_HEIGHT]. It scrolls away
 * with the list, as the mockup draws it. The wash is the cover's own colour as the app already derives it (`pastelOf`, D2).
 */
fun Modifier.flowWash(tint: Color?, list: LazyListState, p: Palette): Modifier {
    // The cover's pastel (decision D2), or `raised` while the cover has not given a colour yet.
    val wash = tint?.forThemeOf(p) ?: p.raised
    return drawBehind {
        drawRect(p.ink)
        val h = FlowPagesRules.WASH_HEIGHT.dp.toPx()
        val scrolled = FlowPagesRules.washScroll(list.firstVisibleItemIndex, list.firstVisibleItemScrollOffset, h)
        drawRect(Brush.verticalGradient(listOf(wash, p.ink), startY = -scrolled, endY = h - scrolled))
    }
}

/** The pastel of a cover tint for this palette (the same one `Color.forTheme` gives, without needing the composition). */
private fun Color.forThemeOf(p: Palette): Color = if (p.light) app.discair.ui.theme.pastelOf(this) else this

/**
 * The page's top bar (flow.css `.bar`): Back at the left, an optional [title] after it, an optional three-dot menu at the right. 44dp round
 * buttons. On [over] a photo they are white glyphs on a 28% black disc (`.over .ib`); otherwise bare accent glyphs (`.bar .ib`).
 */
@Composable
fun FlowPageBar(onBack: () -> Unit, menu: List<Pair<String, () -> Unit>>, modifier: Modifier = Modifier, title: String? = null, over: Boolean = false) {
    val p = LocalPalette.current
    val glyph = if (over) Color.White else p.accentText
    val disc = if (over) Modifier.background(Color.Black.copy(alpha = 0.28f), CircleShape) else Modifier
    Row(modifier.statusBarsPadding().fillMaxWidth().padding(start = 8.dp, end = 8.dp, top = 4.dp), verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(Target).clip(CircleShape).clickable(role = Role.Button, onClick = onBack), contentAlignment = Alignment.Center) {
            Box(Modifier.size(44.dp).then(disc), contentAlignment = Alignment.Center) { Icon(PlayerIcons.Left, contentDescription = "Back", tint = glyph) }
        }
        if (title != null) Text(
            title, Modifier.weight(1f).padding(start = 4.dp), color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis,
            style = MaterialTheme.typography.titleMedium.copy(fontSize = 15.sp, lineHeight = 20.sp, fontWeight = FontWeight.SemiBold),
        ) else Box(Modifier.weight(1f))
        if (menu.isNotEmpty()) {
            var open by remember { mutableStateOf(false) }
            Box {
                Box(Modifier.size(Target).clip(CircleShape).clickable(role = Role.Button) { open = true }, contentAlignment = Alignment.Center) {
                    Box(Modifier.size(44.dp).then(disc), contentAlignment = Alignment.Center) { Icon(Icons.Default.MoreVert, contentDescription = "More", tint = glyph) }
                }
                DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
                    menu.forEach { (label, run) -> DropdownMenuItem(text = { Text(label) }, onClick = { open = false; run() }) }
                }
            }
        }
    }
}

/** A section heading (flow.css `h3`: Inter 700 20/24) with an optional accent link at the right (`.h a`: 500 14). */
@Composable
fun FlowHeading(title: String, modifier: Modifier = Modifier, link: String? = null, onLink: () -> Unit = {}) {
    val p = LocalPalette.current
    Row(modifier.fillMaxWidth().padding(horizontal = 16.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(
            title, Modifier.weight(1f).semantics { heading() }, color = p.text,
            style = MaterialTheme.typography.titleLarge.copy(fontSize = 20.sp, lineHeight = 24.sp, fontWeight = FontWeight.Bold, letterSpacing = (-0.02).em),
        )
        if (link != null) Box(Modifier.heightIn(min = Target).clickable(role = Role.Button, onClick = onLink).padding(start = 8.dp), contentAlignment = Alignment.Center) {
            Text(link, color = p.accentText, style = MaterialTheme.typography.labelLarge.copy(fontSize = 14.sp, fontWeight = FontWeight.Medium))
        }
    }
}

/** A cover with no outline, radius 8 unless [radius] says otherwise (flow.css `.cv`). */
@Composable
fun FlowCover(artist: String, album: String, ownedPath: String?, modifier: Modifier = Modifier, radius: Int = 8) {
    AlbumCover(artist, album, ownedPath, modifier.aspectSquare().clip(RoundedCornerShape(radius.dp)), rect = true)
}

/** A round artist photo 80dp, its name under it, two lines at most, centred, in a cell 84dp wide (flow.css `.who`). */
@Composable
fun FlowArtistChip(name: String, ownedPath: String?, onClick: () -> Unit, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    Column(
        modifier.width(FlowPagesRules.WHO_CELL.dp).clip(RoundedCornerShape(8.dp)).clickable(role = Role.Button, onClick = onClick),
        horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        ArtistPhoto(name, ownedPath, Modifier.size(FlowPagesRules.WHO_PHOTO.dp).clip(CircleShape), circle = true)
        Text(
            name, color = p.text, textAlign = TextAlign.Center, maxLines = 2, overflow = TextOverflow.Ellipsis,
            style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Medium, fontSize = 12.sp, lineHeight = 16.sp),
        )
    }
}
