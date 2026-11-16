package app.discair.ui.discover

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.layout.layout
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.offset
import androidx.compose.ui.unit.sp
import app.discair.model.DiscoveryEntry
import app.discair.model.DiscoveryList
import app.discair.model.InsightCard
import app.discair.model.InsightNarrative
import app.discair.model.InsightsResponse
import app.discair.model.TasteCard
import app.discair.model.TasteCardState
import app.discair.model.TasteEntry
import app.discair.model.TasteProfiles
import app.discair.model.TasteResponse
import app.discair.model.pickReason
import app.discair.ui.LocalBottomClearance
import app.discair.ui.Opener
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.FlowPagesRules
import app.discair.ui.common.GalleryButton
import app.discair.ui.common.GalleryButtonKind
import app.discair.ui.common.GalleryEyebrow
import app.discair.ui.common.GalleryGetAlbumButton
import app.discair.ui.common.GalleryIconButton
import app.discair.ui.common.GalleryIcons
import app.discair.ui.common.GalleryListsRules
import app.discair.ui.common.GalleryMuted
import app.discair.ui.common.GalleryPageHead
import app.discair.ui.common.GalleryPrint
import app.discair.ui.common.GalleryProgress
import app.discair.ui.common.GalleryRule
import app.discair.ui.common.GalleryRules
import app.discair.ui.common.GallerySectionHead
import app.discair.ui.common.GallerySourceSwitch
import app.discair.ui.common.GalleryState
import app.discair.ui.common.GalleryTabs
import app.discair.ui.common.GalleryType
import app.discair.ui.common.SaveState
import app.discair.ui.common.rememberAlbumYear
import app.discair.ui.common.routeKey
import app.discair.ui.theme.LocalPalette
import java.time.LocalDate

/*
 * Gallery's Discover (Layout.Gallery). Spec: docs/GALLERY_THEME.md sections 9 and 10; mockup: docs/design/gallery/pages/discover.html, frames 1 to 3.
 * The date line and "Discover" as the large title, tabs Lists / Insights, the list names as a Fraunces source switch, then each list as catalogue entries
 * (a 104dp print, "No. 01 · genre", the work in italic, the maker, the reason, Get / Save / the three-dot menu). Insights are hairline sections: the taste
 * card (a headline, ranked bars, the listen counts), then one section per lens. The data, the saves and the dismissals are the page every theme has.
 */

private val Gutter = GalleryRules.GUTTER.dp

/** A child that is wider than its parent's padding by [by] on each side: puts a full-width row (tabs) back to the sheet's edges. */
internal fun Modifier.bleed(by: Dp): Modifier = layout { measurable, constraints ->
    val px = by.roundToPx()
    val placeable = measurable.measure(constraints.offset(horizontal = 2 * px))
    layout(placeable.width - 2 * px, placeable.height) { placeable.place(-px, 0) }
}

// ----- the head ------------------------------------------------------------------------------------------------

/** The date line, the large title, the Lists / Insights tabs and (on Lists) the list names. [lastList] is the list Lists returns to from Insights. */
@Composable
internal fun GalleryDiscoverHead(list: DiscoveryList, lastList: DiscoveryList, onSelect: (DiscoveryList) -> Unit) {
    val lists = DiscoveryList.entries.filter { it != DiscoveryList.Insights }
    Column(Modifier.statusBarsPadding()) {
        GalleryPageHead("Discover", Modifier.padding(top = 10.dp).semantics { heading() }, eyebrow = GalleryListsRules.dateLine(LocalDate.now()))
        val onInsights = list == DiscoveryList.Insights
        GalleryTabs(listOf("Lists", "Insights"), if (onInsights) 1 else 0, { onSelect(if (it == 1) DiscoveryList.Insights else lastList) }, Modifier.padding(top = 10.dp))
        if (!onInsights) GallerySourceSwitch(
            lists.map { FlowDiscoverRules.switchName(it) }, lists.indexOf(list).coerceAtLeast(0), { onSelect(lists[it]) }, Modifier.padding(top = 12.dp),
        )
    }
}

// ----- the lists -----------------------------------------------------------------------------------------------

/**
 * A list as catalogue entries under hairline headings (a heading per lens or genre row; none for a plain list). [empty] is the whole-list note for a list with
 * nothing at all. Sideways swipes are the screen's (switchBy), as on Flow.
 */
