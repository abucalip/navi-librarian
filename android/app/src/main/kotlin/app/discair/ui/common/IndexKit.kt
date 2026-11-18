package app.discair.ui.common

import androidx.compose.animation.core.animateDpAsState
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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.material3.minimumInteractiveComponentSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.RectangleShape
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.layout.positionInParent
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import app.discair.ui.theme.IndexMotion
import app.discair.ui.theme.Layout
import app.discair.ui.theme.LocalFontPair
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.LocalThemePalette
import app.discair.ui.theme.Palette
import app.discair.ui.theme.rememberReducedMotion

/**
 * Index's measurements (docs/INDEX_THEME.md sections 3 and 7; the numbers are docs/design/index/tokens.json and index.css, 1 CSS px = 1dp).
 * Pure, so the tests can pin them.
 */
object IndexRules {
    const val GUTTER = 16f
    const val RULE_HEAVY = 2f
    const val RULE_LIGHT = 1f
    const val BUTTON_RADIUS = 3f
    const val BUTTON_HEIGHT = 44f
    const val BUTTON_SMALL_HEIGHT = 36f
    const val SHEET_TOP_RADIUS = 6f
    const val ROW_MIN = 64f
    const val ROW_MIN_TRACKS = 54f
    const val TOUCH_MIN = 48f
    const val ICON_BUTTON = 44f
    const val ICON = 22f
    const val ICON_INLINE = 18f
    const val ICON_TRANSPORT = 26f
    const val HOME_BAR = 54f
    const val PAGE_BAR = 52f
    const val DOCK_STRIP = 56f
    const val DOCK_BAR = 60f
    const val STRIP_COVER = 38f
    const val STRIP_PROGRESS = 3f
    const val SNACK_HEIGHT = 52f
    const val SNACK_RADIUS = 3f
    const val TABS_HEIGHT = 40f
    const val SOURCE_HEIGHT = 34f
    const val SOURCE_BAR = 3f
    const val SWITCH_WIDTH = 44f
    const val SWITCH_HEIGHT = 24f
    const val SEEK = 6f
    const val SEARCH_FIELD = 52f

    /** The bar's cells in order (NavRules.discoverInBar, decision I3). */
    val cells: List<String> = IndexMotion.barOrder

    /** The scrim behind a sheet: rgba(10, 10, 12, .5). */
    val SCRIM = Color(10, 10, 12).copy(alpha = 0.5f)
}

/**
 * Index's own colours (docs/INDEX_THEME.md 4.1 and 4.2, decision I1): the mini-player strip and the insight block. They are not [Palette] fields, so no
 * other theme carries them. Keyed by palette id; the values are `tones` in docs/design/index/tokens.json (IndexTest pins them).
 */
class IndexTones(
    val strip: Color, val onStrip: Color, val stripMuted: Color, val stripProgress: Color,
    val insight: Color, val onInsight: Color, val insightLabel: Color,
) {
    companion object {
        private fun c(hex: Long) = Color(0xFF000000 or hex)

        val SignalBlue = IndexTones(c(0x0B0C0E), c(0xFFFFFF), c(0xA7ACB4), c(0x2B4BFF), c(0x0B0C0E), c(0xFFFFFF), c(0xAEB4FF))
        val NewsprintRed = IndexTones(c(0x141210), c(0xFBF9F4), c(0xB4ADA2), c(0xFF6A5C), c(0xB81F18), c(0xFFFFFF), c(0xFFE1DD))
        val GraphiteOrange = IndexTones(c(0xEDEEEA), c(0x141516), c(0x55585C), c(0xC2410C), c(0xFF6A1A), c(0x141516), c(0x3A1A08))
        val FieldGreen = IndexTones(c(0x0E1A14), c(0xFFFFFF), c(0xA9B8AF), c(0x4CC98D), c(0x0E1A14), c(0xFFFFFF), c(0x8FE0B5))

        val byId: Map<String, IndexTones> = mapOf(
            "index" to SignalBlue, "index_newsprint" to NewsprintRed, "index_graphite" to GraphiteOrange, "index_field" to FieldGreen,
        )

        /** The tones of a palette id; Signal Blue's when the id is not an Index palette (a preview, a theme being left). */
        fun of(id: String?): IndexTones = byId[id] ?: SignalBlue
    }
}

