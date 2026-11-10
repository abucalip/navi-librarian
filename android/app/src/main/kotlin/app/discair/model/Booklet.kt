package app.discair.model

/**
 * What the album's Booklet tab shows (docs/artwork.md, idea 2): the pages of the one release with the most booklet pages, in the
 * server's order (never mixed across editions), then the album's Sticker, Obi and Poster, each once. An album with no booklet
 * has no tab, even when it has a Poster: those follow the pages, they are not a booklet of their own. Chosen by type only.
 */
data class BookletView(val edition: String, val items: List<ArtworkImage>, val pageCount: Int) {
    /** A PDF booklet is one entry that holds many pages; it opens in the PDF viewer, not the page pager. */
    val hasPdf: Boolean get() = items.any { it.isPdf }
}

private val FOLLOWING_TYPES = listOf("Sticker", "Obi", "Poster")

fun bookletView(index: ArtworkIndex?): BookletView? {
    index ?: return null
    val pages = index.bookletImages()
    if (pages.isEmpty()) return null
    val extras = FOLLOWING_TYPES.mapNotNull { index.slotImage(it) }
    val items = (pages + extras).distinctBy { it.imageId }
    return BookletView(index.booklet?.edition.orEmpty(), items, pages.size)
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
