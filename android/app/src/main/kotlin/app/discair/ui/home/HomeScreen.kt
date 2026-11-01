package app.discair.ui.home

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.ui.semantics.Role
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.PlatformTextStyle
import androidx.compose.ui.text.style.LineHeightStyle
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.data.Shelves
import app.discair.model.GenreTile
import app.discair.model.Pick
import app.discair.model.ShelfAlbum
import app.discair.ui.Opener
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.GetAlbumButton
import app.discair.ui.common.pageMetadata
import app.discair.ui.common.CheckBadge
import app.discair.ui.common.Load
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.PageHeading
import app.discair.ui.common.Panel
import app.discair.ui.common.Target
import app.discair.ui.common.aspectSquare
import app.discair.ui.common.genreHue
import app.discair.ui.common.plural
import app.discair.ui.common.rememberAlbumYear
import app.discair.ui.common.rememberLoad
import app.discair.ui.common.routeKey
import app.discair.ui.theme.Ink
import app.discair.ui.theme.Mono
import kotlinx.coroutines.launch

/** The genre row shows this many, drawn at random each time Home opens. */
private const val GENRES_SHOWN = 6

@Composable
fun HomeScreen(open: Opener) {
    val repo = LocalRepository.current
    val picks = rememberLoad("picks") { repo.picks(10).items }
    val genres = rememberLoad("genres") { repo.genres().items }
    LazyColumn(Modifier.fillMaxWidth(), contentPadding = PaddingValues(top = 12.dp, bottom = 24.dp)) {
        item { PageHeading("For you", Modifier.padding(start = 16.dp, end = 16.dp, bottom = 8.dp)) }
        item {
            Box(Modifier.heightIn(min = 120.dp)) {
                when (val state = picks.state) {
                    Load.Loading -> Muted("Loading…")
                    is Load.Failed -> Inline(state.failure.message, picks.reload)
                    is Load.Ready ->
                        if (state.value.isEmpty()) Muted("Nothing recommended right now.")
                        else Recommended(state.value, open)
                }
            }
        }
        item {
            PageHeading("Genres", Modifier.padding(start = 16.dp, end = 16.dp, top = 24.dp, bottom = 8.dp))
        }
        item {
            when (val state = genres.state) {
                Load.Loading -> Muted("Loading…")
                is Load.Failed -> Inline(state.failure.message, genres.reload)
                is Load.Ready -> GenreRow(state.value, open)
            }
        }
        item(key = "new_releases") { ShelfRow("new_releases", "New releases", open) { repo.newReleases() } }
        for (shelf in listOf(Shelves.Newest to "Newly added", Shelves.Recent to "Recently played", Shelves.Frequent to "Most played")) {
            item(key = shelf.first.path) { ShelfRow(shelf.first.path, shelf.second, open) { repo.shelf(shelf.first, 20).items } }
        }
    }
}

@Composable
private fun Muted(text: String) {
    Text(text, Modifier.padding(horizontal = 16.dp, vertical = 8.dp), color = MaterialTheme.colorScheme.onSurfaceVariant)
}

@Composable
private fun Inline(message: String, retry: () -> Unit) {
    Column(Modifier.padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(message, color = Ink.ChartRedText, style = MaterialTheme.typography.bodyMedium)
        OutlinedButton(onClick = retry, Modifier.heightIn(min = Target)) { Text("Try again") }
    }
}

/** The label over a pick: the phone layout shortens the two list names to one word, as the web does. */
private fun pickTag(label: String): String = when {
    label.isBlank() -> "discovery"
    Regex("discover", RegexOption.IGNORE_CASE).containsMatchIn(label) -> "discovery"
    Regex("deep dive", RegexOption.IGNORE_CASE).containsMatchIn(label) -> "deep dive"
    else -> label
}

/** The tag chip: mono capitals on a dark ground with a yellow bar on its left edge. */
@Composable
private fun TagChip(text: String) {
    Row(Modifier.height(22.dp).background(Ink.Raised), verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.width(3.dp).fillMaxHeight().background(Ink.Accent))
        // Line height is trimmed evenly above and below the capitals, so the text sits in the middle of the chip.
        Text(
            text.uppercase(),
            style = MaterialTheme.typography.labelSmall.copy(
                lineHeightStyle = LineHeightStyle(LineHeightStyle.Alignment.Center, LineHeightStyle.Trim.Both),
                platformStyle = PlatformTextStyle(includeFontPadding = false),
            ),
            modifier = Modifier.padding(horizontal = 6.dp),
        )
    }
}

/**
 * The phone strip: swipeable cards, one per page, with the position ("3/10") in the top-left corner.
 * The Get cloud sits on the cover's bottom-left corner. Under the cover come the artist's first
 * one or two genres in small grey text; the year (accent) and the listener count (grey) follow the artist.
 */
