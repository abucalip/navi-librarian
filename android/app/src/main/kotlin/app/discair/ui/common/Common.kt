package app.discair.ui.common

import android.graphics.Bitmap
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.ui.semantics.Role
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.data.LibraryRepository
import app.discair.data.ReadMode
import app.discair.net.ConnectionFailure
import app.discair.net.classifyException
import app.discair.ui.theme.Ink
import coil3.ImageLoader
import coil3.compose.AsyncImage
import coil3.toBitmap
import kotlin.coroutines.cancellation.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

val LocalRepository = compositionLocalOf<LibraryRepository> { error("No repository") }
val LocalImageLoader = compositionLocalOf<ImageLoader> { error("No image loader") }

val Target = 48.dp

/**
 * Cover, bio and year lookups are cosmetic and some are slow (they reach other catalogues), so they
 * share a few threads. That leaves the connection free for the page data the screen is waiting on.
 */
@OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
val LookupDispatcher = Dispatchers.IO.limitedParallelism(3)

/** Years come from a rate-limited catalogue: one at a time, as on the web. */
@OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
val YearDispatcher = Dispatchers.IO.limitedParallelism(1)

/** The release year of an album: [known] when the list had it, otherwise looked up once and remembered. */
@Composable
fun rememberAlbumYear(artist: String, album: String, known: Int?): Int? {
    val repo = LocalRepository.current
    val year by produceState(known, artist, album, known) {
        if (known == null) value = withContext(YearDispatcher) { repo.albumYear(artist, album) }
    }
    return year
}

// ---- Loading

sealed interface Load<out T> {
    data object Loading : Load<Nothing>
    data class Ready<T>(val value: T) : Load<T>
    data class Failed(val failure: ConnectionFailure) : Load<Nothing>
}

class Loaded<T>(val state: Load<T>, val reload: () -> Unit)

/**
 * Runs [block] off the main thread whenever [keys] change or [Loaded.reload] is called. A saved copy of
 * the answer, if there is one, is shown at once; the server's answer then replaces it. If the server
 * cannot be read while a saved copy is showing, the copy stays.
 */
@Composable
fun <T> rememberLoad(vararg keys: Any?, block: () -> T): Loaded<T> {
    var attempt by remember { mutableIntStateOf(0) }
    val state by produceState<Load<T>>(Load.Loading, keys.toList(), attempt) {
        value = Load.Loading
        withContext(Dispatchers.IO) {
            val saved = try {
                ReadMode.only(true, block)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                null
            }
            if (saved != null) value = Load.Ready(saved)
            value = try {
                Load.Ready(block())
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                if (saved != null) Load.Ready(saved) else Load.Failed(classifyException(e, networkAvailable = true))
            }
        }
    }
    return Loaded(state) { attempt++ }
}

/**
 * Like [rememberLoad], for a page that arrives in pieces: [block] calls its argument with the page so far,
 * and the first call replaces the spinner. A failure after something has shown leaves what is on screen.
 */
@Composable
fun <T> rememberStreamLoad(vararg keys: Any?, block: (onPage: (T) -> Unit) -> Unit): Loaded<T> {
    var attempt by remember { mutableIntStateOf(0) }
    val state by produceState<Load<T>>(Load.Loading, keys.toList(), attempt) {
        value = Load.Loading
        withContext(Dispatchers.IO) {
            try {
                ReadMode.only(true) { block { page -> value = Load.Ready(page) } }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                // No saved copy: the spinner stays until the server answers.
            }
            try {
                block { page -> value = Load.Ready(page) }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                if (value !is Load.Ready<*>) value = Load.Failed(classifyException(e, networkAvailable = true))
            }
        }
    }
    return Loaded(state) { attempt++ }
}

/** Shows progress, an error with Retry, or the content. */
@Composable
fun <T> LoadView(loaded: Loaded<T>, modifier: Modifier = Modifier, content: @Composable (T) -> Unit) {
    when (val s = loaded.state) {
        Load.Loading -> Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator(Modifier.semantics { contentDescription = "Loading" })
        }
        is Load.Failed -> ErrorBlock(s.failure, loaded.reload, modifier)
        is Load.Ready -> content(s.value)
    }
}