@Composable
internal fun GalleryDiscoverList(
    sections: List<FlowDiscoverRules.GridSection>, open: Opener, saves: Map<String, SaveState>, defaultSaved: Boolean,
    onSave: (DiscoveryEntry) -> Unit, onDismiss: (DiscoveryEntry, Boolean) -> Unit, empty: @Composable () -> Unit,
) {
    if (sections.all { it.title == null && it.entries.isEmpty() }) {
        empty()
        return
    }
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(top = 6.dp, bottom = 16.dp + LocalBottomClearance.current)) {
        for (section in sections) {
            val title = section.title
            if (title != null) item(key = "h:$title") { GallerySectionHead(title) }
            section.note?.let { note -> item(key = "n:${section.title}") { GalleryMuted(note, Modifier.padding(horizontal = Gutter, vertical = 8.dp)) } }
            itemsIndexedEntries(section) { index, entry ->
                GalleryDiscoverEntry(
                    index, entry, open, saves[entry.key] ?: if (defaultSaved) SaveState.Saved else SaveState.Idle, { onSave(entry) }, { artistToo -> onDismiss(entry, artistToo) },
                )
            }
        }
    }
}

private fun androidx.compose.foundation.lazy.LazyListScope.itemsIndexedEntries(
    section: FlowDiscoverRules.GridSection, content: @Composable androidx.compose.foundation.lazy.LazyItemScope.(Int, DiscoveryEntry) -> Unit,
) {
    items(section.entries.size, key = { FlowDiscoverRules.itemKey(section, section.entries[it]) }) { i -> content(i, section.entries[i]) }
}

/** One entry (mockup frame 1): a 104dp print, "No. 01 · Post-rock", the work in Fraunces italic, "Artist, year", the reason in italic, then the actions. */
@Composable
private fun androidx.compose.foundation.lazy.LazyItemScope.GalleryDiscoverEntry(
    index: Int, entry: DiscoveryEntry, open: Opener, saveState: SaveState, onSave: () -> Unit, onDismiss: (artistToo: Boolean) -> Unit,
) {
    val p = LocalPalette.current
    val item = entry.item
    val artist = item.artistName
    val year = rememberAlbumYear(artist, item.album, item.year)
    val openAlbum = { open.album(routeKey(artist, item.album), artist, item.album, null, item.year) }
    val reason = pickReason(item.because, item.similarTo)
    Column(Modifier.animateItem().padding(horizontal = Gutter)) {
        Row(Modifier.fillMaxWidth().padding(vertical = 18.dp), horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.Top) {
            GalleryPrint(GalleryListsRules.ENTRY_PRINT_DP.dp, Modifier.width(GalleryListsRules.ENTRY_PRINT_DP.dp), small = true) {
                AlbumCover(artist, item.album, null, Modifier.fillMaxWidth().aspectRatio(1f).clickable(role = Role.Button, onClick = openAlbum), rect = true)
            }
            Column(Modifier.weight(1f)) {
                GalleryEyebrow(GalleryListsRules.entryEyebrow(index, GalleryListsRules.entryGenre(item.genres, item.genreRowLabel)))
                Text(
                    item.album, Modifier.padding(top = 4.dp).clickable(role = Role.Button, onClick = openAlbum), color = p.text, style = GalleryType.workM,
                    maxLines = 1, overflow = TextOverflow.Ellipsis,
                )
                Text(
                    app.discair.ui.common.GalleryPagesRules.maker(artist, year), Modifier.padding(top = 2.dp).clickable(role = Role.Button) { open.artist(artist, null, null, null) },
                    color = p.text, style = GalleryType.small(), maxLines = 1, overflow = TextOverflow.Ellipsis,
                )
                if (reason.isNotEmpty()) Text(
                    reason, Modifier.padding(top = 6.dp), color = p.textMuted, style = GalleryType.rowWork.copy(fontSize = 13.sp, lineHeight = 18.sp), maxLines = 2, overflow = TextOverflow.Ellipsis,
                )
                Row(Modifier.fillMaxWidth().padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(2.dp), verticalAlignment = Alignment.CenterVertically) {
                    if (item.acquired) Box(Modifier.heightIn(min = 36.dp).padding(end = 8.dp), contentAlignment = Alignment.CenterStart) { GalleryState("In library", color = p.ok) }
                    else GalleryGetAlbumButton(artist, item.album, entry.raw, primary = true, small = true)
                    GalleryButton(
                        when (saveState) { SaveState.Saved -> "Saved"; SaveState.Pending -> "Saving…"; SaveState.Failed -> "Try save again"; SaveState.Idle -> "Save" },
                        onSave, kind = GalleryButtonKind.Text, small = true, enabled = saveState != SaveState.Pending,
                    )
                    Spacer(Modifier.weight(1f))
                    EntryMenu(entry, onDismiss)
                }
            }
        }
        GalleryRule()
    }
}

