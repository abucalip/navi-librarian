package app.discair.ui.discover

import androidx.compose.foundation.clickable
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.stateDescription
import app.discair.model.GetState
import app.discair.ui.common.LocalAcquisitions
import app.discair.ui.common.ModalBottomSheet
import kotlinx.coroutines.launch
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
import app.discair.ui.common.GalleryIcons
import app.discair.ui.common.GalleryListsRules
import app.discair.ui.common.GalleryMuted
import app.discair.ui.common.GalleryPageHead
import app.discair.ui.common.GalleryPrint
import app.discair.ui.common.GalleryProgress
import app.discair.ui.common.GalleryRule
import app.discair.ui.common.GalleryRules
import app.discair.ui.common.GallerySectionHead
import app.discair.ui.common.GalleryType
import app.discair.ui.common.SaveState
import app.discair.ui.common.rememberAlbumYear
import app.discair.ui.common.galleryArrive
import app.discair.ui.common.routeKey
import app.discair.ui.theme.LocalPalette
import java.time.LocalDate

/*
 * Gallery's Discover (Layout.Gallery). Spec: docs/archive/completed/GALLERY_THEME.md sections 9 and 10; mockup: docs/design/gallery/pages/discover.html, frames 1 to 3.
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

// ----- the head: the title and the one switch (docs/archive/completed/Discover_page.md 4.1, in Gallery's type) ----------------------------

/** The date line and the large title, then the switch row: the list on screen in Fraunces italic with a chevron, and one dash per list. */
@Composable
internal fun GalleryDiscoverHead(list: DiscoveryList, onOpenLists: () -> Unit) {
    Column(Modifier.statusBarsPadding()) {
        GalleryPageHead("Discover", Modifier.padding(top = 10.dp).semantics { heading() }, eyebrow = GalleryListsRules.dateLine(LocalDate.now()))
        GalleryDiscoverSwitch(list, onOpenLists, Modifier.padding(top = 6.dp, bottom = 4.dp))
    }
}

/**
 * The switch row (Flow's frames B1, B3, B4 in Gallery's type): the list's short name in Fraunces italic and a `control` chevron, one button that opens the
 * list sheet; at the right one hairline dash per list, the current one long and in `text`. The button says the full name and the place among the lists.
 */
