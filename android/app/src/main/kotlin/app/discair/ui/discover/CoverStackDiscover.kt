package app.discair.ui.discover

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
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
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.model.DiscoveryEntry
import app.discair.model.GetState
import app.discair.model.InsightCard
import app.discair.model.InsightNarrative
import app.discair.model.TasteEntry
import app.discair.ui.Opener
import app.discair.ui.common.CoverStackCover
import app.discair.ui.common.CoverStackRules
import app.discair.ui.common.CoverStackTabs
import app.discair.ui.common.CoverStackTitle
import app.discair.ui.common.LocalAcquisitions
import app.discair.ui.common.SaveState
import app.discair.ui.common.Target
import app.discair.ui.common.coverStackFrame
import app.discair.ui.common.rememberAlbumYear
import app.discair.ui.common.routeKey
import app.discair.ui.player.PlayerIcons
import app.discair.ui.theme.LocalFontPair
import app.discair.ui.theme.LocalPalette
import app.discair.model.DiscoveryList

/*
 * Soft Brut's (Layout.CoverStack) Discover. Mockup: soft-brut/discover, frames 1 to 3.
 * Only DiscoverScreen, DiscoverCard, InsightsPage and the taste card reach this, behind isCoverStack(); no other theme changes.
 */

/** Lists | Insights as one joined group, then the list names as outlined chips (the chips only while Lists is chosen). */
@Composable
internal fun CoverStackDiscoverHeader(list: DiscoveryList, onSelect: (DiscoveryList) -> Unit) {
    val lists = DiscoveryList.entries.filter { it != DiscoveryList.Insights }
    // Insights are the second tab; Lists remembers nothing of its own, so it opens the first list.
    CoverStackTitle("Discover", Modifier.padding(start = 16.dp, top = 16.dp, end = 16.dp), maxLines = 1)
    CoverStackTabs(
        listOf("Lists", "Insights"), if (list == DiscoveryList.Insights) 1 else 0,
        { if (it == 1) onSelect(DiscoveryList.Insights) else if (list == DiscoveryList.Insights) onSelect(lists.first()) },
        Modifier.padding(start = 16.dp, top = 12.dp, end = 19.dp, bottom = 4.dp).fillMaxWidth(),
    )
    if (list != DiscoveryList.Insights) Row(
        Modifier.horizontalScroll(rememberScrollState()).padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        lists.forEach { CoverStackChip(it.label, it == list) { onSelect(it) } }
    }
}

/** An outlined pill, 36dp drawn inside the 48dp touch target; selected is filled with the accent (mockup `.chip`). */
@Composable
internal fun CoverStackChip(label: String, selected: Boolean, onClick: () -> Unit) {
    val p = LocalPalette.current
    Box(
        Modifier.heightIn(min = Target).clickable(role = Role.RadioButton, onClick = onClick).semantics { this.selected = selected },
        contentAlignment = Alignment.Center,
    ) {
        Box(
            Modifier.height(36.dp).background(if (selected) p.accent else p.surface, CircleShape).border(CoverStackRules.outline(p).dp, p.edgeStrong, CircleShape).padding(horizontal = 13.dp),
            contentAlignment = Alignment.Center,
        ) { Text(label, color = if (selected) p.onAccent else p.text, maxLines = 1, style = MaterialTheme.typography.labelLarge.copy(fontSize = 13.sp, fontWeight = FontWeight.SemiBold)) }
    }
}

