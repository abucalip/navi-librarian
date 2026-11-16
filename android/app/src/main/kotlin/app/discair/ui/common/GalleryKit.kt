package app.discair.ui.common

import android.graphics.BlurMaskFilter
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.drawIntoCanvas
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import app.discair.ui.theme.GalleryFaces
import app.discair.ui.theme.Layout
import app.discair.ui.theme.LocalFontPair
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.Palette

/**
 * Gallery's measurements (docs/GALLERY_THEME.md sections 3 and 7; the numbers are docs/design/gallery/tokens.json and gallery.css, 1 CSS px = 1dp).
 * Pure, so the tests can pin them.
 */
object GalleryRules {
    const val MAT_LARGE = 11f
    const val MAT_PLAYER = 14f
    const val MAT_SMALL = 5f
    /** A cover under this size (dp) takes the small mat and the small shadow. */
    const val SMALL_BELOW = 72f
    const val BUTTON_RADIUS = 2f
    const val BUTTON_HEIGHT = 44f
    const val BUTTON_SMALL_HEIGHT = 36f
    const val SHEET_TOP_RADIUS = 14f
    const val GUTTER = 20f
    const val ROW_MIN = 64f
    const val ROW_MIN_TRACKS = 56f
    const val DOCK_MINI = 58f
    const val DOCK_BAR = 62f
    const val HOME_BAR = 54f
    const val PAGE_BAR = 52f
    const val ICON = 22f
    const val ICON_INLINE = 18f
    const val ICON_TRANSPORT = 26f
    /** The destinations of the bar, in order (NavRules.discoverInBar). */
    val cells: List<String> = listOf("Home", "Discover", "Library", "Search")

    /** The mat for a print [size] dp across: 5 under 72, else 11 (14 for the player). */
    fun mat(size: Float, player: Boolean = false): Float = if (size < SMALL_BELOW) MAT_SMALL else if (player) MAT_PLAYER else MAT_LARGE

    /** One layer of a print's wall shadow: offset y, blur, spread (all dp) and its alpha; [black] on night palettes, else the palette's text colour. */
    class ShadowLayer(val dy: Float, val blur: Float, val spread: Float, val alpha: Float, val black: Boolean)

    fun shadow(large: Boolean, light: Boolean): List<ShadowLayer> = when {
        light && large -> listOf(ShadowLayer(1f, 2f, 0f, 0.08f, false), ShadowLayer(26f, 36f, -24f, 0.50f, false))
        light -> listOf(ShadowLayer(1f, 2f, 0f, 0.08f, false), ShadowLayer(12f, 18f, -12f, 0.45f, false))
        large -> listOf(ShadowLayer(30f, 40f, -22f, 0.90f, true))
        else -> listOf(ShadowLayer(14f, 20f, -12f, 0.85f, true))
    }

    /** The night palettes' glow behind the Home pick and the Now Playing cover: its colour with alpha, or null on a day palette. */
    fun spot(p: Palette): Color? = when (p.id) {
        "gallery_graphite" -> Color(255, 214, 150).copy(alpha = 0.08f)
        "gallery_oxblood" -> Color(242, 139, 120).copy(alpha = 0.08f)
        "gallery_moss" -> Color(200, 230, 170).copy(alpha = 0.07f)
        else -> null
    }

    /** Snackbar, sheet, dock and prints use the palette's own colours; the scrim is fixed (gallery.css `.scrim`). */
    val SCRIM = Color(10, 10, 14).copy(alpha = 0.42f)
}

/** True while the owner's theme is Gallery. Every Gallery branch in a shared control is guarded by this, so no other theme changes. */
@Composable
@androidx.compose.runtime.ReadOnlyComposable
fun isGallery(): Boolean = LocalPalette.current.layout == Layout.Gallery

/** Gallery's text styles (docs/GALLERY_THEME.md 5.3). Fraunces and DM Mono are Gallery's own; the body face follows the owner's font pair. */
object GalleryType {
    private fun fr(weight: Int, opsz: Float, italic: Boolean, size: Float, line: Float, tracking: Float = 0f, features: String? = null) = TextStyle(
        fontFamily = GalleryFaces.fraunces(weight, opsz, italic), fontWeight = FontWeight(weight),
        fontStyle = if (italic) androidx.compose.ui.text.font.FontStyle.Italic else androidx.compose.ui.text.font.FontStyle.Normal,
        fontSize = size.sp, lineHeight = line.sp, letterSpacing = tracking.em, fontFeatureSettings = features,
    )

