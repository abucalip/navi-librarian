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
data class PathReason(
    val text: String, val code: String, val via: PathRef?, val anchor: PathRef?,
    /** The anchor's album and that album's artist, when the server sends them (label and composition paths), to look up a cover. */
    val anchorAlbum: String? = null, val anchorAlbumArtist: String? = null,
)

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

/** A page a step can open: an album (needs its artist's name) or an artist (an MBID helps when the server gave one). */
data class PathLink(val album: Boolean, val name: String, val by: String? = null, val mbid: String? = null)

/** One reason on a Follow the musician pane: the server's sentence, and the musician it names, when it names one. */
data class PathCredit(val text: String, val who: PathLink?)

/** One record on a Sideman pane: the release the leader led, and the recording on it the start artist played on. */
data class PathRecord(val release: String, val carries: String?)

/** One label reason on a Label pane: the label, whether it is only a related one, and the library album that shares it. */
data class PathLabelReason(val label: String, val related: Boolean, val anchor: String?, val anchorArtist: String?, val text: String)

/**
 * What a step's detail pane shows. Each path has its own shape because the server sends different facts for each:
 * a song with its credits, a leader with records, an album with a label, a recording with a work, an artist with a place.
 * Nothing here is invented: a fact the server did not send is null or absent, and the pane leaves it out.
 */
sealed interface PathPane {
    /** Where the step opens: the main page first, then the neutral ones. */
    val primary: PathLink?
    val secondary: List<PathLink>
    /** Reasons the server counted but this pane does not list. */
    val moreReasons: Int

    data class Song(
        val title: String, val album: String?, val artist: String?, val credits: List<PathCredit>,
        override val primary: PathLink?, override val secondary: List<PathLink>, override val moreReasons: Int,
    ) : PathPane

    data class Leader(
        val name: String, val typeLabel: String, val records: List<PathRecord>, val otherReasons: List<String>,
        override val primary: PathLink?, override val secondary: List<PathLink>, override val moreReasons: Int,
    ) : PathPane

    data class LabelAlbum(
        val album: String, val artist: String?, val reasons: List<PathLabelReason>,
        override val primary: PathLink?, override val secondary: List<PathLink>, override val moreReasons: Int,
    ) : PathPane

    data class Recording(
        val work: String?, val related: Boolean, val yours: String?, val yoursAlbum: String?, val yoursArtist: String?,
        val track: String, val performer: String?, val album: String?, val albumArtist: String?, val sentence: String,
        override val primary: PathLink?, override val secondary: List<PathLink>, override val moreReasons: Int,
    ) : PathPane

    data class Place(
        val name: String, val typeLabel: String, val place: String?, val anchor: String?, val years: Int?, val sentence: String,
        override val primary: PathLink?, override val secondary: List<PathLink>, override val moreReasons: Int,
    ) : PathPane
}

private const val PANE_REASONS = 3
private const val LABEL_REASONS = 2
private val WITHIN_YEARS = Regex("""within (\d+) years""")

/** The pane label for a stop's entity type ("person" and "group" keep their name; anything else is "Artist"). */
fun typeLabel(type: String) = when (type) {
    "person" -> "Person"
    "group" -> "Group"
    else -> "Artist"
}

/**
 * The pages a step can open, in the order the sheet has always offered them. An album needs its artist's name to be
 * opened, so one without is not offered.
 */
fun PathStop.links(kind: PathKind): List<PathLink> {
    val out = mutableListOf<PathLink>()
    fun artist(name: String, mbid: String?) {
        if (out.none { !it.album && it.name == name }) out += PathLink(false, name, null, mbid)
    }
    fun album(name: String, by: String?) {
        if (by != null) out += PathLink(true, name, by)
    }
    when (kind) {
        PathKind.FollowTheMusician -> {
            reasons.mapNotNull { it.via }.filter { it.isArtist }.distinctBy { it.name }.take(2).forEach { artist(it.name, it.mbid) }
            this.album?.let { album(it, albumArtist) }
            albumArtist?.let { artist(it, null) }
        }
        PathKind.SidemanToLeader -> {
            artist(name, mbid)
            reasons.firstNotNullOfOrNull { it.via?.takeIf { v -> v.type == "release" } }?.let { album(it.name, name) }
        }
        PathKind.LabelPath -> {
            album(name, albumArtist)
            albumArtist?.let { artist(it, null) }
        }
        PathKind.CompositionPath -> artist?.let { artist(it, null) }
        PathKind.ScenePath -> artist(name, mbid)
    }
    return out
}