/** The three dots: the two ways to say no, then the More / Less like this items every Discover theme offers. */
@Composable
private fun EntryMenu(entry: DiscoveryEntry, onDismiss: (artistToo: Boolean) -> Unit) {
    var menu by remember { mutableStateOf(false) }
    Box {
        GalleryIconButton(GalleryIcons.More, "Options for ${entry.item.album}", { menu = true })
        DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
            DropdownMenuItem(text = { Text("Not this album") }, onClick = { menu = false; onDismiss(false) })
            DropdownMenuItem(text = { Text("Not this artist") }, onClick = { menu = false; onDismiss(true) })
            PickFeedbackItems(entry) { menu = false }
        }
    }
}

// ----- insights ------------------------------------------------------------------------------------------------

/**
 * Insights (mockup frame 2): the taste card, then one hairline section per lens in the server's order. A lens the server has not enabled says "off"; an enabled
 * one with nothing says so. Cards are the server's words; a dismissed card leaves at once and [onDismiss] offers Undo.
 */
@Composable
internal fun GalleryInsights(
    response: InsightsResponse, hidden: Set<String>, onDismiss: (InsightCard) -> Unit, taste: TasteResponse?, tasteLoaded: Boolean, showTaste: Boolean, open: Opener,
) {
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 24.dp + LocalBottomClearance.current)) {
        if (showTaste) item(key = "taste") { GalleryTasteCard(taste?.profiles, tasteLoaded) }
        for (kind in lensKinds(response)) {
            val lens = response.lenses[kind]
            val enabled = lens?.enabled == true
            val cards = lens?.cards.orEmpty().filter { it.id !in hidden }
            item(key = "head:$kind") { GallerySectionHead(lensName(kind), link = if (enabled) null else "off") }
            when {
                !enabled -> item(key = "off:$kind") { GalleryMuted("Off. The server turns a lens on only after it passes its check.", Modifier.padding(horizontal = Gutter)) }
                cards.isEmpty() -> item(key = "none:$kind") {
                    GalleryMuted("Nothing to show right now. The lens is on and found no cards; it never fills the gap with guesses.", Modifier.padding(horizontal = Gutter))
                }
                else -> items(cards, key = { it.id }) { card -> Box(Modifier.animateItem()) { GalleryInsightCard(card, open, onDismiss) } }
            }
        }
    }
}

/** One lens card: a 96dp print, the lens in the accent for an anniversary, the title in italic, the sub line, "Missing" runs, then Open album / Why this? / Dismiss. */
@Composable
private fun GalleryInsightCard(card: InsightCard, open: Opener, onDismiss: (InsightCard) -> Unit) {
    val p = LocalPalette.current
    var why by remember(card.id) { mutableStateOf(false) }
    val artist = card.subject.artist
    val title = card.subject.title
    Column(Modifier.fillMaxWidth().padding(horizontal = Gutter).padding(bottom = 18.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.Top) {
            if (artist != null && title != null) GalleryPrint(GalleryListsRules.INSIGHT_PRINT_DP.dp, Modifier.width(GalleryListsRules.INSIGHT_PRINT_DP.dp), small = true) {
                AlbumCover(artist, title, null, Modifier.fillMaxWidth().aspectRatio(1f), rect = true)
            }
            Column(Modifier.weight(1f)) {
                if (card.kind == "anniversary") Text(lensName(card.kind).removeSuffix("s").uppercase(), color = p.accent, style = GalleryType.catalogue)
                Text(card.title, Modifier.padding(top = 6.dp), color = p.text, style = GalleryType.workM)
                val sub = listOfNotNull(artist, card.body.ifBlank { null }).joinToString(" · ")
                if (sub.isNotEmpty()) GalleryMuted(sub, Modifier.padding(top = 4.dp))
            }
        }
        for (run in card.missingRuns) {
            val span = if (run.firstPosition == run.lastPosition) "${run.firstPosition}" else "${run.firstPosition} to ${run.lastPosition}"
            GalleryMuted("Missing $span" + if (run.labels.isEmpty()) "" else ": " + run.labels.joinToString(", "), Modifier.padding(top = 8.dp))
        }
        if (why) GalleryMuted(InsightNarrative.why(card), Modifier.padding(top = 10.dp))
        Row(Modifier.padding(top = 14.dp), horizontalArrangement = Arrangement.spacedBy(2.dp), verticalAlignment = Alignment.CenterVertically) {
            // A card names an album but carries no library id, so the button opens the album page (where Play is) rather than guessing.
            if (artist != null && title != null) GalleryButton("Open album", { open.album(routeKey(artist, title), artist, title, null, card.subject.year) }, small = true, icon = GalleryIcons.Play)
            GalleryButton(if (why) "Hide why" else "Why this?", { why = !why }, kind = GalleryButtonKind.Text)
            if (card.dismissible) GalleryButton("Dismiss", { onDismiss(card) }, kind = GalleryButtonKind.Text, modifier = Modifier.semantics { contentDescription = "Dismiss ${card.title}" })
        }
    }
}

