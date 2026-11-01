package app.discair.model

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.put

// ---- Acquisition records (GET /api/acquisitions and its SSE stream, contract 5.3)

/** How a status is emphasised. The label and icon carry the state; tone only adds colour (rule 4). */
enum class Tone { Active, Caution, Error, Ok, Muted }

data class StatusInfo(val label: String, val tone: Tone)

/** The server's job statuses with the web's wording (`ACQUISITION_STATUS_TABLE` in `static/app.js`). */
private val STATUS_TABLE = mapOf(
    "searching" to StatusInfo("Searching sources", Tone.Active),
    "requested" to StatusInfo("Requested", Tone.Active),
    "queued" to StatusInfo("Queued", Tone.Active),
    "queued_unconfirmed" to StatusInfo("Queued, not yet confirmed", Tone.Caution),
    "downloading" to StatusInfo("Downloading", Tone.Active),
    "download_complete_waiting_for_folder" to StatusInfo("Download complete, waiting for folder", Tone.Active),
    "importing" to StatusInfo("Importing", Tone.Active),
    "imported" to StatusInfo("Imported", Tone.Ok),
    "monitoring" to StatusInfo("Monitoring download", Tone.Active),
    "recovery_started" to StatusInfo("Recovery started", Tone.Active),
    "queue_uncertain" to StatusInfo("Queue status uncertain", Tone.Caution),
    "review_required" to StatusInfo("Needs review", Tone.Caution),
    "source_switching" to StatusInfo("Switching source", Tone.Active),
    "skip_requested" to StatusInfo("Skip requested", Tone.Active),
    "retry_requested" to StatusInfo("Retry requested", Tone.Active),
    "dismissed" to StatusInfo("Dismissed", Tone.Muted),
    "no_matches" to StatusInfo("No matches found", Tone.Error),
    "queue_failed" to StatusInfo("Could not queue", Tone.Error),
    "settings_required" to StatusInfo("Settings required", Tone.Error),
    "slskd_error" to StatusInfo("Soulseek connection error", Tone.Error),
    "download_failed" to StatusInfo("Download failed", Tone.Error),
    "download_complete_move_failed" to StatusInfo("Could not move download", Tone.Error),
    "source_switch_failed" to StatusInfo("Source switch failed", Tone.Error),
    "monitor_error" to StatusInfo("Monitor error", Tone.Error),
    "monitor_timeout" to StatusInfo("Monitor timed out", Tone.Error),
    "monitor_recovery_failed" to StatusInfo("Recovery failed", Tone.Error),
    "recovery_unavailable" to StatusInfo("Recovery unavailable", Tone.Error),
    "error" to StatusInfo("Error", Tone.Error),
    "failed" to StatusInfo("Failed", Tone.Error),
)

/** A status missing from the table still shows its own name, never a blank. */
fun statusInfo(status: String): StatusInfo {
    val key = status.lowercase()
    STATUS_TABLE[key]?.let { return it }
    val name = key.replace('_', ' ').ifBlank { "unknown status" }
    return StatusInfo(name.replaceFirstChar { it.uppercase() }, Tone.Muted)
}

/** Statuses the web nav counts as an active download (`ACTIVE_DOWNLOAD_STATUSES`). */
private val ACTIVE_STATUSES = setOf(
    "searching", "requested", "queued", "downloading", "download_complete_waiting_for_folder",
    "importing", "queue_uncertain", "recovery_started", "monitoring",
)

/** The statuses that offer Try again (web `retryableStatuses`). */
private val RETRYABLE_STATUSES = setOf("no_matches", "queue_failed", "settings_required", "slskd_error")

private val QUALITY_LABELS = mapOf(
    "mp3_320" to "MP3 320 kbps",
    "mp3_193_319" to "MP3 193–319 kbps",
    "mp3_192" to "MP3 192 kbps",
    "flac_cd" to "FLAC / CD quality",
    "flac_16_44" to "FLAC 16-bit / 44.1 kHz",
)

/** Seconds after a stall before the server accepts "use next source" (the web counts down 15 s). */
const val SKIP_WAIT_SECONDS = 15

/** `live_progress` of a downloading job; every figure may be missing. */
data class LiveProgress(
    val percent: Double?,
    val speedBytesPerSecond: Double?,
    val totalTracks: Int?,
    val remainingTracks: Int?,
    val totalSizeBytes: Double?,
    val remainingSizeBytes: Double?,
)

/**
 * One acquisition record. [raw] keeps the whole `details` object so a retry can send back the
 * `metadata` the server stored, exactly as the web app does.
 */