    val wordmark = fr(600, 96f, true, 25f, 25f, -0.02f)
    val largeTitle = fr(400, 96f, false, 34f, 38f, -0.02f)
    val workXL = fr(420, 72f, true, 36f, 38f, -0.01f)
    val work = fr(420, 72f, true, 30f, 32f, -0.01f)
    val workM = fr(420, 72f, true, 22f, 26f, -0.01f)
    val section = fr(400, 48f, false, 21f, 24f)
    val sourceSwitch = fr(400, 24f, false, 17f, 20f)
    val rowWork = fr(420, 24f, true, 16f, 20f)
    val genreList = fr(300, 48f, false, 22f, 32f)
    val lyric = fr(400, 36f, false, 24f, 32f, -0.01f)
    val trackNumber = fr(400, 24f, false, 19f, 24f, features = "onum")
    val numeral = fr(400, 72f, false, 40f, 40f, -0.02f, features = "lnum")
    val searchField = fr(400, 36f, false, 22f, 28f)

    val catalogue = TextStyle(fontFamily = GalleryFaces.mono, fontWeight = FontWeight.Medium, fontSize = 10.5.sp, lineHeight = 14.sp, letterSpacing = 0.07.em)
    val state = catalogue.copy(letterSpacing = 0.06.em)
    val time = TextStyle(fontFamily = GalleryFaces.mono, fontWeight = FontWeight.Normal, fontSize = 12.sp, lineHeight = 16.sp, fontFeatureSettings = "tnum")

    @Composable private fun body(weight: Int, size: Float, line: Float) =
        TextStyle(fontFamily = LocalFontPair.current.body, fontWeight = FontWeight(weight), fontSize = size.sp, lineHeight = line.sp)

    @Composable fun rowTitle() = body(600, 15f, 20f)
    @Composable fun body() = body(400, 14f, 21f)
    @Composable fun small() = body(400, 12.5f, 18f)
    @Composable fun button() = body(700, 14f, 14f)
    @Composable fun tab() = body(600, 13f, 16f)
    @Composable fun barLabel() = body(600, 11f, 14f)
}

/**
 * A cover in its mat (section 7.1): the `mat` colour round it, no corner radius, a soft wall shadow, and the night palettes' spot is [GallerySpot].
 * [size] is the cover's width in dp and picks the mat and the shadow (5dp mats under 72dp); [player] takes the 14dp mat of Now Playing;
 * [bare] is the mini player's cover (no mat, no shadow).
 */
@Composable
fun GalleryPrint(size: Dp, modifier: Modifier = Modifier, player: Boolean = false, bare: Boolean = false, content: @Composable () -> Unit) {
    val p = LocalPalette.current
    if (bare) { Box(modifier.size(size)) { content() }; return }
    val large = size.value >= GalleryRules.SMALL_BELOW
    val mat = GalleryRules.mat(size.value, player).dp
    Box(modifier.galleryShadow(large, p).background(p.mat).padding(mat)) { content() }
}

/** The wall shadow of a print: each layer of [GalleryRules.shadow] drawn as a blurred rectangle, inflated by its (negative) spread and shifted down. */
fun Modifier.galleryShadow(large: Boolean, p: Palette): Modifier = drawBehind {
    val layers = GalleryRules.shadow(large, p.light)
    val paint = android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG)
    drawIntoCanvas { canvas ->
        for (l in layers) {
            paint.color = (if (l.black) Color.Black else p.text).copy(alpha = l.alpha).toArgb()
            // CSS blur radius b is a Gaussian of sigma b/2; BlurMaskFilter's radius is about (sigma - 0.5) / 0.577.
            paint.maskFilter = BlurMaskFilter(((l.blur / 2f - 0.5f) / 0.577f).coerceAtLeast(0.5f) * density, BlurMaskFilter.Blur.NORMAL)
            val s = l.spread.dp.toPx()
            val dy = l.dy.dp.toPx()
            canvas.nativeCanvas.drawRect(-s, -s + dy, size.width + s, size.height + s + dy, paint)
        }
    }
}

/** The night palettes' glow behind the Home pick and the Now Playing cover: a radial wash, 60% by 55% of the area, fading out at 70%. No-op on a day palette. */
fun Modifier.gallerySpot(p: Palette): Modifier {
    val spot = GalleryRules.spot(p) ?: return this
    return drawBehind {
        val rx = size.width * 0.6f / 2f / 0.7f
        drawRect(Brush.radialGradient(listOf(spot, Color.Transparent), center = Offset(size.width / 2, size.height * 0.55f / 2f + size.height * 0.25f), radius = rx))
    }
}

