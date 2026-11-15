package app.discair.ui.discover

import app.discair.ui.common.ArtIcons
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.material3.Icon
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.selected
import kotlinx.coroutines.launch
import androidx.compose.runtime.rememberCoroutineScope
import app.discair.ui.common.FlowEyebrow
import app.discair.ui.common.FlowGroup
import app.discair.ui.common.FlowIconTile
import app.discair.ui.common.FlowListRow
import app.discair.ui.common.FlowRules
import app.discair.ui.common.ModalBottomSheet
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
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
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import app.discair.model.DiscoveryEntry
import app.discair.model.pickReason
import app.discair.model.DiscoveryList
import app.discair.model.GetState
import app.discair.model.InsightCard
import app.discair.model.InsightNarrative
import app.discair.model.TasteEntry
import app.discair.ui.Opener
import app.discair.ui.common.Button
import app.discair.ui.common.FilterChip
import app.discair.ui.common.FlowCover
import app.discair.ui.common.FlowGetButton
import app.discair.ui.common.FlowPagesRules
import app.discair.ui.common.FlowSmallButton
import app.discair.ui.common.FlowTabs
import app.discair.ui.common.FlowTag
import app.discair.ui.common.LocalAcquisitions
import app.discair.ui.common.OutlinedButton
import app.discair.ui.common.SaveState
import app.discair.ui.common.Target
import app.discair.ui.common.flowCard
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items as gridItems
import app.discair.ui.LocalBottomClearance
import app.discair.ui.common.flowDepth
import androidx.compose.foundation.shape.CircleShape
import app.discair.ui.common.rememberAlbumYear
import app.discair.ui.common.routeKey
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.accentText

/*
 * Flow's Discover. Mockup: flow/discover, frames 1 to 3 (flow.css `.dc`, `.cards`, `.bars`).
 * DiscoverScreen, InsightsPage and the taste card reach this behind isFlow(); no other theme changes. The page's name is drawn large by the
 * shell's bar (MainShell), beside the round buttons, as the mockup has it.
 */

