package app.discair.model

/** How many Track images the queue card shows at most. */
const val TRACK_LIMIT = 3

/**
 * The Track images of the playing album (docs/artwork.md, idea 6): session sheets and studio track lists, shown as cards in the queue
 * while that album plays. Only images typed Track, in the server's quality order, each once. A PDF is left out (its preview is not the
 * sheet). Empty when the album has none, so no card is shown. Chosen by type only, never by taste or play data.
 */
fun trackImages(index: ArtworkIndex?): List<ArtworkImage> {
    index ?: return emptyList()
    return index.images.filter { "Track" in it.types && !it.isPdf }.distinctBy { it.imageId }.take(TRACK_LIMIT)
}