// ---------------------------------------------------------------- controls (section 7.2)

enum class GalleryButtonKind { Primary, Outlined, Danger, Text }

/**
 * Gallery's button: 44dp high (36 when [small]), radius 2, 18dp side padding. Primary is a `control` fill with an `onControl` label (Manrope 700 14, icon 19);
 * Outlined is a 1dp `control` outline; Danger the same in `chartRedText`; Text has no fill and an underlined label.
 */
@Composable
fun GalleryButton(
    label: String, onClick: () -> Unit, modifier: Modifier = Modifier, kind: GalleryButtonKind = GalleryButtonKind.Primary,
    icon: ImageVector? = null, small: Boolean = false, enabled: Boolean = true,
) {
    GalleryButtonBody(kind, onClick, modifier, enabled, small) {
        if (icon != null) Icon(icon, null, Modifier.size(if (small) 16.dp else 19.dp))
        Text(label, maxLines = 1, overflow = TextOverflow.Ellipsis, textDecoration = if (kind == GalleryButtonKind.Text) TextDecoration.Underline else null)
    }
}

/** The shared body of every Gallery button: also what the Material `Button`, `OutlinedButton` and `FilledTonalButton` wrappers draw. */
@Composable
fun GalleryButtonBody(kind: GalleryButtonKind, onClick: () -> Unit, modifier: Modifier, enabled: Boolean, small: Boolean = false, content: @Composable RowScope.() -> Unit) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(GalleryRules.BUTTON_RADIUS.dp)
    val fill = if (kind == GalleryButtonKind.Primary) p.control else Color.Transparent
    val ink = when (kind) {
        GalleryButtonKind.Primary -> p.onControl
        GalleryButtonKind.Danger -> p.chartRedText
        else -> p.control
    }
    val h = if (small) GalleryRules.BUTTON_SMALL_HEIGHT else GalleryRules.BUTTON_HEIGHT
    val outline = when (kind) { GalleryButtonKind.Outlined -> p.control; GalleryButtonKind.Danger -> p.chartRedText; else -> null }
    Row(
        modifier.heightIn(min = h.dp).clip(shape).background(fill)
            .then(if (outline != null) Modifier.border(1.dp, outline, shape) else Modifier)
            .clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .padding(horizontal = if (kind == GalleryButtonKind.Text) 10.dp else if (small) 12.dp else 18.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp, Alignment.CenterHorizontally), verticalAlignment = Alignment.CenterVertically,
    ) {
        androidx.compose.runtime.CompositionLocalProvider(
            androidx.compose.material3.LocalContentColor provides (if (enabled) ink else ink.copy(alpha = 0.38f)),
        ) {
            androidx.compose.material3.ProvideTextStyle(GalleryType.button().copy(fontSize = if (small) 12.5.sp else 14.sp)) { content() }
        }
    }
}

/** An icon button: a 44dp square with a 22dp glyph in `control` and no background. Touch target 48dp. */
@Composable
fun GalleryIconButton(icon: ImageVector, label: String, onClick: () -> Unit, modifier: Modifier = Modifier, tint: Color = LocalPalette.current.control, size: Dp = GalleryRules.ICON.dp) {
    Box(
        modifier.size(48.dp).clip(CircleShape).clickable(role = Role.Button, onClick = onClick).semantics { contentDescription = label },
        contentAlignment = Alignment.Center,
    ) { Icon(icon, null, tint = tint, modifier = Modifier.size(size)) }
}

/**
 * The source switch: Fraunces 17 words 22dp apart, the selected one in `text` with a 1.5dp `control` underline, the others in `textMuted`.
 * Scrolls sideways when the words do not fit. Never chips or pills.
 */
@Composable
fun GallerySourceSwitch(labels: List<String>, selectedIndex: Int, onSelect: (Int) -> Unit, modifier: Modifier = Modifier) {
    Row(modifier.horizontalScroll(rememberScrollState()).padding(horizontal = GalleryRules.GUTTER.dp), horizontalArrangement = Arrangement.spacedBy(22.dp)) {
        labels.forEachIndexed { i, label -> GalleryWord(label, i == selectedIndex, GalleryType.sourceSwitch, Role.Tab) { onSelect(i) } }
    }
}