/** Lists | Insights as the segmented control, then the list names as capsule chips (the chips only while Lists is chosen). */
@Composable
internal fun FlowDiscoverHeader(list: DiscoveryList, onSelect: (DiscoveryList) -> Unit) {
    val lists = DiscoveryList.entries.filter { it != DiscoveryList.Insights }
    FlowTabs(
        listOf("Lists", "Insights"), if (list == DiscoveryList.Insights) 1 else 0,
        { if (it == 1) onSelect(DiscoveryList.Insights) else if (list == DiscoveryList.Insights) onSelect(lists.first()) },
        Modifier.padding(start = 16.dp, top = 4.dp, end = 16.dp, bottom = 12.dp).fillMaxWidth(),
    )
    if (list != DiscoveryList.Insights) Row(
        Modifier.horizontalScroll(rememberScrollState()).padding(start = 16.dp, end = 16.dp, bottom = 12.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        lists.forEach { l -> FilterChip(selected = l == list, onClick = { onSelect(l) }, label = { Text(l.label) }, modifier = Modifier.heightIn(min = 34.dp)) }
    }
}

/**
 * The Discover card (`.dc`): a white card at depth 1, the cover 112 at the left, then title, artist and year, the reason line when the server
 * sent one (see [pickReason]), and Get, Save and a round three-dot menu (Not this album, Not this artist) at the foot. Whether the album is owned is said in words.
 */
@Composable
internal fun FlowDiscoverCard(
    entry: DiscoveryEntry, open: Opener, saveState: SaveState, onSave: () -> Unit, onDismiss: (artistToo: Boolean) -> Unit, modifier: Modifier = Modifier,
) {
    val p = LocalPalette.current
    val item = entry.item
    val artist = item.artistName
    val year = rememberAlbumYear(artist, item.album, item.year)
    val openAlbum = { open.album(routeKey(artist, item.album), artist, item.album, null, item.year) }
    var menu by remember { mutableStateOf(false) }
    Row(
        modifier.fillMaxWidth().flowCard(p).padding(10.dp),
        horizontalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        FlowCover(artist, item.album, null, Modifier.width(FlowPagesRules.DISCOVER_COVER.dp).clickable(role = Role.Button, onClick = openAlbum), radius = 10)
        Column(Modifier.weight(1f).heightIn(min = FlowPagesRules.DISCOVER_COVER.dp)) {
            Text(
                item.album, color = p.text, maxLines = 2, overflow = TextOverflow.Ellipsis,
                style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 15.sp, lineHeight = 20.sp),
                modifier = Modifier.clickable(role = Role.Button, onClick = openAlbum),
            )
            Text(
                listOfNotNull(artist.ifBlank { null }, year?.toString()).joinToString(" · "), color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis,
                style = MaterialTheme.typography.bodySmall.copy(fontSize = 13.sp, lineHeight = 18.sp), modifier = Modifier.clickable(role = Role.Button) { open.artist(artist, null, null, null) },
            )
            val reason = pickReason(item.because, item.similarTo)
            if (reason.isNotEmpty()) Text(reason, color = p.textMuted, maxLines = 2, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall.copy(fontSize = 13.sp, lineHeight = 18.sp))
            Spacer(Modifier.weight(1f))
            Row(horizontalArrangement = Arrangement.spacedBy(0.dp), verticalAlignment = Alignment.CenterVertically) {
                // Every button is the round 34dp icon button the three-dot menu is, in a 48dp-wide touch target.
                val touch = Modifier.widthIn(min = Target)
                if (item.acquired) FlowSmallButton(null, ArtIcons.Check, false, "${item.album} is in your library", touch, enabled = false) {}
                else FlowGetButton(artist, item.album, entry.raw, touch, iconOnly = true)
                val saved = saveState == SaveState.Saved
                FlowSmallButton(
                    null, if (saved) ArtIcons.BookmarkFilled else ArtIcons.Bookmark, false, if (saved) "Remove ${item.album} from saved" else "Save ${item.album}",
                    touch, enabled = saveState != SaveState.Pending, onClick = onSave,
                )
                Spacer(Modifier.weight(1f))
                Box {
                    FlowSmallButton(null, ArtIcons.More, false, "Options for ${item.album}", touch) { menu = true }
                    DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                        DropdownMenuItem(text = { Text("Not this album") }, onClick = { menu = false; onDismiss(false) })
                        DropdownMenuItem(text = { Text("Not this artist") }, onClick = { menu = false; onDismiss(true) })
                        PickFeedbackItems(entry) { menu = false }
                    }
                }
            }
        }
    }
}

/**
 * The grid card (frames B1, B3; docs/Discover_page.md 4.5): the square cover with Get on it, then the title, "artist · year" and the reason line, with Save and
 * the three-dot menu beside the title. The cover opens the album, the artist line the artist.
 */