/** True while the owner's theme is Index. Every Index branch in a shared control is guarded by this, so no other theme changes. */
@Composable
@androidx.compose.runtime.ReadOnlyComposable
fun isIndex(): Boolean = LocalPalette.current.layout == Layout.Index

/** The tones of the owner's chosen palette: the theme palette when the screen is drawn over an artwork tint, as the mini player is. */
@Composable
fun indexTones(): IndexTones = IndexTones.of((LocalThemePalette.current ?: LocalPalette.current).id)

/**
 * Index's text styles (docs/INDEX_THEME.md 5.3). The faces come from the owner's font pair, so another pair chosen in Appearance keeps Index's layout (D4):
 * heads and numerals use the pair's title and numeral faces, text its body face and the data keys its mono. Sizes and tracking are the spec's.
 */
object IndexType {
    @Composable private fun head(size: Float, line: Float, tracking: Float, features: String? = null): TextStyle {
        val f = LocalFontPair.current
        return TextStyle(fontFamily = f.title, fontWeight = f.titleWeight, fontSize = size.sp, lineHeight = line.sp, letterSpacing = tracking.em, fontFeatureSettings = features)
    }

    @Composable private fun numeralFace(size: Float, line: Float, tracking: Float, features: String? = null): TextStyle {
        val f = LocalFontPair.current
        return TextStyle(fontFamily = f.numeral, fontWeight = f.numeralWeight, fontSize = size.sp, lineHeight = line.sp, letterSpacing = tracking.em, fontFeatureSettings = features)
    }

    @Composable private fun body(weight: Int, size: Float, line: Float): TextStyle =
        TextStyle(fontFamily = LocalFontPair.current.body, fontWeight = FontWeight(weight), fontSize = size.sp, lineHeight = line.sp)

    @Composable private fun mono(weight: Int, size: Float, line: Float, tracking: Float): TextStyle =
        TextStyle(fontFamily = LocalFontPair.current.mono, fontWeight = FontWeight(weight), fontSize = size.sp, lineHeight = line.sp, letterSpacing = tracking.em)

    @Composable fun wordmark() = head(22f, 24f, -0.035f)
    @Composable fun display() = head(52f, 44f, -0.035f)
    @Composable fun pageTitle() = head(46f, 42f, -0.035f)
    @Composable fun leadTitle() = head(34f, 31f, -0.035f)
    @Composable fun index() = numeralFace(36f, 36f, -0.02f)
    @Composable fun section() = head(24f, 24f, -0.035f)
    @Composable fun numeral() = numeralFace(92f, 72f, -0.04f)
    @Composable fun trackNumber() = numeralFace(20f, 24f, -0.02f)
    @Composable fun time() = numeralFace(20f, 24f, -0.02f, features = "tnum")
    @Composable fun rowTitle() = body(600, 15f, 20f)
    @Composable fun body() = body(400, 14f, 21f)
    @Composable fun dataValue() = body(500, 12.5f, 18f)
    @Composable fun button() = body(600, 14f, 14f)
    @Composable fun buttonSmall() = body(600, 13f, 14f)
    @Composable fun field() = body(600, 17f, 22f)

    /** Mono capitals: eyebrows, data keys, meta lines, tabs and links. Callers upper-case the text. */
    @Composable fun label() = mono(500, 10.5f, 14f, 0.06f)
    @Composable fun navLabel() = mono(500, 9.5f, 12f, 0.07f)
    @Composable fun count() = mono(600, 13f, 13f, 0f)
}

// ---------------------------------------------------------------- rules and text

/** A rule across the page: 1dp `edge` between rows (the default), or the heavy 2dp `text` rule that opens a section. */
@Composable
fun IndexRule(modifier: Modifier = Modifier, heavy: Boolean = false) {
    val p = LocalPalette.current
    Box(modifier.fillMaxWidth().height((if (heavy) IndexRules.RULE_HEAVY else IndexRules.RULE_LIGHT).dp).background(if (heavy) p.text else p.edge))
}