data class AcquisitionJob(
    val artist: String,
    val album: String,
    val status: String,
    val createdAt: Double,
    val updatedAt: Double?,
    val details: JsonObject,
) {
    private fun text(name: String) = (details[name] as? JsonPrimitive)?.takeIf { it.isString }?.content?.takeIf { it.isNotBlank() }
    private fun number(name: String) = (details[name] as? JsonPrimitive)?.doubleOrNull

    /** Same identity the web uses for a row: artist and album, lower-cased. */
    val key get() = artist.lowercase() + "::" + album.lowercase()

    val info get() = statusInfo(status)
    val isSong get() = text("kind") == "track"

    /** A song's row is named after the song and shows the album it belongs to. */
    val title get() = if (isSong) text("track_title") ?: album.ifBlank { "Unknown song" } else album.ifBlank { "Unknown album" }
    val albumName get() = (if (isSong) text("album_name") else album) ?: "Unknown album"
    val artistName get() = artist.ifBlank { "Unknown artist" }
    val trackNumber get() = number("track_number")?.toInt()?.takeIf { it > 0 }
    val year get() = number("year")?.toInt()?.takeIf { it > 0 }

    val isActive get() = status.lowercase() in ACTIVE_STATUSES
    val canRetry get() = status.lowercase() in RETRYABLE_STATUSES
    val canDismiss get() = status.lowercase() != "dismissed"
    val isImported get() = status.lowercase() == "imported"

    val message get() = text("message")
    val error get() = text("error")
    val peer get() = text("source_username")

    val qualityProfile: String get() {
        val values = (details["quality_summary"] as? kotlinx.serialization.json.JsonArray)
            ?.mapNotNull { (it as? JsonPrimitive)?.contentOrNull } ?: emptyList()
        return if (values.isEmpty()) "Not reported"
        else values.joinToString(" · ") { QUALITY_LABELS[it] ?: it.replace('_', ' ') }
    }

    /** The metadata the server stored for this request; sent back unchanged on Try again. */
    val metadata: JsonObject get() = details["metadata"] as? JsonObject ?: JsonObject(emptyMap())

    val progress: LiveProgress? get() {
        if (status.lowercase() !in setOf("downloading", "download_complete_waiting_for_folder")) return null
        val p = details["live_progress"] as? JsonObject ?: return null
        fun n(name: String) = (p[name] as? JsonPrimitive)?.doubleOrNull
        return LiveProgress(
            percent = n("percent")?.coerceIn(0.0, 100.0),
            speedBytesPerSecond = n("speed_bytes_per_second")?.coerceAtLeast(0.0),
            totalTracks = n("total_tracks")?.toInt()?.coerceAtLeast(0),
            remainingTracks = n("remaining_tracks")?.toInt()?.coerceAtLeast(0),
            totalSizeBytes = n("total_size_bytes")?.coerceAtLeast(0.0),
            remainingSizeBytes = n("remaining_size_bytes")?.coerceAtLeast(0.0),
        )
    }

    /** Seconds until "use next source" is allowed, or null when the server has not offered it. */
    fun skipSecondsLeft(nowEpochSeconds: Double): Int? {
        if (status.lowercase() != "downloading") return null
        val stalled = number("stall_detected_at") ?: return null
        if ((number("fallback_count") ?: 0.0) <= 0.0) return null
        return (SKIP_WAIT_SECONDS - (nowEpochSeconds - stalled).toInt()).coerceAtLeast(0)
    }
}

@Serializable
private data class AcquisitionsBody(val acquisitions: List<JsonObject> = emptyList())

/** Decodes a snapshot (route body or one stream event). Records without an artist and album are dropped. */
fun parseAcquisitions(body: String): List<AcquisitionJob> =
    ApiJson.decodeFromString(AcquisitionsBody.serializer(), body).acquisitions.mapNotNull { raw ->
        fun s(name: String) = (raw[name] as? JsonPrimitive)?.takeIf { it.isString }?.content.orEmpty()
        val artist = s("artist")
        val album = s("album")
        if (artist.isBlank() && album.isBlank()) return@mapNotNull null
        AcquisitionJob(
            artist, album, s("status"),
            createdAt = (raw["created_at"] as? JsonPrimitive)?.doubleOrNull ?: 0.0,
            updatedAt = ((raw["updated_at"] ?: (raw["details"] as? JsonObject)?.get("updated_at")) as? JsonPrimitive)?.doubleOrNull,
            details = raw["details"] as? JsonObject ?: JsonObject(emptyMap()),
        )
    }

