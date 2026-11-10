package app.discair.model

/** How many covers a Downloads row shows for the release group it fetches (docs/artwork.md, idea 13). */
const val EDITION_COVER_LIMIT = 3

/**
 * The covers a Downloads row shows (docs/artwork.md, idea 13): the Front images of the release group, best first (the server's
 * order), never a PDF, at most [EDITION_COVER_LIMIT]. Chosen by type only; taste and play data play no part. Empty when the group
 * has no Front image, so the row shows nothing extra.
 */
fun editionCovers(index: ArtworkIndex?): List<ArtworkImage> = coverEditions(index).take(EDITION_COVER_LIMIT)