@Composable
internal fun GalleryDiscoverSwitch(list: DiscoveryList, onOpen: () -> Unit, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    Row(modifier.fillMaxWidth().height(GalleryListsRules.SWITCH_DP.dp).padding(horizontal = Gutter), verticalAlignment = Alignment.CenterVertically) {
        Row(
            Modifier.weight(1f, fill = false).fillMaxHeight().clickable(role = Role.Button, onClick = onOpen)
                .semantics { contentDescription = FlowDiscoverRules.switchDescription(list) },
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(FlowDiscoverRules.switchName(list), Modifier.weight(1f, fill = false), color = p.text, style = GalleryType.workM, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Spacer(Modifier.width(6.dp))
            Icon(GalleryIcons.Down, null, tint = p.control, modifier = Modifier.size(20.dp))
        }
        Spacer(Modifier.width(12.dp))
        Spacer(Modifier.weight(1f))
        Row(Modifier.clearAndSetSemantics {}, horizontalArrangement = Arrangement.spacedBy(4.dp), verticalAlignment = Alignment.CenterVertically) {
            val current = FlowDiscoverRules.dotIndex(list)
            DiscoveryList.entries.forEachIndexed { i, _ ->
                Box(
                    Modifier.size(width = (if (i == current) GalleryListsRules.DASH_CURRENT_DP else GalleryListsRules.DASH_DP).dp, height = 2.dp)
                        .background(if (i == current) p.text else p.chart3),
                )
            }
        }
    }
}

/** Gallery's icon for each list in the sheet; the rows and their lines are [FlowDiscoverRules.sheetRows], so both themes list the same seven. */
internal fun galleryListIcon(list: DiscoveryList): ImageVector = when (list) {
    DiscoveryList.Daily -> GalleryIcons.Sun
    DiscoveryList.DeepDive -> GalleryIcons.Album
    DiscoveryList.NewReleases -> GalleryIcons.MusicNote
    DiscoveryList.Classics -> GalleryIcons.Lib
    DiscoveryList.Personal -> GalleryIcons.Paths
    DiscoveryList.Saved -> GalleryIcons.Bookmark
    DiscoveryList.Insights -> GalleryIcons.Wave
}

/**
 * The list sheet (Flow's frame B2 in Gallery's type): "Lists" as a section title, the five lists, then Saved and Insights under a "Yours" catalogue line.
 * Rows are the menu sheet's: icon, name, the line under it, hairlines between. The current list carries the accent check and says it is selected.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun GalleryListSheet(list: DiscoveryList, onSelect: (DiscoveryList) -> Unit, onDismiss: () -> Unit) {
    val p = LocalPalette.current
    val state = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val scope = rememberCoroutineScope()
    fun choose(l: DiscoveryList) {
        onSelect(l)
        scope.launch { state.hide() }.invokeOnCompletion { onDismiss() }
    }
    @Composable
    fun group(rows: List<FlowDiscoverRules.SheetRow>) = rows.forEachIndexed { i, row ->
        if (i > 0) GalleryRule()
        val current = row.list == list
        Row(
            Modifier.fillMaxWidth().heightIn(min = 62.dp).clickable(role = Role.Button) { choose(row.list) }
                .semantics(mergeDescendants = true) { if (current) selected = true },
            horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(galleryListIcon(row.list), null, tint = p.control, modifier = Modifier.size(GalleryRules.ICON.dp))
            Column(Modifier.weight(1f).padding(vertical = 10.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(row.list.label, color = p.text, style = GalleryType.rowTitle())
                Text(row.subtitle, color = p.textMuted, style = GalleryType.small())
            }
            if (current) Icon(GalleryIcons.Check, null, tint = p.accent, modifier = Modifier.size(20.dp))
        }
    }
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = state) {
        Column(Modifier.fillMaxWidth().padding(horizontal = Gutter).padding(bottom = 16.dp)) {
            Text("Lists", Modifier.padding(bottom = 10.dp).semantics { heading() }, color = p.text, style = GalleryType.section)
            GalleryRule()
            group(FlowDiscoverRules.sheetRows.filterNot { FlowDiscoverRules.isYours(it.list) })
            GalleryRule()
            GalleryEyebrow("Yours", Modifier.padding(top = 18.dp, bottom = 4.dp))
            group(FlowDiscoverRules.sheetRows.filter { FlowDiscoverRules.isYours(it.list) })
        }
    }
}

// ----- the lists: one grid of tiles (docs/archive/completed/Discover_page.md 4.3 to 4.5, in Gallery's type) ------------------------------------

/**
 * A list as one two-column grid: a hairline section heading with its count per lens (Daily picks) or genre row (Deep dives), a muted note for a lens with
 * nothing, then the tiles. [empty] is the whole-list note for a list with nothing at all. Sideways swipes are the screen's (switchBy).
 */
@Composable
internal fun GalleryDiscoverGrid(
    sections: List<FlowDiscoverRules.GridSection>, open: Opener, saves: Map<String, SaveState>, defaultSaved: Boolean,
    onSave: (DiscoveryEntry) -> Unit, onDismiss: (DiscoveryEntry, Boolean) -> Unit, empty: @Composable () -> Unit,
) {
    if (sections.all { it.title == null && it.entries.isEmpty() }) {
        empty()
        return
    }
    // An album can sit in two lens rows; only its first tile carries the shared print, so one key is never on the page twice.
    val sharedOwner = remember(sections) {
        buildMap { for (sec in sections) for (e in sec.entries) putIfAbsent(routeKey(e.item.artistName, e.item.album), FlowDiscoverRules.itemKey(sec, e)) }
    }
    LazyVerticalGrid(
        GridCells.Fixed(2), Modifier.fillMaxSize(),
        contentPadding = PaddingValues(start = Gutter, end = Gutter, top = 4.dp, bottom = 16.dp + LocalBottomClearance.current),
        horizontalArrangement = Arrangement.spacedBy(GalleryListsRules.GRID_GAP_X_DP.dp),
        verticalArrangement = Arrangement.spacedBy(GalleryListsRules.GRID_GAP_Y_DP.dp),
    ) {
        var block = 0 // the first six headings and tiles rise in turn as the page arrives
        for (section in sections) {
            val title = section.title
            if (title != null) {
                val at = block++
                // The section head draws its own gutter; the grid already has one, so it bleeds back out to the page's edges.
                item(key = "h:$title", span = { GridItemSpan(maxLineSpan) }) { GalleryCountHead(title, section.count, first = at == 0, modifier = Modifier.galleryArrive(at)) }
            }
            section.note?.let { note -> item(key = "n:${section.title}", span = { GridItemSpan(maxLineSpan) }) { GalleryMuted(note) } }
            val first = block
            block += section.entries.size
            items(section.entries.size, key = { FlowDiscoverRules.itemKey(section, section.entries[it]) }) { i ->
                val entry = section.entries[i]
                val albumKey = routeKey(entry.item.artistName, entry.item.album)
                GalleryDiscoverTile(
                    entry, i, albumKey.takeIf { sharedOwner[it] == FlowDiscoverRules.itemKey(section, entry) }, open,
                    saves[entry.key] ?: if (defaultSaved) SaveState.Saved else SaveState.Idle, { onSave(entry) }, { artistToo -> onDismiss(entry, artistToo) },
                    Modifier.animateItem().galleryArrive(first + i),
                )
            }
        }
    }
}

/** A section heading in the grid: the hairline, the lens or genre name in the section face, and the count as a muted catalogue line (not a link). */
@Composable
private fun GalleryCountHead(title: String, count: Int, first: Boolean, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    Column(modifier.fillMaxWidth().padding(top = if (first) 6.dp else 22.dp)) {
        GalleryRule()
        Row(
            Modifier.fillMaxWidth().padding(top = 12.dp, bottom = 2.dp).semantics(mergeDescendants = true) { heading() },
            horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Bottom,
        ) {
            Text(title, Modifier.weight(1f), style = GalleryType.section, color = p.text)
            Text(GalleryListsRules.countLine(count).uppercase(), style = GalleryType.catalogue, color = p.textMuted, maxLines = 1)
        }
    }
}

/**
 * One tile (Flow's grid card in Gallery's type): the matted print with Get on its corner, "No. 01 · genre", the work in Fraunces italic with Save and the
 * three dots beside it, the maker, then the reason for the pick in italic over up to four lines (else "In your library" for an owned album). The print and
 * the work open the album, the maker the artist.
 */
@Composable
private fun GalleryDiscoverTile(
    entry: DiscoveryEntry, index: Int, sharedKey: String?, open: Opener, saveState: SaveState, onSave: () -> Unit, onDismiss: (artistToo: Boolean) -> Unit,
    modifier: Modifier = Modifier,
) {
    val p = LocalPalette.current
    val item = entry.item
    val artist = item.artistName
    val year = rememberAlbumYear(artist, item.album, item.year)
    val openAlbum = { open.album(routeKey(artist, item.album), artist, item.album, null, item.year) }
    Column(modifier.fillMaxWidth()) {
        Box {
            GalleryPrint(GalleryListsRules.TILE_PRINT_DP.dp, Modifier.fillMaxWidth(), small = true, sharedKey = sharedKey) {
                AlbumCover(artist, item.album, null, Modifier.fillMaxWidth().aspectRatio(1f).clickable(role = Role.Button, onClickLabel = "Open ${item.album}", onClick = openAlbum), rect = true)
            }
            GalleryPrintGet(entry, Modifier.align(Alignment.BottomEnd))
        }
        GalleryEyebrow(GalleryListsRules.entryEyebrow(index, GalleryListsRules.entryGenre(item.genres, item.genreRowLabel)), Modifier.padding(top = 12.dp))
        Row(verticalAlignment = Alignment.Top) {
            Column(Modifier.weight(1f).padding(top = 4.dp)) {
                Text(
                    item.album, Modifier.clickable(role = Role.Button, onClick = openAlbum), color = p.text, style = GalleryType.rowWork,
                    maxLines = 2, overflow = TextOverflow.Ellipsis,
                )
                Text(
                    app.discair.ui.common.GalleryPagesRules.maker(artist, year), Modifier.padding(top = 2.dp).clickable(role = Role.Button) { open.artist(artist, null, null, null) },
                    color = p.text, style = GalleryType.small(), maxLines = 1, overflow = TextOverflow.Ellipsis,
                )
            }
            // 36 wide and 48 tall each, as on Flow (open point O1), so the work keeps its room in a narrow column.
            val saved = saveState == SaveState.Saved
            Box(
                Modifier.size(width = 36.dp, height = 48.dp).clickable(enabled = saveState != SaveState.Pending, role = Role.Button, onClick = onSave)
                    .semantics { contentDescription = GalleryListsRules.saveDescription(item.album, saveState == SaveState.Saved, saveState == SaveState.Failed) },
                contentAlignment = Alignment.Center,
            ) { Icon(GalleryIcons.Bookmark, null, tint = if (saved) p.accent else p.control, modifier = Modifier.size(20.dp)) }
            EntryMenu(entry, onDismiss)
        }
        GalleryListsRules.tileReason(pickReason(item.because, item.similarTo), item.reason, item.lens, item.seedTag, item.libraryAlbumCount, item.acquired)?.let {
            Text(
                it, Modifier.padding(top = 6.dp), color = p.textMuted, style = GalleryType.rowWork.copy(fontSize = 13.sp, lineHeight = 18.sp),
                maxLines = GalleryListsRules.REASON_LINES, overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

/**
 * Get on the print's corner: a 34dp square in `control` with the download glyph in `onControl` (touch box 48dp), the same states as every Get button
 * (Requesting disables it, Requested shows a check, a failure asks again). An album in the library shows a `mat` square with the check in `ok`.
 */
@Composable
private fun GalleryPrintGet(entry: DiscoveryEntry, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    val hub = LocalAcquisitions.current
    val item = entry.item
    val get = hub.getState(item.artistName, item.album)
    val square = GalleryListsRules.GET_ON_PRINT_DP.dp
    val shape = RoundedCornerShape(GalleryRules.BUTTON_RADIUS.dp)
    Box(modifier.size(48.dp), contentAlignment = Alignment.Center) {
        if (item.acquired) Box(
            Modifier.size(square).clip(shape).background(p.mat).border(1.dp, p.edge, shape).semantics { contentDescription = "${item.album} is in your library" },
            contentAlignment = Alignment.Center,
        ) { Icon(GalleryIcons.Check, null, tint = p.ok, modifier = Modifier.size(18.dp)) }
        else {
            val idle = get is GetState.Idle || get is GetState.Failed
            Box(
                Modifier.size(square).clip(shape).background(if (idle) p.control else p.mat).border(1.dp, p.control, shape)
                    .clickable(enabled = idle, role = Role.Button, onClickLabel = "Get album ${item.album}") { hub.getAlbum(item.artistName, item.album, entry.raw) }
                    .semantics { contentDescription = "Get album ${item.album}"; stateDescription = GalleryListsRules.getState(get) },
                contentAlignment = Alignment.Center,
            ) {
                Icon(if (get is GetState.Requested) GalleryIcons.Check else GalleryIcons.Get, null, tint = if (idle) p.onControl else p.control, modifier = Modifier.size(18.dp))
            }
        }
    }
}

/** The three dots, 36 by 48 beside the work: the two ways to say no, then the More / Less like this items every Discover theme offers. */
@Composable
private fun EntryMenu(entry: DiscoveryEntry, onDismiss: (artistToo: Boolean) -> Unit) {
    val p = LocalPalette.current
    var menu by remember { mutableStateOf(false) }
    Box {
        Box(
            Modifier.size(width = 36.dp, height = 48.dp).clickable(role = Role.Button) { menu = true }.semantics { contentDescription = "Options for ${entry.item.album}" },
            contentAlignment = Alignment.Center,
        ) { Icon(GalleryIcons.More, null, tint = p.control, modifier = Modifier.size(20.dp)) }
        DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
            DropdownMenuItem(text = { Text("Not this album") }, onClick = { menu = false; onDismiss(false) })
            DropdownMenuItem(text = { Text("Not this artist") }, onClick = { menu = false; onDismiss(true) })
            PickFeedbackItems(entry) { menu = false }
        }
    }
}

// ----- insights ------------------------------------------------------------------------------------------------

/**
 * Insights (docs/archive/completed/Discover_page.md 4.6 in Gallery's type): the taste card, then every visible card in the server's lens order with no lens headings (an
 * anniversary card still names its lens), then one muted line naming the lenses that are off or have nothing today. A dismissed card leaves at once and
 * [onDismiss] offers Undo.
 */
@Composable
internal fun GalleryInsights(
    response: InsightsResponse, hidden: Set<String>, onDismiss: (InsightCard) -> Unit, taste: TasteResponse?, tasteLoaded: Boolean, showTaste: Boolean, open: Opener,
) {
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 24.dp + LocalBottomClearance.current)) {
        if (showTaste) item(key = "taste") { GalleryTasteCard(taste?.profiles, tasteLoaded) }
        val off = mutableListOf<String>()
        val nothing = mutableListOf<String>()
        for (kind in lensKinds(response)) {
            val lens = response.lenses[kind]
            val cards = lens?.cards.orEmpty().filter { it.id !in hidden }
            when {
                lens?.enabled != true -> off += lensName(kind)
                cards.isEmpty() -> nothing += lensName(kind)
                else -> items(cards, key = { it.id }) { card -> Box(Modifier.animateItem()) { GalleryInsightCard(card, open, onDismiss) } }
            }
        }
        FlowDiscoverRules.insightsNote(off, nothing)?.let { note -> item(key = "note") { GalleryMuted(note, Modifier.padding(horizontal = Gutter, vertical = 8.dp)) } }
    }
}

/** One lens card: a 96dp print, the lens in the accent for an anniversary, the title in italic, the sub line, "Missing" runs, then Open album / Why this? / Dismiss. */
@Composable
private fun GalleryInsightCard(card: InsightCard, open: Opener, onDismiss: (InsightCard) -> Unit) {
    val p = LocalPalette.current
    var why by remember(card.id) { mutableStateOf(false) }
    val artist = card.subject.artist
    val title = card.subject.title
    Column(Modifier.fillMaxWidth().padding(horizontal = Gutter).padding(top = 26.dp, bottom = 18.dp)) {
        // No lens headings any more: each card opens with a hairline and names its lens (the anniversary one in the accent).
        GalleryRule(Modifier.padding(bottom = 18.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.Top) {
            if (artist != null && title != null) GalleryPrint(GalleryListsRules.INSIGHT_PRINT_DP.dp, Modifier.width(GalleryListsRules.INSIGHT_PRINT_DP.dp), small = true) {
                AlbumCover(artist, title, null, Modifier.fillMaxWidth().aspectRatio(1f), rect = true)
            }
            Column(Modifier.weight(1f)) {
                Text(GalleryListsRules.lensLine(lensName(card.kind), card.kind == "anniversary").uppercase(), color = if (card.kind == "anniversary") p.accent else p.textMuted, style = GalleryType.catalogue)
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
