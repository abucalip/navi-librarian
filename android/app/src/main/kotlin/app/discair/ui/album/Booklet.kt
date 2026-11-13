package app.discair.ui.album

import android.graphics.Bitmap
import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.calculatePan
import androidx.compose.foundation.gestures.calculateZoom
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.positionChanged
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.CustomAccessibilityAction
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.customActions
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import app.discair.model.ArtworkImage
import app.discair.model.ArtworkSize
import app.discair.model.BookletView
import app.discair.model.FULL_ZOOM
import app.discair.model.MAX_ZOOM
import app.discair.model.anotherBooklet
import app.discair.model.bitmapItems
import app.discair.model.maxPan
import app.discair.model.nextZoom
import app.discair.ui.common.LocalImageLoader
import app.discair.ui.common.LocalRepository
import coil3.compose.AsyncImage
import java.io.File
import kotlinx.coroutines.Dispatchers
import kotlin.coroutines.coroutineContext
import kotlinx.coroutines.isActive
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext

private val Target = 48.dp

/**
 * The album's Booklet tab (docs/artwork.md, idea 2): the pages in a horizontal pager at display size, with the page number and
 * the image's own caption (type, edition, the Cover Art Archive comment as plain text). A tap opens the viewer, which pinch-zooms
 * and loads the full-resolution file only once the reader zooms in. A PDF booklet shows its first-page preview here and opens
 * in a page-by-page PDF viewer. No text recognition and no credit links: pages are images.
 */
@Composable
fun BookletTab(first: BookletView) {
    // The album's booklets, best first; "Another booklet" moves along them and round again. Images load as each is shown and stay cached.
    val all = remember(first) { listOf(first.copy(others = emptyList())) + first.others }
    var current by remember(first) { mutableStateOf(0) }
    var notice by remember(first) { mutableStateOf<String?>(null) }
    val booklet = all[current]
    var viewer by remember(first) { mutableStateOf<Int?>(null) } // kept across "Another booklet" so the viewer stays open
    val state = rememberPagerState { booklet.items.size }
    LaunchedEffect(booklet) { state.scrollToPage(0) }
    val repo = LocalRepository.current
    Column(Modifier.fillMaxWidth().padding(vertical = 16.dp)) {
        if (booklet.edition.isNotBlank()) Text(
            "Booklet from ${booklet.edition}", style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
        )
        HorizontalPager(state, Modifier.fillMaxWidth(), contentPadding = PaddingValues(horizontal = 32.dp), pageSpacing = 12.dp) { i ->
            val image = booklet.items[i]
            val url = remember(image) { repo.artworkImageUrl(image, ArtworkSize.Display) }
            Box(
                Modifier.fillMaxWidth().aspectRatio(1f).clip(MaterialTheme.shapes.small)
                    .background(MaterialTheme.colorScheme.surfaceVariant)
                    .clickable(onClickLabel = if (image.isPdf) "Open the PDF booklet" else "Zoom in on this page", role = Role.Button) { notice = null; viewer = i },
                contentAlignment = Alignment.Center,
            ) {
                if (url != null) AsyncImage(
                    model = url, contentDescription = image.label(), imageLoader = LocalImageLoader.current,
                    contentScale = ContentScale.Fit, modifier = Modifier.fillMaxSize(),
                )
                if (image.isPdf) Text(
                    "PDF · tap to open", style = MaterialTheme.typography.labelMedium, color = Color.White,
                    modifier = Modifier.align(Alignment.BottomCenter).padding(8.dp).background(Color.Black.copy(alpha = 0.6f)).padding(horizontal = 8.dp, vertical = 4.dp),
                )
            }
        }
        val shown = booklet.items[state.currentPage]
        Text(
            if (shown.isPdf) "PDF booklet" else if (state.currentPage < booklet.pageCount) "Page ${state.currentPage + 1} of ${booklet.pageCount}" else shown.types.firstOrNull() ?: "Image",
            style = MaterialTheme.typography.labelLarge, modifier = Modifier.padding(horizontal = 16.dp).padding(top = 12.dp),
        )
        // Third-party text from the Cover Art Archive: plain text, never markup.
        Text(shown.label(), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(horizontal = 16.dp))
    }
    val open = viewer
    if (open != null) {
        // "Another booklet" sits next to Close in the viewer only; it swaps the booklet and starts at its first page.
        val another = { val step = anotherBooklet(current, all); current = step.next; notice = step.message; viewer = 0 }
        val tapped = booklet.items[open.coerceIn(0, booklet.items.lastIndex)]
        key(current) {
            if (tapped.isPdf) PdfViewer(tapped, another, notice) { viewer = null } else {
                val pages = booklet.bitmapItems()
                ImageViewer(pages, pages.indexOfFirst { it.imageId == tapped.imageId }.coerceAtLeast(0), another, notice) { viewer = null }
            }
        }
    }
}