@Composable
fun ErrorBlock(failure: ConnectionFailure, retry: () -> Unit, modifier: Modifier = Modifier) {
    Column(
        modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(failure.message, style = MaterialTheme.typography.bodyLarge, color = Ink.ChartRedText)
        Spacer(Modifier.size(16.dp))
        OutlinedButton(onClick = retry, Modifier.heightIn(min = Target)) { Text("Try again") }
    }
}

// ---- Images

private val placeholder = RoundedCornerShape(4.dp)

@Composable
fun Cover(
    model: String?,
    modifier: Modifier = Modifier,
    circle: Boolean = false,
    rect: Boolean = false,
    onColor: ((Color) -> Unit)? = null,
) {
    val shape = if (circle) CircleShape else if (rect) androidx.compose.ui.graphics.RectangleShape else placeholder
    Box(modifier.clip(shape).background(MaterialTheme.colorScheme.surfaceVariant)) {
        if (model != null) {
            AsyncImage(
                model = model,
                contentDescription = null, // decorative: the title next to it carries the meaning
                imageLoader = LocalImageLoader.current,
                contentScale = ContentScale.Crop,
                onSuccess = { state -> if (onColor != null) dominantColor(state.result.image)?.let(onColor) },
                modifier = Modifier.fillMaxSize(),
            )
        }
    }
}

/**
 * The cover's colour, kept dark so text stays readable, as on the web pages. Saturated pixels count
 * more than grey ones, so a mostly-white sleeve with a red logo still reads red.
 */
fun dominantColor(image: coil3.Image): Color? = try {
    val small = Bitmap.createScaledBitmap(image.toBitmap(), 16, 16, true)
    var r = 0.0; var g = 0.0; var b = 0.0; var weight = 0.0
    val hsv = FloatArray(3)
    for (x in 0 until 16) for (y in 0 until 16) {
        val px = small.getPixel(x, y)
        android.graphics.Color.colorToHSV(px, hsv)
        val w = 0.05 + hsv[1] * hsv[2]
        r += android.graphics.Color.red(px) * w; g += android.graphics.Color.green(px) * w
        b += android.graphics.Color.blue(px) * w; weight += w
    }
    android.graphics.Color.colorToHSV(
        android.graphics.Color.rgb((r / weight).toInt(), (g / weight).toInt(), (b / weight).toInt()), hsv,
    )
    Color.hsv(hsv[0], hsv[1].coerceAtMost(0.85f), hsv[2].coerceAtMost(0.4f))
} catch (e: Exception) {
    null
}

/** The page background: the cover colour at the top, fading to the page ground. */
@Composable
fun TintedPage(
    tint: Color?,
    list: androidx.compose.foundation.lazy.LazyListState,
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit,
) {
    val fade = with(androidx.compose.ui.platform.LocalDensity.current) { 720.dp.toPx() }
    Box(
        modifier.fillMaxSize().drawBehind {
            drawRect(Ink.Ink)
            if (tint != null) {
                // The tint scrolls away with the page, as on the web.
                val scrolled = if (list.firstVisibleItemIndex > 0) fade else list.firstVisibleItemScrollOffset.toFloat()
                drawRect(Brush.verticalGradient(listOf(tint, Ink.Ink), startY = -scrolled, endY = fade - scrolled))
            }
        },
    ) { content() }
}

/** Owned albums use the server-relative cover; others are looked up by name, once per session. */
@Composable
fun AlbumCover(
    artist: String,
    album: String,
    ownedPath: String?,
    modifier: Modifier = Modifier,
    rect: Boolean = false,
    onColor: ((Color) -> Unit)? = null,
) {
    val repo = LocalRepository.current
    val url by produceState<String?>(ownedPath?.let(repo::absolute), artist, album, ownedPath) {
        value = ownedPath?.let(repo::absolute)
            ?: withContext(LookupDispatcher) { repo.albumImage(artist, album) }
    }
    Cover(url, modifier, rect = rect, onColor = onColor)
}