@Composable
internal fun FlowDiscoverGridCard(
    entry: DiscoveryEntry, open: Opener, saveState: SaveState, onSave: () -> Unit, onDismiss: (artistToo: Boolean) -> Unit, modifier: Modifier = Modifier,
) {
    val p = LocalPalette.current
    val item = entry.item
    val artist = item.artistName
    val year = rememberAlbumYear(artist, item.album, item.year)
    val openAlbum = { open.album(routeKey(artist, item.album), artist, item.album, null, item.year) }
    var menu by remember { mutableStateOf(false) }
    val coverShape = RoundedCornerShape(FlowDiscoverRules.GRID_COVER_RADIUS.dp)
    Column(modifier.fillMaxWidth()) {
        Box {
            FlowCover(
                artist, item.album, null, Modifier.fillMaxWidth().flowDepth(1, coverShape, p).clickable(role = Role.Button, onClick = openAlbum),
                radius = FlowDiscoverRules.GRID_COVER_RADIUS,
            )
            // The 34 dp circle sits 8 dp from the corner; its touch box is 48 dp, so the box is 1 dp from it.
            Box(Modifier.align(Alignment.BottomEnd).padding(end = 1.dp, bottom = 1.dp).size(Target), contentAlignment = Alignment.Center) {
                val circle = FlowDiscoverRules.GET_ON_COVER.dp
                Box(Modifier.size(circle).flowDepth(1, CircleShape, p))
                if (item.acquired) Box(
                    Modifier.size(circle).clip(CircleShape).background(p.surface).semantics { contentDescription = "${item.album} is in your library" },
                    contentAlignment = Alignment.Center,
                ) { Icon(ArtIcons.Check, contentDescription = null, tint = p.text, modifier = Modifier.size(18.dp)) }
                else FlowGetButton(artist, item.album, entry.raw, Modifier.widthIn(min = Target), iconOnly = true)
            }
        }
        Spacer(Modifier.height(8.dp))
        Row(verticalAlignment = Alignment.Top) {
            Column(Modifier.weight(1f)) {
                Text(
                    item.album, color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis,
                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold, fontSize = 14.sp, lineHeight = 19.sp),
                    modifier = Modifier.clickable(role = Role.Button, onClick = openAlbum),
                )
                Text(
                    listOfNotNull(artist.ifBlank { null }, year?.toString()).joinToString(" · "), color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis,
                    style = MaterialTheme.typography.bodySmall.copy(fontSize = 12.5.sp, lineHeight = 17.sp),
                    modifier = Modifier.clickable(role = Role.Button) { open.artist(artist, null, null, null) },
                )
            }
            // O1: 36 wide and 48 tall each, so the title keeps its room in a 157 dp column.
            val saved = saveState == SaveState.Saved
            Box(
                Modifier.size(width = 36.dp, height = Target).clickable(enabled = saveState != SaveState.Pending, role = Role.Button, onClick = onSave)
                    .semantics { contentDescription = if (saved) "Remove ${item.album} from saved" else "Save ${item.album}" },
                contentAlignment = Alignment.Center,
            ) { Icon(if (saved) ArtIcons.BookmarkFilled else ArtIcons.Bookmark, contentDescription = null, tint = if (saved) p.accent else p.textMuted, modifier = Modifier.size(18.dp)) }
            Box {
                Box(
                    Modifier.size(width = 36.dp, height = Target).clickable(role = Role.Button) { menu = true }.semantics { contentDescription = "Options for ${item.album}" },
                    contentAlignment = Alignment.Center,
                ) { Icon(ArtIcons.More, contentDescription = null, tint = p.textMuted, modifier = Modifier.size(18.dp)) }
                DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                    DropdownMenuItem(text = { Text("Not this album") }, onClick = { menu = false; onDismiss(false) })
                    DropdownMenuItem(text = { Text("Not this artist") }, onClick = { menu = false; onDismiss(true) })
                    PickFeedbackItems(entry) { menu = false }
                }
            }
        }
        FlowDiscoverRules.thirdLine(pickReason(item.because, item.similarTo), item.acquired)?.let {
            Text(it, color = p.textMuted, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall.copy(fontSize = 12.5.sp, lineHeight = 17.sp))
        }
    }
}

/** The muted box a section note sits in (docs/Discover_page.md 4.4): `raised`, radius 12, 13/18 sp. */
@Composable
internal fun FlowSectionNote(text: String, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    Text(
        text, modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(p.raised).padding(horizontal = 12.dp, vertical = 10.dp), color = p.textMuted,
        style = MaterialTheme.typography.bodySmall.copy(fontSize = 13.sp, lineHeight = 18.sp),
    )
}

/**
 * Flow's list body: one two-column grid, a full-width heading (name and count) and note per section, then the cards. [empty] is the whole-list note
 * for a list with nothing at all.
 */
