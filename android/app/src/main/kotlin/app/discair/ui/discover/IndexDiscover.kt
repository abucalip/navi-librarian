package app.discair.ui.discover

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.Icon
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
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
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
import app.discair.ui.common.GalleryListsRules
import app.discair.ui.common.IndexButton
import app.discair.ui.common.IndexButtonBody
import app.discair.ui.common.IndexButtonKind
import app.discair.ui.common.IndexGet
import app.discair.ui.common.IndexGetButton
import app.discair.ui.common.IndexIcons
import app.discair.ui.common.IndexInsightBlock
import app.discair.ui.common.IndexLabel
import app.discair.ui.common.IndexListsRules
import app.discair.ui.common.IndexMuted
import app.discair.ui.common.IndexPageHead
import app.discair.ui.common.IndexProgress
import app.discair.ui.common.IndexRule
import app.discair.ui.common.IndexRules
import app.discair.ui.common.IndexSectionHead
import app.discair.ui.common.IndexTabs
import app.discair.ui.common.IndexType
import app.discair.ui.common.LocalAcquisitions
import app.discair.ui.common.SaveState
import app.discair.ui.common.indexArrive
import app.discair.ui.common.indexGetOf
import app.discair.ui.common.rememberAlbumYear
import app.discair.ui.common.routeKey
import app.discair.ui.common.sharedCover
import app.discair.ui.home.IndexHomeRules
import app.discair.ui.theme.IndexMotion
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.rememberReducedMotion

/*
 * Index's Discover (Layout.Index). Spec: docs/INDEX_THEME.md step I4; mockup: docs/design/index/pages/discover.html, frames 1 and 2.
 * "Discover" with the entry count as a superscript, the lists as mono tabs (Insights is the last tab), then each list as numbered entries: "01" in mono
 * `accent`, a 96dp cover, the genre, the title, the maker and year, the reason, and Get / Save / X. Daily picks and Deep dives keep a section head per lens
 * or genre row. Insights: the Taste bars, the anniversary as the insight block, the other lenses as numbered rows. The data, saves, dismissals and Undo are
 * the page every theme has (DiscoverScreen).
 */

private val Gutter = IndexRules.GUTTER.dp

// ----- the head ------------------------------------------------------------------------------------------------

/** "Discover" with the count (when the list has loaded and is not empty), then the seven lists as tabs in [DiscoveryList] order (the swipe order). */
@Composable
internal fun IndexDiscoverHead(list: DiscoveryList, count: String?, onSelect: (DiscoveryList) -> Unit) {
    Column {
        IndexPageHead("Discover", Modifier.semantics { heading() }, count = count)
        IndexTabs(IndexListsRules.tabs, DiscoveryList.entries.indexOf(list), { onSelect(DiscoveryList.entries[it]) }, Modifier.padding(top = 12.dp))
    }
}

// ----- the lists -----------------------------------------------------------------------------------------------

/**
 * A list as numbered entries. A titled section (a lens of Daily picks, a genre row of Deep dives) opens with a section head and its count; a lens with
 * nothing says so in a muted line. [empty] is the whole-list note for a list with nothing at all. Numbers restart in each section, as the lens tabs do.
 */
@Composable
internal fun IndexDiscoverList(
    list: DiscoveryList, sections: List<FlowDiscoverRules.GridSection>, open: Opener, saves: Map<String, SaveState>, defaultSaved: Boolean,
    onSave: (DiscoveryEntry) -> Unit, onDismiss: (DiscoveryEntry, Boolean) -> Unit, empty: @Composable () -> Unit,
) {
    if (sections.all { it.title == null && it.entries.isEmpty() }) {
        empty()
        return
    }
    val reduced = rememberReducedMotion()
    // An album can sit in two lens sections; only its first entry carries the shared cover, so one key is never on the page twice.
    val sharedOwner = remember(sections) {
        buildMap { for (sec in sections) for (e in sec.entries) putIfAbsent(routeKey(e.item.artistName, e.item.album), FlowDiscoverRules.itemKey(sec, e)) }
    }
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 24.dp + LocalBottomClearance.current)) {
        var row = 0 // the first twelve rows on the page cascade in (motion #5), keyed on the list so a tab change replays it
        sections.forEachIndexed { s, section ->
            val title = section.title
            // The first head sits 16dp under the tabs' baseline, not the 28dp between sections.
            if (title != null) item(key = "h:$title") {
                IndexSectionHead(title, meta = GalleryListsRules.countLine(section.count), first = s == 0, modifier = if (s == 0) Modifier.padding(top = 16.dp) else Modifier)
            }
            section.note?.let { note -> item(key = "n:${section.title}") { IndexMuted(note, Modifier.padding(horizontal = Gutter, vertical = 10.dp)) } }
            val first = row
            row += section.entries.size
            items(section.entries.size, key = { FlowDiscoverRules.itemKey(section, section.entries[it]) }) { i ->
                val entry = section.entries[i]
                val albumKey = routeKey(entry.item.artistName, entry.item.album)
                IndexEntry(
                    entry, i, albumKey.takeIf { sharedOwner[it] == FlowDiscoverRules.itemKey(section, entry) }, open,
                    saves[entry.key] ?: if (defaultSaved) SaveState.Saved else SaveState.Idle, { onSave(entry) }, { artistToo -> onDismiss(entry, artistToo) },
                    Modifier.animateItem(fadeInSpec = null, placementSpec = IndexMotion.firm(260, reduced), fadeOutSpec = null).indexArrive(first + i, list),
                )
            }
        }
    }
}

