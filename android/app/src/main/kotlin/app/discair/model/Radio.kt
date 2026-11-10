package app.discair.model

import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull

/**
 * Internet radio (docs/RADIO_PLAYBACK_CONTRACT.md sections 3.1 to 3.5). The server owns "what is playing"; these
 * types only read what it says. Nothing here splits artist and title or decides what can be downloaded beyond the
 * contract's one rule ([RadioNow.canDownload]).
 */
data class RadioStation(
    val id: String,
    val name: String,
    /** True when the server relays the station (live title and Download are possible). */
    val proxied: Boolean,
    /** What the player opens: the relay address when proxied, else the station's own. Never shown or logged. */
    val playableUrl: String,
    val homepageUrl: String?,
    /** A server path, always present (the generated tile is served when nothing else is found). */
    val logoUrl: String,
    val favourite: Boolean,
    val tags: List<String>,
    val lastPlayedAt: Double?,
)

/** The state of a live song (contract 3.2). [Idle] is slice 2's addition: nobody is listening, so the server holds no title. */
enum class RadioNowState { Ok, NoMetadata, Unparsed, NotProxied, Unavailable, Idle;
    companion object {
        /** An unknown word from a newer server reads as [Unavailable]: honest text, never a dead Download button. */
        fun from(word: String?): RadioNowState = when (word) {
            "ok" -> Ok
            "no_metadata" -> NoMetadata
            "unparsed" -> Unparsed
            "not_proxied" -> NotProxied
            "idle" -> Idle
            else -> Unavailable
        }
    }
}

data class RadioNow(
    val state: RadioNowState,
    val rawTitle: String?,
    val artist: String?,
    val title: String?,
    val playId: Long?,
    val inLibrary: Boolean,
    val coverUrl: String?,
) {
    /** Contract 3.2: Download is enabled only when the state is `ok` and the song has been heard long enough to have a play id. */
    val canDownload: Boolean get() = state == RadioNowState.Ok && playId != null

    /** The song line for a strip: "Artist - Title" when parsed, else the raw title, else null. */
    val songLine: String? get() = when {
        state == RadioNowState.Ok && !artist.isNullOrBlank() && !title.isNullOrBlank() -> "$artist - $title"
        !rawTitle.isNullOrBlank() -> rawTitle
        else -> null
    }

    companion object {
        val Unknown = RadioNow(RadioNowState.Unavailable, null, null, null, null, false, null)
    }
}

/** One row of `GET /api/radio/now`: the live song of a relayed station. */
data class RadioNowItem(val stationId: String, val now: RadioNow)

private fun parseObject(body: String): JsonObject? = try {
    ApiJson.parseToJsonElement(body) as? JsonObject
} catch (e: SerializationException) {
    null
}

private fun JsonObject.text(name: String) = (this[name] as? JsonPrimitive)?.takeIf { it.isString }?.contentOrNull
private fun JsonObject.flag(name: String) = (this[name] as? JsonPrimitive)?.booleanOrNull
private fun JsonObject.long(name: String) = (this[name] as? JsonPrimitive)?.let { it.intOrNull?.toLong() ?: it.doubleOrNull?.toLong() }

private fun JsonObject.toNow() = RadioNow(
    state = RadioNowState.from(text("state")),
    rawTitle = text("raw_title")?.takeIf { it.isNotBlank() },
    artist = text("artist")?.takeIf { it.isNotBlank() },
    title = text("title")?.takeIf { it.isNotBlank() },
    playId = long("play_id"),
    inLibrary = flag("in_library") ?: false,
    coverUrl = text("cover_url")?.takeIf { it.isNotBlank() },
)

/**
 * Parses `GET /api/radio/stations`. A station without an id, name or playable address cannot be played and is left out.
 * The server's order (favourites first, then last played, then name) is kept. An unreadable body is an empty list.
 */
fun parseRadioStations(body: String): List<RadioStation> {
    val items = parseObject(body)?.get("items") as? JsonArray ?: return emptyList()
    return items.mapNotNull { element ->
        val o = element as? JsonObject ?: return@mapNotNull null
        val id = o.text("id")?.takeIf { it.isNotBlank() } ?: return@mapNotNull null
        val name = o.text("name")?.takeIf { it.isNotBlank() } ?: return@mapNotNull null
        val playable = (o.text("playable_url") ?: o.text("stream_url"))?.takeIf { it.isNotBlank() } ?: return@mapNotNull null
        RadioStation(
            id = id,
            name = name,
            proxied = o.flag("proxied") ?: false,
            playableUrl = playable,
            homepageUrl = o.text("homepage_url")?.takeIf { it.isNotBlank() },
            logoUrl = o.text("logo_url")?.takeIf { it.isNotBlank() } ?: "/api/radio/stations/$id/logo",
            favourite = o.flag("favourite") ?: false,
            tags = (o["tags"] as? JsonArray).orEmpty().mapNotNull { (it as? JsonPrimitive)?.takeIf { p -> p.isString }?.content },
            lastPlayedAt = (o["last_played_at"] as? JsonPrimitive)?.doubleOrNull,
        )
    }
}

/** Parses `GET /api/radio/stations/{id}/now`. An unreadable body is [RadioNow.Unknown], which reads as unreachable. */
fun parseRadioNow(body: String): RadioNow = parseObject(body)?.toNow() ?: RadioNow.Unknown

/** Parses `GET /api/radio/now` into station id to live song. Rows without an id are left out. */
fun parseRadioNowAll(body: String): List<RadioNowItem> {
    val items = parseObject(body)?.get("items") as? JsonArray ?: return emptyList()
    return items.mapNotNull { element ->
        val o = element as? JsonObject ?: return@mapNotNull null
        val id = o.text("id")?.takeIf { it.isNotBlank() } ?: return@mapNotNull null
        RadioNowItem(id, o.toNow())
    }
}

/** Reads `favourite` from the answer to `PUT /api/radio/stations/{id}/favourite`; null when the body does not say. */
fun parseRadioFavourite(body: String): Boolean? = parseObject(body)?.flag("favourite")

/** The words for a live strip (contract section 6). Every state has text, never colour alone. */
fun radioNowText(now: RadioNow, proxied: Boolean): String = when (now.state) {
    RadioNowState.Ok -> now.songLine ?: "Song title not available yet."
    RadioNowState.Unparsed -> (now.rawTitle ?: "On air") + " (could not be matched to an artist and song)"
    RadioNowState.NoMetadata -> "This station sends no song titles."
    RadioNowState.NotProxied -> "Live titles need the relay switched on for this station."
    RadioNowState.Unavailable -> "Station unreachable."
    RadioNowState.Idle -> if (proxied) "Tune in to see what is on." else "Live titles need the relay switched on for this station."
}
