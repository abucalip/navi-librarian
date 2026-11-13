package app.discair.model

/**
 * What the album's Booklet tab shows (docs/artwork.md, idea 2): the pages of the one release with the most booklet pages, in the
 * server's order (never mixed across editions), then the album's Sticker, Obi and Poster, each once. An album with no booklet
 * has no tab, even when it has a Poster: those follow the pages, they are not a booklet of their own. Chosen by type only.
 */
data class BookletView(
    val edition: String,
    val items: List<ArtworkImage>,
    val pageCount: Int,
    /** The album's other booklets, best first, for the "Another booklet" button; empty when there is only this one. */
    val others: List<BookletView> = emptyList(),
) {
    /** A PDF booklet is one entry that holds many pages; it opens in the PDF viewer, not the page pager. */
    val hasPdf: Boolean get() = items.any { it.isPdf }
}

private val FOLLOWING_TYPES = listOf("Sticker", "Obi", "Poster")

fun bookletView(index: ArtworkIndex?): BookletView? {
    index ?: return null
    val all = bookletViews(index)
    return all.firstOrNull()?.copy(others = all.drop(1))
}

/** Every booklet the index holds, best first: one release's pages each, with the album's Sticker, Obi and Poster after them. */
fun bookletViews(index: ArtworkIndex): List<BookletView> {
    val listed = index.booklets.ifEmpty { listOfNotNull(index.booklet) }
    val extras = FOLLOWING_TYPES.mapNotNull { index.slotImage(it) }
    return listed.mapNotNull { b ->
        val pages = index.bookletImages(b)
        if (pages.isEmpty()) null else BookletView(b.edition, (pages + extras).distinctBy { it.imageId }, pages.size)
    }
}

/** What the "Another booklet" button shows: the booklet after [current] (wrapping) and the message, or no move and "no other". */
data class BookletStep(val next: Int, val message: String)

fun anotherBooklet(current: Int, all: List<BookletView>): BookletStep {
    if (all.size < 2) return BookletStep(current, "No other booklet found.")
    val next = (current + 1) % all.size
    val edition = all[next].edition
    return BookletStep(next, "Booklet ${next + 1} of ${all.size}" + (if (edition.isBlank()) "" else " · $edition") + ".")
}

/** The image viewer pages through the bitmaps only; a PDF opens by itself. */
fun BookletView.bitmapItems(): List<ArtworkImage> = items.filterNot { it.isPdf }

/** The zoom after a pinch of [factor], kept between no zoom and [MAX_ZOOM]. */
fun nextZoom(current: Float, factor: Float): Float = (current * factor).coerceIn(1f, MAX_ZOOM)

/** How far the picture may be dragged on one axis at [zoom]: half of what the zoom adds, so an edge never leaves the frame. */
fun maxPan(extent: Float, zoom: Float): Float = if (zoom <= 1f) 0f else extent * (zoom - 1f) / 2f

const val MAX_ZOOM = 6f

/** Past this the full-resolution file is asked for: a small zoom is still sharp enough at display size. */
const val FULL_ZOOM = 1.15f