/** A 36dp outlined button with a hard shadow inside a 48dp touch target (mockup `.dc .acts .btn`). */
@Composable
internal fun SmallButton(label: String?, icon: ImageVector?, filled: Boolean, description: String, modifier: Modifier = Modifier, state: String? = null, enabled: Boolean = true, onClick: () -> Unit) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(CoverStackRules.radius(p).dp)
    Box(
        modifier.heightIn(min = Target).clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .semantics { contentDescription = description; if (state != null) stateDescription = state },
        contentAlignment = Alignment.Center,
    ) {
        Row(
            Modifier.height(36.dp).then(if (label == null) Modifier.width(36.dp) else Modifier.fillMaxWidth().padding(end = CoverStackRules.shadow(p).dp))
                .coverStackFrame(shape, p, if (filled) p.accent else p.surface).padding(horizontal = if (label == null) 0.dp else 8.dp),
            horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically,
        ) {
            if (icon != null) Icon(icon, contentDescription = null, tint = p.text, modifier = Modifier.size(18.dp))
            if (icon != null && label != null) Spacer(Modifier.width(5.dp))
            if (label != null) Text(label, color = p.text, maxLines = 1, style = MaterialTheme.typography.labelLarge.copy(fontSize = 13.sp, fontWeight = FontWeight.Bold))
        }
    }
}

/**
 * The Discover card: the outlined cover on top, then title, artist and year, the "Similar to:" line when the server sent one, and
 * Get, Save and a three-dot menu in one row (Not this album, Not this artist). Whether the album is owned is said in words.
 */
@Composable
internal fun CoverStackDiscoverCard(
    entry: DiscoveryEntry, open: Opener, saveState: SaveState, onSave: () -> Unit, onDismiss: (artistToo: Boolean) -> Unit, modifier: Modifier = Modifier,
) {
    val p = LocalPalette.current
    val item = entry.item
    val artist = item.artistName
    val hub = LocalAcquisitions.current
    val get = hub.getState(artist, item.album)
    val year = rememberAlbumYear(artist, item.album, item.year)
    val openAlbum = { open.album(routeKey(artist, item.album), artist, item.album, null, item.year) }
    var menu by remember { mutableStateOf(false) }
    Column(modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        CoverStackCover(artist, item.album, null, Modifier.fillMaxWidth().clickable(role = Role.Button, onClick = openAlbum), radius = CoverStackRules.radius(p).toInt())
        Text(
            item.album, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis,
            style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold, fontSize = 14.sp),
            modifier = Modifier.clickable(role = Role.Button, onClick = openAlbum),
        )
        Text(
            listOfNotNull(artist.ifBlank { null }, year?.toString()).joinToString(" · ").ifEmpty { " " }, color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis,
            style = MaterialTheme.typography.bodySmall, modifier = Modifier.clickable(role = Role.Button) { open.artist(artist, null, null, null) },
        )
        val similar = item.similarTo.joinToString(", ")
        Text(
            if (similar.isEmpty()) " " else "Similar to: $similar", color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis,
            style = MaterialTheme.typography.bodySmall,
        )
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(0.dp), verticalAlignment = Alignment.CenterVertically) {
            if (item.acquired) SmallButton("In library", Icons.Default.Check, false, "${item.album} is in your library", Modifier.weight(1f), enabled = false) {}
            else SmallButton(
                when (get) { GetState.Pending -> "Requesting"; is GetState.Requested -> "Requested"; is GetState.Failed -> "Retry"; else -> "Get" },
                when (get) { is GetState.Requested -> Icons.Default.Check; else -> PlayerIcons.Cloud },
                get is GetState.Idle || get is GetState.Failed, "Get album ${item.album}", Modifier.weight(1f),
                state = when (get) { GetState.Idle -> "Not requested"; GetState.Pending -> "Requesting"; is GetState.Requested -> "Requested. Follow it under Downloads"; is GetState.Failed -> "Could not request. Select to try again" },
                enabled = get is GetState.Idle || get is GetState.Failed,
            ) { hub.getAlbum(artist, item.album, entry.raw) }
            val saved = saveState == SaveState.Saved
            SmallButton(
                if (saved) "Saved" else "Save", if (saved) Icons.Default.Favorite else null, false, (if (saved) "Remove ${item.album} from saved" else "Save ${item.album}"),
                Modifier.weight(1f), enabled = saveState != SaveState.Pending, onClick = onSave,
            )
            Box {
                SmallButton(null, Icons.Default.MoreVert, false, "Options for ${item.album}") { menu = true }
                DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                    DropdownMenuItem(text = { Text("Not this album") }, onClick = { menu = false; onDismiss(false) })
                    DropdownMenuItem(text = { Text("Not this artist") }, onClick = { menu = false; onDismiss(true) })
                }
            }
        }
    }
}