@Composable
private fun ViewerFrame(title: String, onClose: () -> Unit, another: () -> Unit, notice: String?, content: @Composable () -> Unit) {
    Dialog(onDismissRequest = onClose, properties = DialogProperties(usePlatformDefaultWidth = false)) {
        Box(Modifier.fillMaxSize().background(Color.Black)) {
            content()
            Row(Modifier.statusBarsPadding().fillMaxWidth().padding(8.dp), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f).padding(start = 8.dp)) {
                    Text(title, color = Color.White, style = MaterialTheme.typography.labelLarge, maxLines = 1)
                    notice?.let {
                        Text(it, color = Color.White.copy(alpha = 0.8f), style = MaterialTheme.typography.bodySmall, maxLines = 2,
                            modifier = Modifier.semantics { liveRegion = androidx.compose.ui.semantics.LiveRegionMode.Polite })
                    }
                }
                OutlinedButton(onClick = another, modifier = Modifier.heightIn(min = Target).padding(end = 8.dp)) { Text("Another booklet", color = Color.White) }
                OutlinedButton(onClick = onClose, modifier = Modifier.heightIn(min = Target)) { Text("Close", color = Color.White) }
            }
        }
    }
}

/** The booklet's bitmap pages full screen, swipe to turn, pinch or double-tap to zoom. */
@Composable
private fun ImageViewer(pages: List<ArtworkImage>, start: Int, another: () -> Unit, notice: String?, onClose: () -> Unit) {
    val state = rememberPagerState(initialPage = start) { pages.size }
    var zoomed by remember { mutableStateOf(false) }
    ViewerFrame("Page ${state.currentPage + 1} of ${pages.size}", onClose, another, notice) {
        HorizontalPager(state, Modifier.fillMaxSize(), userScrollEnabled = !zoomed, beyondViewportPageCount = 0) { i ->
            val image = pages[i]
            val repo = LocalRepository.current
            val display = remember(image) { repo.artworkImageUrl(image, ArtworkSize.Display) }
            val full = remember(image) { repo.artworkImageUrl(image, ArtworkSize.Full) }
            var wantFull by remember(image) { mutableStateOf(false) }
            ZoomBox(image.label(), onZoom = { z -> if (z > FULL_ZOOM) wantFull = true; if (i == state.currentPage) zoomed = z > 1f }) {
                if (display != null) AsyncImage(model = display, contentDescription = image.label(), imageLoader = LocalImageLoader.current, contentScale = ContentScale.Fit, modifier = Modifier.fillMaxSize())
                // The original is asked for only after the first real zoom, and drawn over the display size once it arrives.
                if (wantFull && full != null) AsyncImage(model = full, contentDescription = null, imageLoader = LocalImageLoader.current, contentScale = ContentScale.Fit, modifier = Modifier.fillMaxSize())
            }
        }
    }
}

/**
 * Content that pinches and drags once zoomed in, and leaves one-finger swipes to the pager while it is not. A double tap zooms
 * to 2.5x and back; TalkBack gets "Zoom in" and "Zoom out" actions, so zoom does not need a pinch.
 */
@Composable
private fun ZoomBox(description: String, onZoom: (Float) -> Unit, content: @Composable () -> Unit) {
    var scale by remember { mutableFloatStateOf(1f) }
    var panX by remember { mutableFloatStateOf(0f) }
    var panY by remember { mutableFloatStateOf(0f) }
    var size by remember { mutableStateOf(IntSize.Zero) }
    fun set(z: Float, dx: Float = panX, dy: Float = panY) {
        scale = z
        panX = dx.coerceIn(-maxPan(size.width.toFloat(), z), maxPan(size.width.toFloat(), z))
        panY = dy.coerceIn(-maxPan(size.height.toFloat(), z), maxPan(size.height.toFloat(), z))
        onZoom(z)
    }
    Box(
        Modifier.fillMaxSize().clipToBounds().onSizeChanged { size = it }
            .semantics {
                contentDescription = description
                customActions = listOf(
                    CustomAccessibilityAction("Zoom in") { set(nextZoom(scale, 1.6f)); true },
                    CustomAccessibilityAction("Zoom out") { set(nextZoom(scale, 1f / 1.6f)); true },
                )
            }
            .pointerInput(Unit) { detectTapGestures(onDoubleTap = { if (scale > 1f) set(1f, 0f, 0f) else set(2.5f)}) }
            .pointerInput(Unit) {
                awaitEachGesture {
                    awaitFirstDown(requireUnconsumed = false)
                    do {
                        val event = awaitPointerEvent()
                        val pinching = event.changes.count { it.pressed } > 1
                        if (pinching || scale > 1f) {
                            val z = nextZoom(scale, event.calculateZoom())
                            val pan = event.calculatePan()
                            set(z, panX + pan.x, panY + pan.y)
                            event.changes.forEach { if (it.positionChanged()) it.consume() }
                        }
                    } while (event.changes.any { it.pressed })
                }
            },
    ) {
        Box(Modifier.fillMaxSize().graphicsLayer { scaleX = scale; scaleY = scale; translationX = panX; translationY = panY }) { content() }
    }
}

