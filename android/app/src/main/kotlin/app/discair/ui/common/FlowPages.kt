package app.discair.ui.common

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.filled.Check
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
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.graphics.vector.ImageVector
import app.discair.model.GetState
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
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

    /** Discover (flow.css `.dc`): the card's cover, its padding, the gap between cards, the small capsule buttons and the insight card's cover. */
    const val DISCOVER_COVER = 112
    const val DISCOVER_GAP = 12
    const val SMALL_BUTTON = 34
    const val INSIGHT_COVER = 88

    /** The search field (flow.css `.field`) and a list row's cover (`.li .cv`). */
    const val FIELD_HEIGHT = 44
    const val ROW_COVER = 48

    /** Ranked bars (flow.css `.bars`): 8dp high, the longest one 85% of the track, the others in proportion to it, never under 4%. */
    const val BAR_HEIGHT = 8
    const val BAR_LONGEST = 0.85f
    fun barFraction(share: Double, top: Double): Float {
        val longest = top.takeIf { it > 0 } ?: 1.0
        return (BAR_LONGEST * (share / longest).toFloat()).coerceIn(0.04f, BAR_LONGEST)
    }

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
fun FlowPageBar(
    onBack: () -> Unit, menu: List<Pair<String, () -> Unit>>, modifier: Modifier = Modifier, title: String? = null, over: Boolean = false,
    trailing: @Composable () -> Unit = {},
) {
    val p = LocalPalette.current
    val glyph = if (over) Color.White else p.accentText
    val disc = if (over) Modifier.background(Color.Black.copy(alpha = 0.28f), CircleShape) else Modifier
    Row(modifier.statusBarsPadding().fillMaxWidth().padding(start = 8.dp, end = 8.dp, top = 4.dp), verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(Target).clip(CircleShape).clickable(role = Role.Button, onClick = onBack), contentAlignment = Alignment.Center) {
            Box(Modifier.size(44.dp).then(disc), contentAlignment = Alignment.Center) { Icon(ArtIcons.Back, contentDescription = "Back", tint = glyph) }
        }
        if (title != null) Text(
            title, Modifier.weight(1f).padding(start = 4.dp), color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis,
            style = MaterialTheme.typography.titleMedium.copy(fontSize = 15.sp, lineHeight = 20.sp, fontWeight = FontWeight.SemiBold),
        ) else Box(Modifier.weight(1f))
        trailing()
        if (menu.isNotEmpty()) {
            var open by remember { mutableStateOf(false) }
            Box {
                Box(Modifier.size(Target).clip(CircleShape).clickable(role = Role.Button) { open = true }, contentAlignment = Alignment.Center) {
                    Box(Modifier.size(44.dp).then(disc), contentAlignment = Alignment.Center) { Icon(ArtIcons.More, contentDescription = "More", tint = glyph) }
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

/** A small caption in capitals (flow.css `.eb`: Inter 600 12/16, 0.04em, muted): "ARTISTS", "YOUR TASTE · LAST 90 DAYS". */
@Composable
fun FlowEyebrow(text: String, modifier: Modifier = Modifier) {
    Text(
        text.uppercase(), modifier, color = LocalPalette.current.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis,
        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold, fontSize = 12.sp, lineHeight = 16.sp, letterSpacing = 0.04.em),
    )
}

/**
 * A 34dp capsule (flow.css `.btn.sm`, `.dc .acts .btn`) inside a 48dp touch height: filled with the accent and a white label when [primary], else
 * `raised` with an accent label. [icon] only, with no [label], is the round 34dp button.
 */
@Composable
fun FlowSmallButton(
    label: String?, icon: ImageVector?, primary: Boolean, description: String, modifier: Modifier = Modifier,
    state: String? = null, enabled: Boolean = true, onClick: () -> Unit,
) {
    val p = LocalPalette.current
    val ink = if (primary) p.onAccent else p.accentText
    val shape = RoundedCornerShape(17.dp)
    Box(
        modifier.heightIn(min = Target).clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .semantics { contentDescription = description; if (state != null) stateDescription = state },
        contentAlignment = Alignment.Center,
    ) {
        Row(
            Modifier.height(FlowPagesRules.SMALL_BUTTON.dp).then(if (label == null) Modifier.width(FlowPagesRules.SMALL_BUTTON.dp) else Modifier.padding(horizontal = 14.dp))
                .clip(shape).background(if (primary) p.accent else p.raised),
            horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically,
        ) {
            if (icon != null) Icon(icon, contentDescription = null, tint = if (label == null) p.text else ink, modifier = Modifier.size(if (label == null) 18.dp else 20.dp))
            if (icon != null && label != null) Spacer(Modifier.width(4.dp))
            if (label != null) Text(label, color = ink, maxLines = 1, style = MaterialTheme.typography.labelLarge.copy(fontSize = 14.sp, fontWeight = FontWeight.SemiBold))
        }
    }
}

/**
 * The Get capsule for one album: Get, Requesting, Requested, or Retry after a failure, each with its state spoken. A request is never sent twice:
 * only Get and Retry take a tap. [metadata] is what the server needs to find the album.
 */
@Composable
fun FlowGetButton(artist: String, album: String, metadata: kotlinx.serialization.json.JsonObject, modifier: Modifier = Modifier) {
    val hub = LocalAcquisitions.current
    val get = hub.getState(artist, album)
    val idle = get is GetState.Idle || get is GetState.Failed
    FlowSmallButton(
        when (get) { GetState.Pending -> "Requesting"; is GetState.Requested -> "Requested"; is GetState.Failed -> "Retry"; else -> "Get" },
        when (get) { is GetState.Requested -> ArtIcons.Check; GetState.Pending, is GetState.Failed, GetState.Idle -> ArtIcons.Get },
        idle, "Get album $album", modifier,
        state = when (get) { GetState.Idle -> "Not requested"; GetState.Pending -> "Requesting"; is GetState.Requested -> "Requested. Follow it under Downloads"; is GetState.Failed -> "Could not request. Select to try again" },
        enabled = idle,
    ) { hub.getAlbum(artist, album, metadata) }
}

/** A page's large title (flow.css `.lt`: Inter 800 30/36, -0.03em) for a page the shell's bar does not title, such as the Search sheet. */
@Composable
fun FlowLargeTitle(text: String, modifier: Modifier = Modifier) {
    Text(
        text, modifier.semantics { heading() }, color = LocalPalette.current.text, maxLines = 1,
        style = MaterialTheme.typography.headlineLarge.copy(fontSize = 30.sp, lineHeight = 36.sp, fontWeight = FontWeight.ExtraBold, letterSpacing = (-0.03).em),
    )
}

/** The grey chevron at the end of a row (flow.css `.chev`, 16dp). */
@Composable
fun FlowChevron(modifier: Modifier = Modifier) {
    Icon(ArtIcons.Chevron, contentDescription = null, tint = FlowRules.chevron(LocalPalette.current), modifier = modifier.size(16.dp))
}