// ----- Insights ---------------------------------------------------------------------------------------------------------

/** A lens heading: its name in the eyebrow style, and "off" or the card count at the right, so an off lens stays visible. */
@Composable
internal fun CoverStackLensHeading(name: String, count: String) {
    val p = LocalPalette.current
    val eyebrow = MaterialTheme.typography.labelSmall.copy(fontFamily = LocalFontPair.current.mono, fontWeight = FontWeight.Medium, fontSize = 11.sp, lineHeight = 16.sp, letterSpacing = 0.88.sp)
    Row(Modifier.fillMaxWidth().padding(top = 4.dp), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(name.uppercase(), color = p.textMuted, style = eyebrow)
        Text(count.uppercase(), color = p.textMuted, style = eyebrow, modifier = Modifier.semantics { contentDescription = "$name: $count" })
    }
}

/** The outlined card every Cover Stack Insights block sits in (mockup `.card`, padding 12). */
@Composable
internal fun CoverStackCardBox(modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    val p = LocalPalette.current
    Column(
        modifier.fillMaxWidth().coverStackFrame(RoundedCornerShape(CoverStackRules.radius(p).dp), p).padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) { content() }
}

/** An Insights card: tag, title, subject, the server's body and Open album, Why?, Dismiss (mockup frame 2, the Anniversary card). */
@Composable
internal fun CoverStackInsightCard(card: InsightCard, open: Opener, onDismiss: (InsightCard) -> Unit) {
    val p = LocalPalette.current
    var why by remember(card.id) { mutableStateOf(false) }
    val artist = card.subject.artist
    val title = card.subject.title
    CoverStackCardBox {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.Top) {
            if (artist != null && title != null) CoverStackCover(artist, title, null, Modifier.size(88.dp))
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                val tag = RoundedCornerShape(6.dp)
                Text(
                    lensName(card.kind).uppercase(), color = p.text, maxLines = 1,
                    style = MaterialTheme.typography.labelSmall.copy(fontFamily = LocalFontPair.current.mono, fontWeight = FontWeight.Medium, fontSize = 10.sp, lineHeight = 14.sp, letterSpacing = 0.7.sp),
                    modifier = Modifier.background(if (card.kind == "anniversary") p.accent4 else p.accent3, tag).border(CoverStackRules.outline(p).dp, p.edgeStrong, tag).padding(horizontal = 7.dp, vertical = 2.dp),
                )
                Text(card.title, color = p.text, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 14.sp))
                card.subject.artist?.let { Text(it, color = p.textMuted, style = MaterialTheme.typography.bodySmall) }
                if (card.body.isNotEmpty()) Text(card.body, color = p.textMuted, style = MaterialTheme.typography.bodySmall)
            }
        }
        for (run in card.missingRuns) {
            val span = if (run.firstPosition == run.lastPosition) "${run.firstPosition}" else "${run.firstPosition} to ${run.lastPosition}"
            Text("Missing $span" + if (run.labels.isEmpty()) "" else ": " + run.labels.joinToString(", "), color = p.textMuted, style = MaterialTheme.typography.labelMedium)
        }
        if (why) Text(InsightNarrative.why(card), color = p.textMuted, style = MaterialTheme.typography.bodySmall)
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            if (artist != null && title != null) SmallButtonWide("Open album", true, Modifier.weight(1f)) { open.album(routeKey(artist, title), artist, title, null, card.subject.year) }
            SmallButtonWide(if (why) "Hide why" else "Why?", false, Modifier.then(if (artist != null && title != null) Modifier else Modifier.weight(1f))) { why = !why }
            if (card.dismissible) SmallButtonWide("Dismiss", false, Modifier.semantics { contentDescription = "Dismiss ${card.title}" }) { onDismiss(card) }
        }
    }
}