/**
 * One entry (index.css: a row of 26 / 96 / 1fr, 14dp above and below, the 1dp rule under it): the number, the cover, then the genre in mono, the title (Inter
 * 600 16), the maker and year (tapping it opens the artist), the reason, and the actions. The cover and the title open the album.
 */
@Composable
private fun IndexEntry(
    entry: DiscoveryEntry, index: Int, sharedKey: String?, open: Opener, saveState: SaveState, onSave: () -> Unit, onDismiss: (artistToo: Boolean) -> Unit,
    modifier: Modifier = Modifier,
) {
    val p = LocalPalette.current
    val item = entry.item
    val artist = item.artistName
    val year = rememberAlbumYear(artist, item.album, item.year)
    val openAlbum = { open.album(routeKey(artist, item.album), artist, item.album, null, item.year) }
    Column(modifier.fillMaxWidth().padding(horizontal = Gutter)) {
        Row(Modifier.fillMaxWidth().padding(vertical = 14.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.Top) {
            Text(IndexListsRules.number(index), style = IndexType.label(), color = p.accent, maxLines = 1, modifier = Modifier.width(26.dp).padding(top = 2.dp))
            val cover = IndexListsRules.ENTRY_COVER_DP.dp
            AlbumCover(
                artist, item.album, null,
                Modifier.size(cover).aspectRatio(1f).then(if (sharedKey != null) Modifier.sharedCover(sharedKey) else Modifier)
                    .clickable(role = Role.Button, onClickLabel = "Open ${item.album}", onClick = openAlbum),
                rect = true,
            )
            Column(Modifier.weight(1f)) {
                GalleryListsRules.entryGenre(item.genres, item.genreRowLabel)?.let { IndexLabel(it) }
                Text(
                    item.album, Modifier.padding(top = 2.dp).clickable(role = Role.Button, onClick = openAlbum), color = p.text,
                    style = IndexType.rowTitle().copy(fontSize = 16.sp, lineHeight = 20.sp), maxLines = 2, overflow = TextOverflow.Ellipsis,
                )
                Text(
                    IndexListsRules.maker(artist, year), Modifier.clickable(role = Role.Button, onClickLabel = "Open $artist") { open.artist(artist, null, null, null) },
                    color = p.textMuted, style = IndexType.body().copy(fontSize = 13.sp, lineHeight = 18.sp), maxLines = 1, overflow = TextOverflow.Ellipsis,
                )
                GalleryListsRules.tileReason(pickReason(item.because, item.similarTo), item.reason, item.lens, item.seedTag, item.libraryAlbumCount, item.acquired)?.let {
                    Text(
                        it, Modifier.padding(top = 6.dp), color = p.text, style = IndexType.body().copy(fontWeight = FontWeight.Medium, fontSize = 13.sp, lineHeight = 18.sp),
                        maxLines = IndexListsRules.REASON_LINES, overflow = TextOverflow.Ellipsis,
                    )
                }
                Row(Modifier.padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                    EntryGet(entry)
                    val saved = saveState == SaveState.Saved
                    IndexButtonBody(
                        IndexButtonKind.Ghost, onSave,
                        Modifier.semantics { contentDescription = GalleryListsRules.saveDescription(item.album, saved, saveState == SaveState.Failed) },
                        enabled = saveState != SaveState.Pending, small = true, labelColor = if (saved) p.accent else null,
                    ) { Icon(IndexIcons.Bookmark, null, Modifier.size(IndexRules.ICON_INLINE.dp)) }
                    DismissMenu(entry, onDismiss)
                }
            }
        }
        IndexRule()
    }
}

/** Get for an entry: IN LIBRARY for an owned album, else the acquisition's state with the morph (motion #11). The request carries the entry as the server sent it. */
@Composable
private fun EntryGet(entry: DiscoveryEntry) {
    val hub = LocalAcquisitions.current
    val item = entry.item
    val state = if (item.acquired) IndexGet.Owned else indexGetOf(hub.getState(item.artistName, item.album))
    IndexGetButton(state, { hub.getAlbum(item.artistName, item.album, entry.raw) }, Modifier.semantics { contentDescription = "Get album ${item.album}" })
}

/** The X: one ghost square that opens the lettered sheet with both ways to say no (Not this album, Not this artist), then the More / Less like this items every theme offers. */
@Composable
private fun DismissMenu(entry: DiscoveryEntry, onDismiss: (artistToo: Boolean) -> Unit) {
    var menu by remember { mutableStateOf(false) }
    val item = entry.item
    val items = listOf(
        app.discair.ui.common.IndexMenuItem("Not this album", detail = "It leaves this list") { onDismiss(false) },
        app.discair.ui.common.IndexMenuItem("Not this artist", detail = "${item.artistName} leaves every list") { onDismiss(true) },
    ) + app.discair.ui.common.indexMenuItems(pickFeedbackActions(entry))
    Box {
        IndexButtonBody(
            IndexButtonKind.Ghost, { menu = true }, Modifier.semantics { contentDescription = IndexListsRules.dismissMenuDescription(item.album) },
            enabled = true, small = true,
        ) { Icon(IndexIcons.Close, null, Modifier.size(IndexRules.ICON_INLINE.dp)) }
        if (menu) app.discair.ui.common.IndexMenuSheet(
            items, onDismiss = { menu = false },
            header = app.discair.ui.common.IndexMenuHeader(item.album, item.artistName) {
                AlbumCover(item.artistName, item.album, null, Modifier.size(app.discair.ui.common.IndexSheetRules.HEADER_ART.dp), rect = true)
            },
        )
    }
}

// ----- insights ------------------------------------------------------------------------------------------------

/**
 * Insights (frame 2): the Taste section, then each lens in the server's order. An anniversary card is the insight block with its number; every other lens is
 * a section head with its count and numbered rows. The lenses that are off or have nothing today fold into one muted line. A dismissed card leaves at once
 * and [onDismiss] offers Undo.
 */
@Composable
internal fun IndexInsights(
    response: InsightsResponse, hidden: Set<String>, onDismiss: (InsightCard) -> Unit, taste: TasteResponse?, tasteLoaded: Boolean, showTaste: Boolean, open: Opener,
) {
    val reduced = rememberReducedMotion()
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(top = 6.dp, bottom = 24.dp + LocalBottomClearance.current)) {
        if (showTaste) item(key = "taste") { IndexTaste(taste?.profiles, tasteLoaded) }
        val off = mutableListOf<String>()
        val nothing = mutableListOf<String>()
        for (kind in lensKinds(response)) {
            val lens = response.lenses[kind]
            val cards = lens?.cards.orEmpty().filter { it.id !in hidden }
            when {
                lens?.enabled != true -> off += lensName(kind)
                cards.isEmpty() -> nothing += lensName(kind)
                kind == "anniversary" -> items(cards.size, key = { cards[it].id }) { i ->
                    Box(Modifier.animateItem(fadeInSpec = null, placementSpec = IndexMotion.firm(260, reduced), fadeOutSpec = null)) { Anniversary(cards[i], open, onDismiss) }
                }
                else -> {
                    item(key = "h:$kind") { IndexSectionHead(lensName(kind), meta = cards.size.toString()) }
                    items(cards.size, key = { cards[it].id }) { i ->
                        Box(Modifier.animateItem(fadeInSpec = null, placementSpec = IndexMotion.firm(260, reduced), fadeOutSpec = null).indexArrive(i, kind)) {
                            InsightRow(cards[i], i, open, onDismiss)
                        }
                    }
                }
            }
        }
        FlowDiscoverRules.insightsNote(off, nothing)?.let { note -> item(key = "note") { IndexMuted(note, Modifier.padding(horizontal = Gutter, vertical = 16.dp)) } }
    }
}

