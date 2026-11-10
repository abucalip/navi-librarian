package app.discair.model

/**
 * Pictures on the Paths screens (docs/artwork.md, idea 10). Chosen by type and comment words only; nothing recognises what a
 * picture shows, and taste and play data play no part. Mirrors the macOS rules in `macos/Sources/DiscairLibrarian/Artwork.swift`.
 */

/** The most session photos shown for one album in Same Room. */
const val ROOM_PHOTO_LIMIT = 3

/**
 * The covers a path row can cycle through: the Front images of the release group, best first, never a PDF. One cover (or none) is
 * nothing to cycle, so the row then keeps its usual cover and answers no long press.
 */
fun pathCoverFaces(index: ArtworkIndex?): List<ArtworkImage> {
    index ?: return emptyList()
    val faces = index.images.filter { "Front" in it.types && !it.isPdf }.distinctBy { it.imageId }
    return if (faces.size >= 2) faces else emptyList()
}

/** The face after [current] among [count] faces; wraps to the first. */
fun nextPathCover(current: Int, count: Int): Int = if (count <= 0) 0 else (current + 1) % count

/** One album's session and band photos for Same Room, in the server's quality order, at most [ROOM_PHOTO_LIMIT]. */
fun roomPhotos(index: ArtworkIndex?, limit: Int = ROOM_PHOTO_LIMIT): List<ArtworkImage> =
    index?.images.orEmpty().filter { it.qualifiesForCollage() }.distinctBy { it.imageId }.take(limit)

/**
 * Same Room is drawn only when at least one of the two albums has a session photo; an album with none says so in plain words
 * and nothing is inferred from the other. True when there is anything to draw.
 */
fun hasRoomPhotos(start: List<ArtworkImage>, other: List<ArtworkImage>): Boolean = start.isNotEmpty() || other.isNotEmpty()
