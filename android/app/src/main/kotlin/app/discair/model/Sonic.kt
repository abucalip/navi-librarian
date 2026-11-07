package app.discair.model

import app.discair.data.CacheMiss
import app.discair.net.ConnectionException
import app.discair.net.ConnectionFailure
import app.discair.net.classifyException
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull

/**
 * Server V2 sonic similarity (`GET /api/sonic/similar`, Phase 7 client). Every track is a song in the owner's
 * Navidrome. The server's order is kept: [SonicTrack.similarity] sits in a narrow band and is informational only,
 * so nothing here sorts or filters on it.
 */
data class SonicTrack(
    val songId: String,
    val title: String,
    val artist: String,
    val album: String,
    val albumId: String,
    val durationSec: Int,
    val year: Int?,
    val similarity: Double?,
)

/** [status] is the server's `ok`, or `empty` when the song has no analysis data. */
data class SonicResponse(val status: String, val tracks: List<SonicTrack>)

/** Parses a similar-tracks body. A body that is not an object is an empty answer; a track without an id is left out. */
fun parseSonic(body: String): SonicResponse {
    val root = try {
        ApiJson.parseToJsonElement(body) as? JsonObject
    } catch (e: kotlinx.serialization.SerializationException) {
        null
    } ?: return SonicResponse("empty", emptyList())
    val tracks = (root["tracks"] as? JsonArray).orEmpty().mapNotNull { element ->
        val t = element as? JsonObject ?: return@mapNotNull null
        val id = t.string("navidrome_id")?.takeIf { it.isNotBlank() } ?: return@mapNotNull null
        SonicTrack(
            songId = id,
            title = t.string("title").orEmpty(),
            artist = t.string("artist").orEmpty().ifBlank { "Unknown artist" },
            album = t.string("album").orEmpty(),
            albumId = t.string("album_id").orEmpty(),
            durationSec = t.number("duration")?.toInt() ?: 0,
            year = t.number("year")?.toInt(),
            similarity = t.number("similarity"),
        )
    }
    return SonicResponse(root.string("status") ?: "empty", tracks)
}

/** `sonic_available` from a `GET /api/capabilities` body; anything missing or unreadable is false. */
fun sonicAvailableFrom(body: String): Boolean {
    val root = try {
        ApiJson.parseToJsonElement(body) as? JsonObject
    } catch (e: kotlinx.serialization.SerializationException) {
        null
    } ?: return false
    return (root["sonic_available"] as? JsonPrimitive)?.booleanOrNull ?: false
}

/** The honest reason sonic matches could not be read; each status the route returns has its own words. */
fun sonicFailure(error: Throwable): ConnectionFailure {
    if (error is CacheMiss) return ConnectionFailure.Server(0, "Sounds-like needs the server. It is not saved on this phone.")
    val failure = (error as? ConnectionException)?.failure
    if (failure is ConnectionFailure.Server) {
        return when (failure.code) {
            404 -> ConnectionFailure.Server(404, "The server doesn't know this song.")
            422 -> ConnectionFailure.Server(422, "The server rejected the request.")
            502 -> ConnectionFailure.Server(502, "Sound matching isn't available right now. Try again later.")
            else -> failure
        }
    }
    return classifyException(error, networkAvailable = true)
}

private fun JsonObject.string(name: String) = (this[name] as? JsonPrimitive)?.takeIf { it.isString }?.contentOrNull
private fun JsonObject.number(name: String) = (this[name] as? JsonPrimitive)?.let { it.doubleOrNull ?: it.intOrNull?.toDouble() }