@Composable
fun ArtistPhoto(
    name: String,
    ownedPath: String?,
    modifier: Modifier = Modifier,
    circle: Boolean = false,
    onColor: ((Color) -> Unit)? = null,
) {
    val repo = LocalRepository.current
    val url by produceState<String?>(null, name, ownedPath) {
        value = withContext(LookupDispatcher) { repo.artistImage(name) } ?: ownedPath?.let(repo::absolute)
    }
    Cover(url, modifier, circle, onColor = onColor)
}

// ---- Shared pieces

@Composable
fun Heading(text: String, modifier: Modifier = Modifier) {
    Text(
        text,
        style = MaterialTheme.typography.titleMedium,
        modifier = modifier.padding(top = 24.dp, bottom = 8.dp).semantics { heading() },
    )
}

/** A name that opens its page (LIB-01). At least 48dp tall so it can be hit. */
@Composable
fun NameLink(text: String, onClick: () -> Unit, modifier: Modifier = Modifier, maxLines: Int = 1) {
    Text(
        text,
        style = MaterialTheme.typography.bodyLarge,
        color = MaterialTheme.colorScheme.primary,
        maxLines = maxLines,
        overflow = TextOverflow.Ellipsis,
        modifier = modifier.defaultMinSize(minHeight = Target).clickable(role = Role.Button, onClick = onClick)
            .padding(vertical = 12.dp),
    )
}

@Composable
fun OwnedMark(owned: Boolean, modifier: Modifier = Modifier) {
    if (owned) Icon(
        Icons.Default.Check,
        contentDescription = "In your library",
        tint = Ink.Ok,
        modifier = modifier.size(20.dp),
    )
}

@Composable
fun BackBar(onBack: () -> Unit, title: String? = null) {
    Row(Modifier.fillMaxWidth().heightIn(min = 56.dp), verticalAlignment = Alignment.CenterVertically) {
        IconButton(onClick = onBack, Modifier.size(Target)) {
            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
        }
        if (title != null) {
            Text(title, style = MaterialTheme.typography.titleMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
    }
}

/** Body text clamped to [lines] with a Read more / Show less toggle, as on the web pages. */
@Composable
fun ReadMore(text: String, modifier: Modifier = Modifier, lines: Int = 3) {
    var expanded by remember { mutableStateOf(false) }
    var overflows by remember { mutableStateOf(false) }
    Column(modifier) {
        Text(
            text,
            style = MaterialTheme.typography.bodyMedium,
            maxLines = if (expanded) Int.MAX_VALUE else lines,
            overflow = TextOverflow.Ellipsis,
            onTextLayout = { if (!expanded) overflows = it.hasVisualOverflow },
        )
        if (overflows || expanded) {
            androidx.compose.material3.TextButton(
                onClick = { expanded = !expanded },
                modifier = Modifier.defaultMinSize(minHeight = Target),
            ) { Text(if (expanded) "Show less" else "Read more") }
        }
    }
}

/** Circular artist photo with the name under it, for similar-artist rows. */
@Composable
fun ArtistCircle(
    name: String,
    ownedPath: String?,
    owned: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier.clickable(role = Role.Button, onClick = onClick).padding(4.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        ArtistPhoto(name, ownedPath, Modifier.fillMaxWidth().aspectSquare(), circle = true)
        Text(
            name, style = MaterialTheme.typography.labelLarge, textAlign = androidx.compose.ui.text.style.TextAlign.Center,
            modifier = Modifier.padding(top = 6.dp),
        )
        if (owned) Text("In your library", style = MaterialTheme.typography.bodySmall, color = Ink.Ok)
    }
}

fun Modifier.aspectSquare(): Modifier = this.aspectRatio(1f)

/** Album card for shelves and grids. */
@Composable
fun AlbumCard(
    title: String,
    subtitle: String,
    artist: String,
    ownedPath: String?,
    owned: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier.clickable(role = Role.Button, onClick = onClick).padding(4.dp)) {
        Box {
            AlbumCover(artist, title, ownedPath, Modifier.fillMaxWidth().aspectSquare())
        }
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(top = 6.dp)) {
            Text(
                title, style = MaterialTheme.typography.labelLarge, maxLines = 2,
                overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f, fill = false),
            )
            if (owned) {
                Spacer(Modifier.size(4.dp))
                OwnedMark(true)
            }
        }
        Text(
            subtitle, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 1, overflow = TextOverflow.Ellipsis,
        )
    }
}

