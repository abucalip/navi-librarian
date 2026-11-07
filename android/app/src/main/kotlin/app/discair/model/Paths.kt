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
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.doubleOrNull

/**
 * Server V2 discovery paths (`GET /api/knowledge/paths`, Phase 7 client gate). The four kinds the server builds;
 * `place`, `event` and the dropped or parked kinds are not paths, so they are not offered.
 */
enum class PathKind(val wire: String, val label: String) {
    FollowTheMusician("follow_the_musician", "Follow the musician"),
    LabelPath("label_path", "Label"),
    CompositionPath("composition_path", "Composition"),
    ScenePath("scene_path", "Scene"),
}

/** One step: the entity the server reached and the server's own sentence for why (at least one reason). */
data class PathStop(val name: String, val type: String, val owned: Boolean, val reasonCount: Int, val reason: String)

/** A parsed body. [status] is the server's `ok` or `empty`; [truncated] is `rows`, `time`, `stops` or null. */
data class PathsResponse(val kind: String, val status: String, val stops: List<PathStop>, val truncated: String?)

/** What the sheet shows for a read: the server's stops, or nothing it can honestly list. */
sealed interface PathsView {
    data class Stops(val response: PathsResponse) : PathsView
    data object Empty : PathsView
}

/** Parses a path body. A body that is not an object, or a stop the app cannot explain, is left out. */
fun parsePaths(body: String): PathsResponse {
    val root = objectOrNull(body)
        ?: return PathsResponse(kind = "", status = "", stops = emptyList(), truncated = null)
    val stops = (root["stops"] as? JsonArray).orEmpty().mapNotNull { element ->
        val stop = element as? JsonObject ?: return@mapNotNull null
        val entity = stop.obj("entity") ?: return@mapNotNull null
        val name = entity.string("canonical_name")?.trim().orEmpty()
        val reason = (stop["reasons"] as? JsonArray).orEmpty().firstNotNullOfOrNull { r ->
            (r as? JsonObject)?.string("text")?.trim()?.takeIf { it.isNotEmpty() }
        }
        if (name.isEmpty() || reason == null) return@mapNotNull null
        PathStop(
            name = name,
            type = entity.string("type").orEmpty(),
            owned = (entity["owned"] as? JsonPrimitive)?.booleanOrNull ?: false,
            reasonCount = stop.int("reason_count") ?: 1,
            reason = reason,
        )
    }
    return PathsResponse(
        kind = root.string("kind").orEmpty(),
        status = root.string("status").orEmpty(),
        stops = stops,
        truncated = root.string("truncated")?.takeIf { it.isNotBlank() },
    )
}

/** Turns a parsed path into what the sheet shows. An `empty` status or no usable stop is said in words, never blank. */
fun PathsResponse.view(): PathsView = if (status == "ok" && stops.isNotEmpty()) PathsView.Stops(this) else PathsView.Empty

/** `features.paths.available` from a `GET /api/capabilities` body; anything missing or unreadable is false. */
fun pathsAvailableFrom(body: String): Boolean {
    val root = objectOrNull(body) ?: return false
    val paths = root.obj("features")?.obj("paths") ?: return false
    return (paths["available"] as? JsonPrimitive)?.booleanOrNull ?: false
}

/**
 * The honest reason a path could not be read. Each status the route returns has its own words; a failure the
 * app does not recognise falls back to the connection classification used by every other screen.
 */
fun pathsFailure(error: Throwable): ConnectionFailure {
    if (error is CacheMiss) return ConnectionFailure.Server(0, "Paths need the server. They are not saved on this phone.")
    val failure = (error as? ConnectionException)?.failure
    if (failure is ConnectionFailure.Server) {
        return when (failure.code) {
            400 -> ConnectionFailure.Server(400, "The server can't build this path for the artist.")
            404 -> ConnectionFailure.Server(404, "This artist isn't in the server's knowledge store yet.")
            422 -> ConnectionFailure.Server(422, "The server rejected the request.")
            502 -> ConnectionFailure.Server(502, "The server couldn't read its knowledge store. Try again later.")
            else -> failure
        }
    }
    return classifyException(error, networkAvailable = true)
}

/** The body as a JSON object, or null when it is not JSON or not an object. */
private fun objectOrNull(body: String): JsonObject? = try {
    ApiJson.parseToJsonElement(body) as? JsonObject
} catch (e: kotlinx.serialization.SerializationException) {
    null
}

private fun JsonObject.string(name: String) = (this[name] as? JsonPrimitive)?.takeIf { it.isString }?.contentOrNull
private fun JsonObject.int(name: String) = (this[name] as? JsonPrimitive)?.let { it.intOrNull ?: it.doubleOrNull?.toInt() }
private fun JsonObject.obj(name: String) = this[name] as? JsonObject