@Composable
internal fun FlowDiscoverGrid(
    list: DiscoveryList, sections: List<FlowDiscoverRules.GridSection>, open: Opener, saves: Map<String, SaveState>,
    onSave: (DiscoveryEntry) -> Unit, onDismiss: (DiscoveryEntry, Boolean) -> Unit, empty: @Composable () -> Unit,
) {
    if (sections.all { it.title == null && it.entries.isEmpty() }) {
        empty()
        return
    }
    LazyVerticalGrid(
        GridCells.Fixed(2), Modifier.fillMaxSize(),
        contentPadding = PaddingValues(start = 16.dp, end = 16.dp, bottom = 16.dp + LocalBottomClearance.current),
        horizontalArrangement = Arrangement.spacedBy(FlowDiscoverRules.GRID_GAP_X.dp),
        verticalArrangement = Arrangement.spacedBy(FlowDiscoverRules.GRID_GAP_Y.dp),
    ) {
        for (section in sections) {
            val title = section.title
            if (title != null) item(key = "h:$title", span = { GridItemSpan(maxLineSpan) }) {
                Box(Modifier.padding(top = 8.dp)) { FlowLensHeading(title, section.count.toString()) }
            }
            section.note?.let { note -> item(key = "n:${section.title}", span = { GridItemSpan(maxLineSpan) }) { FlowSectionNote(note) } }
            gridItems(section.entries, key = { FlowDiscoverRules.itemKey(section, it) }) { entry ->
                FlowDiscoverGridCard(
                    entry, open, saveState = saves[entry.key] ?: if (list == DiscoveryList.Saved) SaveState.Saved else SaveState.Idle,
                    onSave = { onSave(entry) }, onDismiss = { artistToo -> onDismiss(entry, artistToo) }, modifier = Modifier.animateItem(),
                )
            }
        }
    }
}

// ----- The list switch and its sheet (docs/Discover_page.md 4.1, 4.2; mockup flow/discover-b frames B1 and B2) ----------------

/** The numbers and tables of Flow's one-switch Discover. Kept here, not in the composables, so a unit test can hold them. */
internal object FlowDiscoverRules {
    const val SWITCH_HEIGHT = 48
    const val DOT = 6
    const val DOT_CURRENT = 18
    const val GRID_GAP_X = 14
    const val GRID_GAP_Y = 16
    const val GRID_COVER_RADIUS = 12
    const val GET_ON_COVER = 34
    const val MORE = "More"

    /** One section of the grid (docs/Discover_page.md 4.3, 4.4): a heading with a count ([title] null draws no heading), its cards, or a note when there are none. */
    class GridSection(val title: String?, val entries: List<DiscoveryEntry>, val note: String? = null) {
        val count get() = entries.size
    }

    /**
     * The sections a list draws. Daily picks: one per lens in server order, a failed or empty lens with its note. Deep dives: one per genre row label
     * ("More" when blank), none titled when no row has a label. Every other list: one untitled section. An empty result is one untitled empty section, which
     * the screen draws as the whole-list note; Daily picks turned off is the same, so the note is said once.
     */
    internal fun sections(list: DiscoveryList, sections: List<Section>, hidden: Map<String, Boolean>): List<GridSection> {
        fun visible(s: Section) = s.result?.entries.orEmpty().distinctBy { it.key }.filter { hidden[it.key] != true }
        return when (list) {
            DiscoveryList.Daily ->
                if (sections.isNotEmpty() && sections.all { it.result?.disabled == true }) listOf(GridSection(null, emptyList()))
                else sections.map {
                    val entries = visible(it)
                    GridSection(it.title, entries, if (entries.isNotEmpty()) null else it.error?.let { e -> "${it.title} could not be loaded: $e" } ?: it.result?.message ?: "No albums today.")
                }
            DiscoveryList.DeepDive -> {
                val rows = sections.flatMap { visible(it) }
                val groups = rows.groupBy { it.item.genreRowLabel ?: "" }
                if (groups.keys.all { it.isEmpty() }) listOf(GridSection(null, rows))
                else groups.map { (label, entries) -> GridSection(label.ifEmpty { MORE }, entries) }
            }
            else -> listOf(GridSection(null, sections.flatMap { visible(it) }))
        }
    }