/** A mono data word or meta line (capitals). [color] defaults to `textMuted`. */
@Composable
fun IndexLabel(text: String, modifier: Modifier = Modifier, color: Color = LocalPalette.current.textMuted, maxLines: Int = 1) {
    Text(text.uppercase(), style = IndexType.label(), color = color, maxLines = maxLines, overflow = TextOverflow.Ellipsis, modifier = modifier)
}

/** A state word: mono capitals. "In library" is `ok`, "Try again" is `chartRedText`; everything else defaults to `textMuted`. Never a coloured dot alone. */
@Composable
fun IndexState(text: String, modifier: Modifier = Modifier, color: Color = LocalPalette.current.textMuted) = IndexLabel(text, modifier, color)

/** A superscript count beside a heading ("Picks¹²"): mono 600 13 in `accent`. */
@Composable
fun IndexCount(text: String, modifier: Modifier = Modifier) {
    Text(text, style = IndexType.count(), color = LocalPalette.current.accent, modifier = modifier.padding(start = 4.dp))
}

/**
 * A section head: 28dp above, the 2dp `text` rule, 10dp, the Section title with a mono meta word, and a mono `accent` link pushed right.
 * (The rule draws left to right on arrival in step I2, motion #6.)
 */
@Composable
fun IndexSectionHead(title: String, modifier: Modifier = Modifier, meta: String? = null, link: String? = null, onLink: (() -> Unit)? = null, first: Boolean = false) {
    val p = LocalPalette.current
    Column(modifier.fillMaxWidth().padding(top = if (first) 0.dp else 28.dp, start = IndexRules.GUTTER.dp, end = IndexRules.GUTTER.dp)) {
        IndexRule(heavy = true)
        Row(Modifier.fillMaxWidth().padding(top = 10.dp, bottom = 6.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.Bottom) {
            Text(title, style = IndexType.section(), color = p.text, maxLines = 1)
            if (meta != null) IndexLabel(meta, Modifier.padding(bottom = 2.dp))
            Box(Modifier.weight(1f))
            if (link != null) {
                Text(
                    "${link.uppercase()} →", style = IndexType.label(), color = p.accent, maxLines = 1,
                    modifier = Modifier.heightIn(min = 24.dp).then(if (onLink != null) Modifier.clickable(role = Role.Button, onClick = onLink) else Modifier),
                )
            }
        }
    }
}

/**
 * A page head: the Display title with an `accent` count superscript, and [trailing] (the source switch) right-aligned on the title's baseline, then the 2dp
 * `text` rule 12dp below. 14dp above, 16dp gutters (index.css `.hd` and `.rule`).
 */
@Composable
fun IndexPageHead(title: String, modifier: Modifier = Modifier, count: String? = null, trailing: (@Composable () -> Unit)? = null) {
    val p = LocalPalette.current
    Column(modifier.fillMaxWidth()) {
        Row(Modifier.fillMaxWidth().padding(start = IndexRules.GUTTER.dp, end = IndexRules.GUTTER.dp, top = 14.dp), verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.SpaceBetween) {
            Row(verticalAlignment = Alignment.Top, modifier = Modifier.weight(1f, fill = false)) {
                Text(title, style = IndexType.display(), color = p.text, maxLines = 1)
                if (count != null) IndexCount(count)
            }
            trailing?.invoke()
        }
        IndexRule(Modifier.padding(horizontal = IndexRules.GUTTER.dp).padding(top = 12.dp), heavy = true)
    }
}

// ---------------------------------------------------------------- controls (section 7)

enum class IndexButtonKind { Primary, Ghost, Danger }

/**
 * Index's button: 44dp high (36 small), radius 3, 16dp padding (12 small). Primary is a `control` fill with an `onControl` label (Inter 600 14, icon 18);
 * Ghost has a 1.5dp inset `edge` outline and a `text` label; Danger fills with `chartRedText`. The touch area is 48dp high in every case.
 */
@Composable
fun IndexButton(
    label: String, onClick: () -> Unit, modifier: Modifier = Modifier, kind: IndexButtonKind = IndexButtonKind.Primary,
    icon: ImageVector? = null, small: Boolean = false, enabled: Boolean = true, labelColor: Color? = null,
) {
    IndexButtonBody(kind, onClick, modifier, enabled, small, labelColor) {
        if (icon != null) Icon(icon, null, Modifier.size(IndexRules.ICON_INLINE.dp))
        Text(label, maxLines = 1, overflow = TextOverflow.Ellipsis)
    }
}

/** The shared body of every Index button: also what the Material `Button`, `OutlinedButton` and `FilledTonalButton` wrappers draw. */
@Composable
fun IndexButtonBody(kind: IndexButtonKind, onClick: () -> Unit, modifier: Modifier, enabled: Boolean, small: Boolean = false, labelColor: Color? = null, content: @Composable RowScope.() -> Unit) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(IndexRules.BUTTON_RADIUS.dp)
    val fill = when (kind) { IndexButtonKind.Primary -> p.control; IndexButtonKind.Danger -> p.chartRedText; IndexButtonKind.Ghost -> Color.Transparent }
    // Danger's label: white on the day palettes' dark red (index.css), the page ink on Graphite's light coral so it keeps its contrast.
    val ink = labelColor ?: when (kind) {
        IndexButtonKind.Primary -> p.onControl
        IndexButtonKind.Danger -> if (p.light) Color.White else p.ink
        IndexButtonKind.Ghost -> p.text
    }
    val h = if (small) IndexRules.BUTTON_SMALL_HEIGHT else IndexRules.BUTTON_HEIGHT
    // The caller's modifier goes on the drawn body, so a full-width or weighted button fills its slot. The drawn height stays 44 (36 small); the touch area around it is 48dp high.
    Row(
        modifier.minimumInteractiveComponentSize().heightIn(min = h.dp).clip(shape).background(fill)
            .then(if (kind == IndexButtonKind.Ghost) Modifier.border(1.5.dp, p.edge, shape) else Modifier)
            .clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .padding(horizontal = if (small) 12.dp else 16.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp, Alignment.CenterHorizontally), verticalAlignment = Alignment.CenterVertically,
    ) {
        CompositionLocalProvider(androidx.compose.material3.LocalContentColor provides (if (enabled) ink else ink.copy(alpha = 0.38f))) {
            androidx.compose.material3.ProvideTextStyle(if (small) IndexType.buttonSmall() else IndexType.button()) { content() }
        }
    }
}

