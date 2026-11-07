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
 * Server V2 discovery paths (`GET /api/knowledge/paths`, Phase 7 client gate). The five kinds the server builds;
 * `place`, `event` and the dropped kind (`same_studio_different_decade`) are not paths, so they are not offered.
 * Stops for `sideman_to_leader` are artists, each explained by `sideman_on` (via the release, anchor the recording).
 */
enum class PathKind(val wire: String, val label: String) {
    FollowTheMusician("follow_the_musician", "Follow the musician"),
    SidemanToLeader("sideman_to_leader", "Sideman"),
    LabelPath("label_path", "Label"),
    CompositionPath("composition_path", "Composition"),
    ScenePath("scene_path", "Scene"),
}

/** A named graph entity included in a path explanation. */
data class PathEntity(val name: String, val type: String, val mbid: String?, val owned: Boolean)

/** One stored fact supporting a relationship. */
data class PathEvidence(
    val relation: String,
    val role: String?,
    val source: String?,
    val catalogueNumber: String?,
    val validFrom: String?,
    val validTo: String?,
    val evidenceClass: String?,
    val matchQuality: String?,
)

/** One independent explanation for why a stop belongs in a path. */
data class PathReason(val code: String, val text: String, val via: PathEntity?, val anchor: PathEntity?, val evidence: List<PathEvidence>)

/** One step: the entity the server reached and all bounded reasons/evidence for why. */
data class PathStop(
    val name: String, val type: String, val owned: Boolean, val reasonCount: Int, val reason: String,
    val displayTitle: String? = null, val displayContext: String? = null, val reasons: List<PathReason> = emptyList(),
)

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
        val reasons = (stop["reasons"] as? JsonArray).orEmpty().mapNotNull { r ->
            val item = r as? JsonObject ?: return@mapNotNull null
            val text = item.string("text")?.trim()?.takeIf { it.isNotEmpty() } ?: return@mapNotNull null
            val evidence = (item["evidence"] as? JsonArray).orEmpty().mapNotNull { raw ->
                (raw as? JsonObject)?.pathEvidence()
            }
            PathReason(item.string("code").orEmpty(), text, item.pathEntity("via"), item.pathEntity("anchor"), evidence)
        }
        val reason = reasons.firstOrNull()?.text
        if (name.isEmpty() || reason == null) return@mapNotNull null
        PathStop(
            name = name,
            type = entity.string("type").orEmpty(),
            owned = (entity["owned"] as? JsonPrimitive)?.booleanOrNull ?: false,
            reasonCount = stop.int("reason_count") ?: reasons.size.coerceAtLeast(1),
            reason = reason,
            displayTitle = stop.obj("presentation")?.string("title")?.trim()?.takeIf { it.isNotEmpty() },
            displayContext = stop.obj("presentation")?.string("context")?.trim()?.takeIf { it.isNotEmpty() },
            reasons = reasons,
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

private fun JsonObject.pathEntity(name: String): PathEntity? {
    val entity = obj(name) ?: return null
    val canonicalName = entity.string("canonical_name")?.trim()?.takeIf { it.isNotEmpty() } ?: return null
    return PathEntity(
        canonicalName, entity.string("type").orEmpty(), entity.string("mbid")?.takeIf { it.isNotBlank() },
        (entity["owned"] as? JsonPrimitive)?.booleanOrNull ?: false,
    )
}

private fun JsonObject.pathEvidence(): PathEvidence? {
    val relation = string("relation").orEmpty()
    val role = string("role")?.takeIf { it.isNotBlank() }
    val catalogueNumber = string("catalogue_number")?.takeIf { it.isNotBlank() }
    if (relation.isBlank() && role == null && catalogueNumber == null) return null
    return PathEvidence(
        relation, role, string("source")?.takeIf { it.isNotBlank() }, catalogueNumber,
        string("valid_from")?.takeIf { it.isNotBlank() }, string("valid_to")?.takeIf { it.isNotBlank() },
        string("evidence_class")?.takeIf { it.isNotBlank() }, string("match_quality")?.takeIf { it.isNotBlank() },
    )
}

private fun JsonObject.string(name: String) = (this[name] as? JsonPrimitive)?.takeIf { it.isString }?.contentOrNull
private fun JsonObject.int(name: String) = (this[name] as? JsonPrimitive)?.let { it.intOrNull ?: it.doubleOrNull?.toInt() }
private fun JsonObject.obj(name: String) = this[name] as? JsonObject