/** The anniversary as the insight block (the number from the title, as on Home), then Open album, Why this? and Dismiss. */
@Composable
private fun Anniversary(card: InsightCard, open: Opener, onDismiss: (InsightCard) -> Unit) {
    var why by remember(card.id) { mutableStateOf(false) }
    val artist = card.subject.artist
    val title = card.subject.title
    Column(Modifier.padding(top = 24.dp)) {
        IndexInsightBlock(
            "${GalleryListsRules.lensLine(lensName(card.kind), true)} · this week", listOf(card.title, card.body).filter { it.isNotBlank() }.joinToString(" "),
            Modifier.padding(horizontal = Gutter), numeral = IndexHomeRules.insightNumeral(card.title),
        )
        if (why) IndexMuted(InsightNarrative.why(card), Modifier.padding(horizontal = Gutter).padding(top = 10.dp))
        Row(Modifier.padding(start = Gutter, end = Gutter, top = 10.dp), horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
            // A card names an album but carries no library id, so the button opens the album page (where Play is) rather than guessing.
            if (artist != null && title != null) IndexButton("Open album", { open.album(routeKey(artist, title), artist, title, null, card.subject.year) }, icon = IndexIcons.Play, small = true)
            IndexButton(if (why) "Hide why" else "Why this?", { why = !why }, kind = IndexButtonKind.Ghost, small = true)
            if (card.dismissible) IndexButton("Dismiss", { onDismiss(card) }, Modifier.semantics { contentDescription = "Dismiss ${card.title}" }, kind = IndexButtonKind.Ghost, small = true)
        }
    }
}

