package app.discair.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.decodeFromJsonElement

/** The lists Librarian serves under `GET /api/discovery/{list}`. Names are the server's. */
enum class DiscoveryList(val path: String, val label: String, val empty: String) {
    Daily("daily", "Daily picks", "No daily picks today."),
    DeepDive("artist_deep_dive", "Deep dives", "No deep dives yet."),
    NewReleases("new_releases", "New releases", "No new releases found."),
    Classics("classics", "Add to your collection", "No suggestions yet."),
    Personal("personal", "Personal discoveries", "No personal discoveries yet."),
    Saved("for_me", "Saved", "Nothing saved yet."),
    /** Not a discovery list: Server V2 insight cards (`GET /api/insights`), shown by their own page. */
    Insights("insights", "Insights", "No insights yet."),
}

/** The four daily lens lists, fetched one after the other for the Daily picks page. */
val LensLists = listOf(
    "repeated_tracks" to "Repeated tracks",
    "deep_cuts" to "Deep cuts",
    "obsessions" to "Obsessions",
    "current_tastes" to "Current tastes",
)

/** Raw body of a list route. Rows arrive in `items` (or `recommendations`) in the order to show. */
@Serializable
data class DiscoveryBody(
    val items: List<JsonObject> = emptyList(),
    val recommendations: List<JsonObject> = emptyList(),
    @SerialName("generated_at") val generatedAt: Double? = null,
    val disabled: Boolean = false,
    val message: String? = null,
)

/** Fields the row shows. Anything else the server sent stays in [DiscoveryEntry.raw]. */
@Serializable
data class DiscoveryItem(
    val artist: String = "",
    @SerialName("album_artist") val albumArtist: String = "",
    val album: String = "",
    val year: Int? = null,
    @SerialName("first_release_date") val firstReleaseDate: String? = null,
    @SerialName("lastfm_listeners") val listeners: Long? = null,
    @SerialName("album_listeners") val albumListeners: Long? = null,
    @SerialName("seed_tag") val seedTag: String? = null,
    val reason: String = "",
    val genres: List<String> = emptyList(),
    @SerialName("similar_to") val similarTo: List<String> = emptyList(),
    /** Star Operation S1c: `{kind, names}` from the server. Kept as JSON so a bad value drops only the reason line. */
    val because: JsonElement? = null,
    @SerialName("saved_at") val savedAt: Double? = null,
    val acquired: Boolean = false,
    @SerialName("genre_row_label") val genreRowLabel: String? = null,
    /** The lens a lens-list album came from (`repeated_tracks`, `deep_cuts`, ...); with [seedTag] it says why the album is there. */
    val lens: String? = null,
    /** Collection (classics): how many albums by this artist the library holds. */
    @SerialName("artist_library_album_count") val libraryAlbumCount: Int? = null,
) {
    val artistName get() = artist.ifBlank { albumArtist }
}

/**
 * The reason line for a personal pick (Star Operation S1c, DISC-09). `tag` is a real seed and reads
 * "Because you listen to ..."; `similar_artists` is genre overlap and reads "Shares genres with ...".
 * Any other kind, or no usable names, gives no `because` reason. An older server sends only `similar_to`,
 * the same overlap, so that gets the overlap wording as a fallback. Empty when there is nothing honest to say.
 */
fun pickReason(because: JsonElement?, similarTo: List<String>): String {
    val obj = because as? JsonObject
    val kind = (obj?.get("kind") as? JsonPrimitive)?.takeIf { it.isString }?.content
    val names = (obj?.get("names") as? JsonArray).orEmpty().mapNotNull { element ->
        (element as? JsonPrimitive)?.takeIf { it.isString }?.content?.takeIf { it.isNotBlank() }
    }
    if (names.isNotEmpty()) when (kind) {
        "tag" -> return "Because you listen to " + names.joinToString(", ")
        "similar_artists" -> return "Shares genres with " + names.joinToString(", ")
    }
    val overlap = similarTo.filter { it.isNotBlank() }
    return if (overlap.isEmpty()) "" else "Shares genres with " + overlap.joinToString(", ")
}