// ----- the taste card ------------------------------------------------------------------------------------------

/**
 * The taste card as a section: "Your taste · last 90 days", the server's headline in italic, the window's top four genres as ranked bars, then the listen counts
 * and Details. Empty and thin profiles say so in words (thin with a progress line). Details opens the same full-picture sheet every theme has.
 */
@Composable
internal fun GalleryTasteCard(profiles: TasteProfiles?, loaded: Boolean) {
    val p = LocalPalette.current
    var sheet by remember { mutableStateOf(false) }
    val state = TasteCard.state(profiles)
    GallerySectionHead(
        if (state is TasteCardState.Ready) GalleryListsRules.tasteHeading(TasteCard.windowLabel(state.headline.window, profiles?.recentDays ?: 90)) else "Your taste",
    )
    Column(Modifier.fillMaxWidth().padding(horizontal = Gutter)) {
        when (state) {
            TasteCardState.Empty -> {
                Text(if (loaded) "Taste needs listening history." else "Reading your saved profile.", color = p.text, style = GalleryType.workM, modifier = Modifier.semantics { heading() })
                if (loaded) GalleryMuted("Connect ListenBrainz or keep playing. Once a window has enough listens I will start describing it.", Modifier.padding(top = 6.dp))
            }
            is TasteCardState.Thin -> {
                Text("Still getting to know you.", color = p.text, style = GalleryType.workM, modifier = Modifier.semantics { heading() })
                GalleryMuted("Only ${state.have} listens in the recent window. I won't call a shift until there are ${state.need}.", Modifier.padding(top = 6.dp))
                GalleryProgress(TasteCard.progress(state.have, state.need).toFloat(), Modifier.padding(top = 12.dp).semantics { contentDescription = "${state.have} of ${state.need} listens needed" })
            }
            is TasteCardState.Ready -> {
                Text(state.headline.text, Modifier.padding(bottom = 14.dp), color = p.text, style = GalleryType.workM, maxLines = 3, overflow = TextOverflow.Ellipsis)
                val w = profiles?.window(state.headline.window)
                val top = if (w == null || w.isLowSample("genre")) emptyList() else w.entries("genre").take(GalleryListsRules.BARS_SHOWN)
                if (top.isNotEmpty()) GalleryBars(top)
            }
        }
        if (state !is TasteCardState.Empty) Row(Modifier.fillMaxWidth().padding(top = 6.dp), verticalAlignment = Alignment.CenterVertically) {
            if (state is TasteCardState.Ready) GalleryEyebrow(GalleryListsRules.listensLine(state.windowListens, state.allTimeListens), Modifier.weight(1f))
            else Spacer(Modifier.weight(1f))
            Text(
                "Details", Modifier.heightIn(min = 48.dp).clickable(role = Role.Button) { sheet = true }.padding(top = 14.dp), color = p.control,
                textDecoration = TextDecoration.Underline, style = GalleryType.small(),
            )
        }
    }
    if (sheet && profiles != null) TasteSheet(profiles) { sheet = false }
}

/**
 * Ranked bars (gallery.css `.rank`): a 96dp label, a 6dp bar in `chart3` (the first in `accent`; the longest fills 85% of the track) and the share in DM Mono.
 * [sketch] draws every bar in `chart3`: a low-sample window is a sketch, not a finding.
 */
@Composable
internal fun GalleryBars(entries: List<TasteEntry>, sketch: Boolean = false, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    val top = entries.maxOfOrNull { it.share } ?: 0.0
    Column(modifier, verticalArrangement = Arrangement.spacedBy(12.dp)) {
        for ((i, e) in entries.withIndex()) {
            val pct = TasteCard.percent(e.share)
            val fraction = FlowPagesRules.barFraction(e.share, top)
            val fill = if (i == 0 && !sketch) p.accent else p.chart3
            Row(
                Modifier.fillMaxWidth().semantics(mergeDescendants = true) { contentDescription = "${e.value}, $pct percent" },
                horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(e.value, Modifier.width(96.dp), color = p.text, style = GalleryType.small(), maxLines = 1, overflow = TextOverflow.Ellipsis)
                Box(Modifier.weight(1f).height(6.dp).drawBehind { drawRect(fill, size = Size(size.width * fraction, size.height)) })
                Text("$pct%", Modifier.width(40.dp), color = p.textMuted, style = GalleryType.time, maxLines = 1)
            }
        }
    }
}
