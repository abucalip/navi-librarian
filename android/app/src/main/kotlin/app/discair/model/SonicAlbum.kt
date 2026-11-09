package app.discair.model

import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull

/**
 * `GET /api/sonic/album-neighbours?album_id=`: other albums whose tracks sound like this album's. Ranked by the
 * server by how many of the sampled seeds they match; `similarity` is never read (too narrow a band to sort by).
 * A seed without analysis data is listed in [skipped], never silently dropped.
 */
data class SonicAlbumNeighbours(
    val status: String,
    val start: SonicAlbumStart?,
    val seeds: List<SonicSeed>,
    val skipped: List<SonicSkippedSeed>,
    val stops: List<SonicAlbumNeighbour>,
    val truncated: String?,
)

data class SonicAlbumStart(val album: String, val albumId: String, val artist: String, val tracks: Int, val year: Int?)

data class SonicSeed(val navidromeId: String, val title: String)

data class SonicSkippedSeed(val navidromeId: String, val title: String, val reason: String)

/** One owned album the sample sounds like. [matchCount] is the number of distinct seeds it matched. */
data class SonicAlbumNeighbour(
    val albumId: String, val album: String, val artist: String, val artistId: String?, val year: Int?,
    val coverArt: String?, val owned: Boolean, val matchCount: Int, val reasonText: String?,
)

/** Parses an album-neighbours body. A body that is not an object is an empty answer; an album without an id or name is left out. */
fun parseSonicAlbumNeighbours(body: String): SonicAlbumNeighbours {
    val root = parseObjectOrNull(body)
        ?: return SonicAlbumNeighbours("", null, emptyList(), emptyList(), emptyList(), null)
    val start = root.sub("start")?.let { s ->
        val albumId = s.str("album_id")?.trim()?.takeIf { it.isNotEmpty() } ?: return@let null
        SonicAlbumStart(
            album = s.str("album").orEmpty(), albumId = albumId, artist = s.str("artist").orEmpty(),
            tracks = s.num("tracks") ?: 0, year = s.num("year"),
        )
    }
    val seeds = (root["seeds"] as? JsonArray).orEmpty().mapNotNull { e ->
        val o = e as? JsonObject ?: return@mapNotNull null
        val id = o.str("navidrome_id")?.takeIf { it.isNotBlank() } ?: return@mapNotNull null
        SonicSeed(id, o.str("title").orEmpty())
    }
    val skipped = (root["skipped"] as? JsonArray).orEmpty().mapNotNull { e ->
        val o = e as? JsonObject ?: return@mapNotNull null
        val id = o.str("navidrome_id")?.takeIf { it.isNotBlank() } ?: return@mapNotNull null
        SonicSkippedSeed(id, o.str("title").orEmpty(), o.str("reason").orEmpty())
    }
    val stops = (root["stops"] as? JsonArray).orEmpty().mapNotNull { e ->
        val o = e as? JsonObject ?: return@mapNotNull null
        val albumId = o.str("album_id")?.takeIf { it.isNotBlank() } ?: return@mapNotNull null
        val album = o.str("album")?.trim()?.takeIf { it.isNotEmpty() } ?: return@mapNotNull null
        SonicAlbumNeighbour(
            albumId = albumId,
            album = album,
            artist = o.str("artist").orEmpty(),
            artistId = o.str("artist_id")?.takeIf { it.isNotBlank() },
            year = o.num("year"),
            coverArt = o.str("cover_art")?.takeIf { it.isNotBlank() },
            owned = (o["owned"] as? JsonPrimitive)?.booleanOrNull ?: false,
            matchCount = o.num("match_count") ?: 0,
            reasonText = (o["reasons"] as? JsonArray).orEmpty().firstNotNullOfOrNull { r ->
                (r as? JsonObject)?.str("text")?.trim()?.takeIf { it.isNotEmpty() }
            },
        )
    }
    return SonicAlbumNeighbours(
        status = root.str("status").orEmpty(),
        start = start,
        seeds = seeds,
        skipped = skipped,
        stops = stops,
        truncated = root.str("truncated")?.takeIf { it.isNotBlank() },
    )
}

private fun JsonObject.str(name: String) = (this[name] as? JsonPrimitive)?.takeIf { it.isString }?.contentOrNull
private fun JsonObject.num(name: String) = (this[name] as? JsonPrimitive)?.let { it.intOrNull ?: it.doubleOrNull?.toInt() }
private fun JsonObject.sub(name: String) = this[name] as? JsonObject
private fun parseObjectOrNull(body: String): JsonObject? = try {
    ApiJson.parseToJsonElement(body) as? JsonObject
} catch (e: kotlinx.serialization.SerializationException) {
    null
}