/**
 * One card as a numbered row: the number, a 48dp cover, the title over the artist and the server's line, and a ghost Play square that opens the album.
 * Under it, "Missing" runs for a series, and the reason once Why this? is chosen; the three dots hold Why this? and Dismiss.
 */
@Composable
private fun InsightRow(card: InsightCard, index: Int, open: Opener, onDismiss: (InsightCard) -> Unit) {
    val p = LocalPalette.current
    var why by remember(card.id) { mutableStateOf(false) }
    val artist = card.subject.artist
    val title = card.subject.title
    val openAlbum: (() -> Unit)? = if (artist != null && title != null) { { open.album(routeKey(artist, title), artist, title, null, card.subject.year) } } else null
    Column(Modifier.fillMaxWidth().padding(horizontal = Gutter)) {
        Row(
            Modifier.fillMaxWidth().padding(vertical = 8.dp).then(if (openAlbum != null) Modifier.clickable(role = Role.Button, onClick = openAlbum) else Modifier),
            horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(IndexListsRules.number(index), style = IndexType.label(), color = p.accent, maxLines = 1, modifier = Modifier.width(26.dp))
            if (artist != null && title != null) AlbumCover(artist, title, null, Modifier.size(48.dp), rect = true)
            Column(Modifier.weight(1f).semantics(mergeDescendants = true) {}) {
                Text(card.title, color = p.text, style = IndexType.rowTitle(), maxLines = 2, overflow = TextOverflow.Ellipsis)
                val meta = listOfNotNull(artist, card.body.ifBlank { null }).joinToString(" · ")
                if (meta.isNotEmpty()) IndexLabel(meta, maxLines = 2)
            }
            if (openAlbum != null) IndexButtonBody(IndexButtonKind.Ghost, openAlbum, Modifier.semantics { contentDescription = "Open ${card.title}" }, enabled = true, small = true) {
                Icon(IndexIcons.Play, null, Modifier.size(IndexRules.ICON_INLINE.dp))
            }
            app.discair.ui.common.IndexMenuButton(
                "Options for ${card.title}",
                listOfNotNull(
                    app.discair.ui.common.IndexMenuItem(if (why) "Hide why" else "Why this?") { why = !why },
                    if (card.dismissible) app.discair.ui.common.IndexMenuItem("Dismiss") { onDismiss(card) } else null,
                ),
                size = 20.dp,
            )
        }
        for (run in card.missingRuns) {
            val span = if (run.firstPosition == run.lastPosition) "${run.firstPosition}" else "${run.firstPosition} to ${run.lastPosition}"
            IndexMuted("Missing $span" + if (run.labels.isEmpty()) "" else ": " + run.labels.joinToString(", "), Modifier.padding(start = 38.dp, bottom = 6.dp))
        }
        if (why) IndexMuted(InsightNarrative.why(card), Modifier.padding(start = 38.dp, bottom = 8.dp))
        IndexRule()
    }
}

