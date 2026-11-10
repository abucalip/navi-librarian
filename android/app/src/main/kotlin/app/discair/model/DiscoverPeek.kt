package app.discair.model

import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull

/**
 * The Discover row peek (docs/artwork.md, idea 9): up to three thumbnails of an album a row shows, the Back, the first booklet
 * page and the Medium, in that order. Chosen by type only; taste and play data play no part. The row asks for them only when
 * the reader opens its covers, so lists stay fast.
 */

/** The most thumbnails in one peek. */
const val PEEK_LIMIT = 3

private val MBID = Regex("[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")

/**
 * The MusicBrainz release group a row's album is looked up by, or null when the row does not carry one. The new-releases list
 * sends its release group as `mbid`; the other lists send `release_group_mbid` where they know it. Anything that is not a
 * MusicBrainz id is ignored, so no bad value reaches the server.
 */
fun peekReleaseGroup(list: DiscoveryList, raw: JsonObject): String? {
    val keys = if (list == DiscoveryList.NewReleases) listOf("release_group_mbid", "mbid") else listOf("release_group_mbid")
    return keys.firstNotNullOfOrNull { key ->
        (raw[key] as? JsonPrimitive)?.contentOrNull?.trim()?.takeIf { MBID.matches(it) }?.lowercase()
    }
}

/** The peek pictures for one album's index: Back, booklet page 1 (never a PDF), Medium. Empty when none exist. */
fun discoverPeekFaces(index: ArtworkIndex?): List<ArtworkImage> {
    index ?: return emptyList()
    val firstPage = index.bookletImages().firstOrNull { !it.isPdf }
    return listOfNotNull(index.slotImage("Back"), firstPage, index.slotImage("Medium"))
        .distinctBy { it.imageId }
        .take(PEEK_LIMIT)
}