/** An icon button: a 44dp square with a 22dp glyph in `text` and no background, inside a 48dp touch area. */
@Composable
fun IndexIconButton(icon: ImageVector, label: String, onClick: () -> Unit, modifier: Modifier = Modifier, tint: Color = LocalPalette.current.text, size: Dp = IndexRules.ICON.dp) {
    Box(
        modifier.size(IndexRules.TOUCH_MIN.dp).clickable(role = Role.Button, onClick = onClick).semantics { contentDescription = label },
        contentAlignment = Alignment.Center,
    ) { Icon(icon, null, tint = tint, modifier = Modifier.size(size)) }
}

/** A tag: mono 600 10 capitals, `ink` letters on a square `text` fill (FLAC 16/44.1), 5 by 7 padding. [accent] fills it with `accent` (On air). */
@Composable
fun IndexTag(text: String, modifier: Modifier = Modifier, accent: Boolean = false) {
    val p = LocalPalette.current
    Text(
        text.uppercase(), style = IndexType.label().copy(fontWeight = FontWeight.SemiBold, fontSize = 10.sp, lineHeight = 10.sp), color = if (accent) p.onAccent else p.ink, maxLines = 1,
        modifier = modifier.background(if (accent) p.accent else p.text).padding(horizontal = 7.dp, vertical = 5.dp),
    )
}