    /** The grid key of a card: one album can appear in two lens sections, so the section's title is part of it. */
    fun itemKey(section: GridSection, entry: DiscoveryEntry) = "${section.title.orEmpty()}:${entry.key}"

    /** The third line under a card: the reason, else "In your library" for an owned album, else nothing. */
    fun thirdLine(reason: String, owned: Boolean): String? = reason.ifEmpty { if (owned) "In your library" else null }

    /** The one line under Flow's Insights cards (4.6): the lenses that are off and the ones with nothing today; either half is left out when empty, and no note when both are. */
    fun insightsNote(off: List<String>, empty: List<String>): String? {
        val parts = listOfNotNull(
            off.takeIf { it.isNotEmpty() }?.let { "Off: ${it.joinToString(", ")}." },
            empty.takeIf { it.isNotEmpty() }?.let { "Nothing today: ${it.joinToString(", ")}." },
        )
        return parts.joinToString(" ").ifEmpty { null }
    }

    /** One row of the list sheet: the list, its icon and the line under its name. */
    class SheetRow(val list: DiscoveryList, val icon: ImageVector, val subtitle: String)

    /** The sheet's rows in [DiscoveryList.entries] order: the five lists, then (under "Yours") Saved and Insights. */
    val sheetRows: List<SheetRow> = listOf(
        SheetRow(DiscoveryList.Daily, ArtIcons.Sun, "Four lists, new each day"),
        SheetRow(DiscoveryList.DeepDive, ArtIcons.Album, "More from artists you play, by genre"),
        SheetRow(DiscoveryList.NewReleases, ArtIcons.MusicNote, "Recent albums near your taste"),
        SheetRow(DiscoveryList.Classics, ArtIcons.Lib, "Well-known albums you do not own"),
        SheetRow(DiscoveryList.Personal, ArtIcons.Paths, "Further from what you play"),
        SheetRow(DiscoveryList.Saved, ArtIcons.Bookmark, "Albums you kept for later"),
        SheetRow(DiscoveryList.Insights, ArtIcons.Wave, "Your taste and what it notices"),
    )

    /** Saved and Insights sit under "Yours" in the sheet. */
    fun isYours(list: DiscoveryList) = list == DiscoveryList.Saved || list == DiscoveryList.Insights

    /** The short name the switch shows (owner decision O2); the sheet and everything else keep [DiscoveryList.label]. */
    fun switchName(list: DiscoveryList): String = when (list) {
        DiscoveryList.Classics -> "Collection"
        DiscoveryList.Personal -> "Personal"
        else -> list.label
    }

    /** The page dot that is current. */
    fun dotIndex(list: DiscoveryList): Int = DiscoveryList.entries.indexOf(list)

    /** What a screen reader hears on the switch: the full label and the place among the lists. */
    fun switchDescription(list: DiscoveryList): String =
        "${list.label}, list ${dotIndex(list) + 1} of ${DiscoveryList.entries.size}. Change list"
}

/** The switch row under the shell's bar: the current list's short name with a chevron, and one page dot per list. */
@Composable
internal fun FlowDiscoverSwitch(list: DiscoveryList, onOpen: () -> Unit) {
    val p = LocalPalette.current
    Row(
        Modifier.fillMaxWidth().height(FlowDiscoverRules.SWITCH_HEIGHT.dp).padding(horizontal = 16.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(
            Modifier.weight(1f, fill = false).fillMaxHeight().clickable(role = Role.Button, onClick = onOpen)
                .semantics { contentDescription = FlowDiscoverRules.switchDescription(list) },
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                FlowDiscoverRules.switchName(list), color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f, fill = false),
                style = MaterialTheme.typography.titleLarge.copy(fontSize = 22.sp, lineHeight = 28.sp, fontWeight = FontWeight.Bold, letterSpacing = (-0.02).em),
            )
            Spacer(Modifier.width(4.dp))
            Icon(ArtIcons.Down, contentDescription = null, tint = p.accent, modifier = Modifier.size(20.dp))
        }
        Spacer(Modifier.width(12.dp))
        Spacer(Modifier.weight(1f))
        Row(Modifier.clearAndSetSemantics {}, horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically) {
            val current = FlowDiscoverRules.dotIndex(list)
            DiscoveryList.entries.forEachIndexed { i, _ ->
                Box(
                    Modifier.size(width = (if (i == current) FlowDiscoverRules.DOT_CURRENT else FlowDiscoverRules.DOT).dp, height = FlowDiscoverRules.DOT.dp)
                        .clip(RoundedCornerShape(3.dp)).background(if (i == current) p.text else p.chart3),
                )
            }
        }
    }
}

