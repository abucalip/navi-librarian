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
import kotlin.random.Random

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
    /** More releases that carry the song, best cover guess first, so a cover that is not found can fall back to the next. */
    val albums: List<PathAlbum> = emptyList(),
    /** Scene: the year this artist's career began, and the start artist's. */
    val beginYear: Int? = null, val anchorBeginYear: Int? = null,
)

/** A release and the artist it is credited to: the pair a cover is looked up by. */
data class PathAlbum(val album: String, val artist: String)

/** A stored credit behind a reason: the relation (`instrument`, `vocal`, `producer`...) and its role (the instrument). */
data class PathCreditFact(val relation: String, val role: String?)

/** An entity named inside a reason: the entity it goes through (`via`) or the library item it starts from (`anchor`). */
data class PathRef(val name: String, val type: String, val mbid: String?)

/** One reason the server gives for a stop: its sentence plus the entities it names. */
data class PathReason(
    val text: String, val code: String, val via: PathRef?, val anchor: PathRef?,
    /** The anchor's album and that album's artist, when the server sends them (label and composition paths), to look up a cover. */
    val anchorAlbum: String? = null, val anchorAlbumArtist: String? = null,
    /** The credits the server stored for this reason: first the start's side (the library song), then the stop's. */
    val credits: List<PathCreditFact> = emptyList(),
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

/** A piece of a sentence; [title] pieces are song or album names and are shown in italics. */
data class Span(val text: String, val title: Boolean = false)

/** One record on a Sideman pane: the release the leader led, the recording on it the start artist worked on, and how. */
data class PathRecord(val release: String, val carries: String?, val credit: PathCreditFact?)

/** The label on a Label pane, whether it is only a related one, and the library album that shares it. */
data class PathLabelReason(val label: String, val related: Boolean, val anchor: String?, val anchorArtist: String?, val text: String)

/**
 * What a step's detail pane shows. Each path has its own shape because the server sends different facts for each.
 * Nothing here is invented: a fact the server did not send is null or absent, and the pane leaves it out.
 */
sealed interface PathPane {
    /** Follow the musician: the story of the credit that links the song, the musician and the album to open. */
    data class Song(
        val title: String, val album: String?, val artist: String?, val covers: List<PathAlbum>,
        val story: List<Span>, val musician: PathLink?,
    ) : PathPane

    data class Leader(
        val name: String, val typeLabel: String, val mbid: String?, val records: List<PathRecord>, val otherReasons: List<String>,
    ) : PathPane

    data class LabelAlbum(
        val album: String, val artist: String?, val reason: PathLabelReason?, val covers: List<PathAlbum>, val sentence: String,
    ) : PathPane

    data class Recording(
        val work: String?, val related: Boolean, val yoursAlbum: String?, val yoursArtist: String?,
        val track: String, val performer: String?, val album: String?, val albumArtist: String?, val covers: List<PathAlbum>,
        val sentence: String,
    ) : PathPane

    data class Place(
        val name: String, val typeLabel: String, val place: String?, val anchor: String?, val years: Int?, val era: String?,
        val sentence: String, val mbid: String?,
    ) : PathPane
}

private const val PANE_REASONS = 3
private val WITHIN_YEARS = Regex("""within (\d+) years""")
private val ROLE_NOISE = setOf("additional", "guest", "solo")

/** An instrument as it reads in a sentence: "additional, guitar" is "guitar", "drums (drum set)" is "drums". */
internal fun cleanRole(role: String?): String? = role
    ?.replace(Regex("""\s*\(.*?\)"""), "")?.split(",")?.map { it.trim() }?.filter { it.isNotEmpty() && it !in ROLE_NOISE }
    ?.joinToString(" and ")?.ifBlank { null }

/**
 * What a credit says about the musician, ending in "on" when an object follows: "plays drums on", "sings on", "produces".
 * A credit the app has no word for is "is credited on".
 */
internal fun creditPhrase(credit: PathCreditFact?, past: Boolean): String {
    fun tense(now: String, then: String) = if (past) then else now
    val role = cleanRole(credit?.role)
    return when (credit?.relation) {
        "instrument" -> if (role != null) "${tense("plays", "played")} $role on" else "${tense("plays", "played")} on"
        "vocal" -> tense("sings on", "sang on")
        "producer" -> tense("produces", "produced")
        "main performer", "performer", "performing orchestra" -> tense("performs on", "performed on")
        else -> tense("is credited on", "was credited on")
    }
}

/** "A", "A and B", "A, B and C" as title spans. */
private fun titleList(names: List<String>): List<Span> = names.flatMapIndexed { i, n ->
    val sep = when {
        i == 0 -> ""
        i == names.lastIndex -> " and "
        else -> ", "
    }
    listOfNotNull(sep.takeIf { it.isNotEmpty() }?.let { Span(it) }, Span(n, title = true))
}

/** The era two start years share: the decade they fall in ("1960s"), the one the midpoint is in. */
internal fun eraOf(a: Int, b: Int): String = "${(a + b) / 2 / 10 * 10}s"

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

/**
 * The pane for one step of a path of this kind. Where the server sent more reasons than a pane shows, [random] picks which,
 * so a step reads differently each time it is opened.
 */
fun PathStop.pane(kind: PathKind, startName: String = "", random: Random = Random.Default): PathPane {
    val list = reasons.ifEmpty { listOf(PathReason(reason, "", null, null)) }
    val covers = albums.ifEmpty { if (album != null && albumArtist != null) listOf(PathAlbum(album, albumArtist)) else emptyList() }
    return when (kind) {
        PathKind.FollowTheMusician -> {
            // One musician linked this song to the library: pick one of them, and up to three songs of the start's they share.
            val byMusician = list.filter { it.via?.isArtist == true }.groupBy { it.via!!.name }
            val chosen = byMusician.values.toList().takeIf { it.isNotEmpty() }?.let { it[random.nextInt(it.size)] }
            val story: List<Span>
            var musician: PathLink? = null
            if (chosen != null) {
                val who = chosen.first().via!!
                musician = PathLink(false, who.name, null, who.mbid)
                val first = chosen.shuffled(random).first()
                val phrase = creditPhrase(first.credits.firstOrNull(), past = false)
                val songs = chosen.filter { creditPhrase(it.credits.firstOrNull(), false) == phrase }
                    .mapNotNull { it.anchor?.name }.distinct().shuffled(random).take(PANE_REASONS)
                val also = creditPhrase(first.credits.getOrNull(1), past = false)
                story = buildList {
                    add(Span(who.name)); add(Span(", who $phrase "))
                    if (songs.isNotEmpty()) {
                        addAll(titleList(songs))
                        if (startName.isNotBlank()) add(Span(" by $startName"))
                    } else add(Span("a recording in your library"))
                    add(Span(", also $also ")); add(Span(name, title = true))
                    albumArtist?.let { add(Span(" by $it")) }
                    add(Span("."))
                }
            } else story = listOf(Span(list.first().sentence()))
            PathPane.Song(title = name, album = album, artist = albumArtist, covers = covers, story = story, musician = musician)
        }
        PathKind.SidemanToLeader -> {
            val records = list.mapNotNull { r ->
                r.via?.takeIf { it.type == "release" }?.let { PathRecord(it.name, r.anchor?.name, r.credits.firstOrNull()) }
            }.distinctBy { it.release }.shuffled(random).take(PANE_REASONS)
            val others = if (records.isEmpty()) list.take(PANE_REASONS).map { it.sentence() } else emptyList()
            PathPane.Leader(name = name, typeLabel = typeLabel(type), mbid = mbid, records = records, otherReasons = others)
        }
        PathKind.LabelPath -> {
            // One label is shown: the same one at every opening only when there is just one.
            val r = list.filter { it.via != null }.let { if (it.isEmpty()) list.first() else it[random.nextInt(it.size)] }
            PathPane.LabelAlbum(
                album = name, artist = albumArtist ?: displayContext,
                reason = r.via?.let { PathLabelReason(it.name, r.code.startsWith("related"), r.anchor?.name, r.anchorAlbumArtist, r.sentence()) },
                covers = covers, sentence = r.sentence(),
            )
        }
        PathKind.CompositionPath -> {
            val r = list[random.nextInt(list.size)]
            PathPane.Recording(
                work = r.via?.name, related = r.code.startsWith("related"),
                yoursAlbum = r.anchorAlbum, yoursArtist = r.anchorAlbumArtist,
                track = name, performer = artist, album = album, albumArtist = albumArtist, covers = covers, sentence = r.sentence(),
            )
        }
        PathKind.ScenePath -> {
            val r = list[random.nextInt(list.size)]
            val years = WITHIN_YEARS.find(r.text)?.groupValues?.get(1)?.toIntOrNull()
            PathPane.Place(
                name = name, typeLabel = typeLabel(type), place = r.via?.name, anchor = r.anchor?.name, years = years,
                era = if (beginYear != null && anchorBeginYear != null) eraOf(beginYear, anchorBeginYear) else null,
                sentence = r.sentence(), mbid = mbid,
            )
        }
    }
}

/** A parsed body. [status] is the server's `ok` or `empty`; [truncated] is `rows`, `time`, `stops` or null. */
data class PathsResponse(
    val kind: String, val status: String, val stops: List<PathStop>, val truncated: String?,
    /** The start's entity type (`group`, `person` or `artist`), so wording can fit a band or a single musician. */
    val startType: String = "",
    /** Album paths: stops left out because the artist paths already reach them (never hidden from the count). */
    val overlapDropped: Int = 0,
    /** Album paths: people or works whose albums were cut at the cap, with how many were left out. */
    val capped: List<PathCapped> = emptyList(),
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
            albums = stop.obj("presentation")?.get("albums").let { it as? JsonArray }.orEmpty().mapNotNull { a ->
                val o = a as? JsonObject ?: return@mapNotNull null
                val album = o.string("album")?.trim()?.takeIf { it.isNotEmpty() } ?: return@mapNotNull null
                PathAlbum(album, o.string("album_artist")?.trim()?.takeIf { it.isNotEmpty() } ?: return@mapNotNull null)
            },
            beginYear = stop.obj("presentation")?.int("begin_year"),
            anchorBeginYear = stop.obj("presentation")?.int("anchor_begin_year"),
            reasons = (stop["reasons"] as? JsonArray).orEmpty().mapNotNull { r ->
                val o = r as? JsonObject ?: return@mapNotNull null
                val text = o.string("text")?.trim()?.takeIf { it.isNotEmpty() } ?: return@mapNotNull null
                val anchored = o.obj("anchor_presentation")
                PathReason(
                    text, o.string("code").orEmpty(), o.obj("via")?.ref(), o.obj("anchor")?.ref(),
                    anchored?.string("album")?.trim()?.takeIf { it.isNotEmpty() },
                    anchored?.string("album_artist")?.trim()?.takeIf { it.isNotEmpty() },
                    (o["evidence"] as? JsonArray).orEmpty().mapNotNull { e ->
                        val ev = e as? JsonObject ?: return@mapNotNull null
                        ev.string("relation")?.let { PathCreditFact(it, ev.string("role")?.trim()?.takeIf { r -> r.isNotEmpty() }) }
                    },
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
        overlapDropped = root.int("overlap_dropped") ?: 0,
        capped = parseCapped(root),
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