/** The downloads badge: a square `accent` box at least 15dp across, `onAccent` mono 600 9.5. */
@Composable
fun IndexBadge(count: Int, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    Text(
        if (count > 99) "99+" else count.toString(), color = p.onAccent, maxLines = 1,
        style = IndexType.count().copy(fontSize = 9.5.sp, lineHeight = 15.sp),
        modifier = modifier.heightIn(min = 15.dp).widthIn(min = 15.dp).background(p.accent).padding(horizontal = 3.dp),
    )
}

/** Index's switch: a 44 by 24 square. Off: an `edge` track with a `surface` knob at the left. On: a `control` track with an `onControl` knob at the right. */
@Composable
fun IndexSwitch(checked: Boolean, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    Box(modifier.size(width = IndexRules.SWITCH_WIDTH.dp, height = IndexRules.SWITCH_HEIGHT.dp).background(if (checked) p.control else p.edge)) {
        Box(Modifier.align(Alignment.CenterStart).offset(x = if (checked) 23.dp else 3.dp).size(18.dp).background(if (checked) p.onControl else p.surface))
    }
}

/** A thin progress bar: a 6dp square `edge` track with the played part in `accent` (index.css `.seek`). */
@Composable
fun IndexProgress(fraction: Float, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    Box(modifier.fillMaxWidth().height(IndexRules.SEEK.dp).background(p.edge)) {
        Box(Modifier.fillMaxWidth(fraction.coerceIn(0f, 1f)).height(IndexRules.SEEK.dp).background(p.accent))
    }
}

/** The download tracker: four 4dp segments 4dp apart (`text` reached, `edge` ahead, `chartRedText` on the failed step). [failedAt] is a 0-based step or -1. */
@Composable
fun IndexTracker(reached: Int, modifier: Modifier = Modifier, failedAt: Int = -1, steps: Int = 4) {
    val p = LocalPalette.current
    Row(modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        for (i in 0 until steps) {
            val c = if (i == failedAt) p.chartRedText else if (i < reached) p.text else p.edge
            Box(Modifier.weight(1f).height(4.dp).background(c))
        }
    }
}

// ---------------------------------------------------------------- source switch and tabs (motion #4)

/** One word's place inside its row: its left edge and its width, in px. */
private data class WordSpan(val x: Int, val width: Int)

/**
 * The shared body of the source switch and the tabs (docs/INDEX_THEME.md 8.2 #4): mono words, the chosen one in `text`, and one 3dp `accent` bar under it that
 * moves and resizes to the chosen word over 260ms. Each word is measured, then the bar's x and width are animated. A word's cell is 48dp high for the touch
 * rule; [visibleHeight] of it, at the bottom, is what the mockup draws, so the bar sits on the visible bottom edge.
 */
@Composable
private fun IndexWords(
    labels: List<String>, selectedIndex: Int, onSelect: (Int) -> Unit, modifier: Modifier, gap: Dp, cellPadding: Dp, visibleHeight: Dp, semiboldWhenSelected: Boolean,
) {
    val p = LocalPalette.current
    val reduced = rememberReducedMotion()
    val density = LocalDensity.current
    var spans by remember(labels.size) { mutableStateOf(List(labels.size) { WordSpan(0, 0) }) }
    val span = spans.getOrNull(selectedIndex) ?: WordSpan(0, 0)
    val x by animateDpAsState(with(density) { span.x.toDp() }, IndexMotion.firm<Dp>(IndexMotion.SOURCE_BAR_MS, reduced), label = "indexSourceBarX")
    val w by animateDpAsState(with(density) { span.width.toDp() }, IndexMotion.firm<Dp>(IndexMotion.SOURCE_BAR_MS, reduced), label = "indexSourceBarW")
    Box(modifier.height(IndexRules.TOUCH_MIN.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(gap)) {
            labels.forEachIndexed { i, label ->
                val on = i == selectedIndex
                Box(
                    Modifier.height(IndexRules.TOUCH_MIN.dp)
                        // Written only when the word has moved or resized: this fires on every scroll frame of a page the tabs sit in.
                        .onGloballyPositioned { c ->
                            val now = WordSpan(c.positionInParent().x.toInt(), c.size.width)
                            if (i < spans.size && spans[i] != now) spans = spans.toMutableList().also { l -> l[i] = now }
                        }
                        .clickable(role = Role.Tab, onClick = { onSelect(i) }).semantics { selected = on }.padding(horizontal = cellPadding),
                    contentAlignment = Alignment.BottomCenter,
                ) {
                    Box(Modifier.height(visibleHeight), contentAlignment = Alignment.Center) {
                        Text(
                            label.uppercase(), maxLines = 1, color = if (on) p.text else p.textMuted,
                            style = IndexType.label().let { if (on && semiboldWhenSelected) it.copy(fontWeight = FontWeight.SemiBold) else it },
                        )
                    }
                }
            }
        }
        if (selectedIndex in labels.indices && span.width > 0) {
            Box(Modifier.align(Alignment.BottomStart).offset { IntOffset(with(density) { x.roundToPx() }, 0) }.width(w).height(IndexRules.SOURCE_BAR.dp).background(p.accent))
        }
    }
}