/**
 * Newest request first. The server orders by last update, which made an active download jump to the
 * top every second; the web orders by creation time instead, and so does the app.
 */
fun orderAcquisitions(jobs: List<AcquisitionJob>): List<AcquisitionJob> =
    jobs.withIndex().sortedWith(
        compareByDescending<IndexedValue<AcquisitionJob>> { it.value.createdAt }
            .thenBy { it.value.key }
            .thenBy { it.index },
    ).map { it.value }

fun activeCount(jobs: List<AcquisitionJob>) = jobs.count { it.isActive }

// ---- Launching (POST /api/acquire, POST /api/acquire/track)

/** What the Get control shows. Only [Requested] means the server accepted the request. */
sealed interface GetState {
    data object Idle : GetState
    data object Pending : GetState
    data class Requested(val message: String?) : GetState
    data class Failed(val message: String) : GetState
}

/**
 * Reads a launch reply. The server answers 200 with `ok: false` when it cannot place a request (for
 * example no slskd key), and a song search that finds nothing is a finished request, so Get stays
 * usable: both are failures here (web `searchAlbum` and `searchTrack`).
 */
fun launchOutcome(body: String): GetState {
    val reply = try {
        ApiJson.parseToJsonElement(body) as? JsonObject
    } catch (e: Exception) {
        null
    } ?: return GetState.Failed("The server's answer was not understood.")
    fun s(name: String) = (reply[name] as? JsonPrimitive)?.takeIf { it.isString }?.content?.takeIf { it.isNotBlank() }
    val message = s("message")
    if ((reply["ok"] as? JsonPrimitive)?.booleanOrNull == false) {
        return GetState.Failed(message ?: s("error") ?: "The request could not be placed.")
    }
    if (s("status") == "no_matches") return GetState.Failed(message ?: "No matches were found.")
    return GetState.Requested(message)
}

fun albumLaunchBody(artist: String, album: String, metadata: JsonObject): String = buildJsonObject {
    put("artist", artist)
    put("album", album)
    put("metadata", metadata)
    put("auto_queue", true)
}.toString()

fun trackLaunchBody(artist: String, album: String, title: String, trackNumber: Int?, year: Int?, metadata: JsonObject?): String =
    buildJsonObject {
        put("artist", artist)
        put("album", album)
        put("title", title)
        if (trackNumber != null && trackNumber > 0) put("track_number", trackNumber)
        if (year != null && year > 0) put("year", year)
        if (metadata != null) put("metadata", metadata)
    }.toString()

fun identityBody(artist: String, album: String): String = buildJsonObject {
    put("artist", artist)
    put("album", album)
}.toString()

/** The `message` of a skip or dismiss reply, when there is one. */
fun replyMessage(body: String): String? = try {
    ((ApiJson.parseToJsonElement(body) as? JsonObject)?.get("message") as? JsonPrimitive)?.contentOrNull
} catch (e: Exception) {
    null
}

/** Key a Get control is remembered under: the song for a song request, otherwise the album. */
fun getKey(artist: String, album: String, title: String? = null): String =
    listOf(artist.trim().lowercase(), album.trim().lowercase(), title?.trim()?.lowercase().orEmpty()).joinToString("::")

// ---- Figures on a progress row (web `formatDownloadBytes` and the speed text in `renderAcquisitions`)

/** "1.5 MB", "812 KB": one decimal below 100 of a unit, none above, as the web prints sizes. */
fun formatBytes(bytes: Double?): String? {
    if (bytes == null || bytes < 0) return null
    val units = listOf("B", "KB", "MB", "GB", "TB")
    var amount = bytes
    var unit = 0
    while (amount >= 1024 && unit < units.lastIndex) {
        amount /= 1024
        unit += 1
    }
    return (if (amount >= 100 || unit == 0) "%.0f".format(java.util.Locale.ROOT, amount) else "%.1f".format(java.util.Locale.ROOT, amount)) + " " + units[unit]
}

fun formatSpeed(bytesPerSecond: Double?): String = when {
    bytesPerSecond == null -> "Speed unavailable"
    bytesPerSecond >= 1024 * 1024 -> "%.1f MB/s".format(java.util.Locale.ROOT, bytesPerSecond / (1024 * 1024))
    bytesPerSecond >= 1024 -> "%.0f KB/s".format(java.util.Locale.ROOT, bytesPerSecond / 1024)
    else -> "%.0f B/s".format(java.util.Locale.ROOT, bytesPerSecond)
}
