package app.discair.model

import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.longOrNull

/**
 * An album's images from the Librarian (`GET /api/artwork/index?rgid=&release=`, docs/artwork.md and the "Album artwork"
 * section of docs/SERVER_V2_CONTRACT.md). The server talks to MusicBrainz and the Cover Art Archive; the app only reads
 * this index and the image bytes. Nothing here reads taste or play data, and nothing is shown for an album with no images.
 */
sealed interface ArtworkIndexResult {
    /** `ok`: the index. A truncated one is still shown; [ArtworkIndex.truncatedReason] only says what was left out. */
    data class Ready(val index: ArtworkIndex) : ArtworkIndexResult
    /** Every release answered "no images". Show nothing extra: no placeholder, no empty tab. */
    data object Empty : ArtworkIndexResult
    /** The lookup failed. This says nothing about the album and must never be worded as "no images". */
    data object Unavailable : ArtworkIndexResult
    /** A background build has started; ask again after [retryAfterSeconds]. */
    data class NotLoaded(val retryAfterSeconds: Int) : ArtworkIndexResult
}

/** The index of one release group. [images] are in the server's quality order. */
data class ArtworkIndex(
    val rgid: String,
    /** `null`, `release_cap`, `served_cap` or `partial`. */
    val truncatedReason: String?,
    val releases: ArtworkReleaseCounts,
    /** The id of the best Front image, or `null` when nothing is typed Front (never an artist photo, never an untyped image). */
    val bestFront: Long?,
    /** One best image per type (Front, Back, Spine, Obi, Medium, Tray, Sticker, Poster), keyed by the type name. */
    val slots: Map<String, ArtworkSlot>,
    val booklet: ArtworkBooklet?,
    val images: List<ArtworkImage>,
) {
    private val byId: Map<Long, ArtworkImage> by lazy { images.associateBy { it.imageId } }

    fun image(id: Long): ArtworkImage? = byId[id]

    /** The slot image for [type], or `null` when the album has none; the slot's image can be missing from a trimmed list. */
    fun slotImage(type: String): ArtworkImage? = slots[type]?.let { byId[it.imageId] }

    /** The booklet pages that are in [images], in the server's order. A PDF booklet is one entry. */
    fun bookletImages(): List<ArtworkImage> = booklet?.imageIds.orEmpty().mapNotNull { byId[it] }
}

data class ArtworkReleaseCounts(val total: Int, val fetched: Int, val empty: Int, val failed: Int)

/** A type's best image. [fromOwned] is false when another edition filled in; [edition] then says which. */
data class ArtworkSlot(val imageId: Long, val release: String, val edition: String, val fromOwned: Boolean)

/** The ordered pages of the one release with the most booklet pages. Pages are never mixed across releases. */
data class ArtworkBooklet(val release: String, val edition: String, val imageIds: List<Long>)

data class ArtworkImage(
    val imageId: Long,
    val release: String,
    /** Every fetched release this image is on; the same scan appears once. */
    val releases: List<String>,
    /** "1999 JP CD"; parts MusicBrainz lacked are left out. */
    val edition: String,
    val types: List<String>,
    /** Third-party text: show as plain text, never as markup. */
    val comment: String,
    val approved: Boolean,
    val width: Int?,
    val height: Int?,
    /** The original's file type: `jpg`, `png`, `gif`, `webp` or `pdf`; empty when the server did not say. */
    val format: String,
) {
    /** A PDF original is served only as `size=full`; its thumb and display are a first-page preview image. */
    val isPdf: Boolean get() = format == "pdf"

    /** Untyped images are in no slot; they are only in the full index. */
    val isUntyped: Boolean get() = types.isEmpty()

    /** The text for screen readers and captions: type and edition ("Back cover, 1999 JP CD"), then the comment when there is one. */
    fun label(): String {
        val type = when {
            types.isEmpty() -> "Image"
            types.first() in COVER_TYPES -> "${types.first()} cover"
            else -> types.first()
        }
        val head = if (edition.isBlank()) type else "$type, $edition"
        return if (comment.isBlank()) head else "$head: ${comment.trim()}"
    }

    private companion object {
        val COVER_TYPES = setOf("Front", "Back")
    }
}

/** The sizes `GET /api/artwork/image/{image_id}` serves. `full` is the original (a PDF only here) and is fetched only on zoom or open. */
enum class ArtworkSize(val wire: String) { Thumb("thumb"), Display("display"), Full("full") }

/** The path segments of an image route, ready for the client to encode. */
fun artworkImageSegments(imageId: Long): List<String> = listOf("api", "artwork", "image", imageId.toString())