/**
 * One list row. [raw] is exactly what the server sent; feedback returns it as `metadata`, as the
 * web app does, so the server keeps what it needs without the app interpreting it.
 */
data class DiscoveryEntry(val item: DiscoveryItem, val raw: JsonObject) {
    val key get() = item.artistName.trim().lowercase() + "/" + item.album.trim().lowercase()
}

/**
 * The genres an entry carries: `genres` on the lists, `tags` on the lens lists (the server matches a block on either, so the
 * menu offers both). A lens album's own `lens` name rides along with a lean.
 */
fun entryGenres(entry: DiscoveryEntry): List<String> {
    val tags = (entry.raw["tags"] as? JsonArray).orEmpty().mapNotNull { (it as? JsonPrimitive)?.takeIf { p -> p.isString }?.content }
    return entry.item.genres + tags
}

fun entryLens(entry: DiscoveryEntry): String? =
    (entry.raw["lens"] as? JsonPrimitive)?.takeIf { it.isString }?.content?.takeIf { it.isNotBlank() }

data class DiscoveryResult(val entries: List<DiscoveryEntry>, val disabled: Boolean, val message: String?)

fun parseDiscovery(body: String): DiscoveryResult {
    val parsed = ApiJson.decodeFromString(DiscoveryBody.serializer(), body)
    val rows = parsed.items.ifEmpty { parsed.recommendations }
    val entries = rows.mapNotNull { raw ->
        val item = ApiJson.decodeFromJsonElement<DiscoveryItem>(raw)
        // Rows without an album title are not albums; the web list skips them too.
        if (item.album.isBlank()) null else DiscoveryEntry(item, raw)
    }
    return DiscoveryResult(entries, parsed.disabled, parsed.message)
}

/** Feedback actions the server accepts. */
enum class FeedbackAction(val wire: String) {
    Save("save"), Dismiss("dismiss"), DismissArtist("dismiss_artist"), RemoveSaved("remove_for_me")
}

@Serializable
data class FeedbackReply(val ok: Boolean = false, val error: String? = null)

fun feedbackBody(action: FeedbackAction, artist: String, album: String, metadata: JsonObject): String =
    JsonObject(
        mapOf(
            "artist" to JsonPrimitive(artist),
            "album" to JsonPrimitive(album),
            "action" to JsonPrimitive(action.wire),
            "metadata" to metadata,
        ),
    ).toString()

// ---- Blocklist (Star Operation S2c: /api/discovery/blocked-genres, blocked-artists, artist-lean)

/** What the owner told the server to leave out of picks, or to lean on. A block hides picks only; it never touches the library. */
data class Blocklist(
    val genres: List<String> = emptyList(),
    /** Artists hidden by "Not this artist". */
    val hiddenArtists: List<String> = emptyList(),
    val leans: List<ArtistLean> = emptyList(),
)

enum class Lean(val wire: String) { More("more"), Less("less") }

data class ArtistLean(val artist: String, val lean: Lean)

@Serializable
private data class GenreRow(val genre: String = "")

@Serializable
private data class ArtistRow(val artist: String = "", val lean: String = "")

@Serializable
private data class GenreRows(val genres: List<GenreRow> = emptyList())

@Serializable
private data class ArtistRows(val artists: List<ArtistRow> = emptyList())

fun parseBlockedGenres(body: String): List<String> =
    ApiJson.decodeFromString(GenreRows.serializer(), body).genres.map { it.genre }.filter { it.isNotBlank() }

fun parseBlockedArtists(body: String): List<String> =
    ApiJson.decodeFromString(ArtistRows.serializer(), body).artists.map { it.artist }.filter { it.isNotBlank() }