private sealed interface PdfState {
    data class Downloading(val done: Long, val total: Long) : PdfState
    data class Ready(val file: File) : PdfState
    data object Failed : PdfState
}

/** One PDF booklet, downloaded whole on first open (progress shown, Close cancels) and drawn one page at a time. */
@Composable
private fun PdfViewer(image: ArtworkImage, another: () -> Unit, notice: String?, onClose: () -> Unit) {
    val repo = LocalRepository.current
    val context = LocalContext.current
    val state by produceState<PdfState>(PdfState.Downloading(0, -1), image) {
        val file = File(File(context.cacheDir, "artwork-pdf").apply { mkdirs() }, "${image.imageId}.pdf")
        if (file.isFile && file.length() > 0) { value = PdfState.Ready(file); return@produceState }
        val job = coroutineContext[kotlinx.coroutines.Job]
        value = try {
            withContext(Dispatchers.IO) {
                repo.artworkDownload(image, file, shouldStop = { job?.isActive != true }) { done, total -> value = PdfState.Downloading(done, total) }
            }
            PdfState.Ready(file)
        } catch (e: kotlinx.coroutines.CancellationException) { throw e } catch (e: Exception) { PdfState.Failed }
    }
    ViewerFrame("PDF booklet", onClose, another, notice) {
        Box(Modifier.fillMaxSize()) { when (val s = state) {
            is PdfState.Downloading -> Column(Modifier.align(Alignment.Center), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Downloading the booklet…", color = Color.White, style = MaterialTheme.typography.bodyMedium)
                if (s.total > 0) Text("${s.done / 1_000_000} of ${s.total / 1_000_000} MB", color = Color.White, style = MaterialTheme.typography.bodySmall)
            }
            PdfState.Failed -> Text("The booklet could not be opened.", color = Color.White, modifier = Modifier.align(Alignment.Center), style = MaterialTheme.typography.bodyMedium)
            is PdfState.Ready -> PdfPages(s.file)
        } }
    }
}

/** Pages are drawn to a bitmap one at a time (PdfRenderer allows one open page), at up to 2048 px wide. */
@Composable
private fun PdfPages(file: File) {
    val opened by produceState<Pair<PdfRenderer, ParcelFileDescriptor>?>(null, file) {
        value = withContext(Dispatchers.IO) {
            try {
                val fd = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY)
                try { PdfRenderer(fd) to fd } catch (e: Exception) { fd.close(); null }
            } catch (e: Exception) { null }
        }
        awaitDispose { value?.let { (r, fd) -> r.close(); fd.close() } }
    }
    val (renderer, _) = opened ?: run {
        Box(Modifier.fillMaxSize()) { Text("Opening…", color = Color.White, modifier = Modifier.align(Alignment.Center)) }
        return
    }
    val lock = remember(renderer) { Mutex() }
    val state = rememberPagerState { renderer.pageCount }
    var zoomed by remember { mutableStateOf(false) }
    Column(Modifier.fillMaxSize().padding(top = 56.dp)) {
        HorizontalPager(state, Modifier.weight(1f), userScrollEnabled = !zoomed, beyondViewportPageCount = 0) { i ->
            val bitmap by produceState<Bitmap?>(null, i) {
                value = withContext(Dispatchers.IO) {
                    lock.withLock {
                        try {
                            renderer.openPage(i).use { p ->
                                val w = 2048.coerceAtMost(p.width * 3).coerceAtLeast(p.width)
                                val h = (w.toFloat() / p.width * p.height).toInt()
                                Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888).also {
                                    it.eraseColor(android.graphics.Color.WHITE)
                                    p.render(it, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                                }
                            }
                        } catch (e: Exception) { null }
                    }
                }
            }
            ZoomBox("Page ${i + 1} of ${renderer.pageCount}", onZoom = { z -> if (i == state.currentPage) zoomed = z > 1f }) {
                bitmap?.let { Image(it.asImageBitmap(), "Page ${i + 1}", Modifier.fillMaxSize(), contentScale = ContentScale.Fit) }
            }
        }
        Text("Page ${state.currentPage + 1} of ${renderer.pageCount}", color = Color.White, style = MaterialTheme.typography.labelLarge, modifier = Modifier.align(Alignment.CenterHorizontally).padding(12.dp))
    }
}
