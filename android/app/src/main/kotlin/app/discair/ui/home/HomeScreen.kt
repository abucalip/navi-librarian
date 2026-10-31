package app.discair.ui.home

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.data.Shelves
import app.discair.model.GenreTile
import app.discair.model.Pick
import app.discair.model.ShelfAlbum
import app.discair.ui.Opener
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.CheckBadge
import app.discair.ui.common.Load
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.PageHeading
import app.discair.ui.common.Panel
import app.discair.ui.common.Target
import app.discair.ui.common.aspectSquare
import app.discair.ui.common.genreHue
import app.discair.ui.common.plural
import app.discair.ui.common.rememberLoad
import app.discair.ui.common.routeKey
import app.discair.ui.theme.Display
import app.discair.ui.theme.Ink
import app.discair.ui.theme.Mono
import kotlinx.coroutines.launch

private const val GENRES_SHOWN = 12
private const val GENRES_PER_LINE = 4
private const val GENRES_MAX = 60

@Composable
fun HomeScreen(open: Opener) {
    val repo = LocalRepository.current
    val picks = rememberLoad("picks") { repo.picks(10).items }
    val genres = rememberLoad("genres") { repo.genres().items }
    var showAllGenres by remember { mutableStateOf(false) }
    LazyColumn(Modifier.fillMaxWidth(), contentPadding = PaddingValues(top = 12.dp, bottom = 24.dp)) {
        // The web hides this heading on a phone; it stays for screen readers.
        item {
            Text("Recommended", Modifier.size(1.dp).semantics { heading() }, color = Color.Transparent)
        }
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
            Row(
                Modifier.fillMaxWidth().padding(start = 16.dp, end = 8.dp, top = 24.dp, bottom = 8.dp),
                verticalAlignment = Alignment.Bottom,
            ) {
                PageHeading("Genres", Modifier.weight(1f))
                val ready = (genres.state as? Load.Ready)?.value
                if (ready != null && ready.size > GENRES_SHOWN && !showAllGenres) {
                    TextButton(onClick = { showAllGenres = true }, Modifier.heightIn(min = Target)) {
                        Text("View more", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }
        item {
            when (val state = genres.state) {
                Load.Loading -> Muted("Loading…")
                is Load.Failed -> Inline(state.failure.message, genres.reload)
                is Load.Ready -> GenreGrid(state.value, open, if (showAllGenres) GENRES_MAX else GENRES_SHOWN)
            }
        }
        for (shelf in listOf(Shelves.Newest to "Newly added", Shelves.Recent to "Recently played", Shelves.Frequent to "Most played")) {
            item(key = shelf.first.path) { ShelfRow(shelf.first, shelf.second, open) }
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
    Row(Modifier.height(22.dp).background(Ink.Raised)) {
        Box(Modifier.width(3.dp).fillMaxHeight().background(Ink.Accent))
        Text(
            text.uppercase(), style = MaterialTheme.typography.labelSmall,
            modifier = Modifier.padding(horizontal = 6.dp, vertical = 3.dp),
        )
    }
}

/**
 * The phone strip from the mobile web: swipeable cards, one per page, centred, with a dot for each
 * and no arrows or count. The dots are buttons, so the strip never depends on swiping alone.
 */
@Composable
private fun Recommended(items: List<Pick>, open: Opener) {
    val pager = rememberPagerState { items.size }
    val scope = rememberCoroutineScope()
    Column {
        HorizontalPager(pager, Modifier.fillMaxWidth(), contentPadding = PaddingValues(horizontal = 12.dp), pageSpacing = 8.dp) { page ->
            val pick = items[page]
            var tint by remember(pick) { mutableStateOf<Color?>(null) }
            Column(
                Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp))
                    .background(tint?.let { lerp(Ink.Surface, it, 0.7f) } ?: Ink.Surface)
                    .clickable { open.album(routeKey(pick.artist, pick.album), pick.artist, pick.album, null, pick.year) }
                    .padding(vertical = 16.dp, horizontal = 16.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                AlbumCover(pick.artist, pick.album, null, Modifier.fillMaxWidth(0.6f).aspectSquare(), onColor = { tint = it })
                Spacer(Modifier.size(12.dp))
                TagChip(pickTag(pick.dashboardCategory))
                Text(
                    pick.album, style = MaterialTheme.typography.headlineMedium, textAlign = TextAlign.Center,
                    maxLines = 2, overflow = TextOverflow.Ellipsis, modifier = Modifier.padding(top = 6.dp),
                )
                Text(
                    pick.artist, style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant, textAlign = TextAlign.Center,
                    maxLines = 1, overflow = TextOverflow.Ellipsis,
                )
                val extra = listOfNotNull(
                    pick.year?.toString(),
                    pick.listeners?.takeIf { it > 0 }?.let { "%,d listeners".format(it) },
                ).joinToString(" · ")
                if (extra.isNotEmpty()) Text(extra, style = MaterialTheme.typography.labelMedium, color = Ink.Accent)
            }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
            items.indices.forEach { index ->
                val current = pager.currentPage == index
                Box(
                    // 32dp wide so ten dots fit a 360dp phone; still 48dp tall. Each dot is a button.
                    Modifier.size(width = 32.dp, height = Target)
                        .clickable { scope.launch { pager.animateScrollToPage(index) } }
                        .semantics {
                            contentDescription = "Show album ${index + 1} of ${items.size}"
                            selected = current
                        },
                    contentAlignment = Alignment.Center,
                ) {
                    Box(
                        Modifier.size(8.dp).clip(CircleShape).background(
                            if (current) MaterialTheme.colorScheme.primary else Ink.TextMuted.copy(alpha = 0.3f),
                        ),
                    )
                }
            }
        }
    }
}

/** Genre tiles as on the web phone: a name and a coloured left bar, four to a line. Counts go in the spoken label. */
@Composable
private fun GenreGrid(all: List<GenreTile>, open: Opener, limit: Int) {
    val tiles = all.take(minOf(limit, GENRES_MAX))
    Column(Modifier.padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        tiles.chunked(GENRES_PER_LINE).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                row.forEach { genre ->
                    val bar = Color.hsl(genreHue(genre.tag).toFloat(), 0.55f, 0.55f)
                    Row(
                        Modifier.weight(1f).heightIn(min = Target)
                            .clip(RoundedCornerShape(6.dp))
                            .background(MaterialTheme.colorScheme.surfaceVariant)
                            .clickable { open.genre(genre.tag, genre.name) }
                            .semantics { contentDescription = "${genre.name}, " + plural(genre.albumCount, "album") },
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Box(Modifier.width(4.dp).heightIn(min = Target).fillMaxHeight().background(bar))
                        Text(
                            genre.name, style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurface, maxLines = 1,
                            overflow = TextOverflow.Ellipsis, modifier = Modifier.padding(horizontal = 6.dp),
                        )
                    }
                }
                repeat(GENRES_PER_LINE - row.size) { Spacer(Modifier.weight(1f)) }
            }
        }
    }
}

@Composable
private fun ShelfRow(shelf: Shelves, title: String, open: Opener) {
    val repo = LocalRepository.current
    val loaded = rememberLoad(shelf) { repo.shelf(shelf, 20).items }
    PageHeading(title, Modifier.padding(start = 16.dp, end = 16.dp, top = 24.dp, bottom = 8.dp))
    when (val state = loaded.state) {
        Load.Loading -> Muted("Loading…")
        is Load.Failed -> Inline(state.failure.message, loaded.reload)
        is Load.Ready -> if (state.value.isEmpty()) Muted("Nothing here yet.") else LazyRow(
            contentPadding = PaddingValues(horizontal = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            items(state.value, key = { it.id }) { album: ShelfAlbum ->
                Panel(Modifier.width(208.dp).clickable {
                    open.album(routeKey(album.artist, album.name), album.artist, album.name, album.id, album.year)
                }) {
                    Column {
                        Box {
                            AlbumCover(album.artist, album.name, album.artworkUrl, Modifier.fillMaxWidth().aspectSquare(), rect = true)
                            if (album.owned) CheckBadge(Modifier.align(Alignment.BottomEnd).padding(8.dp))
                        }
                        Column(Modifier.padding(12.dp).heightIn(min = 76.dp)) {
                            Text(
                                album.name, style = MaterialTheme.typography.titleLarge.copy(fontFamily = Display),
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