/** The hue of a genre tile's left bar. Same hash as `genreTileHue` in static/app.js so the two clients agree. */
fun genreHue(tag: String): Int {
    var hash = 0
    tag.codePoints().forEach { hash = (hash * 31 + it) % 360 }
    return hash
}

fun plural(n: Int, one: String, many: String = one + "s") = if (n == 1) "1 $one" else "$n $many"

/**
 * One part of a route key. A "/" inside a name (Jealousy/Progress, AC/DC) would split the web address into too
 * many segments and the server answers 404 "Not Found", so it becomes a space, as the server's own keys do.
 */
fun routePart(name: String) = name.trim().lowercase().replace('/', ' ')

/** A key the route accepts for an album the server has not told us the key of; the server normalises it. */
fun routeKey(artist: String, album: String) = "${routePart(artist)}/${routePart(album)}"

/** Similar artists as the web phone shows them: one row that swipes sideways, 112dp circles, names wrap. */
@Composable
fun SimilarArtistsRow(content: androidx.compose.foundation.lazy.LazyListScope.() -> Unit) {
    androidx.compose.foundation.lazy.LazyRow(
        contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 12.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        content = content,
    )
}

// ---- Web phone look: headings with a short red underline, raised panels, ranked rows

/** A section or page title in the display face with the short red rule under it. */
@Composable
fun PageHeading(text: String, modifier: Modifier = Modifier, large: Boolean = false) {
    Column(modifier.semantics { heading() }) {
        Text(text, style = if (large) MaterialTheme.typography.headlineLarge else MaterialTheme.typography.headlineMedium)
        Box(Modifier.padding(top = 4.dp).size(width = 40.dp, height = 3.dp).background(Ink.ChartRed))
    }
}

@Composable
fun Panel(modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    Box(modifier.clip(RoundedCornerShape(12.dp)).background(MaterialTheme.colorScheme.surface)) { content() }
}

/** The rank numeral on ranked rows: display face, muted, in a fixed-width column. */
@Composable
fun RankNumeral(n: Int, modifier: Modifier = Modifier) {
    Text(
        "$n",
        style = MaterialTheme.typography.titleLarge,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = modifier.width(36.dp),
    )
}

/** Dark rounded-square Back button laid over a hero or cover, as on the web pages. */
@Composable
fun OverlayBack(onBack: () -> Unit, modifier: Modifier = Modifier) {
    Box(
        modifier.size(Target).clip(RoundedCornerShape(6.dp))
            .background(Ink.Ink.copy(alpha = 0.78f))
            .clickable(role = Role.Button, onClick = onBack),
        contentAlignment = Alignment.Center,
    ) { Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back") }
}

/** The green check in a dark circle, bottom right of a cover that is in the library. */
@Composable
fun CheckBadge(modifier: Modifier = Modifier) {
    Box(
        modifier.size(32.dp).clip(CircleShape).background(Ink.Ink.copy(alpha = 0.82f)),
        contentAlignment = Alignment.Center,
    ) { Icon(Icons.Default.Check, contentDescription = "In your library", tint = Ink.Ok, modifier = Modifier.size(20.dp)) }
}

/** 18300 becomes "18.3K", as on the web. */
fun abbreviate(n: Long): String = when {
    n >= 1_000_000 -> "%.1fM".format(n / 1_000_000.0).replace(".0M", "M")
    n >= 1_000 -> "%.1fK".format(n / 1_000.0).replace(".0K", "K")
    else -> "$n"
}

@Composable
fun RowDivider(modifier: Modifier = Modifier) {
    Box(modifier.fillMaxWidth().height(1.dp).background(Ink.Edge))
}
