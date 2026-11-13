package app.discair.ui.common

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.selection.selectable
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material3.BottomSheetDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import app.discair.model.TrailEntry
import app.discair.model.TrailGroup
import app.discair.model.TrailLink
import app.discair.model.TrailStep
import app.discair.model.entries
import app.discair.ui.artist.Eyebrow
import app.discair.ui.theme.Ink
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.MotionRole
import app.discair.ui.theme.MotionRules
import app.discair.ui.theme.MotionTokens
import app.discair.ui.theme.brutalShadow
import app.discair.ui.theme.currentMotionFamily
import app.discair.ui.theme.pillShape
import app.discair.ui.theme.rememberReducedMotion
import app.discair.ui.theme.themeBorder
import app.discair.ui.theme.themeShape
import app.discair.ui.theme.toTween

/*
 * The pieces of the Trail layout of the Paths sheets (docs/pathsredesign.md, sections 3 and 9), shared by the artist and
 * the album sheet. Sizes are those of docs/design/paths-trail/trail.css, where 1 CSS px is 1 dp. Nothing here reads a
 * request or a model: the sheets give each piece its words and its picture.
 *
 * Place [TrailHeader], [TrailTabs], the description and the trail in one column. The column carries the sheet's 16dp
 * side padding; [TrailTabs] draws its rule edge to edge, so it goes outside that padding.
 */

/** Sizes of the trail, in dp. */
object TrailSizes {
    /** Header picture; closed step picture; opened step picture. */
    val HeaderPicture = 40.dp
    val StepPicture = 48.dp
    val OpenPicture = 72.dp
    /** The small chevron of decision D3. */
    val Chevron = 18.dp
    /** Space the trail is indented, and where its line sits (the line's centre, from the trail's own left edge). */
    val Indent = 24.dp
    val LineCentre = 8.dp
    val LineWidth = 2.dp
    /** Where the elbow meets a closed and an opened step, measured from the step's top edge. */
    val ClosedElbow = 31.dp
    val OpenElbow = 47.dp
    /** Gaps above a step, a first link and a later link. */
    val StepGap = 8.dp
    val LinkGap = 12.dp
}

