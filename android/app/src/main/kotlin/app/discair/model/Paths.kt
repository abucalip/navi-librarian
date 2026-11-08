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

/** One step: the entity the server reached and the server's own sentence for why (at least one reason). */
data class PathStop(
    val name: String, val type: String, val owned: Boolean, val reasonCount: Int, val reason: String,
    val displayTitle: String? = null, val displayContext: String? = null,
    val mbid: String? = null,
    /** The server's presentation extras: the song's/label release's album, its artist, and the credited performer. */
    val album: String? = null, val albumArtist: String? = null, val artist: String? = null,
    val reasons: List<PathReason> = emptyList(),
)

/** An entity named inside a reason: the entity it goes through (`via`) or the library item it starts from (`anchor`). */
data class PathRef(val name: String, val type: String, val mbid: String?)

/** One reason the server gives for a stop: its sentence plus the entities it names. */
data class PathReason(val text: String, val code: String, val via: PathRef?, val anchor: PathRef?)

/**
 * The sentence shown for a reason. The server's composition wording ("the work that X performs") reads as if X were a
 * performer, but X is a recording in the library and the work is [PathReason.via]; those two are said with their roles.
 */
fun PathReason.sentence(): String {
    val work = via?.name
    val mine = anchor?.name
    return when {
        code == "same_work" && work != null && mine != null ->
            "Another recording of $work, the same work as $mine, a recording in your library."
        code == "related_work" && work != null && mine != null ->
            "A recording of $work, a work related to the work of $mine, a recording in your library."
        else -> text
    }
}

val PathRef.isArtist get() = type == "artist" || type == "person" || type == "group"

/** The two lines of a row: the main name and the bracketed detail, per kind. A server without presentation never puts a track in the artist slot. */
data class PathHeading(val title: String, val detail: String?)

fun PathStop.heading(kind: PathKind): PathHeading = when (kind) {
    PathKind.FollowTheMusician -> PathHeading(name, album)
    PathKind.LabelPath -> PathHeading(name, albumArtist ?: displayContext)
    // The stop is a recording: the artist is the credited performer, the track goes in brackets.
    PathKind.CompositionPath -> PathHeading(artist ?: displayTitle?.takeIf { it != name } ?: "Artist not listed", name)
    PathKind.SidemanToLeader, PathKind.ScenePath -> PathHeading(name, null)
}

/** A parsed body. [status] is the server's `ok` or `empty`; [truncated] is `rows`, `time`, `stops` or null. */
data class PathsResponse(
    val kind: String, val status: String, val stops: List<PathStop>, val truncated: String?,
    /** The start's entity type (`group`, `person` or `artist`), so wording can fit a band or a single musician. */
    val startType: String = "",
)

/** What the sheet shows for a read: the server's stops, or nothing it can honestly list. */
sealed interface PathsView {
    data class Stops(val response: PathsResponse) : PathsView
    data object Empty : PathsView
}

/** Parses a path body. A body that is not an object, or a stop the app cannot explain, is left out. */
fun parsePaths(body: String): PathsResponse {
    val root = objectOrNull(body)
        ?: return PathsResponse(kind = "", status = "", stops = emptyList(), truncated = null)
    val kind = root.string("kind").orEmpty()
    val stops = (root["stops"] as? JsonArray).orEmpty().mapNotNull { element ->
        val stop = element as? JsonObject ?: return@mapNotNull null
        val entity = stop.obj("entity") ?: return@mapNotNull null
        val name = entity.string("canonical_name")?.trim().orEmpty()
        val reason = (stop["reasons"] as? JsonArray).orEmpty().firstNotNullOfOrNull { r ->
            (r as? JsonObject)?.string("text")?.trim()?.takeIf { it.isNotEmpty() }
        }
        if (name.isEmpty() || reason == null) return@mapNotNull null
        // A placeholder credit ("[unknown]", "[anonymous]") is not an artist the owner can follow.
        if (kind == PathKind.SidemanToLeader.wire && name.isPlaceholderName()) return@mapNotNull null
        PathStop(
            name = name,
            type = entity.string("type").orEmpty(),
            owned = (entity["owned"] as? JsonPrimitive)?.booleanOrNull ?: false,
            reasonCount = stop.int("reason_count") ?: 1,
            reason = reason,
            displayTitle = stop.obj("presentation")?.string("title")?.trim()?.takeIf { it.isNotEmpty() },
            displayContext = stop.obj("presentation")?.string("context")?.trim()?.takeIf { it.isNotEmpty() },
            mbid = entity.string("mbid")?.takeIf { it.isNotBlank() },
            album = stop.obj("presentation")?.string("album")?.trim()?.takeIf { it.isNotEmpty() },
            albumArtist = stop.obj("presentation")?.string("album_artist")?.trim()?.takeIf { it.isNotEmpty() },
            artist = stop.obj("presentation")?.string("artist")?.trim()?.takeIf { it.isNotEmpty() },
            reasons = (stop["reasons"] as? JsonArray).orEmpty().mapNotNull { r ->
                val o = r as? JsonObject ?: return@mapNotNull null
                val text = o.string("text")?.trim()?.takeIf { it.isNotEmpty() } ?: return@mapNotNull null
                PathReason(text, o.string("code").orEmpty(), o.obj("via")?.ref(), o.obj("anchor")?.ref())
            },
        )
    }
    return PathsResponse(
        kind = kind,
        status = root.string("status").orEmpty(),
        stops = stops.dropRepeats(kind),
        truncated = root.string("truncated")?.takeIf { it.isNotBlank() },
        startType = root.obj("start")?.string("type").orEmpty(),
    )
}

private fun String.isPlaceholderName() = startsWith("[") && endsWith("]")

/**
 * One row per place a row leads to: songs that open the same artist (or are the same song) and labels'
 * albums by the same artist collapse to the first. The server does this too; this guards older answers.
 */
private fun List<PathStop>.dropRepeats(kind: String): List<PathStop> {
    if (kind != PathKind.FollowTheMusician.wire && kind != PathKind.LabelPath.wire) return this
    val seen = mutableSetOf<String>()
    return filter { stop ->
        val key = (stop.albumArtist ?: if (kind == PathKind.FollowTheMusician.wire) "song:" + stop.name else null)
            ?.lowercase() ?: return@filter true
        seen.add(key)
    }
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

private fun JsonObject.ref(): PathRef? {
    val name = string("canonical_name")?.trim()?.takeIf { it.isNotEmpty() } ?: return null
    return PathRef(name, string("type").orEmpty(), string("mbid")?.takeIf { it.isNotBlank() })
}
private fun JsonObject.string(name: String) = (this[name] as? JsonPrimitive)?.takeIf { it.isString }?.contentOrNull
private fun JsonObject.int(name: String) = (this[name] as? JsonPrimitive)?.let { it.intOrNull ?: it.doubleOrNull?.toInt() }
private fun JsonObject.obj(name: String) = this[name] as? JsonObject