/** One underlined word of a switch or a tab row. */
@Composable
private fun GalleryWord(label: String, on: Boolean, style: TextStyle, role: Role, padTop: Dp = 8.dp, padBottom: Dp = 7.dp, onClick: () -> Unit) {
    val p = LocalPalette.current
    Box(
        Modifier.heightIn(min = 48.dp).clickable(role = role, onClick = onClick).semantics { selected = on },
        contentAlignment = Alignment.Center,
    ) {
        Text(
            label, style = style, color = if (on) p.text else p.textMuted, maxLines = 1,
            modifier = Modifier.padding(top = padTop, bottom = padBottom).drawBehind {
                if (on) drawRect(p.control, Offset(0f, size.height - 1.5.dp.toPx()), Size(size.width, 1.5.dp.toPx()))
            },
        )
    }
}

/** In-page tabs: Manrope 600 13, 22dp apart, a 1dp `edge` rule under the row and a 1.5dp `control` underline on the selected tab. */
@Composable
fun GalleryTabs(labels: List<String>, selectedIndex: Int, onSelect: (Int) -> Unit, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    Row(
        modifier.fillMaxWidth().drawBehind { drawRect(p.edge, Offset(0f, size.height - 1.dp.toPx()), Size(size.width, 1.dp.toPx())) }
            .horizontalScroll(rememberScrollState()).padding(horizontal = GalleryRules.GUTTER.dp),
        horizontalArrangement = Arrangement.spacedBy(22.dp),
    ) {
        labels.forEachIndexed { i, label -> GalleryWord(label, i == selectedIndex, GalleryType.tab(), Role.Tab, padTop = 12.dp, padBottom = 10.dp) { onSelect(i) } }
    }
}