/** The pane for one step of a path of this kind. */
fun PathStop.pane(kind: PathKind): PathPane {
    val list = reasons.ifEmpty { listOf(PathReason(reason, "", null, null)) }
    return when (kind) {
        PathKind.FollowTheMusician -> {
            val shown = list.take(PANE_REASONS)
            val credited = list.firstNotNullOfOrNull { r -> r.via?.takeIf { it.isArtist }?.let { PathLink(false, it.name, null, it.mbid) } }
            // The album when the server named one, else the album's artist, else the first musician the reasons name.
            val primary = this.album?.takeIf { albumArtist != null }?.let { PathLink(true, it, albumArtist) }
                ?: albumArtist?.let { PathLink(false, it) }
                ?: credited
            PathPane.Song(
                title = name, album = this.album, artist = albumArtist,
                credits = shown.map { r -> PathCredit(r.sentence(), r.via?.takeIf { it.isArtist }?.let { PathLink(false, it.name, null, it.mbid) }) },
                primary = primary,
                secondary = if (primary?.album == true) albumArtist?.let { listOf(PathLink(false, it)) }.orEmpty() else emptyList(),
                moreReasons = (reasonCount - shown.size).coerceAtLeast(0),
            )
        }
        PathKind.SidemanToLeader -> {
            val records = list.mapNotNull { r -> r.via?.takeIf { it.type == "release" }?.let { PathRecord(it.name, r.anchor?.name) } }
                .distinctBy { it.release }.take(PANE_REASONS)
            val others = if (records.isEmpty()) list.take(PANE_REASONS).map { it.sentence() } else emptyList()
            PathPane.Leader(
                name = name, typeLabel = typeLabel(type), records = records, otherReasons = others,
                primary = PathLink(false, name, null, mbid), secondary = emptyList(),
                // Several reasons can name the same release, so the count is of reasons the server sent, not of rows shown.
                moreReasons = (reasonCount - list.size).coerceAtLeast(0),
            )
        }
        PathKind.LabelPath -> {
            val shown = list.take(LABEL_REASONS)
            val primary = albumArtist?.let { PathLink(true, name, it) }
            PathPane.LabelAlbum(
                album = name, artist = albumArtist ?: displayContext,
                reasons = shown.map { r -> PathLabelReason(r.via?.name.orEmpty(), r.code.startsWith("related"), r.anchor?.name, r.anchorAlbumArtist, r.sentence()) },
                primary = primary ?: albumArtist?.let { PathLink(false, it) },
                secondary = if (primary != null) listOf(PathLink(false, albumArtist!!)) else emptyList(),
                moreReasons = (reasonCount - shown.size).coerceAtLeast(0),
            )
        }
        PathKind.CompositionPath -> {
            val r = list.first()
            PathPane.Recording(
                work = r.via?.name, related = r.code.startsWith("related"), yours = r.anchor?.name,
                yoursAlbum = r.anchorAlbum, yoursArtist = r.anchorAlbumArtist,
                track = name, performer = artist, album = this.album, albumArtist = albumArtist, sentence = r.sentence(),
                primary = artist?.let { PathLink(false, it) }, secondary = emptyList(),
                moreReasons = (reasonCount - 1).coerceAtLeast(0),
            )
        }
        PathKind.ScenePath -> {
            val r = list.first()
            PathPane.Place(
                name = name, typeLabel = typeLabel(type), place = r.via?.name, anchor = r.anchor?.name,
                years = WITHIN_YEARS.find(r.text)?.groupValues?.get(1)?.toIntOrNull(), sentence = r.sentence(),
                primary = PathLink(false, name, null, mbid), secondary = emptyList(),
                moreReasons = (reasonCount - 1).coerceAtLeast(0),
            )
        }
    }
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
                val anchored = o.obj("anchor_presentation")
                PathReason(
                    text, o.string("code").orEmpty(), o.obj("via")?.ref(), o.obj("anchor")?.ref(),
                    anchored?.string("album")?.trim()?.takeIf { it.isNotEmpty() },
                    anchored?.string("album_artist")?.trim()?.takeIf { it.isNotEmpty() },
                )
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