/** Rows with a lean the app does not know are dropped, so a newer server cannot break the screen. */
fun parseArtistLeans(body: String): List<ArtistLean> =
    ApiJson.decodeFromString(ArtistRows.serializer(), body).artists.mapNotNull { row ->
        val lean = Lean.entries.firstOrNull { it.wire == row.lean }
        if (row.artist.isBlank() || lean == null) null else ArtistLean(row.artist, lean)
    }

fun genreBody(genre: String): String = JsonObject(mapOf("genre" to JsonPrimitive(genre))).toString()

fun artistBody(artist: String): String = JsonObject(mapOf("artist" to JsonPrimitive(artist))).toString()

/** The server keeps only `genres` and `lens` of [genres] and [lens], so only those are sent. */
fun leanBody(artist: String, lean: Lean, genres: List<String>, lens: String? = null): String {
    val metadata = buildMap<String, kotlinx.serialization.json.JsonElement> {
        if (genres.isNotEmpty()) put("genres", JsonArray(genres.map { JsonPrimitive(it) }))
        if (!lens.isNullOrBlank()) put("lens", JsonPrimitive(lens))
    }
    return JsonObject(
        mapOf("artist" to JsonPrimitive(artist), "lean" to JsonPrimitive(lean.wire), "metadata" to JsonObject(metadata)),
    ).toString()
}

/** The genres a card may offer to block: the album's own, trimmed and without repeats (the server matches on these). */
fun blockableGenres(genres: List<String>, limit: Int = 3): List<String> =
    genres.map { it.trim().replace(Regex("\\s+"), " ") }.filter { it.isNotEmpty() }
        .distinctBy { it.lowercase() }.take(limit)

// ---- Search (GET /api/search, server-sent events)

@Serializable
data class SearchResult(
    val type: String = "",
    val owned: Boolean = false,
    val id: String = "",
    val key: String = "",
    val name: String = "",
    val mbid: String? = null,
    @SerialName("artwork_url") val artworkUrl: String? = null,
    @SerialName("album_count") val albumCount: Int? = null,
    val genre: String? = null,
    val artist: String? = null,
    @SerialName("artist_key") val artistKey: String? = null,
    val year: Int? = null,
    val album: String? = null,
    val tag: String? = null,
    /** For a song result: the Navidrome album it is on, its length and its place (the server sends these). */
    @SerialName("album_id") val albumId: String? = null,
    val duration: Int? = null,
    @SerialName("track_number") val trackNumber: Int? = null,
    /** For an owned song: the file's details (`year` above). Absent or null when the library lacks them. */
    val suffix: String? = null,
    @SerialName("bit_rate") val bitRate: Int? = null,
    @SerialName("bit_depth") val bitDepth: Int? = null,
    @SerialName("sampling_rate") val samplingRate: Int? = null,
    val quality: String? = null,
)

@Serializable
data class SourceState(val source: String = "", val state: String = "")

sealed interface SearchEvent {
    data class Result(val result: SearchResult) : SearchEvent
    data class Source(val source: SourceState) : SearchEvent
    data class Done(val partial: Boolean) : SearchEvent
    data class Error(val message: String) : SearchEvent
    data object Capabilities : SearchEvent
}

/** Decodes one SSE event; unknown event names are ignored (null). */
fun parseSearchEvent(name: String, data: String): SearchEvent? = try {
    when (name) {
        "capabilities" -> SearchEvent.Capabilities
        "result" -> SearchEvent.Result(ApiJson.decodeFromString(SearchResult.serializer(), data))
        "source" -> SearchEvent.Source(ApiJson.decodeFromString(SourceState.serializer(), data))
        "done" -> SearchEvent.Done(ApiJson.decodeFromString(Done.serializer(), data).partial)
        "error" -> SearchEvent.Error(
            (ApiJson.parseToJsonElement(data) as? JsonObject)?.get("message")?.let { (it as? JsonPrimitive)?.content }
                ?: "The search failed.",
        )
        else -> null
    }
} catch (e: Exception) {
    null
}