// ----- taste ---------------------------------------------------------------------------------------------------

/**
 * The Taste section (frame 2): "Taste" with the window as its meta word and Details as the link, the window's top four genres as ranked bars, then the listen
 * counts. Empty and thin profiles say so in words (thin with a progress line). Details opens the same full-picture sheet every theme has.
 */
@Composable
internal fun IndexTaste(profiles: TasteProfiles?, loaded: Boolean) {
    val p = LocalPalette.current
    var sheet by remember { mutableStateOf(false) }
    val state = TasteCard.state(profiles)
    IndexSectionHead(
        "Taste", meta = if (state is TasteCardState.Ready) IndexListsRules.tasteMeta(TasteCard.windowLabel(state.headline.window, profiles?.recentDays ?: 90)) else null,
        link = if (state !is TasteCardState.Empty && profiles != null) "Details" else null, onLink = { sheet = true }, first = true, modifier = Modifier.padding(top = 18.dp),
    )
    Column(Modifier.fillMaxWidth().padding(horizontal = Gutter)) {
        when (state) {
            TasteCardState.Empty -> {
                Text(if (loaded) "Taste needs listening history." else "Reading your saved profile.", color = p.text, style = IndexType.rowTitle())
                if (loaded) IndexMuted("Connect ListenBrainz or keep playing. Once a window has enough listens I will start describing it.", Modifier.padding(top = 4.dp))
            }
            is TasteCardState.Thin -> {
                Text("Still getting to know you.", color = p.text, style = IndexType.rowTitle())
                IndexMuted("Only ${state.have} listens in the recent window. I won't call a shift until there are ${state.need}.", Modifier.padding(top = 4.dp))
                IndexProgress(TasteCard.progress(state.have, state.need).toFloat(), Modifier.padding(top = 10.dp).semantics { contentDescription = "${state.have} of ${state.need} listens needed" })
            }
            is TasteCardState.Ready -> {
                Text(state.headline.text, Modifier.padding(bottom = 10.dp), color = p.text, style = IndexType.body(), maxLines = 3, overflow = TextOverflow.Ellipsis)
                val w = profiles?.window(state.headline.window)
                val top = if (w == null || w.isLowSample("genre")) emptyList() else w.entries("genre").take(GalleryListsRules.BARS_SHOWN)
                if (top.isNotEmpty()) IndexBars(top)
                IndexLabel(GalleryListsRules.listensLine(state.windowListens, state.allTimeListens), Modifier.padding(top = 10.dp))
            }
        }
    }
    if (sheet && profiles != null) TasteSheet(profiles) { sheet = false }
}

/**
 * Ranked bars (index.css: 96 / 1fr / 40): the genre in Inter 500 13, a 6dp `chart3` track with the share in `chart2` (the first in `accent`; the longest fills
 * 85% of the track), and the percent in mono. [sketch] draws every share in `chart2`: a low-sample window is a sketch, not a finding.
 */
@Composable
internal fun IndexBars(entries: List<TasteEntry>, sketch: Boolean = false, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    val top = entries.maxOfOrNull { it.share } ?: 0.0
    Column(modifier, verticalArrangement = Arrangement.spacedBy(8.dp)) {
        for ((i, e) in entries.withIndex()) {
            val pct = TasteCard.percent(e.share)
            val fraction = FlowPagesRules.barFraction(e.share, top)
            val fill = if (i == 0 && !sketch) p.accent else p.chart2
            Row(
                Modifier.fillMaxWidth().semantics(mergeDescendants = true) { contentDescription = "${e.value}, $pct percent" },
                horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(e.value, Modifier.width(96.dp), color = p.text, style = IndexType.body().copy(fontWeight = FontWeight.Medium, fontSize = 13.sp, lineHeight = 18.sp), maxLines = 1, overflow = TextOverflow.Ellipsis)
                Box(Modifier.weight(1f).height(6.dp).background(p.chart3).drawBehind { drawRect(fill, size = Size(size.width * fraction, size.height)) })
                IndexLabel("$pct%", Modifier.width(40.dp))
            }
        }
    }
}
