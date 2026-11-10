package app.discair.model

/**
 * The artist photo strip (docs/artwork.md, idea 8): session and band pictures from the artist's owned albums. Chosen by type and
 * comment words only (a plain string match; nothing recognises what a picture shows). Mirrors the macOS rules
 * (`qualifiesForCollage` and `artistCollage` in `macos/Sources/DiscairLibrarian/Artwork.swift`). Taste and play data play no part.
 */

/** The most owned albums looked up for one strip, in the server's order. */
const val COLLAGE_ALBUM_LIMIT = 8

/** The most pictures in one strip. */
const val COLLAGE_LIMIT = 12

/** The most pictures taken from one album, so a big session set does not fill the strip. */
const val COLLAGE_PER_ALBUM = 3

/** The fewest pictures worth a strip; below this the artist page keeps no strip. */
const val COLLAGE_MINIMUM = 4

private val COLLAGE_TYPES = setOf("Other", "Raw/Unedited", "Liner", "Poster")

/** Packaging is never a session photo through its comment: "studio version" on a Front image is not a studio photo. */
private val PACKAGING_TYPES = setOf("Front", "Back", "Medium", "Tray", "Spine", "Obi", "Sticker")
private val COLLAGE_WORDS = listOf("session", "studio", "band")

/**
 * A session or band picture: one of the Other, Raw/Unedited, Liner or Poster types, or a comment containing "session", "studio" or
 * "band" (case-insensitive). Never a PDF, never packaging, never a booklet page.
 */
fun ArtworkImage.qualifiesForCollage(): Boolean {
    if (isPdf) return false
    if (types.any { it in COLLAGE_TYPES }) return true
    if (types.any { it in PACKAGING_TYPES } || "Booklet" in types) return false
    val note = comment.lowercase()
    return COLLAGE_WORDS.any { it in note }
}

/** One picture in the strip and the owned album it is from. Third-party text: shown as plain text only. */
data class CollageEntry(val image: ArtworkImage, val album: OwnedAlbum)

/**
 * Builds the strip from [albums] (each with its index), in the order given: the qualifying pictures of each album in the server's
 * quality order, taken round-robin so every album shows before any shows twice. An image id appears once. Returns nothing under
 * [COLLAGE_MINIMUM], so the page keeps its usual look.
 */
fun artistCollage(
    albums: List<Pair<OwnedAlbum, ArtworkIndex>>,
    limit: Int = COLLAGE_LIMIT,
    perAlbum: Int = COLLAGE_PER_ALBUM,
): List<CollageEntry> {
    val seen = HashSet<Long>()
    val lists = albums.map { (album, index) ->
        val taken = ArrayList<CollageEntry>()
        for (image in index.images) {
            if (taken.size >= perAlbum) break
            if (image.qualifiesForCollage() && seen.add(image.imageId)) taken += CollageEntry(image, album)
        }
        taken
    }
    val out = ArrayList<CollageEntry>()
    var round = 0
    while (out.size < limit && lists.any { round < it.size }) {
        for (list in lists) if (round < list.size && out.size < limit) out += list[round]
        round++
    }
    return if (out.size >= COLLAGE_MINIMUM) out else emptyList()
}