/** A 44dp action button of the Insights cards (mockup `.btn`): outlined, hard shadow, the primary one filled. */
@Composable
private fun SmallButtonWide(label: String, filled: Boolean, modifier: Modifier = Modifier, onClick: () -> Unit) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(CoverStackRules.radius(p).dp)
    Box(modifier.heightIn(min = Target).padding(end = CoverStackRules.shadow(p).dp).clickable(role = Role.Button, onClick = onClick), contentAlignment = Alignment.Center) {
        Box(
            Modifier.height(44.dp).widthIn(min = 64.dp).then(if (filled) Modifier.fillMaxWidth() else Modifier).coverStackFrame(shape, p, if (filled) p.accent else p.surface).padding(horizontal = 14.dp),
            contentAlignment = Alignment.Center,
        ) { Text(label, color = p.text, maxLines = 1, textAlign = TextAlign.Center, style = MaterialTheme.typography.labelLarge.copy(fontSize = 14.sp, fontWeight = FontWeight.Bold)) }
    }
}

/**
 * Ranked bars (mockup `.bars`): label, an outlined bar, the percentage. The first is filled with the accent and the longest bar is 85% of the track,
 * the others in proportion to it. [sketch] draws every bar unfilled: a low-sample window is a sketch, not a finding.
 */
@Composable
internal fun CoverStackBars(entries: List<TasteEntry>, sketch: Boolean = false, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    val top = entries.maxOfOrNull { it.share }?.takeIf { it > 0 } ?: 1.0
    Column(modifier, verticalArrangement = Arrangement.spacedBy(10.dp)) {
        for ((i, e) in entries.withIndex()) {
            val pct = app.discair.model.TasteCard.percent(e.share)
            Row(
                Modifier.fillMaxWidth().semantics(mergeDescendants = true) { contentDescription = "${e.value}, $pct percent" },
                horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(e.value, Modifier.width(92.dp), color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall)
                Box(Modifier.weight(1f)) {
                    Box(
                        Modifier.fillMaxWidth((0.85f * (e.share / top).toFloat()).coerceIn(0.04f, 0.85f)).height(14.dp)
                            .background(if (i == 0 && !sketch) p.accent else p.surface, RoundedCornerShape(3.dp)).border(CoverStackRules.outline(p).dp, p.edgeStrong, RoundedCornerShape(3.dp)),
                    )
                }
                Text("$pct%", Modifier.width(40.dp), color = p.textMuted, textAlign = TextAlign.End, style = MaterialTheme.typography.bodySmall.copy(fontFamily = LocalFontPair.current.mono))
            }
        }
    }
}

/** The 10dp outlined progress bar with a lavender fill (components: Progress). */
@Composable
internal fun CoverStackProgress(fraction: Double, description: String) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(5.dp)
    Column(Modifier.semantics(mergeDescendants = true) { contentDescription = description }, verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Box(Modifier.fillMaxWidth().height(10.dp).background(p.surface, shape).border(CoverStackRules.outline(p).dp, p.edgeStrong, shape)) {
            Box(Modifier.fillMaxWidth(fraction.toFloat().coerceIn(0f, 1f)).height(10.dp).background(p.accent, shape))
        }
        Text(description, color = p.textMuted, style = MaterialTheme.typography.bodySmall, modifier = Modifier.semantics { contentDescription = "" })
    }
}

/** An underlined ink link (accent is never used as text on this theme). */
@Composable
internal fun CoverStackLink(label: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    val p = LocalPalette.current
    Box(modifier.heightIn(min = Target).clickable(role = Role.Button, onClick = onClick), contentAlignment = Alignment.CenterEnd) {
        Text(label, color = p.text, textDecoration = androidx.compose.ui.text.style.TextDecoration.Underline, style = MaterialTheme.typography.labelLarge.copy(fontSize = 13.sp, fontWeight = FontWeight.SemiBold))
    }
}
