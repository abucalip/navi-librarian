package app.discair.model

/**
 * The covers an owner can pick from (docs/artwork.md, idea 7): Front images of the album's release group, best first,
 * never a PDF. The server checks the same rule on `PUT /api/artwork/choice`, so a pick it would refuse is never offered.
 * With one or none there is nothing to choose, so no stack and no sheet.
 */
fun coverEditions(index: ArtworkIndex?): List<ArtworkImage> =
    index?.images.orEmpty().filter { "Front" in it.types && !it.isPdf }.distinctBy { it.imageId }

/** The picker is offered only when there is a real choice. */
fun hasEditionChoice(editions: List<ArtworkImage>): Boolean = editions.size >= 2

/**
 * The album's cover address with the pick added as a query value. The server ignores it; it only makes a new pick a new
 * address, so the image loader does not keep showing the old cover. `0` stands for "no pick".
 */
fun coverUrlFor(artworkUrl: String?, choice: Long?): String? =
    artworkUrl?.let { it + (if ('?' in it) "&" else "?") + "c=${choice ?: 0}" }