/** A section head: 34dp above, a 1dp `edge` rule, 12dp, the heading in Fraunces 21 left and an optional DM Mono link right, 14dp to the content. */
@Composable
fun GallerySectionHead(title: String, modifier: Modifier = Modifier, link: String? = null, onLink: (() -> Unit)? = null, first: Boolean = false) {
    val p = LocalPalette.current
    Column(modifier.fillMaxWidth().padding(top = if (first) 0.dp else 34.dp, start = GalleryRules.GUTTER.dp, end = GalleryRules.GUTTER.dp)) {
        GalleryRule()
        Row(Modifier.fillMaxWidth().padding(top = 12.dp, bottom = 14.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Bottom) {
            Text(title, style = GalleryType.section, color = p.text, modifier = Modifier.weight(1f))
            if (link != null) {
                Text(
                    link.uppercase(), style = GalleryType.catalogue, color = p.control, textDecoration = TextDecoration.Underline, maxLines = 1,
                    modifier = Modifier.heightIn(min = 24.dp).then(if (onLink != null) Modifier.clickable(role = Role.Button, onClick = onLink) else Modifier),
                )
            }
        }
    }
}

/** A 1dp `edge` hairline: section rules and row dividers. */
@Composable
fun GalleryRule(modifier: Modifier = Modifier) {
    Box(modifier.fillMaxWidth().height(1.dp).background(LocalPalette.current.edge))
}

/**
 * A row (section 7.2): at least 64dp, a 14dp gap, a 1dp `edge` divider under it, [lead] (a 48dp print, a 52dp photo print or a 36dp icon), the title and
 * sub, then [trail] (a state word, a small button, an icon button).
 */
@Composable
fun GalleryRow(
    title: String, modifier: Modifier = Modifier, sub: String = "", onClick: (() -> Unit)? = null, divider: Boolean = true, minHeight: Dp = GalleryRules.ROW_MIN.dp,
    italicTitle: Boolean = false, lead: (@Composable () -> Unit)? = null, trail: (@Composable () -> Unit)? = null,
) {
    val p = LocalPalette.current
    Column(modifier) {
        Row(
            Modifier.fillMaxWidth().heightIn(min = minHeight)
                .then(if (onClick != null) Modifier.clickable(role = Role.Button, onClick = onClick) else Modifier)
                .semantics(mergeDescendants = true) { contentDescription = if (sub.isEmpty()) title else "$title, $sub" }
                .padding(vertical = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(14.dp), verticalAlignment = Alignment.CenterVertically,
        ) {
            lead?.invoke()
            Column(Modifier.weight(1f)) {
                Text(title, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = if (italicTitle) GalleryType.rowWork else GalleryType.rowTitle())
                if (sub.isNotEmpty()) Text(sub, color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis, style = GalleryType.small())
            }
            trail?.invoke()
        }
        if (divider) GalleryRule()
    }
}

/** A state word: DM Mono 10.5 capitals. "In library" is `ok`; others default to `textMuted`. Never a coloured dot alone. */
@Composable
fun GalleryState(text: String, modifier: Modifier = Modifier, color: Color = LocalPalette.current.textMuted) {
    Text(text.uppercase(), style = GalleryType.state, color = color, maxLines = 1, modifier = modifier)
}

/** A tag: DM Mono 10 capitals in a 1dp `edge` box, 5 by 7 padding. [accent] draws it in the accent (the "On air" tag). */
@Composable
fun GalleryTag(text: String, modifier: Modifier = Modifier, accent: Boolean = false) {
    val p = LocalPalette.current
    val c = if (accent) p.accent else p.textMuted
    Text(
        text.uppercase(), style = GalleryType.state.copy(fontSize = 10.sp, lineHeight = 10.sp), color = c, maxLines = 1,
        modifier = modifier.border(1.dp, if (accent) c else p.edge).padding(horizontal = 7.dp, vertical = 5.dp),
    )
}

/** The downloads badge: a 15dp pill, `accent` fill, `onAccent` Manrope 700 9. */
@Composable
fun GalleryBadge(count: Int, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    Text(
        if (count > 99) "99+" else count.toString(), color = p.onAccent, maxLines = 1,
        style = TextStyle(fontFamily = LocalFontPair.current.body, fontWeight = FontWeight.Bold, fontSize = 9.sp, lineHeight = 15.sp),
        modifier = modifier.heightIn(min = 15.dp).widthIn(min = 15.dp).clip(RoundedCornerShape(8.dp)).background(p.accent).padding(horizontal = 4.dp),
    )
}

/** Gallery's switch: 44 by 26. Off: a 1dp `edgeStrong` outline and an 18dp `edgeStrong` knob. On: a `control` fill and an `onControl` knob. */
@Composable
fun GallerySwitch(checked: Boolean, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    val knobX by animateDpAsState(if (checked) 22.dp else 4.dp, tween(200), label = "galleryKnob")
    Box(
        modifier.size(width = 44.dp, height = 26.dp).clip(RoundedCornerShape(13.dp))
            .then(if (checked) Modifier.background(p.control) else Modifier.border(1.dp, p.edgeStrong, RoundedCornerShape(13.dp))),
    ) {
        Box(Modifier.align(Alignment.CenterStart).offset(x = knobX).size(18.dp).background(if (checked) p.onControl else p.edgeStrong, CircleShape))
    }
}

/** A thin progress line: a 1.5dp `edge` track with the played part in `text` (gallery.css `.prog`). */
@Composable
fun GalleryProgress(fraction: Float, modifier: Modifier = Modifier, color: Color = LocalPalette.current.text) {
    val p = LocalPalette.current
    Box(modifier.fillMaxWidth().height(1.5.dp).background(p.edge)) {
        Box(Modifier.fillMaxWidth(fraction.coerceIn(0f, 1f)).height(1.5.dp).background(color))
    }
}

/** The download tracker: four 2dp segments 4dp apart (`text` when reached, `edge` ahead, `chartRedText` on the failed step). [failedAt] is a 0-based step or -1. */
@Composable
fun GalleryTracker(reached: Int, modifier: Modifier = Modifier, failedAt: Int = -1, steps: Int = 4) {
    val p = LocalPalette.current
    Row(modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        for (i in 0 until steps) {
            val c = if (i == failedAt) p.chartRedText else if (i < reached) p.text else p.edge
            Box(Modifier.weight(1f).height(2.dp).background(c))
        }
    }
}

/** A banner: a 1dp `caution` rule above and an `edge` rule below, a `caution` icon, text in `text` and an optional `control` link. */
@Composable
fun GalleryBanner(text: String, modifier: Modifier = Modifier, link: String? = null, onLink: (() -> Unit)? = null) {
    val p = LocalPalette.current
    Column(modifier.fillMaxWidth().padding(horizontal = GalleryRules.GUTTER.dp)) {
        Box(Modifier.fillMaxWidth().height(1.dp).background(p.caution))
        Row(Modifier.padding(vertical = 12.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.Top) {
            Icon(GalleryIcons.Warning, null, tint = p.caution, modifier = Modifier.size(GalleryRules.ICON_INLINE.dp))
            Text(text, color = p.text, style = GalleryType.small().copy(fontSize = 13.sp, lineHeight = 19.sp), modifier = Modifier.weight(1f))
            if (link != null) Text(link, color = p.control, textDecoration = TextDecoration.Underline, style = GalleryType.tab(), modifier = Modifier.then(if (onLink != null) Modifier.clickable(role = Role.Button, onClick = onLink) else Modifier))
        }
        GalleryRule()
    }
}