/** The sheet that lists every list (frame B2): the five lists, then Saved and Insights under "Yours". No counts and no covers. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun FlowListSheet(list: DiscoveryList, onSelect: (DiscoveryList) -> Unit, onDismiss: () -> Unit) {
    val p = LocalPalette.current
    val state = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val scope = rememberCoroutineScope()
    fun choose(l: DiscoveryList) {
        onSelect(l)
        scope.launch { state.hide() }.invokeOnCompletion { onDismiss() }
    }
    @Composable
    fun group(rows: List<FlowDiscoverRules.SheetRow>) = FlowGroup {
        rows.forEachIndexed { i, row ->
            val current = row.list == list
            FlowListRow(
                row.list.label, Modifier.then(if (current) Modifier.semantics { selected = true } else Modifier), state = row.subtitle,
                onClick = { choose(row.list) }, divider = i > 0, leading = { FlowIconTile(row.icon) },
                trailing = { if (current) Icon(ArtIcons.Check, contentDescription = null, tint = p.accent, modifier = Modifier.size(20.dp)) },
            )
        }
    }
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = state, containerColor = p.rail) {
        Column(Modifier.padding(bottom = 16.dp)) {
            Text(
                "Lists", Modifier.padding(start = 16.dp, end = 16.dp, bottom = 12.dp).semantics { heading() }, color = p.text,
                style = MaterialTheme.typography.titleLarge.copy(fontSize = 20.sp, lineHeight = 24.sp, fontWeight = FontWeight.Bold),
            )
            group(FlowDiscoverRules.sheetRows.filterNot { FlowDiscoverRules.isYours(it.list) })
            FlowEyebrow("Yours", Modifier.padding(start = 28.dp, top = 18.dp, end = 28.dp, bottom = 6.dp))
            group(FlowDiscoverRules.sheetRows.filter { FlowDiscoverRules.isYours(it.list) })
        }
    }
}

// ----- Insights ---------------------------------------------------------------------------------------------------------

/** A lens heading (`h3`: Inter 700 20), and "off" or the card count in muted text at the right, so an off lens stays visible. */
@Composable
internal fun FlowLensHeading(name: String, count: String) {
    val p = LocalPalette.current
    Row(Modifier.fillMaxWidth().padding(top = 6.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(
            name, Modifier.weight(1f).semantics { heading() }, color = p.text,
            style = MaterialTheme.typography.titleLarge.copy(fontSize = 20.sp, lineHeight = 24.sp, fontWeight = FontWeight.Bold, letterSpacing = (-0.02).em),
        )
        Text(count, color = p.textMuted, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.semantics { contentDescription = "$name: $count" })
    }
}

/** The white card every Flow Insights block sits in (`.card`: radius 16, depth 1, padding 14). */
@Composable
internal fun FlowCardBox(modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    Column(modifier.fillMaxWidth().flowCard(LocalPalette.current).padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) { content() }
}

/**
 * An Insights card (frame 2, the Anniversary card): the cover 88, a tag, the title, the subject and the server's body, then Open album (filled),
 * Why? and Dismiss. The wording is the server's.
 */
@Composable
internal fun FlowInsightCard(card: InsightCard, open: Opener, onDismiss: (InsightCard) -> Unit) {
    val p = LocalPalette.current
    var why by remember(card.id) { mutableStateOf(false) }
    val artist = card.subject.artist
    val title = card.subject.title
    FlowCardBox {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.Top) {
            if (artist != null && title != null) FlowCover(artist, title, null, Modifier.size(FlowPagesRules.INSIGHT_COVER.dp), radius = 10)
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                if (card.kind == "anniversary") FlowTag(lensName(card.kind), tint = p.cautionDim, labelColor = p.caution) else FlowTag(lensName(card.kind))
                Text(card.title, Modifier.padding(top = 4.dp), color = p.text, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 15.sp, lineHeight = 20.sp))
                artist?.let { Text(it, color = p.textMuted, style = MaterialTheme.typography.bodySmall.copy(fontSize = 13.sp, lineHeight = 18.sp)) }
                if (card.body.isNotEmpty()) Text(card.body, color = p.textMuted, style = MaterialTheme.typography.bodySmall.copy(fontSize = 13.sp, lineHeight = 18.sp))
            }
        }
        for (run in card.missingRuns) {
            val span = if (run.firstPosition == run.lastPosition) "${run.firstPosition}" else "${run.firstPosition} to ${run.lastPosition}"
            Text("Missing $span" + if (run.labels.isEmpty()) "" else ": " + run.labels.joinToString(", "), color = p.textMuted, style = MaterialTheme.typography.labelMedium)
        }
        if (why) Text(InsightNarrative.why(card), color = p.textMuted, style = MaterialTheme.typography.bodySmall)
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            if (artist != null && title != null) Button(
                onClick = { open.album(routeKey(artist, title), artist, title, null, card.subject.year) }, modifier = Modifier.weight(1f),
            ) { Text("Open album", maxLines = 1) }
            OutlinedButton(onClick = { why = !why }, Modifier.then(if (artist != null && title != null) Modifier else Modifier.weight(1f))) { Text(if (why) "Hide why" else "Why?", maxLines = 1) }
            if (card.dismissible) OutlinedButton(onClick = { onDismiss(card) }, Modifier.semantics { contentDescription = "Dismiss ${card.title}" }) { Text("Dismiss", maxLines = 1) }
        }
    }
}