/** The colour behind the sheet, for the ring round a link's dot: the sheet's own container, which is not always `Ink.Surface`. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun trailGround(): Color {
    val p = LocalPalette.current
    return if (isFlow() || p.brutal) p.surface else BottomSheetDefaults.ContainerColor
}

// ---------------------------------------------------------------- header and tabs

/** "Paths from" over the start's name, beside the start's [picture] (40dp: a square cover with 4dp corners, or a circular photo). */
@Composable
fun TrailHeader(name: String, picture: @Composable () -> Unit, modifier: Modifier = Modifier) {
    Row(
        modifier.fillMaxWidth().padding(bottom = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        picture()
        Column(Modifier.weight(1f).semantics(mergeDescendants = true) { heading() }) {
            Eyebrow("Paths from")
            Text(name, style = MaterialTheme.typography.titleLarge, maxLines = 2, overflow = TextOverflow.Ellipsis)
        }
    }
}

/**
 * The tabs: words in a scrolling row, a 3dp mark under the chosen one and a 1dp rule under the whole row, edge to edge.
 * The tabs keep the order they are given.
 */
@Composable
fun TrailTabs(labels: List<String>, selected: Int, onSelect: (Int) -> Unit, modifier: Modifier = Modifier) {
    val state = rememberLazyListState()
    // A tab restored off screen (Back from an album) is brought into view; one already visible is left where it is.
    LaunchedEffect(selected) {
        if (state.layoutInfo.visibleItemsInfo.none { it.index == selected }) state.scrollToItem(selected)
    }
    Column(modifier.fillMaxWidth()) {
        LazyRow(state = state, contentPadding = PaddingValues(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(20.dp)) {
            itemsIndexed(labels) { index, label -> TrailTab(label, index == selected) { onSelect(index) } }
        }
        Box(Modifier.fillMaxWidth().height(1.dp).background(Ink.Edge))
    }
}

@Composable
private fun TrailTab(label: String, selected: Boolean, onClick: () -> Unit) {
    val mark = Ink.AccentText
    Box(
        Modifier.heightIn(min = Target)
            .selectable(selected = selected, role = Role.Tab, onClick = onClick)
            .drawBehind { if (selected) drawRect(mark, Offset(0f, size.height - 3.dp.toPx()), Size(size.width, 3.dp.toPx())) },
        contentAlignment = Alignment.Center,
    ) {
        Text(
            label, style = MaterialTheme.typography.labelLarge,
            fontWeight = if (selected) FontWeight.Bold else null,
            color = if (selected) Ink.Text else Ink.TextMuted,
            maxLines = 1,
        )
    }
}

// ---------------------------------------------------------------- the trail

/**
 * One item of the trail (a link or a step) with its piece of the line: a 2dp line down the left that each item draws up
 * through the gap above it, and, for a step, the elbow that joins the line to the row at [elbow] dp from the step's top.
 * The line starts at the first link's dot and ends at the last step's elbow. A link passes [dot] to put its 10dp dot on the
 * line, ringed in the sheet's own colour so the line stops short of it. Resizing, as a step opens, follows the app's
 * standard duration, and happens at once with reduced motion.
 *
 * [topGap] is the space above the content, inside the item: [TrailSizes.StepGap] for a step, [TrailSizes.LinkGap] for a link
 * that is not first, zero for the first link.
 */
@Composable
fun TrailItem(
    first: Boolean, last: Boolean, topGap: Dp, modifier: Modifier = Modifier, elbow: Dp? = null, dot: Boolean = false,
    content: @Composable () -> Unit,
) {
    val edge = Ink.Edge
    val accent = Ink.Accent
    val ground = trailGround()
    val outline = LocalPalette.current.shape?.outline ?: 0f // a Brutal theme's accent is pastel and needs its outline to be seen
    val resize = MotionRules.timing(MotionTokens.BASE_MS, MotionRole.Move, currentMotionFamily(), rememberReducedMotion())
    Box(
        modifier.fillMaxWidth()
            .animateContentSize(resize.toTween<IntSize>())
            .drawBehind {
                val gap = topGap.toPx()
                val line = TrailSizes.LineWidth.toPx()
                val centre = TrailSizes.LineCentre.toPx()
                val dotY = gap + (size.height - gap) / 2f
                val top = if (first) (if (dot) dotY else gap) else 0f
                val bottom = if (last && elbow != null) gap + elbow.toPx() + 1.dp.toPx() else size.height
                if (bottom > top) drawRect(edge, Offset(centre - line / 2f, top), Size(line, bottom - top))
                if (elbow != null) drawRect(edge, Offset(9.dp.toPx(), gap + elbow.toPx()), Size(11.dp.toPx(), line))
                if (dot) {
                    val at = Offset(centre, dotY)
                    val r = 5.dp.toPx()
                    val o = outline.dp.toPx()
                    drawCircle(ground, r + 3.dp.toPx() + o, at)
                    if (o > 0f) drawCircle(edge, r + o, at)
                    drawCircle(accent, r, at)
                }
            }
            .padding(start = TrailSizes.Indent, top = topGap),
    ) { content() }
}

/** A link: what connects the steps under it. A pill, not a button; a heading for TalkBack, read as "name, kind". */
@Composable
fun TrailLinkPill(link: TrailLink, modifier: Modifier = Modifier) {
    val text = buildAnnotatedString {
        val name = link.name
        if (name != null) {
            withStyle(SpanStyle(fontWeight = FontWeight.SemiBold)) { append(name) }
            withStyle(SpanStyle(fontWeight = FontWeight.Normal)) { append(" · ${link.kind}") }
        } else {
            withStyle(SpanStyle(fontWeight = FontWeight.SemiBold)) { append(link.text) }
        }
    }
    Text(
        text, style = MaterialTheme.typography.labelLarge, color = Ink.Text, // Ink.Text: muted text fails contrast on AccentDim in Night
        modifier = modifier.background(Ink.AccentDim, pillShape()).padding(horizontal = 12.dp, vertical = 4.dp)
            .semantics(mergeDescendants = true) { heading(); contentDescription = link.spoken },
    )
}

/**
 * The trail of a sheet: each group's link, then its steps ([step] draws one, and is told whether it is the open one). [openIndex]
 * is the saved index into the server's list, or -1. When a step opens the list scrolls so it is in view (at once with reduced
 * motion). [notes] go under the trail.
 */
@Composable
fun <T> TrailList(
    groups: List<TrailGroup<T>>, openIndex: Int, state: LazyListState, notes: List<String>, modifier: Modifier = Modifier,
    step: @Composable (TrailStep<T>, Boolean) -> Unit,
) {
    val entries = remember(groups) { groups.entries() }
    val reduced = rememberReducedMotion()
    LaunchedEffect(openIndex, entries) {
        val at = entries.indexOfFirst { it is TrailEntry.Step && it.step.index == openIndex }
        if (at >= 0) {
            val visible = state.layoutInfo.visibleItemsInfo.firstOrNull { it.index == at }
            val fits = visible != null && visible.offset >= 0 && visible.offset + visible.size <= state.layoutInfo.viewportEndOffset
            if (!fits) if (reduced) state.scrollToItem(at) else state.animateScrollToItem(at)
        }
    }
    LazyColumn(modifier.fillMaxSize(), state = state, contentPadding = PaddingValues(start = 16.dp, end = 16.dp, bottom = 32.dp)) {
        itemsIndexed(entries, key = { n, it -> if (it is TrailEntry.Step) "step:${it.step.index}" else "link:$n" }) { _, entry ->
            when (entry) {
                is TrailEntry.Link -> TrailLinkItem(entry.link, entry.first)
                is TrailEntry.Step -> {
                    val open = entry.step.index == openIndex
                    TrailStepItem(entry.last, open) { step(entry.step, open) }
                }
            }
        }
        notes.forEach { note ->
            item {
                Text(note, style = MaterialTheme.typography.bodySmall, color = Ink.TextMuted, modifier = Modifier.padding(top = 16.dp))
            }
        }
    }
}

/** A link on the trail, with its dot. [first] is the first item of the trail, which has no gap above it. */
@Composable
fun TrailLinkItem(link: TrailLink, first: Boolean, modifier: Modifier = Modifier) {
    TrailItem(first = first, last = false, topGap = if (first) 0.dp else TrailSizes.LinkGap, modifier = modifier, dot = true) {
        Box(Modifier.fillMaxWidth()) { TrailLinkPill(link) }
    }
}

/**
 * A closed step as a trail item. [content] is a [TrailStepRow]. [last] is the last step of the whole trail; it ends the line at
 * its elbow. The elbow sits lower on an opened step, whose header is taller.
 */
@Composable
fun TrailStepItem(last: Boolean, open: Boolean, modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    TrailItem(
        first = false, last = last, topGap = TrailSizes.StepGap, modifier = modifier,
        elbow = if (open) TrailSizes.OpenElbow else TrailSizes.ClosedElbow, content = content,
    )
}

/**
 * A closed step: [picture] (48dp), the name over one line, and a small chevron pointing down. The whole row is one button that
 * opens the step in place. A long press (also a TalkBack action) calls [onShowNextCover], when the step has one.
 */
@OptIn(ExperimentalFoundationApi::class)
@Composable
fun TrailStepRow(
    title: String, line: String, picture: @Composable () -> Unit, onOpen: () -> Unit,
    modifier: Modifier = Modifier, onShowNextCover: (() -> Unit)? = null,
) {
    Row(
        modifier.fillMaxWidth().heightIn(min = 64.dp)
            .combinedClickable(
                onClickLabel = "Open step", role = Role.Button, onClick = onOpen,
                onLongClickLabel = if (onShowNextCover != null) "Show next cover" else null, onLongClick = onShowNextCover,
            )
            .semantics { stateDescription = "Collapsed" }
            .padding(vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        picture()
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.titleMedium, maxLines = 2, overflow = TextOverflow.Ellipsis)
            if (line.isNotBlank()) Text(line, style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted, maxLines = 2, overflow = TextOverflow.Ellipsis)
        }
        Icon(Icons.Default.KeyboardArrowDown, contentDescription = null, tint = Ink.TextMuted, modifier = Modifier.size(TrailSizes.Chevron))
    }
}

/**
 * An opened step, in place: the app's panel on the raised ground (a Brutal theme gives it its outline, radius and hard shadow),
 * a header row with [picture] (72dp), the [title], the [lines] under it and a small chevron pointing up, then [body], today's
 * pane for the tab. Cards in the body sit on the sheet's ground, so they read against the raised panel.
 *
 * Tapping the header closes the step. When [onOpenTitle] is given (Sideman: the leader's page), the picture and name open that
 * instead and only the chevron closes the step.
 */
@OptIn(ExperimentalFoundationApi::class)
@Composable
fun TrailOpenStep(
    title: String, lines: List<String>, picture: @Composable () -> Unit, onClose: () -> Unit,
    modifier: Modifier = Modifier, onOpenTitle: (() -> Unit)? = null, body: @Composable ColumnScope.() -> Unit,
) {
    val shape = themeShape(12.dp)
    Column(
        modifier.fillMaxWidth().brutalShadow(shape).clip(shape).background(Ink.Raised)
            .border(themeBorder(BorderStroke(1.dp, Ink.Edge)), shape)
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        val identity: @Composable RowScope.() -> Unit = {
            picture()
            Column(Modifier.weight(1f)) {
                Text(title, style = MaterialTheme.typography.titleLarge, maxLines = 2, overflow = TextOverflow.Ellipsis)
                lines.filter { it.isNotBlank() }.forEach { Text(it, style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted) }
            }
        }
        if (onOpenTitle == null) {
            Row(
                Modifier.fillMaxWidth().heightIn(min = TrailSizes.OpenPicture)
                    .clickable(onClickLabel = "Close step", role = Role.Button, onClick = onClose)
                    .semantics { stateDescription = "Expanded" },
                horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
            ) {
                identity()
                Icon(Icons.Default.KeyboardArrowUp, contentDescription = null, tint = Ink.TextMuted, modifier = Modifier.size(TrailSizes.Chevron))
            }
        } else {
            Row(Modifier.fillMaxWidth().heightIn(min = TrailSizes.OpenPicture), verticalAlignment = Alignment.CenterVertically) {
                Row(
                    Modifier.weight(1f).clickable(onClickLabel = "Open page", role = Role.Button, onClick = onOpenTitle),
                    horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
                ) { identity() }
                Box(
                    Modifier.size(Target)
                        .clickable(onClickLabel = "Close step", role = Role.Button, onClick = onClose)
                        .semantics { stateDescription = "Expanded" },
                    contentAlignment = Alignment.Center,
                ) { Icon(Icons.Default.KeyboardArrowUp, contentDescription = null, tint = Ink.TextMuted, modifier = Modifier.size(TrailSizes.Chevron)) }
            }
        }
        body()
    }
}