@Composable
private fun Recommended(items: List<Pick>, open: Opener) {
    val pager = rememberPagerState { items.size }
    HorizontalPager(pager, Modifier.fillMaxWidth(), contentPadding = PaddingValues(horizontal = 12.dp), pageSpacing = 8.dp) { page ->
        val pick = items[page]
        var tint by remember(pick) { mutableStateOf<Color?>(null) }
        Box(
            Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp))
                .background(tint?.let { lerp(Ink.Surface, it, 0.7f) } ?: Ink.Surface)
                .clickable(role = Role.Button) { open.album(routeKey(pick.artist, pick.album), pick.artist, pick.album, null, pick.year) },
        ) {
            Column(
                Modifier.fillMaxWidth().padding(vertical = 16.dp, horizontal = 16.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Box(Modifier.fillMaxWidth(0.6f)) {
                    AlbumCover(pick.artist, pick.album, null, Modifier.fillMaxWidth().aspectSquare(), onColor = { tint = it })
                    Box(
                        Modifier.align(Alignment.BottomStart).padding(4.dp).clip(CircleShape)
                            .background(Color.Black.copy(alpha = 0.55f)),
                    ) { GetAlbumButton(pick.artist, pick.album, pageMetadata(pick.artist, pick.album, pick.year)) }
                }
                val tags = pick.genres.filter { it.isNotBlank() }.take(2).joinToString(" · ")
                if (tags.isNotEmpty()) Text(
                    tags, style = MaterialTheme.typography.labelSmall, color = Ink.TextMuted,
                    maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.padding(top = 6.dp),
                )
                Spacer(Modifier.size(8.dp))
                TagChip(pickTag(pick.dashboardCategory))
                Text(
                    pick.album, style = MaterialTheme.typography.headlineMedium, textAlign = TextAlign.Center,
                    maxLines = 2, overflow = TextOverflow.Ellipsis, modifier = Modifier.padding(top = 6.dp),
                )
                Text(
                    pick.artist, style = MaterialTheme.typography.bodyLarge,
                    color = Ink.Text, textAlign = TextAlign.Center,
                    maxLines = 1, overflow = TextOverflow.Ellipsis,
                )
                val listeners = pick.listeners?.takeIf { it > 0 }?.let { "%,d listeners".format(it) }
                val year = rememberAlbumYear(pick.artist, pick.album, pick.year)
                if (year != null || listeners != null) Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    year?.let { Text("$it", style = MaterialTheme.typography.labelMedium, color = Ink.Accent) }
                    listeners?.let { Text(it, style = MaterialTheme.typography.labelMedium, color = Ink.TextMuted) }
                }
            }
            Text(
                "${page + 1}/${items.size}", style = MaterialTheme.typography.labelSmall, color = Ink.TextMuted,
                modifier = Modifier.align(Alignment.TopEnd).padding(end = 12.dp, top = 10.dp)
                    .semantics { contentDescription = "Album ${page + 1} of ${items.size}" },
            )
        }
    }
}

/** A slideable row of genre tiles: the name only. A new random few each time Home opens. */
@Composable
private fun GenreRow(all: List<GenreTile>, open: Opener) {
    val tiles = remember(all) { all.shuffled().take(GENRES_SHOWN) }
    LazyRow(contentPadding = PaddingValues(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        items(tiles, key = { it.tag }) { genre ->
            Row(
                Modifier.heightIn(min = Target)
                    .clip(RoundedCornerShape(6.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant)
                    .clickable(role = Role.Button) { open.genre(genre.tag, genre.name) }
                    .semantics { contentDescription = "${genre.name}, " + plural(genre.albumCount, "album") },
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    genre.name, style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface, maxLines = 1,
                    overflow = TextOverflow.Ellipsis, modifier = Modifier.padding(horizontal = 12.dp),
                )
            }
        }
    }
}

@Composable
private fun ShelfRow(shelf: String, title: String, open: Opener, load: () -> List<ShelfAlbum>) {
    val loaded = rememberLoad(shelf) { load() }
    PageHeading(title, Modifier.padding(start = 16.dp, end = 16.dp, top = 24.dp, bottom = 8.dp))
    when (val state = loaded.state) {
        Load.Loading -> Muted("Loading…")
        is Load.Failed -> Inline(state.failure.message, loaded.reload)
        is Load.Ready -> if (state.value.isEmpty()) Muted("Nothing here yet.") else LazyRow(
            contentPadding = PaddingValues(horizontal = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            items(state.value, key = { it.id.ifBlank { it.artist + '/' + it.name } }) { album: ShelfAlbum ->
                Panel(Modifier.width(208.dp).clickable(role = Role.Button) {
                    open.album(routeKey(album.artist, album.name), album.artist, album.name, album.id, album.year)
                }) {
                    Column {
                        Box {
                            AlbumCover(album.artist, album.name, album.artworkUrl, Modifier.fillMaxWidth().aspectSquare(), rect = true)
                            if (album.owned) CheckBadge(Modifier.align(Alignment.BottomEnd).padding(8.dp))
                        }
                        Column(Modifier.padding(12.dp).heightIn(min = 76.dp)) {
                            Text(
                                album.name, style = MaterialTheme.typography.titleLarge,
                                maxLines = 2, overflow = TextOverflow.Ellipsis,
                            )
                            album.year?.let {
                                Text("$it", style = MaterialTheme.typography.labelMedium.copy(fontFamily = Mono), color = Ink.Accent)
                            }
                            if (album.artist.isNotBlank()) Text(
                                album.artist, style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis,
                            )
                        }
                    }
                }
            }
        }
    }
}

/** The New releases shelf: the discovery list in the server's order, cards without an owned cover. */
private fun app.discair.data.LibraryRepository.newReleases(): List<ShelfAlbum> =
    discovery("new_releases", 20).entries.distinctBy { it.key }.map {
        ShelfAlbum(name = it.item.album, artist = it.item.artistName, year = it.item.year, owned = false)
    }