/**
 * Ranked bars (`.bars`): the label, an 8dp rounded bar and the percentage. The first is the accent, the rest `chart3`; the longest is 85% of the
 * track. [sketch] draws every bar in `chart3`: a low-sample window is a sketch, not a finding.
 */
@Composable
internal fun FlowBars(entries: List<TasteEntry>, sketch: Boolean = false, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    val top = entries.maxOfOrNull { it.share } ?: 0.0
    Column(modifier, verticalArrangement = Arrangement.spacedBy(10.dp)) {
        for ((i, e) in entries.withIndex()) {
            val pct = app.discair.model.TasteCard.percent(e.share)
            val fraction = FlowPagesRules.barFraction(e.share, top)
            val fill = if (i == 0 && !sketch) p.chart1 else p.chart3
            Row(
                Modifier.fillMaxWidth().semantics(mergeDescendants = true) { contentDescription = "${e.value}, $pct percent" },
                horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(e.value, Modifier.width(92.dp), color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall.copy(fontSize = 13.sp))
                Box(
                    Modifier.weight(1f).height(FlowPagesRules.BAR_HEIGHT.dp).drawBehind {
                        drawRoundRect(fill, size = androidx.compose.ui.geometry.Size(size.width * fraction, size.height), cornerRadius = CornerRadius(size.height / 2))
                    },
                )
                Text("$pct%", Modifier.width(40.dp), color = p.textMuted, textAlign = TextAlign.End, style = MaterialTheme.typography.bodySmall.copy(fontSize = 13.sp))
            }
        }
    }
}

/** An accent link (`.lk`: Inter 500 14) with a 48dp touch height. */
@Composable
internal fun FlowLink(label: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Box(modifier.heightIn(min = Target).clickable(role = Role.Button, onClick = onClick), contentAlignment = Alignment.CenterEnd) {
        Text(label, color = LocalPalette.current.accentText, style = MaterialTheme.typography.labelLarge.copy(fontSize = 14.sp, fontWeight = FontWeight.Medium))
    }
}
