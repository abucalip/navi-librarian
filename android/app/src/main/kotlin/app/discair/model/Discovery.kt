package app.discair.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
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
    @SerialName("saved_at") val savedAt: Double? = null,
    val acquired: Boolean = false,
    @SerialName("genre_row_label") val genreRowLabel: String? = null,
) {
    val artistName get() = artist.ifBlank { albumArtist }
}

/**
 * One list row. [raw] is exactly what the server sent; feedback returns it as `metadata`, as the
 * web app does, so the server keeps what it needs without the app interpreting it.
 */
data class DiscoveryEntry(val item: DiscoveryItem, val raw: JsonObject) {
    val key get() = item.artistName.trim().lowercase() + "/" + item.album.trim().lowercase()
}

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