/**
 * The source switch (PICKS · NEW · PLAYED): right-aligned mono words, 7dp of padding each side, 34dp high, with the moving 3dp `accent` bar under the chosen
 * word. Never chips or pills.
 */
@Composable
fun IndexSourceSwitch(labels: List<String>, selectedIndex: Int, onSelect: (Int) -> Unit, modifier: Modifier = Modifier) {
    IndexWords(labels, selectedIndex, onSelect, modifier, gap = 0.dp, cellPadding = 7.dp, visibleHeight = IndexRules.SOURCE_HEIGHT.dp, semiboldWhenSelected = false)
}

/** In-page tabs (lenses, library views, path kinds, presets): mono words 16dp apart, 40dp high, a 1dp `edge` baseline, the moving 3dp `accent` bar and the chosen word in 600. */
@Composable
fun IndexTabs(labels: List<String>, selectedIndex: Int, onSelect: (Int) -> Unit, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    Column(modifier.fillMaxWidth()) {
        Box(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal = IndexRules.GUTTER.dp)) {
            IndexWords(labels, selectedIndex, onSelect, Modifier, gap = 16.dp, cellPadding = 0.dp, visibleHeight = IndexRules.TABS_HEIGHT.dp, semiboldWhenSelected = true)
        }
        Box(Modifier.fillMaxWidth().height(1.dp).background(p.edge))
    }
}

// ---------------------------------------------------------------- rows

/**
 * A row (section 7): at least 64dp, a 12dp gap, a 1dp `edge` rule under it. [number] is the mono `accent` index ("01") in a 26dp column, [lead] a 48dp square
 * cover, then the title over a mono meta line, and [trail] (a state word, a button, a count). Each part may be left out and the row closes up.
 */
@Composable
fun IndexRow(
    title: String, modifier: Modifier = Modifier, meta: String = "", number: String? = null, onClick: (() -> Unit)? = null, divider: Boolean = true,
    minHeight: Dp = IndexRules.ROW_MIN.dp, lead: (@Composable () -> Unit)? = null, trail: (@Composable () -> Unit)? = null, titleColor: Color? = null,
) {
    val p = LocalPalette.current
    Column(modifier) {
        Row(
            Modifier.fillMaxWidth().heightIn(min = minHeight)
                .then(if (onClick != null) Modifier.clickable(role = Role.Button, onClick = onClick) else Modifier)
                .semantics(mergeDescendants = true) { contentDescription = if (meta.isEmpty()) title else "$title, $meta" },
            horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
        ) {
            if (number != null) Text(number, style = IndexType.label(), color = p.accent, maxLines = 1, modifier = Modifier.width(26.dp))
            lead?.invoke()
            Column(Modifier.weight(1f)) {
                Text(title, color = titleColor ?: p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = IndexType.rowTitle())
                if (meta.isNotEmpty()) IndexLabel(meta)
            }
            trail?.invoke()
        }
        if (divider) IndexRule()
    }
}