/** Parses an index body. An answer that is not JSON, or has an unknown `status`, is [ArtworkIndexResult.Unavailable]: it says nothing about the album. */
fun parseArtworkIndex(body: String): ArtworkIndexResult {
    val root = try { ApiJson.parseToJsonElement(body) as? JsonObject } catch (e: SerializationException) { null }
        ?: return ArtworkIndexResult.Unavailable
    return when (root.str("status")) {
        "ok" -> {
            val index = parseIndexBody(root)
            // An "ok" with nothing to show is not an error and not a statement either: show nothing extra.
            if (index.images.isEmpty()) ArtworkIndexResult.Empty else ArtworkIndexResult.Ready(index)
        }
        "empty" -> ArtworkIndexResult.Empty
        // "pending" is the knowledge-base name for the same state (docs/efficiency.md, E1): a fetch is queued, ask again.
        "not_loaded", "pending" -> ArtworkIndexResult.NotLoaded((root.num("retry_after") ?: DEFAULT_RETRY_SECONDS).coerceIn(1, MAX_RETRY_SECONDS))
        else -> ArtworkIndexResult.Unavailable
    }
}

private const val DEFAULT_RETRY_SECONDS = 5
private const val MAX_RETRY_SECONDS = 60

private fun parseIndexBody(root: JsonObject): ArtworkIndex {
    val counts = root.sub("releases")
    return ArtworkIndex(
        rgid = root.str("rgid").orEmpty(),
        truncatedReason = if (root.flag("truncated")) root.str("truncated_reason")?.takeIf { it.isNotBlank() } ?: "partial" else null,
        releases = ArtworkReleaseCounts(
            total = counts?.num("total") ?: 0, fetched = counts?.num("fetched") ?: 0,
            empty = counts?.num("empty") ?: 0, failed = counts?.num("failed") ?: 0,
        ),
        bestFront = root.long("best_front"),
        slots = parseSlots(root.sub("slots")),
        booklet = parseBooklet(root.sub("booklet")),
        images = (root["images"] as? JsonArray).orEmpty().mapNotNull { (it as? JsonObject)?.let(::parseImage) },
    )
}

private fun parseSlots(slots: JsonObject?): Map<String, ArtworkSlot> {
    val out = LinkedHashMap<String, ArtworkSlot>()
    slots?.forEach { (type, value) ->
        val o = value as? JsonObject ?: return@forEach
        val id = o.long("image_id") ?: return@forEach
        out[type] = ArtworkSlot(id, o.str("release").orEmpty(), o.str("edition").orEmpty(), o.flag("from_owned"))
    }
    return out
}

private fun parseBooklet(o: JsonObject?): ArtworkBooklet? {
    o ?: return null
    val ids = (o["image_ids"] as? JsonArray).orEmpty().mapNotNull { (it as? JsonPrimitive)?.longOrNull }
    if (ids.isEmpty()) return null
    return ArtworkBooklet(o.str("release").orEmpty(), o.str("edition").orEmpty(), ids)
}

/** An entry without an id is left out, so one bad entry does not drop the rest. */
private fun parseImage(o: JsonObject): ArtworkImage? {
    val id = o.long("image_id")?.takeIf { it > 0 } ?: return null
    return ArtworkImage(
        imageId = id,
        release = o.str("release").orEmpty(),
        releases = (o["releases"] as? JsonArray).orEmpty().mapNotNull { (it as? JsonPrimitive)?.takeIf { p -> p.isString }?.contentOrNull },
        edition = o.str("edition").orEmpty(),
        types = (o["types"] as? JsonArray).orEmpty().mapNotNull { (it as? JsonPrimitive)?.takeIf { p -> p.isString }?.contentOrNull },
        comment = o.str("comment").orEmpty(),
        approved = o.flag("approved"),
        width = o.num("width"),
        height = o.num("height"),
        format = o.str("format").orEmpty().lowercase(),
    )
}

/**
 * Asks for the index until it is built: the server answers `not_loaded` while its background job runs. Gives up after
 * [tries] answers (nothing extra is shown). A failure of [ask] is [ArtworkIndexResult.Unavailable], never an error shown.
 */
suspend fun loadArtworkIndex(
    tries: Int = 8,
    wait: suspend (Long) -> Unit = { kotlinx.coroutines.delay(it) },
    ask: suspend () -> ArtworkIndexResult,
): ArtworkIndexResult {
    var last: ArtworkIndexResult = ArtworkIndexResult.Unavailable
    repeat(tries) {
        last = try { ask() } catch (e: kotlinx.coroutines.CancellationException) { throw e } catch (e: Exception) { ArtworkIndexResult.Unavailable }
        val pending = last as? ArtworkIndexResult.NotLoaded ?: return last
        wait(pending.retryAfterSeconds * 1000L)
    }
    return if (last is ArtworkIndexResult.NotLoaded) ArtworkIndexResult.Unavailable else last
}

private fun JsonObject.str(name: String) = (this[name] as? JsonPrimitive)?.takeIf { it.isString }?.contentOrNull
private fun JsonObject.num(name: String) = (this[name] as? JsonPrimitive)?.let { it.intOrNull ?: it.doubleOrNull?.toInt() }
private fun JsonObject.long(name: String) = (this[name] as? JsonPrimitive)?.let { it.longOrNull ?: it.doubleOrNull?.toLong() }
private fun JsonObject.flag(name: String) = (this[name] as? JsonPrimitive)?.booleanOrNull ?: false
private fun JsonObject.sub(name: String) = this[name] as? JsonObject
